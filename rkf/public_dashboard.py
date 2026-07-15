"""Aggregate-only, publication-gated snapshots for the RKF public dashboard.

The dashboard is deliberately not a live view of the wiki.  It exposes a
small, fixed set of counters and machine-neutral settings.  A preview is first
written under the ignored ``.rkf_private`` tree; publication then requires the
exact aggregate hash from that preview.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
from collections import Counter
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from .core import (
    CLAIM_READINESS,
    DOI_RE,
    FULLTEXT_STATUSES,
    HUMAN_FEEDBACK_LEVELS,
    KNOWLEDGE_TYPES,
    LOCAL_PATH_PATTERNS,
    PAPER_READING_STATUSES,
    SYNTHESIS_MATURITY,
    Workspace,
    build_research_graph,
    knowledge_page_records,
    lint_ars_handoff,
    lint_graph_links,
    lint_knowledge_pages,
    lint_public_safety,
    lint_topics,
    paper_queue,
    read_json,
    recent_hot_events,
)
from .sync import atomic_write_text, run_connect_doctor, sha256_file
from .discovery import (
    DiscoveryError,
    load_acceptance_state,
    load_discovery_run,
    validate_legacy_discovery_run,
)


PUBLIC_DASHBOARD_SCHEMA = "rkf-public-dashboard-v1"
PREVIEW_MANIFEST_SCHEMA = "rkf-dashboard-preview-manifest-v1"
REVIEW_BUNDLE_SCHEMA = "rkf-dashboard-review-bundle-v1"
PUBLIC_SNAPSHOT_FILENAME = "rkf-public-snapshot.json"
DEFAULT_HOT_WINDOW_DAYS = 30
MAX_HOTSPOTS = 12
MAX_REGISTERED_RESEARCH_AREAS = 12
REVIEW_ENTRY_FILE = "index.html"
REVIEW_STATIC_FILES = (
    "index.html",
    "getting-started.html",
    "favicon.svg",
    "assets/app.js",
    "assets/styles.css",
)
REVIEW_GENERATED_FILES = (
    *REVIEW_STATIC_FILES,
    f"data/{PUBLIC_SNAPSHOT_FILENAME}",
    "review-manifest.json",
)

PUBLICATION_STATUSES = {"pending-review", "published", "synthetic-preview"}
CONNECTION_STATUSES = {"ok", "warning", "blocked"}
WRITER_ROLES = {"designated", "other", "unregistered", "conflict", "unknown"}
REVIEW_CADENCES = {"daily", "weekly", "monthly", "quarterly", "annual", "other", "unknown"}
QUEUE_ACTIONS = {
    "create-paper-draft",
    "request-user-pdf",
    "review-reading",
    "synthesis-review",
    "other",
}
DISCOVERY_DECISIONS = {"candidate", "accepted", "rejected", "duplicate", "ambiguous", "other"}
LINT_CATEGORIES = {"structure", "topic", "graph", "ars-handoff", "public-safety"}
SAFE_SCHEMA_RE = re.compile(r"^rkf-v[0-9]+(?:\.[0-9]+)*$")
SAFE_TOPIC_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_PREVIEW_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z_[0-9a-f]{12}$")
EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
SECRET_RE = re.compile(r"(?:api[_-]?key|access[_-]?token|private[_-]?key|password)\s*[:=]", re.IGNORECASE)
ABSOLUTE_PATH_RE = re.compile(r"(?:^|\s)/(?:[^/\s]+/)+[^/\s]+")
WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:[\\/](?:[^\\/\s]+[\\/])+[^\\/\s]+")
TOKENISH_RE = re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b", re.IGNORECASE)


class DashboardSafetyError(ValueError):
    """Raised when a snapshot violates the public aggregate contract."""


def _utc_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _snapshot_digest(payload: dict[str, Any]) -> str:
    hashable = {key: value for key, value in payload.items() if key not in {"snapshot_hash", "publication"}}
    return sha256(_canonical_json(hashable).encode("utf-8")).hexdigest()


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _contained(root: Path, candidate: Path) -> Path:
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise DashboardSafetyError("dashboard path escapes its allowed root") from exc
    lexical = root
    if lexical.is_symlink():
        raise DashboardSafetyError("dashboard path must not use a symlink")
    for part in relative.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise DashboardSafetyError("dashboard path must not use a symlink")
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise DashboardSafetyError("dashboard path escapes its allowed root") from exc
    return resolved_candidate


def _refuse_symlink(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise DashboardSafetyError(f"dashboard {label} must not be a symlink")


def _safe_public_label(value: Any, *, fallback: str) -> str:
    label = re.sub(r"\s+", " ", str(value or "")).strip()[:100]
    if not label:
        return fallback
    if DOI_RE.search(label) or EMAIL_RE.search(label) or SECRET_RE.search(label) or TOKENISH_RE.search(label):
        return fallback
    if ABSOLUTE_PATH_RE.search(label) or WINDOWS_PATH_RE.search(label) or any(
        pattern.search(label) for pattern in LOCAL_PATH_PATTERNS
    ):
        return fallback
    return label


def _fixed_counts(values: Iterable[Any], allowed: Iterable[str]) -> dict[str, int]:
    allowed_values = tuple(sorted(set(allowed)))
    counter = Counter(str(value) if str(value) in allowed_values else "other" for value in values)
    keys = tuple(value for value in allowed_values if value != "other") + (("other",) if "other" in allowed_values else ())
    return {key: int(counter.get(key, 0)) for key in keys}


def _config_section(ws: Workspace, name: str) -> dict[str, Any]:
    section = ws.config.get(name, {}) if isinstance(ws.config, dict) else {}
    return section if isinstance(section, dict) else {}


def _source_records(ws: Workspace) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not ws.paths.sources.exists():
        return records
    for path in sorted(ws.paths.sources.glob("*.json")):
        try:
            record = read_json(path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _legacy_discovery_candidate_count(payload: dict[str, Any]) -> int:
    """Validate the deprecated v1 shape without exposing or trusting decisions."""

    try:
        return validate_legacy_discovery_run(payload)
    except DiscoveryError as exc:
        raise DashboardSafetyError("legacy discovery state is invalid") from exc


def _discovery_aggregates(ws: Workspace) -> dict[str, Any]:
    run_count = 0
    candidate_count = 0
    decisions: list[str] = []
    if ws.paths.search_runs.exists():
        for path in sorted(ws.paths.search_runs.glob("run_*/candidates.json")):
            try:
                payload = load_discovery_run(ws, path.parent.name)
                acceptance = load_acceptance_state(ws, path.parent.name)
            except (DiscoveryError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DashboardSafetyError("governed discovery state is invalid") from exc
            run_count += 1
            accepted_ids = {
                str(item["candidate_id"])
                for item in acceptance.get("accepted", [])
                if isinstance(item, dict)
            }
            for candidate in payload["candidates"]:
                candidate_count += 1
                candidate_id = str(candidate.get("candidate_id", ""))
                if candidate_id in accepted_ids:
                    decision = "accepted"
                else:
                    decision = {
                        "existing": "duplicate",
                        "ambiguous": "ambiguous",
                    }.get(str(candidate.get("dedupe_status", "")), "candidate")
                decisions.append(decision)
        for path in sorted(ws.paths.search_runs.glob("*/candidates.json")):
            if path.parent.name.startswith("run_"):
                continue
            try:
                payload = read_json(path)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DashboardSafetyError("legacy discovery state is invalid") from exc
            if not isinstance(payload, dict):
                raise DashboardSafetyError("legacy discovery state is invalid")
            legacy_count = _legacy_discovery_candidate_count(payload)
            run_count += 1
            candidate_count += legacy_count
            decisions.extend(["other"] * legacy_count)
    return {
        "run_count": run_count,
        "candidate_count": candidate_count,
        "decision_counts": _fixed_counts(decisions, DISCOVERY_DECISIONS),
    }


def _public_topic_names(ws: Workspace) -> dict[str, str]:
    topic_names: dict[str, str] = {}
    for topic in ws.load_topics():
        if not isinstance(topic, dict):
            continue
        topic_id = str(topic.get("topic_id", "")).strip()
        if not SAFE_TOPIC_ID_RE.fullmatch(topic_id):
            continue
        topic_names[topic_id] = _safe_public_label(topic.get("name"), fallback=topic_id)
    return topic_names


def _registered_research_areas(topic_names: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"topic_id": topic_id, "name": name}
        for topic_id, name in sorted(topic_names.items())[:MAX_REGISTERED_RESEARCH_AREAS]
    ]


def _hotspot_aggregates(topic_names: dict[str, str], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for event in events:
        topic_ids = event.get("topic_ids", []) if isinstance(event, dict) else []
        if not isinstance(topic_ids, list):
            continue
        for topic_id_value in set(str(value).strip() for value in topic_ids):
            if topic_id_value in topic_names:
                counts[topic_id_value] += 1
    return [
        {"topic_id": topic_id, "name": topic_names[topic_id], "demand_count": int(count)}
        for topic_id, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:MAX_HOTSPOTS]
    ]


def _review_cadence(value: Any) -> str:
    cadence = str(value or "unknown").strip().lower()
    return cadence if cadence in REVIEW_CADENCES else "other"


def _knowledge_schema(value: Any) -> str:
    schema = str(value or "unknown").strip()
    return schema if SAFE_SCHEMA_RE.fullmatch(schema) else "unknown"


def _configured_handle(section: dict[str, Any], key: str) -> bool:
    return isinstance(section.get(key), str) and bool(str(section.get(key)).strip())


def _lint_counts(ws: Workspace) -> dict[str, int]:
    findings = {
        "structure": lint_knowledge_pages(ws),
        "topic": lint_topics(ws),
        "graph": lint_graph_links(ws),
        "ars-handoff": lint_ars_handoff(ws),
        "public-safety": lint_public_safety(ws),
    }
    return {category: len(findings[category]) for category in sorted(LINT_CATEGORIES)}


def build_public_snapshot(
    ws: Workspace,
    *,
    now: datetime | None = None,
    window_days: int = DEFAULT_HOT_WINDOW_DAYS,
    publication_status: str = "pending-review",
) -> dict[str, Any]:
    """Build a read-only public snapshot containing only allowlisted aggregates."""

    if isinstance(window_days, bool) or not isinstance(window_days, int):
        raise DashboardSafetyError("window_days must be an integer")
    if window_days < 1 or window_days > 365:
        raise DashboardSafetyError("window_days must be between 1 and 365")
    if publication_status not in PUBLICATION_STATUSES:
        raise DashboardSafetyError("invalid publication status")

    generated = _utc_now(now)
    events = recent_hot_events(ws, days=window_days) if ws.paths.hot_md.exists() else []
    pages = knowledge_page_records(ws)
    paper_pages = [meta for _, meta, _ in pages if meta.get("type") == "paper"]
    source_records = _source_records(ws)
    queue = paper_queue(ws)
    graph = build_research_graph(ws)
    topics = ws.load_topics()
    topic_names = _public_topic_names(ws)
    doctor = run_connect_doctor(ws, now=generated)

    storage = _config_section(ws, "storage")
    gates = _config_section(ws, "gates")
    knowledge = _config_section(ws, "knowledge")
    latest_dates = sorted(
        str(event.get("created", ""))[:10]
        for event in events
        if isinstance(event, dict) and str(event.get("created", ""))[:10]
    )
    topic_linked_count = sum(
        1
        for event in events
        if isinstance(event, dict)
        and isinstance(event.get("topic_ids"), list)
        and any(str(value).strip() in topic_names for value in event["topic_ids"])
    )
    paper_lead_count = sum(
        1 for event in events if isinstance(event, dict) and isinstance(event.get("paper_leads"), list) and event["paper_leads"]
    )
    doctor_severities = Counter(finding.severity for finding in doctor.findings)

    payload: dict[str, Any] = {
        "schema": PUBLIC_DASHBOARD_SCHEMA,
        "generated_at": _iso_z(generated),
        "window_days": window_days,
        "snapshot_hash": "",
        "publication": {
            "status": publication_status,
            "approved_snapshot_hash": "",
            "published_at": "",
        },
        "freshness": {
            "latest_hot_event_date": latest_dates[-1] if latest_dates else "",
            "hot_event_count": len(events),
        },
        "research_hotspots": _hotspot_aggregates(topic_names, events),
        "registered_research_areas": _registered_research_areas(topic_names),
        "demand": {
            "event_count": len(events),
            "topic_linked_event_count": topic_linked_count,
            "untriaged_event_count": len(events) - topic_linked_count,
            "paper_lead_event_count": paper_lead_count,
        },
        "discovery": _discovery_aggregates(ws),
        "paper_pipeline": {
            "source_count": len(source_records),
            "paper_page_count": len(paper_pages),
            "queue_count": len(queue),
            "queue_action_counts": _fixed_counts((item.get("action") for item in queue), QUEUE_ACTIONS),
            "reading_state_counts": _fixed_counts(
                (meta.get("reading_state", meta.get("reading_status", "other")) for meta in paper_pages),
                set(PAPER_READING_STATUSES) | {"other"},
            ),
            "fulltext_status_counts": _fixed_counts(
                (meta.get("fulltext_status", "other") for meta in paper_pages),
                set(FULLTEXT_STATUSES) | {"other"},
            ),
            "human_feedback_counts": _fixed_counts(
                (meta.get("human_feedback_level", "other") for meta in paper_pages),
                set(HUMAN_FEEDBACK_LEVELS) | {"other"},
            ),
            "claim_readiness_counts": _fixed_counts(
                (meta.get("claim_readiness", "other") for meta in paper_pages),
                set(CLAIM_READINESS) | {"other"},
            ),
        },
        "knowledge": {
            "page_count": len(pages),
            "registered_topic_count": sum(
                1
                for topic in topics
                if isinstance(topic, dict) and SAFE_TOPIC_ID_RE.fullmatch(str(topic.get("topic_id", "")))
            ),
            "type_counts": _fixed_counts((meta.get("type", "other") for _, meta, _ in pages), set(KNOWLEDGE_TYPES) | {"other"}),
            "synthesis_maturity_counts": _fixed_counts(
                (
                    meta.get("synthesis_maturity", "other")
                    for _, meta, _ in pages
                    if meta.get("type") == "synthesis"
                ),
                set(SYNTHESIS_MATURITY) | {"other"},
            ),
        },
        "graph": {
            "node_count": len(graph.get("nodes", [])),
            "edge_count": len(graph.get("edges", [])),
        },
        "framework": {
            "knowledge_schema": _knowledge_schema(knowledge.get("schema_version")),
            "review_cadence": _review_cadence(knowledge.get("default_review_cadence")),
            "storage_handles": {
                "wiki_root_configured": _configured_handle(storage, "wiki_root"),
                "raw_root_configured": _configured_handle(storage, "raw_root"),
                "private_evidence_configured": _configured_handle(storage, "private_evidence_root"),
            },
            "gates": {
                "require_pdf_checkpoint": gates.get("require_pdf_checkpoint") is True,
                "require_pdf_qc": gates.get("require_pdf_qc") is True,
                "require_claim_support": gates.get("require_claim_support") is True,
                "require_synthesis_review": gates.get("require_synthesis_review") is True,
            },
        },
        "health": {
            "connection_status": doctor.status if doctor.status in CONNECTION_STATUSES else "blocked",
            "writer_role": doctor.writer.get("role", "unknown")
            if doctor.writer.get("role", "unknown") in WRITER_ROLES
            else "unknown",
            "doctor_finding_count": len(doctor.findings),
            "doctor_blocker_count": int(doctor_severities.get("blocker", 0)),
            "doctor_warning_count": int(doctor_severities.get("warning", 0)),
            "lint_counts": _lint_counts(ws),
        },
        "safety": {
            "aggregate_only": True,
            "raw_questions_published": False,
            "paper_identity_published": False,
            "reading_ledgers_published": False,
            "article_text_published": False,
            "demand_is_evidence": False,
            "candidates_are_evidence": False,
        },
    }
    payload["snapshot_hash"] = _snapshot_digest(payload)
    validate_public_snapshot(payload)
    return payload


def _expected_top_level_keys() -> set[str]:
    return {
        "schema",
        "generated_at",
        "window_days",
        "snapshot_hash",
        "publication",
        "freshness",
        "research_hotspots",
        "registered_research_areas",
        "demand",
        "discovery",
        "paper_pipeline",
        "knowledge",
        "graph",
        "framework",
        "health",
        "safety",
    }


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def validate_public_snapshot(payload: dict[str, Any]) -> None:
    """Reject unallowlisted keys, invalid hashes, and obvious private strings."""

    if not isinstance(payload, dict) or set(payload) != _expected_top_level_keys():
        raise DashboardSafetyError("public snapshot has unallowlisted top-level fields")
    if payload.get("schema") != PUBLIC_DASHBOARD_SCHEMA:
        raise DashboardSafetyError("public snapshot schema is invalid")
    publication = payload.get("publication")
    if not isinstance(publication, dict) or set(publication) != {"status", "approved_snapshot_hash", "published_at"}:
        raise DashboardSafetyError("publication envelope is invalid")
    if publication.get("status") not in PUBLICATION_STATUSES:
        raise DashboardSafetyError("publication status is invalid")
    if not all(isinstance(publication.get(key), str) for key in ("status", "approved_snapshot_hash", "published_at")):
        raise DashboardSafetyError("publication envelope values are invalid")
    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str):
        raise DashboardSafetyError("generated_at is invalid")
    try:
        generated_time = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DashboardSafetyError("generated_at is invalid") from exc
    if generated_time.tzinfo is None:
        raise DashboardSafetyError("generated_at must include a timezone")
    window_days = payload.get("window_days")
    if isinstance(window_days, bool) or not isinstance(window_days, int) or not 1 <= window_days <= 365:
        raise DashboardSafetyError("window_days is invalid")
    supplied_hash = str(payload.get("snapshot_hash", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", supplied_hash) or supplied_hash != _snapshot_digest(payload):
        raise DashboardSafetyError("snapshot hash does not match the aggregate payload")

    fixed_shapes: tuple[tuple[Any, set[str]], ...] = (
        (payload.get("freshness"), {"latest_hot_event_date", "hot_event_count"}),
        (
            payload.get("demand"),
            {"event_count", "topic_linked_event_count", "untriaged_event_count", "paper_lead_event_count"},
        ),
        (payload.get("discovery"), {"run_count", "candidate_count", "decision_counts"}),
        (
            payload.get("paper_pipeline"),
            {
                "source_count",
                "paper_page_count",
                "queue_count",
                "queue_action_counts",
                "reading_state_counts",
                "fulltext_status_counts",
                "human_feedback_counts",
                "claim_readiness_counts",
            },
        ),
        (
            payload.get("knowledge"),
            {"page_count", "registered_topic_count", "type_counts", "synthesis_maturity_counts"},
        ),
        (payload.get("graph"), {"node_count", "edge_count"}),
        (payload.get("framework"), {"knowledge_schema", "review_cadence", "storage_handles", "gates"}),
        (
            payload.get("health"),
            {
                "connection_status",
                "writer_role",
                "doctor_finding_count",
                "doctor_blocker_count",
                "doctor_warning_count",
                "lint_counts",
            },
        ),
        (
            payload.get("safety"),
            {
                "aggregate_only",
                "raw_questions_published",
                "paper_identity_published",
                "reading_ledgers_published",
                "article_text_published",
                "demand_is_evidence",
                "candidates_are_evidence",
            },
        ),
    )
    for value, expected_keys in fixed_shapes:
        if not isinstance(value, dict) or set(value) != expected_keys:
            raise DashboardSafetyError("public snapshot contains an unallowlisted aggregate field")

    nested_shapes: tuple[tuple[Any, set[str]], ...] = (
        (payload["discovery"]["decision_counts"], DISCOVERY_DECISIONS),
        (payload["paper_pipeline"]["queue_action_counts"], QUEUE_ACTIONS),
        (
            payload["paper_pipeline"]["reading_state_counts"],
            set(PAPER_READING_STATUSES) | {"other"},
        ),
        (
            payload["paper_pipeline"]["fulltext_status_counts"],
            set(FULLTEXT_STATUSES) | {"other"},
        ),
        (
            payload["paper_pipeline"]["human_feedback_counts"],
            set(HUMAN_FEEDBACK_LEVELS) | {"other"},
        ),
        (
            payload["paper_pipeline"]["claim_readiness_counts"],
            set(CLAIM_READINESS) | {"other"},
        ),
        (payload["knowledge"]["type_counts"], set(KNOWLEDGE_TYPES) | {"other"}),
        (
            payload["knowledge"]["synthesis_maturity_counts"],
            set(SYNTHESIS_MATURITY) | {"other"},
        ),
        (payload["health"]["lint_counts"], LINT_CATEGORIES),
        (
            payload["framework"]["storage_handles"],
            {"wiki_root_configured", "raw_root_configured", "private_evidence_configured"},
        ),
        (
            payload["framework"]["gates"],
            {"require_pdf_checkpoint", "require_pdf_qc", "require_claim_support", "require_synthesis_review"},
        ),
    )
    for value, expected_keys in nested_shapes:
        if not isinstance(value, dict) or set(value) != set(expected_keys):
            raise DashboardSafetyError("public snapshot contains an unallowlisted nested field")

    hotspots = payload.get("research_hotspots")
    if not isinstance(hotspots, list) or len(hotspots) > MAX_HOTSPOTS:
        raise DashboardSafetyError("research hotspot aggregate is invalid")
    for hotspot in hotspots:
        if not isinstance(hotspot, dict) or set(hotspot) != {"topic_id", "name", "demand_count"}:
            raise DashboardSafetyError("research hotspot contains an unallowlisted field")
        if not SAFE_TOPIC_ID_RE.fullmatch(str(hotspot.get("topic_id", ""))):
            raise DashboardSafetyError("research hotspot topic_id is invalid")
        if not isinstance(hotspot.get("name"), str) or not 1 <= len(hotspot["name"]) <= 100:
            raise DashboardSafetyError("research hotspot public name is invalid")

    registered_areas = payload.get("registered_research_areas")
    if not isinstance(registered_areas, list) or len(registered_areas) > MAX_REGISTERED_RESEARCH_AREAS:
        raise DashboardSafetyError("registered research-area aggregate is invalid")
    for area in registered_areas:
        if not isinstance(area, dict) or set(area) != {"topic_id", "name"}:
            raise DashboardSafetyError("registered research area contains an unallowlisted field")
        if not SAFE_TOPIC_ID_RE.fullmatch(str(area.get("topic_id", ""))):
            raise DashboardSafetyError("registered research-area topic_id is invalid")
        if not isinstance(area.get("name"), str) or not 1 <= len(area["name"]) <= 100:
            raise DashboardSafetyError("registered research-area public name is invalid")

    count_maps = (
        payload["discovery"]["decision_counts"],
        payload["paper_pipeline"]["queue_action_counts"],
        payload["paper_pipeline"]["reading_state_counts"],
        payload["paper_pipeline"]["fulltext_status_counts"],
        payload["paper_pipeline"]["human_feedback_counts"],
        payload["paper_pipeline"]["claim_readiness_counts"],
        payload["knowledge"]["type_counts"],
        payload["knowledge"]["synthesis_maturity_counts"],
        payload["health"]["lint_counts"],
    )
    scalar_counts = (
        payload["freshness"]["hot_event_count"],
        *payload["demand"].values(),
        payload["discovery"]["run_count"],
        payload["discovery"]["candidate_count"],
        payload["paper_pipeline"]["source_count"],
        payload["paper_pipeline"]["paper_page_count"],
        payload["paper_pipeline"]["queue_count"],
        payload["knowledge"]["page_count"],
        payload["knowledge"]["registered_topic_count"],
        payload["graph"]["node_count"],
        payload["graph"]["edge_count"],
        payload["health"]["doctor_finding_count"],
        payload["health"]["doctor_blocker_count"],
        payload["health"]["doctor_warning_count"],
        *(hotspot["demand_count"] for hotspot in hotspots),
        *(count for counts in count_maps for count in counts.values()),
    )
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in scalar_counts):
        raise DashboardSafetyError("public snapshot count is invalid")

    if payload["health"]["connection_status"] not in CONNECTION_STATUSES:
        raise DashboardSafetyError("connection status is invalid")
    if payload["health"]["writer_role"] not in WRITER_ROLES:
        raise DashboardSafetyError("writer role is invalid")
    if payload["framework"]["review_cadence"] not in REVIEW_CADENCES:
        raise DashboardSafetyError("review cadence is invalid")
    if not (
        payload["framework"]["knowledge_schema"] == "unknown"
        or SAFE_SCHEMA_RE.fullmatch(str(payload["framework"]["knowledge_schema"]))
    ):
        raise DashboardSafetyError("knowledge schema is invalid")
    if not all(
        isinstance(value, bool)
        for value in (
            *payload["framework"]["storage_handles"].values(),
            *payload["framework"]["gates"].values(),
            *payload["safety"].values(),
        )
    ):
        raise DashboardSafetyError("public snapshot boolean setting is invalid")
    if payload["safety"] != {
        "aggregate_only": True,
        "raw_questions_published": False,
        "paper_identity_published": False,
        "reading_ledgers_published": False,
        "article_text_published": False,
        "demand_is_evidence": False,
        "candidates_are_evidence": False,
    }:
        raise DashboardSafetyError("public snapshot safety boundary is invalid")

    latest_event_date = payload["freshness"]["latest_hot_event_date"]
    if not isinstance(latest_event_date, str):
        raise DashboardSafetyError("latest hot-event date is invalid")
    if latest_event_date:
        try:
            date.fromisoformat(latest_event_date)
        except ValueError as exc:
            raise DashboardSafetyError("latest hot-event date is invalid") from exc
    if payload["freshness"]["hot_event_count"] != payload["demand"]["event_count"]:
        raise DashboardSafetyError("hot-event aggregates are inconsistent")
    if (
        payload["demand"]["topic_linked_event_count"] + payload["demand"]["untriaged_event_count"]
        != payload["demand"]["event_count"]
    ):
        raise DashboardSafetyError("demand aggregates are inconsistent")
    if payload["demand"]["paper_lead_event_count"] > payload["demand"]["event_count"]:
        raise DashboardSafetyError("paper-lead aggregate is inconsistent")
    if sum(payload["discovery"]["decision_counts"].values()) != payload["discovery"]["candidate_count"]:
        raise DashboardSafetyError("discovery aggregates are inconsistent")
    if sum(payload["paper_pipeline"]["queue_action_counts"].values()) != payload["paper_pipeline"]["queue_count"]:
        raise DashboardSafetyError("paper-queue aggregates are inconsistent")
    for key in (
        "reading_state_counts",
        "fulltext_status_counts",
        "human_feedback_counts",
        "claim_readiness_counts",
    ):
        if sum(payload["paper_pipeline"][key].values()) != payload["paper_pipeline"]["paper_page_count"]:
            raise DashboardSafetyError("paper-maturity aggregates are inconsistent")
    if sum(payload["knowledge"]["type_counts"].values()) != payload["knowledge"]["page_count"]:
        raise DashboardSafetyError("knowledge aggregates are inconsistent")
    if sum(payload["knowledge"]["synthesis_maturity_counts"].values()) > payload["knowledge"]["type_counts"]["synthesis"]:
        raise DashboardSafetyError("synthesis aggregates are inconsistent")

    status = publication["status"]
    if status == "published":
        if publication["approved_snapshot_hash"] != supplied_hash or not publication["published_at"]:
            raise DashboardSafetyError("published snapshot is missing exact-hash approval metadata")
        try:
            published_time = datetime.fromisoformat(str(publication["published_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise DashboardSafetyError("published_at is invalid") from exc
        if published_time.tzinfo is None:
            raise DashboardSafetyError("published_at must include a timezone")
    elif publication["approved_snapshot_hash"] or publication["published_at"]:
        raise DashboardSafetyError("unpublished snapshot cannot carry approval metadata")

    forbidden_keys = {
        "query",
        "title",
        "doi",
        "path",
        "machine_id",
        "event_id",
        "source_id",
        "reading_ledger",
        "abstract",
        "article_text",
        "notes",
        "paper_leads",
    }

    def check_keys(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in forbidden_keys:
                    raise DashboardSafetyError("public snapshot contains a forbidden identity or content field")
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)

    check_keys(payload)
    for text in _walk_strings(payload):
        if DOI_RE.search(text) or EMAIL_RE.search(text) or SECRET_RE.search(text) or TOKENISH_RE.search(text):
            raise DashboardSafetyError("public snapshot contains a private or source-identity string")
        if ABSOLUTE_PATH_RE.search(text) or WINDOWS_PATH_RE.search(text) or any(
            pattern.search(text) for pattern in LOCAL_PATH_PATTERNS
        ):
            raise DashboardSafetyError("public snapshot contains a local path")


def dashboard_preview_root(ws: Workspace) -> Path:
    private_root = ws.root / ".rkf_private"
    preview_root = private_root / "dashboard_previews"
    _refuse_symlink(private_root, label="private root")
    _refuse_symlink(preview_root, label="preview root")
    return preview_root.resolve()


def preview_public_dashboard(
    ws: Workspace,
    *,
    now: datetime | None = None,
    window_days: int = DEFAULT_HOT_WINDOW_DAYS,
) -> dict[str, Any]:
    """Atomically create a private review bundle and return path-redacted metadata."""

    generated = _utc_now(now)
    snapshot = build_public_snapshot(ws, now=generated, window_days=window_days)
    preview_id = f"{generated.strftime('%Y%m%dT%H%M%SZ')}_{snapshot['snapshot_hash'][:12]}"
    root = dashboard_preview_root(ws)
    preview_dir = _contained(root, root / preview_id)
    _refuse_symlink(preview_dir, label="preview directory")
    if preview_dir.exists():
        raise DashboardSafetyError("dashboard preview already exists")
    snapshot_path = _contained(preview_dir, preview_dir / "snapshot.json")
    manifest_path = _contained(preview_dir, preview_dir / "manifest.json")
    manifest = {
        "schema": PREVIEW_MANIFEST_SCHEMA,
        "preview_id": preview_id,
        "snapshot_hash": snapshot["snapshot_hash"],
        "snapshot_file": "snapshot.json",
        "generated_at": snapshot["generated_at"],
        "publication_status": "pending-review",
    }
    snapshot_result = atomic_write_text(snapshot_path, _json_text(snapshot), expected_checksum="")
    if not snapshot_result.written:
        raise DashboardSafetyError(f"cannot create dashboard preview snapshot: {snapshot_result.reason}")
    manifest_result = atomic_write_text(manifest_path, _json_text(manifest), expected_checksum="")
    if not manifest_result.written:
        raise DashboardSafetyError(f"cannot create dashboard preview manifest: {manifest_result.reason}")
    return {
        "schema": PREVIEW_MANIFEST_SCHEMA,
        "preview_id": preview_id,
        "snapshot_hash": snapshot["snapshot_hash"],
        "publication_status": "pending-review",
        "paths_redacted": True,
    }


def load_dashboard_preview(ws: Workspace, preview_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not SAFE_PREVIEW_ID_RE.fullmatch(preview_id):
        raise DashboardSafetyError("preview_id is invalid")
    root = dashboard_preview_root(ws)
    preview_dir = _contained(root, root / preview_id)
    snapshot_path = _contained(preview_dir, preview_dir / "snapshot.json")
    manifest_path = _contained(preview_dir, preview_dir / "manifest.json")
    _refuse_symlink(preview_dir, label="preview directory")
    _refuse_symlink(snapshot_path, label="preview snapshot")
    _refuse_symlink(manifest_path, label="preview manifest")
    if not snapshot_path.is_file() or not manifest_path.is_file():
        raise DashboardSafetyError("dashboard preview is incomplete")
    try:
        snapshot = read_json(snapshot_path)
        manifest = read_json(manifest_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DashboardSafetyError("dashboard preview is unreadable") from exc
    validate_public_snapshot(snapshot)
    expected_manifest_fields = {
        "schema",
        "preview_id",
        "snapshot_hash",
        "snapshot_file",
        "generated_at",
        "publication_status",
    }
    publication = snapshot.get("publication")
    generated_at = str(snapshot.get("generated_at", ""))
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DashboardSafetyError("dashboard preview timestamp is invalid") from exc
    expected_preview_id = (
        f"{generated.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_"
        f"{str(snapshot.get('snapshot_hash', ''))[:12]}"
    )
    if (
        not isinstance(manifest, dict)
        or set(manifest) != expected_manifest_fields
        or manifest.get("schema") != PREVIEW_MANIFEST_SCHEMA
        or manifest.get("preview_id") != preview_id
        or manifest.get("snapshot_hash") != snapshot.get("snapshot_hash")
        or manifest.get("snapshot_file") != "snapshot.json"
        or manifest.get("generated_at") != generated_at
        or manifest.get("publication_status") != "pending-review"
        or expected_preview_id != preview_id
        or not isinstance(publication, dict)
        or publication.get("status") != "pending-review"
        or publication.get("approved_snapshot_hash") != ""
        or publication.get("published_at") != ""
    ):
        raise DashboardSafetyError("dashboard preview manifest does not match the snapshot")
    return snapshot, manifest


def _review_snapshot_javascript(snapshot: dict[str, Any]) -> str:
    """Serialize one validated snapshot for safe inline JavaScript use."""

    encoded = _canonical_json(snapshot)
    return (
        encoded.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _private_review_assets(ws: Workspace, snapshot: dict[str, Any]) -> dict[str, str]:
    site_root_path = ws.root / "site"
    assets_root_path = site_root_path / "assets"
    _refuse_symlink(site_root_path, label="site root")
    _refuse_symlink(assets_root_path, label="site assets root")
    site_root = site_root_path.resolve()
    assets: dict[str, str] = {}
    for relative in REVIEW_STATIC_FILES:
        source = _contained(site_root, site_root / relative)
        _refuse_symlink(source, label="review source asset")
        if not source.is_file():
            raise DashboardSafetyError("dashboard review source assets are incomplete")
        try:
            assets[relative] = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise DashboardSafetyError("dashboard review source asset is unreadable") from exc

    for relative in ("index.html", "getting-started.html"):
        html = assets[relative]
        body_match = re.search(r"<body(?:\s[^>]*)?>", html)
        if "</head>" not in html or body_match is None:
            raise DashboardSafetyError("dashboard review source HTML is incompatible")
        html = html.replace(
            "</head>",
            '    <meta name="robots" content="noindex,nofollow,noarchive" />\n  </head>',
            1,
        )
        body_match = re.search(r"<body(?:\s[^>]*)?>", html)
        if body_match is None:
            raise DashboardSafetyError("dashboard review source HTML is incompatible")
        banner = (
            "\n"
            '    <aside class="private-review-banner" role="status">\n'
            "      PRIVATE REVIEW · NOT PUBLISHED · Exact aggregate preview only\n"
            "    </aside>"
        )
        html = html[: body_match.end()] + banner + html[body_match.end() :]
        assets[relative] = html
    assets["assets/styles.css"] += (
        "\n.private-review-banner {\n"
        "  position: sticky;\n"
        "  top: 0;\n"
        "  z-index: 200;\n"
        "  padding: 0.55rem 1rem;\n"
        "  color: #241705;\n"
        "  background: #ffcc75;\n"
        "  border-bottom: 1px solid rgba(36, 23, 5, 0.35);\n"
        "  font-size: 0.72rem;\n"
        "  font-weight: 850;\n"
        "  letter-spacing: 0.09em;\n"
        "  text-align: center;\n"
        "}\n"
    )
    assets["assets/app.js"] = (
        "globalThis.__RKF_PRIVATE_REVIEW_SNAPSHOT__ = "
        f"{_review_snapshot_javascript(snapshot)};\n"
        + assets["assets/app.js"]
    )
    assets[f"data/{PUBLIC_SNAPSHOT_FILENAME}"] = _json_text(snapshot)
    return assets


def _validate_review_bundle(
    review_root: Path,
    *,
    preview_id: str,
    snapshot_hash: str,
) -> dict[str, Any]:
    _refuse_symlink(review_root, label="review bundle")
    if not review_root.is_dir() or (
        os.name == "posix" and stat.S_IMODE(review_root.stat().st_mode) != 0o700
    ):
        raise DashboardSafetyError("dashboard review bundle permissions are invalid")
    expected_files = set(REVIEW_GENERATED_FILES)
    expected_directories = {"assets", "data"}
    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    for entry in review_root.rglob("*"):
        relative = entry.relative_to(review_root).as_posix()
        if entry.is_symlink():
            raise DashboardSafetyError("dashboard review bundle contains a symlink")
        if entry.is_dir():
            observed_directories.add(relative)
            if os.name == "posix" and stat.S_IMODE(entry.stat().st_mode) != 0o700:
                raise DashboardSafetyError("dashboard review directory permissions are invalid")
        elif entry.is_file():
            observed_files.add(relative)
            if os.name == "posix" and stat.S_IMODE(entry.stat().st_mode) != 0o600:
                raise DashboardSafetyError("dashboard review file permissions are invalid")
        else:
            raise DashboardSafetyError("dashboard review bundle contains a non-regular entry")
    if observed_files != expected_files or observed_directories != expected_directories:
        raise DashboardSafetyError("dashboard review bundle tree is not exact")
    manifest_path = _contained(review_root, review_root / "review-manifest.json")
    _refuse_symlink(manifest_path, label="review manifest")
    if not manifest_path.is_file():
        raise DashboardSafetyError("dashboard review bundle is incomplete")
    try:
        manifest = read_json(manifest_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DashboardSafetyError("dashboard review bundle is unreadable") from exc
    expected_fields = {
        "schema",
        "preview_id",
        "snapshot_hash",
        "publication_status",
        "entry_file",
        "self_contained",
        "asset_hashes",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != expected_fields
        or manifest.get("schema") != REVIEW_BUNDLE_SCHEMA
        or manifest.get("preview_id") != preview_id
        or manifest.get("snapshot_hash") != snapshot_hash
        or manifest.get("publication_status") != "pending-review"
        or manifest.get("entry_file") != REVIEW_ENTRY_FILE
        or manifest.get("self_contained") is not True
    ):
        raise DashboardSafetyError("dashboard review manifest does not match the preview")
    asset_hashes = manifest.get("asset_hashes")
    expected_assets = set(REVIEW_GENERATED_FILES) - {"review-manifest.json"}
    if not isinstance(asset_hashes, dict) or set(asset_hashes) != expected_assets:
        raise DashboardSafetyError("dashboard review asset manifest is invalid")
    for relative, expected_hash in asset_hashes.items():
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise DashboardSafetyError("dashboard review asset checksum is invalid")
        target = _contained(review_root, review_root / relative)
        _refuse_symlink(target, label="review asset")
        if not target.is_file() or sha256_file(target) != expected_hash:
            raise DashboardSafetyError("dashboard review asset checksum does not match")
    review_snapshot_path = _contained(
        review_root,
        review_root / "data" / PUBLIC_SNAPSHOT_FILENAME,
    )
    try:
        review_snapshot = read_json(review_snapshot_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DashboardSafetyError("dashboard review snapshot is unreadable") from exc
    validate_public_snapshot(review_snapshot)
    if review_snapshot["snapshot_hash"] != snapshot_hash:
        raise DashboardSafetyError("dashboard review snapshot does not match the preview")
    publication = review_snapshot.get("publication", {})
    if (
        publication.get("status") != "pending-review"
        or publication.get("approved_snapshot_hash") != ""
        or publication.get("published_at") != ""
    ):
        raise DashboardSafetyError("dashboard review snapshot is not pending review")
    return manifest


def render_dashboard_preview(ws: Workspace, *, preview_id: str) -> dict[str, Any]:
    """Create an ignored, self-contained visual bundle for exact-preview review."""

    snapshot, _ = load_dashboard_preview(ws, preview_id)
    preview_root = dashboard_preview_root(ws)
    preview_dir = _contained(preview_root, preview_root / preview_id)
    review_root = _contained(preview_dir, preview_dir / "review")
    _refuse_symlink(preview_dir, label="preview directory")
    _refuse_symlink(review_root, label="review bundle")
    if review_root.exists():
        _validate_review_bundle(
            review_root,
            preview_id=preview_id,
            snapshot_hash=str(snapshot["snapshot_hash"]),
        )
        return {
            "schema": REVIEW_BUNDLE_SCHEMA,
            "preview_id": preview_id,
            "snapshot_hash": snapshot["snapshot_hash"],
            "publication_status": "pending-review",
            "review_status": "already-rendered",
            "review_entry": f"review/{REVIEW_ENTRY_FILE}",
            "self_contained": True,
            "paths_redacted": True,
        }

    assets = _private_review_assets(ws, snapshot)
    build_root = _contained(
        preview_dir,
        preview_dir / f".review-build-{secrets.token_hex(6)}",
    )
    _refuse_symlink(build_root, label="review build directory")
    if build_root.exists():
        raise DashboardSafetyError("dashboard review build directory already exists")
    try:
        build_root.mkdir(mode=0o700)
        (build_root / "assets").mkdir(mode=0o700)
        (build_root / "data").mkdir(mode=0o700)
        if os.name == "posix":
            os.chmod(build_root, 0o700)
            os.chmod(build_root / "assets", 0o700)
            os.chmod(build_root / "data", 0o700)
    except OSError as exc:
        raise DashboardSafetyError("cannot initialize dashboard review build directory") from exc
    try:
        for relative, text in assets.items():
            target = _contained(build_root, build_root / relative)
            _refuse_symlink(target, label="review build asset")
            result = atomic_write_text(target, text, expected_checksum="")
            if not result.written:
                raise DashboardSafetyError(
                    f"cannot create dashboard review asset: {result.reason}"
                )
            if os.name == "posix":
                os.chmod(target, 0o600)
        asset_hashes = {
            relative: sha256_file(_contained(build_root, build_root / relative))
            for relative in sorted(assets)
        }
        review_manifest = {
            "schema": REVIEW_BUNDLE_SCHEMA,
            "preview_id": preview_id,
            "snapshot_hash": snapshot["snapshot_hash"],
            "publication_status": "pending-review",
            "entry_file": REVIEW_ENTRY_FILE,
            "self_contained": True,
            "asset_hashes": asset_hashes,
        }
        manifest_relative = "review-manifest.json"
        manifest_target = _contained(build_root, build_root / manifest_relative)
        manifest_result = atomic_write_text(
            manifest_target,
            _json_text(review_manifest),
            expected_checksum="",
        )
        if not manifest_result.written:
            raise DashboardSafetyError(
                f"cannot create dashboard review manifest: {manifest_result.reason}"
            )
        if os.name == "posix":
            os.chmod(manifest_target, 0o600)
        _validate_review_bundle(
            build_root,
            preview_id=preview_id,
            snapshot_hash=str(snapshot["snapshot_hash"]),
        )
        os.replace(build_root, review_root)
    except (DashboardSafetyError, OSError) as exc:
        if isinstance(exc, DashboardSafetyError):
            raise
        raise DashboardSafetyError("cannot finalize dashboard review bundle") from exc

    _validate_review_bundle(
        review_root,
        preview_id=preview_id,
        snapshot_hash=str(snapshot["snapshot_hash"]),
    )
    return {
        "schema": REVIEW_BUNDLE_SCHEMA,
        "preview_id": preview_id,
        "snapshot_hash": snapshot["snapshot_hash"],
        "publication_status": "pending-review",
        "review_status": "rendered",
        "review_entry": f"review/{REVIEW_ENTRY_FILE}",
        "self_contained": True,
        "paths_redacted": True,
    }


def publish_public_dashboard(
    ws: Workspace,
    *,
    preview_id: str,
    approved_snapshot_hash: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Publish the approved aggregate to the static site after exact-hash checks."""

    snapshot, _ = load_dashboard_preview(ws, preview_id)
    if not re.fullmatch(r"[0-9a-f]{64}", approved_snapshot_hash):
        raise DashboardSafetyError("approved snapshot hash is invalid")
    if snapshot["snapshot_hash"] != approved_snapshot_hash:
        raise DashboardSafetyError("approved snapshot hash does not match the preview")

    published = dict(snapshot)
    published["publication"] = {
        "status": "published",
        "approved_snapshot_hash": approved_snapshot_hash,
        "published_at": _iso_z(_utc_now(now)),
    }
    validate_public_snapshot(published)

    site_root_path = ws.root / "site"
    data_root_path = site_root_path / "data"
    _refuse_symlink(site_root_path, label="site root")
    _refuse_symlink(data_root_path, label="site data root")
    site_root = site_root_path.resolve()
    target = _contained(site_root, site_root / "data" / PUBLIC_SNAPSHOT_FILENAME)
    _refuse_symlink(target, label="public snapshot")
    expected_checksum = sha256_file(target) if target.exists() else ""
    result = atomic_write_text(target, _json_text(published), expected_checksum=expected_checksum)
    if not result.written:
        raise DashboardSafetyError(f"cannot publish dashboard snapshot: {result.reason}")
    return {
        "schema": PUBLIC_DASHBOARD_SCHEMA,
        "preview_id": preview_id,
        "snapshot_hash": approved_snapshot_hash,
        "publication_status": "published",
        "paths_redacted": True,
    }


