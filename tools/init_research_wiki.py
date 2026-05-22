#!/usr/bin/env python3
"""Initialize a Research Wiki test database.

This tool intentionally performs scoped batch deletion after an explicit
interactive confirmation. It is for local testing only.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path

import research_wiki_shortcut as rw


CONFIRM_TEXT = "INIT TEST DATABASE"
TODAY = date.today().isoformat()
RAW_ROOT = rw.ROOT / "raw"
WIKI_ROOT = rw.ROOT / "wiki"
CANONICAL_RAW_ROOT_NAMES = {
    ".gitkeep",
    "doi_dashboard.md",
    "doi_list.md",
    "doi_pdf",
    "files",
    "full_text",
    "full_text_index.json",
    "full_text_index.md",
    "paper_sources.md",
    "staging",
}
CANONICAL_WIKI_ROOT_NAMES = {
    ".obsidian",
    "index.md",
    "literature",
    "meetings",
    "project_synthesis",
    "seminars",
    "synthesis",
}


def assert_inside_root(path: Path) -> None:
    path.resolve().relative_to(rw.ROOT.resolve())


def clear_dir(path: Path, *, keep_names: set[str] | None = None) -> list[str]:
    keep_names = keep_names or {".gitkeep"}
    assert_inside_root(path)
    path.mkdir(parents=True, exist_ok=True)
    deleted: list[str] = []
    for child in sorted(path.iterdir()):
        if child.name in keep_names:
            continue
        assert_inside_root(child)
        deleted.append(rw.repo_relative(child))
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    (path / ".gitkeep").touch()
    return deleted


def clear_unmanaged_children(path: Path, *, keep_names: set[str]) -> list[str]:
    """Delete non-canonical files/dirs directly under a managed root."""
    assert_inside_root(path)
    path.mkdir(parents=True, exist_ok=True)
    deleted: list[str] = []
    for child in sorted(path.iterdir()):
        if child.name in keep_names:
            continue
        assert_inside_root(child)
        deleted.append(rw.repo_relative(child))
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return deleted


def dashboard_text(rows: list[dict[str, str]]) -> str:
    return f"""# DOI Dashboard

This board tracks where each resolved DOI is in the paper-source ingest process.

## DOI Status Board

{rw.render_board(rows)}

## Status Legend

