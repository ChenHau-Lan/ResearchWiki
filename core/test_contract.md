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
  source input, source-page opening, PDF import, staging extraction, and index
  rebuild must not launch Codex; staging reflow/QC and source-resolution
  fallback are explicit LLM actions.
- DOI list input creates or refreshes dashboard rows without fabricating
  metadata.
- DOI-only intake creates a dashboard row but does not create PDF, staging, or
  full-text artifacts.
- DOI plus DOI URL/article URL intake deduplicates DOI rows; unresolved
  non-DOI source pointers remain queued or are recorded as source notes.
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
  - create machine-extracted staging text under `raw/staging/extracted_text/`;
  - create `raw/full_text/<paper_file_key>.md` only after Codex reflow/QC.
- QC failure leaves `raw/full_text/` empty for that paper, does not index the
  staging text, and marks the row `full_text_needed` with next action
  `codex_convert_to_full_text`.
- Running local PDF import twice is idempotent for already imported and QCed
  rows.
- Wiki ingest prompts select only QCed full text and must not acquire sources
  or perform full-text reflow/QC.
- Initializer/reset commands must require explicit confirmation and must only
  delete scoped test evidence and generated pages.

## GitHub / New User Acceptance Scenarios

- A new user can read `INSTALL.zh-TW.md` and understand core vs command vs
  personal branches.
- A user without GitHub CLI login can still run local diagnostics.
- Support report generation redacts private paths and raw evidence.
- Support issue creation opens a prefilled issue URL and does not submit it.
- CI uses synthetic fixtures, not real publisher PDFs.
