# RKF Graph Traversal Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only `graph.neighbors`, `graph.paths`, and `graph.page_context` actions so Codex can traverse public-safe RKF graph context without adding a user-facing CLI surface.

**Architecture:** Extract a pure graph builder in `rkf/core.py`, keep `graph.export` as the only graph action that writes `graph/research_graph.json`, and add traversal helpers that work from the pure in-memory graph. Expose those helpers through `rkf.actions` as structured `ActionResult` payloads, with direct `unittest` coverage and docs that describe the actions as Codex app context tools.

**Tech Stack:** Python standard library, `unittest`, Markdown docs, existing RKF `Workspace`, `ActionRequest`, `ActionResult`, and graph export data shape.

---

## File Structure

- Modify: `tests/test_rkf_actions.py`
  - Owns direct `ActionRequest` / `ActionResult` behavior.
  - Adds red tests for neighbors, paths, page context, missing nodes, bad parameters, and read-only traversal.
- Modify: `rkf/core.py`
  - Owns graph construction and traversal domain logic.
  - Extracts `build_research_graph(ws)` from `export_graph(ws)`.
  - Adds traversal helpers that do not write generated graph files.
- Modify: `rkf/actions.py`
  - Owns app-facing action dispatch and message shaping.
  - Adds wrappers for `graph.neighbors`, `graph.paths`, and `graph.page_context`.
- Modify: `docs/ARCHITECTURE.md`
  - Records graph traversal as part of the action runtime and research graph layer.
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`
  - Adds graph traversal to the Codex app capability map.
- Modify: `docs/PROJECT_MEMORY.md`
  - Records the durable decision that traversal actions are read-only and `graph.export` remains the writing route.

## Task 1: Add Red Action Tests

**Files:**
- Modify: `tests/test_rkf_actions.py`

- [ ] **Step 1: Add a graph seed helper**

Add this helper inside `RKFActionsTests`, after the existing `seed_paper()` helper:

```python
    def seed_graph_paper(self, *, doi: str = "10.1234/graph.traversal") -> tuple[str, str, str]:
        topic_id = "cloud-microphysics"
        record = create_source(
            self.workspace,
            kind="doi",
            value=doi,
            title="Graph Traversal Paper",
            topic_id=topic_id,
            note="Public-safe graph traversal seed.",
        )
        create_paper_note(self.workspace, record)
        source_id = str(record["source_id"])
        paper_id = f"papers/{source_id}"
        return source_id, paper_id, topic_id
```

- [ ] **Step 2: Add the neighbors test**

Add this test method near the existing action tests:

```python
    def test_graph_neighbors_returns_public_safe_edges_without_writing_export(self) -> None:
        source_id, paper_id, topic_id = self.seed_graph_paper()
        graph_path = self.root / "graph" / "research_graph.json"
        self.assertFalse(graph_path.exists())

        result = execute_action_request(
            ActionRequest(
                action="graph.neighbors",
                params={"node_id": paper_id, "direction": "both", "limit": 10},
            ),
            workspace=self.workspace,
        )

        self.assertEqual(result.action, "graph.neighbors")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["node"]["id"], paper_id)
        neighbor_ids = {node["id"] for node in result.payload["neighbors"]}
        self.assertIn(source_id, neighbor_ids)
        self.assertIn(topic_id, neighbor_ids)
        edge_types = {edge["type"] for edge in result.payload["edges"]}
        self.assertIn("derived-from", edge_types)
        self.assertIn("tagged-with", edge_types)
        self.assertEqual(result.payload["direction"], "both")
        self.assertFalse(graph_path.exists())
