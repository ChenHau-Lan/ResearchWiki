# Changelog

## Unreleased

- Add the hot-query layer: `hot.md` as a single public-safe retrieval file with
  CLI recording and refresh commands.
- Route RKF runtime paths through configured `storage.wiki_root` so CLI query,
  lint, graph, index, and log operations use the shared wiki database when one
  is configured.
- Add generated `index.md` and append-only `log.md` support for compact LLM
  retrieval and cross-session continuity.
- Add evidence-tier metadata for saved objects and generated index entries.
- Add public wiki safety linting for knowledge, governance, and graph layers.
- Keep release history in this changelog instead of README or manual prose.

## v1.0.0

- Establish the public RKF baseline: LLM Wiki-based research memory model, five
  active RKF skills, topic review, evidence gates, ARS bridge protocol,
  shared-database experiment, bilingual manuals, page templates, and the Taiwan
  atmospheric experiment example.
