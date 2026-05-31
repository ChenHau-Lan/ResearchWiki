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
  existing governed source, or explicit blocker.
- Experimental workspace config path resolution for shared RAW/wiki and private
  artifact roots.
- Topic registry validation.
- Graph export includes source, evidence, topic, knowledge, and maturity edges.
- Graph lint detects dangling source and evidence references.
- ARS handoff lint keeps ARS-derived material as a proposal or review blocker.
- Save refuses accidental overwrites unless update is explicit.
- Propagation review writes proposal gates without rewriting knowledge pages.
- Workspace status/world prints a compact session bootstrap with maturity
  counts.
- External sandbox capsule states reading maturity and ARS evidence boundaries.
- Active docs do not reference deleted routers or article-text workflow.
- Public safety scan rejects PDFs, article text dumps, local paths, and private
  runtime state.
