# RKF Phase 2 Golden Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a deterministic, paper-centered, zero-live-write migration preview for the configured 57-paper corpus, with per-page diffs, a reviewable routing manifest, and an exact manifest hash for a later live-migration decision.

**Architecture:** Keep paper transformation pure in `rkf/paper_migration.py`; it receives Markdown bytes and produces transformed Markdown plus content-preserving routing proposals. A small preview runner reads the live paper tree, works only in a private ignored report directory, rechecks input checksums, and exposes the result through a session-guarded `paper.migration.preview` action. It deliberately does not implement a live apply path in this phase.

**Tech Stack:** Python 3 standard library (`dataclasses`, `hashlib`, `difflib`, `json`, `pathlib`, `tempfile`), existing RKF `Workspace`, `unittest`, Markdown, JSON Schema.

**Approved Design:** `docs/superpowers/specs/2026-07-10-rkf-1-1-closed-loop-design.md` sections 8–9, 16–19.

## Global Constraints

- A preview must not write inside configured `wiki_root` or `raw_root`; all copies, diffs, manifests, and reports live in an ignored local report root.
- `paper.migration.preview` is unavailable while RKF is OFF and may run in `ACTIVE_READ_ONLY` because it never mutates the canonical knowledge database.
- Every input file is byte-checksummed before and after the preview; drift invalidates the report instead of creating a misleading approval candidate.
- The transform preserves source identity, locators, source-grounded methods/findings/limitations, and all non-empty removed content through manifest entries with content hashes.
- Ambiguous, project/manuscript, cross-paper, or broad-question content is recorded as `needs-human-routing`; any such item makes the preview not ready for live application.
- Migration never infers a higher trust, claim readiness, human feedback level, or stable claim from legacy prose alone.
- Tests use sanitized fixtures; the real 57-paper run is a local acceptance action only and its private report is never committed.
- No live migration, backup creation, rollback, cleanup, dependency installation, commit, or push is authorized by this plan.

---

## File And Interface Map

- Create `rkf/paper_migration.py`: pure parsing, legacy maturity mapping, canonical section transform, routing proposals, SHA-256 manifests, preview runner.
- Modify `rkf/actions.py`: dispatch `paper.migration.preview` after activation without adding it to writer-only canonical writes.
- Modify `rkf/core.py`: limited frontmatter support for lists of mappings so `paper_relations` can round-trip in later phases.
- Modify `templates/rkf/paper.md`: use the RKF v1.1 paper-centered contract.
- Modify `schemas/knowledge_object.schema.json`: document `rkf-paper-v1.1`, `evidence_tier`, and portable `paper_relations` properties.
- Modify `schemas/reading_ledger.schema.json`: accept `rkf-reading-ledger-v1.1`, `inbox-injection`, and `migration` event types.
- Create `tests/test_rkf_paper_migration.py`: pure-transform, routing, manifest, zero-live-write, and controlled 57-fixture assertions.
- Modify `tests/test_rkf_actions.py`: OFF guard and active preview action coverage.
- Modify `docs/PROJECT_MEMORY.md`, `docs/FEATURES_AND_COMMANDS.zh-TW.md`, `CHANGELOG.md`: describe the preview-only boundary and exact approval gate.

---

### Task 1: Establish Lossless Paper Transform Contracts

**Files:**
- Create: `tests/test_rkf_paper_migration.py`
- Create: `rkf/paper_migration.py`

**Interfaces:**
- Produces `sha256_bytes(data: bytes) -> str`, `parse_sections(body: str) -> list[Section]`, `transform_paper_markdown(text: str, *, page_id: str) -> TransformResult`.
- `TransformResult` contains `text`, `input_checksum`, `output_checksum`, `routed_blocks`, and `issues`.

- [ ] **Step 1: Write the failing canonical-heading and preservation tests**

```python
result = transform_paper_markdown(LEGACY_PAPER, page_id="papers/example")
self.assertIn("## Research Question", result.text)
self.assertIn("## Methods And Data", result.text)
self.assertIn("## Main Findings", result.text)
self.assertIn("page 4, Fig. 2", result.text)
self.assertEqual(result.input_checksum, sha256_bytes(LEGACY_PAPER.encode("utf-8")))
```

- [ ] **Step 2: Run the focused test and verify it fails because the module is absent**

