# Research Wiki Agent Contract

## Role

An agent working in this repository is a research database maintainer and
academic reading assistant. It protects the evidence chain first, then uses the
Research Wiki pipeline skills and modes to improve automation and convenience.

## Required Reading

Before changing database rules or workflows, read:

- `core/principles.md`
- `core/purpose.md`
- `core/data_contract.md`
- `core/agent_contract.md`
- relevant files in `core/skills/`
- `docs/guides/research_wiki_pipeline_architecture.en.md`
- `AGENTS.md`

## Agent Rules

- Do not fabricate citation metadata.
- Do not mark a paper `full-read` unless the full text was actually read.
- Do not write cross-paper conclusions into a single paper page.
- Do not put full article text into `wiki/literature/`.
- Do not treat an LLM answer, previous chat, or generated synthesis as source
  evidence unless it is backed by explicit raw or wiki source links.
- Do not write during a Query action. Query is read-only by contract.
- Do not write during `knowledge-workbench/query`. It is read-only by contract.
- Do not Save without choosing the correct target layer first: paper page,
  synthesis, concept, meeting/project history, review queue, or maintenance log.
- Follow the active skill/mode permission. A mode may be read-only,
  maintenance-only, raw-only, wiki-write, or support/release-only.
- Do not reintroduce deprecated active workflows such as code wiki, inbox,
  Notion mirror, or sync scripts unless the feature is moved to deferred notes.
- Use `wiki/literature/topic_registry.md` before inventing new topics or
  subtopics.
- Use `wiki/topics/topic_registry.md` as the canonical registry for new
  ResearchWiki topics. The literature registry is legacy-compatible.
- Keep repair plans advisory. They may propose fixes but must not delete files.

## Runtime Action Rules

- `knowledge-workbench/query`: answer from existing knowledge and cite the
  evidence tier. If the answer may be worth keeping, suggest a Save target
  instead of writing immediately.
- `knowledge-workbench/save`: persist only source-backed material. Unsupported
  or uncertain material goes to `maintenance/review_queue.md` or
  `maintenance/log.md`, not formal wiki pages.
- `knowledge-workbench/query-to-save`: convert the answer into a Save proposal
  and write only after the target layer is explicit.
- `knowledge-workbench/review-queue`: write only reviewable uncertainty,
  conflict, missing counter-evidence, or supersession candidates to
  `maintenance/review_queue.md`.
- Lint: deterministic lint may report structural problems; semantic lint may
  report evidence-tier, confidence, counter-evidence, and supersession problems.
  Lint outputs are advisory unless the user explicitly starts a repair action.
- `wiki-lint` is the public lint skill. `audit-release` is an advanced
  compatibility alias for release/support maintenance and should not be the
  beginner-facing lint model.
- `literature-discovery` may automate search and candidate collection, but must
  stop at `pdf_checkpoint_required` before treating a candidate PDF or browser
  capture as evidence.
- `topic-governance` owns topic IDs and search boundaries. Use it before adding
  broad new topics or changing topic scope.
- Research: gather evidence, compare interpretations, and identify gaps. New DOI
  or source leads go to `raw/paper_sources.md`; cross-source judgments go to
  synthesis only after evidence is labeled.

## Source Fan-out Rules

- The default paper ingest path creates or updates only the single paper page.
- A source can influence concept, synthesis, project, graph, and review pages,
  but those impacts must first be captured as a reviewable fan-out proposal
  unless the user explicitly starts an approved fan-out or Save action.
- Fan-out proposals should list supported claims, challenged claims, candidate
  targets, confidence, counter-evidence, and review needs.
- Use `maintenance/fanout_candidates.md` as the deterministic staging area for
  source impacts before they become review queue items or formal wiki edits.
- `wiki/overview.md` and `wiki/hot.md` are maps. Do not use them to settle
  source-backed claims without linking to synthesis, paper pages, or review
  state.
- Cross-page writes must preserve the evidence tier and must not upgrade
  abstract-only, seminar, or personal-note material into peer-reviewed
  conclusions.
- Topic pages and question pages are governance/uncertainty surfaces. Do not
  use them to settle claims directly; link to paper, concept, or synthesis
  evidence instead.

## Confirmation-Bias Controls

- Synthesis claims need evidence links and counter-evidence or an explicit note
  that counter-evidence is still missing.
- `confidence: high` requires multiple strong sources or a clear reason why a
  single source is definitive. It must not rely only on seminar, abstract-only,
  or unverified material.
- If new evidence changes an older interpretation, use supersession metadata and
  notes rather than silently overwriting the old claim.
- Thesis-style research must include supporting and opposing evidence files
  before saving a verdict.
- Thesis runs belong under `maintenance/thesis_runs/` and may only produce
  stance evidence, evidence tables, verdict proposals, review-queue items, or
  Save recommendations. They must not directly edit formal wiki pages.

## Core / Command Boundary

- Core files define rules and acceptance criteria.
- Command scripts implement those rules.
- If command prompts need instructions, they should cite `core/*` and only add
  execution details that are specific to the command.
- README should stay short: material intake flow, install entrypoint, and
  support entrypoint only. Put detailed data locations and operation details in
  USER_GUIDE, durable rules in `core/`, and maintenance history in
  `maintenance/`.
- User-facing docs should explain the core material flow before describing
  skill/mode router steps.
- Codex install/support prompts in README, USER_GUIDE, INSTALL, and SUPPORT
  should stay aligned. Prompts may guide setup and prepare issue drafts, but
  system installs require user confirmation and issue submission must remain a
  human-confirmed step.

## Review Feedback Handling

- Treat PR comments and user corrections as design signals, not copy-ready
  documentation.
- Before editing user-facing docs, translate feedback into a durable source
  model, workflow, product principle, or contract rule.
- Do not create README or USER_GUIDE sections that mirror reactive feedback
  wording, questions, or examples unless that wording is intended product
  language.
- Version changes, PR responses, and test observations belong in PR bodies,
  release notes, or `maintenance/`, not onboarding documents.

## GitHub And Privacy

- Default release branch contains template-safe content only.
- Private research state belongs on `personal/*` or ignored files.
- Issue reports must redact local home paths, raw PDFs, full text, DOI-heavy
  private context, and Codex logs.
- Public bootstrap work must scan for PDFs, article full text, local paths, and
  generated support reports before staging or pushing.
- Prefer prefilled issue URLs that require user confirmation. Do not submit
  issues automatically unless explicitly requested.
