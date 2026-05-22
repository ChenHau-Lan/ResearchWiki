# Research Wiki Conversation Handoff

Generated: 2026-05-21

## Current Database Shape

- This repo is a GitHub-ready Karpathy-style LLM Wiki research database.
- `core/` is now the command-independent source of truth for principles, data contracts, agent contracts, skills, and test contracts.
- `raw/` is the evidence layer: paper source queue, DOI dashboard, PDFs, extraction staging, QCed full-text Markdown, raw files, full-text index.
- `wiki/` is the curated knowledge layer: literature, synthesis, meetings, project_synthesis, seminars.
- `maintenance/` is outside `wiki/`: logs, repair plans, release checklist, Obsidian graph guide, Codex handoff prompts.
- `ResearchWiki.command` is the main user entrypoint and a command/UI implementation of the core contract. It keeps mechanical tasks local and hands literature-understanding tasks to Codex.
- Paper workflow is: source pointer -> authorized source/page resolution -> evidence import -> staging extraction -> Codex full_text reflow/QC -> wiki literature page.
- Current template state: clean empty DOI/full-text indexes. Synthetic workflow tests no longer leave ignored raw evidence referenced by tracked dashboard/index files unless `RESEARCHWIKI_LEAVE_SAMPLE_STATE=1` is set.

## Current Command Menu

1. Add/open paper sources.
2. Open DOI dashboard.
3. Codex-assisted source/full-text finding for slow/exception cases.
4. Prepare Codex app source/full-text finding prompt and app-run log.
5. Open authorized source pages for queued sources or DOI rows missing evidence.
6. Import evidence, create staging extraction, run Codex reflow/QC, and write `raw/full_text/` only after QC succeeds.
7. Ingest QCed full_text into wiki literature pages.
8. Launch Codex project conversation.
9. Manage topic/subtopic registry.
10. Open Obsidian graph guide.
11. Run database health check.
12. Generate repair plan.
13. Prepare a redacted GitHub support issue draft.

Additional test helper:

- `InitializeResearchWiki.command` resets a local test database after explicit confirmation (`INIT TEST DATABASE`). It batch-clears scoped test evidence, generated raw artifacts, and generated wiki pages, preserving tools/templates/skills/docs/topic registry/Obsidian settings and resetting section index pages.
- `tools/test_research_wiki_workflow.py` runs 10 reset-first integration scenarios and writes `maintenance/workflow_test_report_YYYY-MM-DD.md`. Latest run on 2026-05-21 passed 10/10 and reset the database to a clean template state afterward. Set `RESEARCHWIKI_LEAVE_SAMPLE_STATE=1` only when a maintainer explicitly wants a four-paper sample state for manual inspection.
- `InitializeResearchWiki.command` and `ResearchWiki.command` were smoke-tested from the shell. Their final `read` now tolerates non-interactive EOF so automated checks do not falsely fail after successful work.
- `tools/check_install.py` verifies local install prerequisites.
- `tools/support_report.py` writes a redacted local support report and prints a prefilled GitHub issue URL; it never submits issues automatically.
- Heartbeat new-user testing found and fixed two release blockers: fresh clones no longer warn about stale dashboard/index paths to ignored raw evidence, and support reports no longer include git-status file examples or GitHub account names by default.
- `.github/` contains CI, issue templates, and a PR template for private-first GitHub maintenance.

## Rules To Preserve

- Do not batch-delete files.
- Do not automate unauthorized PDF/full-text downloads.
- Treat `core/*` as authoritative when command behavior and core rules differ.
- Dashboard is not source of truth; actual files and indexes are.
- Paper pages must not copy full article text.
- Use `raw/doi_pdf/<paper_file_key>.pdf`, `raw/staging/extracted_text/<paper_file_key>.md`, and QCed `raw/full_text/<paper_file_key>.md`.
- Use `maintenance/` for logs and repair outputs, not `wiki/maintenance/`.
- Use Research Wiki Dev Mode when discussing database updates.

## Key Problems Still Worth Solving

- Next practical DOI work should preserve the new boundary: staging extraction is not full_text; option 7 should only ingest already-QCed `raw/full_text/*.md`.
- Branch discipline should follow `maintenance/branch_strategy.md`: `main` is private protected integration, `codex/core-*` for core, `codex/command-*` for command/UI, `personal/*` for private research state.
- Browser-session PDF download may depend on macOS/Codex/Chrome permissions; keep Codex acquisition as fallback, not the default batch route.
- `ResearchWiki.command` should stay simple; avoid adding many special-case menu items.
- Obsidian graph quality depends on consistent `Graph Links`; future pages need periodic checks.
- Raw evidence is mostly ignored by Git, so the long-term sync/backup plan for `raw/doi_pdf/` and `raw/full_text/` still needs a firm decision.
- Topic/subtopic registry should remain small; do not let keywords become uncontrolled graph nodes.
- Full text acquisition must clearly record access legality and source type.
