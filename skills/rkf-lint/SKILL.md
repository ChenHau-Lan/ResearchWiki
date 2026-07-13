---
name: rkf-lint
description: Maintain RKF health: structure lint, reading maturity lint, claim-boundary lint, reconcile contradiction detection, graph lint, ARS handoff lint, public safety lint, stale synthesis checks, candidate backlog checks, and repair plans. Use when checking repository quality, wiki consistency, contradictions, evidence boundaries, publication safety, maintenance, 檢查知識庫, 定期維護, 修復計畫, 證據邊界, 閱讀成熟度, 圖譜檢查, or public repo safety.
---

# RKF Lint

Use this skill to keep the RKF wiki safe to grow. Lint is maintenance: it keeps
topics from drifting, registered papers from going dormant, reading maturity
from becoming ambiguous, claim boundaries from blurring, graph links from
breaking, and private material out of Git.

## Modes

| Mode | Checks |
|---|---|
| `structure-lint` | frontmatter, page type, required sections, topic registry |
| `evidence-lint` | reading maturity fields, full-text state, legacy records, claim boundary |
| `graph-lint` | source/evidence/wiki/topic typed links and dangling references |
| `ars-handoff-lint` | ARS output is labeled as proposal or review blocker, not evidence |
| `public-safety-lint` | PDFs, full article text, local paths, private Drive paths |
| `reconcile` | same-topic contradiction hints and AI-marked blockers |
| `repair-plan` | human-readable fixes only |

Use `rkf-knowledge-synthesis` `topic-review` when the user wants semantic topic
recommendations such as merges, splits, aliases, and better search strings.
Use lint when the user wants checks, findings, drift diagnosis, or repair
planning.

## Trigger Phrases

Use this skill when the user says things like:

- "Check whether this wiki is safe to publish."
- "Audit evidence boundaries."
- "Find papers with stale reading state."
- "Find broken graph links."
- "Check topic drift and stale synthesis."
- "Find contradictions across pages."
- "Give me a repair plan."
- "檢查知識庫有沒有問題"
- "做一次定期維護"
- "確認 PDF / private path 沒有進 Git"
- "檢查 paper reading maturity"
- "檢查 ARS 回寫是不是被標成 proposal"
- "幫我做修復建議，不要自動改"

## Maintenance Rhythm

- Active topic: run structure, evidence/maturity, graph, ARS handoff, and
  public-safety checks weekly or after major reading changes.
- Stable topic: run monthly checks for stale synthesis, unresolved candidates,
  papers needing user PDF/feedback, topic drift, and graph health.
- Before sharing or publishing: public-safety lint is mandatory.

## Rules

- Do not auto-delete.
- Do not auto-promote candidates or ledger events to stable evidence.
- Do not repair unsupported claims by inventing sources.
- Reconcile output must be marked as AI integration when it writes blockers.
- Do not treat ARS output as a reviewed source without RKF review.
- Public-safety failures block publication.