```

- [ ] **Step 3: Add the path and page-context tests**

Add these test methods after the neighbors test:

```python
    def test_graph_paths_returns_shortest_public_safe_path(self) -> None:
        _source_id, paper_id, topic_id = self.seed_graph_paper()

        result = execute_action_request(
            ActionRequest(
                action="graph.paths",
                params={
                    "source_id": paper_id,
                    "target_id": topic_id,
                    "direction": "both",
                    "max_depth": 4,
                    "limit": 5,
                },
            ),
            workspace=self.workspace,
        )

        self.assertEqual(result.action, "graph.paths")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["source"]["id"], paper_id)
        self.assertEqual(result.payload["target"]["id"], topic_id)
        self.assertGreaterEqual(len(result.payload["paths"]), 1)
        first_path = result.payload["paths"][0]
        self.assertEqual(first_path["node_ids"][0], paper_id)
        self.assertEqual(first_path["node_ids"][-1], topic_id)
        self.assertEqual(first_path["length"], 1)
        self.assertEqual(first_path["edges"][0]["type"], "tagged-with")

    def test_graph_page_context_groups_related_nodes(self) -> None:
        source_id, paper_id, topic_id = self.seed_graph_paper()

        result = execute_action_request(
            ActionRequest(action="graph.page_context", params={"page_id": paper_id, "limit": 10}),
            workspace=self.workspace,
        )

        self.assertEqual(result.action, "graph.page_context")
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.payload["page_id"], paper_id)
        self.assertEqual(result.payload["node"]["id"], paper_id)
        self.assertIn(source_id, {node["id"] for node in result.payload["related_sources"]})
        self.assertIn(topic_id, {node["id"] for node in result.payload["related_topics"]})
        self.assertIn("outgoing edge(s)", " ".join(result.payload["summary"]))
        self.assertIn("related topic(s)", " ".join(result.payload["summary"]))
```

- [ ] **Step 4: Add missing-node and bad-parameter tests**

Add these test methods after the page-context test:

```python
    def test_graph_traversal_reports_missing_nodes(self) -> None:
        result = execute_action_request(
            ActionRequest(action="graph.neighbors", params={"node_id": "papers/missing"}),
            workspace=self.workspace,
        )

        self.assertEqual(result.action, "graph.neighbors")
        self.assertEqual(result.status, "not-found")
        self.assertEqual(result.payload["node_id"], "papers/missing")

    def test_graph_traversal_rejects_bad_parameters(self) -> None:
        self.seed_graph_paper()

        bad_direction = execute_action_request(
            ActionRequest(
                action="graph.neighbors",
                params={"node_id": "papers/doi_10_1234_graph_traversal", "direction": "sideways"},
            ),
            workspace=self.workspace,
        )
        self.assertEqual(bad_direction.status, "error")
        self.assertIn("direction must be one of", bad_direction.message)

        bad_depth = execute_action_request(
            ActionRequest(
                action="graph.paths",
                params={
                    "source_id": "papers/doi_10_1234_graph_traversal",
                    "target_id": "cloud-microphysics",
                    "max_depth": 0,
                },
            ),
            workspace=self.workspace,
        )
        self.assertEqual(bad_depth.status, "error")
        self.assertIn("max_depth must be greater than 0", bad_depth.message)
```

- [ ] **Step 5: Run the focused red tests**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_graph_neighbors_returns_public_safe_edges_without_writing_export tests.test_rkf_actions.RKFActionsTests.test_graph_paths_returns_shortest_public_safe_path tests.test_rkf_actions.RKFActionsTests.test_graph_page_context_groups_related_nodes tests.test_rkf_actions.RKFActionsTests.test_graph_traversal_reports_missing_nodes tests.test_rkf_actions.RKFActionsTests.test_graph_traversal_rejects_bad_parameters -v
```

Expected: fail with `unsupported RKF action: graph.neighbors` or the matching unsupported action message for the first new action reached.

Do not implement before seeing this failure.

## Task 2: Extract A Pure Graph Builder

**Files:**
- Modify: `rkf/core.py`
- Test: `tests/test_rkf_actions.py`

- [ ] **Step 1: Replace `export_graph(ws)` with a pure builder plus wrapper**

In `rkf/core.py`, replace the existing `def export_graph(ws: Workspace) -> dict[str, Any]:` block with:

```python
def build_research_graph(ws: Workspace) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for path in sorted(ws.paths.sources.glob("*.json")) if ws.paths.sources.exists() else []:
        record = read_json(path)
        node = {"id": record["source_id"], "type": "source", "status": record.get("status", "")}
        for key in ("reading_state", "fulltext_status"):
            if record.get(key):
                node[key] = record[key]
        nodes.append(node)
        for evidence_id in record.get("evidence_ids", []):
            edges.append({"from": record["source_id"], "to": evidence_id, "type": "has-evidence"})
        for topic_id in record.get("topic_ids", []):
            edges.append({"from": record["source_id"], "to": topic_id, "type": "tagged-with"})
    if ws.paths.knowledge.exists():
        for path in sorted(ws.paths.knowledge.rglob("*.md")):
            meta, _ = parse_frontmatter(read_text(path))
            if not meta:
                continue
            node_id = path.relative_to(ws.paths.knowledge).with_suffix("").as_posix()
            node = {"id": node_id, "type": meta.get("type", "knowledge"), "status": meta.get("status", "")}
            for key in (
                "reading_state",
                "fulltext_status",
                "human_feedback_level",
                "claim_readiness",
                "synthesis_maturity",
                "source_coverage",
            ):
                if meta.get(key):
                    node[key] = meta[key]
            nodes.append(node)
            for evidence_id in meta.get("evidence_ids", []):
                edges.append({"from": node_id, "to": evidence_id, "type": "supported-by"})
            if meta.get("source_id"):
                edges.append({"from": node_id, "to": meta["source_id"], "type": "derived-from"})
            for topic_id in meta.get("topics", []):
                edges.append({"from": node_id, "to": topic_id, "type": "tagged-with"})
    return {"schema": "rkf-graph-v1", "generated": today(), "nodes": nodes, "edges": edges}


def export_graph(ws: Workspace) -> dict[str, Any]:
    graph = build_research_graph(ws)
    write_json(ws.paths.graph / "research_graph.json", graph)
    return graph
```

- [ ] **Step 2: Run existing graph export action coverage**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_report_actions_return_structured_payloads -v
```

Expected: pass. The existing `graph.export` action should still write `graph/research_graph.json`.

- [ ] **Step 3: Commit the pure builder extraction**

Run:

```bash
git add rkf/core.py
git commit -m "refactor: extract pure RKF graph builder"
```

Expected: commit succeeds with only `rkf/core.py` staged.

## Task 3: Add Core Traversal Helpers

**Files:**
- Modify: `rkf/core.py`
- Test: `tests/test_rkf_actions.py`

- [ ] **Step 1: Add graph traversal constants and small helpers**

In `rkf/core.py`, add this code after `export_graph(ws)`:

```python
GRAPH_DIRECTIONS = {"outgoing", "incoming", "both"}


def _graph_error(message: str, **payload: Any) -> dict[str, Any]:
    return {"status": "error", "error": message, **payload}


def _graph_not_found(node_id: str) -> dict[str, Any]:
    return {"status": "not-found", "node_id": node_id, "node": None}


def _normalize_graph_direction(direction: str) -> str:
    value = str(direction or "both")
    if value not in GRAPH_DIRECTIONS:
        raise ValueError("direction must be one of: both, incoming, outgoing")
    return value


