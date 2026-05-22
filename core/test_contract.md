# Research Wiki Test Contract

Any command or UI implementation must satisfy these scenarios.

## Core Checks

- Syntax checks pass for project Python tools.
- `tools/wiki_lint.py` passes.
- `tools/wiki_doctor.py` reports no errors for a clean template state.
- `tools/generate_repair_plan.py` writes an advisory plan and does not delete.
- No private raw PDF or full-text file is tracked by Git by default.

## Command Acceptance Scenarios

- DOI list input creates or refreshes dashboard rows without fabricating
  metadata.
- Authorized PDF-page workflow opens source pages or explains what the user
  should do without downloading unauthorized files.
- Local PDF import can:
  - reject non-PDF files;
  - reject valid PDFs that have no DOI and no matching dashboard row;
  - create a dashboard row from a PDF DOI;
  - rename matched PDFs to `<paper_file_key>.pdf`;
  - create machine-extracted `raw/full_text/<paper_file_key>.md`;
  - mark the row as `full_text_needed` with next action `codex_qc_full_text`.
- Running local PDF import twice is idempotent for already imported rows.
- Wiki ingest prompts must first require full-text QC when the source Markdown
  is machine extracted.
- Initializer/reset commands must require explicit confirmation and must only
  delete scoped test evidence and generated pages.

## GitHub / New User Acceptance Scenarios

- A new user can read `INSTALL.zh-TW.md` and understand core vs command vs
  personal branches.
- A user without GitHub CLI login can still run local diagnostics.
- Support report generation redacts private paths and raw evidence.
- Support issue creation opens a prefilled issue URL and does not submit it.
- CI uses synthetic fixtures, not real publisher PDFs.
