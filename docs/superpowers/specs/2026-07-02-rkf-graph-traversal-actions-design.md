# RKF Graph Traversal Actions Design

Date: 2026-07-02

## Goal

Add read-only graph traversal actions to RKF so Codex can follow public-safe
relationships between sources, evidence, topics, and knowledge pages without
reintroducing a user-facing CLI control plane.

This is the next focused optimization after the Codex app action runtime and
stats snapshot work. It gives Codex a structured way to answer questions like:

- What is connected to this paper or synthesis?
- Which pages support or derive from this source?
- Is there a short path between two RKF objects?
- What graph context should a future agent read before editing this page?

## User-Approved Direction

The implementation slice is intentionally narrow:

- Build graph traversal on top of the current `rkf.actions` runtime.
- Keep all user interaction inside Codex app natural-language workflows.
- Do not add new user-facing CLI commands.
- Keep the action results public-safe and read-only.
- Defer paper review cards, read-only MCP, private multi-format ingest, and UI
  dashboard work until traversal actions are stable.

## Scope

In scope:

- Extract a pure graph builder from the current graph export path.
- Add core read-only traversal helpers for neighbors, paths, and page context.
- Add `rkf.actions` dispatch for:
  - `graph.neighbors`
  - `graph.paths`
  - `graph.page_context`
- Add direct action-layer tests with temporary workspaces.
- Update architecture/docs/project memory after implementation.

Out of scope:

- MCP server or connector work.
- Browser dashboard or static HTML graph viewer.
- Paper review cards.
- Private PDF/DOCX/HTML/CSV ingest.
- Semantic, embedding, or vector retrieval.
- Write actions, stable-claim promotion, or maturity upgrades.
- New user-facing CLI commands.

## Current Context

`export_graph(ws)` currently builds the RKF graph in `rkf/core.py` and writes it
to `graph/research_graph.json`. The graph includes public-safe nodes for source
records and knowledge pages, plus typed edges such as:

- `has-evidence`
- `tagged-with`
- `supported-by`
- `derived-from`

The current action runtime already supports `graph.export`, which calls
`export_graph(ws)`, writes the generated JSON file, and returns the graph in the
action payload. That is valid for an explicit export action, but traversal
queries should not modify the workspace just because Codex is inspecting graph
context.

## Recommended Architecture

### Pure Graph Builder

Add a pure helper in `rkf/core.py`, tentatively `build_research_graph(ws)`, that
returns the same graph dictionary currently produced by `export_graph(ws)` but
does not write any files.

Then keep `export_graph(ws)` as a small wrapper:

1. call `build_research_graph(ws)`;
2. write `graph/research_graph.json`;
3. return the graph.

Traversal helpers should use `build_research_graph(ws)` so they are read-only by
construction.

### Core Traversal Helpers

Keep traversal logic in core helpers rather than duplicating graph handling in
the action dispatcher. The helpers should operate on the public-safe graph
dictionary and return compact structured payloads.

Recommended helpers:

- `graph_neighbors(ws, node_id, direction="both", limit=20)`
- `graph_paths(ws, source_id, target_id, max_depth=4, direction="both", limit=5)`
- `graph_page_context(ws, page_id, limit=20)`

The names may be adjusted to match existing local style, but their boundaries
should stay clear: core builds and traverses; actions validate inputs and return
`ActionResult`.

### Action Layer

Add action wrappers in `rkf/actions.py`:

- `graph_neighbors_action(...)`
- `graph_paths_action(...)`
- `graph_page_context_action(...)`

`execute_action_request()` should dispatch the three canonical action names:

- `graph.neighbors`
- `graph.paths`
- `graph.page_context`

Each action returns `ActionResult` with:

- `action`: canonical action name;
- `status`: `ok`, `not-found`, `ambiguous`, or `error`;
- `message`: concise human-readable summary;
- `payload`: structured graph context for Codex rendering and tests.

## Data Model

Graph traversal should reuse the existing exported graph shape:

```json
{
  "schema": "rkf-graph-v1",
  "generated": "YYYY-MM-DD",
  "nodes": [],
  "edges": []
}
```

Node ids should remain the existing graph node ids:

- source records use their existing `source_id`;
- knowledge pages use the relative knowledge id already present in graph export,
  such as `papers/example-paper` or `synthesis/example-synthesis`.

