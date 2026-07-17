# PROJECT_MEMORY

Last updated: 2026-07-16

## vNext Issue #18 Scientific Artifact Acquisition

- The current implementation includes the issue #18 **portable-core slice**
  plus its repository-owned completion layer, but not the human- or
  institution-owned gates in the full issue inventory. Institution-specific
  authorization and several non-PDF/domain metadata reviews remain external.
  Access-control, SSO, and CAPTCHA surfaces must be detected and stopped as
  typed manual handoffs; they are never bypassed.
- `IdentifierAdapterRegistry` now gives each non-DOI identifier type one
  fail-closed owner. Dedicated adapters resolve ADS bibcodes, public OSF
  primary files, current EarthArXiv Janeway and legacy OSF records, ESSOAr
  DOIs, NOAA IR PIDs, WMO publication/library IDs, and registered AR6 IPCC
  report IDs. OSF withdrawn records, bare ESSOAr article numbers, free-form
  NOAA series numbers, and unknown WMO/IPCC aliases remain manual official-
  search handoffs rather than guessed artifacts. Complete IPCC volumes remain
  subject to the bounded default artifact size.
- `rkf/acquisition.py` now implements canonical DOI/URL/arXiv/ADS/DataCite/
  Handle/NTRS/repository/report identifiers, conflict review, a portable
  bounded OA route ladder, atmospheric P0 profiles, optional Elsevier/Wiley
  TDM secrets, a `paper_fetch.py --json` institutional adapter, read-only
  holdings checks, provider-level 429 backoff, private checksum storage, and
  PDF identity/readability/locator QC. The connector enables portable network
  acquisition only with `RKF_ENABLE_PORTABLE_ACQUISITION=1`; Unpaywall also
  requires a real `RKF_CONTACT_EMAIL`.
- Acquisition remains internal to `workflow.add` with `Promotion: none`.
  Idempotent `acquisition_run_id` traces are stored path-redacted under private
  state and exposed by Review; artifacts distinguish Version of Record,
  accepted manuscript, preprint, and unknown version. Provider/QC success
  never verifies Evidence or Claims.
- A new public atmospheric-journal corpus records 11 P0 representative cases
  (AGU/Wiley, Wiley/RMetS, AMS, Copernicus, Elsevier, Springer, Nature, IOP,
  ACS, AAAS, and Taylor & Francis) and 3 P1 cases (MDPI, Frontiers, and
  J-STAGE). In the bounded 2026-07-16 final live run, all 14 were `obtained`
  and all 14 met the smoke helper's research-ready PDF checks across nine
  selected route labels. The routes included current NCBI PMC Cloud and
  authorized repositories. This is evidence about those exact cases and run,
  not proof of journal-wide or future availability. The public-safe result is
  `docs/benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md`.
- Reusable same-journal retry order is recorded in
  `docs/operations/atmospheric-journal-acquisition-route-playbook.zh-TW.md`.
  DOI-family publisher profiles may be reused as route hints, but exact NOAA
  PIDs, GEOMAR URLs, PMCID membership, repository handles, and bitstream UUIDs
  remain article-specific and must come from metadata or explicit user input;
  they must never be guessed from a journal match. The user-requested
  conversation record is preserved as a public-safe decision summary in
  `docs/operations/2026-07-16-issue-18-atmospheric-journal-closeout.zh-TW.md`;
  raw transcript, prompts, article text, private paths, and artifact hashes are
  intentionally excluded.
- The NCBI route now uses the current DOI-to-PMCID converter, checks
  `versions=yes`, selects the flagged current versioned PMCID (or the highest
  listed version when no current flag exists), rejects a selected version
  explicitly marked non-live, checks
  `pmc-oa-opendata` metadata for matching DOI, OA state, and retraction state,
  and converts only that service's S3 PDF pointer to its anonymous HTTPS object
  path. A non-manuscript flag is not treated as VOR proof. Crossref licenses
  are applied only to matching, active artifact versions; unknown and
  accepted-manuscript files remain conservatively classified. The route does
  not scrape or bypass PMC HTML/CAPTCHA surfaces.
- Portable HTTP now validates the actual connected socket peer before reading
  a body, disables environment-proxy resolution in the default opener, rejects
  non-public peers and HTTPS-to-HTTP redirects, and strips path/query data from
  `Referer` before removing it on cross-origin redirects. Secret-bearing
  requests require HTTPS and cannot cross origins.
