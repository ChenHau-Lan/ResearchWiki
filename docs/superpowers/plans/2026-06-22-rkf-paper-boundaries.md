# RKF Paper Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make RKF paper intake Markdown-first by generating paper pages that separate source-grounded notes, reader interpretation, AI/agent notes, feedback, and claim-promotion candidates.

**Architecture:** Keep Markdown files as the durable user-facing artifact and keep the CLI as a thin backend for repeatable generation, validation, indexing, graph export, and automation. Implement the boundary as section conventions first, without adding new required schema fields or moving the live configured wiki.

**Tech Stack:** Python 3 standard library, `unittest`, Markdown templates, RKF YAML-like frontmatter helpers, existing `tools/rk.py` CLI.

---

## Project Rule

This repository's project instructions say not to commit unless the user explicitly asks. The execution steps below use diff-review checkpoints instead of commit steps.

## File Structure

- Modify `tests/test_rkf_cli.py`: add assertions that generated paper pages contain the new boundary sections and locator shape.
- Modify `rkf/core.py`: update `create_paper_note()` generated Markdown body while preserving existing frontmatter and maturity behavior.
- Modify `templates/rkf/paper.md`: align the hand-authored template with the generated page shape.
- Create `docs/workflows/paper-intake.zh-TW.md`: explain the Markdown-first, no-manual-CLI paper intake workflow.
- Modify `docs/FEATURES_AND_COMMANDS.zh-TW.md`: clarify CLI as backend and document paper boundary sections.
- Modify `docs/ARCHITECTURE.md`: document the paper section boundary layer and CLI positioning.
- Modify `docs/PROJECT_MEMORY.md`: record the durable Markdown-first / thin-CLI decision.

## Task 1: Add Failing Paper Boundary Tests

**Files:**
- Modify: `tests/test_rkf_cli.py`

- [ ] **Step 1: Add a helper for paper boundary assertions**

Insert this method inside `RKFCliTests`, immediately after `run_rk()`:

```python
    def assert_paper_boundary_sections(self, text: str) -> None:
        expected_sections = [
            "## Source Identity",
            "## Reading Maturity",
            "## Source-Grounded Summary",
            "## Extracted Evidence And Locators",
            "## Reader Notes",
            "## AI/Agent Notes",
            "## Questions And Feedback",
            "## Claims To Promote",
            "## Future Agent Retrieval Brief",
            "## Graph Links",
        ]
        for section in expected_sections:
            self.assertIn(section, text)
        self.assertNotIn("\n## Locators\n", text)
        self.assertNotIn("\n## Reading Notes\n", text)
```

- [ ] **Step 2: Assert boundary sections for metadata-only paper drafts**

In `test_metadata_only_source_can_create_reading_draft`, after the existing `claim_readiness` assertion, add:

```python
        self.assert_paper_boundary_sections(text)
        self.assertIn("- Evidence boundary: review-blocker", text)
        self.assertIn("- Locator: not recorded yet", text)
```

- [ ] **Step 3: Assert boundary sections for un-QCed PDF drafts**

In `test_unqced_pdf_can_be_distilled_as_partial_fulltext_draft`, after the existing `claim_readiness` assertion, add:

```python
        self.assert_paper_boundary_sections(page)
        self.assertIn("- Evidence boundary: review-blocker", page)
        self.assertIn("- Locator: not recorded yet", page)
```

- [ ] **Step 4: Assert boundary sections and locator formatting for QCed PDFs**

In `test_qced_pdf_can_be_distilled_and_graphed`, after the existing locator assertion, add:

```python
        self.assert_paper_boundary_sections(text)
        self.assertIn("## Extracted Evidence And Locators", text)
        self.assertIn("- Locator: pp. 1-4 methods and results", text)
```

- [ ] **Step 5: Run a targeted test and confirm it fails for the intended reason**

Run:

```bash
python3 -m unittest tests.test_rkf_cli.RKFCliTests.test_metadata_only_source_can_create_reading_draft -v
```

Expected: FAIL because the generated page does not yet contain `## Source-Grounded Summary`.

- [ ] **Step 6: Review checkpoint**

Run:

```bash
git diff -- tests/test_rkf_cli.py
```

Expected: diff only adds the helper and boundary-section assertions.

## Task 2: Update Generated Paper Markdown

**Files:**
- Modify: `rkf/core.py`

- [ ] **Step 1: Replace locator formatting and paper body in `create_paper_note()`**

In `rkf/core.py`, replace the block from `locators = ...` through the closing `body = (...)` section with:

```python
    locators = artifact.get("locators", []) if artifact else []
    locator_lines = "\n".join(f"- Locator: {item}" for item in locators) if locators else "- Locator: not recorded yet"
    evidence_line = f"- PDF Evidence: {artifact['evidence_id']}" if artifact else "- PDF Evidence: not provided yet"
    evidence_status = "Checked PDF" if artifact and artifact.get("status") == "pdf_qc_done" else "Reading draft; evidence boundary not promoted"
    body = (
        f"# {title}\n\n"
        "## Source Identity\n\n"
        f"- Source ID: {record['source_id']}\n"
        f"- DOI: {record.get('normalized_doi', '')}\n"
        f"{evidence_line}\n"
        f"- Evidence status: {evidence_status}\n\n"
        "## Reading Maturity\n\n"
        f"- Reading state: {maturity['reading_state']}\n"
        f"- Full text status: {maturity['fulltext_status']}\n"
        f"- Human feedback level: {maturity['human_feedback_level']}\n"
        f"- Understanding confidence: {maturity['understanding_confidence']}\n"
        f"- Claim readiness: {maturity['claim_readiness']}\n"
        f"- Reading ledger: {maturity['reading_ledger']}\n\n"
        "## Source-Grounded Summary\n\n"
        "- Research question:\n"
        "- Method/data:\n"
        "- Key findings:\n"
        "- Limitations:\n"
        f"- Evidence boundary: {boundary}\n\n"
        "## Extracted Evidence And Locators\n\n"
        f"{locator_lines}\n"
        "- What the source explicitly supports:\n"
        "- What it does not support:\n\n"
        "## Reader Notes\n\n"
        "- My interpretation:\n"
        "- Why this matters to my project:\n"
        "- Connections to other RKF pages:\n\n"
        "## AI/Agent Notes\n\n"
        "- Agent-generated summary:\n"
        "- Unverified inference:\n"
        "- Needs human check:\n\n"
        "## Questions And Feedback\n\n"
        "- User questions:\n"
        "- Human feedback:\n"
        "- Open blockers:\n\n"
        "## Claims To Promote\n\n"
        "- Claim:\n"
        "  - Required locator or blocker:\n"
        "  - Caveat:\n\n"
        "## Future Agent Retrieval Brief\n\n"
        "- Read this page when:\n"
        "- Trust level:\n"
        "- Current gaps:\n"
        "- Next best action:\n\n"
        "## Graph Links\n\n"
        "- Topics:\n"
        "- Concepts:\n"
        "- Questions:\n"
    )
```

- [ ] **Step 2: Run the targeted tests from Task 1**

Run:

```bash
python3 -m unittest tests.test_rkf_cli.RKFCliTests.test_metadata_only_source_can_create_reading_draft tests.test_rkf_cli.RKFCliTests.test_unqced_pdf_can_be_distilled_as_partial_fulltext_draft tests.test_rkf_cli.RKFCliTests.test_qced_pdf_can_be_distilled_and_graphed -v
```

Expected: PASS.

- [ ] **Step 3: Review checkpoint**

Run:

```bash
git diff -- rkf/core.py tests/test_rkf_cli.py
```

Expected: diff only changes generated paper Markdown shape and paper tests.

## Task 3: Align the Paper Template

**Files:**
- Modify: `templates/rkf/paper.md`

- [ ] **Step 1: Replace the body sections after `## Reading Maturity`**

Replace everything from the current `## Locators` section through the end of the file with:

```markdown
## Source-Grounded Summary

- Research question:
- Method/data:
- Key findings:
- Limitations:
- Evidence boundary: review-blocker

## Extracted Evidence And Locators

- Locator: not recorded yet
- What the source explicitly supports:
- What it does not support:

## Reader Notes

- My interpretation:
- Why this matters to my project:
- Connections to other RKF pages:

## AI/Agent Notes

- Agent-generated summary:
- Unverified inference:
- Needs human check:

## Questions And Feedback

- User questions:
- Human feedback:
- Open blockers:

## Claims To Promote

- Claim:
  - Required locator or blocker:
  - Caveat:

## Future Agent Retrieval Brief

- Read this page when:
- Trust level:
- Current gaps:
- Next best action:

## Graph Links

- Topics:
- Concepts:
- Questions:
```

- [ ] **Step 2: Inspect the rendered template text**

Run:

```bash
sed -n '1,140p' templates/rkf/paper.md
```

Expected: template contains `Source-Grounded Summary`, `Extracted Evidence And Locators`, `Reader Notes`, and `AI/Agent Notes`; it no longer contains top-level `## Locators` or `## Reading Notes`.

- [ ] **Step 3: Review checkpoint**

Run:

```bash
git diff -- templates/rkf/paper.md
```

Expected: diff only changes the paper template body sections.

## Task 4: Add Markdown-First Paper Intake Workflow Doc

**Files:**
- Create: `docs/workflows/paper-intake.zh-TW.md`

- [ ] **Step 1: Create the workflows directory**

Run:

```bash
mkdir -p docs/workflows
```

