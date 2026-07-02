# RKF Codex Action Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend RKF's Codex app-facing action layer with structured report actions and a compact health snapshot, without adding any new user-facing CLI surface.

**Architecture:** Keep domain logic in `rkf/core.py`, keep structured dispatch in `rkf/actions.py`, and make the legacy CLI shim delegate to the same action helpers where practical. The first slice adds report/read actions plus `stats.snapshot`; graph traversal, MCP, UI, and private multi-format ingest remain future slices.

**Tech Stack:** Python standard library, `unittest`, Markdown docs, existing RKF `Workspace` and core helpers.

---

## File Structure

- Modify: `tests/test_rkf_actions.py`
  - Owns direct structured-action contract tests.
  - New tests define payload shapes for report/read actions and `stats.snapshot`.
- Modify: `rkf/actions.py`
  - Owns app-facing `ActionRequest` dispatch and `ActionResult` payloads.
  - Adds wrappers for existing core behavior and a read-only health snapshot.
- Modify: `rkf/cli.py`
  - Keeps legacy/dev shim behavior compatible while delegating report paths to actions.
  - No new user-facing parser commands are added.
- Modify: `docs/ARCHITECTURE.md`
  - Records that `rkf.actions` now covers report/read actions and `stats.snapshot`.
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`
  - Updates the Codex app workflow inventory and legacy runtime boundary.
- Modify: `docs/PROJECT_MEMORY.md`
  - Records the durable app-facing action contract and canonical health snapshot route.

## Task 1: Define Report Action Contracts

**Files:**
- Modify: `tests/test_rkf_actions.py`

- [ ] **Step 1: Add imports for core seeding helpers**

Replace the existing import block:

```python
from rkf.actions import ActionRequest, execute_action_request
from rkf.core import Workspace
```

with:

```python
from rkf.actions import ActionRequest, execute_action_request
from rkf.core import Workspace, create_paper_note, create_source
```

- [ ] **Step 2: Add a source/paper seeding helper to `RKFActionsTests`**

Add this method inside `RKFActionsTests`, after `tearDown()`:

```python
    def seed_paper(self, *, doi: str = "10.1234/report.action") -> str:
        record = create_source(
            self.workspace,
            kind="doi",
            value=doi,
            title="Report Action Paper",
            topic_id="",
            note="",
        )
        create_paper_note(self.workspace, record)
        return str(record["source_id"])
```

- [ ] **Step 3: Add failing tests for report/read actions**

Add these test methods at the end of `RKFActionsTests`, before `if __name__ == "__main__":`:

```python
    def test_report_actions_return_structured_payloads(self) -> None:
        source_id = self.seed_paper()

        world = execute_action_request(
            ActionRequest(action="world.render", params={"log_tail": 1}),
            workspace=self.workspace,
        )
        self.assertEqual(world.status, "ok")
        self.assertIn("RKF Workspace Status", world.payload["markdown"])
        self.assertEqual(world.payload["counts"]["sources"], 1)
        self.assertEqual(world.payload["counts"]["knowledge_pages"], 1)

        queue = execute_action_request(
            ActionRequest(action="paper.queue", params={"limit": 5}),
            workspace=self.workspace,
        )
        self.assertEqual(queue.status, "ok")
        self.assertEqual(queue.payload["count"], 1)
        self.assertEqual(queue.payload["items"][0]["source_id"], source_id)

        lint = execute_action_request(
            ActionRequest(action="lint.run", params={"mode": "all"}),
            workspace=self.workspace,
        )
        self.assertEqual(lint.status, "ok")
        self.assertTrue(lint.payload["passed"])
        self.assertEqual(lint.payload["errors"], [])

        graph = execute_action_request(
            ActionRequest(action="graph.export"),
            workspace=self.workspace,
        )
        self.assertEqual(graph.status, "ok")
        self.assertEqual(graph.payload["path"], "graph/research_graph.json")
        self.assertGreaterEqual(graph.payload["node_count"], 1)
        self.assertGreaterEqual(graph.payload["edge_count"], 1)

        index = execute_action_request(
            ActionRequest(action="index.generate"),
            workspace=self.workspace,
        )
        self.assertEqual(index.status, "ok")
        self.assertEqual(index.payload["path"], "index.md")
        self.assertTrue((self.root / "index.md").exists())

        handoff = execute_action_request(
            ActionRequest(action="codex_handoff.generate"),
            workspace=self.workspace,
        )
        self.assertEqual(handoff.status, "ok")
        self.assertEqual(handoff.payload["path"], "prompts/codex_handoff_context.md")
        self.assertTrue((self.root / "prompts" / "codex_handoff_context.md").exists())
