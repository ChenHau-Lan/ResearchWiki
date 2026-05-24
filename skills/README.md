# Project-Local Skills

These skills are project-local references for Research Wiki. They are not automatically installed as global Codex skills.

Use them when optimizing this repository's literature ingest, academic writing,
full-text acquisition, evidence workflows, pipeline skills, and mode handoffs.

Canonical command-independent skill contracts live in `core/skills/`. The files
in this directory are project-local discoverability wrappers and should stay
aligned with the core versions.

## Skill-First Pipeline

- `source-intake`: source queue, dashboard refresh, PDF scan, legal source
  resolution, and QCed full-text handoff.
- `literature-discovery`: topic/DOI/URL search, legal-source candidates,
  acquisition checkpoints, and approved PDF imports.
- `paper-ingest`: QCed `raw/full_text/` to `wiki/literature/` paper pages.
- `topic-governance`: topic IDs, aliases, scope, default searches, canonical
  pages, and review cadence.
- `knowledge-workbench`: Query, Save, query-to-save, and review queue work.
- `synthesis-research`: fan-out review, thesis review, synthesis discussion,
  and approved cross-page updates.
- `wiki-lint`: structure lint, semantic lint, repair plans, and runtime
  state/graph diagnostics.

## Advanced Compatibility

- `audit-release`: compatibility alias for advanced support reports, issue
  drafting, and release maintenance.

## Compatibility Skills

- `research-wiki-academic-writer`: write research documents from this wiki
  without fabricating citations.
- `research-wiki-fulltext-acquisition`: acquire DOI PDFs and verify authorized
  full text for DOI-driven paper intake.

## Notes

- Keep these skills aligned with `core/skills/` and `AGENTS.md`.
- Use `raw/full_text_index.*`, not legacy index names.
- Put DOI PDFs in `raw/doi_pdf/`.
- Put full text in `raw/full_text/`.
- When shell download is blocked but the article/PDF is visible in the user's browser, use authorized browser-session PDF download before asking for manual upload.
- Put paper notes in `wiki/literature/`.
- Put cross-paper judgment in `wiki/synthesis/`.
- Put project evolution in `wiki/project_synthesis/`.
