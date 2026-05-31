---
name: rkf-wiki-core
description: Operate the RKF LLM Wiki memory: retrieve governed wiki context, coordinate ARS reasoning over that context, save durable discussion results, export graph, and create compact context capsules. Use when the task mentions LLM Wiki, knowledge base memory, query, save, graph, wiki context capsule, 問知識庫, 回寫wiki, 保存討論結果, 查詢wiki, 知識圖譜, or context capsule. Use rkf-connect for multi-computer shared folders or sandbox access permissions.
---

# RKF Wiki Core

Use this skill for LLM Wiki operations that do not acquire evidence. It keeps
useful discussion from disappearing into chat history while preserving evidence
boundaries.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `query` | Retrieve governed RKF context and, when useful, ask ARS to reason over it | answer plus save/synthesis proposal |
| `hot-query` | Track repeated public-safe research questions and paper-search demand | generated `hot.md` summary |
| `save` | Save durable non-paper knowledge with boundary | knowledge object |
| `graph` | Export typed source/evidence/wiki links | `graph/research_graph.json` |
| `external-sandbox` | Generate compact wiki context prompt | context capsule |

## Trigger Phrases

Use this skill when the user says things like:

- "What does my wiki know about this?"
- "Use the wiki and ARS to analyze this question."
- "Save this discussion back to the wiki."
- "Export the research graph."
- "Make a context capsule for another sandbox."
- "問我的知識庫"
- "根據 wiki 脈絡分析這個問題"
- "把剛剛值得保留的內容回寫 wiki"
- "做一份外部 sandbox prompt"
- "產生知識圖譜"

## Query Flow

1. Retrieve relevant topic, source, paper, concept, question, claim, and
   synthesis pages from RKF.
2. Let ARS reason over the governed context when the user asks for analysis,
   recommendation, critique, or research direction.
3. Return the answer with evidence gaps.
4. Save only if the result meets the synthesis/save heuristic.

## Save Heuristic

Save only when the result will matter later: a decision, reusable explanation,
source-backed claim, open question, topic boundary, evidence gap, or review
blocker.

## Rules

- Retrieval is not persistence.
- Hot-query recording is operational demand tracking, not evidence or a saved
  knowledge object.
- Save must choose a target layer.
- A query answer is not a wiki page until saved.
- Do not save unsupported chat claims as stable knowledge.
- External sandbox results return as save/review/synthesis proposals.
- Use `rkf-connect` when the task is about Drive links, cross-computer setup, or
  sandbox permissions rather than a plain context capsule.