```

- [ ] **Step 4: Run the focused action tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_report_actions_return_structured_payloads -v
```

Expected: FAIL with `unsupported RKF action: world.render`.

Do not commit or implement anything before seeing this failure.

## Task 2: Implement Report Actions

**Files:**
- Modify: `rkf/actions.py`
- Test: `tests/test_rkf_actions.py`

- [ ] **Step 1: Update imports in `rkf/actions.py`**

Replace the current core import block:

```python
from .core import (
    Workspace,
    create_inbox_item,
    record_hot_query,
    refresh_hot_markdown,
)
```

with:

```python
from .core import (
    Workspace,
    codex_handoff_capsule,
    create_inbox_item,
    export_graph,
    generate_wiki_index,
    knowledge_page_records,
    lint_ars_handoff,
    lint_graph_links,
    lint_knowledge_pages,
    lint_public_safety,
    lint_topics,
    paper_queue,
    recent_hot_events,
    read_json,
    record_hot_query,
    refresh_hot_markdown,
    relative_workspace_path,
    render_workspace_status,
)
```

- [ ] **Step 2: Add action lint mode constants and a count helper**

Add this code after `_workspace()`:

```python
ACTION_LINT_MODES = {
    "all",
    "structure-lint",
    "evidence-lint",
    "graph-lint",
    "ars-handoff-lint",
    "public-safety-lint",
    "repair-plan",
}


def _workspace_counts(ws: Workspace) -> dict[str, int]:
    return {
        "knowledge_pages": len(knowledge_page_records(ws)),
        "sources": len(list(ws.paths.sources.glob("*.json"))) if ws.paths.sources.exists() else 0,
        "evidence_artifacts": len(list(ws.paths.evidence_index.glob("*.json"))) if ws.paths.evidence_index.exists() else 0,
        "topics": len(ws.load_topics()),
    }
```

- [ ] **Step 3: Add a shared lint helper**

Add this code after `_workspace_counts()`:

```python
def _lint_errors(ws: Workspace, mode: str) -> list[str]:
    if mode not in ACTION_LINT_MODES:
        raise SystemExit(f"unknown lint mode: {mode}")
    errors: list[str] = []
    if mode in {"all", "structure-lint", "evidence-lint"}:
        errors.extend(lint_knowledge_pages(ws))
    if mode in {"all", "structure-lint"}:
        errors.extend(lint_topics(ws))
    if mode in {"all", "graph-lint"}:
        errors.extend(lint_graph_links(ws))
    if mode in {"all", "ars-handoff-lint"}:
        errors.extend(lint_ars_handoff(ws))
    if mode == "public-safety-lint":
        errors.extend(lint_public_safety(ws))
    return errors
```

- [ ] **Step 4: Add report action functions**

Add this code after `record_hot()`:

