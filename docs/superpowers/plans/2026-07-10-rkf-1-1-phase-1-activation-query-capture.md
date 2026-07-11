# RKF 1.1 Phase 1 Activation, Query, And Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first independently usable RKF 1.1 slice: every Codex task starts with RKF off, explicit activation performs a read-only preflight, activated research work searches central RKF deterministically, and reusable research material enters an event-first, deduplicated capture route.

**Architecture:** Add a session object owned by the app-facing action runtime; no active state is written to disk. Keep deterministic retrieval and capture policy in focused modules, use immutable operational events as the first write, and allow existing inbox/hot projections only when the current machine matches the shared maintenance-writer registry. The global auto-connect skill becomes an instruction and routing client of structured actions, never a CLI write bypass.

**Tech Stack:** Python 3 standard library, `dataclasses`, `enum`, `hashlib`, `json`, `pathlib`, existing RKF `Workspace`/frontmatter/graph helpers, `unittest`, JSON Schema documents, Markdown/TOML documentation.

**Approved Design:** `docs/superpowers/specs/2026-07-10-rkf-1-1-closed-loop-design.md`

## Global Constraints

- Every new action runtime starts `OFF`; active state is memory-only and never becomes a saved default.
- Before activation, only `rkf.activate`, `rkf.status`, and `rkf.deactivate` may run; all other actions return `RKF_NOT_ACTIVE` before wiki/raw I/O.
- Activation preflight is read-only and masks absolute paths, Drive account paths, device names, and private `storage_path` values.
- `query.search` is read-only and deterministic: exact identity, keyword/topic, graph context, then maturity filters; no embeddings in Phase 1.
- `capture.route` is the normal capture entrypoint; it writes an immutable event before any projection and never promotes a stable claim or synthesis.
- Non-writer machines may create uniquely named events but may not directly rewrite SourceRecords, reading ledgers, `hot.md`, indexes, graphs, views, or reports.
- Google Drive `wiki/` remains the only canonical knowledge database; Google Drive `raw/` remains private source storage; local caches remain rebuildable.
- No live 57-paper migration, Obsidian setup, automation creation, cleanup, dependency installation, commit, or push is authorized by this plan.
- Repository instructions override Superpowers' normal commit cadence: end each task with diff review, not a commit. Commit only if the user separately requests it.
- Use TDD for every behavior change: failing focused test, minimal implementation, passing focused test, then broader validation.

## File And Interface Map

- Create `rkf/session.py`: session state machine, project-marker normalization, read-only preflight, masked activation/status receipts.
- Create `rkf/retrieval.py`: deterministic central RKF search and governed result cards.
- Create `rkf/events.py`: immutable operational-event envelope and event-file writer/reader.
- Create `rkf/capture.py`: canonical research relevance classifier, deterministic deduplication, capture-event construction, and projection request.
- Modify `rkf/core.py`: expose `raw_root`, `state/events`, and `state/sync` through `WorkspacePaths`; no session or routing logic enters this file.
- Modify `rkf/actions.py`: add `RKFActionRuntime`, session guards, `query.search`, and `capture.route` dispatch.
- Modify `tools/rkf_auto_connect.py`: normalize v1/v2 markers, build structured activation/query/capture requests, and remove direct execute/write commands.
- Create `schemas/operational_event.schema.json`: define the immutable public-safe event contract.
- Create `schemas/writer_registry.schema.json`: define the opaque single-writer registry consumed by activation preflight.
- Modify `rkf.workspace.example.toml`: document opaque machine identity and writer registry without private paths.
- Modify tests under `tests/`: direct unit and integration coverage; existing action tests must use one activated runtime per test.
- Modify `docs/ARCHITECTURE.md`, `docs/FEATURES_AND_COMMANDS.zh-TW.md`, `docs/workflows/rkf-auto-connect.zh-TW.md`, `docs/PROJECT_MEMORY.md`, and `CHANGELOG.md`: record the delivered contract and verified commands.
- External, separately approved file: `~/.codex/skills/rkf-auto-connect/SKILL.md`; replace legacy CLI writes with explicit session activation and structured action routing.

---

### Task 1: Session State And Read-Only Activation Preflight

**Files:**
- Create: `rkf/session.py`
- Modify: `rkf/core.py:342-425`
- Create: `schemas/writer_registry.schema.json`
- Create: `tests/test_rkf_session.py`

**Interfaces:**
- Consumes: `rkf.core.Workspace`, `rkf.core.load_toml`, `rkf.core.read_json`.
- Produces: `SessionMode`, `SessionState`, `ProjectPolicy`, `new_session()`, `activate_session()`, `deactivate_session()`, `session_receipt()`.

- [ ] **Step 1: Write the failing session-state and preflight tests**

Create `tests/test_rkf_session.py` with these concrete cases:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace
from rkf.session import (
    SessionMode,
    activate_session,
    deactivate_session,
    new_session,
    read_project_policy,
    session_receipt,
)


class RKFSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.wiki = self.root / "wiki"
        self.raw = self.root / "raw"
        self.project = self.root / "project"
        self.wiki.mkdir()
        self.raw.mkdir()
        self.project.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f"wiki_root = \"{self.wiki.as_posix()}\"\n"
            f"raw_root = \"{self.raw.as_posix()}\"\n\n"
            "[machine]\n"
            "id = \"machine-7f3a2c91\"\n"
            "maintenance_writer = false\n\n"
            "[knowledge]\n"
            "schema_version = \"rkf-v1\"\n",
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_session_is_off_and_receipt_contains_no_absolute_paths(self) -> None:
        session = new_session("task-001")

        receipt = session_receipt(session)

        self.assertEqual(session.mode, SessionMode.OFF)
        self.assertEqual(receipt["session_id"], "task-001")
        self.assertEqual(receipt["mode"], "OFF")
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_v1_and_v2_markers_only_mean_available(self) -> None:
        (self.project / ".rkf-connect.toml").write_text(
            "[rkf_auto_connect]\n"
            "enabled = true\n"
            "mode = \"active-aggressive\"\n",
            encoding="utf-8",
        )
        v1 = read_project_policy(self.project)
        (self.project / ".rkf-connect.toml").write_text(
            "version = 2\n\n"
            "[rkf]\n"
            "available = true\n"
            "activation = \"manual\"\n"
            "query_first = true\n"
            "capture_mode = \"active-aggressive\"\n",
            encoding="utf-8",
        )
        v2 = read_project_policy(self.project)

        self.assertTrue(v1.available)
        self.assertEqual(v1.activation, "manual")
        self.assertTrue(v2.available)
        self.assertEqual(v2.activation, "manual")

    def test_activation_is_read_only_and_becomes_active(self) -> None:
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
        session = new_session("task-002")

        receipt = activate_session(session, self.workspace, project_root=self.project)

        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after, before)
        self.assertEqual(session.mode, SessionMode.ACTIVE)
        self.assertEqual(receipt["roots"]["wiki_root"], {"exists": True, "readable": True})
        self.assertEqual(receipt["roots"]["raw_root"], {"exists": True, "readable": True})
        self.assertNotIn(str(self.root), json.dumps(receipt))

    def test_conflict_degrades_to_active_read_only(self) -> None:
        (self.wiki / "paper.sync-conflict.md").write_text("conflict\n", encoding="utf-8")
        session = new_session("task-003")

        receipt = activate_session(session, self.workspace, project_root=self.project)

        self.assertEqual(session.mode, SessionMode.ACTIVE_READ_ONLY)
        self.assertIn("SYNC_CONFLICT", receipt["warnings"])

    def test_missing_raw_root_fails_activation(self) -> None:
        self.raw.rmdir()
        session = new_session("task-004")

        receipt = activate_session(session, self.workspace, project_root=self.project)

        self.assertEqual(session.mode, SessionMode.OFF)
        self.assertEqual(receipt["error_code"], "RKF_PREFLIGHT_FAILED")

    def test_deactivate_clears_active_scope(self) -> None:
        session = new_session("task-005")
        activate_session(session, self.workspace, project_root=self.project)

        receipt = deactivate_session(session)

        self.assertEqual(session.mode, SessionMode.OFF)
        self.assertEqual(receipt["mode"], "OFF")
        self.assertEqual(receipt["writer_role"], "unknown")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and verify the module is missing**

Run:

```bash
python3 -m unittest tests.test_rkf_session
```

Expected: FAIL with `ModuleNotFoundError: No module named 'rkf.session'`.

- [ ] **Step 3: Extend `WorkspacePaths` with raw and operational-state handles**

In `rkf/core.py`, add these fields to `WorkspacePaths`:

```python
    raw_root: Path
    events: Path
    sync_state: Path
```

In `Workspace._paths()`, resolve and return them with this exact logic:

```python
        raw_root = self._configured_path("storage", "raw_root") or self.root / ".rkf_private" / "raw"
        state = wiki_root / "state"
        return WorkspacePaths(
            root=self.root,
            wiki_root=wiki_root,
            raw_root=raw_root,
            critical_facts=wiki_root / "CRITICAL_FACTS.md",
            index=wiki_root / "index.md",
            log=wiki_root / "log.md",
            hot_md=wiki_root / "hot.md",
            state=state,
            sources=state / "sources",
            evidence_index=state / "evidence",
            gates=state / "gates",
            reading=state / "reading",
            search_runs=state / "search_runs",
            events=state / "events",
            sync_state=state / "sync",
            knowledge=wiki_root / "knowledge",
            governance=wiki_root / "governance",
            graph=wiki_root / "graph",
            prompts=self.root / "prompts",
            private_evidence=private_evidence,
        )
```

Add `self.paths.events` and `self.paths.sync_state` to `ensure_base()` only so existing write workflows can create them; activation must never call `ensure_base()`.

- [ ] **Step 4: Add the opaque writer-registry schema**

Create `schemas/writer_registry.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/rkf/writer_registry.schema.json",
  "title": "RKFWriterRegistry",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema", "machine_id", "assigned_at"],
  "properties": {
    "schema": {"const": "rkf-writer-registry-v1"},
    "machine_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
    "assigned_at": {"type": "string", "format": "date-time"}
  }
}
```

- [ ] **Step 5: Implement the session model and masked preflight**

Create `rkf/session.py` with these public types and functions:

```python
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .core import Workspace, load_toml, read_json


SUPPORTED_SCHEMA_VERSIONS = {"", "rkf-v1", "rkf-v1.1"}
CONFLICT_NAME_RE = re.compile(r"conflicted copy|conflict copy|sync-conflict|\.sync-conflict", re.IGNORECASE)


class SessionMode(str, Enum):
    OFF = "OFF"
    PREFLIGHT = "PREFLIGHT"
    ACTIVE = "ACTIVE"
    ACTIVE_READ_ONLY = "ACTIVE_READ_ONLY"


@dataclass(frozen=True)
class ProjectPolicy:
    version: int
    available: bool
    activation: str
    query_first: bool
    capture_mode: str


@dataclass
class SessionState:
    session_id: str
    mode: SessionMode = SessionMode.OFF
    query_first: bool = False
    capture_mode: str = "off"
    machine_id: str = ""
    writer_role: str = "unknown"
    warnings: list[str] = field(default_factory=list)


def new_session(session_id: str = "") -> SessionState:
    return SessionState(session_id=session_id or f"task-{uuid.uuid4().hex[:12]}")


def read_project_policy(project_root: Path | None) -> ProjectPolicy:
    if project_root is None:
        return ProjectPolicy(0, True, "manual", True, "active-aggressive")
    marker = project_root / ".rkf-connect.toml"
    data = load_toml(marker)
    if not data:
        return ProjectPolicy(0, True, "manual", True, "active-aggressive")
    version = int(data.get("version", 1))
    if version >= 2:
        section = data.get("rkf", {})
        return ProjectPolicy(
            version=version,
            available=bool(section.get("available", False)),
            activation=str(section.get("activation", "manual")),
            query_first=bool(section.get("query_first", True)),
            capture_mode=str(section.get("capture_mode", "active-aggressive")),
        )
    legacy = data.get("rkf_auto_connect", {})
    return ProjectPolicy(
        version=1,
        available=bool(legacy.get("enabled", False)),
        activation="manual",
        query_first=True,
        capture_mode=str(legacy.get("mode", "active-aggressive")),
    )


def _root_status(path: Path) -> dict[str, bool]:
    return {"exists": path.exists(), "readable": path.exists() and os.access(path, os.R_OK)}


def _conflicts(wiki_root: Path) -> list[str]:
    if not wiki_root.exists():
        return []
    return [path.name for path in wiki_root.rglob("*") if path.is_file() and CONFLICT_NAME_RE.search(path.name)]


def _machine_state(ws: Workspace) -> tuple[str, bool]:
    section = ws.config.get("machine", {}) if isinstance(ws.config, dict) else {}
    if not isinstance(section, dict):
        return "", False
    return str(section.get("id", "")).strip(), bool(section.get("maintenance_writer", False))


def _writer_role(ws: Workspace, machine_id: str, requested_writer: bool) -> str:
    registry_path = ws.paths.sync_state / "maintenance-writer.json"
    if not registry_path.exists():
        return "unregistered"
    registry = read_json(registry_path)
    if registry.get("schema") != "rkf-writer-registry-v1" or not registry.get("assigned_at"):
        return "conflict"
    registered = str(registry.get("machine_id", ""))
    if requested_writer and registered == machine_id:
        return "designated"
    if requested_writer and registered != machine_id:
        return "conflict"
    return "other"


def session_receipt(session: SessionState) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "mode": session.mode.value,
        "query_first": session.query_first,
        "capture_mode": session.capture_mode,
        "writer_role": session.writer_role,
        "warnings": list(session.warnings),
    }


def activate_session(session: SessionState, ws: Workspace, *, project_root: Path | None = None) -> dict[str, Any]:
    session.mode = SessionMode.PREFLIGHT
    policy = read_project_policy(project_root)
    if not policy.available:
        session.mode = SessionMode.OFF
        return {**session_receipt(session), "error_code": "RKF_PROJECT_UNAVAILABLE"}
    roots = {"wiki_root": _root_status(ws.paths.wiki_root), "raw_root": _root_status(ws.paths.raw_root)}
    if not all(value["exists"] and value["readable"] for value in roots.values()):
        session.mode = SessionMode.OFF
        return {**session_receipt(session), "roots": roots, "error_code": "RKF_PREFLIGHT_FAILED"}

    machine_id, requested_writer = _machine_state(ws)
    schema = str(ws.config.get("knowledge", {}).get("schema_version", ""))
    warnings: list[str] = []
    if not machine_id:
        warnings.append("MACHINE_ID_MISSING")
    conflicts = _conflicts(ws.paths.wiki_root)
    if conflicts:
        warnings.append("SYNC_CONFLICT")
    if schema not in SUPPORTED_SCHEMA_VERSIONS:
        warnings.append("SCHEMA_INCOMPATIBLE")

    session.query_first = policy.query_first
    session.capture_mode = policy.capture_mode
    session.machine_id = machine_id
    session.writer_role = _writer_role(ws, machine_id, requested_writer) if machine_id else "unknown"
    if session.writer_role == "conflict":
        warnings.append("WRITER_REGISTRY_MISMATCH")
    session.warnings = warnings
    blocking_read_only = {"MACHINE_ID_MISSING", "SYNC_CONFLICT", "SCHEMA_INCOMPATIBLE", "WRITER_REGISTRY_MISMATCH"}
    session.mode = SessionMode.ACTIVE_READ_ONLY if blocking_read_only.intersection(warnings) else SessionMode.ACTIVE
    return {**session_receipt(session), "roots": roots, "project_available": policy.available}


def deactivate_session(session: SessionState) -> dict[str, Any]:
    session.mode = SessionMode.OFF
    session.query_first = False
    session.capture_mode = "off"
    session.machine_id = ""
    session.writer_role = "unknown"
    session.warnings = []
    return session_receipt(session)
```

- [ ] **Step 6: Run focused tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_rkf_session
```

Expected: `Ran 6 tests` and `OK`.

- [ ] **Step 7: Review Task 1 scope without committing**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only `rkf/core.py`, `rkf/session.py`, `schemas/writer_registry.schema.json`, and `tests/test_rkf_session.py` are changed for this task.

---

### Task 2: App-Facing Runtime Guard And Control Actions

**Files:**
- Modify: `rkf/actions.py:1-455`
- Modify: `tests/test_rkf_actions.py:1-270`

**Interfaces:**
- Consumes: Task 1 `SessionState`, `SessionMode`, `activate_session()`, `deactivate_session()`, `session_receipt()`.
- Produces: `RKFActionRuntime.execute(request) -> ActionResult`; guarded compatibility wrapper `execute_action_request(request, *, workspace=None, runtime=None)`.

- [ ] **Step 1: Add failing runtime-guard tests**

Add these imports and tests to `tests/test_rkf_actions.py`:

```python
from rkf.actions import ActionRequest, RKFActionRuntime, execute_action_request


def test_new_runtime_blocks_all_non_control_actions_before_io(self) -> None:
    runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
    before = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())

    result = runtime.execute(ActionRequest(action="world.render"))

    after = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
    self.assertEqual(after, before)
    self.assertEqual(result.status, "blocked")
    self.assertEqual(result.payload["error_code"], "RKF_NOT_ACTIVE")


def test_activate_status_and_deactivate_share_one_runtime(self) -> None:
    runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root, session_id="task-actions")

    activated = runtime.execute(ActionRequest(action="rkf.activate"))
    status = runtime.execute(ActionRequest(action="rkf.status"))
    deactivated = runtime.execute(ActionRequest(action="rkf.deactivate"))
    blocked = runtime.execute(ActionRequest(action="world.render"))

    self.assertEqual(activated.status, "ok")
    self.assertEqual(status.payload["mode"], "ACTIVE")
    self.assertEqual(deactivated.payload["mode"], "OFF")
    self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")


def test_read_only_session_blocks_writes_but_allows_reads(self) -> None:
    (self.root / "paper.sync-conflict.md").write_text("conflict\n", encoding="utf-8")
    runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
    runtime.execute(ActionRequest(action="rkf.activate"))

    read_result = runtime.execute(ActionRequest(action="world.render"))
    write_result = runtime.execute(
        ActionRequest(action="hot.record", params={"query": "paper search", "origin": "codex"})
    )

    self.assertEqual(read_result.status, "ok")
    self.assertEqual(write_result.status, "blocked")
    self.assertEqual(write_result.payload["error_code"], "RKF_READ_ONLY")
```

Update `setUp()` before constructing `Workspace` so the action fixture has valid roots, machine identity, and a matching writer registry:

```python
        self.raw = self.root / "raw"
        self.raw.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f"wiki_root = \"{self.root.as_posix()}\"\n"
            f"raw_root = \"{self.raw.as_posix()}\"\n\n"
            "[machine]\n"
            "id = \"machine-actions\"\n"
            "maintenance_writer = true\n\n"
            "[knowledge]\n"
            "schema_version = \"rkf-v1\"\n",
            encoding="utf-8",
        )
        sync = self.root / "state" / "sync"
        sync.mkdir(parents=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-actions","assigned_at":"2026-07-10T12:00:00Z"}\n',
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)
        self.runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        activated = self.runtime.execute(ActionRequest(action="rkf.activate"))
        self.assertEqual(activated.status, "ok")
```

- [ ] **Step 2: Run the focused tests and confirm the runtime is missing**

Run:

```bash
python3 -m unittest tests.test_rkf_actions
```

Expected: FAIL because `RKFActionRuntime` cannot be imported.

- [ ] **Step 3: Implement the runtime guard in `rkf/actions.py`**

Add these imports and constants:

```python
from .session import (
    SessionMode,
    SessionState,
    activate_session,
    deactivate_session,
    new_session,
    session_receipt,
)


CONTROL_ACTIONS = {"rkf.activate", "rkf.status", "rkf.deactivate"}
WRITE_ACTIONS = {
    "inbox.capture",
    "hot.record",
    "graph.export",
    "index.generate",
    "codex_handoff.generate",
    "capture.route",
}
WRITER_ONLY_ACTIONS = {
    "inbox.capture",
    "hot.record",
    "graph.export",
    "index.generate",
    "codex_handoff.generate",
}
```

Rename the current `execute_action_request()` dispatcher body to `_dispatch_active_action()` without changing its action branches:

```python
def _dispatch_active_action(request: ActionRequest, *, workspace: Workspace) -> ActionResult:
    params = dict(request.params)
    if request.action == "inbox.capture":
        return capture_inbox(workspace=workspace, **params)
    if request.action == "hot.record":
        return record_hot(workspace=workspace, **params)
    if request.action == "world.render":
        return render_world(workspace=workspace, **params)
    if request.action == "paper.queue":
        return queue_papers(workspace=workspace, **params)
    if request.action == "lint.run":
        return run_lint(workspace=workspace, **params)
    if request.action == "graph.export":
        return export_graph_action(workspace=workspace)
    if request.action == "graph.neighbors":
        return graph_neighbors_action(workspace=workspace, **params)
    if request.action == "graph.paths":
        return graph_paths_action(workspace=workspace, **params)
    if request.action == "graph.page_context":
        return graph_page_context_action(workspace=workspace, **params)
    if request.action == "index.generate":
        return generate_index(workspace=workspace)
    if request.action == "codex_handoff.generate":
        return generate_codex_handoff(workspace=workspace)
    if request.action == "stats.snapshot":
        return snapshot_stats(workspace=workspace, **params)
    raise SystemExit(f"unsupported RKF action: {request.action}")
