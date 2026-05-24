# Third-Party Source Policy

RKF is public-safe by default. It may cite and adapt ideas from other projects,
but vendoring is license-gated and should never smuggle private research state
into the repository.

## Inspiration Sources

- Karpathy LLM Wiki gist: conceptual source for compounding, persistent
  Markdown knowledge, and LLM-readable context.
- Imbad0202 Academic Research Skills: inspiration for skill/mode routing,
  agent contracts, gates, mode registries, and integrity checks.
- Oh My Paper: inspiration for literature-survey memory and paper discovery
  ergonomics.
- lucasastorian/llmwiki: reference implementation family for LLM Wiki repo
  organization.

## Video Handling

The YouTube LLM Wiki explanation is treated as an idea source for original
briefs, not as a source for unauthorized full transcript reproduction. If the
user provides authorized captions, quote only short excerpts and build RKF docs
from paraphrase and synthesis.

## Vendoring Rules

- MIT, Apache-2.0, BSD, or similarly permissive code may be vendored only after
  preserving license headers and updating notices.
- CC BY-NC, research-only, unknown-license, or mixed-license content should be
  treated as inspiration unless the repository license strategy explicitly
  supports that restriction.
- Private PDFs, article text, screenshots from authenticated publisher
  sessions, local paths, DOI-heavy private queues, and Codex logs must not be
  vendored into the public repo.

## Policy

RKF adapts architecture patterns instead of copying ARS content wholesale. Any
vendored file needs the exact upstream commit, license, files included, and
reason for inclusion.
