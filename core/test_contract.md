# Research Wiki Test Contract

Any command or UI implementation must satisfy these scenarios.

## Core Checks

- Syntax checks pass for project Python tools.
- `tools/wiki_lint.py` passes.
- `tools/wiki_doctor.py` reports no errors for a clean template state.
- `tools/generate_repair_plan.py` writes an advisory plan and does not delete.
- No private raw PDF or full-text file is tracked by Git by default.

## Command Acceptance Scenarios

- Paper intake exposes local/no-token steps separately from LLM steps:
  source input, source-page opening, PDF import, duplicate review, and index
  rebuild must not launch Codex; full-text QC and source-resolution fallback
  are explicit LLM actions.
- DOI list input creates or refreshes dashboard rows without fabricating
  metadata.
- DOI-only intake creates a dashboard row but does not create PDF, staging, or
  full-text artifacts.
- DOI plus DOI URL/article URL intake deduplicates DOI rows; unresolved
  non-DOI source pointers remain queued or are recorded as source notes.
- DOI and PDF import canonicalizes publisher filename-copy suffixes, so
  duplicate files such as Copernicus `...-2005-2.pdf` do not create duplicate
  paper rows.
- Paper-source intake accepts DOI values, DOI URLs, article URLs, and PDF URLs;
  unresolved non-DOI source pointers remain queued until a DOI or reliable
  metadata is resolved.
- Authorized source-page workflow opens source pages or explains what the user
  should do without downloading unauthorized files.
- Local PDF import can:
  - reject non-PDF files;
  - reject valid PDFs that have no DOI and no matching dashboard row;
  - create a dashboard row from a PDF DOI;
  - rename matched PDFs to `<paper_file_key>.pdf`;
  - avoid creating new persistent un-QCed staging text in the canonical
    Codex-first command;
  - create `raw/full_text/<paper_file_key>.md` only after Codex reflow/QC.
- QC failure leaves `raw/full_text/` empty for that paper, does not index the
  un-QCed source text, and marks the row `full_text_needed` with next action
  `codex_convert_to_full_text`.
- Full-text QC records `table_quality` and keeps wide/continued/numeric tables
  separate from prose; table values marked `partial` or `poor` require PDF,
  HTML/XML, or supplement verification before reuse.
- Dashboard/PDF refresh must list exact byte-identical duplicate PDFs when
  present, keep a canonical PDF, and delete duplicate candidates only after an
  explicit confirmation phrase. It must not delete by wildcard or recursive
  command.
- Running local PDF import twice is idempotent for already imported and QCed
  rows.
- Wiki ingest prompts select only QCed full text and must not acquire sources
  or perform full-text reflow/QC.
- Initializer/reset commands must require explicit confirmation and must only
  delete scoped test evidence and generated pages.

## Codex-First Command Scenarios

- `ResearchWikiCodex.command` is the canonical command entrypoint.
- The deleted legacy staging-based command must not be required by docs,
  install checks, or tests.
- Dashboard refresh may sync DOI rows, rebuild indexes, scan
  `raw/doi_pdf/`, and ask for confirmed byte-identical PDF duplicate cleanup,
  but must not create new persistent files under `raw/staging/extracted_text/`.
- Full-text creation writes only QCed Markdown under
  `raw/full_text/`; failure leaves `raw/full_text/` empty for that paper and
  records a dashboard blocker instead of saving un-QCed staging text.
- Wiki ingest still selects only QCed full text.
- GitHub feedback asks for a title, writes/copies a Codex prompt,
  and opens Codex for a follow-up conversation; the command itself must not
  block on long free-form input or submit a real issue.
- External sandbox handoff writes/copies a prompt for another Codex
  sandbox on the same computer to use the exact repository path directly. It
  must not require branch, PR, clone, rsync, or patch-based sync.
- Windows launchers use repo-relative `%~dp0` paths and fall back to manual
  prompt paste when Codex app auto-launch is unavailable.
- `InitializeResearchWiki.command` and `InitializeResearchWiki.cmd` support
  first-time topic setup; reset mode requires explicit confirmation and only
  deletes scoped generated local artifacts.

## GitHub / New User Acceptance Scenarios

- A new user can read `INSTALL.zh-TW.md` and understand core vs command vs
  personal branches.
- A user without GitHub CLI login can still run local diagnostics.
- Support report generation redacts private paths and raw evidence.
- Support issue creation opens a prefilled issue URL and does not submit it.
- CI uses synthetic fixtures, not real publisher PDFs.
