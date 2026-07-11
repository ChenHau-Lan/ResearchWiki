# PROJECT_MEMORY

Last updated: 2026-07-10

## Project Summary

- Project: Research Knowledge Framework (RKF)
- Mode: research-engineering hybrid
- Repo role: framework code, prompts, docs, tests, and examples for governed
  research memory
- Public baseline: `v1.0.0`
- Active workspace data: external shared `wiki/` and `raw/` roots configured in
  `rkf.workspace.toml`
- Primary audience: the user, future Codex agents, and research workflows that
  need source-aware long-term memory without turning candidate material into
  stable evidence

## Current State

- RKF v1 baseline is active with governed paper, synthesis, topic, hot-query,
  world-context, reading-ledger, inbox-capture, and public-safety flows.
- The repository root does not necessarily store the live `knowledge/` tree.
  Resolve operational wiki state through `rkf.workspace.toml` and the configured
  `wiki_root`.
- `hot.md` is the preferred public-safe demand summary when present in the live
  wiki root.
- The repo contains `docs/LITERATURE_MATRIX.md` and `docs/AI_USE_LOG.md`; use
  them for public-safe literature synthesis notes and AI-use/disclosure traces.
- README files are the public front door; `MODE_REGISTRY.md` is the active mode
  and write-boundary reference; `docs/FEATURES_AND_COMMANDS.zh-TW.md` is now the
  Codex app workflow and capability map.

## Durable Decisions

- RKF 1.1 Phase 1 uses a session-owned `RKFActionRuntime`. Every new Codex task
  starts OFF; only explicit `rkf.activate` can enable that task after a
  read-only storage/writer preflight. `rkf.deactivate` returns it to OFF, and a
  project marker never persists activation.
- `query.search` is the deterministic retrieval-first entry point.
  `capture.route` classifies and deduplicates cross-project material, then
  preserves an immutable operational event before any derived projection.
- Shared-machine writes use an event-first, single-writer contract. The
  registered maintenance writer may project events into inbox/hot/wiki views;
  other machines queue events or remain read-only. Every Phase 1 capture keeps
  `Promotion: none`. Writer maintenance uses `capture.project_pending` and
  per-event/per-target checkpoints so queued or partially completed projections
  can be retried without duplicating completed targets.
- Paper pages remain centered on the paper itself. Project/manuscript extension
  questions and the user's broader research directions must be routed to inbox,
  question, topic, or synthesis layers instead of shifting the paper page's
  center of gravity.

- RKF treats evidence as an upgrade boundary, not an entry gate. Paper drafts
  can start from metadata, abstract, partial full text, publisher HTML, or a
  user-provided PDF.
- The current RKF interaction model is Codex app-only for users. Users work
  through natural language in Codex, while Markdown pages remain durable
  artifacts. New integrations should use `rkf.actions` structured requests.
  The existing legacy CLI is an internal shim for Codex agents, tests,
  validation, indexing, graph export, and maintenance, not a user-facing
  control surface.
- `rkf.actions` is the Codex app-facing runtime boundary. It covers
  `inbox.capture`, `hot.record`, report/read actions (`world.render`,
  `paper.queue`, `lint.run`, `graph.export`, `index.generate`,
  `codex_handoff.generate`), and the read-only `stats.snapshot` health report.
  The legacy CLI delegates shared report paths to these actions where practical
  so Codex app and maintenance behavior do not drift.
- Graph traversal is action-first and read-only: `graph.neighbors`,
  `graph.paths`, and `graph.page_context` use the in-memory
  `build_research_graph(ws)` helper. They do not write
  `graph/research_graph.json`; `graph.export` remains the explicit generated
  graph file route.
- Mixed ChatGPT/web/project-note capture should use `knowledge/inbox/` first.
  DOI injection is guarded: create/update source identity and paper backlinks
  only, while preserving source-grounded notes, reader ideas, and AI/agent notes
  as separate inbox sections until review.