- [ ] **Step 2: Add the workflow document**

Create `docs/workflows/paper-intake.zh-TW.md` with:

````markdown
# Paper Intake Workflow

這份流程說明 RKF v0 的日常文獻整理方式：Markdown 是主要工作介面，CLI 是 agent
與 automation 的薄後端。使用者不需要手動執行 CLI 才能整理 paper。

## 使用者入口

日常可以直接用自然語言交給 agent：

```text
幫我把這篇 DOI 建成 RKF paper note，客觀文獻整理、我的想法、AI 推論要分開。
```

也可以在 Obsidian、VS Code 或任何 Markdown editor 裡直接編輯
`knowledge/papers/*.md`。真正的 operational wiki 由 `rkf.workspace.toml` 的
`wiki_root` 指定；repo 本身保留 framework、docs、templates、tests、examples，
不要把個人 live wiki 搬回 repo。

## Paper Page 分層

每篇 paper note 應維持下列邊界：

| Section | 放什麼 | 不放什麼 |
|---|---|---|
| `Source-Grounded Summary` | 文獻本身支持的研究問題、方法、結果、限制 | 個人建議、跨文獻推論 |
| `Extracted Evidence And Locators` | page/section/figure/table locator，以及來源明確支持或不支持的範圍 | 未定位的 stable claim |
| `Reader Notes` | 使用者自己的理解、研究關聯、主觀判斷 | 偽裝成文獻結論的個人看法 |
| `AI/Agent Notes` | AI 摘要、未驗證推論、需要人工查核的點 | claim evidence |
| `Questions And Feedback` | public-safe 問題、人為回饋、open blocker | 私人全文、private path |
| `Claims To Promote` | 候選 claim、必要 locator/blocker、caveat | 沒有邊界的 stable claim |

## Claim Promotion Rule

`Claims To Promote` 裡的內容只是候選。要升級成 claim page 或 synthesis support，
至少需要下列其中一種邊界：

- locator-backed evidence；
- 既有 supported RKF wiki page；
- annotated 或 trusted human feedback。

如果目前只有 explicit review blocker，保留為候選或 blocked claim draft，清楚標示不能
升級的原因；不得作為 synthesis support。

Candidate、ARS output、hot query、route note、AI/Agent Notes 都不能單獨作為
stable claim evidence。

## CLI 的角色

CLI 是 agent-safe backend，不是使用者一定要手動操作的入口。Agent 或 automation
可以在背後使用：

```bash
python3 tools/rk.py distill paper <source_id>
python3 tools/rk.py paper queue
python3 tools/rk.py lint
python3 tools/rk.py index
python3 tools/rk.py graph
```

手動使用 CLI 適合可重現檢查、批次整理、debug、或 automation 設定。日常閱讀與整理
優先保持 Markdown-first。

## 安全邊界

- 不把 PDF、article full text、browser capture、private evidence path 寫進 public wiki。
- 不把 live 個人 wiki 當成測試 fixture 搬進 repo。
- 不把 AI 推論寫成來源已支持的結論。
- 不把 `hot.md`、candidate、ARS report、`fulltext_routes/*.md` 當成 evidence。
````

- [ ] **Step 3: Inspect the workflow doc**

Run:

```bash
sed -n '1,220p' docs/workflows/paper-intake.zh-TW.md
```

Expected: document explains natural-language and Markdown-first paper intake before mentioning CLI commands.

- [ ] **Step 4: Review checkpoint**

Run:

```bash
git diff -- docs/workflows/paper-intake.zh-TW.md
```

Expected: one new public-safe workflow doc, with no private absolute paths.

## Task 5: Update Feature Documentation

**Files:**
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`

- [ ] **Step 1: Add a Markdown-first usage section after the introduction**

After the opening paragraph ending with `清理候選。`, insert:

```markdown
## 使用入口原則

RKF v0 採用 Markdown-first workflow：`knowledge/*.md` 是主要使用者介面，
agent 可以用自然語言協助建立、整理與更新頁面。CLI 保留為薄後端，用於可重現的
source capture、paper draft 產生、queue、lint、index、graph 與 automation；使用者
不需要手動執行 CLI 才能完成日常文獻整理。
```

- [ ] **Step 2: Update the Paper reading draft feature row**

Replace the `Paper reading draft` row with:

```markdown
| Paper reading draft | 從 metadata、abstract、partial full text 或 PDF 先建立 paper draft；頁面分開 source-grounded summary、locator/evidence、reader notes、AI/Agent notes 與 claim candidates | `knowledge/papers/*.md` |
```

- [ ] **Step 3: Add paper section boundary bullets to Reading And Evidence Rules**

After the bullet that starts `Paper draft 要明確記錄`, add:

```markdown
- Paper draft body 要分開 `Source-Grounded Summary`、`Extracted Evidence And Locators`、
  `Reader Notes`、`AI/Agent Notes`、`Questions And Feedback` 與
  `Claims To Promote`。
