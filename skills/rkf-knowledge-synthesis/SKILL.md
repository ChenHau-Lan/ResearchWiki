---
name: rkf-knowledge-synthesis
description: Route cross-paper comparison and synthesis through RKF v1 Compare & Synthesize. Use when the user wants to compare locator-backed Evidence, identify agreement, contradiction, context, or gaps, and create an Evidence-linked Claim or Synthesis without hiding uncertainty.
---

# RKF Knowledge Synthesis

Use this skill when a question crosses papers or Evidence cards. One-paper
annotation belongs to Read; source-bounded retrieval belongs to Ask. This skill
starts only when the user wants comparison or a durable cross-source judgment.

## Workflow Routing

| User intent | Structured action | Result |
|---|---|---|
| Compare Evidence | `workflow.compare-synthesize` | evidence matrix with support, opposition, and context |
| Form a reviewable Claim | `workflow.compare-synthesize` | Claim linked to exact Evidence IDs |
| Build a Synthesis | `workflow.compare-synthesize` | agreements, contradictions, gaps, provisional conclusion, next action |
| Reassess an existing conclusion | `workflow.compare-synthesize` | updated evidence links and explicit unresolved differences |

## Trigger Phrases

- "Compare these Evidence cards across papers."
- "Which findings agree, contradict, or only provide context?"
- "Create a provisional Claim linked to the supporting and opposing Evidence."
- "Synthesize these papers, but preserve the unresolved gap."
- "Reassess this conclusion after adding the new Evidence."
- "比較這些 Evidence，列出 agreement、contradiction 與 gap。"
- "建立 provisional Claim，不要隱藏 opposing Evidence。"
- "整理成 Synthesis，並指出下一個閱讀行動。"

## Synthesis Rules

- Every supported, disputed, or verified Claim must link locator-backed
  Evidence.
- A verified Claim requires at least one human-verified Evidence card.
- Preserve supporting, opposing, and contextual Evidence separately.
- Keep a conclusion provisional when coverage, verification, or scope is
  incomplete.
- ARS reports and model reasoning are proposals, not Evidence.
- Do not move project ideas or manuscript extensions into a paper-centered
  finding; keep the paper's own question and scope intact.
- If the request is actually a queue, missing-locator, or trust audit, route it
  to `workflow.review`.
