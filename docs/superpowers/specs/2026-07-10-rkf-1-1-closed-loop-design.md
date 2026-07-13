# RKF 1.1 Closed-Loop Research Memory Design

Date: 2026-07-10
Status: Approved by user; implementation proceeds through independent phase plans and approval gates
Scope: ResearchWiki framework, cross-project activation and retrieval, paper-page migration, Obsidian views, multi-computer safety, maintenance, and cleanup planning

## 1. Goal

RKF 1.1 turns the existing action-first Research Knowledge Framework into an
explicitly activated, cross-project research-memory loop while preserving the
current evidence boundary.

After the user says `啟動 RKF` in a Codex session, research tasks query the
central RKF before project-local material, new source leads and reusable
research discussions enter conservative capture paths, and all writes remain
traceable. Before activation, RKF performs no automatic query or capture.

The release also migrates the current 57 live paper pages toward a
paper-centered structure. A paper page describes the paper itself. Current
manuscript use, project strategy, cross-paper curiosity, and broader research
ideas live in overview, question, synthesis, inbox, or reading-ledger objects
that point to the paper.

## 2. Current Evidence Baseline

The design is grounded in the repository and live workspace state observed on
2026-07-10:

- The framework test suite passes 70 tests.
- Python compilation, RKF lint, topic lint, graph lint, and the public-safety
  scan pass.
- The live wiki contains 57 paper pages, 78 source records, and 57 evidence
  artifacts.
- The private raw layer contains the source PDFs corresponding to the current
  paper corpus.
- All 57 paper pages contain project- or manuscript-specific sections that
  shift focus away from the source paper.
- The live pages predate the current maturity template: none of the 57 paper
  pages contains the complete current set of `reading_state`,
  `fulltext_status`, `human_feedback_level`, `understanding_confidence`,
  `claim_readiness`, and `reading_ledger` fields.
- The live wiki has no populated `state/reading/` ledger surface.
- The current `hot.md` records are older than the active 30-day window.
- Two existing RKF-related Codex automations are paused; one points to a stale
  checkout and a missing upload script.
- The repo contains six tracked manual images that are byte-identical to the
  corresponding example screenshots and are not referenced by active docs.

These observations make live-state migration and maintenance closure higher
priority than adding a generic vector-chat stack.

Exact private inventory details, legacy project labels, paths, and source
checksums belong in an ignored migration report. They are not copied into this
public design record.

## 3. Borrowed Patterns And Non-Goals

RKF 1.1 borrows patterns, not implementations, from current open-source work:

