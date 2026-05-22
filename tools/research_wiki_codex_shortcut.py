#!/usr/bin/env python3
"""Codex-first canonical command helper for Research Wiki.

This helper is the primary command entrypoint. It performs local bookkeeping
when possible and asks Codex to make judgment-heavy decisions. It never creates
new persistent staging full text.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import research_wiki_shortcut as base


SYNTHESIS_PROMPT = base.MAINTENANCE_DIR / "codex_first_synthesis_prompt.md"
FEEDBACK_PROMPT = base.MAINTENANCE_DIR / "codex_first_feedback_issue_prompt.md"
EXTERNAL_SANDBOX_PROMPT = base.MAINTENANCE_DIR / "external_sandbox_sync_prompt.md"


def print_header() -> None:
    print("\nResearchWiki Codex-first")
    print("=" * 24)
    print(f"Root: {base.ROOT}\n")


def pause() -> None:
    input("\nPress Enter to continue...")


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{label}{suffix}: ").strip()
    except EOFError:
        return default
    return value or default


def open_or_add_sources() -> None:
    base.ensure_core_files()
    value = prompt("Paste DOI / DOI URL / article URL / PDF URL, or press Enter to open raw/paper_sources.md")
    if not value:
        base.open_path(base.PAPER_SOURCES)
        return
    added = base.queue_source_pointers(value)
    if added:
        print(f"Added {added} source pointer(s) to raw/paper_sources.md.")
    else:
        print("No new source pointers were added.")
    rows = base.sync_doi_board()
    print(f"Dashboard refreshed: {len(rows)} row(s).")


def refresh_dashboard_scan_pdfs(*, quiet: bool = False) -> list[dict[str, str]]:
    base.ensure_core_files()
    rows = base.sync_doi_board()
    messages, warnings = base.import_new_doi_pdfs(rows)
    base.write_dashboard_rows(rows)
    index_output = base.build_full_text_index_quiet()
    rows = base.sync_doi_board()
    if not quiet:
        print("\n== Codex-first Dashboard Refresh ==")
        for message in messages:
            print(f"- {message}")
        for warning in warnings:
            print(f"- Warning: {warning}")
        print("\nNo persistent staging full text was created by this command.")
        if index_output.strip():
            print("\nIndex rebuild:")
            print(index_output.strip())
        deleted = review_delete_duplicate_pdfs(rows, show_empty=False)
        if deleted:
            rows = base.sync_doi_board()
        base.print_dashboard_summary(rows)
        base.open_path(base.DOI_DASHBOARD)
    return rows


def pdf_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duplicate_pdf_groups(rows: list[dict[str, str]]) -> list[tuple[Path, list[Path]]]:
    canonical_paths = {
        (base.ROOT / row["pdf"]).resolve()
        for row in rows
        if row.get("pdf") and base.local_path_exists(row["pdf"])
    }
    by_size: dict[int, list[Path]] = {}
    for path in base.iter_doi_pdf_files():
        try:
            by_size.setdefault(path.stat().st_size, []).append(path)
        except OSError:
            continue
    by_digest: dict[str, list[Path]] = {}
    for same_size in by_size.values():
        if len(same_size) < 2:
            continue
        for path in same_size:
            try:
                by_digest.setdefault(pdf_digest(path), []).append(path)
            except OSError:
                continue

    groups: list[tuple[Path, list[Path]]] = []
    for paths in by_digest.values():
        if len(paths) < 2:
            continue
        ranked = sorted(paths, key=lambda path: duplicate_keep_score(path, canonical_paths), reverse=True)
        groups.append((ranked[0], ranked[1:]))
    groups.sort(key=lambda group: base.repo_relative(group[0]))
    return groups


def duplicate_keep_score(path: Path, canonical_paths: set[Path]) -> tuple[int, int, str]:
    score = 0
    if path.resolve() in canonical_paths:
        score += 100
    if "_" in path.stem:
        score += 20
    if re.search(r"-\d+$", path.stem):
        score -= 5
    return score, -len(path.name), path.name


def review_delete_duplicate_pdfs(rows: list[dict[str, str]] | None = None, *, show_empty: bool = True) -> int:
    base.ensure_core_files()
    if rows is None:
        rows = base.sync_doi_board()
    groups = duplicate_pdf_groups(rows)
    if not groups:
        if show_empty:
            print("\n== Duplicate PDF Review ==")
            print("No byte-identical duplicate PDFs found in raw/doi_pdf/.")
        return 0

    print("\n== Duplicate PDF Review ==")
    print("Only byte-identical PDFs are listed. Canonical files are kept.")
    to_delete: list[Path] = []
    for group_index, (keep, duplicates) in enumerate(groups, start=1):
        print(f"\nGroup {group_index}")
        print(f"- Keep: {base.repo_relative(keep)}")
        for duplicate in duplicates:
            rel_path = base.repo_relative(duplicate)
            to_delete.append(duplicate)
            print(f"- Delete candidate: {rel_path}")

    all_phrase = "DELETE ALL DUPLICATE PDFS"
    print("\nTo delete all listed duplicate candidates together, type:")
    print(all_phrase)
    print("To delete one file at a time instead, press Enter and follow the per-file prompts.")
    value = prompt("Confirmation")
    deleted = 0
    if value == all_phrase:
        for duplicate in to_delete:
            rel_path = base.repo_relative(duplicate)
            try:
                duplicate.unlink()
            except OSError as exc:
                print(f"Could not delete {rel_path}: {exc}")
                continue
            deleted += 1
            print(f"Deleted {rel_path}.")
    else:
        for duplicate in to_delete:
            rel_path = base.repo_relative(duplicate)
            phrase = f"DELETE {rel_path}"
            value = prompt(f"Delete duplicate {rel_path}? Type `{phrase}` to confirm")
            if value != phrase:
                print(f"Skipped {rel_path}.")
                continue
            try:
                duplicate.unlink()
            except OSError as exc:
                print(f"Could not delete {rel_path}: {exc}")
                continue
            deleted += 1
            print(f"Deleted {rel_path}.")
    if deleted:
        rows = base.sync_doi_board()
        base.write_dashboard_rows(rows)
        base.build_full_text_index_quiet()
    print(f"\nDuplicate PDF cleanup finished. Deleted files: {deleted}.")
    return deleted


def existing_staging_for_row(row: dict[str, str]) -> str:
    staging = base.staging_path_for_row(row)
    return base.repo_relative(staging) if staging else ""


def rows_needing_qced_full_text(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    active: list[dict[str, str]] = []
    for row in rows:
        if not row.get("doi"):
            continue
        if row.get("full_text") and base.full_text_is_qced(row.get("full_text", "")):
            continue
        if row.get("status") == "wiki_done" and row.get("full_text"):
            continue
        if row.get("pdf") and base.local_path_exists(row["pdf"]):
            active.append(row)
            continue
        if existing_staging_for_row(row):
            active.append(row)
            continue
        if row.get("status") in {"new", "metadata_ok", "full_text_needed", "abstract_only", "blocked"}:
            active.append(row)
    return active


def rows_ready_for_codex_qc(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ready: list[dict[str, str]] = []
    for row in rows_needing_qced_full_text(rows):
        if row.get("pdf") and base.local_path_exists(row["pdf"]):
            ready.append(row)
        elif existing_staging_for_row(row):
            ready.append(row)
    return ready


def rows_missing_full_text_route(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for row in rows_needing_qced_full_text(rows):
        if row.get("pdf") and base.local_path_exists(row["pdf"]):
            continue
        if existing_staging_for_row(row):
            continue
        if row.get("status") in {"new", "metadata_ok", "full_text_needed", "abstract_only", "blocked"}:
            missing.append(row)
    return missing


def choose_limit(default: int = 3) -> int:
    value = prompt("Max DOI rows to handle now", str(default))
    try:
        return max(1, int(value))
    except ValueError:
        return default


def open_download_pages(rows: list[dict[str, str]], *, max_to_open: int) -> None:
    unresolved = base.unresolved_source_lines()
    source_urls = [url for line in unresolved for url in base.extract_urls(line)]
    print("\n== Download / Full-Text Pages ==")
    print("Open the article/full-text/PDF page, download authorized PDFs to raw/doi_pdf/, then return here.")
    for index, row in enumerate(rows[:max_to_open], start=1):
        print(f"- DOI {index}: {row['doi']} | title: {row.get('title') or 'unknown'}")
    if os.environ.get("RESEARCHWIKI_NO_OPEN") == "1":
        print("Open skipped because RESEARCHWIKI_NO_OPEN=1.")
        return
    opened = 0
    for url in source_urls[:max_to_open]:
        base.open_location(url)
        opened += 1
    for row in rows[: max(0, max_to_open - opened)]:
        doi_url = f"https://doi.org/{quote(row['doi'], safe='/')}"
        base.open_location(doi_url)
        opened += 1
    base.open_path(base.DOI_PDF_DIR)
    print(f"Opened {opened} source/DOI page(s) and raw/doi_pdf/.")


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base.ROOT / path


def render_direct_qced_full_text(row: dict[str, str], pdf_path: Path, text: str, extractor: str) -> str:
    title = row.get("title") or base.pdf_title_hint(text) or pdf_path.stem.replace("_", " ").title()
    journal = row.get("journal") or base.infer_pdf_journal(row, text)
    year = base.infer_pdf_year(row, text)
    source_pdf = base.repo_relative(pdf_path)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", text).strip()
    return "\n".join(
        [
            "---",
            f"doi: {base.yaml_string(row.get('doi', ''))}",
            f"title: {base.yaml_string(title)}",
            "authors: []",
            f"journal: {base.yaml_string(journal)}",
            f"journal_abbrev: {base.yaml_string(journal)}",
            f"year: {base.yaml_string(year)}",
            "source_type: authorized_pdf_codex_first_qc",
            f"source_pdf: {source_pdf}",
            "extraction_status: codex_qc_done",
            "readability_status: readable-with-warnings",
            "equation_quality: partial",
            "table_quality: not_applicable",
            "qc_status: codex_qc_done",
            "language: en",
            f"created: {base.TODAY}",
            f"updated: {base.TODAY}",
            "---",
            "",
            f"# {title}",
            "",
            "## Source Metadata",
            "",
            f"- DOI: {row.get('doi', '')}",
            f"- Journal / venue: {journal or 'unknown'}",
            f"- Year: {year or 'unknown'}",
            f"- Source PDF: {source_pdf}",
            f"- Extraction tool: {extractor}",
            "",
            "## QC Notes",
            "",
            "- This file was created by the Codex-first command's deterministic QC stub.",
            "- Real command runs should use Codex to verify metadata, reflow text, and check equations/tables before writing raw/full_text.",
            "- No persistent staging full text was created.",
            "",
            "## Full Text",
            "",
            cleaned,
            "",
        ]
    )


def test_stub_create_qced_full_text(rows: list[dict[str, str]]) -> tuple[list[str], list[str], bool]:
    messages: list[str] = []
    warnings: list[str] = []
    mutated = False
    for row in rows_needing_qced_full_text(rows):
        pdf_ref = row.get("pdf", "")
        if not pdf_ref or not base.local_path_exists(pdf_ref):
            row["status"] = "full_text_needed"
            row["next_action"] = "codex_first_qc_needs_authorized_source"
            row["updated"] = base.TODAY
            row["note"] = "Codex-first QC needs an authorized PDF or readable source; no staging full text was created."
            mutated = True
            warnings.append(f"No local PDF/source ready for {row['doi']}.")
            continue
        pdf_path = resolve_repo_path(pdf_ref)
        text, extractor = base.pdf_text_extract(pdf_path)
        if not text or len(text.strip()) < 1000:
            row["status"] = "full_text_needed"
            row["full_text"] = ""
            row["next_action"] = "codex_first_qc_needs_authorized_source"
            row["updated"] = base.TODAY
            row["note"] = f"Could not create QCed full_text directly from {base.repo_relative(pdf_path)}; no staging full text was created."
            mutated = True
            warnings.append(row["note"])
            continue
        paper, journal, title, paper_file_key = base.infer_pdf_key(row, pdf_path, text)
        row["paper"] = row.get("paper") or paper
        row["journal"] = row.get("journal") or journal
        row["title"] = row.get("title") or title
        target = base.FULL_TEXT_DIR / f"{paper_file_key}.md"
        target.write_text(render_direct_qced_full_text(row, pdf_path, text, extractor), encoding="utf-8")
        row["full_text"] = base.repo_relative(target)
        row["status"] = "full_text_done" if row.get("status") != "wiki_done" else row["status"]
        row["next_action"] = "ingest_full_text_to_wiki"
        row["access_legality"] = row.get("access_legality") or "verified_source"
        row["updated"] = base.TODAY
        row["note"] = f"created QCed full_text directly from {base.repo_relative(pdf_path)}; no staging full text was created"
        mutated = True
        messages.append(f"Created QCed full_text {base.repo_relative(target)} for {row['doi']}.")
    if not messages and not warnings:
        messages.append("No rows needed Codex-first full_text QC.")
    return messages, warnings, mutated


def build_codex_first_qc_prompt(rows: list[dict[str, str]]) -> str:
    row_lines = []
    for row in rows:
        row_lines.append(
            "\n".join(
                [
                    f"- DOI: {row['doi']}",
                    f"  Title: {row.get('title') or 'unknown'}",
                    f"  Paper: {row.get('paper') or 'unknown'}",
                    f"  Journal: {row.get('journal') or 'unknown'}",
                    f"  PDF: {row.get('pdf') or 'missing'}",
                    f"  Existing staging if any: {existing_staging_for_row(row) or 'none'}",
                    f"  Current status: {row.get('status') or 'unknown'}",
                    f"  Next action: {row.get('next_action') or 'unknown'}",
                ]
            )
        )
    target_lines = "\n".join(row_lines)
    return f"""You are working inside this Research Wiki project.

