# User Guide

[中文操作摘要](USER_GUIDE.zh-TW.md)

This guide is for someone receiving the repository for the first time. You do not need to understand Markdown knowledge bases before using it.

## 1. Concept

Research Wiki is an LLM Wiki:

- `core/` is the command-independent rule layer.
- `raw/` is the evidence and input layer.
- `wiki/` is the curated knowledge layer.
- `ResearchWiki.command` performs local low-token work and launches Codex handoffs.
- Codex performs source judgment, full-text reflow/QC, paper page extraction, synthesis, and discussion.

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

## 3. Add Paper Sources

Use `ResearchWiki.command` and choose `Paper intake: sources -> QCed full_text`, or edit `raw/paper_sources.md` directly:

```md
## Add Sources Here

```text
10.1175/WAF-D-21-0044.1
https://doi.org/10.5194/acp-21-9779-2021
https://example.org/article-page
```
```

Progress is shown in `raw/doi_dashboard.md`.

The dashboard columns are:

```text
Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text
```

Longer next actions and failure reasons are kept in the `DOI Notes` section below the board.

The default paper-source workflow is source-first and semi-automatic:

1. Choose `Paper intake: sources -> QCed full_text`.
2. Paste DOI/URL/PDF source pointers, or use queued sources.
3. Save legal PDFs into `raw/doi_pdf/` when the command opens authorized source pages.
4. Let the command import evidence, create staging text, and use Codex CLI or a pasteable Codex prompt to produce QCed `raw/full_text/`.
5. Choose `Ingest QCed full_text to wiki` when ready to create paper pages.

Codex acquisition is now a fallback for open publisher HTML/XML, authorized browser-session capture, or cases where source-route judgment is needed.

If source/full-text finding needs browser-session access that the CLI cannot use, use the Codex app handoff option. It creates `maintenance/codex_app_handoff_prompt.md`, initializes `maintenance/codex_app_last_run.log`, and asks the Codex app run to append concise acquisition notes to that log.

For normal DOI batches, use `Paper intake: sources -> QCed full_text`. It opens source pages and `raw/doi_pdf/` when user evidence is needed; only use publisher, author, open-access, institutional, or user-provided PDFs/full text.

DOI-derived files use paper-based filenames: `last_name_year_journal_abbrev`. For example, Conrick et al. 2021 in Weather and Forecasting becomes `conrick_2021_waf.pdf` and `conrick_2021_waf.md`.

If a publisher blocks shell download but the article page is readable in your browser and the PDF button works, this is treated as authorized browser-session access. The default workflow is still to download the legal PDF manually after the intake command opens the page, then rerun intake to create QCed full text; Codex browser capture is a fallback.

## 4. Command Menu

1. `Paper intake: sources -> QCed full_text`: the main one-stop workflow. It accepts DOI/URL input, opens authorized source pages when needed, imports PDFs/evidence, creates staging text, and uses Codex CLI or a pasteable prompt to create QCed `raw/full_text/`.
2. `Ingest QCed full_text to wiki`: creates or updates `wiki/literature/` paper pages from already-QCed full text. It does not acquire sources or perform full-text reflow/QC.
3. `Project / idea conversation`: starts Codex with an English project/idea discussion prompt and lets Codex infer topics after the conversation.
4. `Topics / graph`: opens topic/subtopic registry and Obsidian graph guidance.
5. `Maintenance / support`: opens the DOI dashboard, runs health checks, writes repair plans, opens the paper source queue, or prepares a redacted GitHub issue draft.

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