def validate_site_publication(repo_root: Path) -> dict[str, Any]:
    """Fail closed unless the committed site snapshot is exactly approved."""

    root = repo_root.resolve()
    site_root = root / "site"
    data_root = site_root / "data"
    target = data_root / PUBLIC_SNAPSHOT_FILENAME
    _refuse_symlink(site_root, label="site root")
    _refuse_symlink(data_root, label="site data root")
    _refuse_symlink(target, label="public snapshot")
    if not target.is_file():
        raise DashboardSafetyError("published site snapshot is missing")
    try:
        payload = read_json(target)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DashboardSafetyError("published site snapshot is unreadable") from exc
    if payload.get("schema") == "rkf-public-demo-v1":
        if set(payload) != {"schema", "status", "generated_at", "metrics", "quality"}:
            raise DashboardSafetyError("public demo has unallowlisted top-level fields")
        if payload.get("status") != "published":
            raise DashboardSafetyError("public demo must be published")
        quality = payload.get("quality", {})
        if not isinstance(quality, dict) or quality.get("synthetic") is not True:
            raise DashboardSafetyError("public demo must be explicitly synthetic")
        for field in ("article_text_published", "paper_identity_published", "project_activity_published", "raw_prompts_published"):
            if quality.get(field) is not False:
                raise DashboardSafetyError(f"public demo safety flag failed: {field}")
        return {
            "schema": "rkf-demo-deployment-validation-v1",
            "publication_status": "published",
            "snapshot_hash": sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
            "paths_redacted": True,
        }
    validate_public_snapshot(payload)
    publication = payload["publication"]
    if publication["status"] != "published":
        raise DashboardSafetyError("site deployment requires publication.status=published")
    if publication["approved_snapshot_hash"] != payload["snapshot_hash"]:
        raise DashboardSafetyError("site deployment approval hash does not match the snapshot")
    return {
        "schema": "rkf-dashboard-deployment-validation-v1",
        "publication_status": "published",
        "snapshot_hash": payload["snapshot_hash"],
        "paths_redacted": True,
    }
