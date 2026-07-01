# RKF Test Contract

Minimum acceptance tests:

- DOI normalization and source ID stability.
- Metadata-only sources can create conservative paper drafts.
- Missing full text marks `fulltext_status: needs-user-pdf` and enters the
  paper queue.
- User-provided PDFs update full-text state without requiring a new acquisition
  checkpoint.
- Legacy acquisition-checkpoint records still load and lint.
- Human feedback updates maturity fields and appends the reading ledger.
- Paper queue and nudge output prioritize user action, low feedback, repeated
  questions, and synthesis-review readiness.
- Stable claims and trusted synthesis still require a locator, human feedback,
  or existing governed source. Explicit blockers prevent promotion until
  reviewed.
- Experimental workspace config path resolution for shared RAW/wiki and private
  artifact roots.
- Topic registry validation.
- Graph export includes source, evidence, topic, knowledge, and maturity edges.
- Graph lint detects dangling source and evidence references.
- ARS handoff lint keeps ARS-derived material as a proposal or review blocker.
- Save refuses accidental overwrites unless update is explicit.
- `world` prints an L0-L3 context capsule with critical facts, active reading,
  claim readiness, contradiction hints, graph links, and validation state.
- `evolve` writes low-risk AI Integration Notes and high-risk blockers.
- `reconcile` detects contradictions and marks them as AI-integrated blockers.
- `challenge` returns counterpoints without creating stable claims.
- `emerge` creates low-maturity synthesis without requiring candidate records.
- Propagation review remains a preview/audit fallback.
- External sandbox capsule states reading maturity and ARS evidence boundaries.
- Active docs do not reference deleted routers or article-text workflow.
- Public safety scan rejects PDFs, article text dumps, local paths, and private
  runtime state.
