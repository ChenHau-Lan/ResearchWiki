---
name: rkf-auto-connect
description: Connect a Codex task or local research project to a governed RKF workspace. Use when the user asks to connect, activate, query, capture, discover papers, or preview the RKF dashboard from ResearchWiki or a connected project, including 啟動 RKF, 連結 RKF, 問 RKF, 收進 RKF, 自動找 paper, or 研究熱點.
---

# RKF Auto-Connect

Treat a project marker as capability discovery only. Require manual RKF
activation in every new Codex task, and keep stable-knowledge promotion behind
its own evidence and review gates.

## Resolve The Workspace

Read `$HOME/.codex/rkf_connector.toml`, then let the referenced ResearchWiki
checkout resolve storage through its ignored `rkf.workspace.toml`. Never copy
private storage paths into project files or receipts.

If the connector or workspace config is absent, stop and direct the user to
the repository bootstrap and diagnostic. Do not guess another checkout.

## Enforce The Session Boundary

1. Start every task with RKF OFF.
2. Before the user says `啟動 RKF`, do not query, classify for automatic
   capture, or write RKF.
3. Open one task-owned backend runtime using the connector checkout and the
   current project root, then use `rkf.activate` and report its path-redacted
   receipt. The repo helper names this adapter `open_action_runtime`.
4. Reuse that same runtime for all later actions in the current task. Do not
   execute activation and later request-builder commands as unrelated helper
   processes, because ACTIVE state is deliberately in-memory and task-scoped.
5. Use `rkf.deactivate` when the user says `停用 RKF`.

## Route Activated Requests

| User intent | Structured action | Boundary |
|---|---|---|
| 啟動 RKF | `rkf.activate` | read-only preflight |
| 問 RKF | `query.search` | central RKF before project-local |
| 收進 RKF | `capture.route` | immutable event; `Promotion: none` |
| 自動找 paper | `discover.preview` | network read; candidate-only; no persistence |
| 研究熱點 dashboard | `dashboard.preview` | aggregate-only private preview |
| 審查 dashboard preview | `dashboard.review` | self-contained private page; does not update `site/` |
| 停用 RKF | `rkf.deactivate` | return to OFF |

Require the designated writer and exact preview hash for `discover.record`.
Accept only selected candidate IDs through `discover.accept`; default to no
paper draft and no claim promotion. Require the exact reviewed snapshot hash
for `dashboard.publish`; local publication does not authorize commit, push, or
GitHub Pages deployment.

## Read Project Markers

Use the v2 marker contract:

```toml
version = 2

[rkf]
available = true
activation = "manual"
query_first = true
capture_mode = "active-aggressive"
```

Never treat `available = true` as ACTIVE. Preview a v1 upgrade, preserve
semantically matching v2 files, and refuse unknown future versions or policy
differences that require a user-owned edit.

## Capture Safely

After activation, capture reusable public-safe identifiers, paper leads,
source-backed web excerpts, research synthesis, methods, experiment designs,
manuscript evidence reasoning, hypotheses, caveats, and open questions.

Do not capture secrets, credentials, private paths, personal data, PDFs, full
articles, whole transcripts, browser captures, or low-value transient talk.
Candidates remain proposals; ARS output remains a proposal or reading feedback
until RKF review.

## Report

Report the action, dedupe/materialization state when relevant, `Promotion:
none`, and any blocker. Do not echo private paths, machine IDs, keys, raw
queries from dashboard state, or unpublished content.
