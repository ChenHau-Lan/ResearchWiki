---
name: research-wiki-academic-writer
description: Use when drafting paper pages, literature reviews, proposals, reports, or synthesis from Research Wiki evidence without fabricating citations or mixing evidence tiers.
---

# Research Wiki Academic Writer

Compatibility note: in the v2 skill-first pipeline, single-paper writing belongs
to `paper-ingest`, and Query/Save writing belongs to `knowledge-workbench`. Use
this skill to write from Research Wiki evidence while preserving citation
integrity and evidence tiers.

## Non-Negotiables

- Follow `core/principles.md` and `core/data_contract.md`.
- Do not fabricate citations.
- Verify title, authors, venue/year, DOI, or canonical URL before citing.
- Resolve existing evidence through `raw/full_text_index.json`.
- Read synthesis first for research judgment, then literature pages, then
  seminars as lower-priority context.
- Use project synthesis and meetings only for project history and decisions.

## Evidence Priority

1. Reviewed synthesis backed by full-read literature.
2. Full-read paper pages linked to verified `raw/full_text/<paper_file_key>.md`.
3. Abstract-only pages, clearly labeled as limited.
4. Seminar notes as talk context only.
5. Project synthesis and meetings for decision history only.

## Paper Page Generation

- Write a concise single-paper reading note, not an operations report.
- Keep full paper text out of `wiki/literature/`.
- Use `reading_status: full-read` only after reading body, methods, results,
  limitations, and conclusion/summary from QCed full text.
- Before creating a full-read paper page, reject full_text that still contains
  obvious PDF extraction damage: broken paragraphs, repeated page furniture,
  orphaned equation fragments, missing section headings, or missing figure/table
  captions. Send it back to full-text QC instead of ingesting it.
- If `table_quality` is `partial` or `poor`, do not use numeric table values in
  synthesis or paper-page claims unless the PDF, HTML/XML table, or supplement
  has been checked. Record the limitation instead of treating the table as
  fully read.
- Keep cross-paper interpretation in `wiki/synthesis/`.
- Preserve `## Graph Links` with explicit wikilinks.
