---
type: method
status: draft
source_status: personal-note
reading_status: mixed
review_stage: discussed
topics: [synthesis]
keywords: [llm_wiki, research_workflow, scheduled_search, search_ingest, question_log]
created: 2026-05-18
updated: 2026-05-18
sources: [AGENTS.md, research_records]
---

# Research Wiki Operating Manual

## Current Use Pattern

This wiki now works best as a research memory system with five separate layers:

- `raw/`: immutable evidence and search traces.
- `references.bib`: canonical citation registry.
- `wiki/literature/`: paper pages, one page per source.
- `wiki/synthesis/`: cross-paper reasoning and research judgment.
- `wiki/research_records/`: per-session question logs and search ingest records.

The useful habit is to keep each thinking object in the right layer:

- A question goes into a question record.
- A search goes into a search ingest record and raw log.
- A paper goes into a paper page.
- A cross-paper answer goes into a synthesis page.
- A reusable definition goes into a concept page.

## What Has Been Working

- Splitting paper facts from synthesis prevents single-paper pages from accumulating untraceable opinions.
- `reading_status` protects against pretending that abstract-only sources have been fully read.
- `review_stage` separates AI extraction from human-checked or discussed understanding.
- `topics` as broad directions and `keywords` as fine-grained mechanisms keeps Obsidian graph usable.
- Research records make each search/question session recoverable.

## Improvements Needed

### 1. Make Every Research Session Traceable

Every search or deep answer should create:

- `wiki/research_records/search_ingest_<topic>_<YYYY-MM-DD>.md`
- `wiki/research_records/questions_<topic>_<YYYY-MM-DD>.md`

If one user request has two themes, split it into two records. A bridge synthesis page can exist, but each theme should have its own question and search record.

### 2. Add Scheduled Search Workflows

Use scheduled searches to keep the wiki alive without turning it into a dumping ground.

Recommended cadence:

| Cadence | Purpose | Output |
|---|---|---|
| Weekly | New papers from target journals and alerts | search ingest record + candidate queue |
| Monthly | Upgrade top candidate papers to paper pages | paper pages + synthesis updates |
| Quarterly | Re-read synthesis pages for gaps and contradictions | lint-wiki report + follow-up questions |

Target journals for atmospheric research:

- Geoscientific Model Development
- Atmospheric Chemistry and Physics
- Atmospheric Measurement Techniques
- Journal of the Atmospheric Sciences
- Monthly Weather Review
- Journal of Climate
- Journal of Geophysical Research: Atmospheres
- Geophysical Research Letters
- Atmospheric Environment
- Atmospheric Research
- Bulletin of the American Meteorological Society

### 3. Use Search Tiers

Do not ingest everything found.

| Tier | Meaning | Action |
|---|---|---|
| Tier 1 | Directly answers active research question | create paper page, update synthesis |
| Tier 2 | Useful background or method reference | add to candidate queue or keyword page |
| Tier 3 | Interesting but peripheral | log in search record only |
| Reject | Not relevant, weak source, duplicate, or inaccessible | log rejection reason |

### 4. Keep Paper Pages Conservative

Paper pages should contain:

- What the paper itself says.
- Metadata and citation verification.
- Reading limitation.
- Citable claims with evidence.
- Personal notes only under `My Notes on This Paper`.

Do not write cross-paper conclusions inside a paper page.

### 5. Upgrade Sources Deliberately

A paper page can move through:

- `metadata-only`
- `abstract-only`
- `skimmed`
- `full-read`
- `reproduced`

And through:

- `ai-extracted`
- `human-checked`
- `discussed`
- `integrated`
- `cited`

For formal writing, prioritize `full-read + human-checked` or better.

## Scheduled Search Workflow

### weekly-search

1. Pick 1-3 active synthesis pages.
2. Read their `Open Questions`.
3. Search target journals and citation databases with focused queries.
4. Save raw search log under `raw/literature_search/`.
5. Create a `search_ingest_*` record.
6. Add only Tier 1 papers as paper pages.
7. Add Tier 2 papers to a candidate queue.
8. Update synthesis pages only with clearly sourced claims.
9. Append `wiki/log.md`.

### monthly-upgrade

1. Read recent search ingest records.
2. Pick top candidates by relevance.
3. Verify DOI, venue, authors, and source status.
4. Upgrade paper pages from `abstract-only` to `skimmed` or `full-read`.
5. Add citable claims.
6. Update synthesis pages.
7. Update question records with answer status.

### quarterly-lint

1. Check citation consistency with `references.bib`.
2. Check paper pages missing required template sections.
3. Check synthesis claims without evidence links.
4. Check stale `needs_triage` and `needs_subkeyword`.
5. Check whether keyword pages need promotion to concept or synthesis pages.
6. Produce a lint report and append `wiki/log.md`.

## Skill Improvements

The current `academic-researcher` skill is useful for source integrity, but this project needs a narrower local skill:

`research-wiki-curator`

Suggested responsibilities:

- Enforce paper/code/synthesis boundaries.
- Create question records and search ingest records automatically.
- Maintain `references.bib`.
- Maintain topic registry and keyword pages.
- Run paper template audits.
- Run scheduled search workflows.
- Keep synthesis pages evidence-linked.

Suggested triggers:

- "search and ingest"
- "定時搜尋"
- "補充知識庫"
- "回答研究問題"
- "整理文獻"
- "更新 synthesis"

## MD Structure Improvements

Recommended additions:

- `templates/search-ingest.md`
- `templates/question-record.md`
- `wiki/research_records/research_records.md`
- `wiki/concepts/research_wiki_operating_manual.md`
- optional: `wiki/literature/candidate_queue.md`
- optional: `wiki/literature/full_read_queue.md`
- optional: `wiki/lint/`

## Working Rule

Every serious research answer should leave behind three traces:

1. What was asked.
2. What was searched or ingested.
3. What synthesis changed.

If any one of those is missing, the answer may be useful in the moment but weak as a long-term research wiki contribution.
