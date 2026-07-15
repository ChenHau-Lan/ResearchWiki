# v1 Branch Hygiene Audit

Audit date: 2026-07-14
Comparison base: `origin/main@c83d0b7`
Open pull requests: none (verified through the connected GitHub repository)

`behind` is the number of commits present only on `main`; `ahead` is the number
present only on the branch. A branch was eligible for deletion only when
`ahead=0`, no open pull request used it, and it was not a release/default branch.

## Deleted remote branches

| Branch | Before deletion | Reason | Result |
|---|---:|---|---|
| `codex/rkf-observatory` | behind 2, ahead 0 | Fully merged; explicitly named by #19. | Deleted from `origin` on 2026-07-14. |
| `codex/rkf-auto-evolution-docs-cleanup` | behind 25, ahead 0 | Fully merged and not used by an open PR. | Deleted from `origin` on 2026-07-14. |

## Retained remote branches

| Branch | Behind | Ahead | Retention reason |
|---|---:|---:|---|
| `codex-rkf-clean-framework` | 34 | 1 | Contains an unmerged commit; requires manual historical review. |
| `codex-rkf-external-sandbox-workflow` | 36 | 2 | Contains unmerged commits. |
| `codex/rkf-emergent-pattern-agents` | 25 | 1 | Contains an unmerged commit. |
| `codex/rkf-feature-inventory` | 30 | 1 | Contains an unmerged commit. |
| `codex/rkf-l0-l3-world-context` | 28 | 1 | Contains an unmerged commit. |
| `codex/rkf-maintenance-improvements` | 30 | 2 | Contains unmerged commits. |
| `codex/rkf-priority-evolve` | 27 | 1 | Contains an unmerged commit. |
| `codex/rkf-reading-maturity` | 29 | 1 | Contains an unmerged commit. |
| `codex/rkf-reconcile-challenge-bitemporal` | 26 | 1 | Contains an unmerged commit. |
| `codex/rkf-shared-wiki-governance` | 32 | 1 | Contains an unmerged commit. |
| `codex/rkf-v1` | 0 | 1 | Active Phase 0 implementation branch. |

## Automatic post-merge deletion

The connected GitHub app confirms administrative permission, but its repository
mutation surface does not expose the `delete_branch_on_merge` setting. The local
GitHub CLI token is invalid, so the setting could not be changed or verified in
this run. Re-authenticate `gh`, then run and read back:

```bash
gh api --method PATCH repos/ChenHau-Lan/ResearchWiki -f delete_branch_on_merge=true
gh api repos/ChenHau-Lan/ResearchWiki --jq .delete_branch_on_merge
```

This unchecked item must remain open in #19 until the read-back returns `true`.
