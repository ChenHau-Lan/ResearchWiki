# Third-Party Source Policy

ResearchWiki is public-safe by default. It may cite and adapt ideas from other
projects, but vendoring is license-gated.

## Inspiration Sources

- Karpathy LLM Wiki gist: conceptual source for compounding, persistent
  Markdown knowledge, and LLM-readable context.
- Imbad0202 Academic Research Skills: inspiration for skill/mode routing,
  agent contracts, gates, mode registries, and integrity checks.
- Oh My Paper: inspiration for literature-survey memory and paper discovery
  ergonomics.
- lucasastorian/llmwiki: reference implementation family for LLM Wiki repo
  organization.

## Vendoring Rules

- MIT, Apache-2.0, BSD, or similarly permissive code may be vendored only after
  preserving license headers and updating notices.
- CC BY-NC, research-only, unknown-license, or mixed-license content should be
  treated as inspiration unless the repository license strategy explicitly
  supports the restriction.
- Private PDFs, article full text, screenshots from authenticated publisher
  sessions, local paths, DOI-heavy private queues, and Codex logs must not be
  vendored into the public repo.

## Current Decision

This bootstrap adapts architecture patterns instead of copying ARS content
wholesale. Future vendoring should add the exact upstream commit, license, files
included, and reason for inclusion.