First read and follow the command-independent core contract:
- core/principles.md
- core/data_contract.md
- core/agent_contract.md
- core/skills/research-wiki-fulltext-acquisition/SKILL.md

Goal:
Create QCed readable full_text Markdown for the target DOI rows. This is the canonical Codex-first command path optimized for speed: prefer complete web full text, use PDF only when needed, and avoid long route chasing.

Target DOI rows:
{target_lines}

Rules:
0. Core contract is authoritative. If these instructions conflict with core/*, follow core/* and report the mismatch.
1. Prefer complete online article text first: legal publisher HTML/XML, open-access full text, authorized browser DOM, or user-provided source text. If complete web text is available, write QCed raw/full_text from it immediately; PDF backfill is optional and must not block wiki ingest.
2. If complete online text is unavailable and no local PDF is listed, use only a quick DOI/publisher page check and record the visible PDF route for the user. Do not spend a long session searching.
3. Do not create new files under raw/staging/extracted_text/. This command must not persist un-QCed full text.
4. You may read existing staging files if they already exist, but do not rely on them without checking against PDF/source metadata.
5. Write raw/full_text/<paper_file_key>.md only after reflow/QC is complete.
6. Final full_text frontmatter must use extraction_status: codex_qc_done and qc_status: codex_qc_done.
7. Include table_quality: good, partial, poor, or not_applicable in final full_text frontmatter.
8. During reflow/QC, fix PDF extraction line-break damage, dehyphenate words split across lines, remove page headers/footers and isolated equation/furniture fragments, and verify section headings, paragraph order, figure captions, table captions, references, and appendices.
9. Table handling is part of QC: preserve each caption as `### Table N. <caption>`; use Markdown tables only when columns are clear; keep wide/continued/numeric tables in fenced text blocks with `Table status`, `Source pages` if known, and a warning that numeric reuse requires PDF/supplement checking; never let table rows or one-word column fragments spill into prose.
10. If no complete full text or PDF can be obtained quickly but a reliable abstract is available, write an abstract-only Markdown file to raw/full_text/<paper_file_key>.md with extraction_status: abstract_only, readability_status: abstract-only, qc_status: abstract_only, table_quality: not_applicable, and a clear note that complete full text is still needed. Update raw/doi_dashboard.md Status = abstract_only and Next Action = authorized_source_or_pdf_needed.
11. If neither complete text, PDF, nor abstract is available, do not write raw/full_text. Update raw/doi_dashboard.md with Status = full_text_needed, Full Text empty, Next Action = codex_first_qc_needs_authorized_source or codex_convert_to_full_text, and a concise blocker.
12. Use only legal publisher, author, open-access, institutional, or user-provided access. Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
13. Do not create or update wiki/literature pages. Wiki ingest is a separate command option.
14. Run python3 tools/build_full_text_index.py after writing or changing final full_text.

Console output protocol:
- Emit concise progress lines only with these exact prefixes:
  - RW_STATUS|<doi>|<paper title>
  - RW_ATTEMPT|<doi>|codex_first_qc|<source_path_or_url>
  - RW_RESULT|<doi>|success|<reason>
  - RW_RESULT|<doi>|failed|<reason>
  - RW_FILE|<doi>|<pdf_path_or_none>|<full_text_path_or_none>
  - RW_DASHBOARD|<doi>|<wiki_status>|<next_action>
- Do not emit example protocol lines themselves. Never emit angle-bracket placeholders as real progress.
"""


def create_qced_full_text_with_codex() -> None:
    rows = refresh_dashboard_scan_pdfs(quiet=True)
    limit = choose_limit()
    ready = rows_ready_for_codex_qc(rows)
    active = ready[:limit]
    if not active:
        missing = rows_missing_full_text_route(rows)
        if missing:
            open_download_pages(missing, max_to_open=limit)
            prompt("After saving authorized PDFs into raw/doi_pdf/, press Enter to continue")
            rows = refresh_dashboard_scan_pdfs(quiet=True)
            ready = rows_ready_for_codex_qc(rows)
            active = ready[:limit]
        if not active and missing:
            active = missing[:limit]
    if not active:
        print("\nNo DOI rows need QCed full_text.")
        return

    print("\n== Codex-first QCed Full Text ==")
    print(f"Target rows: {len(active)}")
    for row in active:
        print(f"- {row['doi']} | pdf: {row.get('pdf') or 'missing'} | status: {row.get('status') or 'unknown'}")
    if not ready:
        print("No local PDF was found after the download check; Codex will only try quick web full-text / abstract fallback.")

    if os.environ.get("RESEARCHWIKI_TEST_CODEX_FIRST_QC_FAIL") == "1":
        for row in active:
            row["status"] = "full_text_needed"
            row["full_text"] = ""
            row["next_action"] = "codex_first_qc_needs_authorized_source"
            row["updated"] = base.TODAY
            row["note"] = "test-mode Codex-first QC failure; no full_text or staging full text was created"
        base.write_dashboard_rows(rows)
        base.build_full_text_index_quiet()
        print("Test-mode QC failure; no raw/full_text or staging full text was created.")
        return

    if os.environ.get("RESEARCHWIKI_TEST_CODEX_FIRST_QC_STUB") == "1":
        messages, warnings, mutated = test_stub_create_qced_full_text(active)
        if mutated:
            base.write_dashboard_rows(rows)
        base.build_full_text_index_quiet()
        rows = base.sync_doi_board()
        for message in messages:
            print(f"- {message}")
        for warning in warnings:
            print(f"- Warning: {warning}")
        base.print_acquisition_result(rows, {row["doi"] for row in active})
        return

    prompt_text = build_codex_first_qc_prompt(active)
    return_code, failure_hint = base.run_codex_prompt_foreground(prompt_text, "Codex-first full_text QC", reasoning_effort="high")
    base.build_full_text_index_quiet()
    rows = base.sync_doi_board()
    base.print_acquisition_result(rows, {row["doi"] for row in active}, failure_hint if return_code else "")


def start_synthesis_discussion() -> None:
    idea = prompt("Synthesis topic / idea / question")
    if not idea:
        print("No synthesis topic entered.")
        return
    slug = base.slugify_key(idea)[:72] or "new_synthesis"
    page = base.WIKI_SYNTHESIS / f"{slug}.md"
    if not page.exists():
        title = idea.strip()
        page.write_text(
            "\n".join(
                [
                    "---",
                    "type: synthesis",
                    "status: draft",
                    "source_status: personal-note",
                    "reading_status: mixed",
                    "review_stage: discussed",
                    "topics: []",
                    "subtopics: []",
                    "keywords: []",
                    f"created: {base.TODAY}",
                    f"updated: {base.TODAY}",
                    "sources: []",
                    "---",
                    "",
                    f"# {title}",
                    "",
                    "## Research Question",
                    "",
                    idea,
                    "",
                    "## Current Synthesis",
                    "",
                    "- Discuss with Codex before turning this into evidence-backed claims.",
                    "",
                    "## Evidence Map",
                    "",
                    "| Evidence | Type | Reading Status | Supports | Limits |",
                    "|---|---|---|---|---|",
                    "",
                    "## Tensions / Contradictions",
                    "",
                    "## Open Questions",
                    "",
                    "## Graph Links",
                    "",
                    "- Topics:",
                    "- Subtopics:",
                    "- Related literature:",
                    "- Related synthesis:",
                    "- Related seminars:",
                    "- Related projects:",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    prompt_text = f"""You are working inside this Research Wiki project.

Synthesis topic / idea:
{idea}

Draft synthesis page:
{base.repo_relative(page)}

First read core/principles.md, core/data_contract.md, core/agent_contract.md, AGENTS.md, USER_GUIDE.md, wiki/index.md, and wiki/literature/topic_registry.md.

Start a new conversation with me about this idea. Do not assume the final synthesis title or thesis yet.

As the discussion develops, check existing wiki/synthesis, wiki/literature, wiki/seminars, wiki/project_synthesis, raw/full_text_index.md, and raw/doi_dashboard.md for related evidence. Treat peer-reviewed full-read paper pages as stronger evidence than seminar or abstract-only context.

Use the draft page above as the working page. Ask me questions first. When the discussion becomes specific enough and evidence is available, update that page with source-backed synthesis. If evidence is not sufficient, list DOI/source pointers that should be added to raw/paper_sources.md instead of writing unsupported synthesis.

Do not create code pages, inbox pages, Notion mirrors, or new workflow categories.
"""
    base.MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    SYNTHESIS_PROMPT.write_text(prompt_text, encoding="utf-8")
    copied = base.copy_to_clipboard(prompt_text)
    base.open_path(page)
    base.open_path(SYNTHESIS_PROMPT)
    launched = base.launch_codex()
    print("\n== Synthesis Conversation Handoff ==")
    print(f"Draft page: {base.repo_relative(page)}")
    print(f"Prompt file: {base.repo_relative(SYNTHESIS_PROMPT)}")
    print("Prompt copied to clipboard." if copied else "Clipboard copy was unavailable; open the prompt file and paste it into Codex.")
    if launched:
        print("Codex app has been asked to open this project.")


def write_discussion_draft_page(idea: str, *, page_kind: str) -> Path:
    is_project = page_kind == "project_synthesis"
    folder = base.WIKI_PROJECT_SYNTHESIS if is_project else base.WIKI_SYNTHESIS
    page_type = "project-synthesis" if is_project else "synthesis"
    slug = base.slugify_key(idea)[:72] or ("new_project_synthesis" if is_project else "new_synthesis")
    page = folder / f"{slug}.md"
    if page.exists():
        return page
    heading = "Project Question" if is_project else "Research Question"
    body_heading = "Current Project Synthesis" if is_project else "Current Synthesis"
    page.write_text(
        "\n".join(
            [
                "---",
                f"type: {page_type}",
                "status: draft",
                "source_status: personal-note",
                "reading_status: mixed",
                "review_stage: discussed",
                "topics: []",
                "subtopics: []",
                "keywords: []",
                f"created: {base.TODAY}",
                f"updated: {base.TODAY}",
                "sources: []",
                "---",
                "",
                f"# {idea.strip()}",
                "",
                f"## {heading}",
                "",
                idea.strip(),
                "",
                f"## {body_heading}",
                "",
                "- Discuss with Codex before turning this into evidence-backed claims.",
                "",
                "## Evidence Map",
                "",
                "| Evidence | Type | Reading Status | Supports | Limits |",
                "|---|---|---|---|---|",
                "",
                "## Tensions / Contradictions",
                "",
                "## Open Questions",
                "",
                "## Graph Links",
                "",
                "- Topics:",
                "- Subtopics:",
                "- Related literature:",
                "- Related synthesis:",
                "- Related seminars:",
                "- Related projects:",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return page


def prepare_external_sandbox_prompt() -> None:
    base.ensure_core_files()
    idea = prompt("External sandbox question / topic / project idea")
    if not idea:
        print("No question entered.")
        return
    kind_value = prompt("Target page kind: synthesis or project_synthesis", "synthesis")
    page_kind = "project_synthesis" if "project" in kind_value.lower() else "synthesis"
    page = write_discussion_draft_page(idea, page_kind=page_kind)
    prompt_text = f"""You are working in another Codex sandbox on the same computer, but I want you to use and update my Research Wiki database directly.

Research Wiki database path on my machine:
{base.ROOT}

Discussion question / project idea:
{idea}

Draft wiki page to update:
{base.repo_relative(page)}

I may paste current results, notes, screenshots, code output, or analysis from this sandbox after this prompt. Treat that material as provisional working context until it is supported by Research Wiki evidence or explicitly marked as my own note.

First orient yourself:
1. Use the exact path above as the working directory. Do not create a separate clone or branch for this handoff.
2. Run `pwd` and `git status --short` from that path before editing.
3. If the path is not available in your sandbox, stop and ask me to reopen Codex with that folder mounted or selected. Do not proceed from a different copy.
4. Read `core/principles.md`, `core/data_contract.md`, `core/agent_contract.md`, `AGENTS.md`, `USER_GUIDE.md`, `raw/full_text_index.md`, `raw/doi_dashboard.md`, and `wiki/literature/topic_registry.md`.
5. For ordinary research questions, check `wiki/synthesis/`, `wiki/literature/`, then `wiki/seminars/`.
6. For project history, decisions, or cross-project context, check `wiki/project_synthesis/`, then `wiki/meetings/`, then relevant synthesis/literature.
7. Do not invent citation metadata, DOI values, full-read status, or unavailable full text.

Discussion behavior:
- Ask me clarifying questions before writing strong claims.
- Mix my external sandbox results with the Research Wiki only when the evidence tier is clear.
- Peer-reviewed full-read paper pages and QCed `raw/full_text/` are stronger than seminar notes, meeting notes, or abstract-only material.
- If evidence is insufficient, add DOI/source candidates to `raw/paper_sources.md` instead of writing unsupported synthesis.

Allowed writeback:
- Update the draft page above and closely related pages in `wiki/synthesis/` or `wiki/project_synthesis/`.
- Add source pointers to `raw/paper_sources.md` when new literature is needed.
- Add a short handoff note under `maintenance/` if useful.
- Do not edit `raw/doi_pdf/`, `raw/full_text/`, `raw/staging/`, or create `wiki/literature/` paper pages unless I explicitly ask for paper ingest.

Sync-back protocol:
1. Make edits directly in the exact database path above.
2. Run `python3 tools/wiki_lint.py` and `python3 tools/wiki_doctor.py` after editing.
3. Tell me the changed files and remaining warnings.
4. Do not use branch, PR, clone, rsync, or patch-based sync for this handoff.

Output expectations:
- Keep a concise evidence map: what came from Research Wiki, what came from my external sandbox context, and what remains uncertain.
- Update the draft page only after the discussion has enough evidence.
- Preserve YAML frontmatter and `## Graph Links` with explicit wikilinks.
"""
    base.MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    EXTERNAL_SANDBOX_PROMPT.write_text(prompt_text, encoding="utf-8")
    copied = base.copy_to_clipboard(prompt_text)
    base.open_path(page)
    base.open_path(EXTERNAL_SANDBOX_PROMPT)
    print("\n== External Sandbox Handoff ==")
    print(f"Draft page: {base.repo_relative(page)}")
    print(f"Prompt file: {base.repo_relative(EXTERNAL_SANDBOX_PROMPT)}")
    print("Prompt copied to clipboard. Paste it into the other sandbox." if copied else "Clipboard copy was unavailable; open the prompt file and paste it into the other sandbox.")


def send_feedback_issue() -> None:
    base.ensure_core_files()
    title = prompt("Issue title", "[feedback] Research Wiki Codex-first command")
    prompt_text = f"""You are working inside this Research Wiki project.

Goal:
Help me send a GitHub issue for Research Wiki feedback/problem reporting.

Issue title:
{title}

Important:
- I will provide the full description before sending.
- I may add screenshots, copied terminal output, browser observations, or extra context in the next message.
- Do not submit the issue until I explicitly confirm.

Workflow:
1. Read SUPPORT.md, core/agent_contract.md, and AGENTS.md.
2. Ask me for the complete description, expected behavior, actual behavior, reproduction steps, screenshots/images if relevant, and whether private research state needs redaction.
3. Run python3 tools/support_report.py --issue-url or use tools/support_report.py helpers to prepare a redacted report/body.
4. Check the draft for local paths, DOI values, raw PDF/full_text paths, full article text, Codex logs, and private research state.
5. Show me the draft summary and ask for explicit confirmation.
6. Only after confirmation, send the GitHub issue with gh issue create or give me the prefilled issue URL if GitHub CLI authentication is unavailable.
"""
    base.MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PROMPT.write_text(prompt_text, encoding="utf-8")
    copied = base.copy_to_clipboard(prompt_text)
    base.open_path(FEEDBACK_PROMPT)
    launched = base.launch_codex()
    print("\n== Feedback Issue Handoff ==")
    print(f"Prompt file: {base.repo_relative(FEEDBACK_PROMPT)}")
    print("Prompt copied to clipboard." if copied else "Clipboard copy was unavailable; open the prompt file and paste it into Codex.")
    if launched:
        print("Codex app has been asked to open this project.")


def menu() -> None:
    actions = {
        "1": ("Open/add paper sources", open_or_add_sources),
        "2": ("Refresh DOI dashboard + scan PDFs", refresh_dashboard_scan_pdfs),
        "3": ("Create QCed full_text with Codex", create_qced_full_text_with_codex),
        "4": ("Ingest QCed full_text to wiki", base.launch_wiki_ingest_prompt),
        "5": ("Prepare synthesis page + Codex prompt", start_synthesis_discussion),
        "6": ("Prepare feedback issue Codex prompt", send_feedback_issue),
        "7": ("Prepare external sandbox sync prompt", prepare_external_sandbox_prompt),
        "0": ("Exit", None),
    }
    while True:
        print_header()
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        choice = prompt("Choose", "0" if not sys.stdin.isatty() else "")
        if choice == "0":
            print("Bye.")
            return
        action = actions.get(choice)
        if not action:
            print("Unknown choice.")
            pause()
            continue
        try:
            action[1]()
        except KeyboardInterrupt:
            print("\nCancelled.")
        except Exception as exc:
            print(f"\nError: {exc}")
        pause()


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\nBye.")
        sys.exit(130)
