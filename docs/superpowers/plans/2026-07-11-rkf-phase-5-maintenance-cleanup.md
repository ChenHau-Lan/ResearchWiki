# RKF Phase 5 Maintenance And Cleanup Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make periodic RKF maintenance inspectable and safe by default, provide an exact paused-automation proposal without creating it, and generate a read-only cleanup manifest that identifies candidates and their rollback conditions without deleting or archiving anything.

**Architecture:** `rkf/maintenance.py` builds deterministic daily/weekly/monthly plans from existing queue/lint/event state and raw incoming-file metadata; its preview path has no writes and its writer execution path can only run already-governed projections and generated aggregate refreshes with `Promotion: none`. `rkf/cleanup.py` inventories exact candidates, references, risk, and rollback into a local ignored manifest; it contains no delete operation. Automation configuration remains an external Codex-app operation and is represented only by a human-reviewable proposal in this phase.

**Tech Stack:** Python 3 standard library (`dataclasses`, `hashlib`, `json`, `pathlib`, `datetime`), existing RKF runtime/actions/lints, `unittest`, Markdown/JSON.

**Approved Design:** `docs/superpowers/specs/2026-07-10-rkf-1-1-closed-loop-design.md` sections 13–14 and 16–19.

## Global Constraints

- A maintenance plan and cleanup manifest are read-only with respect to canonical wiki/raw state and never promote a stable claim or trusted synthesis.
- Automated execution, if later created, starts a fresh OFF runtime, must activate through normal preflight, and may run only on the designated maintenance writer after a passing doctor report.
- The phase creates no automation through the Codex app; a later user approval must identify target machine, prompt, schedule, and permitted writes before even a paused automation is created.
- Do not reactivate, edit, or delete existing paused automations in this phase; represent them only as exact manifest candidates.
- Cleanup manifests must include exact logical path or automation ID, references, owner, replacement/archive destination, risk, rollback, dry-run result, and approval status.
- The cleanup code has no filesystem deletion, archive, rename, or automation-delete function. Exact apply batches require a later manifest-specific approval.
- Preserve legacy CLI shims, schemas, tests, live wiki/raw PDFs, canonical example screenshots, and Git history.
- No automation creation/activation, live migration, cleanup application, dependency installation, commit, or push is authorized by this plan.

---

## File And Interface Map

- Create `rkf/maintenance.py`: immutable maintenance plan/receipt types, raw incoming metadata scan, cadence-specific checks, explicit no-promotion plan.
- Create `rkf/cleanup.py`: candidate/referrer records and local cleanup-manifest renderer only.
- Modify `rkf/actions.py`: `maintenance.preview` and writer-only `maintenance.run`; `cleanup.manifest.preview` remains read-only/local-report only.
- Create `tests/test_rkf_maintenance.py`: cadence, no-promotion, raw checksum, writer, doctor blocker, and fresh-runtime coverage.
- Create `tests/test_rkf_cleanup.py`: referenced/unreferenced candidates and no-mutation manifest coverage.
- Create `schemas/cleanup_manifest.schema.json`: strict public-safe review manifest vocabulary.
- Create `docs/operations/rkf-maintenance-automation-proposal.md`: uncreated, paused-by-design replacement proposal.
- Modify `docs/PROJECT_MEMORY.md`, `docs/FEATURES_AND_COMMANDS.zh-TW.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`.

---

### Task 1: Produce Read-Only Daily, Weekly, And Monthly Maintenance Plans

**Files:**
- Create: `tests/test_rkf_maintenance.py`
- Create: `rkf/maintenance.py`

**Interfaces:**
- Produces `MaintenancePlan`, `scan_incoming_artifacts(raw_root: Path) -> list[IncomingArtifact]`, `plan_maintenance(ws: Workspace, *, cadence: str, now: datetime | None = None) -> MaintenancePlan`.

- [ ] **Step 1: Write failing daily-plan and source-safety tests**

```python
before = file_snapshot(self.root)
plan = plan_maintenance(self.workspace, cadence="daily", now=datetime(2026, 7, 11, 8, 0, 0))
self.assertEqual(file_snapshot(self.root), before)
self.assertEqual(plan.promotion, "none")
self.assertEqual(plan.incoming[0].checksum, sha256_file(self.incoming_pdf))
self.assertIn("review source identity", plan.actions[0].reason)
```

