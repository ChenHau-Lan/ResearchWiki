# Research Wiki Principles

## Purpose

Research Wiki is a paper-source-first academic research database. It accepts
DOIs, DOI URLs, article URLs, PDF URLs, and local PDFs as source pointers,
resolves them into evidence, turns verified full text into concise research
notes, and supports synthesis without fabricating citations or mixing evidence
tiers. DOI remains the preferred canonical identity when available.
The durable purpose statement lives in `core/purpose.md`; user-facing purpose
navigation lives in `wiki/purpose.md`.

Research Wiki v2 treats the database as a skill-first research knowledge
runtime, not only as a paper-ingest pipeline. The runtime is operated through
pipeline skills and modes:

- `source-intake`: source queue, dashboard refresh, PDF scan, legal source
  resolution, and QCed full-text handoff.
- `literature-discovery`: topic/DOI/URL search, candidate ranking, legal-source
  discovery, acquisition checkpoints, and screenshot-assisted source review.
- `paper-ingest`: QCed full text to single-paper wiki pages.
- `topic-governance`: topic IDs, scope, aliases, search strings, canonical
  pages, and review cadence.
- `knowledge-workbench`: Query, Save, query-to-save, and review queue work.
- `synthesis-research`: fan-out, thesis review, synthesis discussion, and
  cross-page research.
- `wiki-lint`: structure lint, semantic lint, repair plans, and runtime
  graph/state diagnostics. `audit-release` remains an advanced compatibility
  alias for support and release maintenance.

Query, Save, Lint, and Research remain conceptual actions, but they are now
mode-level permissions inside these skills.

## Evidence Chain

- `raw/` is evidence. It stores paper-source pointers, DOI dashboards, PDFs,
  extraction staging, QCed full text, indexes, and user-provided source files.
- `wiki/` is knowledge. It stores curated paper notes, synthesis, meetings,
  project synthesis, seminars, and promoted concept pages.
- `maintenance/` is operations. It stores repair plans, logs, release checks,
  support reports, test reports, review queues, runtime state, graph exports,
  and research/thesis review runs.
- Dashboard rows are not evidence. Real evidence is the presence of files in
  `raw/doi_pdf/`, `raw/staging/`, `raw/full_text/`, `raw/files/`,
  `raw/full_text_index.*`, and curated pages in `wiki/`.
- `researchwiki.config.toml` is local machine configuration and must stay out
  of Git. Public Git keeps only `researchwiki.config.example.toml`.

## Skill Runtime Actions

- `knowledge-workbench/query` is read-only. It may answer from `wiki/`,
  `raw/full_text_index.*`, and verified raw evidence, but it must not update
  wiki pages, dashboards, review queues, or logs.
- `knowledge-workbench/save` is an explicit transition from conversation to
  durable knowledge. A Save mode must choose the target layer before writing:
  paper fact, synthesis, concept, meeting/project history, review queue, or
  maintenance log.
- `knowledge-workbench/query-to-save` converts a useful Query result into a
  Save proposal, then writes only after the target layer is explicit.
- `knowledge-workbench/review-queue` writes uncertain or low-confidence items
  only to `maintenance/review_queue.md`.
- `wiki-lint` has two layers. Deterministic structure lint checks frontmatter,
  links, indexes, paths, Graph Links, orphans, and dashboard/index drift.
  Semantic lint checks evidence tiers, stale claims, contradictions,
  confidence, counter-evidence, supersession candidates, and possible
  confirmation bias. Lint should also suggest source leads or review queue
  items when the wiki lacks enough evidence.
- Research is not a free-form write action. It gathers evidence, compares
  positions, identifies gaps, and produces either a source-backed wiki update
  or a review-queue item.

## Token Discipline

- Use local tools for mechanical work: scanning, path checks, indexes, status
  refreshes, and diagnostics.
- Use Codex or another LLM for interpretation: source-access judgment,
  full-text reflow/QC, paper-note writing, synthesis, and project discussion.
- A command or UI should not spend LLM time on tasks that deterministic local
  tooling can do safely.

## Knowledge Growth

- A paper ingest creates or updates the single-paper page only.
- A source may influence multiple pages, but that fan-out must first be recorded
  as a deterministic candidate and then a reviewable proposal unless the user
  explicitly starts an approved Save or fan-out action.
- Cross-paper interpretation belongs in `wiki/synthesis/`, not in paper pages.
- Repeated methods, mechanisms, datasets, instruments, models, or variables may
  be promoted to concept pages when they connect multiple sources.
- Uncertain, conflicting, low-confidence, or potentially superseding claims go
  to the review queue before becoming stable knowledge.
- `wiki/overview.md` maps stable knowledge areas. `wiki/hot.md` maps active
  questions. Neither page should settle claims without linking to evidence or
  review state.
- Topic pages govern retrieval scope. Question pages preserve uncertainty until
  evidence and counter-evidence are strong enough for synthesis.

## Confirmation-Bias Controls

- LLM-generated answers are not evidence. They become durable only after Save
  chooses a target layer and cites source-backed evidence.
- Synthesis claims should record evidence tier, confidence, evidence links, and
  counter-evidence.
- `confidence: high` requires more than a single weak source and must not rely
  only on seminar context, abstract-only pages, or unverified full text.
- New evidence should supersede older interpretations explicitly instead of
  silently overwriting them.
- Thesis-style research must include opposing or falsifying evidence before a
  verdict is saved.

## Safety

- Do not automate unauthorized full-text acquisition.
- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Automated PDF acquisition must stop at a human checkpoint before treating a
  candidate file as evidence.
- Do not copy full articles into `wiki/`.
- Repair tools diagnose and plan; they do not delete files automatically.
- Release tooling must not publish private PDFs, full text, local paths, logs,
  or personal research state unless explicitly intended.

## Separation

- Core rules belong in `core/`.
- Command/UI behavior belongs in command scripts and user docs.
- Personal research state belongs on `personal/*` branches or ignored raw data.
- PDFs, article full text, screenshots from authenticated sessions, and local
  Drive paths must not be committed to the public repository.
- When a rule and a command behavior conflict, the core contract wins.
