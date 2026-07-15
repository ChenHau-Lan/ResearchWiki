"""Deterministic, maturity-aware retrieval over the central RKF workspace."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from .core import (
    PAPER_RELATION_TYPES,
    Workspace,
    extract_doi,
    first_heading,
    first_summary_line,
    parse_frontmatter,
    relative_workspace_path,
)
from .events import valid_event_envelope
from .lineage import ACTIVATION_ID_RE, PROJECT_ID_RE, input_fingerprint, utc_now
from .providers import RetrievalHit, RetrievalProvider


MATCH_PRIORITY = {
    "exact-source-id": 0,
    "exact-doi": 1,
    "exact-identifier": 2,
    "exact-page-id": 3,
    "exact-title": 4,
    "exact-alias": 5,
    "keyword": 6,
    "semantic": 7,
    "graph-context": 8,
}


@dataclass(frozen=True)
class SearchResultCard:
    id: str
    path: str
    type: str
    title: str
    source_id: str
    match_reason: str
    score: int
    reading_maturity: str
    evidence_boundary: str
    evidence_use: str
    claim_readiness: str
    missing: list[str]
    summary: str


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _path_is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _preflight_collection_root(ws: Workspace, root: Path, *, label: str) -> bool:
    """Validate one retrieval collection root without accepting symlink boundaries."""

    try:
        relative = root.relative_to(ws.paths.wiki_root)
    except ValueError as error:
        raise ValueError(f"retrieval {label} root escaped the configured wiki root") from error
    current = ws.paths.wiki_root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"retrieval {label} root cannot be a symlink")
    if not _path_is_within(ws.paths.wiki_root, root):
        raise ValueError(f"retrieval {label} root escaped the configured wiki root")
    if not root.exists():
        return False
    try:
        mode = root.lstat().st_mode
    except OSError as error:
        raise ValueError(f"retrieval {label} root cannot be inspected") from error
    if not stat.S_ISDIR(mode):
        raise ValueError(f"retrieval {label} root must be a directory")
    return True


def _safe_flat_files(
    ws: Workspace,
    root: Path,
    *,
    suffix: str,
    label: str,
) -> list[Path]:
    if not _preflight_collection_root(ws, root, label=label):
        return []
    paths: list[Path] = []
    try:
        entries = list(os.scandir(root))
    except OSError as error:
        raise ValueError(f"retrieval {label} root cannot be listed") from error
    for entry in entries:
        if not entry.name.endswith(suffix):
            continue
        try:
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                continue
        except OSError:
            continue
        path = Path(entry.path)
        if _path_is_within(root, path):
            paths.append(path)
    return sorted(paths)


def _safe_recursive_files(
    ws: Workspace,
    root: Path,
    *,
    suffix: str,
    label: str,
) -> list[Path]:
    if not _preflight_collection_root(ws, root, label=label):
        return []
    paths: list[Path] = []
    for current_name, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(current_name)
        safe_directories: list[str] = []
        for name in directory_names:
            candidate = current / name
            try:
                mode = candidate.lstat().st_mode
            except OSError:
                continue
            if (
                stat.S_ISDIR(mode)
                and not stat.S_ISLNK(mode)
                and _path_is_within(root, candidate)
            ):
                safe_directories.append(name)
        directory_names[:] = safe_directories
        for name in file_names:
            if not name.endswith(suffix):
                continue
            candidate = current / name
            try:
                mode = candidate.lstat().st_mode
            except OSError:
                continue
            if (
                stat.S_ISREG(mode)
                and not stat.S_ISLNK(mode)
                and _path_is_within(root, candidate)
            ):
                paths.append(candidate)
    return sorted(paths)


def _read_regular_text(path: Path, *, label: str) -> str:
    """Read one regular retrieval entry without following a target symlink."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if path.is_symlink():
            raise ValueError(f"retrieval {label} entry cannot be a symlink") from error
        raise
    descriptor_open = True
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError(f"retrieval {label} entry must be a regular file")
        with os.fdopen(descriptor, "r", encoding="utf-8", errors="replace") as handle:
            descriptor_open = False
            return handle.read()
    finally:
        if descriptor_open:
            os.close(descriptor)


