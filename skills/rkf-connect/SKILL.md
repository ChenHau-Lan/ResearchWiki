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
| `sandbox-bootstrap` | Start another sandbox with RKF path, CLI, and reading-boundary rules | bootstrap prompt |
| `sandbox-direct-write` | Let a trusted sandbox use RKF CLI directly while preserving maturity and claim boundaries | guarded write workflow |
| `sandbox-save-proposal` | Convert sandbox discoveries into RKF proposals | save/review proposal |

## Trigger Phrases

Use this skill when the user says things like:

- "Set up a shared RKF database across my computers."
- "Use Google Drive as the shared RAW and wiki folder."
- "Link this wiki into another sandbox."
- "Give an external sandbox read access to my RKF wiki."
- "Start RKF mode in another sandbox."
- "Let another sandbox search papers and add them to RKF."
- "Save useful questions from another sandbox back to RKF."
- "建立共享資料庫在不同電腦"
- "把 Drive 裡的 RAW 和 wiki 連到 RKF 資料夾"
- "設定外部 sandbox 可以讀 wiki"
- "在其他 sandbox 啟動 RKF"
- "讓其他 sandbox 搜尋論文並加入 wiki"
- "把 sandbox 裡值得保存的問題回寫 RKF"

## Connection Rules

- Treat this as experimental unless the user says the workspace is already
  standardized.
- The shared Drive folder stores the real `RAW` and `wiki` data.
- Each computer may create local links into its RKF folder, but those links and
  machine-specific paths are not the public source of truth.
- External sandboxes are read-only by default.
- A trusted sandbox may write through RKF CLI only when the user grants the RKF
  repo as a writable workspace and the workflow still preserves RKF boundaries.
- A trusted sandbox may record public-safe hot-query signals through RKF, but
  those signals remain operational memory in `hot.md`, not evidence.
- Sandbox outputs become RKF save/review proposals when write access is missing,
  topic fit is unclear, full text is unavailable, reading maturity is low,
  locators are insufficient, or human review is needed.
- Never expose private tokens, account-specific paths, or unpublished evidence
  in public docs.

## External Sandbox Workflow

Use `sandbox-bootstrap` when the user wants another project or sandbox to start
using RKF without switching back to the main RKF session. Provide a bootstrap
prompt that tells the sandbox to read the generated context capsule, replace
`<RKF_REPO_PATH>` with the local RKF repo path, and follow RKF reading and claim
rules.

Use `sandbox-direct-write` only for trusted sandboxes with explicit workspace
write access. The direct-write path is still guarded:

```text
paper search
  -> source candidate
  -> capture DOI/URL/PDF pointer
  -> paper reading draft
  -> full-text status update; request user PDF only when unavailable
  -> reading feedback or locator check
  -> claim/synthesis readiness review
  -> lint and public-safety scan
```

If the sandbox cannot satisfy the boundary for a stable claim or trusted
synthesis, it must stop at `sandbox-save-proposal` instead of editing a stable
claim.

Recommended bootstrap files:

- `prompts/external_sandbox_context.md`: generated local context capsule; may
  contain machine-specific paths and is not committed.
- `prompts/external_sandbox_bootstrap.en.md`: committed reusable startup prompt
  with `<RKF_REPO_PATH>` placeholders.
- `prompts/external_sandbox_bootstrap.zh-TW.md`: committed reusable startup
  prompt with `<RKF_REPO_PATH>` placeholders.