- [ ] **Step 2: Run the focused test and verify the planner is absent**

Run: `python3 -m unittest tests.test_rkf_maintenance.RKFMaintenancePlanTests.test_daily_plan_scans_incoming_without_writing`

Expected: `ModuleNotFoundError: No module named 'rkf.maintenance'`.

- [ ] **Step 3: Implement deterministic plan construction**

```python
def plan_maintenance(ws: Workspace, *, cadence: str, now: datetime | None = None) -> MaintenancePlan:
    validate_cadence(cadence)
    return MaintenancePlan(cadence=cadence, promotion="none", incoming=scan_incoming_artifacts(ws.paths.raw_root / "incoming"), actions=build_actions(ws, cadence, now))
```

- [ ] **Step 4: Add weekly/monthly tests**

Weekly plans include lint, link/orphan/duplicate checks, reading queue, stale hot and inbox review. Monthly plans add topic/synthesis/migration/PDF-checksum/cleanup-preview items as proposals rather than mutations.

- [ ] **Step 5: Run all maintenance-plan tests**

Run: `python3 -m unittest tests.test_rkf_maintenance`

Expected: PASS; PDF bytes are only checksummed, never copied or parsed into public content.

### Task 2: Add Controlled Maintenance Action Receipts

**Files:**
- Modify: `tests/test_rkf_maintenance.py`
- Modify: `tests/test_rkf_actions.py`
- Modify: `rkf/maintenance.py`
- Modify: `rkf/actions.py`

**Interfaces:**
- Adds `ActionRequest("maintenance.preview", {"cadence": "weekly"})` and writer-only `ActionRequest("maintenance.run", {"cadence": "daily"})`.
- `maintenance.run` consumes a `DoctorReport` and only calls existing guarded projection/index/view hooks after it is healthy.

- [ ] **Step 1: Write failing guard and no-promotion tests**

```python
blocked = non_writer.execute(ActionRequest(action="maintenance.run", params={"cadence": "daily"}))
self.assertEqual(blocked.payload["error_code"], "RKF_WRITER_REQUIRED")
receipt = writer.execute(ActionRequest(action="maintenance.run", params={"cadence": "daily"}))
self.assertEqual(receipt.payload["promotion"], "none")
```

- [ ] **Step 2: Run the focused test and verify the actions are unsupported**

Run: `python3 -m unittest tests.test_rkf_maintenance.RKFMaintenanceActionTests.test_only_writer_runs_daily_maintenance`

Expected: FAIL with an unsupported action until the dispatch and writer guard are added.

- [ ] **Step 3: Implement preview and gated run paths**

`maintenance.preview` returns the pure plan. `maintenance.run` fails closed on a doctor blocker, uses a fresh plan, folds existing safe events if any, and returns a public-safe receipt with `Promotion: none`.

- [ ] **Step 4: Test a fresh OFF runtime cannot run maintenance before activation**

Run: `python3 -m unittest tests.test_rkf_maintenance.RKFMaintenanceActionTests.test_fresh_runtime_blocks_maintenance_before_activation`

Expected: PASS with `RKF_NOT_ACTIVE` and zero I/O.

### Task 3: Generate a Read-Only Cleanup Manifest

**Files:**
- Create: `tests/test_rkf_cleanup.py`
- Create: `rkf/cleanup.py`
- Create: `schemas/cleanup_manifest.schema.json`

**Interfaces:**
- Produces `CleanupCandidate`, `CleanupManifest`, `inventory_cleanup(root: Path, *, automation_candidates: list[dict[str, str]] | None = None) -> CleanupManifest`, `write_cleanup_manifest(manifest: CleanupManifest, report_root: Path) -> Path`.

- [ ] **Step 1: Write failing referenced-versus-unreferenced tests**

