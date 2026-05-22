---
type: maintenance
status: draft
source_status: personal-note
reading_status: mixed
review_stage: ai-extracted
topics: []
subtopics: []
keywords: [github, branch_management, current_state]
created: 2026-05-21
updated: 2026-05-21
sources: []
---

# Current GitHub Arrangement

This note records the current repository and branch arrangement after the
Research Wiki core/command/GitHub support refactor.

## Remote

- GitHub repository: `ChenHau-Lan/wiki_research`
- Remote name: `origin`
- Remote URL: `git@github.com:ChenHau-Lan/wiki_research.git`

## Branches Now

- `origin/main`: GitHub integration branch.
- `origin/codex/core-command-github`: current draft PR branch for the core,
  command, GitHub support, install docs, and testing refactor.
- local `codex-core-command-github`: local tracking branch for
  `origin/codex/core-command-github`. The local name uses hyphens because a
  slash branch creation failed locally earlier, but it pushes to the correct
  remote branch name.
- local `main`: currently has one local-only commit,
  `7470cf6 Daily wiki sync 2026-05-18`, ahead of `origin/main`.

## Current PR

- PR: `https://github.com/ChenHau-Lan/wiki_research/pull/1`
- Head branch: `codex/core-command-github`
- Base branch: `main`
- State: draft
- Purpose: make the repository GitHub-ready as a template-like Research Wiki
  with `core/`, command implementation, support issue flow, install docs, CI,
  and synthetic workflow tests.

## Should Other Branches Be Uploaded?

No additional branches need to be uploaded right now.

The current refactor has already been pushed as one clean remote branch:

- `codex/core-command-github`

The local `main` commit `7470cf6 Daily wiki sync 2026-05-18` should not be
pushed directly to GitHub `main` right now. It contains older sync/personal
workflow state that is not part of the cleaned core/command template direction.

If that local-only commit contains anything worth preserving, use one of these
routes after review:

- move it to a `personal/chenhau-lan` branch if it represents private or
  personal research state;
- cherry-pick selected files into a future `codex/*` branch if they are still
  useful for the public template;
- leave it local and do not publish it if it only records obsolete workflow
  state.

## Branch Discipline Going Forward

- Use `main` only as the protected integration branch.
- Use `codex/core-*` for rule, contract, skill, and test-contract changes.
- Use `codex/command-*` for command/UI implementation changes.
- Use `codex/github-*` for GitHub Actions, issue templates, PR templates, and
  release/support tooling.
- Use `personal/*` for private research state, personal DOI dashboards, topic
  preferences, local project history, and anything that should not become part
  of the reusable template.

## Merge Plan

1. Review PR #1 while it remains draft.
2. Confirm CI stays green.
3. Confirm no raw PDFs, full-text Markdown, support reports, Codex logs, local
   paths, or private research state are tracked.
4. Mark PR #1 ready for review or merge it when the repository owner is
   satisfied.
5. After PR #1 is merged, delete `origin/codex/core-command-github`.
6. Only then decide what to do with local `main`'s `7470cf6` commit.

## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects: [[project_synthesis/project_synthesis]]
