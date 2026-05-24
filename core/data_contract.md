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
- `wiki/questions/`: open research questions, hypotheses, and answer drafts
  that still need evidence tracking.
- `wiki/concepts/`: promoted concept pages for recurring methods, mechanisms,
  datasets, instruments, models, or variables.
- `wiki/topics/`: topic governance pages and the canonical topic registry.
- `wiki/synthesis/`: cross-literature research judgment.
- `wiki/purpose.md`: user-facing purpose and boundary page derived from
  `core/purpose.md`.
- `wiki/overview.md`: map-of-content page for the compiled research state.
- `wiki/hot.md`: active questions and high-priority review map.
- `wiki/meetings/`: meeting records.
- `wiki/project_synthesis/`: project history and decision synthesis.
- `wiki/seminars/`: seminar and talk notes.
- `maintenance/`: repair, support, release, test, and handoff artifacts.
- `maintenance/log.md`: concise append-only human-readable runtime log.
- `maintenance/review_queue.md`: uncertain, conflicting, low-confidence, or
  potentially superseding knowledge items awaiting review.
- `maintenance/fanout_candidates.md`: deterministic source-impact candidates
  that have not yet become review queue items or formal wiki edits.
- `maintenance/state.json`: generated runtime state for dirty/needs-review
  tracking.
- `maintenance/graph.json`: generated knowledge graph export from frontmatter
  and wikilinks; it is not the Obsidian view config.
- `maintenance/thesis_runs/`: thesis-mode research runs with stance evidence,
  evidence tables, verdict proposals, and Save/review recommendations.

## Pipeline Skill Mapping

Research Wiki v2 keeps the same data layers but routes user operations through
pipeline skills and modes:

- `source-intake`: writes source pointers, DOI dashboard state, DOI PDFs,
  staging when explicitly legacy/import-labeled, QCed `raw/full_text/`, and
  full-text indexes.
- `literature-discovery`: runs topic/DOI/URL search, legal-source candidate
  discovery, acquisition checkpoints, and screenshot-assisted source review.
- `paper-ingest`: reads QCed `raw/full_text/` and writes one
  `wiki/literature/` paper page.
- `topic-governance`: owns topic IDs, aliases, scope rules, default search
  strings, canonical pages, and review cadence.
- `knowledge-workbench`: reads existing knowledge, saves source-backed answers
  to the chosen target layer, or writes uncertainty to
  `maintenance/review_queue.md`.
- `synthesis-research`: stages and applies reviewed cross-page source impact,
  thesis runs, synthesis starts, and project-synthesis discussion.
- `wiki-lint`: writes generated diagnostics, repair plans, and graph/state
  exports under `maintenance/`. `audit-release` is a compatibility alias for
  advanced support and release maintenance.

Mode permissions, not skill names alone, define whether a run is read-only,
raw-only, maintenance-only, wiki-write, or support/release scoped.

## DOI Status Values

Only these dashboard statuses are valid:

- `new`
- `metadata_ok`
- `candidate_found`
- `pdf_checkpoint_required`
- `pdf_downloaded`
- `full_text_needed`
- `full_text_done`
- `wiki_done`
- `abstract_only`
- `blocked`

Dashboard main board columns are:

```text
Last Name_Year | Journal | DOI | Wiki Status | PDF | Full Text
```

`PDF` and `Full Text` are checkboxes that indicate whether evidence is present.
Longer next actions, blockers, source routes, and path details belong in the
`DOI Notes` section or are derived from actual files and `raw/full_text_index.*`.
The main board no longer tracks `Access Legality` as a separate column.

Status meanings:

- `new`: source pointer exists but has not been resolved.
- `metadata_ok`: title/authors/year/venue/DOI or stable source identity checked.
- `candidate_found`: metadata, DOI, PDF, or legal source candidates exist but
  have not been approved for evidence use.
- `pdf_checkpoint_required`: a candidate PDF, URL, screenshot, or local file
  needs human approval before being treated as evidence.
- `pdf_downloaded`: approved PDF evidence is present in the configured PDF root.
- `full_text_needed`: metadata or PDF evidence exists, but readable QCed full
  text is missing.
