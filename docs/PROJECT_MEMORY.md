# PROJECT_MEMORY

Last updated: 2026-07-13

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
- RKF 1.1 Phase 2 now has a local-only `paper.migration.preview` path. It
  checks exact paper-input hashes, transforms only copied pages, writes copied
  migration ledger events/diffs/manifest into ignored `.rkf_private`, and
  reports a stable manifest hash. It never applies a migration to live wiki.
  Any `needs-human-routing` item or strict v1.1 contract error blocks future
  live readiness.
- RKF 1.1 Phase 3 implements but does not auto-run approval-bound live apply
  and rollback. `paper.migration.apply` requires an exact reviewed manifest
  hash, no input drift, a designated writer, and a passing doctor; it creates a
  private raw backup/journal and atomically replaces validated pages/ledgers.
  Partial failures roll back automatically. `paper.migration.rollback` requires
  the matching backup ID and manifest hash. Backup deletion remains a separate
  cleanup approval.
- Paper v1.1 pages use the canonical source/maturity/question/method/findings/
  locators/limitations/paper-question/retrieval-brief/intrinsic-link structure.
  Inbox backlink injection records `inbox_items` plus a reading-ledger event;
  it must not recreate legacy `Questions And Feedback` content in paper pages.
- `connect.doctor` is read-only and path-redacted. It checks root readability,
  writer registry agreement, conflict copies, schema compatibility, stale
  aggregates, and divergent same-identity PDF checksums. A blocker after
  activation downgrades the current runtime to `ACTIVE_READ_ONLY`.
- `views.preview` emits five public-safe Obsidian Base definitions without
  writing. `views.generate` is designated-writer-only and uses expected-
  checksum atomic replacement for `wiki/views/*.base`. Obsidian settings and
  local vault links are intentionally out of the canonical wiki.
- `maintenance.preview` / `maintenance.run` are conservative planning and
  receipt surfaces. They inventory RAW incoming artifacts by checksum and
  preserve `Promotion: none`; no Codex automation is created by them.
- `cleanup.manifest.preview` writes only a local pending manifest. It has no
  delete/archive/apply path and can include paused automation snapshots without
  changing their external scheduler state.
- Portable onboarding uses repo-relative ignored storage by default.
  `Workspace(explicit_root)` takes precedence over `RKF_ROOT`, and relative
  storage handles resolve from that checkout rather than the process cwd.
  `tools/bootstrap_rkf.py` is preview-first, refuses overlaps/nonempty targets/
  symlink config targets, and never overwrites existing configuration.
- Cross-project setup is a bundle: the machine-local connector and the
  version-matched vendored `skills/rkf-auto-connect` skill. Bootstrap creates
  missing files only; `tools/check_install.py --strict` fails if a connector is
  present but the installed global skill differs from this checkout. Bundle
  verification covers both `SKILL.md` and `agents/openai.yaml`; bootstrap
  preflights connector/config parents, symlinks, storage targets, and all
  project-bridge destinations before any write, so malformed setup fails
  without a partial marker or workspace config.
- A connected project opens one task-owned action host with
  `tools.rkf_auto_connect.open_action_runtime(...)` and reuses that same
  `RKFActionRuntime` for activation, retrieval, discovery, dashboard preview,
  and capture. An explicit external project root must have a valid current
  project marker; a connector file alone is not sufficient authorization.
- A clean bootstrap starts with an empty topic registry. The first discovery
  exercise therefore uses an explicit public-safe query; topic-based discovery
  is introduced only after the user has reviewed and registered a topic.
- Public dashboard state is aggregate-only and identity-free. Preview writes
  only under ignored `.rkf_private/dashboard_previews`; local publication
  requires the exact snapshot hash. GitHub Pages deployment has an additional
  fail-closed validator requiring `publication.status=published`; public-safe
  never means publication-approved. Recent demand hotspots and registered
  research areas are separate fields; an empty demand window must not relabel
  topic registry entries as hotspots. A demand event counts as topic-linked
  only when at least one topic ID still exists in the current registry;
  unknown or retired IDs remain untriaged. Storage settings are booleans only,
  and doctor output is reduced to blocker/warning counts. Governed v2 discovery
  aggregates use the same strict run and acceptance loaders as discovery
  actions; deprecated v1 records may contribute only to the explicitly labeled
  `other` / legacy-unclassified count after strict legacy-shape validation.
