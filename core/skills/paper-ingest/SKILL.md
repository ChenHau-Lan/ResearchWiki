---
name: paper-ingest
description: Use when turning QCed raw/full_text Markdown into single-paper wiki/literature pages while preserving evidence tier, reading status, and graph links.
---

# Paper Ingest

Paper ingest turns one QCed full text into one paper page. It does not perform
source acquisition and does not write cross-paper synthesis.

## Modes

- `ingest-qced-full-text`: read `raw/full_text/<paper_file_key>.md`, verify that
  QC metadata permits ingest, then create or update `wiki/literature/<slug>.md`.

## Rules

- Use `reading_status: full-read` only when the QCed full text was read across
  abstract, body, methods/results where present, limitations, conclusion, and
  captions/tables when relevant.
- If full text is `abstract_only`, create only an abstract/metadata-limited page
  and mark the limitation clearly.
- Keep the page about the single paper. Cross-paper judgment belongs in
  `wiki/synthesis/`.
- Preserve `doi`, `citation_key`, `paper_file_key`, frontmatter, and
  `## Graph Links` with explicit wikilinks.
- If table or equation QC is partial/poor, do not use exact numeric or formula
  claims without checking PDF, HTML/XML table, or supplement.
