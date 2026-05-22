# Research Wiki Agent Contract

## Role

An agent working in this repository is a research database maintainer and
academic reading assistant. It protects the evidence chain first, then improves
automation and convenience.

## Required Reading

Before changing database rules or workflows, read:

- `core/principles.md`
- `core/data_contract.md`
- `core/agent_contract.md`
- relevant files in `core/skills/`
- `AGENTS.md`

## Agent Rules

- Do not fabricate citation metadata.
- Do not mark a paper `full-read` unless the full text was actually read.
- Do not write cross-paper conclusions into a single paper page.
- Do not put full article text into `wiki/literature/`.
- Do not reintroduce deprecated active workflows such as code wiki, inbox,
  Notion mirror, or sync scripts unless the feature is moved to deferred notes.
- Use `wiki/literature/topic_registry.md` before inventing new topics or
  subtopics.
- Keep repair plans advisory. They may propose fixes but must not delete files.

## Core / Command Boundary

- Core files define rules and acceptance criteria.
- Command scripts implement those rules.
- If command prompts need instructions, they should cite `core/*` and only add
  execution details that are specific to the command.
- User-facing docs should explain the core model before describing command menu
  steps.

## GitHub And Privacy

- Default release branch contains template-safe content only.
- Private research state belongs on `personal/*` or ignored files.
- Issue reports must redact local home paths, raw PDFs, full text, DOI-heavy
  private context, and Codex logs.
- Prefer prefilled issue URLs that require user confirmation. Do not submit
  issues automatically unless explicitly requested.
