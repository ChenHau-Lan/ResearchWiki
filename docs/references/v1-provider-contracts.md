# RKF v1 Optional Provider Contracts

Issue #18's current vNext portable-core slice is documented separately in
[`vnext-acquisition.md`](vnext-acquisition.md). It preserves this v1 evidence
boundary while adding portable OA routes, artifact/version QC, acquisition-run
lineage, and an optional external institutional bridge. It neither completes
the issue's institutional-adapter inventory nor adds a new user-facing
workflow.

RKF v1 remains usable with no optional provider. The deterministic core owns
canonical objects, evidence boundaries, and project/activation lineage.
Providers may improve acquisition, appraisal, or retrieval, but they cannot
promote trust.

## Full text in Add

`workflow.add` accepts `operation: acquire` only when the task runtime has an
explicitly configured `FullTextProvider`. Results use one of:

- `obtained`
- `manual-required`
- `retryable`
- `not-entitled`
- `unavailable`
- `blocked`
- `identity-mismatch`
- `invalid-artifact`
- `provider-error`

These nine values are the canonical final provider statuses in
`schemas/rkf_v1.schema.json`. Route-level attempts may additionally use
`resolved` or `no-result`; neither means that a full-text artifact was
obtained.

`retryable` is never rewritten as `unavailable`. An obtained artifact requires
a SHA-256 digest and explicit `%PDF` magic-byte validation. The public record
keeps the artifact ID, digest, provider, route, and readiness state; any local
artifact handle stays under `.rkf_private/`. Registration deduplicates one
artifact per checksum while canonical `paper_ids` / `source_ids` arrays retain
every relation. The legacy singular fields remain compatibility mirrors of the
current registration. A symlink at the private root, artifact parent, or
target fails closed before the handle is written. Private artifact directories
and handle files are restricted to owner-only `0700` and `0600` permissions.
The standalone acquisition smoke helper uses a separately supplied private or
temporary boundary and rejects output inside the repository, symlinked output,
and overwrite attempts. It does not place test PDFs under the checkout.

The included external-command adapter is a minimal `shell=False` JSON bridge.
It does not configure a browser, institution, credential, or publisher route,
and the core does not implement SSO/CAPTCHA bypass. Such surfaces must stop as
a manual handoff in the external machine-local workflow.
An obtained result also updates the existing canonical Paper to
`access_state: fulltext`; missing Paper records fail closed before acquisition.

## Digest and appraisal in Read

`workflow.read` supports `intent: digest | appraise | both` with an explicit
`reading_scope`.

- Read requires an existing `rkf-paper-v1.1` Paper with valid access and review
  state; requested scope cannot exceed the Paper's `access_state`.
- Digest requires `fulltext`; otherwise it stops with
  `RKF_READ_NEEDS_FULLTEXT`.
- Abstract-only appraisal stays low-trust and cannot create human-verified
  Evidence.
- Citation existence and citation support are separate checks.
- Failed external checks remain visible.
- Generic deterministic rules flag association-to-causation,
  surrogate-to-hard-outcome, single-study-to-consistency,
  subgroup/secondary-to-general-benefit, and mechanism/opinion-to-outcome
  gaps.

Structured observations may first become `rkf-finding-v1` FindingDrafts with a
`missing`, `coarse`, or `exact` locator state. Missing/coarse drafts stay in the
Review locator-debt queue and cannot support a Claim. Only an exact,
receipt-backed FindingDraft can be promoted into the existing canonical
Evidence format; the direct exact-locator Evidence route remains compatible.
Claim and Synthesis creation reloads Evidence cards and revalidates schema, ID,
Paper, locator, stance, verification state, lineage, public-safe status, and
content fingerprint. FindingDraft, Evidence, Claim, and Synthesis fingerprints
must also match a successful ActionEvent object receipt from the same project
and activation.
Directly editing an Evidence or Claim to raise trust therefore fails closed.
Canonical state and Review reads reject path escape and symlink boundaries.
Appraisal flags and failures remain a Read run until a human maps
source-backed material into Evidence or a Claim blocker.
Optional domain profiles return only typed public-safe flags, warnings, and
failure codes; they cannot change verification state.

## Optional retrieval in Ask

`workflow.ask` always runs exact identity/title/alias and deterministic keyword
retrieval before optional semantic hits. Semantic hits:

- never override exact results;
- must declare the requested index scope and point to an existing canonical
  object;
- are rejected unless they explicitly declare `index_scope: public-safe` for a
  public-safe query; returned title, summary, and path are rebuilt from
  canonical state rather than provider text;
- may omit a provider locator when retrieving canonical source context; that
  card remains context-only and not claim-ready. Supplying a provider locator
  never upgrades the canonical object's trust label;
- produce a path-redacted `retrieval_run_id` tied to project, activation, and
  the actual result fingerprint;
- safely fall back to deterministic Ask when the provider fails or is absent.

`answer_policy: context-ok` is the default and reports `answer_mode` as
`no-results`, `context-only`, `mixed`, or `evidence`. `evidence-only` retains the
strict formal-support gate while leaving governed context visible for
inspection. Stage timing is diagnostic only and is excluded from retrieval and
lineage identities.

Changed result cards, scores, provider generation, or answer boundary create a
new retrieval run and append-only lineage successor; an identical result
deduplicates. An `ACTIVE_READ_ONLY` Ask skips the shared retrieval-run write but
still records a private, path-redacted ActionEvent for the action and its
affected canonical object IDs. Retrieval-run state and canonical collection
reads use contained, no-follow paths; malformed, drifted, non-public-safe, or
receipt-less Evidence/Claim/Synthesis records cannot raise the answer boundary.

The v1.2 audit policy remains compatible: an active writable Ask persists its
retrieval run and may refresh the derived query projection; an
`ACTIVE_READ_ONLY` Ask writes neither of those shared artifacts. Both still
record the required private ActionEvent. Query-index and persistence controls
are runtime-owned rather than user-supplied workflow parameters.

Provider similarity, route success, or appraisal output does not raise
Evidence verification or Claim status.

The deterministic query index is separate from the optional semantic provider.
It is a versioned, fingerprint-backed SQLite projection under private storage.
Canonical candidates are ranked into an oversampled window and then reloaded
from source with their fingerprints and receipts. A stale, corrupt, tampered,
disabled, or symlinked projection falls back to the deterministic source scan;
deleting it never changes canonical data.
The reproducible zero-network contract and reference observation are recorded
in [the Ask scaling baseline](../benchmarks/ask-v1.2.md).

`ExternalCommandRetrievalProvider` is the shell-free structured boundary for
an optional local semantic index. The external provider owns section-aware
chunking, content-hash incremental rebuilds, ghost-result pruning, and atomic
READY generations under private storage; RKF persists only generation,
latency, canonical result IDs, scores, and lineage.
