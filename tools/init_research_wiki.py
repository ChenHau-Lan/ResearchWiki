#!/usr/bin/env python3
"""Initialize or reset a local Research Wiki database.

This tool intentionally performs scoped batch deletion after an explicit
interactive confirmation. Topic setup is non-destructive and can be run by new
users after installing the template.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
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


def safe_input(label: str, default: str = "") -> str:
    try:
        return input(label).strip()
    except EOFError:
        print("")
        return default


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


def split_csv(value: str) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for raw in value.split(","):
        item = rw.slugify_key(raw.strip())
        if item and item not in seen:
            items.append(item)
            seen.add(item)
    return items


def topic_registry_text(topics: list[str], subtopics: list[str]) -> str:
    topic_rows = "\n".join(
        f"| `{topic}` | [[topic_{topic}]] | User-defined initial topic. |"
        for topic in topics
    )
    subtopic_rows = "\n".join(
        f"| `{subtopic}` | [[subtopic_{subtopic}]] | User-defined initial subtopic. |"
        for subtopic in subtopics
    )
    return f"""---
type: maintenance
status: draft
source_status: personal-note
reading_status: mixed
review_stage: discussed
topics: []
subtopics: []
keywords: [topics, subtopics, graph_hubs]
created: {TODAY}
updated: {TODAY}
sources: []
---

# Topic Registry

Use this minimal registry to keep research classification precise without creating too many folders.

## Rules

- `topics` are broad and stable research areas.
- `subtopics` are more precise retrieval categories.
- `keywords` are flexible details and do not automatically become graph nodes.
- Promote a subtopic only when it repeatedly connects papers, synthesis pages, seminars, or project synthesis pages.
- Use explicit wikilinks for promoted topic and subtopic hubs.

## Active Topics

| Topic | Graph Hub | Use When |
|---|---|---|
{topic_rows}

## Active Subtopics

| Subtopic | Graph Hub | Use When |
|---|---|---|
{subtopic_rows}

## Candidate Subtopics

| Candidate | Reason to Consider | Promote When |
|---|---|---|

## Graph Links

- Topics:
- Subtopics:
- Related literature: [[literature/literature]]
- Related synthesis: [[synthesis/synthesis]]
- Related seminars: [[seminars/seminars]]
- Related projects: [[project_synthesis/project_synthesis]]
"""


def configure_topic_registry() -> None:
    print("")
    print("Topic setup")
    print("-----------")
    print("Enter comma-separated values. Leave blank for an empty registry.")
    topics = split_csv(safe_input("Initial topics: "))
    subtopics = split_csv(safe_input("Initial subtopics: "))
    rw.TOPICS.write_text(topic_registry_text(topics, subtopics), encoding="utf-8")
    print(f"Updated {rw.repo_relative(rw.TOPICS)}.")
    print(f"Topics: {', '.join(topics) if topics else '<empty>'}")
    print(f"Subtopics: {', '.join(subtopics) if subtopics else '<empty>'}")


def sample_rows() -> list[dict[str, str]]:
    return [
        {
            "paper": "conrick_2021",
            "journal": "waf",
            "doi": "10.1175/waf-d-21-0044.1",
            "status": "new",
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
    rw.FULL_TEXT_INDEX_MD.write_text(
        f"""# full_text Index

Generated: {TODAY}

This file is generated by `tools/build_full_text_index.py`.
Use it as the dispatch table between DOI/citation keys, paper wiki pages, verified full text, and optional downstream artifacts.

## Summary

- `generated`: {TODAY}
- `primary_entries`: 0
- `all_text_sources`: 0
- `primary_readable_md`: 0
- `primary_source_or_clean_text_md`: 0
- `primary_with_wiki_page`: 0
- `primary_with_zh_full_md`: 0
- `fulltext_acquisition_needed`: 0
- `fulltext_qc_needed`: 0
- `wiki_ingest_needed`: 0
- `readable_markdown_upgrade_needed`: 0
- `ready_for_downstream_tasks`: 0

## Dispatch Rule

Resolve DOI/citation key/slug here first; use wiki_page for knowledge tasks, readable_md for full-text verification or optional translation, and source_pdf/source_path only when equation/table/layout checks are required.

## Entries