```python
def render_world(
    *,
    workspace: Workspace | Path | None = None,
    log_tail: int = 5,
) -> ActionResult:
    ws = _workspace(workspace)
    markdown = render_workspace_status(ws, log_tail=log_tail)
    return ActionResult(
        action="world.render",
        status="ok",
        message="rendered RKF world context",
        payload={"markdown": markdown, "counts": _workspace_counts(ws), "log_tail": log_tail},
    )


def queue_papers(
    *,
    workspace: Workspace | Path | None = None,
    limit: int = 20,
) -> ActionResult:
    ws = _workspace(workspace)
    items = paper_queue(ws)
    limited = items[:limit]
    return ActionResult(
        action="paper.queue",
        status="ok",
        message=f"found {len(items)} active paper nudges",
        payload={"items": limited, "count": len(items), "limit": limit},
    )


def run_lint(
    *,
    workspace: Workspace | Path | None = None,
    mode: str = "all",
) -> ActionResult:
    ws = _workspace(workspace)
    errors = _lint_errors(ws, mode)
    passed = not errors
    return ActionResult(
        action="lint.run",
        status="ok" if passed else "failed",
        message=f"rkf {mode} {'passed' if passed else 'failed'}",
        payload={"mode": mode, "passed": passed, "errors": errors},
    )


def export_graph_action(*, workspace: Workspace | Path | None = None) -> ActionResult:
    ws = _workspace(workspace)
    graph = export_graph(ws)
    rel_path = relative_workspace_path(ws, ws.paths.graph / "research_graph.json")
    return ActionResult(
        action="graph.export",
        status="ok",
        message=f"exported graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges",
        payload={
            "path": rel_path,
            "node_count": len(graph["nodes"]),
            "edge_count": len(graph["edges"]),
            "graph": graph,
        },
    )


def generate_index(*, workspace: Workspace | Path | None = None) -> ActionResult:
    ws = _workspace(workspace)
    path = generate_wiki_index(ws)
    rel_path = relative_workspace_path(ws, path)
    return ActionResult(
        action="index.generate",
        status="ok",
        message=f"generated wiki index: {rel_path}",
        payload={"path": rel_path},
    )


def generate_codex_handoff(*, workspace: Workspace | Path | None = None) -> ActionResult:
    ws = _workspace(workspace)
    path = codex_handoff_capsule(ws)
    rel_path = relative_workspace_path(ws, path)
    return ActionResult(
        action="codex_handoff.generate",
        status="ok",
        message=f"generated Codex handoff context: {rel_path}",
        payload={"path": rel_path},
    )
```

- [ ] **Step 5: Dispatch report actions**

Replace `execute_action_request()` with:

```python
def execute_action_request(request: ActionRequest, *, workspace: Workspace | Path | None = None) -> ActionResult:
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
        return export_graph_action(workspace=workspace, **params)
    if request.action == "index.generate":
        return generate_index(workspace=workspace, **params)
    if request.action == "codex_handoff.generate":
        return generate_codex_handoff(workspace=workspace, **params)
    raise SystemExit(f"unsupported RKF action: {request.action}")
```

- [ ] **Step 6: Run focused tests and verify report actions pass**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_report_actions_return_structured_payloads -v
```

Expected: PASS.

- [ ] **Step 7: Run all action tests**

Run:

```bash
python3 -m unittest tests.test_rkf_actions -v
```

Expected: all tests in `tests.test_rkf_actions` pass.

- [ ] **Step 8: Commit report action implementation**

Run:

```bash
git add rkf/actions.py tests/test_rkf_actions.py
git commit -m "feat: add RKF report actions"
```

Expected: commit succeeds with report action tests and implementation staged.

## Task 3: Define And Implement `stats.snapshot`

**Files:**
- Modify: `tests/test_rkf_actions.py`
- Modify: `rkf/actions.py`

- [ ] **Step 1: Add a failing `stats.snapshot` test**

Add this test method at the end of `RKFActionsTests`, before `if __name__ == "__main__":`:

```python
    def test_stats_snapshot_summarizes_review_health_without_writes(self) -> None:
        source_id = self.seed_paper(doi="10.1234/stats.snapshot")
        before_files = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())

        result = execute_action_request(
            ActionRequest(action="stats.snapshot", params={"paper_limit": 3}),
            workspace=self.workspace,
        )

        after_files = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*") if path.is_file())
        self.assertEqual(after_files, before_files)
        self.assertEqual(result.action, "stats.snapshot")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["counts"]["sources"], 1)
        self.assertEqual(result.payload["counts"]["knowledge_pages"], 1)
        self.assertEqual(result.payload["counts"]["paper_queue"], 1)
        self.assertEqual(result.payload["distributions"]["knowledge_types"]["paper"], 1)
        self.assertEqual(result.payload["distributions"]["claim_readiness"]["not-ready"], 1)
        self.assertEqual(result.payload["top_paper_nudges"][0]["source_id"], source_id)
        self.assertIn("review the top paper nudges", result.payload["next_actions"][0])
