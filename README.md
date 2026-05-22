# Research Wiki

[中文快速說明](README.zh-TW.md)

Research Wiki is a GitHub-ready Karpathy-style LLM Wiki template for academic reading, DOI intake, full-text evidence caching, research synthesis, project synthesis, and Obsidian graph navigation.

The core idea is simple: keep mechanical maintenance local, and spend LLM tokens only on literature understanding and research discussion.

## What This Is

- A DOI-first research database.
- A command-independent core contract for evidence, pages, skills, and tests.
- A local command helper for low-token / no-token operations.
- A wiki structure optimized for paper reading and cross-paper synthesis.
- An Obsidian-friendly knowledge graph built from explicit wikilinks.
- A repairable database with lint, health checks, and human-reviewed repair plans.

## Core, Command, Personal

Research Wiki has three layers:

1. `core/`: principles, data contract, agent contract, skills, and acceptance tests. This is the source of truth.
2. Command layer: `ResearchWiki.command` and `tools/` implement the core contract as a local UI.
3. Personal layer: user-specific research state belongs on `personal/*` branches or ignored raw files.

If command behavior and `core/` disagree, treat `core/` as authoritative and open an issue.

## Five-Minute Quickstart

1. Clone or open this repository in Codex.
2. Ask Codex to check required apps and skills:

   ```text
   Please read core/README.md, README.md, USER_GUIDE.md, and AGENTS.md, then run python3 tools/check_install.py and tell me what I need to install before using Research Wiki.
   ```

3. Open `ResearchWiki.command`.
4. Add DOI values to `raw/doi_list.md`.
5. Choose `Open authorized PDF pages (recommended first)`, download legal PDFs from authorized sources, and place them in `raw/doi_pdf/`.
6. Run `Import PDFs + extract full_text + rebuild index`.
7. After machine-extracted full text exists, choose `Launch Codex full_text QC + wiki ingest`.
8. Use `Launch Codex fallback acquisition (slow)` only for open publisher HTML/XML, authorized browser-session capture, or rows where source judgment is genuinely needed.

## Required Apps And Optional Tools

Required:

- Codex
- Git
- Python 3
- ripgrep (`rg`)

Recommended:

- Obsidian for graph browsing.
- Poppler / `pdftotext` for PDF extraction.
- Chrome for authorized publisher pages.

Optional:

- Zotero, only when papers become citation-ready.
- Google Drive, only as an external file sync layer.

## Command Menu

`ResearchWiki.command` is designed for fast local operations.

1. `Open/add DOI to raw/doi_list.md`: local DOI input helper.
2. `Open/manage DOI dashboard`: opens the status board.
3. `Launch Codex fallback acquisition (slow)`: runs Codex only for exceptions such as open publisher HTML/XML, authorized browser-session capture, or source-route judgment. It should stop and request the PDF-first path instead of spending a long session chasing blocked publisher routes.
4. `Generate Codex app fallback acquisition prompt`: writes the same fallback acquisition prompt to `maintenance/codex_app_handoff_prompt.md`, initializes `maintenance/codex_app_last_run.log`, copies the prompt to the clipboard when possible, and opens the Codex app on this repository.
5. `Open authorized PDF pages (recommended first)`: opens DOI landing pages for rows missing PDFs and opens `raw/doi_pdf/`. Use publisher, author, open-access, institutional, or user-provided PDFs only; the project does not automate unauthorized shadow-library downloads.
6. `Import PDFs + extract full_text + rebuild index`: local maintenance; it checks `raw/doi_pdf/` for newly added PDFs, creates missing dashboard rows from PDF DOI metadata, renames matched files to `<paper_file_key>.pdf`, writes machine-extracted Markdown into `raw/full_text/`, marks it for Codex QC, updates PDF/full-text links, and rebuilds the index.
7. `Launch Codex full_text QC + wiki ingest`: runs Codex in the foreground to reflow/QC machine-extracted full text, set readability/equation metadata, and then turn QCed full text into a paper-specific reading page.
8. `Launch Codex project conversation`: starts a new project or idea discussion prompt in this repository.
9. `Manage topic registry`: opens or appends to topic/subtopic registry.
10. `Open Obsidian graph guide`: opens graph navigation guidance for relationship maps.
11. `Run database health check (diagnose only)`: local diagnostics for stale paths, graph links, release hygiene, and local machine paths; no file deletion.
12. `Generate repair plan (no deletes)`: writes a human-reviewed repair plan under `maintenance/` with issue-specific actions and safe cleanup notes.
13. `Prepare GitHub support issue (redacted)`: writes `maintenance/support_report.md` and opens a prefilled GitHub issue URL. Review before submitting.

