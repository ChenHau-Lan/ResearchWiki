#!/usr/bin/env python3
"""Database health diagnostics for Research Wiki.

This script reports issues only. It does not edit or delete files.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
DOI_DASHBOARD = RAW / "doi_dashboard.md"
PAPER_SOURCES = RAW / "paper_sources.md"
DOI_PDF_DIR = RAW / "doi_pdf"
FULL_TEXT_DIR = RAW / "full_text"
FULL_TEXT_INDEX_JSON = RAW / "full_text_index.json"
REVIEW_QUEUE = ROOT / "maintenance" / "review_queue.md"
FANOUT_CANDIDATES = ROOT / "maintenance" / "fanout_candidates.md"
RUNTIME_LOG = ROOT / "maintenance" / "log.md"
STATE_JSON = ROOT / "maintenance" / "state.json"
GRAPH_JSON = ROOT / "maintenance" / "graph.json"
COMPILER_NAV_PAGES = [
    WIKI / "purpose.md",
    WIKI / "overview.md",
    WIKI / "hot.md",
]
CORE_REQUIRED = [
    "core/principles.md",
    "core/data_contract.md",
    "core/agent_contract.md",
    "core/test_contract.md",
    "core/skills/literature-discovery/SKILL.md",
    "core/skills/source-intake/SKILL.md",
    "core/skills/paper-ingest/SKILL.md",
    "core/skills/topic-governance/SKILL.md",
    "core/skills/knowledge-workbench/SKILL.md",
    "core/skills/synthesis-research/SKILL.md",
    "core/skills/wiki-lint/SKILL.md",
    "core/skills/audit-release/SKILL.md",
    "core/skills/research-wiki-fulltext-acquisition/SKILL.md",
    "core/skills/research-wiki-academic-writer/SKILL.md",
    "docs/ARCHITECTURE.md",
    "docs/guides/research_wiki_pipeline_architecture.en.md",
    "docs/guides/research_wiki_pipeline_architecture.zh-TW.md",
    "docs/manuals/research_wiki_skill_first_quickstart.en.md",
    "docs/manuals/research_wiki_skill_first_quickstart.zh-TW.md",
    "skills/wiki-lint/SKILL.md",
    "MODE_REGISTRY.md",
    "researchwiki.config.example.toml",
    "tools/rw.py",
    "tools/public_safety_scan.py",
    "tools/render_markdown_pdf.py",
    "tools/render_skill_first_manual_assets.py",
]
OLD_BOARD_HEADER = "| DOI | Status | Title | Full Text | Wiki Page | Next Action | Updated | Note |"
LEGACY_BOARD_HEADER = "| Paper | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
LEGACY_DETAIL_BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
LEGACY_COMPACT_BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text |"
BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | PDF | Full Text |"
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
COPERNICUS_FILENAME_COPY_DOI_RE = re.compile(r"^(10\.5194/[a-z][a-z0-9]*-\d+-\d+-(?:19|20)\d{2})-\d+$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
VIRTUAL_LINK_PREFIXES = ("topic_", "subtopic_")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    result: dict[str, str] = {}
    for line in text[4:end].strip().splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def normalize_doi(value: str) -> str:
    value = value.strip().rstrip(".,;")
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    value = value.lower()
    copy_suffix = COPERNICUS_FILENAME_COPY_DOI_RE.fullmatch(value)
    return copy_suffix.group(1) if copy_suffix else value


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [part.strip().replace(r"\|", "|") for part in stripped.strip("|").split("|")]


def local_path_exists(value: str) -> bool:
    if not value or re.match(r"^[a-z]+://", value, flags=re.IGNORECASE):
        return False
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / value
    return path.exists()


def parse_dashboard() -> list[dict[str, str]]:
    if not DOI_DASHBOARD.exists():
        return []
    rows: list[dict[str, str]] = []
    in_board = ""
    for line in read(DOI_DASHBOARD).splitlines():
        if line.strip() == BOARD_HEADER:
            in_board = "new"
            continue
        if line.strip() in {LEGACY_BOARD_HEADER, LEGACY_DETAIL_BOARD_HEADER, LEGACY_COMPACT_BOARD_HEADER}:
            in_board = "legacy"
            continue
        if line.strip() == OLD_BOARD_HEADER:
            in_board = "old"
            continue
        if not in_board or line.strip().startswith("|---") or not line.startswith("|"):
            continue
        parts = split_row(line)
        if in_board == "new" and len(parts) == 6:
            rows.append(
                {
                    "doi": normalize_doi(parts[2]),
                    "status": parts[3],
                    "access_legality": "",
                    "pdf": "",
                    "full_text": "",
                    "wiki_page": "",
                    "next_action": "",
                    "updated": "",
                    "note": "",
                }
            )
        elif in_board == "legacy" and len(parts) in {7, 10}:
            rows.append(
                {
                    "doi": normalize_doi(parts[2]),
                    "status": parts[3],
                    "access_legality": parts[4],
                    "pdf": parts[5],
                    "full_text": parts[6],
                    "wiki_page": "",
                    "next_action": parts[7] if len(parts) == 10 else "",
                    "updated": parts[8] if len(parts) == 10 else "",
                    "note": parts[9] if len(parts) == 10 else "",
                }
            )
        elif in_board == "old" and len(parts) == 8:
            rows.append(
                {
                    "doi": normalize_doi(parts[0]),
                    "status": parts[1],
                    "title": parts[2],
                    "full_text": parts[3],
                    "wiki_page": parts[4],
                    "next_action": parts[5],
                    "updated": parts[6],
                    "note": parts[7],
                }
            )
    return rows


def wiki_pages() -> list[Path]:
    if not WIKI.exists():
        return []
    return sorted(path for path in WIKI.rglob("*.md") if ".obsidian" not in path.parts)


def link_target_exists(
    target: str,
    pages_by_stem: dict[str, Path],
    pages_by_repo_rel: set[str],
    pages_by_vault_rel: set[str],
) -> bool:
    if target.startswith(VIRTUAL_LINK_PREFIXES):
        return True
    normalized = target.strip("/")
    if normalized in pages_by_repo_rel or f"{normalized}.md" in pages_by_repo_rel:
        return True
    if normalized in pages_by_vault_rel or f"{normalized}.md" in pages_by_vault_rel:
        return True
    return normalized in pages_by_stem


def collect_issues() -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []

    for rel_path in CORE_REQUIRED:
        if not (ROOT / rel_path).exists():
            errors.append(f"Missing core contract file: {rel_path}")

    if not REVIEW_QUEUE.exists():
        warnings.append("Missing governance review queue: maintenance/review_queue.md")
    if not FANOUT_CANDIDATES.exists():
        warnings.append("Missing source fan-out candidate queue: maintenance/fanout_candidates.md")
    elif "## Candidates" not in read(FANOUT_CANDIDATES) or "## Candidate Details" not in read(FANOUT_CANDIDATES):
        warnings.append("Fan-out candidate queue missing required sections: maintenance/fanout_candidates.md")
    if not RUNTIME_LOG.exists():
        warnings.append("Missing runtime log: maintenance/log.md")
    if not STATE_JSON.exists():
        warnings.append("Missing runtime state export: maintenance/state.json")
    if not GRAPH_JSON.exists():
        warnings.append("Missing knowledge graph export: maintenance/graph.json")
    for page in COMPILER_NAV_PAGES:
        if not page.exists():
            warnings.append(f"Missing compiler navigation page: {rel(page)}")

    if not PAPER_SOURCES.exists():
        errors.append("Missing paper source intake file: raw/paper_sources.md")
    elif "## Add Sources Here" not in read(PAPER_SOURCES):
        errors.append("raw/paper_sources.md is missing the '## Add Sources Here' section")

    rows = parse_dashboard()
    seen: set[str] = set()
    for row in rows:
        doi = row["doi"]
        if not DOI_RE.fullmatch(doi):
            errors.append(f"Invalid DOI in dashboard: {doi}")
        if doi in seen:
            errors.append(f"Duplicate DOI in dashboard: {doi}")
        seen.add(doi)
        if row.get("pdf") and not local_path_exists(row["pdf"]):
            warnings.append(f"Stale PDF path for {doi}: {row['pdf']}")
        if row["full_text"] and not local_path_exists(row["full_text"]):
            warnings.append(f"Stale full text path for {doi}: {row['full_text']}")
        if row["wiki_page"] and not local_path_exists(row["wiki_page"]):
            warnings.append(f"Stale wiki page path for {doi}: {row['wiki_page']}")

    if FULL_TEXT_INDEX_JSON.exists():
        try:
            data = json.loads(read(FULL_TEXT_INDEX_JSON))
            for entry in data.get("entries", []):
                readable = str(entry.get("readable_md") or "")
                wiki_page = str(entry.get("wiki_page") or "")
                if readable and not local_path_exists(readable):
                    warnings.append(f"Index readable_md missing: {readable}")
                if wiki_page and not local_path_exists(wiki_page):
                    warnings.append(f"Index wiki_page missing: {wiki_page}")
        except json.JSONDecodeError:
            errors.append("raw/full_text_index.json is not valid JSON")
    else:
        errors.append("raw/full_text_index.json is missing")

    if STATE_JSON.exists():
        try:
            state = json.loads(read(STATE_JSON))
            tracked = state.get("tracked_files", {})
            for rel_path, details in tracked.items():
                path = ROOT / rel_path
                if path.exists() and details.get("sha256") and details.get("sha256") != file_digest(path):
                    warnings.append(f"Runtime state stale for tracked file: {rel_path}")
        except json.JSONDecodeError:
            errors.append("maintenance/state.json is not valid JSON")

    if GRAPH_JSON.exists():
        try:
            graph = json.loads(read(GRAPH_JSON))
            graph_nodes = {node.get("path") for node in graph.get("nodes", []) if isinstance(node, dict)}
            current_nodes = {rel(path) for path in wiki_pages()}
            missing_nodes = sorted(current_nodes - graph_nodes)
            if missing_nodes:
                warnings.append("Knowledge graph export stale; missing nodes: " + ", ".join(missing_nodes[:5]))
        except json.JSONDecodeError:
            errors.append("maintenance/graph.json is not valid JSON")

    pending_markers = {
        "machine_extracted_needs_codex_qc",
        "needs_codex_qc",
        "pending_codex_qc",
        "needs-human-review",
    }
    if FULL_TEXT_DIR.exists():
        for path in sorted(FULL_TEXT_DIR.glob("*.md")):
            text = read(path).lower()
            if any(marker in text for marker in pending_markers):
                warnings.append(
                    f"Pending QC text in raw/full_text: {rel(path)}; move/recreate it through raw/staging/extracted_text and Paper intake"
                )
            if "extraction_status: codex_qc_done" in text and "table_quality:" not in text:
                warnings.append(f"Missing table_quality in QCed full_text: {rel(path)}")

    if DOI_PDF_DIR.exists():
        pdfs = sorted(path for path in DOI_PDF_DIR.glob("*.pdf") if path.is_file() and not path.name.startswith("."))
        by_size: dict[int, list[Path]] = {}
        for path in pdfs:
            try:
                by_size.setdefault(path.stat().st_size, []).append(path)
            except OSError:
                warnings.append(f"Could not stat PDF while checking duplicates: {rel(path)}")
        by_digest: dict[str, list[Path]] = {}
        for same_size in by_size.values():
            if len(same_size) < 2:
                continue
            for path in same_size:
                try:
                    by_digest.setdefault(file_digest(path), []).append(path)
                except OSError:
                    warnings.append(f"Could not read PDF while checking duplicates: {rel(path)}")
        for duplicates in by_digest.values():
            if len(duplicates) > 1:
                warnings.append(
                    "Duplicate PDF content in raw/doi_pdf: "
                    + ", ".join(rel(path) for path in duplicates)
                    + "; keep the canonical DOI PDF and use ResearchWikiCodex option 2 for confirmed cleanup if desired"
                )

    pages = wiki_pages()
    pages_by_repo_rel = {rel(path) for path in pages}
    pages_by_vault_rel = {path.relative_to(WIKI).as_posix() for path in pages}
    pages_by_stem = {path.stem: path for path in pages}
    incoming: dict[str, int] = {rel(path): 0 for path in pages}
    review_queue_text = read(REVIEW_QUEUE) if REVIEW_QUEUE.exists() else ""
    for path in pages:
        text = read(path)
        page_rel = rel(path)
        meta = parse_frontmatter(text) or {}
        if "## Graph Links" not in text:
            warnings.append(f"Missing Graph Links section: {page_rel}")
        if meta.get("confidence") == "high" and "Counter-evidence" not in text and "counter-evidence" not in text:
            warnings.append(f"Semantic lint candidate: high-confidence page missing counter-evidence: {page_rel}")
        if meta.get("review_queue") == "true" and REVIEW_QUEUE.exists() and page_rel not in review_queue_text:
            warnings.append(f"Review queue flag without queue reference: {page_rel}")
        for target in WIKILINK_RE.findall(text):
            if not link_target_exists(target, pages_by_stem, pages_by_repo_rel, pages_by_vault_rel):
                warnings.append(f"Unresolved wikilink in {page_rel}: [[{target}]]")
            target_rel = target if target.endswith(".md") else f"{target}.md"
            if target_rel in incoming:
                incoming[target_rel] += 1
            elif f"wiki/{target_rel}" in incoming:
                incoming[f"wiki/{target_rel}"] += 1
            elif target in pages_by_stem:
                incoming[rel(pages_by_stem[target])] += 1

    for path in pages:
        page_rel = rel(path)
        if path.name in {"index.md", "maintenance.md", "concepts.md", "codex_app_handoff_prompt.md"} or path.name.startswith("repair_plan_"):
            continue
        if path.parent.name == "concepts" and incoming.get(page_rel, 0) == 0:
            warnings.append(f"Potential orphan concept page: {page_rel}")
            continue
        if incoming.get(page_rel, 0) == 0 and path.parent != WIKI:
            warnings.append(f"Potential orphan page: {page_rel}")

    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.name == ".DS_Store":
            warnings.append(f"Release hygiene: .DS_Store present at {rel(path)}")
        if path.is_file():
            if path in {ROOT / "tools" / "wiki_doctor.py", ROOT / "tools" / "public_safety_scan.py"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "/Users/" in text and path.suffix in {".md", ".json", ".py", ".bib"}:
                warnings.append(f"Release hygiene: local /Users path found in {rel(path)}")

    return errors, warnings


def main() -> int:
    errors, warnings = collect_issues()
    print("Research Wiki Doctor")
    print("====================")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    if errors:
        print("\nErrors")
        for issue in errors:
            print(f"- {issue}")
    if warnings:
        print("\nWarnings")
        for issue in warnings:
            print(f"- {issue}")
    if not errors and not warnings:
        print("\nNo issues found.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
