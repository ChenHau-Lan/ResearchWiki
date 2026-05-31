# RKF Agent Contract

Agents working in RKF must preserve evidence boundaries while turning research
work into governed LLM Wiki memory.

## Allowed Promotion

- Metadata may become a `SourceRecord`.
- Discovery results may become candidates and paper-reading prompts.
- Metadata, abstracts, partial full text, and user-provided PDFs may create or
  update an early `paper` draft when the page records conservative reading
  maturity.
- User PDF handling may update `fulltext_status` and reading state directly;
  older route-note records remain accepted for compatibility.
- PDF/OCR/visual checks may upgrade locator confidence and claim readiness.
- Human questions, corrections, annotations, and trust changes may update a
  public-safe reading ledger and maturity fields.
- Low-risk existing-page updates may use `evolve` when the page records an AI
  Integration Note and conservative maturity.
- `reconcile` may write page-local blockers for contradictions when the output
  is marked as AI integration.
- `challenge` may critique a page using RKF knowledge, but it is not a stable
  claim.
- `emerge` may create low-maturity synthesis drafts from existing RKF state
  without requiring candidate records.
- ARS outputs may become proposals only until RKF review promotes them.
- Topic edits may become review proposals, merge/split suggestions, alias
  updates, or search-string updates.
- External sandbox outputs may become save/review proposals only unless the
  user approves a stable write path.

## Required Refusals

- Do not present metadata-only or partially read paper drafts as stable claims.
- Do not treat candidates, ARS output, AI answers, or ledger events as evidence
  by themselves.
- Do not treat auto-synthesis or challenge output as human-reviewed knowledge.
- Do not create open-web or multimodal ingest pipelines inside RKF; route
  external research expansion through ARS unless a future plan explicitly
  changes this boundary.
- Do not promote stable claims or trusted synthesis without a locator, human
  feedback, existing governed source, or explicit review blocker.
- Do not save durable article text as a knowledge layer.
- Do not paste full article text into public pages.
- Do not commit machine-specific Drive paths, cross-platform links, sandbox
  access tokens, PDFs, browser captures, or local secrets.

## Bridge Rule

When ARS output should influence RKF, produce a proposal with target layer,
evidence boundary, confidence, and recommended RKF mode. Then route through the
appropriate RKF skill. If the result concerns a paper or synthesis, carry over
the reading or synthesis maturity level and the reason it is ready, blocked, or
still only a draft.
