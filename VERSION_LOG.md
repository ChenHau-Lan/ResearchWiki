# Research Wiki Version Log

This file records release-visible Research Wiki changes. It is not a changelog for every commit; it is the map a user can use to understand which version they want to keep using or return to.

## Version Policy

- `v1.x.y`: compatible fixes, guide improvements, advisory tooling, and small behavior clarifications.
- `v1.(x+1).0`: compatible user-visible feature additions.
- `v2.0.0`: breaking changes to data contracts, command semantics, required frontmatter, folder roles, or migration expectations.

## v2.0.0 - Skill-First Pipeline Refactor

Date: 2026-05-24
Baseline branch: `codex/skill-first-pipeline-refactor`
Status: proposed PR baseline for the skill-first workflow model

### What v2.0.0 Changes

- Replaces the old 14-option command-menu mental model with five pipeline
  skills: `source-intake`, `paper-ingest`, `knowledge-workbench`,
  `synthesis-research`, and `wiki-lint`; `audit-release` remains an advanced
  compatibility entrypoint.
- Combines Query and Save under `knowledge-workbench`, with mode-level
  permissions for `query`, `save`, `query-to-save`, and `review-queue`.
- Adds an ARS-style pipeline architecture guide with flow, skill/mode matrix,
  artifacts, write permissions, gates, and data boundaries.
- Downgrades `ResearchWikiCodex.command` to a thin skill/mode router and
  compatibility entrypoint.
- Rewrites README around the skill-first workflow, narrows USER_GUIDE into a
  mode reference, and adds a bilingual Skill-first illustrated quickstart.
- Renders bilingual README PDFs and Skill-first quickstart PDFs under
  `output/pdf/`.
- Converts the old full-ingest walkthrough into a legacy pointer and corrects
  the fan-out apply section so it is not treated as a routine next step.
- Makes `wiki-lint` the public LLM Wiki health-check model: structure lint,
  semantic lint, repair plans, and state/graph diagnostics.
- Adds `maintenance/documentation_cleanup_candidates_2026-05-24.md` with exact
  cleanup candidates for old manuals, old screenshots, and `.DS_Store` files;
  vague bulk deletion remains disallowed.

### Compatibility Notes

- The data model is unchanged: `raw/` is evidence, `wiki/` is knowledge, and
  `maintenance/` is governance.
- Existing command-backed capabilities remain available through skill/mode
  routing, but old option numbers are no longer the primary UI contract.
- Query remains read-only, Save remains deliberate, source fan-out remains
  reviewed, and repair tools still do not delete files automatically.
- If legacy walkthrough files remain, they are compatibility pointers only. New
  users should follow `docs/manuals/research_wiki_skill_first_quickstart.*.md`.
- `audit-release/semantic-audit`, `audit-release/runtime-state-graph`, and
  `audit-release/release-hygiene` continue to map to `wiki-lint` modes.

## v1.0.0 - Research Wiki vNext Baseline

Date: 2026-05-23  
Baseline branch: `origin/codex/vnext-research-compiler-governance` after PR #14  
Status: current stable baseline for the v1 improvement stack

### What v1.0.0 Includes

- Evidence chain: `raw/` for source evidence, `wiki/` for curated knowledge, `maintenance/` for governance/runtime artifacts.
- Four runtime actions: Query, Save, Lint, Research.
- Conservative paper ingest: source -> QCed full text -> paper page; multi-page source impact goes through fan-out candidate/review.
- Frontmatter vNext fields for identity, confidence, evidence tier, counter-evidence, review queue, provenance, and supersession.
- Concept, purpose, overview, hot-question, synthesis, meeting, project-synthesis, seminar, and paper page types.
- Runtime state and graph exports under `maintenance/state.json` and `maintenance/graph.json`.
- Thesis mode scaffolding with supporting, opposing, mechanistic, meta-review, adjacent evidence, evidence table, and verdict proposal.
- Full-ingest bilingual walkthrough manuals demonstrating the visible `pdf_template/` sample set.

### Compatibility Notes

- This version is template-safe: raw PDFs and raw full text are not part of the publishable baseline.
- Query is read-only by contract.
- Save, fan-out apply, semantic lint, thesis mode, and state/graph export are explicit actions.
- Dashboard rows are status views, not the evidence source of truth.

## Updating This File

Add a new entry whenever a PR changes user-visible workflow, command behavior, data contracts, guide structure, or version policy. Keep entries short and link to the relevant PR in the PR body.
