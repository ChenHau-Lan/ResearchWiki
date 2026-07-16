# RKF v1 Researcher Manual

RKF is an LLM Wiki-based research knowledge framework operated through natural
language in Codex. Its core path is Paper → source context → FindingDraft →
exact-locator Evidence → human-reviewed Claim → Synthesis. Routine users do
not need to operate action JSON or the legacy CLI.

## One-time setup and per-project connection

Initialize the central checkout once:

```bash
python3 tools/bootstrap_rkf.py --install-connector
python3 tools/bootstrap_rkf.py --apply --install-connector
python3 tools/check_install.py --profile codex --strict --json
```

For each research project, preview and then apply the connection:

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

This creates only a v2 `.rkf-connect.toml` and a lightweight `RKF/` bridge.
`available = true` means RKF can be used; it never means a task is permanently
active.

## Natural-language flow for each task

Open Codex in the research project folder and say:

> Activate RKF and validate this project. From this conversation, extract the
> research question and search terms. Ask RKF first, then search public
> scholarly sources if needed. Show me candidate papers; after I confirm them,
> Add their DOI or URL and a short source-aware note. Do not save the whole
> conversation. Promotion: none.

This routes the work through:

1. `rkf.activate` and `connect.validate` for this task and project only.
2. `workflow.ask` to check existing RKF knowledge first.
3. Public scholarly search only when requested and available; results remain
   candidates.
4. `workflow.add` for user-selected DOI/URL metadata, search terms, and a short
   note.

The whole conversation, raw prompts, PDFs, article text, private paths, and
secrets are excluded from lineage and public knowledge. Model summaries and
search results do not become Evidence by themselves.

## See which projects have open activation records

Say:

> Show RKF status. List project names with open activation records, mark this
> task’s project, and include project IDs. Do not show absolute paths.

`rkf.status` separates:

- This task: `mode`, `project_name`, `project_id`, and `activation_id`.
- Cross-task summary: `active_project_count`, `open_activation_count`, each
  project’s mode, open-task count, and latest activation time.

For local privacy, RKF reports marker project names and stable `project_id`
values, not full folder paths. The list comes from append-only lineage. If a
Codex task stops without `rkf.deactivate`, its activation can remain open until
a later closure or expiry event is recorded. Review can inspect that timeline;
the list is not an operating-system process monitor.

When finished, say:

> Deactivate RKF.

## Five research workflows

These are the Common Workflows in the Codex app:

- Add captures a DOI, URL, PDF pointer, note, or selected paper with
  `Promotion: none`.
- Ask retrieves governed source context deterministically and labels
  context-only versus evidence-ready answers; claim support requires exact
  Evidence.
- Read can capture a missing/coarse/exact FindingDraft, promote only an exact
  finding to Evidence, or use the compatible direct exact-Evidence route.
- Compare & Synthesize records Claim/Synthesis agreement, opposition, and gaps.
- Review shows research gaps, pending checks, next reading actions, and project
  lineage.

The academic-research-suite may search, reason, write, or review, but its output
remains a proposal until RKF evidence rules are satisfied.

## Paper Maturity and save boundary

`access_state` is `metadata | abstract | partial | fulltext`.
`review_state` is `unread | skimmed | read | annotated | reproduced`.
Legacy reading labels are normalized conservatively and unknown values become
data-quality findings. When authorized full text is unavailable, use the
explicit `needs-user-pdf` blocker; never infer that a paper was read from
metadata alone.

Candidates, context-only results, FindingDrafts, and LLM output are not
Evidence. Verified Claims require human-verified, locator-backed Evidence.
Ask may show governed context without a locator, but must mark it not
claim-ready.

## Troubleshooting

- Status is OFF: explicitly say “Activate RKF” in the current task.
- A project is absent: connect it first, then activate RKF in that task.
- A project stays open: a prior task may not have deactivated; inspect the
  activation timeline through Review.
- A found paper was not saved: select the candidate before routing it to Add.
- Only metadata exists: do not describe the paper as read; update access and
  review state only after obtaining authorized source material.
