---
name: source-intake
description: Use when adding DOI/URL/PDF sources, refreshing the DOI dashboard, scanning PDFs, resolving legal full text, or producing QCed raw/full_text without creating paper pages.
---

# Source Intake

Source intake owns source pointers and evidence import. It writes only to
`raw/` and generated intake indexes unless a support prompt explicitly says
otherwise.

## Modes

- `add-source`: add DOI, DOI URL, article URL, PDF URL, or source notes to
  `raw/paper_sources.md`, then refresh dashboard metadata when possible.
- `refresh-dashboard`: sync `raw/doi_dashboard.md`, scan `raw/doi_pdf/`, detect
  duplicate-looking PDFs, and rebuild `raw/full_text_index.*`.
- `qced-full-text`: use legal full text, authorized browser DOM, user-provided
  PDF/text, or abstract fallback to create only QCed `raw/full_text/`.

## Rules

- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Do not create `wiki/literature/` pages in this skill.
- Do not write machine extraction to `raw/full_text/`; un-QCed staging belongs
  only in `raw/staging/extracted_text/` when a legacy/import tool explicitly
  labels it as not ready.
- Only mark `full_text_done` after reflow/QC.
- If complete text is unavailable, use `abstract_only` honestly or leave the
  dashboard at `full_text_needed` with a blocker.
- Duplicate or release-noise files may be reported, but not batch-deleted by
  repair tooling.
