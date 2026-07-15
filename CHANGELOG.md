# Changelog

## v1.1.0 - 2026-07-15

- Apply the explicitly approved 57-paper canonical migration for manifest
  `bb4ef62bcb0c533bf023838f9468b180dcb36441da8f674789cbf5405e340aff`,
  create 57 reading ledgers, and retain the 114-entry private checksum-verified
  rollback journal. Cleanup and backup removal remain separately gated.
- Complete the repository-safe v1 runtime slice: expand the canonical schema
  to Paper/Evidence/Claim/Synthesis, provider, Read, retrieval, project,
  activation, and action contracts; make activation closure append-only; add
  object-origin Review filters and evidence matrices; enforce full-text digest
  and deterministic appraisal gates; add optional full-text/appraisal/retrieval
  adapters with PDF magic validation, SHA-256 dedupe, Paper access updates,
  structured argument maps, external-command smoke tests, and safe fallback;
  and reject non-v1 actions from the
  default runtime. Migration-only tools remain behind an explicit internal
  compatibility flag until the applied 57-paper migration rollback window is
  closed and its backup disposition is separately approved.
- Fail closed across the final research boundary: Read now requires a valid
  canonical Paper and scope no broader than its access state; Claim and
  Synthesis revalidate Evidence content fingerprints and ActionEvent receipts;
  public-safe Ask rejects drifted canonical objects and semantic results that
  lack canonical locators; read-only Ask keeps private action lineage without
  writing a shared retrieval run; checksum artifacts preserve all Paper/source
  relations; and canonical state, retrieval, artifact, Review, and lineage
  paths reject symlink escape. Private artifact and lineage storage now uses
  owner-only permissions.
- Make the default strict install diagnostic v1-native: retired
  designated-writer and multi-computer doctor checks now run only with the
  explicit maintainer `--legacy-compatibility` flag.

- Complete v1 Phase 0 scope freeze: align the English and Traditional Chinese
  README around install → Connect & Activate → the five-workflow 10-minute
  loop; add a dependency-free machine-readable keep/merge/delete/temporary-shim
  inventory with owner, migration/test impact, follow-up issue, and mandatory
  shim removal versions; and record branch-retention evidence. Establish
  `v1.1.0` as the first verifiable public tag without fabricating or moving a
  historical `v1.0.0` tag.
- Define the compatible RKF `v1.1.0` product surface as five workflows—Add,
  Ask, Read, Compare & Synthesize, and Review—plus task-scoped Connect &
  Activate. Add canonical paper/evidence/claim/synthesis enums, conservative
  legacy reading-state mapping, locator-backed Evidence, human-verification
  gates, actionable Review/Home, and optional full-text/appraisal/retrieval
  provider contracts.
- Add stable project IDs to new v2 connection markers and append-only,
  path-redacted ActivationEvent/ActionEvent lineage with idempotent retries.
  Legacy v2 markers without a project ID now require explicit review/upgrade.
- Remove default automation prompts, meeting/seminar/overview templates, and
  the Obsidian workflow entry. Non-core dashboard/discovery/migration/CLI code
  is classified as an internal compatibility shim with a removal target rather
  than an app-facing workflow.
- Replace the public admin/vanity-metric Observatory with a synthetic guided
  Paper → Evidence → Claim → Synthesis demo, research-quality metrics, a
  data-quality banner, and reachable mobile navigation.

- Add portable, preview-first local onboarding, version-matched global
  `rkf-auto-connect` installation/diagnostics, and non-overwriting v2 project
  connection scaffolding. Preflight now validates the complete skill bundle,
  connector/config parents, symlinks, and every bridge target before writing,
  so stale or malformed integrations fail without partial setup. Connected
  projects now use one validated task-owned action runtime across activation,
  retrieval, discovery, dashboard preview, and capture; clean installs begin
  discovery with an explicit query before any topic is registered.
- Add an aggregate-only RKF Observatory static dashboard with private preview,
  self-contained private visual review, exact-hash local publication,
  fail-closed GitHub Pages validation, and an inactive deployment workflow
  example. Review bundles are fixed-tree, checksum-verified, noindex,
  nonpublishing, and directly openable without a server. Recent hotspots are now separate from
  registered research areas; machine-neutral storage/doctor state and legacy
  discovery are visible without paths or identities. Unknown or retired topic
  IDs remain untriaged instead of inflating topic-linked demand. Governed
  discovery counts reuse strict run/acceptance validation, while shape-validated
  v1 candidates can appear only as legacy/unclassified.