```

- [ ] **Step 2: Run the `stats.snapshot` test and verify it fails**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_stats_snapshot_summarizes_review_health_without_writes -v
```

Expected: FAIL with `unsupported RKF action: stats.snapshot`.

- [ ] **Step 3: Add imports needed by `stats.snapshot`**

In `rkf/actions.py`, add this import near the top:

```python
from collections import Counter
```

In the existing `.core` import block, add `recent_hot_events` if it is not already present from Task 2.

- [ ] **Step 4: Add counter and snapshot helpers**

Add this code after `_lint_errors()`:

```python
def _counter_dict(values: list[str]) -> dict[str, int]:
    return dict(Counter(values).most_common())


def _source_status_counts(ws: Workspace) -> dict[str, int]:
    if not ws.paths.sources.exists():
        return {}
    statuses: list[str] = []
    for path in sorted(ws.paths.sources.glob("*.json")):
        record = read_json(path)
        statuses.append(str(record.get("status", "unknown")))
    return _counter_dict(statuses)


def _evidence_status_counts(ws: Workspace) -> dict[str, int]:
    if not ws.paths.evidence_index.exists():
        return {}
    statuses: list[str] = []
    for path in sorted(ws.paths.evidence_index.glob("*.json")):
        record = read_json(path)
        statuses.append(str(record.get("status", "unknown")))
    return _counter_dict(statuses)


def _knowledge_distributions(ws: Workspace) -> dict[str, dict[str, int]]:
    records = knowledge_page_records(ws)
    return {
        "knowledge_types": _counter_dict([str(meta.get("type", "unknown")) for _, meta, _ in records]),
        "paper_reading_state": _counter_dict(
            [
                str(meta.get("reading_state", meta.get("reading_status", "unknown")))
                for _, meta, _ in records
                if meta.get("type") == "paper"
            ]
        ),
        "fulltext_status": _counter_dict(
            [str(meta.get("fulltext_status", "unknown")) for _, meta, _ in records if meta.get("type") == "paper"]
        ),
        "claim_readiness": _counter_dict(
            [
                str(meta.get("claim_readiness", "unknown"))
                for _, meta, _ in records
                if meta.get("type") in {"paper", "claim", "synthesis"}
            ]
        ),
        "synthesis_maturity": _counter_dict(
            [str(meta.get("synthesis_maturity", "unknown")) for _, meta, _ in records if meta.get("type") == "synthesis"]
        ),
    }
```

- [ ] **Step 5: Add the `snapshot_stats()` action**

Add this code after `generate_codex_handoff()`:

```python
def snapshot_stats(
    *,
    workspace: Workspace | Path | None = None,
    paper_limit: int = 8,
    lint_mode: str = "all",
) -> ActionResult:
    ws = _workspace(workspace)
    queue_items = paper_queue(ws)
    hot_events = recent_hot_events(ws) if ws.paths.hot_md.exists() else []
    lint_errors = _lint_errors(ws, lint_mode)
    counts = _workspace_counts(ws)
    counts.update(
        {
            "paper_queue": len(queue_items),
            "hot_queries": len(hot_events),
            "lint_errors": len(lint_errors),
        }
    )
    distributions = {
        "source_status": _source_status_counts(ws),
        "evidence_status": _evidence_status_counts(ws),
        **_knowledge_distributions(ws),
    }
    next_actions: list[str] = []
    if queue_items:
        next_actions.append("review the top paper nudges before promoting claims")
    if lint_errors:
        next_actions.append(f"resolve {len(lint_errors)} lint finding(s) before publishing or trusting synthesis")
    if not next_actions:
        next_actions.append("no deterministic RKF health blocker detected in this snapshot")
    return ActionResult(
        action="stats.snapshot",
        status="ok" if not lint_errors else "blocked",
        message=f"snapshot: {counts['paper_queue']} paper nudges, {counts['lint_errors']} lint findings",
        payload={
            "counts": counts,
            "distributions": distributions,
            "top_paper_nudges": queue_items[:paper_limit],
            "lint": {"mode": lint_mode, "passed": not lint_errors, "errors": lint_errors},
            "next_actions": next_actions,
        },
    )
```