def _read_regular_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(_read_regular_text(path, label=label))
    except json.JSONDecodeError as error:
        raise ValueError(f"retrieval {label} entry must contain valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"retrieval {label} entry must contain a JSON object")
    return payload


def _safe_knowledge_records(ws: Workspace) -> list[tuple[Path, dict[str, Any], str]]:
    records: list[tuple[Path, dict[str, Any], str]] = []
    for path in _safe_recursive_files(
        ws,
        ws.paths.knowledge,
        suffix=".md",
        label="knowledge",
    ):
        meta, body = parse_frontmatter(_read_regular_text(path, label="knowledge"))
        if meta:
            records.append((path, meta, body))
    return records


def _safe_json_records(
    ws: Workspace,
    root: Path,
    *,
    label: str,
) -> list[tuple[Path, dict[str, Any]]]:
    return [
        (path, _read_regular_json(path, label=label))
        for path in _safe_flat_files(ws, root, suffix=".json", label=label)
    ]


def _safe_operational_events(ws: Workspace) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in _safe_recursive_files(
        ws,
        ws.paths.events,
        suffix=".json",
        label="events",
    ):
        if not path.name.startswith("evt_"):
            continue
        try:
            event = _read_regular_json(path, label="events")
        except (OSError, ValueError, TypeError):
            continue
        if valid_event_envelope(event):
            events.append(event)
    return events


def _build_safe_research_graph(
    knowledge_records: list[tuple[Path, dict[str, Any], str]],
    source_records: list[tuple[Path, dict[str, Any]]],
    *,
    knowledge_root: Path,
) -> dict[str, Any]:
    """Build the retrieval graph only from entries already read with no-follow."""

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for _, record in source_records:
        source_id = str(record.get("source_id", ""))
        if not source_id:
            continue
        node = {"id": source_id, "type": "source", "status": record.get("status", "")}
        for key in ("reading_state", "fulltext_status"):
            if record.get(key):
                node[key] = record[key]
        nodes.append(node)
        for evidence_id in record.get("evidence_ids", []):
            edges.append({"from": source_id, "to": evidence_id, "type": "has-evidence"})
        for topic_id in record.get("topic_ids", []):
            edges.append({"from": source_id, "to": topic_id, "type": "tagged-with"})
    for path, meta, _ in knowledge_records:
        node_id = path.relative_to(knowledge_root).with_suffix("").as_posix()
        node = {
            "id": node_id,
            "type": meta.get("type", "knowledge"),
            "status": meta.get("status", ""),
        }
        for key in (
            "reading_state",
            "fulltext_status",
            "human_feedback_level",
            "claim_readiness",
            "synthesis_maturity",
            "source_coverage",
        ):
            if meta.get(key):
                node[key] = meta[key]
        nodes.append(node)
        for evidence_id in meta.get("evidence_ids", []):
            edges.append({"from": node_id, "to": evidence_id, "type": "supported-by"})
        if meta.get("source_id"):
            edges.append({"from": node_id, "to": meta["source_id"], "type": "derived-from"})
        for topic_id in meta.get("topics", []):
            edges.append({"from": node_id, "to": topic_id, "type": "tagged-with"})
        relations = meta.get("paper_relations", [])
        if isinstance(relations, list):
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                target = str(relation.get("paper_id", ""))
                relation_type = str(relation.get("relation", ""))
                if target and relation_type in PAPER_RELATION_TYPES:
                    edges.append({"from": node_id, "to": target, "type": relation_type})
    return {"schema": "rkf-graph-v1", "nodes": nodes, "edges": edges}


def _retrieval_run_path(ws: Workspace, retrieval_run_id: str) -> Path:
    """Return a contained run path only when root, parent, and target are safe."""

    root = ws.paths.state
    parent = root / "retrieval_runs"
    target = parent / f"{retrieval_run_id}.json"
    for label, path in (("root", root), ("parent", parent), ("target", target)):
        if path.is_symlink():
            raise ValueError(f"retrieval run {label} cannot be a symlink")
    if not _path_is_within(ws.paths.wiki_root, root):
        raise ValueError("retrieval run root escaped the configured wiki root")
    if root.exists() and not root.is_dir():
        raise ValueError("retrieval run root must be a directory")
    if parent.exists() and not parent.is_dir():
        raise ValueError("retrieval run parent must be a directory")
    if target.exists() and not target.is_file():
        raise ValueError("retrieval run target must be a regular file")
    root.mkdir(parents=True, exist_ok=True)
    parent.mkdir(mode=0o755, exist_ok=True)
    for label, path in (("root", root), ("parent", parent), ("target", target)):
        if path.is_symlink():
            raise ValueError(f"retrieval run {label} cannot be a symlink")
    return target


def _atomic_write_retrieval_run(path: Path, payload: dict[str, Any]) -> None:
    """Atomically publish one preflighted run without following its target."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    descriptor_open = True
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor_open = False
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            raise ValueError("retrieval run target cannot be a symlink")
        os.replace(temporary, path)
    finally:
        if descriptor_open:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _read_retrieval_run(path: Path) -> dict[str, Any]:
    return _read_regular_json(path, label="run")


def _assert_same_retrieval_run(
    existing: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    immutable_keys = (
        "schema",
        "retrieval_run_id",
        "project_id",
        "activation_id",
        "query_fingerprint",
        "result_fingerprint",
        "provider",
        "provider_version",
        "index_generation",
        "index_scope",
        "result_object_ids",
        "result_scores",
        "paths_redacted",
    )
    if any(existing.get(key) != expected.get(key) for key in immutable_keys):
        raise ValueError("existing retrieval run does not match its deterministic identity")


def _missing(meta: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not meta.get("evidence_ids"):
        missing.append("locator")
    if str(meta.get("fulltext_status", "")) in {
        "",
        "unknown",
        "needs-user-pdf",
        "partial-only",
    }:
        missing.append("full-text")
    if str(meta.get("human_feedback_level", "none")) == "none":
        missing.append("human-feedback")
    return missing


def _evidence_use(page_type: str, boundary: str) -> str:
    if page_type in {"inbox", "candidate"} or boundary in {
        "inbox-only",
        "ars-proposal",
        "review-blocker",
    }:
        return "proposal-only"
    if page_type == "paper":
        return "source-context"
    return "maintained-knowledge"


def _match(
    query: str,
    query_doi: str,
    candidate_id: str,
    title: str,
    source_id: str,
    doi: str,
    identifiers: list[str],
    aliases: list[str],
    text: str,
) -> tuple[str, int] | None:
    normalized_query = _normalize(query)
    if query == source_id:
        return "exact-source-id", 1000
    if query_doi and query_doi == doi:
        return "exact-doi", 950
    if normalized_query and any(
        normalized_query == _normalize(value) for value in identifiers if value
    ):
        return "exact-identifier", 925
    if query == candidate_id:
        return "exact-page-id", 900
    if normalized_query and normalized_query == _normalize(title):
        return "exact-title", 850
    if normalized_query and any(
        normalized_query == _normalize(value) for value in aliases if value
    ):
        return "exact-alias", 825
    normalized_candidate = _normalize(f"{title} {text}")
    if normalized_query and normalized_query in normalized_candidate:
        return "keyword", 200 + len(normalized_query)
    query_words = set(normalized_query.split())
    candidate_words = set(normalized_candidate.split())
    overlap = len(query_words & candidate_words)
    if overlap:
        return "keyword", 100 + overlap
    return None


def search_central_rkf(
    ws: Workspace,
    query: str,
    *,
    limit: int = 10,
    page_types: list[str] | None = None,
    reading_states: list[str] | None = None,
    evidence_boundaries: list[str] | None = None,
    retrieval_provider: RetrievalProvider | None = None,
    project_id: str = "",
    activation_id: str = "",
    index_scope: str = "public-safe",
    persist_retrieval_run: bool = True,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise SystemExit("query.search requires a non-empty query")
    allowed_types = set(page_types or [])
    allowed_reading = set(reading_states or [])
    allowed_boundaries = set(evidence_boundaries or [])
    query_doi = extract_doi(query)
    cards: list[SearchResultCard] = []
    canonical_objects: dict[tuple[str, str], SearchResultCard] = {}
    if index_scope not in {"public-safe", "private-fulltext"}:
        raise SystemExit("index_scope must be public-safe or private-fulltext")
    if not isinstance(persist_retrieval_run, bool):
        raise SystemExit("persist_retrieval_run must be a boolean")

    knowledge_records = _safe_knowledge_records(ws)
    source_records = _safe_json_records(ws, ws.paths.sources, label="source")

    for path, meta, body in knowledge_records:
        page_type = str(meta.get("type", "knowledge"))
        if allowed_types and page_type not in allowed_types:
            continue
        reading_maturity = str(
            meta.get("reading_state", meta.get("reading_status", "unknown"))
        )
        evidence_boundary = str(meta.get("evidence_boundary", "unknown"))
        if allowed_reading and reading_maturity not in allowed_reading:
            continue
        if allowed_boundaries and evidence_boundary not in allowed_boundaries:
            continue
        page_id = path.relative_to(ws.paths.knowledge).with_suffix("").as_posix()
        title = first_heading(body, page_id)
        source_id = str(meta.get("source_id", ""))
        sources = _string_list(meta.get("sources", []))
        doi = extract_doi(" ".join([str(meta.get("doi", "")), *sources]))
        identifiers = [source_id, str(meta.get("doi", "")), *sources]
        aliases = _string_list(meta.get("aliases", []))
        topics = _string_list(meta.get("topics", []))
        search_text = f"{body} {' '.join(topics)}"
        canonical = SearchResultCard(
            id=page_id,
            path=relative_workspace_path(ws, path),
            type=page_type,
            title=title,
            source_id=source_id,
            match_reason="semantic",
            score=0,
            reading_maturity=reading_maturity,
            evidence_boundary=evidence_boundary,
            evidence_use=_evidence_use(page_type, evidence_boundary),
            claim_readiness=str(meta.get("claim_readiness", "unknown")),
            missing=_missing(meta),
            summary=first_summary_line(body),
        )
        canonical_objects[(page_type, page_id)] = canonical
        matched = _match(
            query,
            query_doi,
            page_id,
            title,
            source_id,
            doi,
            identifiers,
            aliases,
            search_text,
        )
        if matched is None:
            continue
        reason, score = matched
        cards.append(replace(canonical, match_reason=reason, score=score))

    for path, record in source_records:
        if allowed_types and "source" not in allowed_types:
            continue
        source_id = str(record.get("source_id", path.stem))
        title = str(record.get("title", source_id))
        doi = str(record.get("normalized_doi", ""))
        reading_maturity = str(record.get("reading_state", "metadata-only"))
        if allowed_reading and reading_maturity not in allowed_reading:
            continue
        if allowed_boundaries and "source-record" not in allowed_boundaries:
            continue
        canonical = SearchResultCard(
            id=source_id,
            path=relative_workspace_path(ws, path),
            type="source",
            title=title,
            source_id=source_id,
            match_reason="semantic",
            score=0,
            reading_maturity=reading_maturity,
            evidence_boundary="source-record",
            evidence_use="identity-only",
            claim_readiness="not-ready",
            missing=(
                ["paper-page"]
                if not any(
                    card.source_id == source_id and card.type == "paper"
                    for card in canonical_objects.values()
                )
                else []
            ),
            summary="",
        )
        canonical_objects[("source", source_id)] = canonical
        matched = _match(
            query,
            query_doi,
            source_id,
            title,
            source_id,
            doi,
            [str(record.get("value", "")), doi],
            _string_list(record.get("aliases", [])),
            str(record.get("notes", "")),
        )
        if matched is None:
            continue
        reason, score = matched
        cards.append(replace(canonical, match_reason=reason, score=score))

    if not allowed_types or "event" in allowed_types:
        for event in _safe_operational_events(ws):
            if allowed_reading and "captured" not in allowed_reading:
                continue
            if allowed_boundaries and "event-only" not in allowed_boundaries:
                continue
            payload = event.get("payload", {})
            title = str(payload.get("title", event.get("event_id", "capture event")))
            text = " ".join(
                str(payload.get(key, ""))
                for key in ("text", "doi", "source_url", "intent", "reasons")
            )
            matched = _match(
                query,
                query_doi,
                str(event.get("event_id", "")),
                title,
                str(payload.get("matched_id", "")),
                str(payload.get("doi", "")),
                [str(payload.get("doi", "")), str(payload.get("source_url", ""))],
                [],
                text,
            )
            if matched is None:
                continue
            reason, score = matched
            event_path = (
                ws.paths.events
                / str(event["created"])[:10]
                / f"{event['event_id']}.json"
            )
            cards.append(
                SearchResultCard(
                    id=str(event["event_id"]),
                    path=relative_workspace_path(ws, event_path),
                    type="event",
                    title=title,
                    source_id=str(payload.get("matched_id", "")),
                    match_reason=reason,
                    score=score,
                    reading_maturity="captured",
                    evidence_boundary="event-only",
                    evidence_use="proposal-only",
                    claim_readiness="not-ready",
                    missing=["classification-review"],
                    summary=str(payload.get("text", ""))[:180],
                )
            )

    # Keep this import local so research review code can use retrieval helpers
    # without creating a module import cycle.
    from .research import (
        load_canonical_claim,
        load_canonical_evidence,
        load_canonical_synthesis,
    )

    canonical_groups = (
        (
            "evidence",
            ws.paths.evidence_index / "cards",
            "evidence-pointer",
            load_canonical_evidence,
        ),
        (
            "claim",
            ws.paths.state / "claims",
            "canonical-claim",
            load_canonical_claim,
        ),
        (
            "synthesis",
            ws.paths.state / "syntheses",
            "canonical-synthesis",
            load_canonical_synthesis,
        ),
    )
    for object_type, root, boundary, loader in canonical_groups:
        if allowed_types and object_type not in allowed_types:
            continue
        for path in _safe_flat_files(
            ws,
            root,
            suffix=".json",
            label=object_type,
        ):
            try:
                record = loader(ws, path.stem)
            except (OSError, UnicodeDecodeError, ValueError):
                continue
            object_id = str(
                record.get(
                    f"{object_type}_id",
                    record.get("evidence_id", path.stem),
                )
            )
            if object_type == "evidence":
                title = str(record.get("summary", object_id))
                locator = record.get("locator", {})
                locator_text = (
                    f"{locator.get('kind', '')}:{locator.get('value', '')}"
                    if isinstance(locator, dict)
                    else ""
                )
                text = f"{record.get('paper_id', '')} {title} {locator_text}"
                source_id = str(record.get("paper_id", ""))
                evidence_use = "locator-backed"
                missing = [] if locator_text else ["locator"]
                claim_readiness = str(record.get("verification_state", "unreviewed"))
            elif object_type == "claim":
                title = str(record.get("statement", object_id))
                evidence_ids = [
                    *record.get("supporting_evidence_ids", []),
                    *record.get("opposing_evidence_ids", []),
                    *record.get("context_evidence_ids", []),
                ]
                text = f"{title} {' '.join(str(item) for item in evidence_ids)}"
                source_id = ""
                evidence_use = "claim-with-evidence" if evidence_ids else "proposal-only"
                missing = [] if evidence_ids else ["locator"]
                claim_readiness = str(record.get("status", "proposed"))
            else:
                title = str(record.get("research_question", object_id))
                text = f"{title} {record.get('provisional_conclusion', '')}"
                source_id = ""
                evidence_matrix = record.get("evidence_matrix", [])
                has_locator_backed_evidence = (
                    isinstance(evidence_matrix, list) and bool(evidence_matrix)
                )
                evidence_use = (
                    "cross-paper-synthesis"
                    if has_locator_backed_evidence
                    else "proposal-only"
                )
                missing = [] if has_locator_backed_evidence else ["locator"]
                if record.get("evidence_gaps"):
                    missing.append("evidence-gap")
                claim_readiness = "provisional"
            canonical = SearchResultCard(
                id=object_id,
                path=relative_workspace_path(ws, path),
                type=object_type,
                title=title,
                source_id=source_id,
                match_reason="semantic",
                score=0,
                reading_maturity="canonical",
                evidence_boundary=boundary,
                evidence_use=evidence_use,
                claim_readiness=claim_readiness,
                missing=missing,
                summary=title[:180],
            )
            canonical_objects[(object_type, object_id)] = canonical
            matched = _match(
                query,
                query_doi,
                object_id,
                title,
                source_id,
                "",
                [object_id],
                [],
                text,
            )
            if matched is None:
                continue
            reason, score = matched
            cards.append(replace(canonical, match_reason=reason, score=score))

    unique: dict[tuple[str, str], SearchResultCard] = {}
    for card in cards:
        key = (card.type, card.id)
        previous = unique.get(key)
        if previous is None or card.score > previous.score:
            unique[key] = card
    graph = _build_safe_research_graph(
        knowledge_records,
        source_records,
        knowledge_root=ws.paths.knowledge,
    )
    primary_ids = {card.id for card in unique.values()}
    nodes = {
        str(node.get("id", "")): node
        for node in graph.get("nodes", [])
        if str(node.get("id", ""))
    }
    adjacent_ids: set[str] = set()
    for edge in graph.get("edges", []):
        from_id = str(edge.get("from", ""))
        to_id = str(edge.get("to", ""))
        if from_id in primary_ids and to_id:
            adjacent_ids.add(to_id)
        if to_id in primary_ids and from_id:
            adjacent_ids.add(from_id)
        if to_id and to_id not in nodes:
            nodes[to_id] = {
                "id": to_id,
                "type": (
                    "topic"
                    if edge.get("type") == "tagged-with"
                    else "evidence"
                    if edge.get("type") in {"has-evidence", "supported-by"}
                    else "implicit"
                ),
                "status": "implicit",
            }
    for node_id in sorted(adjacent_ids - primary_ids):
        node = nodes.get(node_id, {"id": node_id, "type": "implicit"})
        node_type = str(node.get("type", "implicit"))
        if allowed_types and node_type not in allowed_types:
            continue
        if node_type == "source":
            path = f"state/sources/{node_id}.json"
            boundary = "source-record"
            evidence_use = "identity-only"
        elif node_type == "topic":
            path = f"governance/topic_registry.json#{node_id}"
            boundary = "governed-topic"
            evidence_use = "maintained-knowledge"
        elif node_type == "evidence":
            path = f"state/evidence/{node_id}.json"
            boundary = "evidence-pointer"
            evidence_use = "locator-only"
        else:
            path = f"knowledge/{node_id}.md"
            boundary = "graph-linked"
            evidence_use = "maintained-knowledge"
        reading = str(node.get("reading_state", "unknown"))
        if allowed_reading and reading not in allowed_reading:
            continue
        if allowed_boundaries and boundary not in allowed_boundaries:
            continue
        card = SearchResultCard(
            id=node_id,
            path=path,
            type=node_type,
            title=node_id.replace("-", " ").replace("/", " / "),
            source_id=node_id if node_type == "source" else "",
            match_reason="graph-context",
            score=50,
            reading_maturity=reading,
            evidence_boundary=boundary,
            evidence_use=evidence_use,
            claim_readiness=str(node.get("claim_readiness", "unknown")),
            missing=[],
            summary="Graph neighbor of a deterministic RKF match.",
        )
        unique[(card.type, card.id)] = card

    semantic_provider_name = "none"
    semantic_provider_version = ""
    semantic_index_generation = "none"
    semantic_elapsed_ms = 0
    if retrieval_provider is not None:
        if not PROJECT_ID_RE.fullmatch(project_id) or not ACTIVATION_ID_RE.fullmatch(
            activation_id
        ):
            raise SystemExit("optional retrieval requires project/activation lineage")
        semantic_provider_name = str(getattr(retrieval_provider, "name", "semantic"))
        semantic_provider_version = str(getattr(retrieval_provider, "version", "unknown"))
        try:
            hits = retrieval_provider.search(
                query=query,
                limit=limit,
                project_id=project_id,
                activation_id=activation_id,
                index_scope=index_scope,
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            hits = []
            semantic_provider_name = f"{semantic_provider_name}:fallback"
        semantic_index_generation = str(getattr(retrieval_provider, "index_generation", "unknown"))
        semantic_elapsed_ms = max(0, int(getattr(retrieval_provider, "elapsed_ms", 0)))
        for hit in hits:
            if not isinstance(hit, RetrievalHit):
                semantic_provider_name = f"{semantic_provider_name}:fallback"
                continue
            hit_scope = str(hit.metadata.get("index_scope", ""))
            if index_scope == "public-safe" and hit_scope != "public-safe":
                continue
            if index_scope == "private-fulltext" and hit_scope not in {
                "public-safe",
                "private-fulltext",
            }:
                continue
            if not hit.locator.strip():
                continue
            key = (str(hit.metadata.get("object_type", "")), hit.object_id)
            if key in unique:
                continue
            canonical = canonical_objects.get(key)
            if canonical is None:
                continue
            card = replace(
                canonical,
                match_reason="semantic",
                score=max(0, min(49, int(hit.score * 49))),
            )
            unique[key] = card

    ordered = sorted(
        unique.values(),
        key=lambda card: (
            MATCH_PRIORITY[card.match_reason],
            -card.score,
            card.path,
        ),
    )[:limit]
    matched_ids = {card.id for card in ordered}
    graph_edges = [
        edge
        for edge in graph.get("edges", [])
        if edge.get("from") in matched_ids or edge.get("to") in matched_ids
    ]
    card_payloads = [asdict(card) for card in ordered]
    answer_boundary = (
        "locator-backed"
        if any(
            card.evidence_use
            in {"locator-backed", "claim-with-evidence", "cross-paper-synthesis"}
            and "locator" not in card.missing
            for card in ordered
        )
        else "insufficient-evidence"
    )
    result_payload = {
        "query": query,
        "cards": card_payloads,
        "count": len(ordered),
        "graph_context": graph_edges,
        "answer_boundary": answer_boundary,
        "provider": semantic_provider_name,
        "provider_version": semantic_provider_version,
        "index_generation": semantic_index_generation,
        "next_step": "inspect-project-local-if-central-context-is-incomplete",
        "retrieval_persisted": False,
        "affected_object_ids": [card.id for card in ordered],
    }
    result_identity = input_fingerprint(
        {
            "cards": card_payloads,
            "graph_context": graph_edges,
            "answer_boundary": answer_boundary,
            "provider": semantic_provider_name,
            "provider_version": semantic_provider_version,
            "index_generation": semantic_index_generation,
            "index_scope": index_scope,
        }
    )
    result_payload["retrieval_result_fingerprint"] = result_identity
    if (
        persist_retrieval_run
        and PROJECT_ID_RE.fullmatch(project_id)
        and ACTIVATION_ID_RE.fullmatch(activation_id)
    ):
        fingerprint = input_fingerprint(
            {
                "query": query,
                "limit": limit,
                "page_types": page_types or [],
                "reading_states": reading_states or [],
                "evidence_boundaries": evidence_boundaries or [],
                "index_scope": index_scope,
            }
        )
        retrieval_run_id = "rrun_" + hashlib.sha256(
            f"{activation_id}\0{fingerprint}\0{result_identity}".encode("utf-8")
        ).hexdigest()[:24]
        run_payload = {
            "schema": "rkf-retrieval-run-v1",
            "retrieval_run_id": retrieval_run_id,
            "project_id": project_id,
            "activation_id": activation_id,
            "query_fingerprint": fingerprint,
            "result_fingerprint": result_identity,
            "provider": semantic_provider_name,
            "provider_version": semantic_provider_version,
            "index_generation": semantic_index_generation,
            "elapsed_ms": semantic_elapsed_ms,
            "index_scope": index_scope,
            "result_object_ids": [card.id for card in ordered],
            "result_scores": [card.score for card in ordered],
            "created": utc_now(),
            "paths_redacted": True,
        }
        run_path = _retrieval_run_path(ws, retrieval_run_id)
        if run_path.exists():
            _assert_same_retrieval_run(_read_retrieval_run(run_path), run_payload)
        else:
            _atomic_write_retrieval_run(run_path, run_payload)
        result_payload["retrieval_run_id"] = retrieval_run_id
        result_payload["retrieval_persisted"] = True
        result_payload["affected_object_ids"] = [
            retrieval_run_id,
            *result_payload["affected_object_ids"],
        ]
    return result_payload