```

Add the runtime and wrapper:

```python
class RKFActionRuntime:
    def __init__(
        self,
        *,
        workspace: Workspace | Path | None = None,
        project_root: Path | None = None,
        session_id: str = "",
    ) -> None:
        self.workspace = _workspace(workspace)
        self.project_root = project_root
        self.session: SessionState = new_session(session_id)

    def execute(self, request: ActionRequest) -> ActionResult:
        if request.action == "rkf.status":
            return ActionResult("rkf.status", "ok", f"RKF is {self.session.mode.value}", session_receipt(self.session))
        if request.action == "rkf.activate":
            receipt = activate_session(self.session, self.workspace, project_root=self.project_root)
            status = "failed" if self.session.mode == SessionMode.OFF else "ok"
            return ActionResult("rkf.activate", status, f"RKF is {self.session.mode.value}", receipt)
        if request.action == "rkf.deactivate":
            receipt = deactivate_session(self.session)
            return ActionResult("rkf.deactivate", "ok", "RKF is OFF", receipt)
        if self.session.mode == SessionMode.OFF:
            return ActionResult(
                request.action,
                "blocked",
                "RKF is not active; say 啟動 RKF first",
                {"error_code": "RKF_NOT_ACTIVE", **session_receipt(self.session)},
            )
        if self.session.mode == SessionMode.ACTIVE_READ_ONLY and request.action in WRITE_ACTIONS:
            return ActionResult(
                request.action,
                "blocked",
                "RKF is active read-only",
                {"error_code": "RKF_READ_ONLY", **session_receipt(self.session)},
            )
        if request.action in WRITER_ONLY_ACTIONS and self.session.writer_role != "designated":
            return ActionResult(
                request.action,
                "blocked",
                "This projection requires the maintenance writer",
                {"error_code": "RKF_WRITER_REQUIRED", **session_receipt(self.session)},
            )
        return _dispatch_active_action(request, workspace=self.workspace)


def execute_action_request(
    request: ActionRequest,
    *,
    workspace: Workspace | Path | None = None,
    runtime: RKFActionRuntime | None = None,
) -> ActionResult:
    active_runtime = runtime or RKFActionRuntime(workspace=workspace)
    return active_runtime.execute(request)
```

- [ ] **Step 4: Route every existing action test through the activated runtime**

Replace calls shaped like this:

```python
result = execute_action_request(request, workspace=self.workspace)
```

with:

```python
result = execute_action_request(request, runtime=self.runtime)
```

For multiline calls, preserve the `ActionRequest` unchanged and replace only `workspace=self.workspace` with `runtime=self.runtime`.

- [ ] **Step 5: Run action and session tests**

Run:

```bash
python3 -m unittest tests.test_rkf_session tests.test_rkf_actions
```

Expected: all tests pass with `OK`; the new runtime tests confirm OFF, ACTIVE, ACTIVE_READ_ONLY, and deactivation behavior.

- [ ] **Step 6: Review Task 2 scope without committing**

Run:

```bash
git diff --check
git diff -- rkf/actions.py tests/test_rkf_actions.py
```

Expected: no whitespace errors; action bodies are unchanged except for the explicit guard/runtime boundary and test call sites.

---

### Task 3: Deterministic Central `query.search`

**Files:**
- Create: `rkf/retrieval.py`
- Modify: `rkf/actions.py`
- Create: `tests/test_rkf_retrieval.py`

**Interfaces:**
- Consumes: `Workspace`, `knowledge_page_records()`, `read_json()`, `extract_doi()`, `first_heading()`, `first_summary_line()`, `build_research_graph()`.
- Produces: `SearchResultCard`, `search_central_rkf(ws, query, limit=10, page_types=None, reading_states=None, evidence_boundaries=None) -> dict[str, Any]`; action `query.search`.

- [ ] **Step 1: Write failing retrieval tests**

Create `tests/test_rkf_retrieval.py` covering exact DOI, exact page ID, keyword order, maturity fields, graph context, and zero writes:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rkf.core import Workspace, create_paper_note, create_source
from rkf.retrieval import search_central_rkf


class RKFRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)
        record = create_source(
            self.workspace,
            kind="doi",
            value="10.1234/cloud.study",
            title="Cloud Microphysics Retrieval Study",
            topic_id="cloud-microphysics",
            note="Public-safe source note.",
        )
        create_paper_note(self.workspace, record)
        self.source_id = str(record["source_id"])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_exact_doi_precedes_keyword_matches(self) -> None:
        result = search_central_rkf(self.workspace, "10.1234/cloud.study")

        self.assertEqual(result["cards"][0]["source_id"], self.source_id)
        self.assertEqual(result["cards"][0]["match_reason"], "exact-doi")

    def test_result_card_exposes_maturity_and_evidence_gaps(self) -> None:
        result = search_central_rkf(self.workspace, "Cloud Microphysics Retrieval Study")

        paper = next(card for card in result["cards"] if card["type"] == "paper")
        self.assertEqual(paper["reading_maturity"], "metadata-only")
        self.assertEqual(paper["evidence_boundary"], "review-blocker")
        self.assertEqual(paper["evidence_use"], "proposal-only")
        self.assertIn("locator", paper["missing"])

    def test_search_is_read_only(self) -> None:
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())

        result = search_central_rkf(self.workspace, "cloud microphysics")

        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after, before)
        self.assertGreaterEqual(result["count"], 1)
        self.assertEqual(result["next_step"], "inspect-project-local-if-central-context-is-incomplete")

    def test_maturity_and_type_filters_are_applied(self) -> None:
        result = search_central_rkf(
            self.workspace,
            "cloud",
            page_types=["paper"],
            reading_states=["metadata-only"],
            evidence_boundaries=["review-blocker"],
        )

        self.assertGreaterEqual(result["count"], 1)
        self.assertTrue(all(card["type"] == "paper" for card in result["cards"]))
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_rkf_retrieval
```

Expected: FAIL with `ModuleNotFoundError: No module named 'rkf.retrieval'`.

- [ ] **Step 3: Implement deterministic result cards and ranking**

Create `rkf/retrieval.py`. Use these exact public shapes and ordering constants:

```python
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .core import (
    Workspace,
    build_research_graph,
    extract_doi,
    first_heading,
    first_summary_line,
    knowledge_page_records,
    read_json,
    relative_workspace_path,
)


MATCH_PRIORITY = {
    "exact-source-id": 0,
    "exact-doi": 1,
    "exact-identifier": 2,
    "exact-page-id": 3,
    "exact-title": 4,
    "exact-alias": 5,
    "keyword": 6,
    "graph-context": 7,
}


@dataclass(frozen=True)
class SearchResultCard:
    id: str
    path: str
    type: str
    title: str
    source_id: str
    match_reason: str
    score: int
    reading_maturity: str
    evidence_boundary: str
    evidence_use: str
    claim_readiness: str
    missing: list[str]
    summary: str


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _missing(meta: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not meta.get("evidence_ids"):
        missing.append("locator")
    if str(meta.get("fulltext_status", "")) in {"", "unknown", "needs-user-pdf", "partial-only"}:
        missing.append("full-text")
    if str(meta.get("human_feedback_level", "none")) == "none":
        missing.append("human-feedback")
    return missing


def _evidence_use(page_type: str, boundary: str) -> str:
    if page_type in {"inbox", "candidate"} or boundary in {"inbox-only", "ars-proposal", "review-blocker"}:
        return "proposal-only"
    if page_type == "paper":
        return "source-context"
    return "maintained-knowledge"


def _match(
    query: str,
    query_doi: str,
    candidate_id: str,
    title: str,
    source_id: str,
    doi: str,
    identifiers: list[str],
    aliases: list[str],
    text: str,
) -> tuple[str, int] | None:
    normalized_query = _normalize(query)
    if query == source_id:
        return "exact-source-id", 1000
    if query_doi and query_doi == doi:
        return "exact-doi", 950
    if normalized_query and any(normalized_query == _normalize(value) for value in identifiers if value):
        return "exact-identifier", 925
    if query == candidate_id:
        return "exact-page-id", 900
    if normalized_query and normalized_query == _normalize(title):
        return "exact-title", 850
    if normalized_query and any(normalized_query == _normalize(value) for value in aliases if value):
        return "exact-alias", 825
    query_words = set(normalized_query.split())
    candidate_words = set(_normalize(f"{title} {text}").split())
    overlap = len(query_words & candidate_words)
    if overlap:
        return "keyword", 100 + overlap
    return None


def search_central_rkf(
    ws: Workspace,
    query: str,
    *,
    limit: int = 10,
    page_types: list[str] | None = None,
    reading_states: list[str] | None = None,
    evidence_boundaries: list[str] | None = None,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise SystemExit("query.search requires a non-empty query")
    allowed_types = set(page_types or [])
    allowed_reading = set(reading_states or [])
    allowed_boundaries = set(evidence_boundaries or [])
    query_doi = extract_doi(query)
    cards: list[SearchResultCard] = []

    for path, meta, body in knowledge_page_records(ws):
        page_type = str(meta.get("type", "knowledge"))
        if allowed_types and page_type not in allowed_types:
            continue
        reading_maturity = str(meta.get("reading_state", meta.get("reading_status", "unknown")))
        evidence_boundary = str(meta.get("evidence_boundary", "unknown"))
        if allowed_reading and reading_maturity not in allowed_reading:
            continue
        if allowed_boundaries and evidence_boundary not in allowed_boundaries:
            continue
        page_id = path.relative_to(ws.paths.knowledge).with_suffix("").as_posix()
        title = first_heading(body, page_id)
        source_id = str(meta.get("source_id", ""))
        doi = extract_doi(" ".join(str(meta.get(key, "")) for key in ("doi", "sources")))
        identifiers = [source_id, str(meta.get("doi", ""))] + [str(value) for value in meta.get("sources", [])]
        aliases = [str(value) for value in meta.get("aliases", [])]
        search_text = f"{body} {' '.join(str(value) for value in meta.get('topics', []))}"
        matched = _match(query, query_doi, page_id, title, source_id, doi, identifiers, aliases, search_text)
        if matched is None:
            continue
        reason, score = matched
        cards.append(
            SearchResultCard(
                id=page_id,
                path=relative_workspace_path(ws, path),
                type=page_type,
                title=title,
                source_id=source_id,
                match_reason=reason,
                score=score,
                reading_maturity=reading_maturity,
                evidence_boundary=evidence_boundary,
                evidence_use=_evidence_use(page_type, evidence_boundary),
                claim_readiness=str(meta.get("claim_readiness", "unknown")),
                missing=_missing(meta),
                summary=first_summary_line(body),
            )
        )

    for path in sorted(ws.paths.sources.glob("*.json")) if ws.paths.sources.exists() else []:
        record = read_json(path)
        if allowed_types and "source" not in allowed_types:
            continue
        source_id = str(record.get("source_id", path.stem))
        title = str(record.get("title", source_id))
        doi = str(record.get("normalized_doi", ""))
        reading_maturity = str(record.get("reading_state", "metadata-only"))
        if allowed_reading and reading_maturity not in allowed_reading:
            continue
        if allowed_boundaries and "source-record" not in allowed_boundaries:
            continue
        identifiers = [str(record.get("value", "")), doi]
        aliases = [str(value) for value in record.get("aliases", [])]
        matched = _match(
            query,
            query_doi,
            source_id,
            title,
            source_id,
            doi,
            identifiers,
            aliases,
            str(record.get("notes", "")),
        )
        if matched is None:
            continue
        reason, score = matched
        cards.append(
            SearchResultCard(
                id=source_id,
                path=relative_workspace_path(ws, path),
                type="source",
                title=title,
                source_id=source_id,
                match_reason=reason,
                score=score,
                reading_maturity=reading_maturity,
                evidence_boundary="source-record",
                evidence_use="identity-only",
                claim_readiness="not-ready",
                missing=["paper-page"] if not any(card.source_id == source_id and card.type == "paper" for card in cards) else [],
                summary="",
            )
        )

    unique: dict[tuple[str, str], SearchResultCard] = {}
    for card in cards:
        key = (card.type, card.id)
        previous = unique.get(key)
        if previous is None or card.score > previous.score:
            unique[key] = card
    ordered = sorted(unique.values(), key=lambda card: (MATCH_PRIORITY[card.match_reason], -card.score, card.path))[:limit]
    graph = build_research_graph(ws)
    matched_ids = {card.id for card in ordered}
    graph_edges = [edge for edge in graph.get("edges", []) if edge.get("from") in matched_ids or edge.get("to") in matched_ids]
    return {
        "query": query,
        "cards": [asdict(card) for card in ordered],
        "count": len(ordered),
        "graph_context": graph_edges,
        "next_step": "inspect-project-local-if-central-context-is-incomplete",
    }
```

