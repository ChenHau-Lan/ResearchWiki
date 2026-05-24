---
name: wiki-lint
description: Use when checking Research Wiki health: structure lint, semantic lint, repair plans, and runtime state/graph diagnostics for an LLM Wiki knowledge base.
---

# Wiki Lint

Wiki Lint is the public health-check skill for Research Wiki. It follows the
LLM Wiki pattern: after sources are ingested and knowledge is queried or saved,
lint keeps the compiled wiki coherent.

## Modes

- `structure-lint`: run deterministic local checks for frontmatter, indexes,
  stale paths, unresolved wikilinks, missing Graph Links, orphan pages, and
  dashboard/index drift.
- `semantic-lint`: ask Codex to inspect evidence tiers, stale claims,
  contradictions, missing counter-evidence, supersession candidates, and
  research gaps.
- `repair-plan`: generate a human-readable repair plan. It may recommend exact
  fixes and source leads, but must not delete files.
- `state-graph`: regenerate `maintenance/state.json` and
  `maintenance/graph.json` for diagnostic navigation.
- `support-report`: advanced support mode for redacted support reports.
- `feedback-issue`: advanced support mode for human-confirmed issue drafts.

## Rules

- Lint is advisory by default. Formal wiki edits must happen through
  Knowledge Workbench Save or an approved fan-out mode.
- Structure lint uses local tools first; do not spend LLM context on checks that
  deterministic tooling can perform.
- Semantic lint should return review queue items, source leads, or Save
  proposals rather than silently rewriting claims.
- Repair plans diagnose and suggest; they do not delete files.
- Support and feedback modes must redact local paths, private raw evidence,
  full text, sensitive source batches, and conversation logs.

## Lint Questions

Use Wiki Lint to answer:

- Are links, indexes, frontmatter, and graph sections structurally coherent?
- Are claims stale, contradicted, over-confident, or missing counter-evidence?
- Are there orphan pages or missing cross-references?
- Which source leads should go back to `source-intake`?
- Which uncertain findings should go to `maintenance/review_queue.md`?