```python
manifest = inventory_cleanup(self.root, automation_candidates=[{"id": "legacy-paused", "status": "PAUSED"}])
duplicate = next(item for item in manifest.entries if item.logical_id == "docs/manuals/assets/duplicate.png")
self.assertEqual(duplicate.approval_status, "pending")
self.assertEqual(duplicate.dry_run, "no-change")
self.assertTrue(any(item.logical_id == "legacy-paused" for item in manifest.entries))
```

- [ ] **Step 2: Run the focused test and verify the cleanup module is absent**

Run: `python3 -m unittest tests.test_rkf_cleanup.RKFCleanupManifestTests.test_manifest_never_deletes_or_archives`

Expected: `ModuleNotFoundError: No module named 'rkf.cleanup'`.

- [ ] **Step 3: Implement inventory-only candidates and reference scanning**

Candidate kinds are `ignored-cache`, `duplicate-asset`, `empty-directory`, `stale-document`, and `paused-automation`. Referenced or protected items are included with `recommended_action: retain`, not silently excluded.

- [ ] **Step 4: Implement private report writing with an explicit no-change dry run**

```python
def write_cleanup_manifest(manifest: CleanupManifest, report_root: Path) -> Path:
    path = report_root / f"cleanup-manifest-{manifest.manifest_hash}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.to_json(), encoding="utf-8")
    return path
```

- [ ] **Step 5: Run all cleanup tests**

Run: `python3 -m unittest tests.test_rkf_cleanup`

Expected: PASS; no manifest method removes, moves, or renames a file.

### Task 4: Expose Cleanup Preview and an Uncreated Automation Proposal

**Files:**
- Modify: `tests/test_rkf_cleanup.py`
- Modify: `rkf/actions.py`
- Create: `docs/operations/rkf-maintenance-automation-proposal.md`
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`

**Interfaces:**
- Adds `ActionRequest("cleanup.manifest.preview")` after activation; its output contains manifest hash/counts and a local report only.

- [ ] **Step 1: Write failing OFF and active cleanup-preview tests**

```python
blocked = fresh.execute(ActionRequest(action="cleanup.manifest.preview"))
self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
result = active.execute(ActionRequest(action="cleanup.manifest.preview"))
self.assertEqual(result.payload["manifest"]["approval_status"], "pending")
```

- [ ] **Step 2: Run the focused test and verify action dispatch is missing**

Run: `python3 -m unittest tests.test_rkf_cleanup.RKFCleanupActionTests.test_preview_requires_activation_and_writes_only_private_report`

Expected: FAIL until action routing exists.

- [ ] **Step 3: Add action dispatch with no apply operation**

Do not add `cleanup.apply` or automation mutation dispatch. The action accepts only explicit local report root and candidate snapshot input used by tests.

- [ ] **Step 4: Write the automation proposal as a review artifact, not an automation**

The proposal recommends a single replacement in `PAUSED` state after later approval, names the designated-writer condition, lists daily/weekly/monthly allowed actions, forbids stable-claim promotion, and lists the exact decisions still required from the user.

- [ ] **Step 5: Run focused action tests**

Run: `python3 -m unittest tests.test_rkf_maintenance tests.test_rkf_cleanup tests.test_rkf_actions`

Expected: PASS.

### Task 5: Document Gates and Run Repository Validation

**Files:**
- Modify: `docs/PROJECT_MEMORY.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Record precise Phase 5–8 boundaries**

Document that a proposal/manifest exists, but no actual recurring automation or cleanup batch is created, enabled, deleted, or archived without the separate approvals named in the design.

- [ ] **Step 2: Run all focused tests and repository validation**

Run:

```bash
python3 -m unittest tests.test_rkf_maintenance tests.test_rkf_cleanup tests.test_rkf_actions
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/rk.py lint --mode all
python3 tools/rk.py topic lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/public_safety_scan.py
git diff --check
```

Expected: all commands pass; any live doctor/view/preview result is described separately and no deletion or automation state change occurred.

## Gates After This Plan

1. To create a paused automation, the user must explicitly approve the target machine, exact prompt, schedule, and allowed writes.
2. To enable it, the user must separately approve activation after a manual dry-run health report.
3. To delete or archive anything, the user must separately approve one exact cleanup manifest batch by hash or item list after reviewing references and rollback information.