| Citation Key | DOI | Dispatch Status | Wiki Page | Full Text MD | Optional Translation MD |
|---|---|---|---|---|---|
""",
        encoding="utf-8",
    )
    rw.FULL_TEXT_INDEX_JSON.write_text(
        json.dumps(
            {
                "schema": "full-text-index-v2",
                "summary": {
                    "generated": TODAY,
                    "primary_entries": 0,
                    "all_text_sources": 0,
                    "primary_readable_md": 0,
                    "primary_source_or_clean_text_md": 0,
                    "primary_with_wiki_page": 0,
                    "primary_with_zh_full_md": 0,
                    "fulltext_acquisition_needed": 0,
                    "fulltext_qc_needed": 0,
                    "wiki_ingest_needed": 0,
                    "readable_markdown_upgrade_needed": 0,
                    "ready_for_downstream_tasks": 0,
                },
                "dispatch_rule": "Resolve DOI/citation key/slug here first; use wiki_page for knowledge tasks, readable_md for full-text verification or optional translation, and source_pdf/source_path only when equation/table/layout checks are required.",
                "entries": [],
                "all_text_sources": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def existing_yaml_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return ""


def frontmatter(page_type: str, keywords: str = "[]", *, target: Path | None = None) -> str:
    created = existing_yaml_value(target, "created") if target else ""
    updated = existing_yaml_value(target, "updated") if target else ""
    created = created or TODAY
    updated = updated or created
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
            f"created: {created}",
            f"updated: {updated}",
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
    wiki_index = WIKI_ROOT / "index.md"
    literature_index = rw.WIKI_LIT / "literature.md"
    synthesis_index = rw.WIKI_SYNTHESIS / "synthesis.md"
    meetings_index = rw.WIKI_MEETINGS / "meetings.md"
    project_index = rw.WIKI_PROJECT_SYNTHESIS / "project_synthesis.md"
    seminars_index = rw.WIKI_SEMINARS / "seminars.md"

    wiki_index.write_text(
        frontmatter("synthesis", "[index]", target=wiki_index)
        + "# Research Wiki Index\n\n"
        + "- [[literature/literature|Literature]]\n"
        + "- [[synthesis/synthesis|Synthesis]]\n"
        + "- [[meetings/meetings|Meetings]]\n"
        + "- [[project_synthesis/project_synthesis|Project Synthesis]]\n"
        + "- [[seminars/seminars|Seminars]]\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    literature_index.write_text(
        frontmatter("paper", "[literature_index]", target=literature_index)
        + "# Literature\n\n"
        + "Paper reading pages live in this folder.\n\n"
        + "New papers enter through `raw/paper_sources.md`. Processing progress is tracked in `raw/doi_dashboard.md`.\n\n"
        + "Use [[literature/topic_registry|Topic Registry]] for `topics`, `subtopics`, and graph hubs.\n\n"
        + "## Papers\n\n"
        + "- No paper pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    synthesis_index.write_text(
        frontmatter("synthesis", "[synthesis_index]", target=synthesis_index)
        + "# Synthesis\n\n"
        + "Cross-literature research judgment pages live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No synthesis pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    meetings_index.write_text(
        frontmatter("meeting", "[meeting_index]", target=meetings_index)
        + "# Meetings\n\n"
        + "Single-meeting records live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No meeting pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )
    project_index.write_text(
        frontmatter("project-synthesis", "[project_synthesis_index]", target=project_index)
        + "# Project Synthesis\n\n"
        + "Cross-meeting project evolution, decision history, and project links live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No project synthesis pages have been generated yet.\n\n"
        + graph_links(related_projects=False),
        encoding="utf-8",
    )
    seminars_index.write_text(
        frontmatter("seminar", "[seminar_index]", target=seminars_index)
        + "# Seminars\n\n"
        + "Seminar and talk records live in this folder.\n\n"
        + "## Pages\n\n"
        + "- No seminar pages have been generated yet.\n\n"
        + graph_links(),
        encoding="utf-8",
    )


def reset_database(*, already_confirmed: bool = False) -> int:
    print("")
    print("This will batch-delete local test evidence, generated raw artifacts, and generated wiki pages.")
    print("It will keep tools, templates, skills, docs, topic registry, and Obsidian settings.")
    print("It will reset section index pages so they do not point to deleted generated pages.")
    print("")
    if not already_confirmed:
        answer = safe_input(f'Type "{CONFIRM_TEXT}" to continue: ')
        if answer != CONFIRM_TEXT:
            print("Cancelled.")
            return 1

    include_sample = safe_input("Add the sample WAF DOI to the reset dashboard? [y/N]: ").lower() in {"y", "yes"}
    setup_topics = safe_input("Set up topic registry after reset? [y/N]: ").lower() in {"y", "yes"}

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
    subprocess.run([sys.executable, "tools/build_full_text_index.py"], cwd=rw.ROOT)
    if setup_topics:
        configure_topic_registry()

    print("")
    print("Initialized local Research Wiki database.")
    print(f"Deleted {len(deleted)} path(s).")
    if deleted:
        print("Deleted paths:")
        for path in deleted:
            print(f"- {path}")
    print("")
    print("Next test path:")
    print("1. Run ResearchWikiCodex.command to add/open paper sources.")
    print("2. Save legal PDFs into raw/doi_pdf/.")
    print("3. Run option 2 to refresh the dashboard and scan PDFs.")
    print("4. Run option 3 to create QCed raw/full_text.")
    print("5. Run option 4 to ingest QCed full_text to wiki.")
    return 0


def main() -> int:
    print("Research Wiki initializer and setup")
    print("===================================")
    print(f"Root: {rw.ROOT}")
    print("")
    print("1. Set up topic registry")
    print("2. Reset generated local database artifacts")
    print("0. Exit")
    print("")
    answer = safe_input(f'Choose an option, or type "{CONFIRM_TEXT}" for reset: ')
    if answer == CONFIRM_TEXT:
        return reset_database(already_confirmed=True)
    if answer in {"", "1"}:
        configure_topic_registry()
        return 0
    if answer == "2":
        return reset_database()
    if answer == "0":
        print("Cancelled.")
        return 0
    print("Unknown option.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
