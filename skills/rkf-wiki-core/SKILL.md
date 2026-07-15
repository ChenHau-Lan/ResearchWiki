---
name: rkf-wiki-core
description: Route governed RKF retrieval through v1 Ask. Use when the user asks what RKF knows about a paper, topic, method, finding, or research question. Search exact identifiers and titles first, preserve evidence maturity, require locators for claim-supporting answers, and report insufficient evidence when support is missing.
---

# RKF Ask

Use this skill for source-bounded questions over governed RKF state. Retrieval
does not persist an answer, create Evidence, or upgrade a Claim.

## Workflow Routing

| User intent | Structured action | Result |
|---|---|---|
| Ask about a paper or topic | `workflow.ask` | exact-first, source-bounded answer |
| Ask for claim support | `workflow.ask` | Evidence IDs and exact locators, or insufficient evidence |
| Ask about disagreement | `workflow.ask` | supporting, opposing, and contextual Evidence kept separate |
| Ask what is unknown | `workflow.ask` | explicit gaps and recommended next reading action |

## Trigger Phrases

- "What does RKF know about this paper?"
- "Ask RKF what the sources report about this relationship."
- "Which Evidence supports or opposes this Claim?"
- "Answer only if RKF has an exact locator."
- "What is still unknown, and what should I read next?"
- "問 RKF 這篇 paper 的主要 finding。"
- "根據 governed RKF context 回答；沒有 locator 就說證據不足。"
- "哪些 Evidence 支持或反對這個 Claim？"

## Ask Flow

1. Require an active, validated task.
2. Search exact paper ID, DOI, title, and alias before deterministic keywords.
3. Filter results by object type, maturity, and evidence boundary.
4. For a claim-supporting answer, return Evidence IDs and exact locators.
5. Preserve contradiction, context, limitations, and unresolved gaps.
6. If support is insufficient, say so and recommend a Read or Review action.

## Rules

- Retrieval is not persistence or trust promotion.
- Candidate metadata and model output cannot support a stable Claim.
- Optional retrieval providers are internal and exact-first behavior remains the
  fallback.
- Never expose private index contents, raw prompts, PDFs, article text, secrets,
  or private paths.
- If the user wants to capture, annotate, synthesize, or audit rather than ask,
  route the request to the matching v1 workflow.
