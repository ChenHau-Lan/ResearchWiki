# LLM Wiki Video Content Brief

This file is an original, structured brief for using the LLM Wiki idea inside
ResearchWiki. It is not a verbatim transcript. If authorized captions are added
later, keep quotations short and cite the source; otherwise use paraphrase.

## Core Message

An LLM Wiki turns accumulated work into a persistent, model-readable knowledge
base. Instead of treating each chat as disposable context, the user and agent
save durable decisions, source-backed claims, project state, and open questions
into plain text pages that future sessions can read.

## Working Principles

- Keep knowledge in simple files that both humans and models can inspect.
- Save only material that will matter later: decisions, source-backed claims,
  reusable explanations, open questions, and task state.
- Prefer small linked pages over one giant context dump.
- Separate raw evidence from interpretation.
- Treat retrieval as part of the workflow: every useful answer should be able to
  point back to the page or source that justified it.
- Let the wiki compound. Each session should leave the project easier to resume.

## ResearchWiki Translation

- `raw/` stores source pointers, PDFs, extracted text staging, QCed full text,
  and generated indexes.
- `wiki/` stores reading notes, questions, concepts, topics, and synthesis.
- `maintenance/` stores review queues, acquisition checkpoints, fan-out
  candidates, runtime state, and external-sandbox prompts.
- `knowledge-workbench/query` is read-only; `query-to-save` is the bridge from
  useful discussion to durable wiki update.
- Topic pages and question pages prevent automated search from drifting into
  loosely related literature.

## Save Heuristic

Save a discussion result when it meets at least one condition:

- It answers a recurring research question.
- It changes a synthesis, concept, topic boundary, or search strategy.
- It identifies a source lead or counter-evidence need.
- It records a project decision that future sessions must honor.
- It explains how to operate the repo or avoid a repeated mistake.

Do not save unsupported chat claims as formal knowledge. Stage uncertain items
in `maintenance/review_queue.md`.
