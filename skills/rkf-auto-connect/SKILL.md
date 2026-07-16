---
name: rkf-auto-connect
description: Connect a Codex task or local research project to RKF, require task-scoped activation, and route requests only through Connect & Activate, Add, Ask, Read, Compare & Synthesize, or Review. Use for 啟動 RKF, 連結 RKF, 問 RKF, 收進 RKF, 記錄 Evidence, 比較 claims, 查看下一步, or 停用 RKF.
---

# RKF Auto-Connect

Use this skill as the installable front door to RKF v1. A project marker means
RKF is available; it never means the current task is active. Stable-knowledge
promotion remains behind Evidence and human-review gates.

## Resolve The Workspace

Read `$HOME/.codex/rkf_connector.toml`, then let the referenced ResearchWiki
checkout resolve storage through its ignored `rkf.workspace.toml`. Never copy
private storage paths into project files or receipts.

If the connector or workspace config is absent, stop and direct the user to the
repository bootstrap and strict diagnostic. Do not guess another checkout.

## Enforce The Session Boundary

1. Start every task with RKF OFF.
2. Before explicit activation, do not query or write RKF.
3. Open one task-owned backend runtime from the validated connector checkout and
   current project root.
4. Execute `rkf.activate`, validate the connection, and report the path-redacted
   receipt.
5. Reuse that runtime for every later action in the task.
6. Execute `rkf.deactivate` when the user says `停用 RKF`.

## Workflow Routing

| User intent | Structured action | Boundary |
|---|---|---|
| 啟動 RKF | `rkf.activate` then `connect.validate` | read-only validation before research work |
| 查看狀態 | `rkf.status` | task receipt plus path-redacted open-project summary |
| 收進 RKF | `workflow.add` | candidate capture; `Promotion: none` |
| 問 RKF | `workflow.ask` | exact-first; claim-supporting answers need locators |
| 記錄閱讀 | `workflow.read` | exact-locator Evidence and explicit verification |
| 比較與整合 | `workflow.compare-synthesize` | Evidence-linked Claim or Synthesis |
| 查看下一步 | `workflow.review` | gaps, pending checks, disputed Claims, and lineage |
| 停用 RKF | `rkf.deactivate` | return the task to OFF |

## Trigger Phrases

- "Activate RKF and validate this project."
- "Add this DOI, but keep Promotion: none."
- "Ask RKF; if there is no locator, say the evidence is insufficient."
- "Record p. 8, Fig. 3 as unreviewed Evidence."
- "Compare these Evidence cards and preserve contradictions and gaps."
- "Review this project and tell me the next reading action."
- "啟動 RKF 並確認 connection。"
- "根據目前對話整理搜尋詞，先 Ask RKF；列出候選論文，等我確認後再 Add DOI／URL 與短 note，不保存完整對話。"
- "顯示 RKF 狀態，列出仍有 open activation record 的 project name 與 project_id，並標示這個 task。"
- "把這個 DOI 收進 RKF，但不要升級成 Evidence。"
- "停用 RKF。"

## Read Project Markers

Use the v2 marker contract. Never treat `available = true` as ACTIVE. Preserve a
semantically matching v2 file, preview a legacy upgrade, and refuse unknown
versions or policy differences that require a user-owned edit.

## Safety Rules

- Do not capture secrets, credentials, private paths, personal data, PDFs, full
  articles, whole transcripts, or browser captures.
- Candidate metadata and model output are not Evidence.
- Every connected action keeps project/activation lineage without raw prompts or
  private paths.
- Internal helpers and compatibility code never authorize a new user workflow,
  commit, push, deployment, or trust promotion.

## Report

Report the workflow, activation or dedupe state when relevant, `Promotion:
none`, and any blocker. For status requests, separate the current task from
projects with open activation records, and note that interrupted tasks can
remain open until a later closure or expiry event is recorded. Do not echo
private paths, machine IDs, keys, raw prompts, or unpublished content.
