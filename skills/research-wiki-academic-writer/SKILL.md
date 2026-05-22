---
name: research-wiki-academic-writer
description: Use this project-local skill when drafting papers, literature reviews, proposals, or research reports from the Research Wiki. It prioritizes verified wiki evidence, raw/full_text_index, references.bib integrity, and clear separation between literature, synthesis, seminar context, and project synthesis.
license: MIT
---

# Research Wiki Academic Writer

Use this skill to write academic documents from this repository without fabricating citations or mixing evidence tiers.

Canonical command-independent rules live in `core/skills/research-wiki-academic-writer/SKILL.md`, `core/principles.md`, and `core/data_contract.md`. Treat those files as authoritative if this project-local wrapper drifts.

## Non-Negotiables

- Do not fabricate citations.
- Verify title, authors, venue/year, DOI or canonical URL before citing.
- Use `references.bib` as the formal citation registry.
- Resolve existing evidence through `raw/full_text_index.json` before re-searching.
- Read `wiki/synthesis/` first for research judgment, then `wiki/literature/`, then `wiki/seminars/` as lower-priority context.
- Use `wiki/project_synthesis/` and `wiki/meetings/` only for project history, decisions, and work planning.

## Evidence Priority

1. Reviewed synthesis backed by full-read literature.
2. Full-read paper pages linked to verified `raw/full_text/<paper_file_key>.md`.
3. Abstract-only paper pages, clearly labeled as limited.
4. Seminar notes as talk context only.
5. Project synthesis / meetings for decision history, not peer-reviewed claims.

## Workflow

1. Read `AGENTS.md`, `wiki/index.md`, and relevant synthesis pages.
2. Resolve DOI/citation keys in `raw/full_text_index.json`.
3. Check paper pages in `wiki/literature/`.
4. Use `references.bib` only after a paper is citation-ready.
5. Draft with explicit claim-to-evidence mapping.
6. If evidence is weak, write it as a hypothesis or limitation.

## Output Guidance

- Literature reviews should organize by themes and evidence tiers.
- Research papers should keep IMRaD structure when appropriate.
- Proposals should separate known evidence, open questions, and planned work.
- Do not copy full paper text into wiki pages or manuscripts.

## Paper Page Generation

When creating or updating `wiki/literature/` paper pages:

- Write a concise single-paper reading note, not an operations report.
- Include only this paper's content plus minimal source pointers.
- Do not copy template field guides, placeholder text, empty fields, generic Zotero boilerplate, user-trigger boilerplate, or unnecessary maintenance sections.
- Keep metadata short: title, authors, venue/year, DOI, reading status, full text path, and PDF path if available.
- Before marking a page `full-read`, reject `raw/full_text/` that still has
  obvious PDF extraction damage: broken paragraphs, repeated page headers or
  footers, orphaned equation fragments, missing section headings, or missing
  figure/table captions. Return it to full-text QC instead.
- If `table_quality` is `partial` or `poor`, do not reuse numeric table values
  in paper pages, synthesis, or reports unless the PDF, HTML/XML table, or
  supplement has been checked. Record the limitation plainly.
- Keep cross-paper interpretation out of the paper page unless it is explicitly labeled and necessary; prefer `wiki/synthesis/` for that.
- Preserve `## Graph Links` so Obsidian can connect topics, subtopics, literature, synthesis, seminars, and projects.

## Repository Paths

- Full-text dispatch: `raw/full_text_index.json`
- Readable full text: `raw/full_text/<paper_file_key>.md`
- Paper pages: `wiki/literature/`
- Cross-paper synthesis: `wiki/synthesis/`
- Project synthesis: `wiki/project_synthesis/`
- Seminar context: `wiki/seminars/`
