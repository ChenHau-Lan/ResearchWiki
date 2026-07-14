# Research Knowledge Framework Agent Guide

RKF is a research-engineering project that turns papers into locator-backed,
human-reviewed research knowledge. Read `docs/PROJECT_MEMORY.md`, `README.md`,
`MODE_REGISTRY.md`, and `docs/FEATURES_AND_COMMANDS.zh-TW.md` before non-trivial
work.

## v1 Product Contract

The only user-facing research workflows are:

- Add → `workflow.add`
- Ask → `workflow.ask`
- Read → `workflow.read`
- Compare & Synthesize → `workflow.compare-synthesize`
- Review → `workflow.review`

Cross-project access uses preview/apply `connect-project`, then task-scoped
`rkf.activate`, `connect.validate`, `rkf.status`, and `rkf.deactivate`.
Every new task starts OFF. A marker means available, never permanently active.

Graph/index/world/handoff, inbox/source/discovery helpers, and synthesis review
passes are internal projections or helpers. Do not present them as additional
product modes. The compatibility/removal inventory is
`docs/V1_SCOPE_INVENTORY.md`.

## Evidence Rules

- Canonical path: Paper → locator-backed Evidence → human-reviewed Claim →
  Synthesis.
- Paper state uses `access_state` and `review_state` from
  `schemas/rkf_v1.schema.json`.
- Evidence requires a page, section, figure, table, or paragraph locator.
- Supported/disputed/verified claims require Evidence; verified claims require
  at least one human-verified Evidence card.
- Candidate metadata, retrieval similarity, provider success, ARS reports and
  LLM output cannot promote trust by themselves.
- Paper drafts may start early from metadata/abstract/partial text, but their
  maturity must remain explicit.

## Cross-project Lineage

- New v2 markers contain a random stable `project_id`, never an absolute path.
- Each activation gets an `activation_id`; each action gets an idempotent,
  append-only ActionEvent.
- Raw prompts, secrets, PDFs, article text, private Drive paths and local paths
  are excluded from lineage and public output.
- Review must support project/activation timeline reconstruction and object
  origin lookup.

## Providers

Optional full-text, appraisal and semantic retrieval adapters implement the
contracts in `rkf/providers.py`. Deterministic retrieval remains the default.
Do not add browser login, institutional credentials, heavy semantic services or
the full `paper-fetch` acquisition engine to core v1; that is vNext scope.

## Public Site

The public site is a synthetic/public-safe guided demo. It may show locator
coverage, human-verified evidence, verified/disputed claims and unresolved
gaps. It must not expose project activity, writer/storage/doctor state, raw
candidate/run counts, graph vanity metrics, paper identity, raw prompts,
private paths, PDFs or article text.

## Documentation

- Long-term decisions and verified commands → `docs/PROJECT_MEMORY.md`
- Literature synthesis → `docs/LITERATURE_MATRIX.md`
- AI research/writing assistance → `docs/AI_USE_LOG.md`
- Release history → `CHANGELOG.md`

Do not put secrets, tokens, private paths or unpublished article text in these
files.

## Validation

Use the smallest relevant checks, then for broad framework changes run:

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/public_safety_scan.py
```

Also inspect the final diff. Do not commit or push unless the user asks.