Run: `python3 -m unittest tests.test_rkf_paper_migration.RKFPaperMigrationTests.test_legacy_summary_becomes_paper_centered_sections`

Expected: `ModuleNotFoundError: No module named 'rkf.paper_migration'`.

- [ ] **Step 3: Implement the pure data types and heading transform**

```python
@dataclass(frozen=True)
class RoutedBlock:
    source_heading: str
    content_hash: str
    classification: str
    proposed_target: str
    review_status: str

def transform_paper_markdown(text: str, *, page_id: str) -> TransformResult:
    meta, body = parse_frontmatter(text)
    sections = parse_sections(body)
    canonical, routed, issues = canonicalize_sections(sections, page_id=page_id)
    return TransformResult(render_paper(meta, canonical), sha256_bytes(text.encode("utf-8")), routed, issues)
```

- [ ] **Step 4: Re-run the focused test and add source/locator no-loss assertions**

Run: `python3 -m unittest tests.test_rkf_paper_migration.RKFPaperMigrationTests.test_legacy_summary_becomes_paper_centered_sections`

Expected: PASS.

### Task 2: Make Routing Conservative And Maturity Mapping Explicit

**Files:**
- Modify: `tests/test_rkf_paper_migration.py`
- Modify: `rkf/paper_migration.py`
- Modify: `schemas/reading_ledger.schema.json`

**Interfaces:**
- Produces `map_legacy_maturity(meta: dict[str, Any]) -> dict[str, Any]` and `route_nonpaper_block(section: Section, *, page_id: str) -> RoutedBlock | None`.

- [ ] **Step 1: Write failing tests for broad questions and reading-state compatibility**

```python
result = transform_paper_markdown(BROAD_QUESTION_PAPER, page_id="papers/example")
self.assertEqual(result.routed_blocks[0].review_status, "needs-human-routing")
self.assertEqual(result.meta["reading_state"], "abstract-read")
self.assertEqual(result.meta["reading_status"], "abstract-read")
self.assertEqual(result.meta["human_feedback_level"], "none")
```

- [ ] **Step 2: Run the focused test and verify the required routing state is missing**

Run: `python3 -m unittest tests.test_rkf_paper_migration.RKFPaperMigrationTests.test_broad_question_blocks_live_readiness`

Expected: FAIL because broad questions are not yet marked `needs-human-routing`.

- [ ] **Step 3: Implement deterministic mapping and proposal-only routing**

```python
LEGACY_READING_MAP = {
    "abstract-only": "abstract-read",
    "fulltext-available": "partial-fulltext",
    "full-read": "fulltext-read",
    "synthesis-ready": "fulltext-read",
}

def map_legacy_maturity(meta: dict[str, Any]) -> dict[str, Any]:
    state = LEGACY_READING_MAP.get(str(meta.get("reading_state") or meta.get("reading_status") or "metadata-only"), "metadata-only")
    return {"schema": "rkf-paper-v1.1", "reading_state": state, "reading_status": state, "human_feedback_level": "none"}
```

- [ ] **Step 4: Upgrade the ledger vocabulary without accepting arbitrary event names**

Set the schema const to accept v1 and v1.1 during transition, and add only `inbox-injection` and `migration` to the event enum.

- [ ] **Step 5: Run all paper-migration tests**

Run: `python3 -m unittest tests.test_rkf_paper_migration`

Expected: PASS with all ambiguous material represented in the result rather than discarded.

### Task 3: Add Preview-Only Corpus Runner And Action Guard

**Files:**
- Modify: `tests/test_rkf_paper_migration.py`
- Modify: `tests/test_rkf_actions.py`
- Modify: `rkf/paper_migration.py`
- Modify: `rkf/actions.py`

**Interfaces:**
- Produces `run_preview(ws: Workspace, *, report_root: Path, expected_count: int | None = 57) -> PreviewReport`.
- The action is `ActionRequest("paper.migration.preview", {"report_root": "...", "expected_count": 57})`.

- [ ] **Step 1: Write failing zero-live-write and controlled-corpus tests**

```python
before = checksums(live_paper_paths)
report = run_preview(workspace, report_root=private_reports, expected_count=57)
self.assertEqual(report.input_count, 57)
self.assertEqual(report.output_count, 57)
self.assertEqual(checksums(live_paper_paths), before)
self.assertTrue((private_reports / report.run_id / "manifest.json").exists())
```

