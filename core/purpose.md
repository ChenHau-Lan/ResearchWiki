# Research Wiki Purpose

Research Wiki exists to turn research evidence into durable, reviewable
knowledge without losing provenance. It is a compiler-style knowledge base:
sources enter as evidence, LLM/Codex work compiles them into structured wiki
pages, and diagnostics keep the compiled artifact honest over time.

## Primary Goal

Support academic research by making it easy to answer:

- What have we read?
- Which claims are well supported?
- Which claims are uncertain, contradicted, or stale?
- Which sources should update concepts, synthesis, overview pages, or active
  research questions?

## In Scope

- DOI, URL, PDF, seminar, meeting, and user-provided research sources.
- QCed full-text evidence and concise paper pages.
- Concept pages for recurring mechanisms, methods, datasets, instruments,
  models, and variables.
- Synthesis pages for cross-source judgment.
- Overview and hot-question pages that help a researcher navigate the current
  state of the field.
- Review queues, fan-out candidates, thesis runs, runtime state, and graph
  exports that make research operations auditable.

## Out Of Scope

- Unauthorized full-text acquisition.
- Treating generated answers as evidence without source links.
- Copying full article text into the curated wiki.
- Automatically upgrading one source into broad synthesis without review.
- Replacing human research judgment with unchecked automation.

## Success Criteria

- Every important claim can be traced back to evidence or a review need.
- Query is read-only, Save is deliberate, Lint is repeatable, and Research
  produces source-labeled outputs.
- One source can influence multiple pages, but fan-out happens through
  candidates and review, not hidden side effects.
- High-confidence claims have counter-evidence review or an explicit missing
  counter-evidence note.
- The wiki remains useful to future agents because state, graph, queues, and
  logs are generated or maintained in predictable places.