def _positive_graph_int(value: int, *, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if number <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return number


def _implicit_graph_node_type(edge: dict[str, Any], endpoint: str) -> str:
    edge_type = str(edge.get("type", ""))
    if endpoint == "to" and edge_type in {"has-evidence", "supported-by"}:
        return "evidence"
    if endpoint == "to" and edge_type == "tagged-with":
        return "topic"
    return "implicit"
```

- [ ] **Step 2: Add node lookup and edge iterator helpers**

Add this code after `_implicit_graph_node_type()`:

```python
def _graph_nodes_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for node in graph.get("nodes", []):
        node_id = str(node.get("id", ""))
        if node_id:
            nodes[node_id] = dict(node)
    for edge in graph.get("edges", []):
        for endpoint in ("from", "to"):
            node_id = str(edge.get(endpoint, ""))
            if node_id and node_id not in nodes:
                nodes[node_id] = {
                    "id": node_id,
                    "type": _implicit_graph_node_type(edge, endpoint),
                    "status": "implicit",
                }
    return nodes


def _iter_graph_edges(
    graph: dict[str, Any],
    node_id: str,
    *,
    direction: str,
) -> list[tuple[dict[str, Any], str]]:
    matches: list[tuple[dict[str, Any], str]] = []
    for edge in graph.get("edges", []):
        from_id = str(edge.get("from", ""))
        to_id = str(edge.get("to", ""))
        if direction in {"outgoing", "both"} and from_id == node_id and to_id:
            matches.append((dict(edge), to_id))
        if direction in {"incoming", "both"} and to_id == node_id and from_id:
            matches.append((dict(edge), from_id))
    return matches
```

- [ ] **Step 3: Add `graph_neighbors()`**

Add this code after `_iter_graph_edges()`:

```python
def graph_neighbors(
    ws: Workspace,
    *,
    node_id: str,
    direction: str = "both",
    limit: int = 20,
) -> dict[str, Any]:
    try:
        normalized_direction = _normalize_graph_direction(direction)
        normalized_limit = _positive_graph_int(limit, name="limit")
    except ValueError as exc:
        return _graph_error(str(exc), node_id=node_id)

    graph = build_research_graph(ws)
    nodes = _graph_nodes_by_id(graph)
    if node_id not in nodes:
        return _graph_not_found(node_id)

    neighbors: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for edge, neighbor_id in _iter_graph_edges(graph, node_id, direction=normalized_direction):
        if neighbor_id in seen:
            continue
        if len(neighbors) >= normalized_limit:
            break
        seen.add(neighbor_id)
        neighbors.append(nodes[neighbor_id])
        edges.append(edge)

    return {
        "status": "ok",
        "node": nodes[node_id],
        "neighbors": neighbors,
        "edges": edges,
        "direction": normalized_direction,
        "limit": normalized_limit,
    }
```

- [ ] **Step 4: Add `graph_paths()`**

Add this code after `graph_neighbors()`:

```python
def graph_paths(
    ws: Workspace,
    *,
    source_id: str,
    target_id: str,
    direction: str = "both",
    max_depth: int = 4,
    limit: int = 5,
) -> dict[str, Any]:
    try:
        normalized_direction = _normalize_graph_direction(direction)
        normalized_depth = _positive_graph_int(max_depth, name="max_depth")
        normalized_limit = _positive_graph_int(limit, name="limit")
    except ValueError as exc:
        return _graph_error(str(exc), source_id=source_id, target_id=target_id)

    graph = build_research_graph(ws)
    nodes = _graph_nodes_by_id(graph)
    if source_id not in nodes:
        return _graph_not_found(source_id)
    if target_id not in nodes:
        return _graph_not_found(target_id)

    queue: list[tuple[str, list[str], list[dict[str, Any]]]] = [(source_id, [source_id], [])]
    paths: list[dict[str, Any]] = []
    while queue and len(paths) < normalized_limit:
        current_id, node_path, edge_path = queue.pop(0)
        if len(edge_path) >= normalized_depth:
            continue
        for edge, next_id in _iter_graph_edges(graph, current_id, direction=normalized_direction):
            if next_id in node_path:
                continue
            next_node_path = [*node_path, next_id]
            next_edge_path = [*edge_path, edge]
            if next_id == target_id:
                paths.append(
                    {
                        "node_ids": next_node_path,
                        "nodes": [nodes[item] for item in next_node_path],
                        "edges": next_edge_path,
                        "length": len(next_edge_path),
                    }
                )
                if len(paths) >= normalized_limit:
                    break
            else:
                queue.append((next_id, next_node_path, next_edge_path))

    return {
        "status": "ok",
        "source": nodes[source_id],
        "target": nodes[target_id],
        "paths": paths,
        "direction": normalized_direction,
        "max_depth": normalized_depth,
        "limit": normalized_limit,
    }
```

- [ ] **Step 5: Add `graph_page_context()`**

Add this code after `graph_paths()`:

```python
def graph_page_context(
    ws: Workspace,
    *,
    page_id: str,
    limit: int = 20,
) -> dict[str, Any]:
    try:
        normalized_limit = _positive_graph_int(limit, name="limit")
    except ValueError as exc:
        return _graph_error(str(exc), page_id=page_id)

    graph = build_research_graph(ws)
    nodes = _graph_nodes_by_id(graph)
    if page_id not in nodes:
        return _graph_not_found(page_id)

    incoming_pairs = _iter_graph_edges(graph, page_id, direction="incoming")[:normalized_limit]
    outgoing_pairs = _iter_graph_edges(graph, page_id, direction="outgoing")[:normalized_limit]
    related_ids: list[str] = []
    for _edge, node_id in [*incoming_pairs, *outgoing_pairs]:
        if node_id not in related_ids:
            related_ids.append(node_id)
    related_nodes = [nodes[node_id] for node_id in related_ids]

    related_sources = [node for node in related_nodes if node.get("type") == "source"]
    related_evidence = [node for node in related_nodes if node.get("type") == "evidence"]
    related_topics = [node for node in related_nodes if node.get("type") == "topic"]
    related_pages = [
        node
        for node in related_nodes
        if node.get("type") not in {"source", "evidence", "topic", "implicit"}
    ]
    summary = [
        f"{len(incoming_pairs)} incoming edge(s)",
        f"{len(outgoing_pairs)} outgoing edge(s)",
        f"{len(related_sources)} related source(s)",
        f"{len(related_evidence)} related evidence item(s)",
        f"{len(related_topics)} related topic(s)",
        f"{len(related_pages)} related page(s)",
    ]

    return {
        "status": "ok",
        "page_id": page_id,
        "node": nodes[page_id],
        "incoming": [edge for edge, _node_id in incoming_pairs],
        "outgoing": [edge for edge, _node_id in outgoing_pairs],
        "related_sources": related_sources,
        "related_evidence": related_evidence,
        "related_topics": related_topics,
        "related_pages": related_pages,
        "summary": summary,
        "limit": normalized_limit,
    }
```

- [ ] **Step 6: Run the focused tests and confirm they still fail at action dispatch**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_graph_neighbors_returns_public_safe_edges_without_writing_export tests.test_rkf_actions.RKFActionsTests.test_graph_paths_returns_shortest_public_safe_path tests.test_rkf_actions.RKFActionsTests.test_graph_page_context_groups_related_nodes tests.test_rkf_actions.RKFActionsTests.test_graph_traversal_reports_missing_nodes tests.test_rkf_actions.RKFActionsTests.test_graph_traversal_rejects_bad_parameters -v
```

Expected: fail with `unsupported RKF action: graph.neighbors`. Core helpers exist, but actions do not dispatch them yet.

- [ ] **Step 7: Keep the red-green slice open**

Do not commit yet. At this point the core traversal helpers exist, but the
action dispatch tests are still red. Leave `rkf/core.py` and
`tests/test_rkf_actions.py` in the working tree and continue to Task 4.

Expected: `git status --short` shows uncommitted changes in `rkf/core.py` and
`tests/test_rkf_actions.py`.

## Task 4: Add Action Wrappers And Dispatch

**Files:**
- Modify: `rkf/actions.py`
- Test: `tests/test_rkf_actions.py`

- [ ] **Step 1: Import the core traversal helpers**

In `rkf/actions.py`, add these names to the existing `.core` import list:

```python
    graph_neighbors,
    graph_page_context,
    graph_paths,
```

- [ ] **Step 2: Add a small result builder for graph traversal actions**

Add this helper after `export_graph_action()`:

```python
def _graph_action_result(*, action: str, payload: dict[str, Any], ok_message: str) -> ActionResult:
    status = str(payload.get("status", "ok"))
    if status == "ok":
        message = ok_message
    elif status == "not-found":
        message = f"graph node not found: {payload.get('node_id', payload.get('page_id', 'unknown'))}"
    else:
        message = str(payload.get("error", "graph traversal failed"))
    return ActionResult(action=action, status=status, message=message, payload=payload)
```

- [ ] **Step 3: Add the three action wrappers**

Add this code after `_graph_action_result()`:

```python
def graph_neighbors_action(
    *,
    workspace: Workspace | Path | None = None,
    node_id: str,
    direction: str = "both",
    limit: int = 20,
) -> ActionResult:
    ws = _workspace(workspace)
    payload = graph_neighbors(ws, node_id=node_id, direction=direction, limit=limit)
    neighbor_count = len(payload.get("neighbors", []))
    return _graph_action_result(
        action="graph.neighbors",
        payload=payload,
        ok_message=f"found {neighbor_count} graph neighbor(s) for {node_id}",
    )


def graph_paths_action(
    *,
    workspace: Workspace | Path | None = None,
    source_id: str,
    target_id: str,
    direction: str = "both",
    max_depth: int = 4,
    limit: int = 5,
) -> ActionResult:
    ws = _workspace(workspace)
    payload = graph_paths(
        ws,
        source_id=source_id,
        target_id=target_id,
        direction=direction,
        max_depth=max_depth,
        limit=limit,
    )
    path_count = len(payload.get("paths", []))
    return _graph_action_result(
        action="graph.paths",
        payload=payload,
        ok_message=f"found {path_count} graph path(s) from {source_id} to {target_id}",
    )


def graph_page_context_action(
    *,
    workspace: Workspace | Path | None = None,
    page_id: str,
    limit: int = 20,
) -> ActionResult:
    ws = _workspace(workspace)
    payload = graph_page_context(ws, page_id=page_id, limit=limit)
    return _graph_action_result(
        action="graph.page_context",
        payload=payload,
        ok_message=f"rendered graph page context for {page_id}",
    )
```

- [ ] **Step 4: Add action dispatch entries**

In `execute_action_request()`, add these branches after the existing `graph.export` branch:

```python
    if request.action == "graph.neighbors":
        return graph_neighbors_action(workspace=workspace, **params)
    if request.action == "graph.paths":
        return graph_paths_action(workspace=workspace, **params)
    if request.action == "graph.page_context":
        return graph_page_context_action(workspace=workspace, **params)
```

- [ ] **Step 5: Run the focused graph traversal tests**

Run:

```bash
python3 -m unittest tests.test_rkf_actions.RKFActionsTests.test_graph_neighbors_returns_public_safe_edges_without_writing_export tests.test_rkf_actions.RKFActionsTests.test_graph_paths_returns_shortest_public_safe_path tests.test_rkf_actions.RKFActionsTests.test_graph_page_context_groups_related_nodes tests.test_rkf_actions.RKFActionsTests.test_graph_traversal_reports_missing_nodes tests.test_rkf_actions.RKFActionsTests.test_graph_traversal_rejects_bad_parameters -v
```

Expected: pass. The neighbors test should also confirm that `graph/research_graph.json` is not created by traversal.

- [ ] **Step 6: Run the whole action test module**

Run:

```bash
python3 -m unittest tests.test_rkf_actions -v
```

Expected: pass. Existing report/read actions should still work.

- [ ] **Step 7: Commit the action dispatch work**

Run:

```bash
git add rkf/core.py rkf/actions.py tests/test_rkf_actions.py
git commit -m "feat: expose RKF graph traversal actions"
```

Expected: commit succeeds with core, action, and test files staged after the
focused graph traversal tests pass.

## Task 5: Update RKF Docs And Project Memory

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`
- Modify: `docs/PROJECT_MEMORY.md`

- [ ] **Step 1: Update the architecture action-runtime wording**

In `docs/ARCHITECTURE.md`, update the action runtime row or nearby action runtime paragraph so it explicitly includes traversal actions:

```markdown
| Action Runtime | Execute Codex app workflow requests without routing through the CLI parser, including read/report actions and read-only graph traversal | `rkf/actions.py`, structured request/result only |
```

Also update the action runtime paragraph near the existing `rkf.actions` section to include:

```markdown
`rkf.actions` also exposes read-only graph traversal actions:
`graph.neighbors`, `graph.paths`, and `graph.page_context`. These actions read
from an in-memory graph built by `build_research_graph(ws)` and do not write
`graph/research_graph.json`; explicit `graph.export` remains the generated-file
route.
```

- [ ] **Step 2: Update the feature map**

In `docs/FEATURES_AND_COMMANDS.zh-TW.md`, change the graph export capability row from:

```markdown
| Graph export | 輸出 source/evidence/wiki/topic typed links | `graph/research_graph.json` |
```

to:

```markdown
| Graph export / traversal | 輸出 source/evidence/wiki/topic typed links，並用 `graph.neighbors`、`graph.paths`、`graph.page_context` 在 Codex app 內讀取 public-safe graph context | `graph/research_graph.json` / Codex app report |
```

- [ ] **Step 3: Update project memory**

In `docs/PROJECT_MEMORY.md`, extend the `rkf.actions` durable decision bullet with:

```markdown
- Graph traversal is now action-first and read-only: `graph.neighbors`,
  `graph.paths`, and `graph.page_context` use the in-memory
  `build_research_graph(ws)` helper. They do not write
  `graph/research_graph.json`; `graph.export` remains the explicit generated
  graph file route.
```

- [ ] **Step 4: Run documentation scans**

Run:

```bash
rg -n "graph.neighbors|graph.paths|graph.page_context|build_research_graph" docs/ARCHITECTURE.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/PROJECT_MEMORY.md
```

Expected: output includes the new graph traversal action names and `build_research_graph`.

- [ ] **Step 5: Commit docs and project memory**

Run:

```bash
git add docs/ARCHITECTURE.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/PROJECT_MEMORY.md
git commit -m "docs: document RKF graph traversal actions"
```

Expected: commit succeeds with only docs staged.

## Task 6: Final Verification

**Files:**
- Verify: `rkf/core.py`
- Verify: `rkf/actions.py`
- Verify: `tests/test_rkf_actions.py`
- Verify: docs changed in Task 5

- [ ] **Step 1: Run Python compile checks**

Run:

```bash
python3 -m py_compile tools/rk.py tools/rkf_auto_connect.py rkf/*.py tools/public_safety_scan.py
```

Expected: exit code 0 and no output.

- [ ] **Step 2: Run focused action tests**

Run:

```bash
python3 -m unittest tests.test_rkf_actions -v
```

Expected: all tests in `tests.test_rkf_actions` pass.

- [ ] **Step 3: Run the full test suite**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 4: Run RKF maintenance checks**

Run:

```bash
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/rk.py paper queue
python3 tools/public_safety_scan.py
```

Expected:

- `topic lint passed`
- `rkf all passed`
- paper queue prints the current queue without crashing
- `public_safety_scan passed`

- [ ] **Step 5: Run whitespace and keyword checks**

Run:

```bash
git diff --check
rg -n "external-sandbox|external_sandbox|sandbox-grant|sandbox-bootstrap|synthesize auto|python3 tools/rk.py" docs/ARCHITECTURE.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/PROJECT_MEMORY.md rkf/actions.py rkf/core.py tests/test_rkf_actions.py
```

Expected:

- `git diff --check` has no output and exits 0.
- `rg` has no output for the removed legacy surface strings.

- [ ] **Step 6: Inspect staged or uncommitted diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: no uncommitted changes after the task commits, or only the current plan file if execution intentionally leaves planning docs uncommitted.

## Execution Notes

- Do not add new user-facing CLI parser commands for traversal.
- Keep `graph.export` behavior intact because existing reports and tests expect it to write `graph/research_graph.json`.
- Keep traversal actions read-only by calling `build_research_graph(ws)`.
- Treat topic and evidence endpoints that appear only in edges as public-safe implicit nodes with `status="implicit"`.
- Do not read private evidence roots, PDFs, browser captures, or raw article text.