- RKF auto-connect is a global personal skill plus a small request-only
  repo-side helper. Its Active/Aggressive classifier runs only after explicit
  session activation; it cannot persist ACTIVE state or bypass runtime guards.
- v1 and v2 project markers mean available, never active. The installed global
  skill must not call the legacy CLI for writes.
- The repo-side `tools/rkf_auto_connect.py` helper builds `rkf.activate`,
  `query.search`, and `capture.route` request payloads. Execution requires the
  same live session-owned runtime; invoking the helper alone remains OFF.
- Codex handoff/bootstrap prompts should request RKF app workflows, structured
  actions, or proposals. They should not instruct users or handoff agents to
  operate RKF through shell commands.
- Legacy handoff naming has been retired. Use `codex-handoff` for hot
  origins, `prompt codex-handoff` for internal context capsule generation,
  `prompts/codex_handoff_context.md` for generated local handoff context, and
  `prompts/codex_handoff_bootstrap.*.md` for committed bootstrap templates.
- Redundant runtime aliases were removed from the internal shim. Use `world`,
  `graph`, and `emerge` as the canonical routes.
- Connected projects may add a project-local `RKF/` bridge folder with
  `README.md`, `hot.md`, `memory.md`, and `captures.md` to speed future agent
  retrieval. Treat that folder as an operational index only, not a second RKF
  database or stable evidence layer.
- Paper pages must keep source-grounded literature notes, reader interpretation,
  AI/agent notes, questions/feedback, and claim-promotion candidates visibly
  separate.
- The 2026-06-22 open-source template scan found useful patterns in Quartz,
  Dendron, Foam, and Logseq: keep local-first Markdown, templates, graph aids,
  and live/test data separation, but do not add an external PKM runtime now.
- Candidates, discovery runs, ARS reports, hot-query lines, and route notes are
  proposals or operational signals until supported by locator-backed evidence,
  existing supported wiki pages, or strong human feedback. Explicit blockers
  keep candidates blocked until reviewed.
- Durable public knowledge must not contain PDFs, article text, private Drive
  paths, browser captures, local secrets, or private runtime state.
- `state/reading/` is operational memory; it can record public-safe questions,
  answers, corrections, annotations, trust changes, and blockers, but it does
  not automatically promote claims.
- `fulltext_routes/*.md` are route/evidence notes, not public-safe full-text
  artifacts.
- Use `evolve` for low-risk direct updates to existing pages when an
  `AI Integration Note` and conservative maturity state are appropriate.
- Use `reconcile`, `challenge`, and `emerge` as critique or low-maturity
  synthesis paths, not as silent trust upgrades.

## Personalized Workflow Preferences

- If the user writes in Chinese, reply in Traditional Chinese while preserving
  RKF field names, mode names, and skill names in English where useful.
- For recurring RKF daily digests, check the live/shared `hot.md` first. If no
  useful `hot.md` exists, fall back to recently modified or current-goal pages
  under `knowledge/topics`, `knowledge/questions`, `knowledge/concepts`,
  `knowledge/papers`, `knowledge/synthesis`, and `examples/*/knowledge`.
- In digest wording, separate demand signals, context, and evidence-backed
  claims. Do not upgrade candidates, ARS reports, or route notes into evidence.
- Gmail delivery is the only approved delivery path for the RKF daily digest.
  Verify the connected Gmail profile live before sending. If Gmail permissions,
  connector startup, or sending fails, report the blocker and do not reroute to
  Slack or another channel.
- Daily digest messages should preserve these exact framing lines:
  - `**[Codex Research Daily Bot]**`
  - `由 Codex 自動整理 / Generated by Codex automation`
  - `Source: RKF <project-root>`
  Replace `<project-root>` with the active workspace root only in the outgoing
  email body when explicitly needed. Do not store private absolute paths in
  committed docs.
- Daily digests should be brief, bilingual Traditional Chinese + English,
  public-safe, email-only, attachment-free, and should not create new wiki pages
  unless explicitly requested.
- When no public-safe full-text Markdown exists, cite safe wiki/read-note pages
  instead of article text or private artifacts.

## Verified Validation

