# RKF Data Contract

## Objects

- `SourceRecord`: source candidate, resolved identity, and current reading
  route.
- `EvidenceArtifact`: private PDF or related artifact pointer plus public-safe
  provenance.
- `KnowledgeObject`: maintained Markdown page with an explicit evidence or
  maturity boundary.
- `ReadingLedger`: public-safe operational memory for reading events, user
  questions, AI answers, human corrections, annotations, trust changes, and open
  blockers.
- `Topic`: governed research scope.
- `GateDecision`: legacy route notes, claim-support checks, synthesis review,
  public-safety checks, or repair plans.
- `GraphEdge`: typed relation among sources, evidence, topics, reading state,
  and wiki pages.
- `HotQueryEvent`: public-safe query/search demand signal stored in `hot.md`;
  not evidence.
- `AI Integration Note`: page-local audit note for direct AI rewrites,
  reconciliation blockers, and low-maturity generated context.

## Source Status

Current statuses:

- `new`
- `metadata_ok`
- `candidate_found`
- `paper_draft`
- `needs_user_pdf`
- `fulltext_available`
- `reading_in_progress`
- `reading_mature`
- `pdf_downloaded`
- `pdf_qc_needed`
- `pdf_qc_done`
- `wiki_done`
- `abstract_only`
- `blocked`

Legacy compatibility:

- `pdf_checkpoint_required`

The legacy status may appear in old records and lint should not break on it, but
new normal flows should prefer `needs_user_pdf`, `fulltext_available`, and
reading maturity fields.

## Reading Maturity Fields

Paper pages and source records may carry:

- `reading_state`: `metadata-only`, `abstract-read`, `partial-fulltext`,
  `fulltext-available`, `fulltext-read`, `human-reviewed`, `synthesis-ready`,
  or `blocked`.
- `fulltext_status`: `unknown`, `needs-user-pdf`, `user-pdf-provided`,
  `publisher-html`, `publisher-pdf`, `open-access-pdf`, `partial-only`,
  `fulltext-read`, `unavailable`, or `blocked`.
- `human_feedback_level`: `none`, `skimmed`, `discussed`, `annotated`, or
  `trusted`.
- `understanding_confidence`: `low`, `medium`, `high`, or `mixed`.
- `claim_readiness`: `not-ready`, `locator-needed`, `claim-ready`, or
  `synthesis-ready`.
- `last_reading_interaction`
- `reading_ledger`

Synthesis pages may carry:

- `synthesis_maturity`: `draft`, `single-source`, `multi-source`,
  `human-reviewed`, or `publication-ready`.
- `source_coverage`: `unknown`, `partial`, `representative`, or
  `systematic`.
- `human_feedback_level`
- `claim_readiness`
- `last_synthesis_interaction`

Claim and synthesis pages may carry minimal temporal metadata:

- `observed_at`: when RKF recorded or integrated the content.
- `valid_from`: when the described fact or interpretation starts applying.
- `valid_until`: optional expiry or replacement date.
- `supersedes`: optional replaced page, fact, or synthesis.

AI-integrated content may carry:

- `ai_integrated`: true when an AI update rewrote or generated page content.
- `ai_integration_priority`: `low`, `medium`, or `high`.
- `last_ai_integration`

Stable AI-integrated claim or synthesis content must include an AI Integration
Note plus `observed_at` and `valid_from`.

## Knowledge Types

- `paper`
- `question`
- `concept`
- `claim`
- `topic`
- `synthesis`
- `overview`
- `project-synthesis`
- `meeting`
- `seminar`

## Hot Query Event

Stored as short Markdown lines in `hot.md`.

Fields:

- `schema`: `rkf-hot-query-event-v1`
- `event_id`
- `created`
- `origin`: local session or external sandbox
- `intent`: query, discover, paper-search, or proposal
- `query`
- `normalized_query`
- `topic_ids`
- `topic_fit`
- `paper_leads`
- `notes`

Hot-query events must be public-safe. They must not store PDFs, article text,
browser captures, private paths, tokens, or raw chat transcripts.

## Paper Draft Rule

Paper drafts require:

- a `SourceRecord`;
- conservative maturity fields;
- a public-safe `reading_ledger` reference;
- an `evidence_boundary` that states whether the page is metadata-only,
  partial-fulltext, locator-backed, human-reviewed, or blocked.

A draft may be created before full text is available. Missing full text should
set `fulltext_status: needs-user-pdf` and queue the paper for user action.

## Auto-Evolution Rule

`evolve` is the normal low-risk direct update path. It must leave an AI
Integration Note and keep maturity conservative. `reconcile` can add blockers
for contradictions. `challenge` is critique only. `emerge` can create
low-maturity synthesis drafts from existing RKF signals without requiring
candidate records.

## Claim Boundary

Stable claims, trusted synthesis, citation-ready summaries, and publication
exports require at least one of:

- a locator to a governed source or checked artifact;
- human feedback at `discussed`, `annotated`, or `trusted`;
- an existing RKF page that already carries the boundary;
- an explicit `review-blocker` or `locator-needed` note.

Durable article text is not a data layer. Reading ledgers are operational
memory; they are useful maturity signals, but not claim evidence by themselves.