## DOI Workflow

1. Paste DOI values into `raw/doi_list.md`.
2. Use `Open authorized PDF pages (recommended first)`; only download PDFs from publisher, author, open-access, institutional, or user-provided sources.
3. Put downloaded PDFs directly in `raw/doi_pdf/`.
4. Run `Import PDFs + extract full_text + rebuild index`; command maintenance detects extra PDFs, creates missing DOI rows from PDF metadata, renames matched files, extracts machine Markdown, marks it for Codex QC, and updates the dashboard/index.
5. Use Codex fallback acquisition only when PDF-first cannot work or when open publisher HTML/XML can produce better full text.
6. If shell download is blocked but the article/PDF is visible in the user's browser, Codex may use browser-session PDF download before asking for manual upload.
7. DOI PDFs go to `raw/doi_pdf/<paper_file_key>.pdf`.
8. Readable full text goes to `raw/full_text/<paper_file_key>.md`.
9. Launch Codex full_text QC + wiki ingest from existing full text.
10. Paper notes go to `wiki/literature/<slug>.md`.
11. Cross-paper judgment goes to `wiki/synthesis/`.
12. Local tools rebuild `raw/full_text_index.*` and refresh `raw/doi_dashboard.md`.

Example paper file key: Conrick et al. 2021 in Weather and Forecasting becomes `conrick_2021_waf`.

`raw/doi_dashboard.md` is not the evidence source of truth. Real evidence must exist in `raw/doi_pdf/`, `raw/full_text/`, `wiki/literature/`, `raw/files/`, or `raw/full_text_index.*`.

The DOI dashboard is intentionally compact:

```text
Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text
```

Longer failure reasons and next actions live below it in `DOI Notes`.

## Query Priority

Default research questions:

1. `wiki/synthesis/`
2. `wiki/literature/`
3. `wiki/seminars/`

Project history or meeting decisions:

1. `wiki/project_synthesis/`
2. `wiki/meetings/`

## Folder Map

```text
raw/
  doi_list.md
  doi_dashboard.md
  doi_pdf/
  full_text/
  full_text_index.md
  full_text_index.json
  files/

wiki/
  literature/
  synthesis/
  meetings/
  project_synthesis/
  seminars/

core/
  principles.md
  data_contract.md
  agent_contract.md
  test_contract.md
  skills/

maintenance/
templates/
tools/
skills/
```

## Maintenance

Run:

```bash
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
```

Repair plans are advisory. They do not delete files.

For install or first-run problems:

```bash
python3 tools/check_install.py
python3 tools/support_report.py --issue-url
```

The support report redacts local paths, DOI values, raw PDF paths, full-text paths, and Codex logs. It prepares an issue URL but does not submit it.

If the doctor reports `.DS_Store`, treat it as release hygiene. Review the exact path and remove only one explicit file at a time after human review; do not use recursive, wildcard, or bulk cleanup commands.

## Test Reset

`InitializeResearchWiki.command` resets the local database for testing. It asks for the exact confirmation text `INIT TEST DATABASE`, then batch-clears scoped test evidence, generated raw artifacts, and generated wiki pages while keeping tools, templates, skills, docs, topic registry, and Obsidian settings. It also resets section index pages so they do not point to deleted generated pages. Use it only when you intentionally want a clean local test database.

## Obsidian Graph

Open `wiki/` as an Obsidian vault. Formal pages include a `Graph Links` section so the graph can show relationships among literature, synthesis, seminars, projects, topics, and subtopics.

See `maintenance/obsidian_graph_guide.md`.

## More

- [User Guide](USER_GUIDE.md)
- [Install Guide](INSTALL.md)
- [Support Guide](SUPPORT.md)
- [Agent Rules](AGENTS.md)
- [Chinese Quickstart](README.zh-TW.md)
- [Contributing](CONTRIBUTING.md)
