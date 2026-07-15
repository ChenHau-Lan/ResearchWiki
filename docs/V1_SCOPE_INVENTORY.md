# RKF v1 Scope Inventory

The canonical, reviewable inventory is
[`docs/operations/v1-scope-inventory.yaml`](operations/v1-scope-inventory.yaml).
It is a JSON-compatible YAML 1.2 document so the standard Python `json` module
can validate it without adding a runtime dependency.

Every entry uses exactly one Phase 0 classification:

- `keep` — remains part of the v1 contract or an essential internal invariant.
- `merge` — behavior remains, but only under a target workflow or internal
  service; it is not a parallel product entry.
- `delete` — remove the runtime, prompt, template, test, or document after its
  stated dependency is cleared.
- `temporary-shim` — compatibility-only and required to name a removal version.

The inventory records current name/path, target workflow or service, migration
impact, test/docs impact, removal version, owner, and follow-up issue. CI checks
that every action returned by `rkf.actions.available_actions()` is classified,
that the visible workflow set is exact, and that no shim lacks a removal target.

## Frozen v1 surface

The only visible research workflows are Add, Ask, Read, Compare & Synthesize,
and Review. Connect & Activate is the one access layer. Graph/index/handoff and
static-site behavior are internal services. Intake helpers merge into Add;
critique/synthesis passes merge into Compare & Synthesize; queue/status/quality
projections merge into Review.

Cross-project connection, stable project/activation/action lineage, event-first
capture, idempotency, and public/private safety checks are explicitly retained.
Multi-computer synchronization is a separate deleted product and must not be
confused with cross-project connection.

Branch retention and deletion evidence is recorded separately in
[`docs/operations/v1-branch-audit.md`](operations/v1-branch-audit.md).