- `dashboard.review` renders one validated pending preview as a self-contained
  ignored page without modifying `site/`, its source preview, or publication
  state. The fixed review tree uses exact checksums, restrictive permissions,
  noindex metadata, a permanent NOT PUBLISHED banner, and an embedded snapshot
  so `review/index.html` can be opened directly. Preview envelope, timestamp,
  hash prefix, publication state, extra-file, and symlink drift fail closed.
- Provider paper discovery is candidate-only. `discover.preview` performs no
  RKF state write; `discover.record` stores one immutable exact-hash v2 run;
  `discover.accept` records selected decisions separately and routes them
  through capture. Acceptance defaults to no paper draft and no claim
  promotion. The paper-radar integration is metadata adapter-only, not a repo
  clone, service, export reader, or scheduler. Provider metadata and landing
  URLs are allowlisted and revalidated on read; local/reserved/obscured-IP URLs,
  private metadata, and untrusted acceptance sidecars fail closed. Acceptance
  actor provenance reaches capture events, and an already completed acceptance
  is idempotent. Each `(run_id, candidate_id)` uses a deterministic transaction
  key, so a retry after an event/sidecar interruption reuses the one valid event
  and finishes pending work. Recovery strictly matches actor, writer, origin,
  identity, payload, and dedupe state; duplicate or conflicting transaction
  events fail closed. The designated writer must still serialize acceptance
  operations for the same run.

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
python3 -m py_compile tools/bootstrap_rkf.py tools/check_install.py tools/rkf_auto_connect.py tools/build_public_dashboard.py
python3 -m unittest discover -s tests
python3 tools/rk.py lint --mode all
python3 tools/rk.py topic lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/public_safety_scan.py
```

For RKF state checks, ask Codex for topic lint, all lint, paper queue, world
context, hot demand recording, or hot refresh through the app/internal runtime.
There is no `hot show` workflow; inspect `hot.md` directly.

2026-07-13 onboarding/dashboard/discovery verification completed with 297 unit
tests, Python compilation, all/topic/graph lint, public-safety scan, 14 closed
JSON schemas, deterministic discovery-acceptance restart recovery,
task-owned cross-project runtime validation, `rkf-auto-connect` exact-manifest
validation, self-contained exact-preview review bundles, desktop/mobile browser
QA, and a non-persistent Crossref/arXiv live smoke test. Exact mobile
geometry was verified at a 390 CSS-pixel viewport (`scrollWidth == innerWidth`)
after discovering that headless Chrome's command-line window has a 500-pixel
minimum unless device metrics are overridden. The current machine diagnostic
remains blocked by one connection-doctor blocker and a non-exact pre-existing
global auto-connect skill; neither was changed automatically.

The latest private aggregate preview for the finalized dashboard schema is
`20260713T093756Z_5eb6a1d2f68b`, exact hash
`5eb6a1d2f68bfbbcfc76a75efa5a5412cb30e7a659f92c98db3609c9680216d4`.
Its self-contained private review page was rendered and verified at 1440 and
390 CSS pixels with no horizontal overflow or non-file request. It is
`pending-review`, not published. The committed site snapshot remains the
synthetic preview with hash
`327a2fea61033a126a1e6fe3bd1cfdbd53e0b3bd8994a2c532a8ebe3e3cf2f51`.

As observed on 2026-07-13, GitHub Pages is disabled on both configured remotes.
The local `main` commit is 9 ahead / 0 behind `wiki_research/main` and 26 ahead /
2 behind public `origin/main`; the latter has an empty content diff but is not a
fast-forward relationship. Publish through a reconciled integration branch and
normal PR, then enable Pages with GitHub Actions and a deployment reviewer;
never force-push the public default branch for dashboard activation.

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
- Trap: creating a new runtime for every cross-project action. Fix: open one
  task-owned runtime only after validating the external project marker, then
  reuse it for activation and every subsequent action in that Codex task.
- Trap: treating the connector TOML as proof that Codex can discover RKF.
  Fix: install and strictly verify the vendored `rkf-auto-connect` skill too;
  preserve and manually review any differing pre-existing global skill.
- Trap: assuming an enabled marker or a previous task keeps RKF active. Fix:
  every new task starts OFF and requires the user to say `啟動 RKF`.
- Trap: treating candidate discovery or a public-safe dashboard snapshot as
  evidence/publication approval. Fix: preserve candidate and exact-hash review
  gates; commit, push, Pages activation, scheduling, and claim promotion each
  remain separate decisions.
- Trap: starting a clean-install discovery walkthrough with a topic ID that has
  not been registered yet. Fix: use an explicit public-safe query first, then
  review and add a topic before using its default search strings.
- Trap: trusting deprecated discovery `decision`/`status` fields or an
  unvalidated acceptance sidecar when building public counts. Fix: strict-load
  v2 runs and acceptance state; route shape-validated v1 records only to the
  legacy/unclassified aggregate and fail the preview on malformed state.
- Trap: treating a headless Chrome `--window-size=390` screenshot as a true
  390-CSS-pixel mobile viewport on this Retina Mac. Fix: use DevTools device
  metrics and verify `documentElement.scrollWidth == innerWidth`.
- Trap: letting multiple Drive-synced computers project the same capture into
  wiki files. Fix: keep immutable events as source of truth and allow only the
  registered maintenance writer to materialize projections.
- Trap: treating a valid migration preview as a live-migration authorization.
  Fix: request a separate user approval that names the exact manifest hash only
  after the 57-paper preview has no unresolved routing items.
- Trap: using Obsidian as a parallel knowledge database. Fix: keep it a local
  view client of the Google Drive wiki, never sync `.obsidian/` alongside the
  canonical files, and generate Bases only from Markdown properties.
- Trap: treating a cleanup candidate or paused automation as pre-approved.
  Fix: use the generated manifest and wait for one exact user-approved batch;
  automation creation and activation each require their own approval.
- Trap: treating a sandbox-only writer-access failure as an OS permission
  failure. Fix: the live workspace now has an opaque machine identity and a
  matching designated-writer registry; use the path-redacted elevated install
  diagnostic for approved external operations, while ordinary sandboxed runs
  must still stop when writer storage is not writable.
- Trap: treating a project-local `RKF/hot.md` or `RKF/memory.md` as canonical
  RKF evidence. Fix: keep `RKF/` bridge files pointer-oriented and route
  durable capture through the central RKF Codex app/action flow.
- Trap: assuming `python3` resolves to the same runtime in the main checkout
  and a temporary worktree. On this project it may resolve to Python 3.9 in the
  main checkout and Python 3.13 in a temporary worktree. Fix: keep the
  `tomllib` fallback covered by direct parser tests and verify marker/session
  tests under both the default runtime and a Python 3.11+ runtime when runtime
  routing changes.

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

- Complete branch/PR reconciliation, GitHub Pages enablement, deployment, and
  live exact-hash verification for the approved public dashboard snapshot.
- Two governed candidate-only manual discovery runs have completed for the two
  approved topics with Crossref and arXiv: 40 candidates, 0 accepted, and no
  promotion. Create and verify the approved weekly scheduler only after its
  saved policy exactly preserves those boundaries.

- The private 57-paper migration preview has been generated and validated.
  Inspect its ignored local manifest/diffs and request approval tied to that
  exact hash before any live apply.
- Run `connect.doctor` before any shared-writer generated view or maintenance
  action; resolve blockers manually rather than selecting a sync winner.
- `rkf-maintenance-preview` now exists and was read back as `PAUSED`; it is a
  daily local preview-only job and must stay paused until machine/writer setup,
  schedule, permitted writes, and activation are separately approved.
- Ask for an exact cleanup-manifest batch before deleting, archiving, or
  modifying any candidate or paused automation.
