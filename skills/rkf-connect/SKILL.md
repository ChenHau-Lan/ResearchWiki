---
name: rkf-connect
description: Manage experimental RKF shared-database connections: Google Drive-backed RAW/wiki folders, multi-computer symlink or junction plans, and Codex handoff read/save boundaries. Use when the task mentions shared database, Google Drive, ResearchSync, symlink, junction, ln, Codex handoff, connect wiki, handoff access, 共享資料庫, 多台電腦, 連結wiki, 連結RAW, or handoff回寫.
---

# RKF Connect

Use this skill when RKF must be used across multiple computers, connected
projects, or another Codex session. It is a connection and permission skill, not
an evidence or synthesis skill.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `shared-database-plan` | Plan a Google Drive-backed shared RAW/wiki layout | machine-neutral setup plan |
| `link-workspace` | Link shared RAW/wiki folders into one local RKF project | per-machine link checklist |
| `handoff-grant` | Give another Codex session/project safe read context and boundaries | access capsule |
| `handoff-bootstrap` | Start another Codex session/project with RKF context and reading-boundary rules | bootstrap prompt |
| `handoff-direct-write` | Let a trusted Codex handoff request guarded RKF actions after explicit write approval | guarded app workflow |
| `handoff-save-proposal` | Convert handoff discoveries into RKF proposals or low-risk AI-marked updates | save/review proposal, evolve/reconcile/emerge request |

## Trigger Phrases

Use this skill when the user says things like:

- "Set up a shared RKF database across my computers."
- "Use Google Drive as the shared RAW and wiki folder."
- "Link this wiki into another Codex project."
- "Give another Codex session read access to my RKF wiki."
- "Hand this RKF context to another Codex thread."
- "Start RKF mode in another Codex session."
- "Let another Codex session search papers and add them to RKF."
- "Save useful questions from another Codex session back to RKF."
- "Let another Codex session return evolve/reconcile/emerge updates."
- "建立共享資料庫在不同電腦"
- "把 Drive 裡的 RAW 和 wiki 連到 RKF 資料夾"
- "設定其他 Codex session 可以讀 wiki"
- "在其他 Codex session 啟動 RKF"
- "讓其他 Codex session 搜尋論文並加入 wiki"
- "把 handoff 裡值得保存的問題回寫 RKF"

## Connection Rules

- Treat this as experimental unless the user says the workspace is already
  standardized.
- The shared Drive folder stores the real `RAW` and `wiki` data.
- Each computer may create local links into its RKF folder, but those links and
  machine-specific paths are not the public source of truth.
- Another Codex session/project starts with a read/proposal boundary by default.
- A trusted handoff may request guarded RKF actions only when the user grants the
  RKF repo as a writable workspace and the workflow still preserves RKF
  boundaries.
- A trusted handoff may record public-safe hot-query signals through RKF, but
  those signals remain operational memory in `hot.md`, not evidence.
- Handoff outputs become RKF save/review proposals when write access is missing,
  topic fit is unclear, full text is unavailable, reading maturity is low,
  locators are insufficient, or human review is needed.
- Trusted handoffs may return `evolve`, `reconcile`, or `emerge` updates when
  every write is AI-marked, public-safe, and maturity-aware.
- Never expose private tokens, account-specific paths, or unpublished evidence
  in public docs.

## Codex Handoff Workflow

Use `handoff-bootstrap` when the user wants another project or Codex session to
start using RKF without switching back to the main RKF session. Provide a
bootstrap prompt that tells the handoff agent to read the generated context
capsule, resolve RKF state through the authorized workspace, and follow RKF
reading and claim rules.

Use `handoff-direct-write` only for trusted handoffs with explicit workspace
write access. The write path is still guarded:

```text
paper search
  -> source candidate
  -> capture DOI/URL/PDF pointer
  -> paper reading draft
  -> full-text status update; request user PDF only when unavailable
  -> reading feedback or locator check
  -> optional evolve/reconcile/emerge update with AI Integration Note
  -> claim/synthesis readiness review
  -> lint and public-safety scan
```

If the handoff cannot satisfy the boundary for a stable claim or trusted
synthesis, it must stop at `handoff-save-proposal` instead of editing a stable
claim.

Recommended bootstrap files:

- `prompts/codex_handoff_context.md`: generated local context capsule; may
  contain machine-specific paths and is not committed.
- `prompts/codex_handoff_bootstrap.en.md`: committed reusable startup prompt
  with `<RKF_REPO_PATH>` placeholders.
- `prompts/codex_handoff_bootstrap.zh-TW.md`: committed reusable startup
  prompt with `<RKF_REPO_PATH>` placeholders.
