# Changelog

## Unreleased

- Reframe RKF around active paper reading maturity: early paper drafts can begin
  from metadata, abstracts, partial full text, or user-provided PDFs, while
  stable claims and trusted synthesis stay gated by locators, human feedback,
  existing governed sources, or explicit blockers.
- Add reading maturity fields for paper and synthesis objects plus a
  public-safe `state/reading/` ledger contract.
- Add paper queue, feedback, next-item, and nudge CLI flows for registered
  papers that need user PDF, human review, or synthesis review.
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
