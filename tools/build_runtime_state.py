#!/usr/bin/env python3
"""Build Research Wiki runtime state and graph exports.

The generated files live under maintenance/ and are operational indexes, not
formal wiki knowledge pages.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
MAINTENANCE = ROOT / "maintenance"
STATE_JSON = MAINTENANCE / "state.json"
GRAPH_JSON = MAINTENANCE / "graph.json"
FULL_TEXT_INDEX_JSON = RAW / "full_text_index.json"
TRACKED_STATE_FILES = [
    RAW / "paper_sources.md",
    RAW / "doi_dashboard.md",
    FULL_TEXT_INDEX_JSON,
    MAINTENANCE / "fanout_candidates.md",
    MAINTENANCE / "review_queue.md",
    MAINTENANCE / "log.md",
]
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].strip().splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def wiki_pages() -> list[Path]:
    if not WIKI.exists():
        return []
    return sorted(path for path in WIKI.rglob("*.md") if ".obsidian" not in path.parts)


def page_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return fallback


def graph_target(target: str, pages_by_stem: dict[str, str], pages_by_vault_rel: set[str]) -> str:
    normalized = target.strip("/")
    if normalized in pages_by_vault_rel:
        return f"wiki/{normalized}"
    if f"{normalized}.md" in pages_by_vault_rel:
        return f"wiki/{normalized}.md"
    if normalized in pages_by_stem:
        return pages_by_stem[normalized]
    if target.startswith(("topic_", "subtopic_")):
        return f"virtual/{target}"
    return f"unresolved/{target}"


def load_full_text_entries() -> list[dict[str, str]]:
    if not FULL_TEXT_INDEX_JSON.exists():
        return []
    try:
        data = json.loads(read(FULL_TEXT_INDEX_JSON))
    except json.JSONDecodeError:
        return []
    return list(data.get("entries", []))


def build_graph() -> dict[str, object]:
    pages = wiki_pages()
    pages_by_stem = {path.stem: f"wiki/{path.relative_to(WIKI).as_posix()}" for path in pages}
    pages_by_vault_rel = {path.relative_to(WIKI).as_posix() for path in pages}
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    for path in pages:
        text = read(path)
        meta = parse_frontmatter(text)
        node_id = f"wiki/{path.relative_to(WIKI).as_posix()}"
        nodes.append(
            {
                "id": node_id,
                "path": repo_relative(path),
                "title": page_title(text, path.stem),
                "type": meta.get("type", ""),
                "status": meta.get("status", ""),
                "confidence": meta.get("confidence", ""),
                "evidence_tier": meta.get("evidence_tier", ""),
                "claim_status": meta.get("claim_status", ""),
                "provenance_state": meta.get("provenance_state", ""),
                "review_queue": meta.get("review_queue", "false"),
                "topics": meta.get("topics", ""),
                "subtopics": meta.get("subtopics", ""),
            }
        )
        for target in WIKILINK_RE.findall(text):
            edges.append(
                {
                    "source": node_id,
                    "target": graph_target(target, pages_by_stem, pages_by_vault_rel),
                    "kind": "wikilink",
                    "label": target,
                }
            )
    return {
        "schema": "research-wiki-graph-v1",
        "generated": date.today().isoformat(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def build_state(graph: dict[str, object]) -> dict[str, object]:
    entries = load_full_text_entries()
    tracked = {
        repo_relative(path): {
            "exists": path.exists(),
            "sha256": file_hash(path),
        }
        for path in TRACKED_STATE_FILES
    }
    dispatch = []
    for entry in entries:
        dispatch.append(
            {
                "citation_key": entry.get("citation_key") or entry.get("slug") or "",
                "doi": entry.get("doi", ""),
                "readable_md": entry.get("readable_md", ""),
                "wiki_page": entry.get("wiki_page", ""),
                "dispatch_status": entry.get("dispatch_status", ""),
                "needs_review": entry.get("dispatch_status") not in {"ready_for_downstream_tasks", "wiki_done"},
            }
        )
    return {
        "schema": "research-wiki-state-v1",
        "generated": date.today().isoformat(),
        "tracked_files": tracked,
        "wiki_page_count": graph["node_count"],
        "graph_edge_count": graph["edge_count"],
        "full_text_dispatch": dispatch,
        "fanout_candidates": repo_relative(MAINTENANCE / "fanout_candidates.md"),
        "review_queue": repo_relative(MAINTENANCE / "review_queue.md"),
        "runtime_log": repo_relative(MAINTENANCE / "log.md"),
    }


def main() -> int:
    MAINTENANCE.mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    state = build_state(graph)
    GRAPH_JSON.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    STATE_JSON.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {repo_relative(STATE_JSON)}")
    print(f"Wrote {repo_relative(GRAPH_JSON)}")
    print(f"Wiki pages: {graph['node_count']}")
    print(f"Graph edges: {graph['edge_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