- The post-PR-#30 completion layer adds a monotonic wall-clock deadline while
  streaming HTTP bodies and byte-bounded stdout/stderr capture for both
  external full-text adapters. Output overflow kills the child and returns a
  typed blocker; timeout, profile-busy, watchdog, and Ovid `license_seat_e3`
  remain retryable rather than becoming unavailable.
- Desktop publisher tokens can now be read from allowlisted macOS Keychain,
  Linux Secret Service, or optional Windows Credential Manager/`pywin32`
  backends. The connector chooses the native backend only after acquisition is
  explicitly enabled. Secret values remain in memory/header only and are not
  written to lineage or logs. Environment secrets remain a CI/test-only
  backend.
- Provider `Retry-After` is persisted across processes in an owner-only SQLite
  file containing only route labels and timestamps. Review derives a
  path-redacted route-health scorecard from acquisition attempts. Institution
  holdings can be imported from a six-column CSV through
  `tools/import_rkf_holdings.py`; preview is the default and `--apply`
  atomically creates the owner-only SQLite table consumed read-only by
  `SQLiteHoldingsEntitlementProvider`.
- Related dataset/code/supplement/HTML/XML/version/correction/retraction
  pointers now receive independent `rkf-related-artifact-v1` records linked to
  the checksum source artifact, Paper, and acquisition run. The record stores
  only host plus identifier fingerprint, retains `Promotion: none`, and stays
  `pointer-only` with explicit provenance review gaps until a human validates
  identity and relationship. Crossref and DataCite relationship metadata feed
  the same graph. Review exposes these records plus missing artifact version
  and license fields.
- The optional institutional/browser boundary is now executable only when a
  caller supplies a machine-local `BrowserSessionProvider` and explicitly uses
  policy profile `institutional-external`; calls are serial. The bundled
  `ExternalPaperFetchProvider` implements that boundary. RKF still ships no
  institution endpoint, credentials, CAPTCHA/SSO automation, or access-control
  bypass.
- Each acquisition has a shared 32-request artifact/landing budget across
  top-level and recursive candidates. PDF DOI identity compares a complete
  token exactly, including legacy AMS angle-bracket forms, instead of accepting
  a DOI prefix. External `paper_fetch.py` route output is restricted to the
  pinned upstream route allowlist and cannot echo arbitrary token-shaped text.
- Repository landing discovery now supports HTTP Signposting PDF items. A
  standard DSpace front-end bitstream UUID is tried through the same-origin
  public REST content endpoint before the advertised front-end URL. This made
  the migrated Iowa State repository route for the AMS representative stable;
  the resulting PDF still passed the ordinary DOI/readability/locator gates.
- Private artifact stores are anchored to an explicit trusted boundary and
  fail closed on symlinks/path escape. The live-smoke helper additionally
  requires a fresh non-symlinked report/artifact directory outside the
  repository and refuses overwrite; PDFs and private raw reports are never
  committed.
- The earlier 2026-07-16 broad user corpus contained 79 citations and 78 DOI
  identifiers. Treat the following numbers as a historical baseline, not the
  current 14-case journal result or a global availability claim.
  The final citation-only live run obtained 40 artifacts; an official UCAR URL
  resolved the no-identifier Tewari 2004 item, producing 41 obtained and 38
  remaining manual. All 41 passed PDF/checksum/text/page/title-or-DOI and
  locator-readiness QC under the then-current classifier/verifier; that corpus
  was not rerun under the later stricter identity and conservative version
  rules, so its VOR and identity labels are historical rather than current
  revalidation. Raw PDFs and JSON remained in temporary private storage; only
  the public-safe result is recorded in
  `docs/benchmarks/acquisition-issue-18-atmospheric-smoke.md`.
- Five legacy AMS DOI strings containing percent-encoded angle brackets first
  exposed a double-encoding bug. Canonical DOI resolution now decodes once and
  URL construction re-encodes once; a focused live rerun resolved Crossref
  identity and correctly left only the AMS authorization blocker.
- Remaining gates are not ordinary portable-core implementation gaps: a real
  Unpaywall contact and any authorized institutional/Ovid configuration are
  machine-local; ambiguous free-form report aliases require an authoritative
  catalogue; downloaded HTML/JATS/XML/supplement identity validation and
  atmosphere-specific availability-statement extraction need source-specific
  evidence; and URL-only version/license plus provider terms remain human
  provenance/legal review. The live 14/14 observation does not close those
  gates. Do not label the historical baseline's remaining 38 globally
  unavailable; they were manual/authorization handoffs in that environment.