Edges should keep the existing shape:

```json
{ "from": "node-a", "to": "node-b", "type": "supported-by" }
```

Traversal parameters:

- `direction`: `outgoing`, `incoming`, or `both`; default `both`;
- `limit`: maximum returned neighbors or paths;
- `max_depth`: maximum number of edges in a path; default `4`.

## Action Payloads

### `graph.neighbors`

Input:

```json
{
  "node_id": "papers/example-paper",
  "direction": "both",
  "limit": 20
}
```

Payload:

```json
{
  "node": {},
  "neighbors": [],
  "edges": [],
  "direction": "both",
  "limit": 20
}
```

The action should return `not-found` if the node id does not exist.

### `graph.paths`

Input:

```json
{
  "source_id": "papers/example-paper",
  "target_id": "topics/example-topic",
  "direction": "both",
  "max_depth": 4,
  "limit": 5
}
```

Payload:

```json
{
  "source": {},
  "target": {},
  "paths": [],
  "direction": "both",
  "max_depth": 4,
  "limit": 5
}
```

Use breadth-first traversal so short paths appear first. For `direction="both"`,
treat edges as traversable in either direction but preserve original edge
objects in returned paths.

### `graph.page_context`

Input:

```json
{
  "page_id": "synthesis/example-synthesis",
  "limit": 20
}
```

Payload:

```json
{
  "page_id": "synthesis/example-synthesis",
  "node": {},
  "incoming": [],
  "outgoing": [],
  "related_sources": [],
  "related_evidence": [],
  "related_topics": [],
  "related_pages": [],
  "summary": []
}
```

`page_id` should accept the exact graph id first. If a user-facing page path is
accepted later, ambiguity must be reported instead of guessed.

## Safety And Error Handling

- Traversal actions must not read PDFs, raw full text, private evidence roots,
  browser captures, or local Drive paths.
- Traversal actions must not write `graph/research_graph.json`; only
  `graph.export` writes that file.
- Missing nodes return `status="not-found"` with the requested id in the
  payload.
- Ambiguous page identifiers return `status="ambiguous"` with exact candidates.
- Invalid `direction`, negative limits, or non-positive `max_depth` return a
  clear error result or validation failure.
- Candidates, ARS reports, hot queries, and route notes remain below the
  evidence boundary. Traversal context is retrieval context, not claim support.

## Testing Strategy

Add direct action tests in `tests/test_rkf_actions.py`:

- `graph.neighbors` returns expected neighbor nodes and typed edges.
- `graph.paths` returns a shortest path between seeded graph nodes.
- `graph.page_context` groups incoming, outgoing, source, topic, evidence, and
  page relationships.
- Missing nodes return `not-found`.
- Invalid traversal parameters fail clearly.
- Traversal actions do not create or modify `graph/research_graph.json`.

Use temporary workspaces seeded with minimal source records, paper or synthesis
pages, evidence artifacts, and topic metadata. Tests should call
`execute_action_request()` directly. Existing CLI tests should only change if
the implementation needs to preserve current `graph.export` behavior.

## Implementation Slice

1. Add failing tests for the three new action names and read-only guarantees.
2. Extract `build_research_graph(ws)` from `export_graph(ws)`.
3. Add adjacency and traversal helpers in `rkf/core.py`.
4. Add `rkf.actions` wrappers and dispatch entries.
5. Update architecture, feature map, and project memory to describe traversal
   actions as Codex app context tools.
6. Run focused action tests, full unittest, py_compile, public safety scan, and
   diff check.

## Deferred Work

- Paper review cards for daily reading triage.
- Read-only MCP tools built on top of the now-stable action payloads.
- Semantic ranking or embedding search.
- Browser or static HTML dashboard.
- Private multi-format ingest.

## Success Criteria

- Codex can ask for neighbors, paths, and page context through structured
  `ActionRequest` objects.
- Traversal actions return compact public-safe payloads suitable for Codex app
  rendering.
- Traversal does not write generated graph files or private runtime state.
- `graph.export` continues to produce `graph/research_graph.json`.
- Tests cover happy paths, missing nodes, invalid parameters, and read-only
  behavior.
- Documentation makes clear that graph traversal is an app-facing action layer,
  not a new user-facing CLI surface.
