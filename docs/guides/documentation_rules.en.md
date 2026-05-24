# Research Wiki Documentation Rules

This guide keeps Research Wiki documentation consistent as the project grows. It is for maintainers and Codex agents who edit user-facing docs, core contracts, manuals, support guides, or PR descriptions.

## Documentation Layers

Research Wiki docs have different jobs. Put information in the lowest-confusion layer:

| Layer | Purpose | Typical files |
|---|---|---|
| First read | Explain what the project is and how to start | `README.md`, `README.zh-TW.md` |
| User operation | Explain skills, the optional router, folders, mode permissions, and workflows | `USER_GUIDE.md`, `USER_GUIDE.zh-TW.md` |
| Installation/support | Help a user install, check, and report issues | `INSTALL*`, `SUPPORT*` |
| Durable rules | Define what tools and agents must obey | `core/*`, `AGENTS.md` |
| Teaching manuals | Explain a complete workflow with screenshots and examples | `docs/manuals/*`, `output/pdf/*` |
| Reference guides | Explain concepts, structure, file roles, and version policy | `docs/guides/*`, `VERSION_LOG*` |
| Runtime history | Record actions and maintenance outcomes | `maintenance/log.md`, PR bodies |

Do not turn README into a full manual. README should tell a new user what
Research Wiki is, the skill-first pipeline mental model, how to start, where
the optional command router is, and where to read next.

## Product Teaching Voice

README, Quickstart, and beginner manuals must read like product teaching, not
PR records or migration notes. They should describe what the user does now,
what they will see, and where they go next.

Do not put these items in beginner-facing product docs:

- internal migration narrative, such as "old version", "v1/v2 refactor", or
  "this manual replaces...";
- old command, old option number, or old menu comparisons;
- screenshot redaction notes or "this screenshot does not contain private data"
  statements;
- PR, release, test observation, or cleanup history;
- maintainer rationale or raw user-feedback wording.

Put those details in `VERSION_LOG*`, `SUPPORT*`, `docs/guides/*`,
`maintenance/*`, or legacy pointers. Product teaching may keep necessary safety
boundaries, but phrase them as action rules, such as "use sources you are
allowed to use", not as upload or screenshot disclaimers.

## Bilingual And PDF Policy

Long-form teaching or reference docs must be written in both English and Traditional Chinese when they are intended for users. Each such guide should have:

- an English Markdown file;
- a Traditional Chinese Markdown file;
- rendered PDFs under `output/pdf/`;
- at least one Poppler render check before the PR is opened;
- a `pdftotext` check for important headings.

Short maintenance notes, repair plans, and PR-specific records may stay in one language unless they are user-facing guides.

## How To Update Docs Safely

When a workflow changes, update docs in this order:

1. Update the durable contract first if behavior or rules changed.
2. Update command prompts or tools after the rule exists.
3. Update USER_GUIDE when a user must operate the new behavior.
4. Update README only with a short entrypoint if first-time users need to know it.
5. Update manuals or guides when they teach the workflow.
6. Update `VERSION_LOG.md` and `VERSION_LOG.zh-TW.md` when the change affects a release-visible workflow, contract, or user mental model.

Do not copy a PR discussion or user complaint directly into docs. First translate it into a durable rule, workflow boundary, or user-facing explanation.

## PR Documentation Checklist

Every PR should state:

- what was intentionally uploaded;
- what was intentionally not uploaded;
- whether README/USER_GUIDE links changed;
- whether generated PDFs were refreshed;
- whether private raw PDFs, raw full text, local paths, and Codex logs were excluded;
- which tests and render checks ran.

If a PR changes workflow behavior, include the affected skill/mode mappings and
whether each mode writes files. If a PR changes evidence or wiki rules, mention
the affected `core/*` contract.

## Version Policy

Research Wiki starts at `v1.0.0` after the merged vNext compiler/manual baseline.
`v2.0.0` is the skill-first pipeline baseline because command semantics change.
Use:

- `v1.x.y` for compatible additions, documentation improvements, new guides, advisory tools, or skill/mode router changes that preserve existing contracts;
- `v1.(x+1).0` for user-visible compatible feature additions;
- `v2.0.0` for breaking changes to data contracts, command semantics, required frontmatter, folder roles, or migration expectations.

Users should be able to return to a preferred version by checking the version log and the PRs listed there.
