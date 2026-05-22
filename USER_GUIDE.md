# User Guide

[中文操作摘要](USER_GUIDE.zh-TW.md)

This guide is for someone receiving the repository for the first time. You do not need to understand Markdown knowledge bases before using it.

## 1. Concept

Research Wiki is an LLM Wiki:

- `core/` is the command-independent rule layer.
- `raw/` is the evidence and input layer.
- `wiki/` is the curated knowledge layer.
- `ResearchWiki.command` performs local low-token work and launches Codex handoffs.
- Codex performs full-text acquisition, paper page extraction, synthesis, and discussion.

Use this mental model:

- Core defines what must be true.
- Command is one way to operate the database.
- Personal branches and ignored files store user-specific research state.

## 2. Install And Check Tools

Ask Codex:

```text
Please read core/README.md, README.md, USER_GUIDE.md, and AGENTS.md, then run python3 tools/check_install.py and tell me what I need to install before using Research Wiki.
```

Required tools:

- Codex
- Git
- Python 3
- ripgrep (`rg`)

Recommended:

- Obsidian
- Poppler / `pdftotext`
- Chrome

Optional:

- Zotero
- Google Drive

## 3. Add DOI Values

Use `ResearchWiki.command` and choose `Open/add DOI to raw/doi_list.md`, or edit the file directly:

```md
## Add DOI Here

```text
10.1175/WAF-D-21-0044.1
```
```

Progress is shown in `raw/doi_dashboard.md`.

The dashboard columns are:

```text
Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text
```

Longer next actions and failure reasons are kept in the `DOI Notes` section below the board.

The default DOI workflow is PDF-first and semi-automatic:

1. Open authorized DOI/publisher pages.
2. Save legal PDFs into `raw/doi_pdf/`.
3. Import PDFs and extract local machine text into `raw/full_text/`.
4. Use Codex to reflow/QC full text, set readability/equation metadata, and ingest QCed text into `wiki/literature/`.

Codex acquisition is now a fallback for open publisher HTML/XML, authorized browser-session capture, or cases where source-route judgment is needed.

If fallback acquisition needs browser-session access that the CLI cannot use, use the Codex app handoff option. It creates `maintenance/codex_app_handoff_prompt.md`, initializes `maintenance/codex_app_last_run.log`, and asks the Codex app run to append concise acquisition notes to that log.

For normal DOI batches, use the authorized PDF page option first. It opens DOI landing pages and `raw/doi_pdf/`; only use publisher, author, open-access, institutional, or user-provided PDFs.

DOI-derived files use paper-based filenames: `last_name_year_journal_abbrev`. For example, Conrick et al. 2021 in Weather and Forecasting becomes `conrick_2021_waf.pdf` and `conrick_2021_waf.md`.

If a publisher blocks shell download but the article page is readable in your browser and the PDF button works, this is treated as authorized browser-session access. The default workflow is still to download the legal PDF manually through option 5 and let option 6 extract full text locally; Codex browser capture is a fallback.

## 4. Command Menu

1. `Open/add DOI to raw/doi_list.md`: local DOI input.
2. `Open/manage DOI dashboard`: opens progress board.
3. `Launch Codex fallback acquisition (slow)`: runs Codex only for exceptions such as open publisher HTML/XML, authorized browser-session capture, or source-route judgment. It should stop and request the PDF-first path instead of spending a long session chasing blocked publisher routes.
4. `Generate Codex app fallback acquisition prompt`: writes the fallback acquisition prompt to `maintenance/codex_app_handoff_prompt.md`, initializes `maintenance/codex_app_last_run.log`, copies the prompt to the clipboard when possible, and opens the Codex app on this repository.
5. `Open authorized PDF pages (recommended first)`: opens DOI landing pages for dashboard rows missing PDFs and opens `raw/doi_pdf/`. Do not use this project to automate unauthorized shadow-library downloads.
6. `Import PDFs + extract full_text + rebuild index`: local maintenance, no literature reasoning. It checks `raw/doi_pdf/` for newly added PDFs, creates missing dashboard rows from PDF DOI metadata, renames matched files to `<paper_file_key>.pdf`, extracts machine Markdown into `raw/full_text/`, marks it for Codex QC, updates paths, then prints DOI dashboard status and full-text index output separately.
7. `Launch Codex full_text QC + wiki ingest`: runs Codex in the foreground, shows concise QC/ingest status, reflows and QC-labels machine-extracted full text, then turns QCed text into paper-specific reading pages.
8. `Launch Codex project conversation`: starts Codex with an English project/idea discussion prompt and lets Codex infer topics after the conversation.
9. `Manage topic registry`: opens or appends topics and subtopics.
10. `Open Obsidian graph guide`: opens graph instructions for reading relationships.
11. `Run database health check (diagnose only)`: checks stale paths, missing graph links, unresolved links, release hygiene, local machine paths, and structure issues without deleting files.
12. `Generate repair plan (no deletes)`: writes an issue-specific repair plan under `maintenance/` without deleting files.
13. `Prepare GitHub support issue (redacted)`: writes a redacted support report and opens a prefilled GitHub issue URL for human review.

## 5. Knowledge Areas

Default research query priority:

1. `wiki/synthesis/`
2. `wiki/literature/`
3. `wiki/seminars/`

Project history or meeting-decision priority:

1. `wiki/project_synthesis/`
2. `wiki/meetings/`

Page roles:

- Literature: single-paper facts.
- Synthesis: cross-paper research judgment.
- Meeting: one meeting.
- Project synthesis: cross-meeting project evolution and decisions.
- Seminar: one talk or seminar, lower evidence tier than literature.

## 6. Topics, Subtopics, Keywords

Use `wiki/literature/topic_registry.md`.

- `topics`: broad research areas.
- `subtopics`: precise retrieval categories.
- `keywords`: flexible details.

Use `subtopics` to make future search more precise, but do not promote every keyword into a subtopic.

## 7. Obsidian Graph

Open the `wiki/` folder as an Obsidian vault.

Formal pages should include:

```md
## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects:
```

Use explicit wikilinks such as `[[topic_aerosol]]` and `[[subtopic_wildfire_smoke_microphysics]]`. This makes the graph readable.

See `maintenance/obsidian_graph_guide.md`.

## 8. Maintenance And Repair

Run:

```bash
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
```

Repair plans do not delete files. They list candidate issues and recommended actions.

If a repair plan lists `.DS_Store`, handle it as release hygiene. Review the exact path and remove only one explicit file at a time after human review; do not use recursive, wildcard, or bulk cleanup commands.

## 9. Test Reset Command

Use `InitializeResearchWiki.command` only when you intentionally want a clean local test database. It asks you to type `INIT TEST DATABASE`, then batch-clears scoped test evidence, generated raw artifacts, and generated wiki pages while keeping tools, templates, skills, docs, topic registry, and Obsidian settings. It also resets section index pages so they do not point to deleted generated pages.

## 10. GitHub Release Check

Before publishing:

- Check for absolute local home-directory paths.
- Remove `.DS_Store` files from the release one explicit path at a time.
- Do not publish private PDFs or raw data accidentally.
- Keep `raw/full_text/` data out of Git unless intentionally included.
- Confirm `skills/THIRD_PARTY_NOTICES.md`.

## 11. Support Issues

If install or first run fails:

```bash
python3 tools/support_report.py --issue-url
```

The report is written to `maintenance/support_report.md`. It redacts local home paths, DOI values, raw PDF paths, full-text paths, and Codex logs. The GitHub issue URL is only prefilled; you must review and submit it yourself.
