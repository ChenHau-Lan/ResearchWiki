---
name: rkf-lint
description: Route RKF quality, evidence-boundary, link-integrity, and public-safety checks through v1 Review. Use when the user asks what to fix next, which locators or verification steps are missing, whether Claims are disputed, or whether public output is safe. Return findings and repair actions without automatic trust promotion or deletion.
---

# RKF Review And Quality Checks

Use this skill for actionable Review. It can call internal validators, but the
user-facing result remains one Review workflow rather than a separate checker
taxonomy.

## Workflow Routing

| User intent | Structured action | Result |
|---|---|---|
| Review the current project | `workflow.review` | prioritized gaps and next reading action |
| Find missing Evidence details | `workflow.review` | missing locators, invalid states, and affected IDs |
| Inspect trust readiness | `workflow.review` | pending verification and disputed Claim findings |
| Check publication safety | `workflow.review` | blocking private-data or unsupported-claim findings |
| Request a repair plan | `workflow.review` | ordered human-review actions without automatic mutation |

## Trigger Phrases

- "Review this RKF project and tell me what to fix next."
- "Find Evidence cards that are missing exact locators."
- "Which Claims are disputed or still waiting for human verification?"
- "Check whether this output is safe to publish."
- "Give me a repair plan, but do not change files."
- "檢查這個 RKF project 還缺什麼。"
- "找出缺 locator 或 verification 的 Evidence。"
- "確認 public output 沒有 private path、PDF 或 article text。"

## Review Rules

- Report findings by severity, affected object, evidence, and next action.
- Do not auto-delete, auto-repair, or silently rewrite knowledge objects.
- Do not promote candidates, ledger events, provider output, or model output to
  stable Evidence.
- Do not invent a source to repair an unsupported Claim.
- Public-safety failures block publication.
- A Review receipt may include path-redacted project and activation lineage; it
  must not expose raw prompts, secrets, article text, PDFs, or private paths.
- Internal validators and derived projections remain implementation details;
  their names are not additional user workflows.
