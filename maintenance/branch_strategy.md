---
type: maintenance
status: draft
source_status: personal-note
reading_status: mixed
review_stage: ai-extracted
topics: []
subtopics: []
keywords: [github, branch_management, release]
created: 2026-05-21
updated: 2026-05-21
sources: []
---

# Branch Strategy

This repository is private-first. Treat `main` as the integration branch that
should remain template-safe and eventually publishable.

## Branches

- `main`: protected integration branch; merge by PR only.
- `codex/core-*`: core contract, principles, skills, and test contract changes.
- `codex/command-*`: command/UI implementation changes.
- `codex/github-*`: GitHub Actions, issue templates, release/support tooling.
- `personal/*`: private user research state, personal DOI dashboards, raw
  evidence decisions, and project-specific notes.

## Protection Rules

Configure GitHub branch protection for `main`:

- require pull requests before merging;
- require status checks: `template-ci` and `mac-command-smoke`;
- block force pushes;
- block branch deletion;
- require review/conversation resolution when collaborators are added.

## Release Rule

Before public release:

- run `python3 tools/check_install.py --strict`;
- run the lint/doctor/repair workflow;
- run the synthetic workflow test;
- confirm no private raw PDFs, full text, local paths, support reports, or
  Codex logs are tracked.

## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects: [[project_synthesis/project_synthesis]]
