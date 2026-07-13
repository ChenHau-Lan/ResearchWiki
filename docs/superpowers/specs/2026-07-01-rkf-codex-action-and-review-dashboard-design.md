# RKF Codex Action And Review Dashboard Design

Date: 2026-07-01

## Goal

Make the cleaned-up RKF architecture genuinely Codex app-first by moving the
next optimization layer onto structured `rkf.actions` requests and Codex app
reports, rather than adding new user-facing CLI commands.

The first implementation should give Codex a reliable app-facing runtime for
common RKF state checks and maintenance reports, then expose a compact health
snapshot that tells the user what to review next.

## User-Approved Direction

After the CLI/control-surface cleanup, the earlier P0 ideas still mostly fit,
but their order changes:

- Build on `rkf.actions` first.
- Treat `tools/rk.py` / `rkf/cli.py` as a legacy/dev shim only.
- Keep the user experience inside Codex app natural-language workflows.
- Add review dashboard and stats as Codex app reports, not as a new web UI or
  user-facing CLI surface.
- Defer read-only MCP, multi-format ingest, and larger UI work until the
  structured action surface is stable.

## Scope

In scope for the first implementation:

- Extend `rkf.actions` with report/read actions for existing RKF behavior.
- Keep CLI compatibility by making the legacy shim call the same action helpers
  where practical.
- Add a compact stats/health snapshot suitable for Codex app responses.
- Add tests that exercise the action layer directly, not only the CLI shim.
- Update docs and project memory to make the new app-facing action contract
  durable.

Out of scope for the first implementation:

- New user-facing CLI commands.
- Browser dashboard, hosted UI, or large local web app.
- Read-only MCP server.
- Multi-format private ingest for PDF/DOCX/HTML/CSV.
- Full migration of every write path out of `rkf/cli.py`.
- Any automatic stable-claim promotion or silent maturity upgrade.

## Current Context

RKF now has a clear interaction boundary:

- The Codex app is the user-facing control surface.
- Markdown pages remain the durable artifact layer.
- `rkf.actions` is the intended structured runtime API.
- `tools/rk.py` / `rkf/cli.py` remain for maintenance, tests, and compatibility.

The current action layer is intentionally small. It supports:

- `inbox.capture`
- `hot.record`

Many high-value operations still live mainly in `rkf/cli.py` and lower-level
core helpers, including `world`, `lint`, `paper queue`, `graph`, `index`, and
`codex-handoff`. That creates a risk that future optimizations accidentally
rebuild a CLI-shaped control plane.

## Recommended Approach

Use a staged app-action approach.

First, add structured report actions that wrap existing core behavior and
return `ActionResult` payloads:

- `world.render`
- `paper.queue`
- `lint.run`
- `graph.export`
- `index.generate`
- `codex_handoff.generate`

Second, add a new `stats.snapshot` action that composes a concise health report
from existing data:

- knowledge/source/evidence counts;
- paper queue count and top nudges;
- reading state distribution;
- full-text status distribution;
- claim readiness distribution;
- synthesis maturity distribution;
- hot-query count;
- missing locator or missing human-feedback hints;
- lint/public-safety summary.

Third, keep graph traversal for the next implementation slice:

- `graph.neighbors`
- `graph.paths`
- `graph.page_context`

This keeps the first version focused on a reliable app-facing runtime and the
daily review experience.

## Alternatives Considered

### A. Dashboard First

Build a static HTML or browser dashboard immediately.

This would be visually useful, but it would add another surface before the
runtime boundary is stable. It also risks pulling RKF back toward a product UI
before the Codex app workflow has a strong action API.

### B. MCP First

Expose RKF through a read-only MCP server now.

This is attractive for future agents, but it would freeze the current action
surface too early. MCP should come after core read/report actions and graph
traversal have stable structured results.

### C. Action Layer First

Move common report/read behavior into `rkf.actions`, then add a Codex app health
snapshot.

This is the recommended path. It fits the cleanup direction, improves daily
usefulness quickly, and creates the right base for graph traversal, MCP, and
future dashboards.

## Architecture

### `rkf.actions`

`rkf.actions` remains the app-facing runtime boundary. It should expose small,
named actions with stable input dictionaries and structured payloads.

Each action returns:

- `action`: canonical action name;
- `status`: `ok` or a clear failure status;
- `message`: short human-readable summary;
- `payload`: structured data for Codex app rendering and tests.

Actions should avoid printing and should avoid parsing CLI-shaped argument
objects.

### Core Helpers

Existing RKF behavior should remain in `rkf/core.py` or small dedicated helper
functions. If a CLI command currently contains reusable logic, extract the
logic into core or actions before adding a new action wrapper.

The action layer should not become a second copy of `rkf/cli.py`.

### Legacy CLI Shim

The legacy shim may remain, but it should increasingly delegate to action
helpers for shared behavior. The CLI should not gain new user-facing concepts
for this work.

For compatibility, old tests can still run through `tools/rk.py`, but new
coverage should exercise `rkf.actions` directly.

### Codex App Reports

The first user-facing improvement is a compact review report that Codex can
render in the conversation. It should be dense, public-safe, and action-oriented:

- what changed or exists;
- what needs review;
- what is blocked;
- what should be handled next.

No large dashboard UI is required for this phase.

## Data Flow

For a Codex app request such as "幫我看 RKF 今天最需要處理什麼":

1. Codex routes the request to RKF review/report behavior.
2. Codex builds an `ActionRequest`, for example `stats.snapshot`.
3. `execute_action_request()` dispatches to the matching action helper.
4. The action helper reads existing RKF state through `Workspace` and core
   helpers.
5. The action returns an `ActionResult` with structured counts, findings, and
   recommended next items.
6. Codex renders a concise Traditional Chinese or bilingual report for the user.

For existing CLI validation:

1. The legacy CLI parses arguments.
2. The CLI calls the same action/core helper where practical.
3. Existing CLI output remains deterministic enough for tests and maintenance.

## Error Handling And Safety

Actions should fail closed when state is missing or unsafe:

- If `wiki_root` cannot be resolved, return a clear error instead of guessing.
- If a public-safety lint action finds private paths or article text, mark the
  result as failed or blocked.
- If an action would write, it must preserve the existing maturity and evidence
  boundary rules.
- Report actions must not write unless their action name clearly indicates a
  write, such as `graph.export` or `index.generate`.
- `stats.snapshot` should be read-only.
- `lint.run` should report findings and not silently repair files.

All reports must keep candidates, ARS output, hot queries, and route notes below
the evidence boundary.

## Testing Strategy

Add or expand tests in focused layers:

- `tests/test_rkf_actions.py` for direct action dispatch and payloads.
- Existing CLI tests for compatibility and to ensure the shim still works.
- Snapshot-style assertions for `stats.snapshot` on small temporary workspaces.
- Safety assertions that report actions do not write unexpected files.
- Public-safety checks for generated docs and reports.

Recommended validation before completion:

```bash
python3 -m py_compile tools/rk.py tools/rkf_auto_connect.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/public_safety_scan.py
```

Also request RKF topic lint, all lint, paper queue, and world checks through
the Codex app/internal runtime when runtime behavior changes.

## First Implementation Slice

The first implementation plan should be limited to:

1. Add action helpers and dispatch entries for:
   - `world.render`
   - `paper.queue`
   - `lint.run`
   - `graph.export`
   - `index.generate`
   - `codex_handoff.generate`
2. Add `stats.snapshot`.
3. Make the CLI shim delegate to actions for the report paths where practical.
4. Add direct action tests.
5. Update `docs/ARCHITECTURE.md`, `docs/FEATURES_AND_COMMANDS.zh-TW.md`, and
   `docs/PROJECT_MEMORY.md`.

## Deferred Follow-Ups

After the first slice is stable:

- Add `graph.neighbors`, `graph.paths`, and `graph.page_context`.
- Add paper review cards for quick human feedback updates.
- Consider a read-only MCP server over the stable action/graph context layer.
- Consider private multi-format ingest with strict temporary-text and locator
  boundaries.

## Success Criteria

The design is successful when:

- Codex can answer RKF health/review questions through `rkf.actions` without
  relying on CLI command construction.
- The user can ask for a concise "what should I review next" report.
- Existing validation and CLI compatibility tests still pass.
- New tests prove the action layer returns structured payloads.
- No new user-facing CLI surface is introduced.
- Evidence maturity, public safety, and ARS proposal boundaries remain intact.