- `full_text_done`: QCed `raw/full_text/<paper_file_key>.md` exists.
- `wiki_done`: `wiki/literature/<slug>.md` exists.
- `abstract_only`: only abstract was available; downstream pages must say so.
- `blocked`: source/access/identity problem needs human decision.

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

The `source-intake` pipeline and the thin `ResearchWikiCodex.command` router
must not create new persistent un-QCed staging full text. Staging remains a
supported evidence layer for legacy imports, existing files, and tools that
explicitly label machine extraction as not ready for wiki ingest.

Only Codex-reflowed/QCed Markdown may be written to `raw/full_text/`.
Final full text must use:

- `extraction_status: codex_qc_done`
- `qc_status: codex_qc_done`
- `readability_status: readable`, `readable-with-warnings`, or `poor`
- `equation_quality: good`, `partial`, `poor`, or `not_applicable`
- `table_quality: good`, `partial`, `poor`, or `not_applicable`

`table_quality` separates prose readability from table reliability. Wide,
continued, or numeric tables may be preserved as fenced text with an explicit
warning; numeric table reuse requires checking the PDF, HTML/XML table, or
supplement when `table_quality` is `partial` or `poor`.

DOI comparisons are canonicalized before dashboard work. Duplicate PDF filename
suffixes from publisher downloads, such as Copernicus `...-2005-2.pdf`, must not
create additional DOI rows.

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

Formal wiki pages use YAML frontmatter. Required v1 keys remain valid, and
vNext pages add identity and governance fields when applicable:

```yaml
---
type: paper | question | concept | topic | synthesis | overview | hot | purpose | meeting | project-synthesis | seminar
status: draft | reviewed | needs-verification | deprecated
source_status: peer-reviewed | preprint | dataset | software | talk | personal-note | non-academic
reading_status: metadata-only | abstract-only | skimmed | full-read | reproduced | mixed
review_stage: ai-extracted | human-checked | discussed | integrated | cited
confidence: low | medium | high | mixed | not-applicable
evidence_scope: single-source | cross-source | concept | map | project-history | seminar-context | hypothesis | mixed
evidence_tier: peer-reviewed | preprint | dataset | software | talk | personal-note | raw-source | abstract-only | hypothesis | mixed | not-applicable
claim_status: source-report | provisional | open | map | stable | challenged | superseded | record | needs-literature-check | not-applicable
counter_evidence: required | required-for-stable-claims | required-before-synthesis | tracked-in-linked-pages | missing | not-applicable
source_hash:
source_lines: []
provenance_state: extracted | merged | inferred | ambiguous | authored | not-applicable
review_queue: false
review_priority: low | medium | high
last_reviewed: YYYY-MM-DD
review_due: YYYY-MM-DD
doi:
citation_key:
paper_file_key:
aliases: []
supersedes: []
superseded_by: []
topics: []
subtopics: []
keywords: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
---
```

Support pages may use support metadata, but must not create new content types.

Frontmatter rules:

- Paper pages should include `doi`, `citation_key`, and `paper_file_key` when a
  DOI identity exists. These fields mirror raw evidence identity and make
  machine dispatch stable.
- Synthesis, concept, and project-synthesis pages should include confidence,
  evidence scope, evidence tier, claim status, counter-evidence, review cadence,
  and supersession fields.
- Overview and hot-question pages are navigation pages. They may point to
  claims, queues, and evidence, but they should not become unsourced synthesis.
- `source_hash` and `source_lines` are optional claim-level provenance helpers.
  Use them when a claim needs tighter source pinning than a page-level source
  link can provide.
- `review_queue: true` means the page or claim needs human or semantic-lint
  review before it should be treated as stable knowledge.
- `supersedes` and `superseded_by` preserve research history. Do not erase an
  older interpretation merely because a newer one exists.

## Page Types

- `paper`: a single source only. It records what that paper says and necessary
  source pointers, not cross-paper conclusions.
- `question`: an open research question or hypothesis with current evidence,
  missing evidence, and search plan. It must not masquerade as stable synthesis.
- `concept`: a promoted recurring method, mechanism, dataset, instrument,
  model, variable, or domain concept. It should cite linked papers or synthesis
  pages and avoid becoming an unsourced glossary.
