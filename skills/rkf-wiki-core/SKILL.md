---
name: rkf-wiki-core
description: Operate the RKF LLM Wiki memory: retrieve governed wiki context, coordinate ARS reasoning, save durable discussion results, track paper reading queues, export graph, and create compact context capsules. Use when the task mentions LLM Wiki, knowledge base memory, query, save, graph, paper queue, nudge, reading feedback, wiki context capsule, 問知識庫, 回寫wiki, 保存討論結果, 查詢wiki, 知識圖譜, paper推播, or context capsule. Use rkf-connect for multi-computer shared folders or sandbox access permissions.
---

# RKF Wiki Core

Use this skill for LLM Wiki operations that do not acquire evidence. It keeps
useful discussion from disappearing into chat history while preserving reading
maturity and claim boundaries.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `query` | Retrieve governed RKF context and, when useful, ask ARS to reason over it | answer plus save/synthesis proposal |
| `hot-query` | Track repeated public-safe research questions and paper-search demand | generated `hot.md` summary |
| `paper-status` | Inspect registered papers by reading state, full-text status, and feedback | maturity/status report |
| `paper-feedback` | Record user questions, corrections, annotations, or trust changes | ledger event and maturity update |
| `paper-queue` | List papers needing PDF, human feedback, repeated-question review, or synthesis review | prioritized queue |
| `paper-nudge` | Produce scheduled public-safe paper reminders | nudge text |
| `status` | Reconstruct compact workspace state at the start of a session | source/evidence/topic/log/maturity summary |
| `save` | Save durable non-paper knowledge with boundary | knowledge object |
| `propagate` | Identify pages affected by new evidence or synthesis | proposal-only review gate |
| `graph` | Export typed source/evidence/wiki links | `graph/research_graph.json` |
| `external-sandbox` | Generate compact wiki context prompt | context capsule |

## Trigger Phrases

Use this skill when the user says things like:

- "What does my wiki know about this?"
- "Use the wiki and ARS to analyze this question."
- "Save this discussion back to the wiki."
- "Show me papers that need my feedback."
- "Which registered paper should I read next?"
- "Generate today paper nudge."
- "Record my correction for this paper."
- "Show me the current RKF status before we continue."
- "Which pages might this new evidence affect? Do not rewrite them yet."
- "Export the research graph."
- "Make a context capsule for another sandbox."
- "問我的知識庫"
- "根據 wiki 脈絡分析這個問題"
- "把剛剛值得保留的內容回寫 wiki"
- "列出需要我提供 PDF 或 feedback 的 paper"
- "做一份外部 sandbox prompt"
- "產生知識圖譜"

## Query Flow

1. Retrieve relevant topic, source, paper, concept, question, claim, synthesis,
   and reading-ledger summaries from RKF.
2. Let ARS reason over the governed context when the user asks for analysis,
   recommendation, critique, or research direction.
3. Return the answer with evidence gaps and maturity gaps.
4. Save only if the result meets the synthesis/save heuristic.

## Save Heuristic

Save only when the result will matter later: a decision, reusable explanation,
source-backed claim, open question, topic boundary, evidence gap, maturity
change, human correction, or review blocker.

## Rules

- Retrieval is not persistence.
- Hot-query recording is operational demand tracking, not evidence or a saved
  knowledge object.
- Reading ledgers are operational memory, not stable claim evidence by
  themselves.
- Save must choose a target layer.
- Saving must not overwrite existing knowledge unless the update path is
  explicit.
- Propagation review is proposal-only and must not rewrite stable pages by
  itself.
- A query answer is not a wiki page until saved.
- Do not save unsupported chat claims as stable knowledge.
- External sandbox results return as save/review/synthesis proposals.
- Use `rkf-connect` when the task is about Drive links, cross-computer setup, or
  sandbox permissions rather than a plain context capsule.
