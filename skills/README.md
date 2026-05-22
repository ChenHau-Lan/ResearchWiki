# Project-Local Skills

These skills are project-local references for Research Wiki. They are not automatically installed as global Codex skills.

Use them when optimizing this repository's literature ingest, academic writing, full-text acquisition, and evidence workflows.

Canonical command-independent skill contracts live in `core/skills/`. The files
in this directory are project-local discoverability wrappers and should stay
aligned with the core versions.

## Skills

- `research-wiki-academic-writer`: write research documents from this wiki without fabricating citations.
- `research-wiki-fulltext-acquisition`: acquire DOI PDFs and verify authorized full text for DOI-driven paper intake.

## Notes

- Keep these skills aligned with `core/skills/` and `AGENTS.md`.
- Use `raw/full_text_index.*`, not legacy index names.
- Put DOI PDFs in `raw/doi_pdf/`.
- Put full text in `raw/full_text/`.
- When shell download is blocked but the article/PDF is visible in the user's browser, use authorized browser-session PDF download before asking for manual upload.
- Put paper notes in `wiki/literature/`.
- Put cross-paper judgment in `wiki/synthesis/`.
- Put project evolution in `wiki/project_synthesis/`.