- `Reader Notes` 可以保存使用者主觀判斷；`AI/Agent Notes` 可以保存 AI 推論；
  兩者都不能單獨作為 stable claim evidence。
```

- [ ] **Step 4: Clarify the `distill paper` command purpose**

Replace the `distill paper <source_id>` row with:

```markdown
| `distill paper <source_id>` | `--slug` | 建立或更新分層 paper reading draft；通常由 agent/automation 在背後呼叫 |
```

- [ ] **Step 5: Run a focused inspection**

Run:

```bash
sed -n '1,130p' docs/FEATURES_AND_COMMANDS.zh-TW.md
```

Expected: file now states Markdown-first before command inventory and documents the paper body boundary.

## Task 6: Update Architecture And Project Memory

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/PROJECT_MEMORY.md`

- [ ] **Step 1: Add paper boundary layer to architecture**

In `docs/ARCHITECTURE.md`, add this row immediately after `Paper Drafts` in the Layer Model table:

```markdown
| Paper Section Boundaries | Separate source-grounded summary, extracted locators, reader notes, AI/agent notes, feedback, and claim-promotion candidates | concise Markdown sections only |
```

- [ ] **Step 2: Add boundary rules to architecture**

In `docs/ARCHITECTURE.md`, after `Paper drafts are active reading objects and may be created early.`, add:

```markdown
- Paper pages separate source-grounded summaries from reader interpretation and
  AI/agent notes. Only locator-backed or otherwise supported source-grounded
  material can support claim promotion.
- The CLI is a thin backend for repeatable agent and automation operations; the
  user-facing paper intake workflow remains Markdown-first.
```

- [ ] **Step 3: Add durable decision to project memory**

In `docs/PROJECT_MEMORY.md`, under `## Durable Decisions`, add:

```markdown
- RKF v0 paper intake is Markdown-first. Users can work through natural
  language and Markdown pages; the CLI remains a thin backend for repeatable
  agent operations, validation, indexing, graph export, and automation.
- Paper pages must keep source-grounded literature notes, reader interpretation,
  AI/agent notes, questions/feedback, and claim-promotion candidates visibly
  separate.
```

- [ ] **Step 4: Inspect docs**

Run:

```bash
sed -n '1,120p' docs/ARCHITECTURE.md
sed -n '1,90p' docs/PROJECT_MEMORY.md
```

Expected: architecture and memory both describe Markdown-first paper intake and separated paper sections.

## Task 7: Final Verification And Diff Review

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run Python syntax checks**

Run:

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
```

Expected: exits with code 0 and prints no errors.

- [ ] **Step 2: Run the full unit test suite**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: exits with code 0.

- [ ] **Step 3: Run the public safety scan**

Run:

```bash
python3 tools/public_safety_scan.py
```

Expected: exits with code 0 or reports only pre-existing findings unrelated to this change. If it reports new findings in files touched by this plan, fix them before continuing.

- [ ] **Step 4: Check for private absolute paths in new docs**

Run:

```bash
rg -n "/U[s]ers/|G[o]ogleDrive-|我的雲端硬[碟]" docs/workflows docs/superpowers
```

Expected: no output.

- [ ] **Step 5: Review the complete diff**

Run:

```bash
git diff -- tests/test_rkf_cli.py rkf/core.py templates/rkf/paper.md docs/workflows/paper-intake.zh-TW.md docs/FEATURES_AND_COMMANDS.zh-TW.md docs/ARCHITECTURE.md docs/PROJECT_MEMORY.md
```

Expected: diff is limited to paper boundary sections, Markdown-first workflow docs, and tests.

- [ ] **Step 6: Capture final status**

Run:

```bash
git status --short
```

Expected: modified and new files are visible. Do not stage or commit unless the user explicitly asks.

## Self-Review

Spec coverage:

- Paper template update: Task 3.
- Generated paper body update: Task 2.
- Tests for generated page shape: Task 1 and Task 7.
- Markdown-first workflow doc: Task 4.
- Feature and architecture docs: Task 5 and Task 6.
- Project memory update: Task 6.
- No live wiki migration or schema migration: explicitly omitted from all tasks.

Type and naming consistency:

- Section names match the approved spec: `Source-Grounded Summary`, `Extracted Evidence And Locators`, `Reader Notes`, `AI/Agent Notes`, `Questions And Feedback`, `Claims To Promote`, `Future Agent Retrieval Brief`, and `Graph Links`.
- Existing frontmatter fields are preserved.
- Existing CLI names remain unchanged.

Execution safety:

- No commit, push, destructive command, live wiki migration, or private evidence move is included.
- The only directory creation is `docs/workflows`, which is inside the writable repo.
