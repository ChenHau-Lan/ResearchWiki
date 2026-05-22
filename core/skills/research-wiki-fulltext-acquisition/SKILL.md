---
name: research-wiki-fulltext-acquisition
description: Use when acquiring authorized full text for DOI-driven Research Wiki intake while preserving evidence, legality, naming, full-text QC state, and index/dashboard consistency without creating wiki paper pages.
---

# Research Wiki Full-Text Acquisition

Use this skill for DOI or article URL intake when the task is to obtain legal,
complete, readable full-text Markdown for a Research Wiki database.

## Core Rules

- Follow `core/principles.md` and `core/data_contract.md`.
- Preserve the evidence chain.
- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Prefer legal publisher HTML/XML/DOM when it provides complete text.
- Save DOI PDFs as `raw/doi_pdf/<paper_file_key>.pdf`.
- Save full text as `raw/full_text/<paper_file_key>.md`.
- Do not create or update `wiki/literature/`.
- Rebuild the full-text index after adding or changing evidence.

## Acquisition Order

1. Existing verified `raw/full_text/`.
2. Existing local `raw/doi_pdf/`, then local PDF extraction.
3. User-provided full text or saved legal HTML/XML.
4. Publisher HTML/XML when legally accessible.
5. Authorized browser-session PDF or DOM capture when the user already has
   access.
6. Public open-access or author manuscript routes.
7. Ask for user-provided PDF or mark the row blocked/full-text-needed.

## PDF Extraction State

Machine-extracted PDF Markdown is not citation-ready. Mark it:

```yaml
extraction_status: machine_extracted_needs_codex_qc
readability_status: needs_codex_qc
qc_status: pending_codex_qc
equation_quality: not_checked
```

Dashboard status remains `full_text_needed`; next action is
`codex_qc_full_text`.

## Completion

Before marking full text usable, verify DOI/title, abstract, body sections,
conclusion or summary when present, figure/table captions, references, and
readability. Flag equations and tables honestly if extraction damaged them.