- `new`: newly added, not processed yet.
- `metadata_ok`: title/authors/year/venue/DOI checked.
- `full_text_needed`: metadata exists, readable full text is missing.
- `full_text_done`: QCed `raw/full_text/<paper_file_key>.md` exists.
- `wiki_done`: `wiki/literature/<slug>.md` exists.
- `abstract_only`: only abstract was available; the paper page must say so.
- `blocked`: DOI/source/access problem needs human decision.
"""


def sample_rows() -> list[dict[str, str]]:
    return [
        {
            "paper": "conrick_2021",
            "journal": "waf",
            "doi": "10.1175/waf-d-21-0044.1",
            "status": "new",
            "access_legality": "unknown",
            "pdf": "",
            "full_text": "",
            "next_action": "open_authorized_source_page",
            "updated": TODAY,
            "note": "sample DOI for testing the source-first workflow",
        }
    ]


def reset_core_files(include_sample: bool) -> None:
    rw.DOI_LIST.write_text(rw.default_doi_list(), encoding="utf-8")
    rw.PAPER_SOURCES.write_text(rw.default_paper_sources(), encoding="utf-8")
    rw.DOI_DASHBOARD.write_text(dashboard_text(sample_rows() if include_sample else []), encoding="utf-8")
    rw.FULL_TEXT_INDEX_MD.write_text("# Full Text Index\n\nNo full text files indexed yet.\n", encoding="utf-8")
    rw.FULL_TEXT_INDEX_JSON.write_text(
        '{\n  "generated": "' + TODAY + '",\n  "primary_entries": 0,\n  "all_text_sources": 0,\n  "entries": []\n}\n',
        encoding="utf-8",
    )


def frontmatter(page_type: str, keywords: str = "[]") -> str:
    return "\n".join(
        [
            "---",
            f"type: {page_type}",
            "status: draft",
            "source_status: personal-note",
            "reading_status: mixed",
            "review_stage: discussed",
            "topics: []",
            "subtopics: []",
            f"keywords: {keywords}",
            f"created: {TODAY}",
            f"updated: {TODAY}",
            "sources: []",
            "---",
            "",
        ]
    )


def graph_links(*, related_projects: bool = True) -> str:
    project_link = "[[project_synthesis/project_synthesis]]" if related_projects else ""
    project_line = f"- Related projects: {project_link}" if project_link else "- Related projects:"
    return "\n".join(
        [
            "## Graph Links",
            "",
            "- Topics:",
            "- Subtopics:",
            "- Related literature:",
            "- Related synthesis:",
            "- Related seminars:",
            project_line,
            "",
        ]
    )


def reset_wiki_index_files() -> None:
    (WIKI_ROOT / "index.md").write_text(
        frontmatter("synthesis", "[index]")
        + "# Research Wiki Index\n\n"
        + "- [[literature/literature|Literature]]\n"
        + "- [[synthesis/synthesis|Synthesis]]\n"
        + "- [[meetings/meetings|Meetings]]\n"
        + "- [[project_synthesis/project_synthesis|Project Synthesis]]\n"
        + "- [[seminars/seminars|Seminars]]\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    (rw.WIKI_LIT / "literature.md").write_text(
        frontmatter("paper", "[literature_index]")
        + "# Literature\n\n"
        + "Paper reading pages live in this folder.\n\n"
        + "New papers enter through `raw/paper_sources.md`. Processing progress is tracked in `raw/doi_dashboard.md`.\n\n"
        + "Use [[literature/topic_registry|Topic Registry]] for `topics`, `subtopics`, and graph hubs.\n\n"
        + "## Papers\n\n"
        + "- No paper pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    (rw.WIKI_SYNTHESIS / "synthesis.md").write_text(
        frontmatter("synthesis", "[synthesis_index]")
        + "# Synthesis\n\n"
        + "Cross-literature research judgment pages live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No synthesis pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    (rw.WIKI_MEETINGS / "meetings.md").write_text(
        frontmatter("meeting", "[meeting_index]")
        + "# Meetings\n\n"
        + "Single-meeting records live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No meeting pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    (rw.WIKI_PROJECT_SYNTHESIS / "project_synthesis.md").write_text(
        frontmatter("project-synthesis", "[project_synthesis_index]")
        + "# Project Synthesis\n\n"
        + "Cross-meeting project evolution, decision history, and project links live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No project synthesis pages have been generated yet.\n\n"
        + graph_links(related_projects=False),
        encoding="utf-8",
    )
    (rw.WIKI_SEMINARS / "seminars.md").write_text(
        frontmatter("seminar", "[seminar_index]")
        + "# Seminars\n\n"
        + "Seminar and talk records live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No seminar pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )


def main() -> int:
    print("Research Wiki test database initializer")
    print("=======================================")
    print("")
    print("This will batch-delete local test evidence, generated raw artifacts, and generated wiki pages.")
    print("It will keep tools, templates, skills, docs, topic registry, and Obsidian settings.")
    print("It will reset section index pages so they do not point to deleted generated pages.")
    print("")
    answer = input(f'Type "{CONFIRM_TEXT}" to continue: ').strip()
    if answer != CONFIRM_TEXT:
        print("Cancelled.")
        return 1

    include_sample = input("Add the sample WAF DOI to the reset dashboard? [y/N]: ").strip().lower() in {"y", "yes"}

    rw.ensure_core_files()
    deleted: list[str] = []
    deleted.extend(clear_unmanaged_children(RAW_ROOT, keep_names=CANONICAL_RAW_ROOT_NAMES))
    deleted.extend(clear_unmanaged_children(WIKI_ROOT, keep_names=CANONICAL_WIKI_ROOT_NAMES))
    deleted.extend(clear_dir(rw.DOI_PDF_DIR))
    deleted.extend(clear_dir(rw.FULL_TEXT_DIR))
    deleted.extend(clear_dir(rw.RAW_FILES_DIR))
    deleted.extend(clear_dir(rw.STAGING_TEXT_DIR))
    deleted.extend(clear_dir(rw.WIKI_LIT, keep_names={".gitkeep", "literature.md", "topic_registry.md"}))
    deleted.extend(clear_dir(rw.WIKI_SYNTHESIS, keep_names={".gitkeep", "synthesis.md"}))
    deleted.extend(clear_dir(rw.WIKI_MEETINGS, keep_names={".gitkeep", "meetings.md"}))
    deleted.extend(clear_dir(rw.WIKI_PROJECT_SYNTHESIS, keep_names={".gitkeep", "project_synthesis.md"}))
    deleted.extend(clear_dir(rw.WIKI_SEMINARS, keep_names={".gitkeep", "seminars.md"}))

    reset_core_files(include_sample)
    reset_wiki_index_files()
    subprocess.run(["python3", "tools/build_full_text_index.py"], cwd=rw.ROOT)

    print("")
    print("Initialized test database.")
    print(f"Deleted {len(deleted)} path(s).")
    if deleted:
        print("Deleted paths:")
        for path in deleted:
            print(f"- {path}")
    print("")
    print("Next test path:")
    print("1. Run ResearchWiki.command Paper intake to open authorized source pages.")
    print("2. Save legal PDFs into raw/doi_pdf/.")
    print("3. Run Paper intake again to import evidence and create QCed raw/full_text.")
    print("4. Run Ingest QCed full_text to wiki.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