Use the narrowest validation set that matches the change. Commands observed or
documented as valid for this repo include:

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/rk.py lint --mode all
python3 tools/rk.py topic lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/public_safety_scan.py
```

For RKF state checks, ask Codex for topic lint, all lint, paper queue, world
context, hot demand recording, or hot refresh through the app/internal runtime.
There is no `hot show` workflow; inspect `hot.md` directly.

## Known Operational Traps

- Trap: searching only the repo-local checkout for live wiki pages can produce a
  false negative. Fix: resolve `wiki_root` from `rkf.workspace.toml` early.
- Trap: treating shared `hot.md` as evidence. Fix: use it as a demand dashboard,
  then inspect topic/question/synthesis/paper pages for support and maturity.
- Trap: treating `fulltext_routes/*.md` as durable article text. Fix: treat them
  as route notes and link safe wiki/read-note pages instead.
- Trap: assuming Gmail can be switched or replaced automatically. Fix: preflight
  the connected account; if unavailable, stop and report the setup blocker.
- Trap: writing generated research summaries straight into stable wiki pages.
  Fix: save as proposal, reading feedback, low-maturity synthesis, or
  AI-integrated update with explicit maturity and blockers.
- Trap: copying an entire ChatGPT transcript or web article into durable wiki.
  Fix: save only a short public-safe excerpt/summary plus provenance in
  `knowledge/inbox/`; route DOI metadata through guarded source/paper backlink
  injection.
- Trap: making every project duplicate RKF routing rules. Fix: use the global
  `rkf-auto-connect` skill and keep project markers small and public-safe.
- Trap: assuming an enabled marker or a previous task keeps RKF active. Fix:
  every new task starts OFF and requires the user to say `啟動 RKF`.
- Trap: letting multiple Drive-synced computers project the same capture into
  wiki files. Fix: keep immutable events as source of truth and allow only the
  registered maintenance writer to materialize projections.
- Trap: treating a project-local `RKF/hot.md` or `RKF/memory.md` as canonical
  RKF evidence. Fix: keep `RKF/` bridge files pointer-oriented and route
  durable capture through the central RKF Codex app/action flow.

## Documentation Map

- `AGENTS.md`: repo-specific agent rules, RKF routing, personalized workflow
  rules, safety boundaries, and validation commands.
- `README.md` and `README.zh-TW.md`: public project overview and quick start.
- `MODE_REGISTRY.md`: modes, write boundaries, oversight levels, and bridge
  protocol.
- `docs/ARCHITECTURE.md`: framework architecture.
- `docs/FEATURES_AND_COMMANDS.zh-TW.md`: current Codex app workflow and
  capability map.
- `docs/LITERATURE_MATRIX.md`: concise public-safe cross-paper synthesis notes.
- `docs/AI_USE_LOG.md`: AI-assisted research/digest/writing disclosure log.
- `docs/references/ars_bridge_protocol.md`: ARS-to-RKF handoff contract.
- `skills/*/SKILL.md`: local RKF skill definitions.
- `examples/taiwan-atmospheric-experiment/`: stable fallback/example surface
  when the live wiki has no useful `hot.md`.

## Change Discipline

- Keep changes scoped to the requested RKF mode or object boundary.
- Do not overwrite existing knowledge objects unless an update path is explicit.
- Keep Chinese and English README files aligned at the capability level.
- Update `CHANGELOG.md` for public feature changes, schema changes, command
  changes, or safety contract changes.
- Update this file when a reusable command, workflow rule, failure mode, or
  storage decision is learned.
- Update `docs/AI_USE_LOG.md` when AI assistance produces research-facing
  summaries, writing, synthesis, analysis, or deliverables that may need later
  disclosure.

## Next Steps

- Keep automation summaries anchored to the live/shared wiki state rather than
  repo-local file presence.
- Keep validating that digest and synthesis outputs do not blur proposals,
  route notes, and evidence-backed claims.
- Expand tests and docs together when adding new Codex app workflows, RKF action
  surfaces, or RKF modes.
