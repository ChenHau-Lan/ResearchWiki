# v1 Branch Hygiene Audit

Audit date: 2026-07-15

Comparison base: `main@06cf63d`

Open pull requests at pre-cleanup check: none

The connected GitHub repository was checked immediately before deletion.
`ahead` and `behind` describe commit topology; `net files` is the live compare
result against `main`. A historical branch was eligible only when it had no
open PR, was not default/release/active, and its net file diff was empty.

## Deleted remote branches

### Fully merged branches removed earlier

| Branch | Result |
|---|---|
| `codex/rkf-observatory` | Deleted 2026-07-14 after `ahead=0` verification. |
| `codex/rkf-auto-evolution-docs-cleanup` | Deleted 2026-07-14 after `ahead=0` verification. |
| `codex/rkf-v1` | Removed after PR #20 merged. |
| `codex/rkf-phase1-schema-gate` | Removed after PR #21 merged. |

### Patch-equivalent historical branches removed in this audit

These branches were not ancestors of `main`, but GitHub's live compare returned
zero changed files for each one. Their historical commits remain in Git history.

| Branch | Behind | Ahead | Net files | Result |
|---|---:|---:|---:|---|
| `codex-rkf-clean-framework` | 39 | 1 | 0 | Deleted 2026-07-15. |
| `codex/rkf-emergent-pattern-agents` | 30 | 1 | 0 | Deleted 2026-07-15. |
| `codex/rkf-feature-inventory` | 35 | 1 | 0 | Deleted 2026-07-15. |
| `codex/rkf-l0-l3-world-context` | 33 | 1 | 0 | Deleted 2026-07-15. |
| `codex/rkf-maintenance-improvements` | 35 | 2 | 0 | Deleted 2026-07-15. |
| `codex/rkf-priority-evolve` | 32 | 1 | 0 | Deleted 2026-07-15. |
| `codex/rkf-reading-maturity` | 34 | 1 | 0 | Deleted 2026-07-15. |
| `codex/rkf-reconcile-challenge-bitemporal` | 31 | 1 | 0 | Deleted 2026-07-15. |
| `codex/rkf-shared-wiki-governance` | 37 | 1 | 0 | Deleted 2026-07-15. |

## Retained remote branch

| Branch | Behind | Ahead | Net files | Retention reason |
|---|---:|---:|---:|---|
| `codex-rkf-external-sandbox-workflow` | 41 | 2 | 10 | Contains real unmerged external-sandbox workflow changes; requires a separate product decision. |

After deletion, the live remote branch list contained only `main` and the
retained external-sandbox branch. The v1.1 completion branch is created and
removed through its release pull request, not treated as historical debt.

## Local hygiene

Remote tracking refs were pruned. Two stale worktree registrations whose
gitdir targets no longer existed were pruned, then 15 local historical branches
were removed with safe `git branch -d` checks. No branch required force
deletion. Local `main`, the active release branch, and the unmerged
external-sandbox branch were retained.

The GitHub connector still does not expose the repository's
`delete_branch_on_merge` setting, and the local `gh` token is invalid. Release
cleanup therefore verifies the live branch list and deletes the completion
branch explicitly if GitHub does not remove it automatically.
