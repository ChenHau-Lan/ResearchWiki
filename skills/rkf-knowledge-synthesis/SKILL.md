---
name: rkf-knowledge-synthesis
description: Write and maintain RKF knowledge objects from reviewed evidence and governed wiki context: paper pages, questions, concepts, claims, topics, synthesis, overviews, meetings, seminars, and topic review recommendations. Use when the task asks to create, update, synthesize, organize wiki knowledge, review topics, merge or split topics, refresh topic search strings, 整理成wiki, 論文筆記, 文獻摘要, 概念頁, 問題頁, 主題治理, topic整理, topic建議, or 綜整.
---

# RKF Knowledge Synthesis

Use this skill for the knowledge side of RKF. Paper pages come from reviewed
paper evidence, usually QCed PDFs. Non-paper pages must state their evidence
boundary or review blocker.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `distill-paper` | Turn reviewed paper evidence into one paper wiki page | `knowledge/papers/*.md` |
| `save-question` | Preserve research question, uncertainty, or search plan | question page |
| `save-concept` | Preserve reusable method, mechanism, dataset, instrument, or variable | concept page |
| `save-claim` | Preserve a supported or reviewable claim | claim page or review item |
| `synthesize` | Save cross-source judgment, research recommendation, or durable answer | synthesis page |
| `topic-governance` | Topic ID, aliases, scope, include/exclude, default search | topic registry/page |
| `topic-review` | Regularly inspect topic drift, stale candidates, duplicate topics, and search quality | topic review report and update proposal |

## Trigger Phrases

Use this skill when the user says things like:

- "Turn this verified paper evidence into a wiki page."
- "Summarize this paper into my wiki."
- "Make a concept/question/synthesis page."
- "Connect these papers into a recommendation."
- "Save this query answer as durable synthesis."
- "Review this topic and suggest merge/split/search-string updates."
- "把這份 QC 過的 PDF 整理成 wiki page"
- "幫我做論文筆記"
- "整理成概念頁 / 問題頁 / 綜整頁"
- "定期查看 topic / 整理 topic / 給 topic 建議"
- "針對這些文獻提出研究建議並保存"

## Synthesis Heuristic

Use `synthesize` when an answer crosses multiple sources, supports a research
decision, will likely be asked again, exposes evidence gaps, or changes topic
direction. Otherwise return a query answer or save a smaller question/concept.

## Topic Review Heuristic

Use `topic-review` when a topic is active, has many candidates, has ambiguous
aliases, mixes unrelated scopes, repeats concepts, has stale synthesis, or
needs better search strings. Suggest merges, splits, alias changes,
include/exclude rules, canonical pages, and candidate backlog cleanup.

## Rules

- Paper pages require reviewed paper evidence.
- A paper page reports one source; cross-source judgment belongs in synthesis.
- Query answers are not wiki pages until deliberately saved.
- Every promoted claim needs a locator, existing wiki source, or review blocker.
- Topic changes should preserve stable IDs when possible; propose redirects or
  aliases before splitting established pages.
- ARS outputs are proposals, not evidence. Apply the bridge protocol before
  saving ARS-derived material.
