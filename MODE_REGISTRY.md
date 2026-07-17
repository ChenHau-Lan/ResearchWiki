# RKF v1 Workflow Registry

RKF exposes five research workflows plus a task-scoped Connect & Activate
layer. Internal helpers are implementation details, not parallel user modes.

| User workflow | Structured action | Writes | Evidence boundary |
|---|---|---:|---|
| Connect & Activate | `rkf.activate`, `rkf.status`, `rkf.deactivate`, `connect.validate` | lineage only | every task starts OFF; only direct activation consent permits `rkf.activate`; status summarizes open projects without paths; raw prompts are excluded |
| Add | `workflow.add` | event, inbox/source projection | candidates and metadata are not stable evidence |
| Ask | `workflow.ask` | action lineage only | governed source context may be shown without a locator; claim support requires exact Evidence |
| Read | `workflow.read` | FindingDraft or canonical Evidence | drafts may have missing/coarse locators; Evidence still requires exact locator and explicit verification |
| Compare & Synthesize | `workflow.compare-synthesize` | Claim or Synthesis | verified claims require human-verified evidence |
| Review | `workflow.review` | action lineage only | actionable gaps and project activity; no trust promotion |

## Routing

- DOI, URL, PDF pointer, note or selected search result → Add.
- Question over papers/topics → Ask; distinguish source context from
  locator-backed, claim-ready support.
- Annotation, correction, locator or verification → Read.
- Claim comparison, contradiction, gap or conclusion → Compare & Synthesize.
- Reading queue, missing locators, pending verification or project timeline → Review.
- External project access → preview/apply `connect-project`, then explicitly
  activate in each Codex task.
- A workflow request while OFF → `RKF_NOT_ACTIVE`; never infer activation
  consent, change connection state, or perform RKF research-data I/O.
- An Ask request while OFF → include `是否要「啟動 RKF」？` and wait for an
  explicit answer without activating automatically.

## Invariants

1. Paper → source context → FindingDraft → exact-locator Evidence →
   human-reviewed Claim → Synthesis.
2. `project_id` is stored in the v2 marker and is not an absolute path.
3. Each activation has a unique `activation_id`; each action has an append-only,
   idempotent ActionEvent.
4. Raw prompts, secrets, PDFs, article text and private paths are not lineage.
5. Exact/deterministic retrieval precedes optional semantic retrieval.
6. Provider success never upgrades evidence or claim trust.
7. A locator is a promotion gate for formal Evidence and supported claims, not
   an entry gate for Add or source-context Ask results.

## Installation profiles

- `core` validates the local framework; the connector and Codex skill are
  optional.
- `codex` validates the natural-language/cross-project integration; a missing or
  stale connector or skill blocks readiness.
- Both diagnostics return a boolean `ready`, the string `status`, and the
  selected `profile`. The zero-network two-paper smoke test is
  `python3 tools/demo_quickstart.py --check`.

The deprecated action taxonomy is inventoried in
`docs/V1_SCOPE_INVENTORY.md`. Compatibility code is not part of the app-facing
registry and has an explicit removal target.