## Unreleased v1.2 Locator Promotion Gate

- GitHub epic #23 is split into FindingDraft #24, context-first Ask #25,
  truthful onboarding #26, and Ask scaling #27. The implementation target is
  still unreleased; `v1.1.0` remains the latest published release.
- The canonical trust path is now Paper → source context → FindingDraft →
  exact-locator Evidence → human-reviewed Claim → Synthesis. FindingDrafts may
  have `missing`, `coarse`, or `exact` locator state, but only an exact,
  fingerprint-valid, receipt-backed finding can be promoted. Batch capture and
  its ActionEvent receipt form one rollback boundary so a trace failure leaves
  no orphan drafts.
- `workflow.ask` defaults to `answer_policy: context-ok` and exposes
  `answer_mode: no-results | context-only | mixed | evidence` while retaining
  the compatible `answer_boundary`. `evidence-only` keeps the formal-support
  gate. A provider locator never raises canonical trust, and timing fields are
  diagnostic metadata excluded from retrieval/run identity.
- Deterministic Ask may use `.rkf_private/query-index-v1.sqlite3` as a
  disposable, fingerprint-backed SQLite projection. Warm hits reuse candidate
  data without rereading corpus contents, then fully validate only an
  oversampled canonical window plus semantic targets. Unsafe, stale, corrupt,
  or tampered index state falls back to a full deterministic scan; deletion
  cannot change canonical data. The reproducible baseline is
  `python3 tools/benchmark_rkf_ask.py --check` and uses ranking/trust parity,
  corpus-read reduction, and validation-window limits rather than a fixed
  millisecond requirement. Persistence policy is unchanged: active writable
  Ask may persist a retrieval run and refresh the projection;
  `ACTIVE_READ_ONLY` writes neither, while both retain private ActionEvent
  lineage. Query-index controls are runtime-owned.
- Installation now has explicit profiles. Local core uses
  `python3 tools/check_install.py --profile core --strict --json`; Codex
  integration uses `--profile codex` and treats a missing or stale
  connector/skill as a failure. `python3 tools/demo_quickstart.py --check`
  runs all five workflows with two synthetic papers in an isolated,
  zero-network workspace.
- The integrated v1.2 working tree passed 420 unit tests, Python compilation,
  canonical schema validation, topic/all lint, public-safety scan, both strict
  install profiles, connector resolution, the zero-network quickstart, the
  relative-I/O Ask scaling baseline, and `git diff --check` on 2026-07-15.
- The 2026-07-15 pre-merge issue-audit snapshot found seven open issues: #15,
  #18, and #23–#27. #15 remained open for its separately approved rollback-
  window, exact cleanup-manifest, and opt-in automation gates; #18 remained the
  unimplemented vNext acquisition backlog. At that audit cutoff, #23–#27 were
  implemented and verified on pushed commit `1a77fae` with successful GitHub
  Actions run #39, but no PR existed and the commit was not yet in `main`; no
  issue was closed during that audit. The agreed closeout order after merge was
  #24–#27 first, followed by parent epic #23, with merge and CI evidence.

## RKF v1.1 Scope Simplification

- Everyday RKF use is documented as natural-language-first inside a connected
  project folder: activate and validate, derive queries from the current
  conversation, Ask existing RKF knowledge, show public-source candidates, and
  Add only user-confirmed DOI/URL metadata plus a short note. Whole transcripts
  and raw prompts remain excluded. `rkf.status` now preserves the same control
  action while adding a path-redacted, project-grouped summary of activation
  records whose latest transition is `started`; it reports open counts and
  warns that interrupted tasks are lineage-open rather than proven-live OS
  processes.
- Phase 0 uses `docs/operations/v1-scope-inventory.yaml` as the canonical,
  machine-readable classification authority. It is JSON-compatible YAML 1.2,
  requires owner/follow-up/migration/test impact for every entry, and requires
  an explicit removal version for every `temporary-shim`.
- The public README path is installation → preview/apply `connect-project` →
  task-scoped activation → Add → Ask → Read → Compare & Synthesize → Review.
  The actual bootstrap CLI is flag-based: preview with
  `python3 tools/bootstrap_rkf.py`, apply with `--apply`, then run
  `python3 tools/check_install.py --profile core --strict --json`. Codex
  integration separately installs the connector and validates with
  `--profile codex`. Positional `preview`/`apply` examples are invalid and
  must not return to the docs.
