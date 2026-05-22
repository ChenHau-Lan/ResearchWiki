---
type: maintenance
status: draft
source_status: personal-note
reading_status: mixed
review_stage: discussed
topics: []
subtopics: []
keywords: [intake_matrix, command_testing]
created: 2026-05-22
updated: 2026-05-22
sources: []
---

# Research Wiki Intake Test Matrix

This matrix records the reset-first scenarios used to verify that paper intake
keeps local/no-token work separate from Codex/LLM work.

## Core Entry Scenarios

| Scenario | Input | Expected Local Result | Expected Next Step |
|---|---|---|---|
| DOI only | DOI in `raw/doi_list.md` or `raw/paper_sources.md` | one dashboard row; no PDF, staging, or full_text | open authorized source or provide PDF |
| DOI through command UI | DOI pasted into `Paper intake -> Add/open paper sources` | source pointer queued; local import creates one dashboard row only | open authorized source or provide PDF |
| DOI + URL | DOI plus DOI URL/article URL/PDF URL in `raw/paper_sources.md` | DOI row deduped; unresolved article/PDF URL stays queued or is noted | local source-page opening or explicit source-resolution fallback |
| Duplicate DOI across queues | same DOI in `raw/doi_list.md`, `raw/paper_sources.md`, and DOI URL form | one dashboard row only; duplicate DOI URL is consumed | open authorized source or provide PDF |
| Open authorized source pages | queued DOI/source pointers | opens or lists only authorized source pages; in test mode it skips opening and never starts Codex | user downloads legal PDF or chooses explicit fallback |
| PDF only | authorized PDF in `raw/doi_pdf/` | DOI row from PDF metadata, canonical PDF rename, staging extraction | Codex reflow/QC staging -> full_text |
| PDF with uppercase `.PDF` extension | authorized PDF in `raw/doi_pdf/` with uppercase extension | imported the same as lowercase PDFs and renamed to canonical `.pdf` | Codex reflow/QC staging -> full_text |
| PDF but no local text extractor | DOI plus authorized PDF in `raw/doi_pdf/`, with PDF text extraction unavailable | PDF evidence is imported/renamed; no staging or full_text is created | install/check extractor or use Codex/manual conversion route |
| DOI + PDF | DOI already queued and matching PDF in `raw/doi_pdf/` | PDF attaches to the row, canonical rename, staging extraction | Codex reflow/QC; then wiki ingest |
| PDF backfill after QCed full text | QCed `raw/full_text/` already exists; matching PDF is added later | PDF attaches to the row and updates `source_pdf`; no staging or Codex starts | wiki ingest, or review if wiki already exists |

## Adjacent Failure Scenarios

| Scenario | Expected Guardrail |
|---|---|
| Duplicate DOI / DOI URL | no duplicate dashboard rows |
| Article URL without DOI | remains queued until DOI/metadata judgment |
| Non-PDF file in `raw/doi_pdf/` | rejected as not a PDF |
| Valid PDF with no DOI | not silently ingested as DOI evidence |
| Queued DOI plus mismatched PDF DOI | PDF creates/updates its own DOI row; it is not forced onto the wrong row |
| QC failure | no `raw/full_text/` file, staging not indexed, dashboard stays `full_text_needed` |
| Pending machine extraction accidentally placed in `raw/full_text/` | lint rejects it, index skips it, wiki ingest ignores it, and reset removes the bad artifact |
| Wiki ingest before QC | no ingest; staging is ignored |
| Explicit source fallback | Codex prompt appears only when the LLM fallback option is selected |

## Commands Under Test

- Local/no-token:
  - `Paper intake -> Add/open paper sources`
  - `Paper intake -> Open authorized source pages`
  - `Paper intake -> Import PDFs + extract staging + rebuild index`
- LLM:
  - `Paper intake -> Codex reflow/QC staging -> full_text`
  - `Paper intake -> Codex source-resolution fallback`
- Wiki:
  - `Ingest QCed full_text to wiki`

## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects: [[project_synthesis/project_synthesis]]
