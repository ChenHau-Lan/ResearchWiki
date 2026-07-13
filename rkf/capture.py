"""Canonical RKF capture classification, deduplication, and event routing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .core import Workspace, extract_doi, normalize_doi, read_json
from .events import (
    build_operational_event,
    load_recent_operational_events,
    public_safety_violations,
    valid_event_envelope,
    write_operational_event,
)


SOURCE_TERMS = {
    "paper",
    "papers",
    "doi",
    "citation",
    "reference",
    "journal",
    "literature",
    "source",
    "arxiv",
    "pubmed",
    "文獻",
    "論文",
}
RESEARCH_TERMS = {
    "synthesis",
    "method",
    "experiment design",
    "manuscript",
    "hypothesis",
    "claim",
    "evidence",
    "研究",
    "方法",
    "實驗",
    "假說",
    "證據",
    "綜整",
}
CODING_ONLY_TERMS = {
    "css",
    "button",
    "padding",
    "typescript",
    "react component",
    "build error",
    "lint error",
}
MAX_CAPTURE_CHARS = 12_000


@dataclass(frozen=True)
class CaptureInput:
    text: str
    origin: str
    title: str = ""
    doi: str = ""
    source_url: str = ""
    authors: str = ""
    year: str = ""
    intent: str = "research-discussion"
    reader_note: str = ""
    agent_note: str = ""
    topic_id: str = ""
    create_paper_draft: bool = True


@dataclass(frozen=True)
class CaptureDecision:
    level: str
    targets: list[str]
    reasons: list[str]


@dataclass(frozen=True)
class DedupeResult:
    status: str
    matched_id: str
    key: str


@dataclass(frozen=True)
class CaptureRoute:
    event_path: str
    event_id: str
    decision: CaptureDecision
    dedupe: DedupeResult
    materialize: bool
    created: str
    transaction_recovered: bool = False


class CaptureTransactionConflict(RuntimeError):
    """Raised when a deterministic capture transaction cannot be reused safely."""


_CAPTURE_EVENT_PAYLOAD_KEYS = {
    "title",
    "text",
    "doi",
    "source_url",
    "authors",
    "year",
    "intent",
    "reader_note",
    "agent_note",
    "topic_id",
    "create_paper_draft",
    "targets",
    "reasons",
    "dedupe_status",
    "materialize",
    "matched_id",
    "content_fingerprint",
    "normalized_text",
    "promotion",
}


def _contains(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _canonical_doi(item: CaptureInput) -> str:
    return normalize_doi(
        item.doi
        or extract_doi(
            "\n".join([item.title, item.text, item.source_url])
        )
    )


def classify_capture(item: CaptureInput) -> CaptureDecision:
    haystack = " ".join(str(value) for value in asdict(item).values()).strip()
    if len(haystack) > MAX_CAPTURE_CHARS:
        return CaptureDecision("blocked", [], ["too-long"])
    violations = public_safety_violations(asdict(item))
    if violations:
        return CaptureDecision("blocked", [], violations)
    if not haystack or _contains(haystack, CODING_ONLY_TERMS):
        return CaptureDecision("none", [], ["ordinary-or-uncertain"])

    doi = _canonical_doi(item)
    bibliographic_hint = item.intent == "paper-search" and bool(
        item.title or item.authors or item.year
    )
    source_like = bool(
        doi
        or item.source_url
        or bibliographic_hint
        or _contains(haystack, SOURCE_TERMS)
    )
    research_discussion = _contains(haystack, RESEARCH_TERMS)
    if not source_like and not research_discussion:
        return CaptureDecision("none", [], ["uncertain"])

    targets = ["inbox"]
    reasons: list[str] = []
    if doi:
        reasons.append("doi")
    if item.source_url:
        reasons.append("url")
    if source_like:
        reasons.append("source-like")
        targets.append("hot")
    if research_discussion:
        reasons.append("research-discussion")
    level = "aggressive" if research_discussion else "active"
    return CaptureDecision(level, sorted(set(targets)), sorted(set(reasons)))


def _normalized_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def _canonical_url(value: str) -> str:
    if not value.strip():
        return ""
    parts = urlsplit(value.strip())
    query = sorted(
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    )
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(query),
            "",
        )
    )


def _fingerprint(item: CaptureInput) -> str:
    normalized = json.dumps(
        {
            "title": _normalized_title(item.title),
            "text": " ".join(item.text.lower().split()),
            "url": _canonical_url(item.source_url),
            "doi": _canonical_doi(item),
        },
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def dedupe_capture(
    ws: Workspace,
    item: CaptureInput,
    *,
    now: datetime,
) -> DedupeResult:
    doi = _canonical_doi(item)
    normalized_title = _normalized_title(item.title)
    ambiguous_title = ""
    source_paths = sorted(ws.paths.sources.glob("*.json")) if ws.paths.sources.exists() else []
    for path in source_paths:
        record = read_json(path)
        source_id = str(record.get("source_id", path.stem))
        if doi and doi == str(record.get("normalized_doi", "")):
            return DedupeResult("existing", source_id, f"doi:{doi}")
        canonical_url = _canonical_url(item.source_url)
        if canonical_url and canonical_url == _canonical_url(str(record.get("value", ""))):
            return DedupeResult("existing", source_id, f"url:{canonical_url}")
        if normalized_title and normalized_title == _normalized_title(
            str(record.get("title", ""))
        ):
            record_text = _normalized_title(json.dumps(record, ensure_ascii=False))
            author_hint = _normalized_title(item.authors)
            year_hint = item.year.strip().lower()
            author_matches = not author_hint or author_hint in record_text
            year_matches = not year_hint or year_hint in record_text
            if (author_hint or year_hint) and author_matches and year_matches:
                return DedupeResult(
                    "existing",
                    source_id,
                    f"title:{normalized_title}:{author_hint}:{year_hint}",
                )
            ambiguous_title = source_id
    if ambiguous_title:
        return DedupeResult("ambiguous", ambiguous_title, f"title:{normalized_title}")

    fingerprint = _fingerprint(item)
    recent = load_recent_operational_events(ws, since=now - timedelta(hours=24))
    normalized_text = " ".join(item.text.lower().split())
    for event in recent:
        payload = event.get("payload", {})
        if payload.get("content_fingerprint") == fingerprint:
            return DedupeResult(
                "existing",
                str(event.get("event_id", "")),
                f"fingerprint:{fingerprint}",
            )
        if (
            event.get("origin") == item.origin
            and payload.get("intent") == item.intent
            and payload.get("normalized_text") == normalized_text
        ):
            return DedupeResult(
                "existing",
                str(event.get("event_id", "")),
                "recent-origin-intent",
            )
    key = f"doi:{doi}" if doi else f"fingerprint:{fingerprint}"
    return DedupeResult("new", "", key)


def _normalized_machine_id(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def _capture_payload_invariants(
    item: CaptureInput,
    *,
    decision: CaptureDecision,
    doi: str,
    fingerprint: str,
) -> dict[str, Any]:
    return {
        "title": item.title,
        "text": item.text,
        "doi": doi,
        "source_url": item.source_url,
        "authors": item.authors,
        "year": item.year,
        "intent": item.intent,
        "reader_note": item.reader_note,
        "agent_note": item.agent_note,
        "topic_id": item.topic_id,
        "create_paper_draft": item.create_paper_draft,
        "targets": decision.targets,
        "reasons": decision.reasons,
        "content_fingerprint": fingerprint,
        "normalized_text": " ".join(item.text.lower().split()),
        "promotion": "none",
    }


def _capture_payload(
    item: CaptureInput,
    *,
    decision: CaptureDecision,
    dedupe: DedupeResult,
    doi: str,
    fingerprint: str,
) -> dict[str, Any]:
    return {
        **_capture_payload_invariants(
            item,
            decision=decision,
            doi=doi,
            fingerprint=fingerprint,
        ),
        "dedupe_status": dedupe.status,
        "materialize": dedupe.status == "new",
        "matched_id": dedupe.matched_id,
    }


def _transaction_event_matches(
    ws: Workspace,
    *,
    idempotency_key: str,
) -> list[tuple[Path, dict[str, Any]]]:
    """Return parseable events carrying one exact transaction key.

    Operational-event loading normally ignores malformed files.  Recovery must
    be stricter: a parseable envelope that claims this transaction key but is
    invalid is itself a conflict and must never be bypassed by writing another
    event.
    """

    if not ws.paths.events.exists():
        return []
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(ws.paths.events.rglob("evt_*.json")):
        try:
            event = read_json(path)
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(event, dict) or event.get("idempotency_key") != idempotency_key:
            continue
        if not valid_event_envelope(event):
            raise CaptureTransactionConflict(
                "capture transaction has an invalid matching event envelope"
            )
        matches.append((path, event))
    return matches


def _recover_capture_transaction(
    ws: Workspace,
    item: CaptureInput,
    *,
    decision: CaptureDecision,
    doi: str,
    fingerprint: str,
    machine_id: str,
    actor: str,
    idempotency_key: str,
) -> CaptureRoute | None:
    matches = _transaction_event_matches(
        ws,
        idempotency_key=idempotency_key,
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise CaptureTransactionConflict(
            "capture transaction has duplicate matching events"
        )

    path, event = matches[0]
    if event["actor"] != actor:
        raise CaptureTransactionConflict(
            "capture transaction actor does not match the retry actor"
        )
    expected_machine = _normalized_machine_id(machine_id)
    if not expected_machine or event["machine_id"] != expected_machine:
        raise CaptureTransactionConflict(
            "capture transaction writer does not match the retry writer"
        )
    expected_target = f"doi:{doi}" if doi else f"fingerprint:{fingerprint}"
    if (
        event["origin"] != item.origin.strip()
        or event["target_identity"] != expected_target
    ):
        raise CaptureTransactionConflict(
            "capture transaction identity does not match the retry input"
        )

    payload = event["payload"]
    if set(payload) != _CAPTURE_EVENT_PAYLOAD_KEYS:
        raise CaptureTransactionConflict(
            "capture transaction payload shape does not match the current contract"
        )
    expected_payload = _capture_payload_invariants(
        item,
        decision=decision,
        doi=doi,
        fingerprint=fingerprint,
    )
    if any(
        type(payload.get(key)) is not type(value) or payload.get(key) != value
        for key, value in expected_payload.items()
    ):
        raise CaptureTransactionConflict(
            "capture transaction payload does not match the retry input"
        )

    dedupe_status = payload.get("dedupe_status")
    materialize = payload.get("materialize")
    matched_id = payload.get("matched_id")
    if (
        dedupe_status not in {"new", "existing", "ambiguous"}
        or type(materialize) is not bool
        or materialize is not (dedupe_status == "new")
        or not isinstance(matched_id, str)
        or event["action"]
        != ("capture.review" if dedupe_status == "ambiguous" else "capture.route")
    ):
        raise CaptureTransactionConflict(
            "capture transaction deduplication state is inconsistent"
        )

    dedupe = DedupeResult(
        status=str(dedupe_status),
        matched_id=matched_id,
        key=idempotency_key,
    )
    return CaptureRoute(
        event_path=path.relative_to(ws.paths.wiki_root).as_posix(),
        event_id=str(event["event_id"]),
        decision=decision,
        dedupe=dedupe,
        materialize=materialize,
        created=str(event["created"]),
        transaction_recovered=True,
    )


def route_capture(
    ws: Workspace,
    item: CaptureInput,
    *,
    machine_id: str,
    actor: str = "codex",
    now: datetime | None = None,
    idempotency_key: str = "",
) -> CaptureRoute:
    instant = now or datetime.now(timezone.utc)
    decision = classify_capture(item)
    if decision.level == "blocked":
        raise SystemExit(f"capture.route blocked: {','.join(decision.reasons)}")
    if decision.level == "none":
        raise SystemExit("capture.route did not find a deterministic research trigger")

    doi = _canonical_doi(item)
    fingerprint = _fingerprint(item)
    transaction_key = idempotency_key.strip()
    if transaction_key:
        recovered = _recover_capture_transaction(
            ws,
            item,
            decision=decision,
            doi=doi,
            fingerprint=fingerprint,
            machine_id=machine_id,
            actor=actor,
            idempotency_key=transaction_key,
        )
        if recovered is not None:
            return recovered

    dedupe = dedupe_capture(ws, item, now=instant)
    action = "capture.review" if dedupe.status == "ambiguous" else "capture.route"
    payload = _capture_payload(
        item,
        decision=decision,
        dedupe=dedupe,
        doi=doi,
        fingerprint=fingerprint,
    )
    event = build_operational_event(
        action=action,
        actor=actor,
        origin=item.origin,
        machine_id=machine_id,
        target_identity=(
            f"doi:{doi}" if doi else f"fingerprint:{fingerprint}"
        ),
        idempotency_key=transaction_key or dedupe.key,
        payload=payload,
        created=instant,
    )
    path = write_operational_event(ws, event)
    return CaptureRoute(
        event_path=path.relative_to(ws.paths.wiki_root).as_posix(),
        event_id=event.event_id,
        decision=decision,
        dedupe=dedupe,
        materialize=dedupe.status == "new",
        created=event.created,
        transaction_recovered=False,
    )


def projection_checkpoint(ws: Workspace, event_id: str) -> dict[str, Any]:
    path = ws.paths.sync_state / "projections" / f"{event_id}.json"
    if not path.exists():
        return {
            "schema": "rkf-projection-checkpoint-v1",
            "event_id": event_id,
            "completed_targets": [],
        }
    try:
        state = read_json(path)
    except (OSError, ValueError, TypeError):
        return {
            "schema": "rkf-projection-checkpoint-v1",
            "event_id": event_id,
            "completed_targets": [],
        }
    return state


def record_projection_target(ws: Workspace, event_id: str, target: str) -> None:
    state = projection_checkpoint(ws, event_id)
    completed = {str(item) for item in state.get("completed_targets", [])}
    completed.add(target)
    destination = ws.paths.sync_state / "projections" / f"{event_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.tmp-{secrets.token_hex(6)}"
    )
    data = {
        "schema": "rkf-projection-checkpoint-v1",
        "event_id": event_id,
        "completed_targets": sorted(completed),
        "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def pending_projection_events(ws: Workspace) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    from .events import load_operational_events

    for event in load_operational_events(ws):
        payload = event.get("payload", {})
        if event.get("action") != "capture.route" or not payload.get("materialize"):
            continue
        targets = {str(item) for item in payload.get("targets", [])}
        completed = {
            str(item)
            for item in projection_checkpoint(ws, str(event.get("event_id", ""))).get(
                "completed_targets", []
            )
        }
        if targets - completed:
            pending.append(event)
    return pending