- [ ] **Step 6: Dispatch `stats.snapshot`**

In `execute_action_request()`, add this branch before the final unsupported-action error:

```python
    if request.action == "stats.snapshot":
        return snapshot_stats(workspace=workspace, **params)
```

- [ ] **Step 7: Run the `stats.snapshot` test**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_stats_snapshot_summarizes_review_health_without_writes -v
```

Expected: PASS.

- [ ] **Step 8: Run all direct action tests**

Run:

```bash
python3 -m unittest tests.test_rkf_actions -v
```

Expected: all tests in `tests.test_rkf_actions` pass.

- [ ] **Step 9: Commit stats snapshot**

Run:

```bash
git add rkf/actions.py tests/test_rkf_actions.py
git commit -m "feat: add RKF stats snapshot action"
```

Expected: commit succeeds with only action tests and action runtime changes staged.

## Task 4: Make Legacy CLI Report Paths Delegate To Actions

**Files:**
- Modify: `rkf/cli.py`
- Test: `tests/test_rkf_cli.py`

- [ ] **Step 1: Add imports for report actions**

Replace the current action import block:

```python
from .actions import capture_inbox as action_capture_inbox
from .actions import record_hot as action_record_hot
```

with:

```python
from .actions import capture_inbox as action_capture_inbox
from .actions import export_graph_action as action_export_graph
from .actions import generate_codex_handoff as action_generate_codex_handoff
from .actions import generate_index as action_generate_index
from .actions import queue_papers as action_queue_papers
from .actions import record_hot as action_record_hot
from .actions import render_world as action_render_world
from .actions import run_lint as action_run_lint
```

- [ ] **Step 2: Remove direct core imports that become unused**

From the `.core` import block in `rkf/cli.py`, remove these names after replacing the command bodies in this task:

```python
codex_handoff_capsule,
export_graph,
generate_wiki_index,
lint_ars_handoff,
lint_graph_links,
lint_knowledge_pages,
lint_public_safety,
lint_topics,
render_workspace_status,
```

Keep `paper_queue` because `cmd_paper_status()`, `cmd_paper_next()`, and `cmd_paper_nudge()` still use it.

- [ ] **Step 3: Replace `cmd_lint()` body**

Replace the full `cmd_lint()` function with:

```python
def cmd_lint(args: argparse.Namespace) -> int:
    ws = Workspace()
    result = action_run_lint(workspace=ws, mode=args.mode)
    errors = result.payload["errors"]
    if errors:
        print(f"rkf {args.mode} failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    if args.mode == "repair-plan":
        print("repair-plan: no deterministic repair needed")
    else:
        print(f"rkf {args.mode} passed")
    return 0
```

- [ ] **Step 4: Replace `cmd_paper_queue()` body**

Replace the full `cmd_paper_queue()` function with:

```python
def cmd_paper_queue(args: argparse.Namespace) -> int:
    ws = Workspace()
    result = action_queue_papers(workspace=ws, limit=args.limit)
    items = result.payload["items"]
    if not items:
        print("paper queue is empty")
        return 0
    for item in items:
        print(f"- {item['source_id']}\taction={item['action']}\tpriority={item['priority']}\tpath={item.get('path', '')}")
        print(f"  reasons: {'; '.join(item['reasons'])}")
    return 0
```

- [ ] **Step 5: Replace graph, world, index, and handoff command bodies**

Replace these functions:

```python
def cmd_graph(args: argparse.Namespace) -> int:
    ws = Workspace()
    result = action_export_graph(workspace=ws)
    print(f"graph nodes: {result.payload['node_count']}")
    print(f"graph edges: {result.payload['edge_count']}")
    print(f"wrote: {result.payload['path']}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ws = Workspace()
    result = action_render_world(workspace=ws, log_tail=args.log_tail)
    print(result.payload["markdown"], end="")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    ws = Workspace()
    result = action_generate_index(workspace=ws)
    print(f"wrote: {result.payload['path']}")
    return 0


def cmd_prompt_codex_handoff(args: argparse.Namespace) -> int:
    ws = Workspace()
    result = action_generate_codex_handoff(workspace=ws)
    print(f"wrote: {result.payload['path']}")
    return 0
```

- [ ] **Step 6: Run focused CLI compatibility tests**

Run:

```bash
python3 -m unittest \
  tests.test_rkf_cli.RKFCliTests.test_graph_lint_finds_dangling_source_and_evidence_links \
  tests.test_rkf_cli.RKFCliTests.test_status_and_world_print_workspace_bootstrap \
  tests.test_rkf_cli.RKFCliTests.test_qced_pdf_can_be_distilled_and_graphed \
  tests.test_rkf_cli.RKFCliTests.test_topic_lint_and_codex_handoff_capsule \
  -v
```

Expected: all four tests pass.

- [ ] **Step 7: Run all CLI tests**

Run:

```bash
python3 -m unittest tests.test_rkf_cli -v
```

Expected: all tests in `tests.test_rkf_cli` pass.

- [ ] **Step 8: Commit CLI delegation**

Run:

```bash
git add rkf/cli.py tests/test_rkf_cli.py
git commit -m "refactor: delegate RKF report CLI paths to actions"
```

Expected: commit succeeds. `tests/test_rkf_cli.py` may have no staged diff if existing compatibility tests were enough.

## Task 5: Update Documentation And Project Memory

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`
- Modify: `docs/PROJECT_MEMORY.md`

- [ ] **Step 1: Update `docs/ARCHITECTURE.md` runtime surface**

In `docs/ARCHITECTURE.md`, replace the `rkf.actions` bullet under `## Runtime Surfaces` with:

```markdown
- `rkf.actions`: structured Codex app action API. It covers
  `inbox.capture`, `hot.record`, report/read actions (`world.render`,
  `paper.queue`, `lint.run`, `graph.export`, `index.generate`,
  `codex_handoff.generate`), and `stats.snapshot` for compact health review.
  Actions return `ActionResult` objects for agent-facing summaries and tests.
```

- [ ] **Step 2: Update `docs/FEATURES_AND_COMMANDS.zh-TW.md` capability table**

In the core feature table, replace the `Action runtime` row with:

```markdown
| Action runtime | 讓 Codex app / auto-connect 以 structured request 執行 RKF write path 與 report/read path | `rkf/actions.py` |
```

Add this row immediately after `L0-L3 world context`:

```markdown
| Health snapshot | 以 Codex app report 顯示 sources、paper queue、claim readiness、maturity、hot-query 與 lint 摘要 | `stats.snapshot` action |
```

- [ ] **Step 3: Update `docs/FEATURES_AND_COMMANDS.zh-TW.md` workflow inventory**

Add this workflow row immediately after `Paper queue`:

```markdown
| Health snapshot | 「幫我看 RKF 今天最需要處理什麼。」 | Read-only report；不提升 evidence maturity |
```

In `## Legacy Runtime Boundary`, replace the paragraph with:

```markdown
現有 `tools/rk.py` / `rkf/cli.py` 保留為 legacy/dev shim，供 Codex app agent、測試與維護使用。`rkf.actions` 已支援 `inbox.capture`、`hot.record`、常用 report/read actions 與 `stats.snapshot`；auto-connect 也可直接執行已支援的 action。CLI 不是正式使用者控制介面。新增或修改能力時，優先描述 Codex app 工作流與 RKF action 邊界；不要新增面向使用者的 CLI 教學。
```

- [ ] **Step 4: Update `docs/PROJECT_MEMORY.md` durable decisions**

Replace the durable-decision bullet that begins with ``- `rkf.actions` currently covers`` with:

```markdown
- `rkf.actions` is the Codex app-facing runtime boundary. It covers
  `inbox.capture`, `hot.record`, report/read actions (`world.render`,
  `paper.queue`, `lint.run`, `graph.export`, `index.generate`,
  `codex_handoff.generate`), and the read-only `stats.snapshot` health report.
  The legacy CLI delegates shared report paths to these actions where practical
  so Codex app and maintenance behavior do not drift.
```

- [ ] **Step 5: Run doc-focused checks**

Run:

```bash
rg -n "stats.snapshot|world.render|paper.queue|lint.run|graph.export|index.generate|codex_handoff.generate" docs/ARCHITECTURE.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/PROJECT_MEMORY.md
python3 tools/public_safety_scan.py
git diff --check
```

Expected:

- `rg` prints all three documentation files.
- `public_safety_scan passed`.
- `git diff --check` prints no output.

- [ ] **Step 6: Commit docs**

Run:

```bash
git add docs/ARCHITECTURE.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/PROJECT_MEMORY.md
git commit -m "docs: document RKF action dashboard runtime"
```

Expected: commit succeeds with only documentation changes staged.

## Task 6: Full Verification

**Files:**
- Verify: `rkf/actions.py`
- Verify: `rkf/cli.py`
- Verify: `tests/test_rkf_actions.py`
- Verify: `tests/test_rkf_cli.py`
- Verify: documentation changed in Task 5

- [ ] **Step 1: Compile Python files**

Run:

```bash
python3 -m py_compile tools/rk.py tools/rkf_auto_connect.py rkf/*.py tools/public_safety_scan.py
```

Expected: command exits 0 with no output.

- [ ] **Step 2: Run direct action tests**

Run:

```bash
python3 -m unittest tests.test_rkf_actions -v
```

Expected: all direct action tests pass, including report actions and `stats.snapshot`.

- [ ] **Step 3: Run all unit tests**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: all repo tests pass.

- [ ] **Step 4: Run RKF internal validation through the existing maintenance shim**

Run:

```bash
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/rk.py paper queue
python3 tools/rk.py world --log-tail 1
```

Expected:

- `topic lint passed`
- `rkf all passed`
- `paper queue` prints active queue items or `paper queue is empty`
- `world` prints `RKF Workspace Status`

- [ ] **Step 5: Run public safety and whitespace checks**

Run:

```bash
python3 tools/public_safety_scan.py
git diff --check
```

Expected:

- `public_safety_scan passed`
- `git diff --check` prints no output

- [ ] **Step 6: Inspect final diff**

Run:

```bash
git status --short
git diff --stat HEAD
```

Expected:

- only files from this plan are modified;
- no generated `prompts/codex_handoff_context.md`, `graph/research_graph.json`, `index.md`, or live `hot.md` changes are accidentally staged unless a test fixture explicitly owns them.

- [ ] **Step 7: Commit final verification fixes if needed**

If Step 1 through Step 6 required a small correction, run:

```bash
git add rkf/actions.py rkf/cli.py tests/test_rkf_actions.py tests/test_rkf_cli.py docs/ARCHITECTURE.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/PROJECT_MEMORY.md
git commit -m "fix: stabilize RKF action dashboard"
```

Expected: commit succeeds only when there are corrective changes. If there are no changes after Step 6, skip this commit.

## Handoff Notes

- Do not add new user-facing CLI commands.
- Do not implement MCP, browser dashboard, graph traversal, paper review cards, or multi-format ingest in this plan.
- `stats.snapshot` must be read-only. Its test records the workspace file list before and after execution to protect that boundary.
- Report actions that intentionally write generated artifacts are limited to `graph.export`, `index.generate`, and `codex_handoff.generate`.
- Keep candidates, ARS outputs, hot queries, and route notes below the evidence boundary in every report message and payload.