- The branch audit in `docs/operations/v1-branch-audit.md` records live compare
  evidence. On 2026-07-15 nine patch-equivalent historical branches with zero
  net changed files were removed. Only `main` and
  `codex-rkf-external-sandbox-workflow` remained; the latter has ten real file
  differences and requires a separate product decision.
- GitHub issues #15–#18 define the current v1 contract. Live GitHub inspection
  on 2026-07-15 found no historical tags or releases; `v1.1.0` is therefore the
  first verifiable public tag. Do not fabricate or move a `v1.0.0` tag merely
  to match older prose.
- The app-facing registry is limited to Connect & Activate plus five workflows:
  `workflow.add`, `workflow.ask`, `workflow.read`,
  `workflow.compare-synthesize`, and `workflow.review`.
- Canonical paper state is split into `access_state` and `review_state`.
  `rkf/schema.py` contains conservative legacy mappings; unexpected values are
  findings, never a normal `other` KPI.
- Phase 1 schema-first work now loads canonical enum values directly from
  `schemas/rkf_v1.schema.json` through `rkf/schema.py`. The maintainer gate
  `python3 tools/validate_rkf_schema.py` checks runtime/schema parity and
  legacy mapping targets; legacy `reading_state`/`reading_status` inputs remain
  an explicit compatibility boundary until the migration report and backup
  window are complete.
- The current private Phase 1 preview uses the canonical paper transform,
  covers all 57 paper pages, and classifies all 64 deprecated discovery
  candidates as isolated candidate-only records. It has zero unresolved or
  validation findings. On 2026-07-15 the user explicitly approved manifest
  `bb4ef62bcb0c533bf023838f9468b180dcb36441da8f674789cbf5405e340aff`;
  the atomic live apply completed for 57 paper pages and 57 reading ledgers.
  All 114 live outputs and all 114 backup journal records passed checksum
  verification. Preserve backup
  `paper-v1.1-bb4ef62bcb0c533bf023838f9468b180dcb36441da8f674789cbf5405e340aff`
  until a separately approved rollback-window closeout and cleanup batch.
- New v2 project markers contain a random stable `project_id`. Each activation
  and action receives append-only, path-redacted lineage under ignored local
  state. Raw prompt, private path and secret values are excluded. Retrying the
  same action in one activation reuses the ActionEvent.
- Canonical Evidence requires an existing `rkf-paper-v1.1` Paper, an exact
  page/section/figure/table/paragraph locator, valid lineage, and a content
  fingerprint. Claim and Synthesis creation reloads and revalidates those
  fields plus the matching successful ActionEvent object receipt; direct
  Evidence or Claim edits fail closed. `verified` claims require currently
  human-verified Evidence. Candidate metadata and LLM output remain
  insufficient.
- `paper-fetch`, `paper-review-and-digest`, and `vault-search` inform optional
  provider contracts only. The complete Scientific Artifact Acquisition Engine
  remains vNext work.
- The public site is a synthetic/public-safe guided demo. It must not expose
  writer, storage, doctor, project activity, raw candidate/run, graph vanity,
  raw prompt, paper identity, or private-path data.
- Default profile checks are v1-native and do not run the retired
  designated-writer or multi-computer doctor product. Maintainers may add
  `--legacy-compatibility` while those internal shims remain. On 2026-07-15 the
  installed global `rkf-auto-connect` was backed up and synchronized to this
  checkout; the then-current strict diagnostic returned `ready` with zero
  failures.
- The v1.1 release candidate passed 372 tests on Python 3.9 and Python 3.12,
  canonical schema validation, topic/all/graph lint, public-safety scan,
  exact-snapshot site validation, install parity, and `git diff --check`.

## Project Summary

- Project: Research Knowledge Framework (RKF)
- Mode: research-engineering hybrid
- Repo role: framework code, prompts, docs, tests, and examples for governed
  research memory
- Historical changelog baseline: `v1.0.0` (not a verified public tag)
- Active workspace data: external shared `wiki/` and `raw/` roots configured in
  `rkf.workspace.toml`
- Primary audience: the user, future Codex agents, and research workflows that
  need source-aware long-term memory without turning candidate material into
  stable evidence

## Current State

- The v1.1 target exposes only the five governed workflows plus Connect &
  Activate. Older hot-query, world-context, discovery lifecycle, dashboard,
  migration, maintenance, view, and cleanup routes are internal compatibility
  or deletion candidates, not parallel user-facing products.