- [ ] **Step 4: Add `query.search` to the guarded action runtime**

Import `search_central_rkf` in `rkf/actions.py` and add this active dispatcher branch before the unsupported-action error:

```python
    if request.action == "query.search":
        payload = search_central_rkf(workspace, **params)
        return ActionResult(
            action="query.search",
            status="ok",
            message=f"found {payload['count']} governed RKF result(s)",
            payload=payload,
        )
```

Do not add `query.search` to `WRITE_ACTIONS` or `WRITER_ONLY_ACTIONS`.

- [ ] **Step 5: Add an action-level query test**

In `tests/test_rkf_actions.py`, add:

```python
    def test_query_search_is_available_only_after_activation(self) -> None:
        self.seed_paper(doi="10.1234/query.action")
        fresh = RKFActionRuntime(workspace=self.workspace, project_root=self.root)

        blocked = fresh.execute(ActionRequest(action="query.search", params={"query": "10.1234/query.action"}))
        fresh.execute(ActionRequest(action="rkf.activate"))
        found = fresh.execute(ActionRequest(action="query.search", params={"query": "10.1234/query.action"}))

        self.assertEqual(blocked.payload["error_code"], "RKF_NOT_ACTIVE")
        self.assertEqual(found.status, "ok")
        self.assertGreaterEqual(found.payload["count"], 1)
```

- [ ] **Step 6: Run retrieval and action tests**

Run:

```bash
python3 -m unittest tests.test_rkf_retrieval tests.test_rkf_actions
```

Expected: all tests pass with `OK`; the search test leaves the file inventory unchanged.

- [ ] **Step 7: Review Task 3 scope without committing**

Run:

```bash
git diff --check
git diff -- rkf/retrieval.py rkf/actions.py tests/test_rkf_retrieval.py tests/test_rkf_actions.py
```

Expected: no whitespace errors; retrieval contains no write helper calls.

---

### Task 4: Immutable Operational Event Envelope

**Files:**
- Create: `schemas/operational_event.schema.json`
- Create: `rkf/events.py`
- Create: `tests/test_rkf_events.py`

**Interfaces:**
- Consumes: `Workspace.paths.events`, `LOCAL_PATH_PATTERNS`.
- Produces: `OperationalEvent`, `build_operational_event()`, `write_operational_event()`, `load_operational_events()`, `load_recent_operational_events()`.

- [ ] **Step 1: Write failing event tests**

Create `tests/test_rkf_events.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from rkf.core import Workspace, read_json
from rkf.events import build_operational_event, load_recent_operational_events, write_operational_event


class RKFOperationalEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workspace = Workspace(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_event_id_and_path_are_unique_and_public_safe(self) -> None:
        event = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="project:Demo",
            machine_id="machine-7f3a2c91",
            target_identity="doi:10.1234/example",
            idempotency_key="idem-123",
            payload={"title": "Example paper", "promotion": "none"},
            created=datetime(2026, 7, 10, 12, 30, tzinfo=timezone.utc),
            nonce="a1b2c3d4",
        )

        path = write_operational_event(self.workspace, event)
        stored = read_json(path)

        self.assertEqual(stored["schema"], "rkf-operational-event-v1")
        self.assertEqual(stored["event_id"], event.event_id)
        self.assertEqual(path.parent.name, "2026-07-10")
        self.assertEqual(stored["payload"]["promotion"], "none")

    def test_existing_event_cannot_be_overwritten(self) -> None:
        event = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="codex",
            machine_id="machine-7f3a2c91",
            target_identity="query:cloud",
            idempotency_key="idem-456",
            payload={"query": "cloud microphysics"},
            created=datetime(2026, 7, 10, 12, 30, tzinfo=timezone.utc),
            nonce="fixednonce",
        )
        write_operational_event(self.workspace, event)

        with self.assertRaises(FileExistsError):
            write_operational_event(self.workspace, event)

    def test_private_path_payload_is_rejected(self) -> None:
        private_value = "/" + "Users/example/private.pdf"

        with self.assertRaises(SystemExit):
            build_operational_event(
                action="capture.route",
                actor="codex",
                origin="codex",
                machine_id="machine-7f3a2c91",
                target_identity="file:private",
                idempotency_key="idem-789",
                payload={"clip": private_value},
            )

    def test_recent_loader_filters_by_cutoff(self) -> None:
        event = build_operational_event(
            action="capture.route",
            actor="codex",
            origin="codex",
            machine_id="machine-7f3a2c91",
            target_identity="query:cloud",
            idempotency_key="idem-recent",
            payload={"query": "cloud microphysics"},
            created=datetime(2026, 7, 10, 12, 30, tzinfo=timezone.utc),
            nonce="recent001",
        )
        write_operational_event(self.workspace, event)

        loaded = load_recent_operational_events(
            self.workspace,
            since=datetime(2026, 7, 9, tzinfo=timezone.utc),
        )

        self.assertEqual([item["event_id"] for item in loaded], [event.event_id])
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_rkf_events
```

Expected: FAIL with `ModuleNotFoundError: No module named 'rkf.events'`.

- [ ] **Step 3: Add the complete event JSON Schema**

Create `schemas/operational_event.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/rkf/operational_event.schema.json",
  "title": "RKFOperationalEvent",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema",
    "event_id",
    "action",
    "actor",
    "origin",
    "machine_id",
    "created",
    "target_identity",
    "idempotency_key",
    "public_safe",
    "payload"
  ],
  "properties": {
    "schema": {"const": "rkf-operational-event-v1"},
    "event_id": {"type": "string", "pattern": "^evt_[0-9]{8}T[0-9]{6}Z_[a-z0-9-]+_[a-z0-9]+$"},
    "action": {"type": "string", "enum": ["capture.route", "capture.review"]},
    "actor": {"type": "string", "enum": ["codex", "human", "codex-handoff", "automation"]},
    "origin": {"type": "string", "minLength": 1, "maxLength": 200},
    "machine_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
    "created": {"type": "string", "format": "date-time"},
    "target_identity": {"type": "string", "minLength": 1, "maxLength": 500},
    "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 128},
    "public_safe": {"const": true},
    "payload": {"type": "object"}
  }
}
```

- [ ] **Step 4: Implement event construction, exclusive writes, and loading**

Create `rkf/events.py`:

```python
from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import LOCAL_PATH_PATTERNS, Workspace, read_json


EVENT_SCHEMA = "rkf-operational-event-v1"
MAX_EVENT_BYTES = 16_384


@dataclass(frozen=True)
class OperationalEvent:
    schema: str
    event_id: str
    action: str
    actor: str
    origin: str
    machine_id: str
    created: str
    target_identity: str
    idempotency_key: str
    public_safe: bool
    payload: dict[str, Any]


def _safe_machine_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    if not normalized:
        raise SystemExit("operational event requires machine_id")
    return normalized


def _assert_public_safe(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(serialized.encode("utf-8")) > MAX_EVENT_BYTES:
        raise SystemExit("operational event payload is too large")
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(serialized):
            raise SystemExit("operational event payload contains a private path")


def build_operational_event(
    *,
    action: str,
    actor: str,
    origin: str,
    machine_id: str,
    target_identity: str,
    idempotency_key: str,
    payload: dict[str, Any],
    created: datetime | None = None,
    nonce: str = "",
) -> OperationalEvent:
    _assert_public_safe(payload)
    instant = (created or datetime.now(timezone.utc)).astimezone(timezone.utc)
    machine = _safe_machine_id(machine_id)
    suffix = re.sub(r"[^a-z0-9]+", "", (nonce or secrets.token_hex(6)).lower())
    event_id = f"evt_{instant.strftime('%Y%m%dT%H%M%SZ')}_{machine}_{suffix}"
    return OperationalEvent(
        schema=EVENT_SCHEMA,
        event_id=event_id,
        action=action,
        actor=actor,
        origin=origin,
        machine_id=machine,
        created=instant.isoformat().replace("+00:00", "Z"),
        target_identity=target_identity,
        idempotency_key=idempotency_key,
        public_safe=True,
        payload=payload,
    )


def write_operational_event(ws: Workspace, event: OperationalEvent) -> Path:
    event_day = event.created[:10]
    destination = ws.paths.events / event_day / f"{event.event_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(asdict(event), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    with destination.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return destination


def load_operational_events(ws: Workspace) -> list[dict[str, Any]]:
    if not ws.paths.events.exists():
        return []
    return [read_json(path) for path in sorted(ws.paths.events.rglob("evt_*.json"))]


def load_recent_operational_events(ws: Workspace, *, since: datetime) -> list[dict[str, Any]]:
    cutoff = since.astimezone(timezone.utc)
    return [
        event
        for event in load_operational_events(ws)
        if datetime.fromisoformat(str(event["created"]).replace("Z", "+00:00")) >= cutoff
    ]
```

