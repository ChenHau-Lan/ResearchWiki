# Changelog

## Unreleased

- Add RKF 1.1 Phase 1 activation and closed-loop foundations: every new Codex
  task starts OFF; `rkf.activate` performs read-only preflight;
  `query.search` provides deterministic maturity-aware retrieval;
  `capture.route` records deduplicated immutable events; `rkf.deactivate`
  closes the session. Shared projections use a designated writer with
  `capture.project_pending` checkpoints, and every capture receipt states
  `Promotion: none`.
- Keep project/workspace TOML parsing compatible with Python 3.9 by preserving
  top-level values and typed booleans in the standard-library fallback parser.

- Reframe RKF around active paper reading maturity: early paper drafts can begin
  from metadata, abstracts, partial full text, or user-provided PDFs, while
  stable claims and trusted synthesis stay gated by locators, human feedback,
  or existing governed sources; explicit blockers keep unresolved claims from
  promotion.
- Add reading maturity fields for paper and synthesis objects plus a
  public-safe `state/reading/` ledger contract.
- Add paper queue, feedback, next-item, and nudge CLI flows for registered
  papers that need user PDF, human review, or synthesis review.
- Add RKF inbox capture for ChatGPT/web/project clips with guarded DOI injection
  that creates or backlinks source/paper pages without promoting claims.
- Add RKF auto-connect design and helper plan for cross-project
  Active/Aggressive capture into RKF inbox and hot-query layers.
- Add project-local `RKF/` bridge folder scaffolding for connected projects,
  with public-safe `README.md`, `hot.md`, `memory.md`, and `captures.md`
  templates that remain operational indexes rather than evidence.
- Soft-migrate acquisition: user-provided PDFs update full-text state directly,
  while legacy checkpoint records remain compatible.
- Add the hot-query layer: `hot.md` as a single public-safe retrieval file with
  CLI recording and refresh commands.
- Route RKF runtime paths through configured `storage.wiki_root` so CLI query,
  lint, graph, index, and log operations use the shared wiki database when one
  is configured.
- Add generated `index.md` and append-only `log.md` support for compact LLM
  retrieval and cross-session continuity.
- Add evidence-tier metadata for saved objects and generated index entries.
- Refuse accidental knowledge-object overwrites unless an update is explicit.
- Add real graph-link and ARS-handoff lint checks.
- Add proposal-first propagation review for affected knowledge pages.
- Add compact workspace status/world output for session bootstrap.
- Add a current feature and command inventory with local cleanup candidates.
- Add public wiki safety linting for knowledge, governance, and graph layers.
- Keep release history in this changelog instead of README or manual prose.

## v1.0.0

- Establish the public RKF baseline: LLM Wiki-based research memory model, five
  active RKF skills, topic review, evidence gates, ARS bridge protocol,
  shared-database experiment, bilingual manuals, page templates, and the Taiwan
  atmospheric experiment example.
