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
- In Codex-first workflows, do not create new persistent staging full
  text; use legal complete online text first, then user-downloaded PDF, then
  abstract-only fallback if complete text is unavailable.
- Complete publisher HTML/XML/authorized DOM is sufficient to create QCed
  `raw/full_text/`; PDF is valuable evidence backfill but should not block wiki
  ingest when the web full text is complete.
- Do not create or update `wiki/literature/`.
- Rebuild the full-text index after adding or changing evidence.

## Acquisition Order

1. Existing verified `raw/full_text/`.
2. Legal complete online text: publisher HTML/XML, open-access full text,
   authorized browser DOM, or user-provided source text.
3. Existing local `raw/doi_pdf/`, then local PDF extraction to staging and
   Codex reflow/QC for legacy staging-based workflows.
4. Authorized browser-session PDF or DOM capture when the user already has
   access.
5. Public open-access or author manuscript routes.
6. Ask the user to download the visible publisher PDF into `raw/doi_pdf/`, then
   continue after confirming the file exists. Prefer this local handoff over
   long Codex source hunting.
7. If only reliable metadata/abstract is available, create an abstract-only
   placeholder in `raw/full_text/` and mark the dashboard `abstract_only`.
8. Mark the row blocked/full-text-needed only when no complete text, PDF route,
   or reliable abstract is available.

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
table_quality: not_applicable
```

Use `readable-with-warnings`, `poor`, `good`, or `partial` where those values
are more accurate.

If only an abstract is available, the file in `raw/full_text/` must clearly be
abstract-only:

```yaml
extraction_status: abstract_only
readability_status: abstract-only
qc_status: abstract_only
table_quality: not_applicable
```

The DOI dashboard status must be `abstract_only`, and the next action should
point to a complete full-text/PDF acquisition route.

## Reflow / QC Requirements

Before marking a PDF-derived full text usable:

- Repair broken line wraps and dehyphenate words split across lines.
- Remove repeated page headers/footers, page numbers, author-name page
  furniture, journal issue/date furniture, and isolated extraction fragments.
- Remove or quarantine equation noise when it appears as disconnected symbols,
  for example isolated numbered fragments without surrounding explanation.
- Preserve every article section in order, with clear Markdown headings.
- Preserve figure captions, table captions, references, appendices, and
  supplementary-material notes when present.
- If equations, tables, or captions cannot be recovered cleanly, set
  `equation_quality`, `table_quality`, or readability warnings honestly and
  record the blocker.

## Table QC Gate

Tables must not be allowed to corrupt prose. Handle each table explicitly:

- Preserve every caption as its own heading, e.g. `### Table 1. Caption`.
- Use a Markdown table only when the row/column structure is unambiguous and
  compact enough to read.
- For wide, numeric, multi-page, or continued tables, preserve the content under
  the table heading in a fenced `text` block, and add `Table status`, source
  pages when known, and a note that numeric reuse requires checking the PDF or
  supplement.
- Keep `Table N. Continued` blocks under the same table section. Do not split
  them into body paragraphs.
- Remove one-word column fragments, page headers, and repeated table furniture
  from surrounding prose; keep them only inside the table block if needed.
- If a table is central to the paper and cannot be recovered from HTML/XML,
  PDF, or supplement, do not claim table QC success. Set `table_quality: poor`
  and keep `readability_status: readable-with-warnings` or `poor`; if this
  prevents trustworthy reading, leave the dashboard `full_text_needed`.

## Completion

Before marking full text usable, verify DOI/title, abstract, body sections,
conclusion or summary when present, figure/table captions, references,
appendices, and readability. Flag equations and tables honestly if extraction
damaged them.

## Duplicate DOI / PDF Guard

Before spending Codex time, check whether the canonical DOI already has
`raw/doi_pdf/`, `raw/full_text/`, or an index/dashboard row. Reuse existing
evidence instead of creating another paper entry.

- Normalize DOI URLs and DOI strings before comparison.
- Treat Copernicus filename-copy suffixes such as
  `10.5194/acp-5-799-2005-2` or `10.5194/acp-5-799-2005-3` as duplicates of
  `10.5194/acp-5-799-2005`, not as new papers.
- If duplicate PDF files are found, do not delete them automatically. Report
  the duplicate paths and continue with the canonical PDF/full_text only.