- [ ] **Step 5: Run event tests**

Run:

```bash
python3 -m unittest tests.test_rkf_events
```

Expected: `Ran 4 tests` and `OK`.

- [ ] **Step 6: Review Task 4 scope without committing**

Run:

```bash
git diff --check
python3 -m json.tool schemas/operational_event.schema.json
```

Expected: no whitespace errors; JSON parsing succeeds and prints the schema.

---

### Task 5: Canonical Research Classification, Deduplication, And `capture.route`

**Files:**
- Create: `rkf/capture.py`
- Modify: `rkf/actions.py`
- Modify: `rkf/retrieval.py`
- Create: `tests/test_rkf_capture.py`
- Modify: `tests/test_rkf_retrieval.py`

**Interfaces:**
- Consumes: Task 4 `build_operational_event()`, `write_operational_event()`, `load_recent_operational_events()`; existing `capture_inbox()` and `record_hot()` projection functions.
- Produces: `CaptureInput`, `CaptureDecision`, `DedupeResult`, `CaptureRoute`, `classify_capture()`, `route_capture()`; action `capture.route`.

- [ ] **Step 1: Write failing classifier, dedupe, and routing tests**

Create `tests/test_rkf_capture.py` with these concrete behaviors:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rkf.actions import ActionRequest, RKFActionRuntime
from rkf.capture import CaptureInput, classify_capture
from rkf.core import Workspace, create_source


class RKFCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw"
        self.raw.mkdir()
        (self.root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f"wiki_root = \"{self.root.as_posix()}\"\n"
            f"raw_root = \"{self.raw.as_posix()}\"\n\n"
            "[machine]\n"
            "id = \"machine-capture\"\n"
            "maintenance_writer = false\n\n"
            "[knowledge]\n"
            "schema_version = \"rkf-v1\"\n",
            encoding="utf-8",
        )
        self.workspace = Workspace(self.root)
        self.runtime = RKFActionRuntime(workspace=self.workspace, project_root=self.root)
        self.runtime.execute(ActionRequest(action="rkf.activate"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_uncertain_and_ordinary_coding_do_not_auto_capture(self) -> None:
        uncertain = classify_capture(CaptureInput(text="Maybe remember this", origin="codex"))
        coding = classify_capture(CaptureInput(text="Fix the CSS padding", origin="project:WebApp"))

        self.assertEqual(uncertain.level, "none")
        self.assertEqual(coding.level, "none")

        routed = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={"title": "Uncertain", "text": "Maybe remember this", "origin": "codex"},
            )
        )
        self.assertEqual(routed.status, "not-applicable")
        self.assertEqual(routed.payload["error_code"], "RKF_CAPTURE_NOT_TRIGGERED")

    def test_external_gpt_source_is_explicitly_provenanced(self) -> None:
        result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "External GPT paper lead",
                    "text": "Short summary for DOI 10.1234/external.gpt",
                    "origin": "external-gpt",
                    "doi": "10.1234/external.gpt",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["promotion"], "none")
        self.assertEqual(result.payload["materialization"], "queued")
        event_path = self.root / result.payload["event_path"]
        event = json.loads(event_path.read_text(encoding="utf-8"))
        self.assertEqual(event["origin"], "external-gpt")

        found = self.runtime.execute(
            ActionRequest(action="query.search", params={"query": "10.1234/external.gpt"})
        )
        event_card = next(card for card in found.payload["cards"] if card["type"] == "event")
        self.assertEqual(event_card["evidence_use"], "proposal-only")

    def test_existing_doi_is_recorded_without_duplicate_projection(self) -> None:
        create_source(
            self.workspace,
            kind="doi",
            value="10.1234/existing",
            title="Existing Paper",
            topic_id="",
            note="",
        )

        result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Existing Paper",
                    "text": "A repeated DOI 10.1234/existing lead",
                    "origin": "project:Demo",
                    "doi": "10.1234/existing",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(result.payload["dedupe_status"], "existing")
        self.assertEqual(result.payload["materialization"], "not-needed")

    def test_canonical_url_and_ambiguous_title_do_not_silently_merge(self) -> None:
        create_source(
            self.workspace,
            kind="url",
            value="https://example.org/paper?a=1",
            title="Shared Paper Title",
            topic_id="",
            note="",
        )

        url_result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "URL repeat",
                    "text": "Paper source URL",
                    "origin": "project:Demo",
                    "source_url": "https://EXAMPLE.org/paper?utm_source=chat&a=1#abstract",
                    "intent": "paper-search",
                },
            )
        )
        title_result = self.runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "Shared Paper Title",
                    "text": "Find this paper title",
                    "origin": "project:Demo",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(url_result.payload["dedupe_status"], "existing")
        self.assertEqual(title_result.payload["dedupe_status"], "ambiguous")
        self.assertEqual(title_result.payload["materialization"], "not-needed")

    def test_same_capture_within_24_hours_is_idempotent(self) -> None:
        params = {
            "title": "Repeated cloud lead",
            "text": "Find DOI 10.1234/repeated.cloud",
            "origin": "project:Demo",
            "doi": "10.1234/repeated.cloud",
            "intent": "paper-search",
        }

        first = self.runtime.execute(ActionRequest(action="capture.route", params=params))
        second = self.runtime.execute(ActionRequest(action="capture.route", params=params))

        self.assertEqual(first.payload["dedupe_status"], "new")
        self.assertEqual(second.payload["dedupe_status"], "existing")

    def test_writer_materializes_inbox_and_hot_after_event(self) -> None:
        sync = self.root / "state" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "maintenance-writer.json").write_text(
            '{"schema":"rkf-writer-registry-v1","machine_id":"machine-capture","assigned_at":"2026-07-10T12:00:00Z"}\n',
            encoding="utf-8",
        )
        text = (self.root / "rkf.workspace.toml").read_text(encoding="utf-8")
        (self.root / "rkf.workspace.toml").write_text(text.replace("maintenance_writer = false", "maintenance_writer = true"), encoding="utf-8")
        writer_runtime = RKFActionRuntime(workspace=Workspace(self.root), project_root=self.root)
        writer_runtime.execute(ActionRequest(action="rkf.activate"))

        result = writer_runtime.execute(
            ActionRequest(
                action="capture.route",
                params={
                    "title": "New cloud paper",
                    "text": "Find DOI 10.1234/new.cloud paper",
                    "origin": "project:Demo",
                    "doi": "10.1234/new.cloud",
                    "intent": "paper-search",
                },
            )
        )

        self.assertEqual(result.payload["materialization"], "materialized")
        self.assertTrue((self.root / "knowledge" / "inbox").exists())
        self.assertTrue((self.root / "hot.md").exists())
        self.assertTrue((self.root / "state" / "events").exists())
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_rkf_capture
```

Expected: FAIL because `rkf.capture` does not exist and `capture.route` is unsupported.

- [ ] **Step 3: Implement canonical capture input, classification, and dedupe**

Create `rkf/capture.py` with these public dataclasses and deterministic rules:

```python
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .core import LOCAL_PATH_PATTERNS, Workspace, extract_doi, normalize_doi, read_json
from .events import build_operational_event, load_recent_operational_events, write_operational_event


SOURCE_TERMS = {"paper", "papers", "doi", "citation", "reference", "journal", "literature", "source", "arxiv", "pubmed", "文獻", "論文"}
RESEARCH_TERMS = {"synthesis", "method", "experiment design", "manuscript", "hypothesis", "claim", "evidence", "研究", "方法", "實驗", "假說", "證據", "綜整"}
CODING_ONLY_TERMS = {"css", "button", "padding", "typescript", "react component", "build error", "lint error"}
SENSITIVE_RE = re.compile(r"\b(api[_ -]?key|access[_ -]?token|password|private[_ -]?key|secret)\b", re.IGNORECASE)
MAX_CAPTURE_CHARS = 12_000


@dataclass(frozen=True)
class CaptureInput:
    text: str
    origin: str
    title: str = ""
    doi: str = ""
    source_url: str = ""
    authors: str = ""
    year: str = ""
    intent: str = "research-discussion"
    reader_note: str = ""
    agent_note: str = ""
    topic_id: str = ""


@dataclass(frozen=True)
class CaptureDecision:
    level: str
    targets: list[str]
    reasons: list[str]


@dataclass(frozen=True)
class DedupeResult:
    status: str
    matched_id: str
    key: str


@dataclass(frozen=True)
class CaptureRoute:
    event_path: str
    event_id: str
    decision: CaptureDecision
    dedupe: DedupeResult
    materialize: bool


