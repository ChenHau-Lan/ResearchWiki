"""Deterministic, maturity-aware retrieval over the central RKF workspace."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from .core import (
    Workspace,
    build_research_graph,
    extract_doi,
    first_heading,
    first_summary_line,
    knowledge_page_records,
    read_json,
    relative_workspace_path,
)
from .events import load_operational_events


MATCH_PRIORITY = {
    "exact-source-id": 0,
    "exact-doi": 1,
    "exact-identifier": 2,
    "exact-page-id": 3,
    "exact-title": 4,
    "exact-alias": 5,
    "keyword": 6,
    "graph-context": 7,
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
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise SystemExit("query.search requires a non-empty query")
    allowed_types = set(page_types or [])
    allowed_reading = set(reading_states or [])
    allowed_boundaries = set(evidence_boundaries or [])
    query_doi = extract_doi(query)
    cards: list[SearchResultCard] = []

    for path, meta, body in knowledge_page_records(ws):
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
        cards.append(
            SearchResultCard(
                id=page_id,
                path=relative_workspace_path(ws, path),
                type=page_type,
                title=title,
                source_id=source_id,
                match_reason=reason,
                score=score,
                reading_maturity=reading_maturity,
                evidence_boundary=evidence_boundary,
                evidence_use=_evidence_use(page_type, evidence_boundary),
                claim_readiness=str(meta.get("claim_readiness", "unknown")),
                missing=_missing(meta),
                summary=first_summary_line(body),
            )
        )

    source_paths = sorted(ws.paths.sources.glob("*.json")) if ws.paths.sources.exists() else []
    for path in source_paths:
        if allowed_types and "source" not in allowed_types:
            continue
        record = read_json(path)
        source_id = str(record.get("source_id", path.stem))
        title = str(record.get("title", source_id))
        doi = str(record.get("normalized_doi", ""))
        reading_maturity = str(record.get("reading_state", "metadata-only"))
        if allowed_reading and reading_maturity not in allowed_reading:
            continue
        if allowed_boundaries and "source-record" not in allowed_boundaries:
            continue
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
        cards.append(
            SearchResultCard(
                id=source_id,
                path=relative_workspace_path(ws, path),
                type="source",
                title=title,
                source_id=source_id,
                match_reason=reason,
                score=score,
                reading_maturity=reading_maturity,
                evidence_boundary="source-record",
                evidence_use="identity-only",
                claim_readiness="not-ready",
                missing=(
                    ["paper-page"]
                    if not any(
                        card.source_id == source_id and card.type == "paper"
                        for card in cards
                    )
                    else []
                ),
                summary="",
            )
        )

    if not allowed_types or "event" in allowed_types:
        for event in load_operational_events(ws):
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

    unique: dict[tuple[str, str], SearchResultCard] = {}
    for card in cards:
        key = (card.type, card.id)
        previous = unique.get(key)
        if previous is None or card.score > previous.score:
            unique[key] = card
    graph = build_research_graph(ws)
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
    return {
        "query": query,
        "cards": [asdict(card) for card in ordered],
        "count": len(ordered),
        "graph_context": graph_edges,
        "next_step": "inspect-project-local-if-central-context-is-incomplete",
    }
