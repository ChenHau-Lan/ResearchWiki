# Research Wiki Data Contract

## Canonical Files

- `raw/doi_list.md`: legacy DOI-only input, retained for compatibility.
- `raw/paper_sources.md`: primary paper-source intake for DOI values, DOI URLs,
  article URLs, PDF URLs, and source notes.
- `raw/doi_dashboard.md`: processing dashboard, not evidence source of truth.
- `raw/doi_pdf/`: DOI PDF evidence, named `<paper_file_key>.pdf`.
- `raw/staging/extracted_text/`: machine-extracted text that is not yet
  readable full text and must not be indexed as full text.
- `raw/full_text/`: Codex-reflowed, QCed, readable full-text Markdown, named
  `<paper_file_key>.md`.
- `raw/full_text_index.md` and `raw/full_text_index.json`: dispatch indexes.
- `raw/files/`: non-DOI raw sources such as seminar slides or transcripts.
- `wiki/literature/`: single-paper reading notes.
- `wiki/synthesis/`: cross-literature research judgment.
- `wiki/meetings/`: meeting records.
- `wiki/project_synthesis/`: project history and decision synthesis.
- `wiki/seminars/`: seminar and talk notes.
- `maintenance/`: repair, support, release, test, and handoff artifacts.

## DOI Status Values

Only these dashboard statuses are valid:

- `new`
- `metadata_ok`
- `full_text_needed`
- `full_text_done`
- `wiki_done`
- `abstract_only`
- `blocked`

Machine-extracted PDF text that still needs Codex QC is represented as staging,
not as full text:

- dashboard status: `full_text_needed`
- dashboard next action: `codex_convert_to_full_text`
- staging path: `raw/staging/extracted_text/<paper_file_key>.md`
- staging frontmatter:
  - `extraction_status: machine_extracted_needs_codex_qc`
  - `readability_status: needs_codex_qc`
  - `qc_status: pending_codex_qc`
  - `equation_quality: not_checked`

Only Codex-reflowed/QCed Markdown may be written to `raw/full_text/`.
Final full text must use:

- `extraction_status: codex_qc_done`
- `qc_status: codex_qc_done`
- `readability_status: readable`, `readable-with-warnings`, or `poor`
- `equation_quality: good`, `partial`, `poor`, or `not_applicable`

## Naming

`paper_file_key` is:

```text
first_author_last_name_year_journal_abbrev
```

Rules:

- lowercase ASCII
- punctuation and spaces replaced by underscores
- use a common journal abbreviation when known
- append a short DOI slug only when needed to avoid collisions

Examples:

- Weather and Forecasting -> `waf`
- Atmospheric Chemistry and Physics -> `acp`
- Bulletin of the American Meteorological Society -> `bams`

## Wiki Frontmatter

Formal wiki pages use YAML frontmatter:

```yaml
---
type: paper | synthesis | meeting | project-synthesis | seminar
status: draft | reviewed | needs-verification | deprecated
source_status: peer-reviewed | preprint | dataset | software | talk | personal-note | non-academic
reading_status: metadata-only | abstract-only | skimmed | full-read | reproduced | mixed
review_stage: ai-extracted | human-checked | discussed | integrated | cited
topics: []
subtopics: []
keywords: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
---
```

Support pages may use support metadata, but must not create new content types.

## Graph Links

Every formal page includes:

```md
## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects:
```

Use explicit wikilinks. Do not rely only on YAML for Obsidian graph structure.

## Evidence Priority

For research answers, default priority is:

1. `wiki/synthesis/`
2. `wiki/literature/`
3. `wiki/seminars/`

For project history or decision questions, default priority is:

1. `wiki/project_synthesis/`
2. `wiki/meetings/`

Seminars are useful context, but lower evidence than peer-reviewed literature.
Abstract-only pages cannot be cited as full-read evidence.