- [OpenKnowledge](https://github.com/inkeep/open-knowledge): provisional to
  canonical promotion, natural-language workflows, and dry-run removal plans.
- [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki): SHA256 incremental
  ingest, persistent queues, source watching, MCP/API ergonomics, and
  Obsidian-compatible views.
- [Graphiti](https://github.com/getzep/graphiti): provenance, temporal
  supersession, incremental deduplication, and invalidation concepts.
- [Onyx](https://github.com/onyx-dot-app/onyx): connector checkpoints, failed
  item queues, and targeted reindex patterns.
- [Cognee](https://github.com/topoteretes/cognee): central-memory-first prompt
  routing and small remember/recall-style action vocabulary.
- [Smart Connections](https://github.com/brianpetro/obsidian-smart-connections):
  optional local semantic related-note UX.

RKF 1.1 does not copy GPL/AGPL or source-available implementations. It does not
adopt RAGFlow, PandaWiki, Onyx, Cognee, Graphiti, or another product as the RKF
runtime.

Non-goals for this release:

- no always-on clipboard, browser, or filesystem surveillance;
- no generic vector-database chat application;
- no background daemon required for normal use;
- no second canonical database in project-local `RKF/` folders;
- no automatic stable-claim or trusted-synthesis promotion;
- no simultaneous use of Google Drive and Obsidian Sync for the same files;
- no durable full-article text in the public knowledge layer;
- no automatic commit, push, destructive cleanup, or live migration without a
  separate user approval gate.

## 4. Fixed Data Ownership

RKF has four storage planes with one responsibility each.

### 4.1 Framework control plane

The Git repository contains:

- Python runtime and structured actions;
- schemas and templates;
- tests and migration tooling;
- public workflow documentation and design records.

It does not contain the user's live wiki, PDFs, OCR outputs, private Drive
paths, private runtime state, or per-machine Obsidian configuration.

### 4.2 Knowledge plane

The configured Google Drive `wiki/` root is the only canonical knowledge
database. It contains public-safe Markdown, source/evidence metadata, reading
state, graph/index outputs, hot demand, and generated Obsidian view artifacts.

Obsidian, Codex, local search, and future optional semantic indexes are views
or clients of this layer. They are not independent sources of truth.

### 4.3 Private source plane

The configured Google Drive `raw/` root stores private source artifacts:

```text
raw/
├── doi_pdf/      immutable or near-immutable article PDFs
├── files/        original attachments and source documents
├── incoming/     unclassified and not-yet-deduplicated source artifacts
└── migration_backups/  private, temporary, approval-gated rollback material
```

The currently empty `raw/full_txt/` directory is a retirement candidate.
`migration_backups/` is excluded from indexing and is removed only through a
separately approved cleanup batch after rollback is no longer needed.
Generated OCR, PDF-to-text output, embeddings, and transient indexes belong in
a per-machine local cache and must be reproducible from source artifacts.

Large scientific datasets, model output, and instrument archives remain in
their owning research project, data archive, or NAS. RKF stores only a
public-safe manifest, checksum, version, locator, and evidence pointer.

### 4.4 Per-machine execution plane

Each computer keeps:

- ignored workspace configuration;
- a stable `machine.id`;
- a `maintenance_writer` role;
- a local reconstructible cache;
- a local Obsidian configuration and workspace state.

Machine-specific paths and links never become committed or canonical data.

## 5. Project Connection And Manual Activation

### 5.1 Project capability marker

A connected project may contain:

```text
Project/
├── .rkf-connect.toml
└── RKF/
    ├── README.md
    ├── memory.md
    ├── hot.md
    └── captures.md
```

The marker and bridge files mean that RKF is available. They do not activate
RKF and are not evidence or a second database.

The version-2 marker is:

```toml
version = 2

[rkf]
available = true
activation = "manual"
query_first = true
capture_mode = "active-aggressive"
```

Version-1 markers remain readable and are interpreted conservatively. An
upgrade preview is generated before rewriting an existing marker. A version-1
marker always means `available`; it never implies an active session.

### 5.2 Session state machine

Every new Codex session starts in `OFF`.

Activation state is session-local and is never persisted as an active default.
Closing a task, starting a new task, or handing work to another task therefore
requires a fresh `啟動 RKF` command.

```text
OFF
  -> user says "啟動 RKF"
PREFLIGHT
  -> all required checks pass
ACTIVE
  -> conflict or unsafe shared-write state appears
ACTIVE_READ_ONLY
  -> user says "停用 RKF"
OFF
```

Before activation:

- no central RKF query;
- no automatic source or discussion capture;
- no hot-query, inbox, SourceRecord, or reading-ledger write;
- only setup, status, and activation guidance is allowed.

Activation performs a read-only preflight:

- resolve the global connector and ResearchWiki checkout;
- resolve `wiki_root` and `raw_root` from workspace configuration;
- verify required paths and framework files;
- read the project marker and bridge index;
- identify the current machine and maintenance-writer role;
- check conflict-copy patterns, writer-registry agreement, named-file
  checksums, and schema compatibility;
- return an explicit activation receipt.

The receipt reports scope, query-first state, capture policy, allowed writes,
writer role, and degraded-state warnings.

Receipts and doctor output expose logical handles such as `wiki_root` and
`raw_root` plus `exists`, `readable`, and `writable` states. They never echo an
absolute path, Drive account path, device name, or private `storage_path`.

### 5.3 Session actions

The structured action surface adds:

- `rkf.activate`
- `rkf.status`
- `rkf.deactivate`

Any action that requires activation returns `RKF_NOT_ACTIVE` before performing
I/O when the session is off. `rkf.deactivate` immediately disables subsequent
automatic query and capture behavior.

The global `rkf-auto-connect` skill is part of the activation boundary. Phase
1 must replace its current automatic/legacy-CLI behavior with the structured
session actions. Because that skill is installed outside this repository,
editing it requires a separate filesystem approval during implementation. RKF
1.1 cannot be declared complete while the old skill can bypass `OFF`.

## 6. Cross-Project Query-First Retrieval

After activation, only research-relevant tasks invoke query-first retrieval.
Ordinary coding and administrative tasks continue normally.

Research relevance is deterministic in the first implementation. A request is
research-relevant when it contains a source identifier/citation or asks for
literature discovery, paper interpretation, cross-paper synthesis, research
method/experiment design, manuscript evidence, or scientific claim review.
The exclusions in Section 7.1 take precedence. An uncertain classification
does not query or capture automatically; the receipt offers the explicit
`問 RKF` or `收進 RKF` action instead.

The request flow is:

```text
user research request
  -> classify research relevance
  -> query.search central RKF
  -> return governed result cards
  -> inspect project-local files when central context is absent or incomplete
  -> reason over both with their provenance kept separate
```

The structured action surface adds read-only `query.search`.

Retrieval order:

1. exact source ID, DOI, arXiv/PubMed ID, title, alias, or page ID;
2. keyword and topic matching;
3. graph neighbors and page context;
4. maturity and evidence-boundary filters;
5. an optional local semantic index only after deterministic paths are
   validated.

Embeddings are not required for the first implementation. If later enabled,
they are a rebuildable local index and never become evidence.

Every result card includes:

- page path and type;
- match reason;
- reading or synthesis maturity;
- evidence boundary;
- claim readiness;
- missing PDF, locator, human feedback, or review state.

The result distinguishes central RKF knowledge from project-local material and
never presents a candidate, inbox item, hot-query record, route note, or ARS
report as stable evidence.

## 7. Activated Capture And Deduplication

The structured action surface adds `capture.route` as the single entrypoint for
cross-project capture.

It composes the existing `inbox.capture` and `hot.record` actions instead of
creating a parallel write path.

### 7.1 Trigger policy

Active source triggers:

- DOI, arXiv ID, PubMed ID, formal citation, paper title;
- research-focused URL used as a source;
- literature-search query or candidate paper list;
- public-safe web clip with provenance.

Aggressive research triggers:

- literature synthesis and comparison;
- method or experiment design;
- manuscript argument reasoning;
- research claim evaluation;
- reusable hypotheses, caveats, and open questions.

Excluded material:

- ordinary coding/debugging with no research value;
- secrets, credentials, personal data, and private paths;
- complete conversations, full articles, PDFs, and browser captures;
- low-value transient discussion.

Cross-project automatic capture applies only inside an activated Codex task.
RKF does not observe unrelated ChatGPT web/app conversations. Material from an
external GPT conversation enters RKF only when the user explicitly forwards,
pastes, or imports a public-safe excerpt, source list, share artifact, or
official export into an activated task. The capture receipt preserves that
external-conversation provenance.

### 7.2 Deduplication keys

Capture checks, in order:

- normalized formal identifier;
- canonical URL;
- normalized title plus year/author hints;
- public-safe content fingerprint;
- same-project query and intent recorded within the previous 24 hours.

The first implementation remains deterministic. Ambiguous title or source
matches produce a review proposal rather than merging records.

### 7.3 Capture destinations

- source/web/chat material -> uniquely named inbox/event object;
- paper-search demand -> hot-query event, later projected into `hot.md`;
- resolved source identity -> SourceRecord projection;
- paper backlink -> guarded identity link only;
- user/agent reading interaction -> reading event, later projected into the
  reading ledger;
- stable claim or synthesis -> never automatic.

Every capture first creates an immutable, uniquely named public-safe event. The
maintenance writer may materialize the relevant inbox, SourceRecord, hot, or
reading-ledger projection immediately; another machine leaves the event queued.
Every write returns a receipt with event ID, destination, queued/materialized
state, trigger reason, deduplication result, and an explicit statement that no
stable knowledge was promoted.

## 8. Paper-Centered Knowledge Model

### 8.1 Three knowledge layers

RKF distinguishes:

| Layer | Objects | Meaning |
|---|---|---|
| Capture | inbox and candidates | unclassified or provisional material |
| Reading | paper pages and reading ledgers | what a source contains and how much has been read |
| Knowledge | concept, claim, synthesis, topic | reviewed, reusable maintained knowledge |

### 8.2 Canonical paper page

The paper template becomes:

```markdown
# Paper Title

## Source Identity

## Reading Maturity

## Research Question

## Methods And Data

## Main Findings

## Evidence And Locators

## Limitations And Boundaries

## Questions About This Paper

## Future Agent Retrieval Brief

## Intrinsic Links
```

Paper-page rules:

- The page describes the paper, not a current project or manuscript.
- Source-grounded statements must trace to the source or a locator.
- `Questions About This Paper` contains only questions about this paper's
  method, data, results, figures, assumptions, limitations, and
  reproducibility.
- User and AI reading interactions remain in the reading ledger by default.
- Only reviewed, paper-specific clarification is integrated into the page.
- `Intrinsic Links` contains concepts, methods, datasets, and subject topics
  intrinsic to the paper.
- Project, manuscript, and cross-paper relationships point toward the paper;
  they do not require the paper to point back.

### 8.3 Content routed out of paper pages

| Content | Destination |
|---|---|
| manuscript use or citation role | `project-synthesis` page |
| cross-paper judgment | synthesis page |
| broader research curiosity | question page |
| tentative hypothesis or idea | inbox |
| user and AI reading interaction | reading ledger |
| project-to-paper relationship | `project-synthesis` page plus backlink/graph edge |

Obsidian backlinks and the RKF graph expose these incoming relationships
without changing the paper's center of gravity.

### 8.4 Incoming relationship contract

`project-synthesis`, `synthesis`, `question`, and `overview` pages may point to
paper pages with a portable relation contract:

```yaml
paper_relations:
  - paper_id: papers/example-paper
    relation: uses-paper
```

`paper_id` is the canonical node ID relative to `knowledge/`, without the
`.md` suffix. Allowed relation values are `uses-paper`, `compares-paper`,
`extends-from-paper`, and `discusses-paper`.

Each structured relation must also have a standard relative Markdown link in
the page body, for example:

```markdown
- [Example Paper](../papers/example-paper.md) — role in this project
```

Standard Markdown keeps the files portable and causes Obsidian Backlinks to
show the incoming relationship. The graph builder reads `paper_relations` and
emits the same directed edge from the external page to the paper. Lint rejects
an unknown relation, missing paper target, or missing body link. Paper pages do
not need reciprocal project links.

### 8.5 Frontmatter

The complete paper maturity contract includes:

```yaml
schema: rkf-paper-v1.1
type: paper
status: draft
source_id: doi_example
source_status: paper_draft
reading_state: metadata-only
reading_status: metadata-only
fulltext_status: needs-user-pdf
human_feedback_level: none
understanding_confidence: low
claim_readiness: not-ready
review_stage: ai-extracted
evidence_boundary: review-blocker
evidence_tier: reading-draft
evidence_ids: []
reading_ledger: state/reading/doi_example.json
topics: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
```

`reading_state` is canonical. `reading_status` is a deprecated compatibility
mirror during RKF 1.1 and must equal `reading_state`; a later schema release may
remove it after all runtime consumers migrate. `last_reading_interaction` is
present only when a verifiable event exists and must match the most recent
ledger event date. The schema, template, linter, runtime, and migration tool
must agree on these fields before the 57-page preview.

Intrinsic topic assignment must reflect the paper itself. Project-specific
associations live outside the paper page.

## 9. Fifty-Seven-Paper Golden-Corpus Migration

The current 57 pages form the complete migration test corpus.

The structured migration surface is `paper.migration.preview`,
`paper.migration.apply`, and `paper.migration.rollback`. Preview is read-only
with respect to live wiki paths. Apply requires the approved manifest hash.

### 9.1 Preview workflow

1. Inventory all 57 pages and record checksums.
2. Copy them into a temporary, non-live test workspace.
3. Apply a pure paper-centered transform to all copies.
4. Produce one diff per page and a corpus summary.
5. Produce an extraction proposal manifest for content routed out of paper
   pages.
6. Run schema, section, graph, public-safety, and private-path checks.
7. Present representative diffs and the full summary for user review.
8. Do not modify the live wiki until a separate approval.

The private inventory generates a deterministic migration-pattern catalog for
known project/manuscript headings and structured blocks. A block is moved
automatically only when it matches that catalog. Ambiguous prose remains in
the preview output, receives `needs-human-routing` in the manifest, and blocks
live application until reviewed. A paper-specific question is limited to the
current source's method, data, results, figures, assumptions, limitations, or
reproducibility; broader questions receive the same review/routing treatment.

### 9.2 Preservation requirements

The transform preserves without scientific rewriting:

- title, DOI, source ID, authors, journal, and year;
- source and evidence references;
- source-grounded summary, methods, findings, and limitations;
- page, section, figure, and term locators;
- supported and unsupported claim boundaries.

The transform may move existing blocks and normalize headings. It must not
silently delete content.

Every removed or moved block records:

- source page;
- source heading and content hash;
- classification reason;
- proposed target object;
- review status.

### 9.3 Conservative maturity mapping

Legacy `reading_status` values map deterministically into the new
`reading_state` and `fulltext_status` fields. Migration sets
`human_feedback_level: none` unless a verifiable reading interaction exists.
It does not infer a trust upgrade or `claim-ready` state merely because a page
was migrated.

Each page receives a migration ledger event that records the old state, new
state, transform version, and lack of automatic promotion. Reading-ledger
schema v1.1 adds the currently emitted `inbox-injection` event plus a
`migration` event. During preview, migration events are written only to copied
ledgers in the temporary workspace. The live ledger remains untouched.

### 9.4 Golden assertions

- 57 input pages produce 57 output pages.
- Required source identity and locator content is preserved.
- No output page contains a block classified as project- or
  manuscript-centered by the private migration-pattern catalog.
- Every routed block exists in the proposal manifest.
- Paper-specific questions remain; broader questions are proposed for question
  pages.
- No `needs-human-routing` item remains before live application.
- New pages satisfy the paper section and frontmatter contract.
- No live path is written during preview.

### 9.5 Live application and rollback

Immediately before live application, RKF rereads all 57 inputs and compares
their checksums with the reviewed preview manifest. Any added, removed, or
changed page invalidates the approval and stops the apply.

After that drift guard passes, RKF creates a one-time private backup under the
configured raw backup area and records original/output checksums plus an apply
journal. The backup is never indexed, linked into Obsidian, or used as a second
wiki. Each page is staged, validated, and atomically replaced; the journal
records every completed replacement.

Any apply or post-apply validation failure triggers rollback of all replaced
pages from the backup. `paper.migration.rollback` is also available while the
backup exists. Rollback is complete only when every restored page matches its
original checksum and the full live validation passes. Backup deletion remains
a separate approved cleanup step.

Live migration requires a dedicated user approval tied to the exact preview
manifest hash after golden-corpus review.

## 10. Multi-Computer Safety

Per-machine ignored configuration includes:

```toml
[machine]
id = "machine-id"
maintenance_writer = false

[sync]
atomic_writes = true
conflict_detection = true
```

Exactly one machine is the designated maintenance writer for aggregate files.

The canonical operational state contains a small shared writer registry with
an opaque machine ID, role-assignment time, and schema version. It contains no
private path or device name. Changing the registered writer is an explicit
setup operation, not an automatic election. `connect.doctor` compares the
local ignored setting with this registry, so a second writer is rejected
instead of inferred from inaccessible per-machine files.

All interactive machines may query and create uniquely named append-only events
under `state/events/YYYY-MM-DD/` in the shared operational event queue. Event
IDs combine timestamp, opaque machine ID, and a random nonce; an idempotency
key prevents duplicate folding. The event envelope records schema version,
event ID, action, actor, origin, created time, public-safe payload, target
identity, and idempotency key. Events are operational provenance, not claim
evidence.
Non-writer machines do not directly update SourceRecords, consolidated reading
ledgers, `hot.md`, `index.md`, graph exports, generated views, or scheduled
reports. The maintenance writer folds queued events into those named
projections and records the last folded event/checksum.

Named-file writes use an expected-input checksum, a temporary sibling file,
flush, atomic rename, and post-write checksum verification. A changed expected
checksum aborts the materialization. Atomic rename prevents partial files;
single-writer enforcement and checksum comparison prevent lost updates.

The read-only `connect.doctor` action checks:

- workspace and source roots;
- machine identity and writer-role uniqueness;
- whether configured roots exist and a read probe succeeds (without claiming
  that Drive cloud synchronization itself is current);
- conflict-copy filename patterns;
- same-DOI/different-checksum PDFs;
- stale aggregate files;
- schema-version compatibility.

For doctor output, a conflict means any Drive conflict-copy pattern,
same-identity/different-checksum object, unexpected named-file checksum,
writer-registry mismatch, or incompatible schema. An aggregate is stale when
its `generated_at` exceeds twice its configured cadence; the default daily
cadence therefore becomes stale after 48 hours. Tests use an injected clock.

Conflict detection never silently picks a winner. A conflict changes the
session to `ACTIVE_READ_ONLY` until reviewed.

PDFs are treated as immutable after identity verification. A changed binary
under an existing source identity creates a blocker rather than overwriting the
registered artifact.

## 11. Obsidian View Layer

Each computer uses a local view vault:

```text
Local RKF-Obsidian/
├── .obsidian/
└── wiki/ -> configured Google Drive wiki root
```

macOS uses a symlink and Windows uses a junction. These links and
`.obsidian/` settings are machine-local and are not committed or synced in the
canonical data root.

The first implementation uses Obsidian core features only:

- Backlinks;
- Local Graph;
- Properties;
- Bases;
- Search and Outline.

Canonical, public-safe generated view artifacts live in:

```text
wiki/views/
├── papers.base
├── reading-queue.base
├── inbox.base
├── questions.base
└── synthesis.base
```

These views derive entirely from Markdown properties. A future Smart
Connections pilot may add local semantic related-note suggestions, but it must
remain optional, local, and non-authoritative.

## 12. User-Facing Vocabulary

The normal interface is natural language:

```text
啟動 RKF
問 RKF：...
收進 RKF：...
我讀完／註解了這篇...
今天 RKF 要處理什麼？
停用 RKF
```

After activation, ordinary research conversation can invoke query-first and
capture automatically. Explicit phrases remain available when the user wants
predictable control.

Query answers return a compact research card containing:

- the answer;
- matched pages and evidence/maturity state;
- unsupported or missing evidence;
- RKF actions taken;
- an explicit promotion statement.

Capture returns a receipt containing destination, reason, deduplication result,
and `Promotion: none` unless the user separately approves a governed promotion.

## 13. Scheduled Maintenance

Interactive activation and scheduled maintenance are independent.

Automations are disabled by default. They are created or enabled only after the
user explicitly says `啟用 RKF 定期維護` and approves the target machine,
prompt, schedule, and allowed writes.

Approval of this design or of earlier implementation phases does not authorize
even a paused automation to be created. Creation is itself an external-state
write and has its own review gate; activation has a later, separate gate.

Daily maintenance by the designated writer:

- inspect already-provided `raw/incoming/` artifacts;
- deduplicate by checksum and identity;
- create conservative inbox/SourceRecord candidates;
- refresh hot demand and index outputs;
- report conflicts, failed ingest, and pending review;
- never promote stable knowledge.

Weekly maintenance:

- structure, evidence, graph, and public-safety lint;
- broken links, orphan pages, and duplicate sources;
- paper reading queue;
- stale hot demand and unreviewed inbox;
- read-only health report.

Monthly maintenance:

- topic merge/split/staleness proposals;
- synthesis coverage and maturity review;
- legacy migration status;
- raw PDF checksum audit;
- cleanup dry-run.

The two current paused automations are not reactivated. They enter the cleanup
or replacement review because one has stale naming/intent and the other points
to an obsolete checkout and missing script.

## 14. Safe Cleanup

Cleanup starts with a read-only removal manifest. Every entry records:

- exact path or automation ID;
- reason and owner;
- references discovered;
- replacement or archive destination;
- risk and rollback method;
- dry-run result;
- approval status.

Initial candidates:

- ignored `.DS_Store`, `__pycache__`, and `.pyc` artifacts;
- six unreferenced duplicate manual images;
- empty `raw/full_txt/`;
- stale root `log.md` content describing retired architecture;
- completed Superpowers plans/specs for archival or ADR consolidation;
- paused and obsolete RKF automations.

Explicitly retained:

- `tools/rk.py` and `rkf/cli.py` as compatibility/test shims;
- schemas, templates, and tests;
- live wiki and raw PDFs;
- the example's canonical screenshots;
- Git history and research source records.

No cleanup applies automatically. Each exact deletion or archive batch requires
user approval, reference scanning, and post-change validation.

## 15. Implementation Boundaries

New behavior should not enlarge `rkf/core.py` indiscriminately. The intended
module responsibilities are:

- `rkf/session.py`: activation state, preflight, and receipts;
- `rkf/retrieval.py`: deterministic query-first search and result cards;
- `rkf/capture.py`: routing, trigger policy, and deduplication;
- `rkf/paper_migration.py`: pure paper-page transforms and manifests;
- `rkf/sync.py`: atomic writes, writer roles, and connection doctor;
- `rkf/views.py`: index and Obsidian Bases generation;
- `rkf/actions.py`: structured dispatch and permission boundary;
- `schemas/knowledge_object.schema.json`: paper v1.1 fields and incoming
  `paper_relations`;
- `schemas/reading_ledger.schema.json`: v1.1 event vocabulary;
- a new operational-event schema: immutable queue envelope and idempotency
  contract;
- `tools/rkf_auto_connect.py`: thin compatibility/helper surface;
- `rkf/cli.py`: legacy/dev shim only.

The installed global `rkf-auto-connect` skill must route only through these
structured actions and honor session `OFF`; it is an external implementation
surface requiring separate write permission. Exact file creation and
extraction scope is finalized in the implementation plan after code-level
dependency review.

## 16. Error Handling

Required failures are explicit and non-destructive:

- missing connector or workspace config -> activation fails with setup guidance;
- unavailable `wiki_root` or `raw_root` -> activation fails;
- conflict or incompatible schema -> `ACTIVE_READ_ONLY`;
- ambiguous source identity -> review proposal, no merge;
- duplicate identifier with differing binary checksum -> evidence blocker;
- migration parse failure -> original file unchanged and failure recorded;
- required section or public-safety failure -> no live migration;
- non-writer aggregate rebuild -> rejected;
- deactivated session -> `RKF_NOT_ACTIVE` before I/O.

No failure falls back to another database, silently drops content, bypasses
evidence boundaries, or weakens validation.

## 17. Testing Strategy

### 17.1 Unit tests

- activation state transitions and receipts;
- v1/v2 marker compatibility;
- query search ordering and evidence filters;
- capture trigger classification and deterministic deduplication;
- pre-activation I/O rejection;
- version-1 markers remain available but never active;
- deactivation behavior;
- activation/doctor output path redaction;
- immutable event envelope, idempotent folding, checksum compare-and-swap, and
  writer-role checks;
- paper-page parsing, routing, and lossless transforms;
- `paper_relations` validation and directed graph edges;
- Obsidian view generation.

### 17.2 Integration tests

- activate -> query -> capture -> receipt -> deactivate;
- outside-project activation with global connector resolution;
- invoking the global auto-connect skill while `OFF` produces zero wiki/raw
  I/O and never falls back to the legacy CLI;
- unavailable Drive and conflict degradation;
- two simulated maintenance writers;
- two machines concurrently submit the same DOI and reading feedback without
  directly rewriting the same SourceRecord or ledger;
- same DOI with equal and unequal checksums;
- generated Bases and backlinks over a fixture wiki;
- cleanup manifest with referenced and unreferenced artifacts.

### 17.3 Golden-corpus tests

Normal CI uses sanitized fixtures that cover each legacy section/routing class,
the manifest format, drift rejection, partial-apply rollback, and checksum
verification. The complete 57-page run is a private local acceptance action:
it resolves the configured live root, copies inputs into a temporary workspace,
and writes only an ignored report containing checksums and diffs. The
assertions in Section 9 are required before any live write.

### 17.4 Repository validation

Every implementation phase runs:

- focused unit tests;
- full unit-test discovery;
- Python compilation;
- RKF all/topic/graph lint as applicable;
- public-safety and private-path scans;
- `git diff --check` and scoped diff review.

## 18. Rollout Gates

The release is divided into independently reviewable phases:

1. Activation, query-first retrieval, and capture closure.
2. Fifty-seven-paper golden preview and migration report.
3. Separate approval for live paper migration.
4. Multi-computer doctor and Obsidian view layer.
5. Automation creation in paused state.
6. Separate approval for automation activation.
7. Cleanup manifest.
8. Separate approval for every deletion/archive batch.

The user reviews each gate. A later phase cannot broaden the authorization of
an earlier phase.

## 19. Acceptance Criteria

RKF 1.1 is complete only when:

- a new session performs zero RKF query/capture before activation;
- activation reports exact scope, policy, and writer state;
- activated research tasks query central RKF before local project material;
- source leads and reusable research discussion enter conservative,
  deduplicated capture paths with receipts;
- an external GPT conversation can be explicitly forwarded or imported with
  provenance, but is never silently monitored;
- paper pages are centered on their source and contain only paper-specific
  questions;
- project/manuscript use is discoverable through incoming links without
  changing paper-page focus;
- all 57 pages pass the golden-corpus preservation and routing checks;
- no Drive conflict is silently overwritten;
- Obsidian remains a view rather than a second database;
- scheduled work cannot promote stable knowledge;
- cleanup is manifest-driven, reversible, and explicitly approved;
- the full repository validation suite passes.
