# RKF Codex Handoff Bootstrap

Enable Research Knowledge Framework (RKF) mode in this Codex handoff session.

## Workspace

Primary RKF repo:

```text
<RKF_REPO_PATH>
```

First read:

```text
<RKF_REPO_PATH>/prompts/codex_handoff_context.md
```

Follow its reading maturity boundary, public-safe boundary, and save proposal
format.

## Default Mode

You may help search for papers, read legally available PDFs or publisher
artifacts, organize source candidates, create paper reading drafts, and propose
durable research knowledge for RKF.

Use the Codex app RKF workflow, structured RKF actions, or the proposal format
below. Do not bypass the Codex app or structured action boundary. If write
access is unavailable, or the claim boundary is incomplete, do
not edit stable wiki knowledge directly. Return a proposal instead.

For hot-query tracking, request the `hot.record` RKF action or return a short
hot-query proposal. Do not create separate hot-query files or a handoff inbox.

Low-risk direct updates may use `evolve` only when the page will show an AI
Integration Note and conservative maturity. `reconcile` may write blockers for
contradictions; `challenge` is critique only; `emerge` creates low-maturity
synthesis drafts from existing RKF state.

## Reading And Evidence Rules

- Candidates and metadata can create paper drafts, but are not stable claim
  evidence by themselves.
- ARS/deep-research reports are proposals, not evidence by themselves.
- A paper draft must state reading state, full-text status, human feedback
  level, claim readiness, and a reading ledger reference.
- When full text is unavailable, mark `fulltext_status: needs-user-pdf` and ask
  the user for the PDF.
- Do not promote stable claims or trusted synthesis without a locator, human
  feedback, or existing governed source. Explicit review blockers preserve the
  boundary and prevent promotion until reviewed.
- Do not save PDFs, full article text, browser captures, private Drive paths,
  tokens, or local secrets.
- Do not put raw chat transcripts, private paths, PDFs, browser captures, or
  full article text into `hot.md` or hot-query events.
- Temporary PDF text or OCR may be used for reading, but full text must not be
  committed to RKF.

## Proposal Fallback

Return a proposal when:

- topic fit is unclear
- there are only search results and no source record yet
- full text is unavailable and the user needs to provide a PDF
- reading maturity is too low for a stable claim
- locators are insufficient
- claim support is unclear
- you cannot write to the RKF repo

Proposal format:

```yaml
target_layer: paper | question | concept | claim | synthesis | topic | review
title: short title
doi_or_url: DOI or URL if available
topic_fit: existing topic id or new topic proposal
reading_state: metadata-only | abstract-read | partial-fulltext | fulltext-read | human-reviewed | blocked
fulltext_status: unknown | needs-user-pdf | user-pdf-provided | publisher-html | publisher-pdf | open-access-pdf | partial-only | fulltext-read | unavailable | blocked
human_feedback_level: none | skimmed | discussed | annotated | trusted
evidence_boundary: metadata-only | locator available | existing RKF page | human-reviewed | review blocker
confidence: low | medium | high | mixed
recommended_rkf_mode: capture | acquire | verify-pdf | distill | paper-feedback | save | review | synthesize | evolve | reconcile | challenge | emerge
reason_to_save: one sentence
hot_query: optional short public-safe question to record in hot.md
notes: short notes only; no full article text
```

## Validation

After RKF writes, ask the host Codex app to run the smallest relevant
verification: tests for changed code, RKF lint for changed knowledge, and the
public-safety scan before sharing or publishing. Report any skipped checks.