- Add candidate-only Crossref/arXiv discovery with optional OpenAlex and
  paper-radar metadata adapters, immutable exact-hash runs, separate acceptance
  state, selected capture, and no default paper-draft or claim promotion.
  Public-URL and metadata privacy checks reject local/obscured-IP destinations
  and credential-shaped content; recorded runs and acceptance sidecars are
  semantically revalidated, acceptance actor provenance reaches capture events,
  and repeated acceptance does not create duplicate capture events. A
  deterministic transaction key now recovers the same capture event after an
  event/acceptance-sidecar interruption, while actor, writer, payload, identity,
  or duplicate-event conflicts fail closed.
- Add approval-bound `paper.migration.apply` and `paper.migration.rollback`.
  Apply rechecks every reviewed checksum, creates a private raw backup plus
  per-target journal, uses atomic replacements, and automatically rolls back
  partial failure. Explicit rollback restores exact original bytes. No live
  apply or backup deletion occurs without manifest-specific approval.
- Add and verify the `rkf-maintenance-preview` Codex automation in `PAUSED`
  state. Its prompt is daily, read-only, doctor-first, and explicitly forbids
  migration apply, canonical view/index writes, cleanup, delivery, and claim
  promotion until a separate activation approval.
- Add RKF 1.1 paper-centered migration preview: strict v1.1 paper template
  and lint contract, lossless copied-corpus transforms, per-page diffs, copied
  migration ledgers, routing manifests, and a stable manifest hash. Preview
  writes only local ignored artifacts; live apply remains separately approved.
- Add shared-workspace safety primitives: read-only `connect.doctor`,
  writer/conflict/schema/PDF/staleness checks, post-activation read-only
  downgrade, and expected-checksum atomic named-file writes.
- Add canonical Obsidian Base rendering (`papers`, `reading queue`, `inbox`,
  `questions`, `synthesis`). Bases are generated only by the designated writer
  and Obsidian remains a local view client rather than a second database.
- Add daily/weekly/monthly maintenance previews and no-promotion receipts, an
  uncreated automation proposal, and pending cleanup-manifest generation with
  exact candidates, references, risks, rollback notes, and no apply operation.
- Add portable incoming `paper_relations` parsing, graph edges, and link lint.
- Keep inbox backlink injection in frontmatter and the reading ledger; it no
  longer recreates legacy non-paper sections in paper pages.
- Add RKF 1.1 Phase 1 activation and closed-loop foundations: every new Codex
  task starts OFF; `rkf.activate` performs read-only preflight;
  `query.search` provides deterministic maturity-aware retrieval;
  `capture.route` records deduplicated immutable events; `rkf.deactivate`
  closes the session. Shared projections use a designated writer with
  `capture.project_pending` checkpoints, and every capture receipt states
  `Promotion: none`.
- Keep project/workspace TOML parsing compatible with Python 3.9 by preserving
  top-level values and typed booleans in the standard-library fallback parser.

- Reframe RKF around active paper reading maturity: early paper drafts can begin
  from metadata, abstracts, partial full text, or user-provided PDFs, while
  stable claims and trusted synthesis stay gated by locators, human feedback,
  or existing governed sources; explicit blockers keep unresolved claims from
  promotion.
- Add reading maturity fields for paper and synthesis objects plus a
  public-safe `state/reading/` ledger contract.
- Add paper queue, feedback, next-item, and nudge CLI flows for registered
  papers that need user PDF, human review, or synthesis review.
- Add RKF inbox capture for ChatGPT/web/project clips with guarded DOI injection
  that creates or backlinks source/paper pages without promoting claims.
- Add RKF auto-connect design and helper plan for cross-project
  Active/Aggressive capture into RKF inbox and hot-query layers.
- Add project-local `RKF/` bridge folder scaffolding for connected projects,
  with public-safe `README.md`, `hot.md`, `memory.md`, and `captures.md`
  templates that remain operational indexes rather than evidence.
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
