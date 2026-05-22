---
name: research-wiki-fulltext-acquisition
description: Use when acquiring authorized full text for paper-source Research Wiki intake while preserving evidence, legality, naming, full-text QC state, and index/dashboard consistency without creating wiki paper pages.
---

# Research Wiki Full-Text Acquisition

Use this skill for DOI, DOI URL, article URL, PDF URL, or local PDF intake when
the task is to obtain legal evidence and produce complete, readable, QCed
full-text Markdown for a Research Wiki database.

## Core Rules

- Follow `core/principles.md` and `core/data_contract.md`.
- Preserve the evidence chain.
- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Prefer legal publisher HTML/XML/DOM when it provides complete text.
- Save source pointers in `raw/paper_sources.md` until a DOI or reliable
  metadata is resolved.
- Save DOI PDFs as `raw/doi_pdf/<paper_file_key>.pdf`.
- Save machine extraction only as staging under `raw/staging/extracted_text/`.
- Save final full text as `raw/full_text/<paper_file_key>.md` only after
  reflow/QC.
- Do not create or update `wiki/literature/`.
- Rebuild the full-text index after adding or changing evidence.

## Acquisition Order

1. Existing verified `raw/full_text/`.
2. Existing local `raw/doi_pdf/`, then local PDF extraction to staging and
   Codex reflow/QC.
3. User-provided full text or saved legal HTML/XML.
4. Publisher HTML/XML when legally accessible.
5. Authorized browser-session PDF or DOM capture when the user already has
   access.
6. Public open-access or author manuscript routes.
7. Ask for user-provided PDF or mark the row blocked/full-text-needed.

## PDF Extraction State

Machine-extracted PDF Markdown is not citation-ready and must not be written to
`raw/full_text/`. Put it under `raw/staging/extracted_text/` and mark it:

```yaml
extraction_status: machine_extracted_needs_codex_qc
readability_status: needs_codex_qc
qc_status: pending_codex_qc
equation_quality: not_checked
```

Dashboard status remains `full_text_needed`; next action is
`codex_convert_to_full_text`.

## Full Text Completion State

Only write `raw/full_text/<paper_file_key>.md` after reflow/QC. Final
frontmatter must include:

```yaml
extraction_status: codex_qc_done
readability_status: readable
qc_status: codex_qc_done
equation_quality: not_applicable
```

Use `readable-with-warnings`, `poor`, `good`, or `partial` where those values
are more accurate.

## Completion

Before marking full text usable, verify DOI/title, abstract, body sections,
conclusion or summary when present, figure/table captions, references, and
readability. Flag equations and tables honestly if extraction damaged them.