- The repository root does not necessarily store the live `knowledge/` tree.
  Resolve operational wiki state through `rkf.workspace.toml` and the configured
  `wiki_root`.
- `hot.md`, when present in the live wiki root, is a legacy operational demand
  signal only; it is not canonical evidence or a v1 product entry.
- The repo contains `docs/LITERATURE_MATRIX.md` and `docs/AI_USE_LOG.md`; use
  them for public-safe literature synthesis notes and AI-use/disclosure traces.
- README files are the public front door; `MODE_REGISTRY.md` is the active mode
  and write-boundary reference; `docs/FEATURES_AND_COMMANDS.zh-TW.md` is now the
  Codex app workflow and capability map.

## Durable Decisions

- `RKFActionRuntime` rejects every action outside Connect & Activate plus the
  five v1 workflows by default. Migration/dashboard/discovery/sync/view/
  maintenance/cleanup routes are reachable only through the explicit
  `allow_internal_actions=True` compatibility boundary used by maintainer
  tests while the migration backup window remains open.
- `connect.validate` checks the v2 marker, stable random `project_id`, marker
  schema, connector version, bridge presence, and central RKF availability
  without running multi-computer writer/storage diagnostics. Invalid legacy
  markers fail closed in the default runtime.
- Activation start/close/failure/expiry are append-only transition events.
  Deactivation never mutates the activation-start snapshot. Action lineage can
  be filtered by project, activation, action, status, and target object.
- `workflow.read` accepts only an existing, schema-valid canonical Paper and
  rejects a requested reading scope above its `access_state`. It supports
  FindingDraft capture/promotion, direct locator-backed Evidence, and scoped
  `digest | appraise | both` Read runs.
  Digest requires full text; abstract-only appraisal stays low-trust; citation
  existence is distinct from citation support; failed external checks remain
  visible; deterministic inference-gap rules are authoritative gates.
- Optional FullText/Retrieval providers are off by default. Acquisition uses
  typed status and SHA-256 artifact dedupe; one checksum artifact can retain
  canonical `paper_ids` / `source_ids` relations, while legacy singular fields
  remain compatibility mirrors. Private handles remain under `.rkf_private`,
  and root/parent/target symlinks are rejected before a private handle write.
  Retrieval stays exact-first. Public-safe semantic hits require an explicit
  public-safe scope and an existing canonical object; a missing locator keeps
  the result context-only, while a supplied provider locator still cannot
  upgrade trust. Display data is rebuilt from canonical state. Deterministic
  Ask also excludes malformed,
  drifted, non-public-safe, or receipt-less Evidence/Claim/Synthesis objects.
  Persisted run identity includes result content, so changed results create
  lineage successors while identical results deduplicate. Read-only Ask skips
  the shared retrieval-run write but still records its path-redacted private
  ActionEvent. Provider failure falls back safely.
- New v1 canonical state, retrieval runs, provider artifacts, Review reads, and
  private lineage reject root/parent/target symlinks and path escape. Private
  artifact and lineage directories/files are normalized to owner-only
  `0700`/`0600`; lineage uses no-follow, anchored directory access and rejects
  traversal IDs.
- The pinned third-party design references and verified MIT notices are in
  `THIRD_PARTY_NOTICES.md`; no upstream source file was copied into v1.

## Internal Compatibility History (not v1 product authority)

The notes below describe retained migration/maintenance implementations and
older releases. They do not expand the current app-facing v1 surface.

- RKF 1.1 Phase 1 uses a session-owned `RKFActionRuntime`. Every new Codex task
  starts OFF; only explicit `rkf.activate` can enable that task after a
  read-only storage/writer preflight. `rkf.deactivate` returns it to OFF, and a
  project marker never persists activation.