- `topic`: a retrieval and governance page. It defines topic IDs, aliases,
  scope, include/exclude rules, canonical searches, and review cadence.
- `synthesis`: cross-source research judgment, including overview, comparison,
  evidence map, and open-question subtypes.
- `overview`: map-of-content page for the current compiled research state.
- `hot`: active-question and priority review page. It is a routing page, not a
  stable claim page.
- `purpose`: user-facing scope and boundary page.
- `meeting`: one meeting record.
- `project-synthesis`: cross-meeting project history, decisions, and evolution.
- `seminar`: talk or seminar notes, lower evidence tier than literature.

## Source Fan-out

A source may affect multiple knowledge pages, but the default ingest path is
deliberately conservative:

1. Create or update the paper page from QCed full text.
2. Record candidate concept, synthesis, overview, hot-question, graph, or
   supersession impacts in `maintenance/fanout_candidates.md`.
3. Promote accepted candidates into `maintenance/review_queue.md`.
4. Apply cross-page updates only through an explicit Save, approved fan-out, or
   research action.

Fan-out candidates and proposals must list source page, candidate targets,
supported claims, challenged claims, confidence, counter-evidence needs, and
unresolved review needs. Candidates are not stable evidence.

## Storage And Sync

ResearchWiki separates version control from large research evidence:

- Git stores repo rules, docs, scripts, tests, public-safe indexes, templates,
  and wiki Markdown that is safe to publish.
- Google Drive for desktop stores real PDFs, attachments, large raw files, and
  other machine-specific research data under one shared root such as
  `Google Drive/My Drive/ResearchSync/`.
- `researchwiki.config.toml` maps each computer to its local Drive root and is
  ignored by Git. `researchwiki.config.example.toml` is the committed template.
- Local symlinks or junctions may preserve old paths on a single computer, but
  they are never the cross-platform source of truth.
- `raw/doi_pdf` is the canonical repo-relative name. Legacy `RAW/DOI_PDF` may
  be recognized by tools as an import/compatibility path, but new docs and
  generated paths use lowercase.

## Acquisition Gates

Automated discovery may find metadata, legal candidates, PDF URLs, screenshots,
or local files, but the chain to wiki is gated:

1. Metadata or search candidates may set `candidate_found`.
2. Candidate PDFs or browser/screenshot evidence must set
   `pdf_checkpoint_required` until a human approves the route.
3. Approved PDFs may set `pdf_downloaded`.
4. Only Codex-reflowed or human-QCed full text may enter `raw/full_text/`.
5. `paper-ingest` must reject metadata-only and un-QCed extraction. It may only
   create an abstract-limited page when explicitly marked `abstract_only`.

## Claim Governance

Important synthesis claims should record:

- evidence tier: peer-reviewed full-read, abstract-only, seminar-context, raw
  source, personal-note, or hypothesis;
- evidence links: explicit wiki links or raw source pointers;
- confidence: low, medium, high, or mixed;
- counter-evidence or missing evidence;
- supersession relationship when the claim replaces an older interpretation.

Claims supported by only one source, abstract-only material, seminar context, or
unverified extraction must not be marked high confidence.

## Thesis Runs

Thesis review is used for high-risk research claims that need counter-evidence
before they affect synthesis. A thesis run lives under
`maintenance/thesis_runs/<date>_<slug>/` and contains:

- `thesis.md`: claim, variables, predictions, and falsification criteria;
- `supporting.md`: evidence supporting the thesis;
- `opposing.md`: evidence against or limiting the thesis;
- `mechanistic.md`: mechanism and causal-path evidence;
- `meta_review.md`: review, meta-analysis, consensus, or field-level evidence;
- `adjacent.md`: adjacent-domain evidence and analogies;
- `evidence_table.md`: compact source/evidence comparison;
- `verdict.md`: verdict proposal and Save/review recommendation.

Allowed verdicts are `supported`, `partially supported`, `contradicted`,
`insufficient evidence`, and `mixed`. Thesis runs are maintenance artifacts, not
formal wiki knowledge. They may propose Save or review-queue actions but must not
directly update formal wiki pages.

## Graph Links

Every formal page includes:

```md
## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related concepts:
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
