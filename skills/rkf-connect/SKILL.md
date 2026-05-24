---
name: rkf-connect
description: Manage experimental RKF shared-database connections: Google Drive-backed RAW/wiki folders, multi-computer symlink or junction plans, and external sandbox read/save boundaries. Use when the task mentions shared database, Google Drive, ResearchSync, symlink, junction, ln, external sandbox access, connect wiki, 共享資料庫, 多台電腦, 連結wiki, 連結RAW, 外部sandbox, or sandbox回寫.
---

# RKF Connect

Use this skill when RKF must be used across multiple computers or external
sandboxes. It is a connection and permission skill, not an evidence or synthesis
skill.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `shared-database-plan` | Plan a Google Drive-backed shared RAW/wiki layout | machine-neutral setup plan |
| `link-workspace` | Link shared RAW/wiki folders into one local RKF project | per-machine link checklist |
| `sandbox-grant` | Give an external sandbox safe read context and boundaries | access capsule |
| `sandbox-save-proposal` | Convert sandbox discoveries into RKF proposals | save/review proposal |

## Trigger Phrases

Use this skill when the user says things like:

- "Set up a shared RKF database across my computers."
- "Use Google Drive as the shared RAW and wiki folder."
- "Link this wiki into another sandbox."
- "Give an external sandbox read access to my RKF wiki."
- "Save useful questions from another sandbox back to RKF."
- "建立共享資料庫在不同電腦"
- "把 Drive 裡的 RAW 和 wiki 連到 RKF 資料夾"
- "設定外部 sandbox 可以讀 wiki"
- "把 sandbox 裡值得保存的問題回寫 RKF"

## Connection Rules

- Treat this as experimental unless the user says the workspace is already
  standardized.
- The shared Drive folder stores the real `RAW` and `wiki` data.
- Each computer may create local links into its RKF folder, but those links and
  machine-specific paths are not the public source of truth.
- External sandboxes are read-only by default.
- Sandbox outputs become RKF save/review proposals unless the user explicitly
  approves a stable write path.
- Never expose private tokens, account-specific paths, or unpublished evidence
  in public docs.