- Activation consent is literal and separate from workflow intent. `Ask RKF`,
  `問 RKF`, Add, Read, Compare & Synthesize, or Review while OFF must return
  `RKF_NOT_ACTIVE`; the agent must not activate, connect, scan, or write RKF
  research data until the user separately and directly requests activation.
  An OFF Ask additionally asks `是否要「啟動 RKF」？` and waits; neither the
  original Ask nor this question constitutes activation consent.
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
  missing files only; `tools/check_install.py --profile codex --strict` fails
  if the connector or installed global skill is missing or differs from this
  checkout. Bundle
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
python3 tools/validate_rkf_schema.py
python3 tools/rk.py lint --mode all
python3 tools/rk.py topic lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/public_safety_scan.py
```

2026-07-16 issue #18 atmospheric-journal verification completed with 492 unit
tests, Python compilation, a fresh 14-case live run, and exact corpus/report
comparison. The designated run obtained 14/14 artifacts and all 14 passed the
readability, page, locator, and identity gate across nine route labels.
Version/license review remains separate: five artifacts are version-unknown,
eight have no machine-recorded license, and the IOP Crossref artifact is an
accepted manuscript. The raw report and PDFs remained under a fresh private
repository-external temporary boundary; public records retain `Promotion:
none`.

For user-facing RKF work, use only Add, Ask, Read, Compare & Synthesize, and
Review after explicit activation. Maintainers may still run the documented
lint and safety commands directly; old queue/world/hot names are compatibility
history, not product workflows.

2026-07-13 onboarding/dashboard/discovery verification completed with 297 unit
tests, Python compilation, all/topic/graph lint, public-safety scan, 14 closed
JSON schemas, deterministic discovery-acceptance restart recovery,
task-owned cross-project runtime validation, `rkf-auto-connect` exact-manifest
validation, self-contained exact-preview review bundles, desktop/mobile browser
QA, and governed Crossref/arXiv discovery. Exact mobile
geometry was verified at a 390 CSS-pixel viewport (`scrollWidth == innerWidth`)
after discovering that headless Chrome's command-line window has a 500-pixel
minimum unless device metrics are overridden. The old global skill was moved to
a timestamped backup and replaced with the exact vendored bundle. The live
workspace now has an opaque machine identity and matching designated-writer
registry; the elevated path-redacted strict diagnostic is ready. Doctor remains
warning-only because 57 existing PDFs still lack governed identity mapping.
An ordinary repo-only sandbox cannot prove write access to external shared
storage, so unattended runs must still stop if their execution profile reports
writer storage unavailable.

2026-07-14 Phase 0 scope-freeze verification completed with 305 unit tests,
Python compilation, all/topic/graph lint, `public_safety_scan.py`, documentation
command/link/inventory checks, and `git diff --check`. The GitHub issue record
was updated without closing #15–#19 or claiming unmerged work as complete.

2026-07-14 Phase 1 schema-gate slice completed with 308 unit tests, canonical
schema validation, Python compilation, all/topic/graph lint, public-safety
scan, and `git diff --check`. This slice does not migrate live paper records.

The latest private aggregate preview for the finalized dashboard schema is
`20260713T093756Z_5eb6a1d2f68b`, exact hash
`5eb6a1d2f68bfbbcfc76a75efa5a5412cb30e7a659f92c98db3609c9680216d4`.
Its self-contained private review page was rendered and verified at 1440 and
390 CSS pixels with no horizontal overflow or non-file request. The user
approved that exact preview/hash, and it was published without rebuilding the
snapshot. The committed and live JSON both report `publication.status` as
`published`, and `approved_snapshot_hash` equals `snapshot_hash`.

PR #13 reconciled the public history without force-push and merged the
Observatory release into public `main`. GitHub Pages uses the GitHub Actions
source and a `github-pages` environment restricted to `main`, with a required
reviewer. Deployment workflow run #1 completed successfully for merge commit
`9f82519`; the live site is
`https://chenhau-lan.github.io/ResearchWiki/`. Live HTML and JSON were verified,
including the exact approved hash and absence of the private-review banner.

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

- Future dashboard refreshes must create a new private preview and receive a new
  exact-hash approval; never treat the current deployment approval as reusable.
- Monitor the first scheduled run of `rkf-weekly-paper-candidate-harvest`. Its
  saved state is ACTIVE for Monday 09:00 `America/Denver`, and its prompt fixes
  both approved topics, Crossref + arXiv, 20 candidates per topic/run, exact
  recording, 0 automatic acceptance, and `Promotion: none`.

- Review the applied 57-paper canonical state during the rollback window. Keep
  the exact private backup and journal unchanged until a separate cleanup
  approval decides their disposition.
- For legacy internal shared-writer/view maintenance only, run the explicit
  `--legacy-compatibility` install diagnostic and resolve blockers manually.
- `rkf-maintenance-preview` now exists and was read back as `PAUSED`; it is a
  daily local preview-only job and must stay paused until machine/writer setup,
  schedule, permitted writes, and activation are separately approved.
- Ask for an exact cleanup-manifest batch before deleting, archiving, or
  modifying any candidate or paused automation.