- [ ] **Step 2: Run the focused test and verify no runner exists**

Run: `python3 -m unittest tests.test_rkf_paper_migration.RKFPreviewTests.test_preview_uses_private_report_root_and_keeps_live_corpus_unchanged`

Expected: FAIL because `run_preview` is unavailable.

- [ ] **Step 3: Implement the report writer with input drift protection**

```python
def run_preview(ws: Workspace, *, report_root: Path, expected_count: int | None = 57) -> PreviewReport:
    reject_canonical_root(report_root, ws.paths.wiki_root, ws.paths.raw_root)
    inputs = inventory_papers(ws.paths.knowledge / "papers")
    before = {item.relative_path: item.checksum for item in inputs}
    transformed = [transform_file(item) for item in inputs]
    assert_current_checksums(inputs, before)
    return write_private_report(report_root, inputs, transformed, expected_count=expected_count)
```

- [ ] **Step 4: Add action dispatch and OFF guard coverage**

The action calls `run_preview` only after `RKFActionRuntime` is active. `ACTIVE_READ_ONLY` is permitted because the output is local and canonical files are untouched.

- [ ] **Step 5: Run focused action and preview tests**

Run: `python3 -m unittest tests.test_rkf_actions tests.test_rkf_paper_migration`

Expected: PASS; an OFF action returns `RKF_NOT_ACTIVE` before any report directory is created.

### Task 4: Align Templates, Schemas, And Portable Relations

**Files:**
- Modify: `rkf/core.py`
- Modify: `templates/rkf/paper.md`
- Modify: `schemas/knowledge_object.schema.json`
- Modify: `tests/test_rkf_paper_migration.py`

**Interfaces:**
- `frontmatter()` supports lists of scalars and lists of `{paper_id, relation}` mappings.
- Paper v1.1 declares `schema`, `evidence_tier`, and canonical paper headings.

- [ ] **Step 1: Write failing relation round-trip and template contract tests**

```python
meta, _ = parse_frontmatter("---\npaper_relations:\n  - paper_id: papers/example\n    relation: uses-paper\n---\n")
self.assertEqual(meta["paper_relations"][0]["relation"], "uses-paper")
self.assertIn("## Questions About This Paper", PAPER_TEMPLATE)
```

- [ ] **Step 2: Run the focused test and verify list-of-mapping parsing is absent**

Run: `python3 -m unittest tests.test_rkf_paper_migration.RKFSchemaAndTemplateTests.test_paper_relations_round_trip`

Expected: FAIL because nested relation data is not preserved.

- [ ] **Step 3: Implement limited mapping-list parsing and rendering**

Only accept mapping-list structures used by `paper_relations`; preserve existing scalar/list behavior and avoid adding a YAML dependency.

- [ ] **Step 4: Update the paper template and JSON Schema**

The template has the eleven canonical paper sections from the approved design. The schema accepts the transition fields and restricts relation values to `uses-paper`, `compares-paper`, `extends-from-paper`, and `discusses-paper`.

- [ ] **Step 5: Run all focused tests**

Run: `python3 -m unittest tests.test_rkf_paper_migration tests.test_rkf_actions`

Expected: PASS.

### Task 5: Document, Validate, And Produce the Review Gate

**Files:**
- Modify: `docs/PROJECT_MEMORY.md`
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Document the private-preview and manifest-hash boundary**

State that preview reports are local/private, page copies are not live writes, and `paper.migration.apply` still needs a later user message that names the produced manifest hash.

- [ ] **Step 2: Run the controlled 57-fixture acceptance test**

Run: `python3 -m unittest tests.test_rkf_paper_migration.RKFPreviewTests.test_controlled_fifty_seven_page_corpus`

Expected: PASS with exactly 57 inputs, 57 outputs, 57 diff records, and no hidden deletion.

- [ ] **Step 3: Run repository validation**

Run:

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/rk.py lint --mode all
python3 tools/rk.py topic lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/public_safety_scan.py
git diff --check
```

Expected: all commands pass on sanitized repo fixtures; the private live-corpus preview is reported separately and remains a review gate.

## Gate After This Plan

Do not invoke `paper.migration.apply` against the live wiki. Present the final `manifest_hash`, count, unresolved-routing count, and report location, then wait for a separate user message approving that exact hash.
