# RKF v1 Optional Provider Contracts

RKF v1 remains usable with no optional provider. The deterministic core owns
canonical objects, evidence boundaries, and project/activation lineage.
Providers may improve acquisition, appraisal, or retrieval, but they cannot
promote trust.

## Full text in Add

`workflow.add` accepts `operation: acquire` only when the task runtime has an
explicitly configured `FullTextProvider`. Results use one of:

- `obtained`
- `manual-required`
- `unavailable`
- `retryable`
- `blocked`

`retryable` is never rewritten as `unavailable`. An obtained artifact requires
a SHA-256 digest and explicit `%PDF` magic-byte validation. The public record
keeps the artifact ID, digest, provider, route, and readiness state; any local
artifact handle stays under `.rkf_private/`. Registration deduplicates one
artifact per checksum while canonical `paper_ids` / `source_ids` arrays retain
every relation. The legacy singular fields remain compatibility mirrors of the
current registration. A symlink at the private root, artifact parent, or
target fails closed before the handle is written. Private artifact directories
and handle files are restricted to owner-only `0700` and `0600` permissions.

The included external-command adapter is a minimal `shell=False` JSON bridge.
It does not configure a browser, institution, credential, or publisher route.
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

Structured substantive findings require exact locators and become canonical
Evidence cards tied to the Paper, lineage, and a content fingerprint. Claim and
Synthesis creation reloads those cards and revalidates schema, ID, Paper,
locator, stance, verification state, lineage, public-safe status, and content
fingerprint. Evidence, Claim, and Synthesis fingerprints must also match a
successful ActionEvent object receipt from the same project and activation.
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
  object plus a non-empty locator/section;
- are rejected unless they explicitly declare `index_scope: public-safe` for a
  public-safe query; returned title, summary, and path are rebuilt from
  canonical state rather than provider text;
- produce a path-redacted `retrieval_run_id` tied to project, activation, and
  the actual result fingerprint;
- safely fall back to deterministic Ask when the provider fails or is absent.

Changed result cards, scores, provider generation, or answer boundary create a
new retrieval run and append-only lineage successor; an identical result
deduplicates. An `ACTIVE_READ_ONLY` Ask skips the shared retrieval-run write but
still records a private, path-redacted ActionEvent for the action and its
affected canonical object IDs. Retrieval-run state and canonical collection
reads use contained, no-follow paths; malformed, drifted, non-public-safe, or
receipt-less Evidence/Claim/Synthesis records cannot raise the answer boundary.

Provider similarity, route success, or appraisal output does not raise
Evidence verification or Claim status.

`ExternalCommandRetrievalProvider` is the shell-free structured boundary for
an optional local semantic index. The external provider owns section-aware
chunking, content-hash incremental rebuilds, ghost-result pruning, and atomic
READY generations under private storage; RKF persists only generation,
latency, canonical result IDs, scores, and lineage.
