---
name: rkf-knowledge-synthesis
description: Write and maintain RKF knowledge objects from active reading state and governed wiki context: paper drafts, questions, concepts, claims, topics, synthesis, overviews, meetings, seminars, and topic review recommendations. Use when the task asks to create, update, synthesize, organize wiki knowledge, review topics, merge or split topics, refresh topic search strings, 整理成wiki, 論文筆記, 文獻摘要, 概念頁, 問題頁, 主題治理, topic整理, topic建議, or 綜整.
---

# RKF Knowledge Synthesis

Use this skill for the knowledge side of RKF. Paper pages are active reading
objects: they may begin as conservative drafts from metadata, abstracts, partial
full text, or user-provided PDFs. Non-paper pages must state their evidence
boundary, maturity boundary, or review blocker.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `distill-paper` | Create or update one paper reading draft | `knowledge/papers/*.md` with maturity fields |
| `save-question` | Preserve research question, uncertainty, or search plan | question page |
| `save-concept` | Preserve reusable method, mechanism, dataset, instrument, or variable | concept page |
| `save-claim` | Preserve a supported or reviewable claim | claim page or review item |
| `synthesize` | Save cross-source judgment, research recommendation, or durable answer | synthesis page with maturity fields |
| `topic-governance` | Topic ID, aliases, scope, include/exclude, default search | topic registry/page |
| `topic-review` | Regularly inspect topic drift, stale candidates, duplicate topics, and search quality | topic review report and update proposal |

## Trigger Phrases

Use this skill when the user says things like:

- "Turn this source into a paper draft."
- "Summarize this paper into my wiki."
- "Record what we currently understand about this paper."
- "Make a concept/question/synthesis page."
- "Connect these papers into a recommendation."
- "Save this query answer as durable synthesis."
- "Review this topic and suggest merge/split/search-string updates."
- "把這篇 paper 先整理成 draft"
- "幫我做論文筆記"
- "整理成概念頁 / 問題頁 / 綜整頁"
- "定期查看 topic / 整理 topic / 給 topic 建議"
- "針對這些文獻提出研究建議並保存"

## Synthesis Heuristic

Use `synthesize` when an answer crosses multiple sources, supports a research
decision, will likely be asked again, exposes evidence gaps, changes topic
direction, or reflects repeated human interaction. Otherwise return a query
answer or save a smaller question/concept.

## Topic Review Heuristic

Use `topic-review` when a topic is active, has many candidates, has ambiguous
aliases, mixes unrelated scopes, repeats concepts, has stale synthesis, or
needs better search strings. Suggest merges, splits, alias changes,
include/exclude rules, canonical pages, and candidate backlog cleanup.

## Rules

- A paper draft reports one source and its current reading state.
- A paper draft may be metadata-only, abstract-read, partial-fulltext, or
  fulltext-read; the page must say which.
- A paper page can mature through user questions, AI answers, human corrections,
  annotations, checked locators, and synthesis review.
- Cross-source judgment belongs in synthesis.
- Query answers are not wiki pages until deliberately saved.
- Every promoted claim needs a locator, human feedback, existing wiki source, or
  explicit review blocker.
- Trusted synthesis must record source coverage, human feedback level, and
  claim readiness.
- Topic changes should preserve stable IDs when possible; propose redirects or
  aliases before splitting established pages.
- ARS outputs are proposals, not evidence. Apply the bridge protocol before
  saving ARS-derived material.
