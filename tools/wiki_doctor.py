#!/usr/bin/env python3
"""Database health diagnostics for Research Wiki.

This script reports issues only. It does not edit or delete files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
DOI_DASHBOARD = RAW / "doi_dashboard.md"
FULL_TEXT_INDEX_JSON = RAW / "full_text_index.json"
CORE_REQUIRED = [
    "core/principles.md",
    "core/data_contract.md",
    "core/agent_contract.md",
    "core/test_contract.md",
    "core/skills/research-wiki-fulltext-acquisition/SKILL.md",
    "core/skills/research-wiki-academic-writer/SKILL.md",
]
OLD_BOARD_HEADER = "| DOI | Status | Title | Full Text | Wiki Page | Next Action | Updated | Note |"
LEGACY_BOARD_HEADER = "| Paper | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
LEGACY_DETAIL_BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text |"
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
VIRTUAL_LINK_PREFIXES = ("topic_", "subtopic_")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def normalize_doi(value: str) -> str:
    value = value.strip().rstrip(".,;")
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.lower()


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
        if line.strip() in {BOARD_HEADER, LEGACY_BOARD_HEADER, LEGACY_DETAIL_BOARD_HEADER}:
            in_board = "new"
            continue
        if line.strip() == OLD_BOARD_HEADER:
            in_board = "old"
            continue
        if not in_board or line.strip().startswith("|---") or not line.startswith("|"):
            continue
        parts = split_row(line)
        if in_board == "new" and len(parts) in {7, 10}:
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

    pages = wiki_pages()
    pages_by_repo_rel = {rel(path) for path in pages}
    pages_by_vault_rel = {path.relative_to(WIKI).as_posix() for path in pages}
    pages_by_stem = {path.stem: path for path in pages}
    incoming: dict[str, int] = {rel(path): 0 for path in pages}
    for path in pages:
        text = read(path)
        page_rel = rel(path)
        if "## Graph Links" not in text:
            warnings.append(f"Missing Graph Links section: {page_rel}")
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
        if path.name in {"index.md", "maintenance.md", "codex_app_handoff_prompt.md"} or path.name.startswith("repair_plan_"):
            continue
        if incoming.get(page_rel, 0) == 0 and path.parent != WIKI:
            warnings.append(f"Potential orphan page: {page_rel}")

    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.name == ".DS_Store":
            warnings.append(f"Release hygiene: .DS_Store present at {rel(path)}")
        if path.is_file():
            if path == ROOT / "tools" / "wiki_doctor.py":
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
