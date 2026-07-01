# RKF Paper Boundary Design

Date: 2026-06-22

## Goal

Refine RKF v0 so daily paper intake is Markdown-first while still keeping a
thin CLI backend for repeatable agent operations, validation, indexing, and
automation. New paper pages must visibly separate source-grounded literature
notes, reader interpretation, AI-generated inferences, and claim-promotion
work.

## Scope

This design covers the next implementation pass for paper-note boundaries only.
It does not migrate the live Google Drive wiki, move existing user files, add a
web app, or make the CLI the primary user interface.

In scope:

- Update `templates/rkf/paper.md`.
- Update the generated paper body in `rkf/core.py:create_paper_note`.
- Update tests that assert generated paper-page shape.
- Update user-facing documentation to explain the Markdown-first workflow.
- Keep existing maturity fields and evidence gates compatible.

Out of scope:

- Moving or copying the configured `wiki_root` or `raw_root`.
- Reorganizing existing live wiki pages.
- Adding new required schema fields.
- Adding a database, MCP server, browser extension, or hosted UI.
- Replacing the current CLI.

## Design Principles

The Markdown page is the durable artifact. A user should be able to understand
and edit the paper note directly in Obsidian, VS Code, Codex, Finder previews,
or any Markdown viewer.

The CLI is a thin backend. It remains useful for repeatable creation, lint,
index, graph, queue, and automation workflows, but it is not the product
surface the user must operate by hand.

The live personal wiki stays external. `rkf.workspace.toml` resolves operational
`wiki_root`, `raw_root`, and private evidence paths. The repo remains framework,
docs, templates, tests, examples, and public-safe fixtures.

Evidence boundaries stay conservative. Candidates, route notes, hot queries,
ARS outputs, and AI/agent notes can start discussion or proposals, but they do
not become stable claim support without locator-backed evidence, supported wiki
pages, or human feedback. Explicit blockers keep candidates blocked until
reviewed.

## Recommended User Workflow

The normal user-facing workflow is:

1. The user provides a DOI, URL, PDF, or topic lead in natural language.
2. The agent captures or identifies the source and creates or updates a paper
   Markdown page.
3. The paper page is edited in Markdown with separate sections for source
   support, reader interpretation, AI notes, feedback, and claims to promote.
4. The agent or automation runs CLI checks only when useful: `distill paper`,
   `paper queue`, `lint`, `index`, `graph`, or public-safety scans.
5. Mature claims or synthesis are promoted only through the existing RKF
   evidence boundary.

## Paper Page Structure

Generated paper notes should use these sections:

```markdown
## Source Identity

## Reading Maturity

## Source-Grounded Summary

## Extracted Evidence And Locators

## Reader Notes

## AI/Agent Notes

## Questions And Feedback

## Claims To Promote

## Future Agent Retrieval Brief

## Graph Links
```

### Source-Grounded Summary

This section records only what the source itself supports, at the current
reading maturity. It should not contain personal recommendations or broad
research extrapolation.

Default prompts:

- Research question:
- Method/data:
- Key findings:
- Limitations:
- Evidence boundary:

### Extracted Evidence And Locators

This section records locators and support limits. It is where future claim
promotion starts, but not where claims are silently promoted.

Default prompts:

- Locator:
- What the source explicitly supports:
- What it does not support:

### Reader Notes

This section records the user's interpretation, project relevance, and personal
research thinking. It may include subjective judgment if it is clearly labeled
as reader interpretation.

Default prompts:

- My interpretation:
- Why this matters to my project:
- Connections to other RKF pages:

### AI/Agent Notes

This section records AI-generated summaries, unverified inference, and human
check needs. It is explicitly not evidence by itself.

Default prompts:

- Agent-generated summary:
- Unverified inference:
- Needs human check:

### Questions And Feedback

This section records public-safe user questions, human feedback, and blockers.
Detailed interaction history remains in `state/reading/<source_id>.json`.

Default prompts:

- User questions:
- Human feedback:
- Open blockers:

### Claims To Promote

This section lists candidate claims that might become claim pages or synthesis
support after review. Each candidate claim must include a locator or blocker
and a caveat.

Default prompts:

- Claim:
  - Required locator or blocker:
  - Caveat:

## Frontmatter Compatibility

The implementation should keep existing fields:

- `reading_state`
- `fulltext_status`
- `human_feedback_level`
- `understanding_confidence`
- `claim_readiness`
- `reading_ledger`
- `review_stage`
- `evidence_boundary`
- `evidence_tier`
- `evidence_ids`
- `topics`

No new required schema fields are introduced in this pass. The boundary change
is expressed through section conventions first, so existing pages and tests stay
compatible.

## CLI Positioning

The CLI remains available as an agent-safe and automation-safe backend:

- `distill paper <source_id>` creates the structured Markdown paper page.
- `paper queue` and `paper nudge` identify missing PDF, feedback, locator, or
  synthesis-review needs.
- `lint`, `topic lint`, `public_safety_scan.py`, `index`, and `graph` verify or
  regenerate derived state.

The CLI documentation should make clear that users do not need to hand-run
commands for normal paper reading. Agent-driven natural-language workflows may
call CLI commands behind the scenes when repeatability or safety checks matter.

## Documentation Updates

Add a user-facing workflow page:

- `docs/workflows/paper-intake.zh-TW.md`

It should explain:

- how to intake a paper without manually using the CLI;
- where source-grounded notes, reader notes, AI notes, and claims belong;
- when a claim can be promoted;
- how the CLI is used by agents and automation;
- where the live wiki lives relative to the repo.

Update existing docs where needed:

- `docs/FEATURES_AND_COMMANDS.zh-TW.md`: clarify CLI as backend and paper page
  section boundaries.
- `docs/ARCHITECTURE.md`: add the paper-page boundary layer to the layer model
  or boundary rules.
- `docs/PROJECT_MEMORY.md`: record the durable decision that v0 is
  Markdown-first with a thin CLI backend.

## Test Strategy

Focused tests should verify generated Markdown shape without overfitting to
every line:

- metadata-only source creates a paper draft with the new boundary sections;
- un-QCed user PDF creates the same boundary sections while preserving
  `partial-fulltext`, `user-pdf-provided`, and `locator-needed`;
- QCed PDF locator appears in the locator/evidence section and keeps graph
  behavior intact;
- paper feedback still updates frontmatter and reading ledger;
- existing queue, graph, and lint behavior remains compatible.

The smallest expected validation set is:

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
```

If documentation-only edits happen before implementation, a manual read-through
and placeholder scan is sufficient for that intermediate step.

## Risks And Mitigations

Risk: Existing pages keep the older section shape.

Mitigation: The new convention applies to newly generated or intentionally
rewritten paper pages. Existing pages remain valid unless a later migration is
explicitly requested.

Risk: More sections make paper notes feel heavier.

Mitigation: The section prompts are short and optional. Empty bullets are
acceptable for early metadata-only drafts.

Risk: Users may still think the CLI is required.

Mitigation: The workflow documentation should lead with natural-language and
Markdown editing, then describe CLI commands as backend tools.

Risk: AI notes may still be mistaken for evidence.

Mitigation: The AI/Agent Notes section explicitly labels unverified inference,
and the claim-promotion section requires locator or blocker plus caveat.

## Acceptance Criteria

- New generated paper pages contain the boundary sections listed above.
- Existing paper maturity fields and graph behavior continue to work.
- Documentation explains Markdown-first paper intake without manual CLI use.
- No private live wiki paths or personal article text are committed in new
  public docs.
- Tests cover the generated paper-page boundary sections and pass locally.