def _contains(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def classify_capture(item: CaptureInput) -> CaptureDecision:
    haystack = " ".join([item.text, item.title, item.doi, item.source_url]).strip()
    if len(haystack) > MAX_CAPTURE_CHARS:
        return CaptureDecision("blocked", [], ["too-long"])
    if any(pattern.search(haystack) for pattern in LOCAL_PATH_PATTERNS):
        return CaptureDecision("blocked", [], ["private-path"])
    if SENSITIVE_RE.search(haystack):
        return CaptureDecision("blocked", [], ["sensitive-material"])
    if not haystack or _contains(haystack, CODING_ONLY_TERMS):
        return CaptureDecision("none", [], ["ordinary-or-uncertain"])
    doi = normalize_doi(item.doi or extract_doi(haystack))
    bibliographic_hint = item.intent == "paper-search" and bool(item.title or item.authors or item.year)
    source_like = bool(doi or item.source_url or bibliographic_hint or _contains(haystack, SOURCE_TERMS))
    research_discussion = _contains(haystack, RESEARCH_TERMS)
    if not source_like and not research_discussion:
        return CaptureDecision("none", [], ["uncertain"])
    targets = ["inbox"]
    reasons: list[str] = []
    if doi:
        reasons.append("doi")
    if item.source_url:
        reasons.append("url")
    if source_like:
        reasons.append("source-like")
        targets.append("hot")
    if research_discussion:
        reasons.append("research-discussion")
    level = "aggressive" if research_discussion else "active"
    return CaptureDecision(level, sorted(set(targets)), sorted(set(reasons)))


def _normalized_title(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _canonical_url(value: str) -> str:
    if not value.strip():
        return ""
    parts = urlsplit(value.strip())
    query = sorted(
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))


def _fingerprint(item: CaptureInput) -> str:
    normalized = json.dumps(
        {
            "title": _normalized_title(item.title),
            "text": " ".join(item.text.lower().split()),
            "url": _canonical_url(item.source_url),
            "doi": normalize_doi(item.doi or extract_doi(item.text)),
        },
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def dedupe_capture(ws: Workspace, item: CaptureInput, *, now: datetime) -> DedupeResult:
    doi = normalize_doi(item.doi or extract_doi(item.text))
    normalized_title = _normalized_title(item.title)
    ambiguous_title = ""
    for path in sorted(ws.paths.sources.glob("*.json")) if ws.paths.sources.exists() else []:
        record = read_json(path)
        source_id = str(record.get("source_id", path.stem))
        if doi and doi == str(record.get("normalized_doi", "")):
            return DedupeResult("existing", source_id, f"doi:{doi}")
        canonical_url = _canonical_url(item.source_url)
        if canonical_url and canonical_url == _canonical_url(str(record.get("value", ""))):
            return DedupeResult("existing", source_id, f"url:{canonical_url}")
        if normalized_title and normalized_title == _normalized_title(str(record.get("title", ""))):
            record_text = _normalized_title(json.dumps(record, ensure_ascii=False))
            author_hint = _normalized_title(item.authors)
            year_hint = item.year.strip().lower()
            author_matches = not author_hint or author_hint in record_text
            year_matches = not year_hint or year_hint in record_text
            if (author_hint or year_hint) and author_matches and year_matches:
                return DedupeResult("existing", source_id, f"title:{normalized_title}:{author_hint}:{year_hint}")
            ambiguous_title = source_id
    if ambiguous_title:
        return DedupeResult("ambiguous", ambiguous_title, f"title:{normalized_title}")

    fingerprint = _fingerprint(item)
    recent = load_recent_operational_events(ws, since=now - timedelta(hours=24))
    for event in recent:
        payload = event.get("payload", {})
        if payload.get("content_fingerprint") == fingerprint:
            return DedupeResult("existing", str(event.get("event_id", "")), f"fingerprint:{fingerprint}")
        if (
            event.get("origin") == item.origin
            and payload.get("intent") == item.intent
            and payload.get("normalized_text") == " ".join(item.text.lower().split())
        ):
            return DedupeResult("existing", str(event.get("event_id", "")), "recent-origin-intent")
    key = f"doi:{doi}" if doi else f"fingerprint:{fingerprint}"
    return DedupeResult("new", "", key)


def route_capture(
    ws: Workspace,
    item: CaptureInput,
    *,
    machine_id: str,
    actor: str = "codex",
    now: datetime | None = None,
) -> CaptureRoute:
    instant = now or datetime.now(timezone.utc)
    decision = classify_capture(item)
    if decision.level == "blocked":
        raise SystemExit(f"capture.route blocked: {','.join(decision.reasons)}")
    if decision.level == "none":
        raise SystemExit("capture.route did not find a deterministic research trigger")
    dedupe = dedupe_capture(ws, item, now=instant)
    doi = normalize_doi(item.doi or extract_doi(item.text))
    fingerprint = _fingerprint(item)
    action = "capture.review" if dedupe.status == "ambiguous" else "capture.route"
    payload: dict[str, Any] = {
        "title": item.title,
        "text": item.text,
        "doi": doi,
        "source_url": item.source_url,
        "authors": item.authors,
        "year": item.year,
        "intent": item.intent,
        "reader_note": item.reader_note,
        "agent_note": item.agent_note,
        "topic_id": item.topic_id,
        "targets": decision.targets,
        "reasons": decision.reasons,
        "dedupe_status": dedupe.status,
        "matched_id": dedupe.matched_id,
        "content_fingerprint": fingerprint,
        "normalized_text": " ".join(item.text.lower().split()),
        "promotion": "none",
    }
    event = build_operational_event(
        action=action,
        actor=actor,
        origin=item.origin,
        machine_id=machine_id,
        target_identity=f"doi:{doi}" if doi else f"fingerprint:{fingerprint}",
        idempotency_key=dedupe.key,
        payload=payload,
        created=instant,
    )
    path = write_operational_event(ws, event)
    return CaptureRoute(
        event_path=path.relative_to(ws.paths.wiki_root).as_posix(),
        event_id=event.event_id,
        decision=decision,
        dedupe=dedupe,
        materialize=dedupe.status == "new",
    )
```

- [ ] **Step 4: Make queued capture events retrievable as proposal-only cards**

Import `load_operational_events` in `rkf/retrieval.py`:

```python
from .events import load_operational_events
```

Inside `search_central_rkf()`, after SourceRecord cards are collected and before deduplication/sorting, add:

```python
    if not allowed_types or "event" in allowed_types:
        for event in load_operational_events(ws):
            if allowed_reading and "captured" not in allowed_reading:
                continue
            if allowed_boundaries and "event-only" not in allowed_boundaries:
                continue
            payload = event.get("payload", {})
            title = str(payload.get("title", event.get("event_id", "capture event")))
            text = " ".join(
                str(payload.get(key, ""))
                for key in ("text", "doi", "source_url", "intent", "reasons")
            )
            matched = _match(
                query,
                query_doi,
                str(event.get("event_id", "")),
                title,
                str(payload.get("matched_id", "")),
                str(payload.get("doi", "")),
                [str(payload.get("doi", "")), str(payload.get("source_url", ""))],
                [],
                text,
            )
            if matched is None:
                continue
            reason, score = matched
            event_path = ws.paths.events / str(event["created"])[:10] / f"{event['event_id']}.json"
            cards.append(
                SearchResultCard(
                    id=str(event["event_id"]),
                    path=relative_workspace_path(ws, event_path),
                    type="event",
                    title=title,
                    source_id=str(payload.get("matched_id", "")),
                    match_reason=reason,
                    score=score,
                    reading_maturity="captured",
                    evidence_boundary="event-only",
                    evidence_use="proposal-only",
                    claim_readiness="not-ready",
                    missing=["classification-review"],
                    summary=str(payload.get("text", ""))[:180],
                )
            )
```

This makes non-writer captures discoverable without presenting them as maintained knowledge or stable evidence.

- [ ] **Step 5: Add the writer-aware action wrapper and receipt**

Import `CaptureInput` and `route_capture` in `rkf/actions.py`. Add this method to `RKFActionRuntime`:

```python
    def _capture_route(self, params: dict[str, Any]) -> ActionResult:
        item = CaptureInput(**params)
        try:
            routed = route_capture(
                self.workspace,
                item,
                machine_id=self.session.machine_id,
            )
        except SystemExit as error:
            message = str(error)
            not_triggered = "did not find a deterministic research trigger" in message
            return ActionResult(
                action="capture.route",
                status="not-applicable" if not_triggered else "blocked",
                message=message,
                payload={
                    "error_code": "RKF_CAPTURE_NOT_TRIGGERED" if not_triggered else "RKF_CAPTURE_REJECTED",
                    "promotion": "none",
                },
            )
        projections: list[dict[str, Any]] = []
        materialization = "not-needed" if not routed.materialize else "queued"
        if routed.materialize and self.session.writer_role == "designated":
            try:
                if "inbox" in routed.decision.targets:
                    inbox = capture_inbox(
                        workspace=self.workspace,
                        title=item.title or item.text[:80],
                        origin=item.origin,
                        source_url=item.source_url,
                        doi=item.doi,
                        clip=item.text,
                        reader_note=item.reader_note,
                        agent_note=item.agent_note,
                        topic_id=item.topic_id,
                        inject=True,
                    )
                    projections.append({"action": inbox.action, "status": inbox.status, "payload": inbox.payload})
                if "hot" in routed.decision.targets:
                    hot = record_hot(
                        workspace=self.workspace,
                        query=item.text,
                        topic_id=item.topic_id,
                        origin=item.origin,
                        intent=item.intent,
                        notes="",
                    )
                    projections.append({"action": hot.action, "status": hot.status, "payload": hot.payload})
                materialization = "materialized"
            except (OSError, SystemExit) as error:
                return ActionResult(
                    action="capture.route",
                    status="partial",
                    message=f"captured event {routed.event_id}; projection queued after failure; Promotion: none",
                    payload={
                        "event_id": routed.event_id,
                        "event_path": routed.event_path,
                        "dedupe_status": routed.dedupe.status,
                        "materialization": "queued",
                        "projection_error": str(error),
                        "promotion": "none",
                    },
                )
        payload = {
            "event_id": routed.event_id,
            "event_path": routed.event_path,
            "capture_level": routed.decision.level,
            "targets": routed.decision.targets,
            "reasons": routed.decision.reasons,
            "dedupe_status": routed.dedupe.status,
            "matched_id": routed.dedupe.matched_id,
            "materialization": materialization,
            "projections": projections,
            "promotion": "none",
        }
        return ActionResult(
            action="capture.route",
            status="ok",
            message=f"captured event {routed.event_id}; Promotion: none",
            payload=payload,
        )
```

In `RKFActionRuntime.execute()`, after session/read-only checks and before writer-only checks, add:

```python
        if request.action == "capture.route":
            return self._capture_route(dict(request.params))
```

This ordering allows any active machine to queue a unique event; only the designated writer materializes named projections.

- [ ] **Step 6: Run capture, event, retrieval, and action tests**

Run:

```bash
python3 -m unittest tests.test_rkf_capture tests.test_rkf_events tests.test_rkf_retrieval tests.test_rkf_actions
```

Expected: all tests pass with `OK`; non-writer capture creates an event but no inbox/hot projection, while writer capture creates event first and then projections.

- [ ] **Step 7: Review Task 5 scope without committing**

Run:

```bash
git diff --check
git diff -- rkf/capture.py rkf/actions.py rkf/retrieval.py tests/test_rkf_capture.py tests/test_rkf_retrieval.py
```

Expected: no whitespace errors; `capture.route` always reports `promotion: none` and cannot write while the session is OFF or ACTIVE_READ_ONLY.

---

### Task 6: Project Marker V2, Auto-Connect Helper, And Global Skill Boundary

**Files:**
- Modify: `tools/rkf_auto_connect.py:1-456`
- Modify: `tests/test_rkf_auto_connect.py:1-285`
- External modify after separate permission: `~/.codex/skills/rkf-auto-connect/SKILL.md`

**Interfaces:**
- Consumes: `RKFActionRuntime`, `ActionRequest`, canonical `CaptureInput`/`CaptureDecision` classifier.
- Produces: v2 `.rkf-connect.toml`; `build_activate_request()`, `build_query_request()`, `build_capture_request()`; no direct helper write execution.

- [ ] **Step 1: Replace legacy helper expectations with failing v2 and OFF-boundary tests**

In `tests/test_rkf_auto_connect.py`, replace the marker and request tests with:

```python
    def test_write_project_marker_uses_v2_manual_activation(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        marker = auto.write_project_marker(project, mode="active-aggressive")
        policy = auto.read_project_marker(project)

        text = marker.read_text(encoding="utf-8")
        self.assertIn("version = 2", text)
        self.assertIn("available = true", text)
        self.assertIn('activation = "manual"', text)
        self.assertNotIn("enabled = true", text)
        self.assertTrue(policy["available"])
        self.assertEqual(policy["activation"], "manual")

    def test_v1_marker_upgrade_requires_preview_and_explicit_apply(self) -> None:
        project = self.root / "LegacyProject"
        project.mkdir()
        marker = project / ".rkf-connect.toml"
        original = "[rkf_auto_connect]\nenabled = true\nmode = \"active-aggressive\"\n"
        marker.write_text(original, encoding="utf-8")

        preview = auto.preview_project_marker(project, mode="active-aggressive")

        self.assertTrue(preview["would_change"])
        self.assertEqual(preview["from_version"], 1)
        self.assertEqual(marker.read_text(encoding="utf-8"), original)
        with self.assertRaises(SystemExit):
            auto.write_project_marker(project, mode="active-aggressive")
        auto.write_project_marker(project, mode="active-aggressive", approve_upgrade=True)
        self.assertIn("version = 2", marker.read_text(encoding="utf-8"))

    def test_build_requests_use_only_control_query_and_capture_actions(self) -> None:
        config = auto.load_connector_config()

        self.assertEqual(auto.build_activate_request(config=config).action, "rkf.activate")
        self.assertEqual(auto.build_query_request(config=config, query="cloud papers").action, "query.search")
        capture = auto.build_capture_request(
            config=config,
            title="Cloud paper lead",
            text="Find DOI 10.1234/cloud.lead",
            origin="project:Demo",
            doi="10.1234/cloud.lead",
            intent="paper-search",
        )
        self.assertEqual(capture.action, "capture.route")

    def test_execute_without_shared_runtime_is_off_and_writes_nothing(self) -> None:
        config = auto.load_connector_config()
        request = auto.build_capture_request(
            config=config,
            title="Blocked lead",
            text="Find DOI 10.1234/blocked",
            origin="project:Demo",
            doi="10.1234/blocked",
            intent="paper-search",
        )
        before = sorted(path.relative_to(self.researchwiki) for path in self.researchwiki.rglob("*") if path.is_file())

        result = auto.execute_action_request(config=config, request=request)

        after = sorted(path.relative_to(self.researchwiki) for path in self.researchwiki.rglob("*") if path.is_file())
        self.assertEqual(after, before)
        self.assertEqual(result.payload["error_code"], "RKF_NOT_ACTIVE")
```

Remove tests asserting that `inbox-execute` or `hot-execute` writes directly. Retain tests for classification, private-path blocking, external-project execution, bridge preservation, and absence of legacy command arrays.

- [ ] **Step 2: Run helper tests and verify they fail against the v1 helper**

Run:

```bash
python3 -m unittest tests.test_rkf_auto_connect
```

Expected: FAIL because the marker still uses `[rkf_auto_connect]`, new request builders are missing, and current execute helpers write without activation.

- [ ] **Step 3: Make `rkf.capture` the single classifier and add structured request builders**

In `tools/rkf_auto_connect.py`, remove duplicated trigger constants and `classify_capture()`. Import:

```python
from rkf.actions import ActionRequest, ActionResult, RKFActionRuntime
from rkf.capture import CaptureInput, classify_capture as classify_rkf_capture
```

Keep the helper's current public `classify_capture()` signature as a thin adapter:

```python
def classify_capture(*, text: str, source_url: str = "", project_name: str = "") -> CaptureDecision:
    decision = classify_rkf_capture(
        CaptureInput(
            text=text,
            origin=f"project:{project_name}" if project_name else "codex",
            source_url=source_url,
        )
    )
    return CaptureDecision(
        level=decision.level,
        targets=decision.targets,
        reasons=decision.reasons,
        summary=_summary(text),
    )
```

Replace inbox/hot request builders with:

```python
def build_activate_request(*, config: ConnectorConfig) -> ActionRequest:
    _ = config
    return ActionRequest(action="rkf.activate")


def build_query_request(*, config: ConnectorConfig, query: str, limit: int = 10) -> ActionRequest:
    _ = config
    return ActionRequest(action="query.search", params={"query": query, "limit": limit})


def build_capture_request(
    *,
    config: ConnectorConfig,
    title: str,
    text: str,
    origin: str,
    doi: str = "",
    source_url: str = "",
    authors: str = "",
    year: str = "",
    intent: str = "research-discussion",
    reader_note: str = "",
    agent_note: str = "",
    topic_id: str = "",
) -> ActionRequest:
    _ = config
    return ActionRequest(
        action="capture.route",
        params={
            "title": title,
            "text": text,
            "origin": origin,
            "doi": doi,
            "source_url": source_url,
            "authors": authors,
            "year": year,
            "intent": intent,
            "reader_note": reader_note,
            "agent_note": agent_note,
            "topic_id": topic_id,
        },
    )


def execute_action_request(
    *,
    config: ConnectorConfig,
    request: ActionRequest,
    runtime: RKFActionRuntime | None = None,
) -> ActionResult:
    active_runtime = runtime or RKFActionRuntime(workspace=Workspace(config.researchwiki_root))
    return active_runtime.execute(request)
```

- [ ] **Step 4: Write and normalize v2 markers with an upgrade preview gate**

Add a pure renderer and preview, then replace `write_project_marker()`:

```python
def render_project_marker(*, mode: str) -> str:
    return (
        "version = 2\n\n"
        "[rkf]\n"
        "available = true\n"
        "activation = \"manual\"\n"
        "query_first = true\n"
        f"capture_mode = \"{mode}\"\n"
    )


def preview_project_marker(project_root: Path, *, mode: str = "active-aggressive") -> dict[str, Any]:
    marker = project_root / ".rkf-connect.toml"
    current = read_project_marker(project_root)
    proposed = render_project_marker(mode=mode)
    return {
        "path": ".rkf-connect.toml",
        "from_version": int(current["version"]),
        "to_version": 2,
        "would_change": not marker.exists() or marker.read_text(encoding="utf-8") != proposed,
        "proposed": proposed,
    }


def write_project_marker(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
    approve_upgrade: bool = False,
) -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    marker = project_root / ".rkf-connect.toml"
    current = read_project_marker(project_root)
    if marker.exists() and int(current["version"]) < 2 and not approve_upgrade:
        raise SystemExit("v1 marker upgrade requires preview and explicit approval")
    marker.write_text(render_project_marker(mode=mode), encoding="utf-8")
    return marker
```

Replace `read_project_marker()` with a normalizer that accepts both versions but never returns active state:

```python
def read_project_marker(project_root: Path) -> dict[str, Any]:
    marker = project_root / ".rkf-connect.toml"
    if not marker.exists():
        return {"version": 0, "available": False, "activation": "manual", "query_first": True, "capture_mode": "off"}
    data = _load_toml(marker)
    version = int(data.get("version", 1))
    if version >= 2:
        section = data.get("rkf", {})
        return {
            "version": version,
            "available": bool(section.get("available", False)),
            "activation": "manual",
            "query_first": bool(section.get("query_first", True)),
            "capture_mode": str(section.get("capture_mode", "active-aggressive")),
        }
    section = data.get("rkf_auto_connect", {})
    return {
        "version": 1,
        "available": bool(section.get("enabled", False)),
        "activation": "manual",
        "query_first": True,
        "capture_mode": str(section.get("mode", "active-aggressive")),
    }
```

- [ ] **Step 5: Remove direct execute subcommands and private-path output**

Keep `resolve`, `classify`, `mark-project`, and `bridge-folder`. Remove `inbox-request`, `hot-request`, `inbox-execute`, and `hot-execute`. Add these request-only parsers:

```python
    marker = sub.add_parser("mark-project")
    marker.add_argument("project_root")
    marker.add_argument("--mode", default="active-aggressive")
    marker.add_argument("--apply-upgrade", action="store_true")

    activate_request = sub.add_parser("activate-request")

    query_request = sub.add_parser("query-request")
    query_request.add_argument("query")
    query_request.add_argument("--limit", type=int, default=10)

    capture_request = sub.add_parser("capture-request")
    capture_request.add_argument("title")
    capture_request.add_argument("--text", required=True)
    capture_request.add_argument("--origin", required=True)
    capture_request.add_argument("--doi", default="")
    capture_request.add_argument("--source-url", default="")
    capture_request.add_argument("--authors", default="")
    capture_request.add_argument("--year", default="")
    capture_request.add_argument("--intent", default="research-discussion")
    capture_request.add_argument("--reader-note", default="")
    capture_request.add_argument("--agent-note", default="")
    capture_request.add_argument("--topic-id", default="")
```

Replace the existing `mark-project` branch with a preview-first branch:

```python
    if args.command == "mark-project":
        project_root = Path(args.project_root).expanduser().resolve()
        marker_path = project_root / ".rkf-connect.toml"
        if marker_path.exists() and not args.apply_upgrade:
            print(json.dumps(preview_project_marker(project_root, mode=args.mode), ensure_ascii=False, indent=2))
            return 0
        path = write_project_marker(
            project_root,
            mode=args.mode,
            approve_upgrade=args.apply_upgrade,
        )
        print(path.name)
        return 0
```

After project-marker and bridge-folder handling, load connector config and add these branches:

```python
    config = load_connector_config()
    if args.command == "activate-request":
        print(json.dumps(asdict(build_activate_request(config=config)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "query-request":
        request = build_query_request(config=config, query=args.query, limit=args.limit)
        print(json.dumps(asdict(request), ensure_ascii=False, indent=2))
        return 0
    if args.command == "capture-request":
        request = build_capture_request(
            config=config,
            title=args.title,
            text=args.text,
            origin=args.origin,
            doi=args.doi,
            source_url=args.source_url,
            authors=args.authors,
            year=args.year,
            intent=args.intent,
            reader_note=args.reader_note,
            agent_note=args.agent_note,
            topic_id=args.topic_id,
        )
        print(json.dumps(asdict(request), ensure_ascii=False, indent=2))
        return 0
```

The `resolve` output must be:

```python
print(
    json.dumps(
        {
            "researchwiki": "configured",
            "workspace_config": True,
            "mode": config.mode,
        },
        ensure_ascii=False,
        indent=2,
    )
)
```

Do not print `config.researchwiki_root`, `config.config_path`, `wiki_root`, or `raw_root`.

Replace the old hot-request command test with:

```python
    def test_capture_request_command_outputs_structured_action_json(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            status = auto.main(
                [
                    "capture-request",
                    "Cloud paper lead",
                    "--text",
                    "Find DOI 10.1234/cloud.lead",
                    "--origin",
                    "project:Demo",
                    "--doi",
                    "10.1234/cloud.lead",
                    "--intent",
                    "paper-search",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["action"], "capture.route")
        self.assertEqual(payload["params"]["doi"], "10.1234/cloud.lead")
```

- [ ] **Step 6: Run helper tests**

Run:

```bash
python3 -m unittest tests.test_rkf_auto_connect
```

Expected: all helper tests pass with `OK`; no helper command can write to RKF without a shared activated runtime.

- [ ] **Step 7: Request separate permission and update the installed global skill**

Before editing `~/.codex/skills/rkf-auto-connect/SKILL.md`, request filesystem approval because the file is outside the repository. Replace the skill's setup/connection/commands contract with these exact rules:

```markdown
## Session Boundary

- Every new Codex task starts with RKF OFF.
- A project marker means RKF is available; it never activates RKF.
- Do not query, classify for automatic capture, or write RKF until the user says `啟動 RKF` in the current task.
- On activation, use structured action `rkf.activate` and report its masked receipt.
- Keep one action runtime for the current task. Do not reuse it in another task.
- When the user says `停用 RKF`, call `rkf.deactivate`.

## Activated Research Workflow

1. For a deterministic research trigger, call `query.search` before reading project-local material.
2. Keep RKF and project-local provenance separate in the answer.
3. Route reusable research material through `capture.route`.
4. Report event ID, queued/materialized state, dedupe state, and `Promotion: none`.
5. For uncertain classification, do not auto-query or auto-capture; offer `問 RKF` or `收進 RKF`.

## Prohibited Bypasses

- Do not call `tools/rk.py` for cross-project writes.
- Do not call helper execute commands.
- Do not treat v1 `enabled = true` or v2 `available = true` as ACTIVE.
- Do not silently monitor unrelated ChatGPT web/app conversations.
```

- [ ] **Step 8: Verify the global skill no longer contains a write bypass**

Run after approval and edit:

```bash
rg -n "啟動 RKF|rkf.activate|query.search|capture.route|Promotion: none" ~/.codex/skills/rkf-auto-connect/SKILL.md
rg -n "python3.*tools/rk.py|inbox-execute|hot-execute|enabled = true.*ACTIVE" ~/.codex/skills/rkf-auto-connect/SKILL.md
```

Expected: the first command finds all five required contract terms; the second command returns no matches.

- [ ] **Step 9: Review Task 6 scope without committing**

Run:

```bash
git diff --check
git diff -- tools/rkf_auto_connect.py tests/test_rkf_auto_connect.py
```

Expected: no whitespace errors; repository changes contain no private absolute path and no direct cross-project write command.

---

### Task 7: Configuration, User Documentation, Durable Memory, And Phase Validation

**Files:**
- Modify: `rkf.workspace.example.toml`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`
- Modify: `docs/workflows/rkf-auto-connect.zh-TW.md`
- Modify: `docs/PROJECT_MEMORY.md`
- Modify: `CHANGELOG.md`
- Test: all `tests/`

**Interfaces:**
- Consumes: all Phase 1 behavior and action names.
- Produces: public-safe configuration guidance, natural-language workflow, durable project decision record, and fresh verification evidence.

- [ ] **Step 1: Add a public-safe machine/writer example configuration**

Append to `rkf.workspace.example.toml`:

```toml
[machine]
# Use an opaque stable ID; do not use a personal name, device name, or path.
id = "machine-7f3a2c91"
# Set true only when the shared writer registry names this same opaque ID.
maintenance_writer = false

[sync]
writer_registry = "state/sync/maintenance-writer.json"
event_root = "state/events"
```

Do not modify the ignored live `rkf.workspace.toml` in this phase.

- [ ] **Step 2: Update architecture and feature documentation with exact action flow**

In `docs/ARCHITECTURE.md`, add this state and data flow:

```text
new Codex task -> OFF
啟動 RKF -> read-only preflight -> ACTIVE | ACTIVE_READ_ONLY
research request -> query.search -> central governed result cards -> project-local fallback
reusable source/discussion -> capture.route -> immutable event -> writer projection
停用 RKF -> OFF
```

State explicitly that `inbox.capture` and `hot.record` are writer-side projection actions, not normal cross-project entrypoints.

In `docs/FEATURES_AND_COMMANDS.zh-TW.md`, add these natural-language mappings:

```markdown
| 啟動 RKF | `rkf.activate` | 唯讀 preflight；回傳遮蔽路徑的 session receipt |
| 問 RKF：... | `query.search` | 先查中央 RKF；不足才讀 project-local |
| 收進 RKF：... | `capture.route` | 先寫 immutable event；回報 dedupe、queued/materialized、Promotion: none |
| 停用 RKF | `rkf.deactivate` | 本 task 後續不再查詢或攝入 RKF |
```

- [ ] **Step 3: Rewrite the auto-connect workflow around manual activation**

In `docs/workflows/rkf-auto-connect.zh-TW.md`, ensure the normal workflow is exactly:

```markdown
1. 新 task 預設 RKF OFF。
2. 使用者說「啟動 RKF」。
3. Agent 執行 `rkf.activate`，先回報 ACTIVE 或 ACTIVE_READ_ONLY 與 warning。
4. 研究型請求先執行 `query.search`，再視不足處讀 project-local 資料。
5. DOI、URL、paper lead 或可重用研究討論經 `capture.route` 進入 event queue。
6. 回報 event ID、dedupe、queued/materialized 與 `Promotion: none`。
7. 使用者說「停用 RKF」後執行 `rkf.deactivate`。
```

Remove instructions that imply project markers or trigger detection activate RKF automatically. Remove every cross-project `tools/rk.py` write example.

- [ ] **Step 4: Record durable decisions and delivered behavior**

Append a dated Phase 1 entry to `docs/PROJECT_MEMORY.md` containing:

```markdown
- RKF 1.1 Phase 1 uses a session-owned `RKFActionRuntime`: every task starts OFF, activation preflight is read-only, and no active default is persisted.
- `query.search` is deterministic and read-only; the global auto-connect workflow queries central RKF before project-local research material only after activation.
- `capture.route` writes a public-safe immutable event first. Non-writers queue events; the designated writer may materialize inbox/hot projections. No stable promotion occurs.
- v1 and v2 project markers mean available, never active. The installed global skill must not call the legacy CLI for writes.
- Verified commands: `python3 -m unittest discover -s tests`, Python compilation, RKF lint, public-safety scan, private-path scan, and `git diff --check`.
```

Add a concise Phase 1 feature entry to `CHANGELOG.md`; do not mention private inventory paths or machine names.

- [ ] **Step 5: Run focused Phase 1 tests**

Run:

```bash
python3 -m unittest tests.test_rkf_session tests.test_rkf_retrieval tests.test_rkf_events tests.test_rkf_capture tests.test_rkf_actions tests.test_rkf_auto_connect
```

Expected: all Phase 1 tests pass with `OK` and zero failures.

- [ ] **Step 6: Run the full repository test and compile suite**

Run:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tools/rk.py tools/rkf_auto_connect.py rkf/*.py tools/public_safety_scan.py
```

Expected: unittest reports `OK`; compilation exits 0 with no output.

- [ ] **Step 7: Run RKF lint and public/private safety checks**

Run:

```bash
python3 tools/rk.py lint --mode all
python3 tools/rk.py topic lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/public_safety_scan.py
```

Expected: all lint/safety commands pass; the public-safety scanner reports no private paths in Phase 1 runtime or public outputs.

- [ ] **Step 8: Verify the critical user flows from a temporary fixture**

Run a dedicated integration test from `tests/test_rkf_actions.py` and `tests/test_rkf_capture.py`:

```bash
python3 -m unittest \
  tests.test_rkf_actions.RKFActionsTests.test_new_runtime_blocks_all_non_control_actions_before_io \
  tests.test_rkf_actions.RKFActionsTests.test_activate_status_and_deactivate_share_one_runtime \
  tests.test_rkf_actions.RKFActionsTests.test_query_search_is_available_only_after_activation \
  tests.test_rkf_capture.RKFCaptureTests.test_writer_materializes_inbox_and_hot_after_event
```

Expected: `Ran 4 tests` and `OK`.

- [ ] **Step 9: Perform final scoped diff review without committing**

Run:

```bash
git diff --check
git status --short
git diff --stat
git diff -- rkf tools/rkf_auto_connect.py tests schemas rkf.workspace.example.toml docs/ARCHITECTURE.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/workflows/rkf-auto-connect.zh-TW.md docs/PROJECT_MEMORY.md CHANGELOG.md
```

Expected: no whitespace errors; changes are limited to Phase 1 files plus the already approved spec/plan documents. Confirm explicitly that live wiki/raw roots, 57 paper pages, automations, Obsidian settings, and cleanup targets were not modified.

## Phase 1 Completion Gate

Phase 1 is ready for user review only when all of the following are evidenced in the same execution run:

- a fresh runtime blocks query/capture before activation without wiki/raw I/O;
- activation is read-only, returns masked handles, and degrades on conflict/schema mismatch;
- activated `query.search` returns deterministic maturity-aware cards and writes nothing;
- `capture.route` creates an immutable event, deduplicates DOI/URL/title/fingerprint/recent intent, and reports `Promotion: none`;
- non-writer capture remains queued while a registered writer can materialize existing inbox/hot projections;
- v1/v2 markers never imply ACTIVE;
- the global skill contains no legacy CLI write bypass;
- all focused/full tests, compilation, lint, public-safety, private-path, and diff checks pass;
- no live paper migration, automation, Obsidian, cleanup, commit, or push occurred.

After Phase 1 review, write the separate Phase 2 plan for the 57-paper golden-corpus schema and preview migration. Do not treat Phase 1 approval as authorization for live migration.
