---
name: rkf-connect
description: Route cross-project setup and task access through RKF v1 Connect & Activate. Use for connect-project preview/apply, marker validation, 啟動 RKF, connection status, or 停用 RKF. This skill does not create a second data store or persist ACTIVE state.
---

# RKF Connect

Use this skill only for the Connect & Activate access layer. It prepares a
project to use the central RKF checkout and controls access for one Codex task;
it does not acquire Evidence or write research conclusions.

## Workflow Routing

| User intent | Structured route | Result |
|---|---|---|
| Preview a project connection | `connect-project` preview | proposed v2 marker and lightweight bridge |
| Apply an approved connection | `connect-project --apply` | non-overwriting marker and bridge |
| Activate this task | `rkf.activate` | unique, path-redacted `activation_id` receipt |
| Validate the connection | `connect.validate` | marker/version/availability checks |
| Inspect task state | `rkf.status` | OFF or active task receipt |
| Finish RKF work | `rkf.deactivate` | append-only close event and return to OFF |

## Trigger Phrases

- "Preview connecting this project to RKF."
- "Apply the reviewed project connection."
- "Activate RKF for this task and validate the connection."
- "Show the current RKF status."
- "Deactivate RKF now."
- "先 preview 這個 project 的 RKF connection。"
- "啟動 RKF 並確認 marker。"
- "停用 RKF。"

## Connection Rules

- Preview before apply; never overwrite an existing marker or bridge silently.
- A v2 marker contains a stable random `project_id`, never an absolute path.
- A marker means available, not active. Every new task starts OFF.
- Open one task-owned runtime and reuse it for all actions in that task.
- Keep raw prompts, credentials, private paths, PDFs, and article text out of
  connection metadata and lineage.
- The `RKF/` bridge is a lightweight pointer surface, not another wiki or
  Evidence store.
- If validation fails, remain OFF and report the blocker without guessing a
  different checkout or storage root.

## Boundary

After successful activation, route research intent to `workflow.add`,
`workflow.ask`, `workflow.read`, `workflow.compare-synthesize`, or
`workflow.review`. Compatibility helpers are internal and do not expand the
access layer.
