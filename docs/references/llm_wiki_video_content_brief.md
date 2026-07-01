# LLM Wiki Content Brief

This file is an original, structured brief for using the LLM Wiki idea inside
Research Knowledge Framework. It is not a verbatim transcript of any video. If
authorized captions are supplied later, keep quotations short, cite the source,
and preserve this brief as original synthesis rather than copied transcript.

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
- Separate source candidates, reading maturity, private evidence, and
  interpretation.
- Treat retrieval as part of the workflow: every useful answer should be able to
  point back to the page or source that justified it.
- Let the wiki compound. Each session should leave the project easier to resume.

## RKF Translation

- `SourceRecord` stores candidates and metadata; it is not evidence.
- `EvidenceArtifact` stores a public-safe pointer to private evidence such as
  PDF, HTML snapshot, screenshot, or attachment.
- `KnowledgeObject` stores maintained understanding: paper, question, concept,
  claim, topic, synthesis, overview, project-synthesis, meeting, or seminar.
- Paper knowledge starts as active reading memory and matures through full-text
  status, user feedback, locator checks, and synthesis review.
- `ReadingLedger` stores public-safe operational reading events without turning
  those events into claim evidence by themselves.
- `GateDecision` records review blockers, legacy route notes, claim-support
  checks, synthesis review, and public-safety checks.
- `GraphEdge` makes source, evidence, topic, and knowledge relationships
  inspectable by humans and future LLM sessions.
- External sandbox capsules let another environment help while requiring useful
  results to return as save or review proposals.

## Save Heuristic

Save a discussion result when it meets at least one condition:

- It answers a recurring research question.
- It changes a synthesis, concept, topic boundary, or search strategy.
- It identifies a source lead or counter-evidence need.
- It records a project decision that future sessions must honor.
- It explains how to operate the framework or avoid a repeated mistake.

Do not save unsupported chat claims as formal knowledge. Stage uncertain items
as reading drafts or review work until locators, human feedback, or existing RKF
sources support promotion; explicit blockers clarify why promotion is paused.
