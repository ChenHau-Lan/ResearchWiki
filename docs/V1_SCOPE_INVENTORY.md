# RKF v1 Scope Inventory

This inventory implements the scope decision in GitHub issues #15–#18. The
app-facing registry is `rkf.actions.available_actions()`.

| Surface | Classification | v1 disposition |
|---|---|---|
| `rkf.activate`, `rkf.status`, `rkf.deactivate` | keep | task-scoped activation with project and activation lineage |
| `connect-project`, v2 marker, `RKF/` bridge | keep | central RKF access without copying a wiki |
| `connect.validate` | keep | marker, central availability, version and redaction validation |
| `workflow.add` | keep | DOI, URL, PDF pointer, note and selected-provider intake |
| `workflow.ask` | keep | deterministic retrieval; optional semantic providers follow it |
| `workflow.read` | keep | locator-backed Evidence and human verification |
| `workflow.compare-synthesize` | keep | Claim and Synthesis; review passes are internal options |
| `workflow.review` | keep | research actions, data-quality findings and project activity |
| graph, index, world and handoff helpers | merge | internal retrieval/lineage projections; not app-facing |
| inbox, source and discovery helpers | merge | internal implementation of Add |
| challenge, reconcile, emerge, evolve and propagation | merge | internal Compare & Synthesize passes |
| static site renderer and safety scanner | temporary-shim | maintainer-only through v1.x; removal/replacement target v2.0 |
| paper migration preview/apply/rollback | temporary-shim | internal release recovery through v1.1; remove after backup window |
| discovery run lifecycle | temporary-shim | internal provider compatibility through v1.1; not app-facing |
| legacy CLI | temporary-shim | tests/maintenance only; removal target v2.0 |
| multi-machine writer/sync doctor | delete | replaced by local/cross-project `connect.validate` |
| Obsidian Bases | delete | optional integration may return outside core |
| maintenance planner and cleanup manifest | delete | not part of the research product |
| morning/nightly/weekly/health prompts | delete | no default automation package |
| Hot Query mode/manual `hot.md` truth | delete | action event log is canonical; demand views are derived |
| meeting, seminar and overview object types | delete | use typed Note, Topic or Synthesis |
| editable `CRITICAL_FACTS.md` truth | delete | verified-claim projection only |

## Optional integrations in v1

- `FullTextProvider`: minimal typed result and external adapter boundary. A full
  `paper-fetch` acquisition engine is vNext (#18).
- `AppraisalProvider`: digest/appraisal passes feed Read without becoming new
  modes; discipline-specific profiles are optional.
- `RetrievalProvider`: semantic retrieval follows exact identifier/title and
  deterministic keyword search. It never promotes trust.

No optional provider is required for the deterministic core.
