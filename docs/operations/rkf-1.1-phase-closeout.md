# RKF 1.1 Phase Closeout

Date: 2026-07-15
Status: v1.1 release candidate validated; cleanup and backup-removal gates remain

## Completed

- Phase 1: canonical schema/runtime/template gate plus a private 57-paper
  `access_state` / `review_state` preview; all 64 deprecated discovery
  candidates are classified as isolated candidate-only records.
- Phase 2: v2 ProjectConnection validation, OFF-by-default activation,
  append-only ActivationEvent/ActionEvent lineage, idempotency, redaction, and
  object-origin/timeline lookup.
- Phase 3: default runtime and install surface restricted to Connect & Activate
  plus Add, Ask, Read, Compare & Synthesize, and Review. Compatibility actions
  require an explicit internal/legacy flag.
- Phase 4: locator-backed Evidence, evidence-linked Claim and Synthesis,
  evidence matrices, scope-gated Read passes, and optional full-text,
  appraisal, and retrieval adapters with `Promotion: none`.
- Phase 5: actionable private Review/Home and a synthetic/public-safe guided
  Paper → Evidence → Claim → Synthesis site with mobile navigation.
- Phase 6: canonical schema, docs, attribution, unit/integration tests,
  semantic gates, lint, public-safety scan, and release notes.
- Final hardening: Read requires a schema-valid canonical Paper and a scope no
  broader than its `access_state`; Claim and Synthesis revalidate Evidence
  fingerprints and successful ActionEvent receipts; public-safe Ask accepts
  only validated canonical objects and semantic hits with explicit scope and
  locators; read-only Ask skips the shared retrieval-run write but retains its
  private ActionEvent; checksum artifacts retain all `paper_ids` / `source_ids`;
  canonical state, retrieval runs, artifacts, Review reads, and lineage fail
  closed on path escape or symlink boundaries; and private artifact/lineage
  storage is owner-only.
- Final release-candidate validation passed 372 tests on Python 3.9 and 3.12,
  canonical schema validation, topic/all/graph lint, public-safety scan,
  exact-snapshot site validation, install parity, and diff checks.
- The explicitly approved migration manifest
  `bb4ef62bcb0c533bf023838f9468b180dcb36441da8f674789cbf5405e340aff`
  was applied atomically to all 57 paper pages and 57 reading ledgers. The
  114-entry private backup journal remains available for exact rollback; all
  live outputs and backup records passed post-apply checksum verification.

## Rollback-window exit criteria

The backup may leave the rollback window only after all of the following are
true:

1. The released commit passes the canonical schema gate, full test suite,
   lints, and public-safety scan.
2. The 57 paper outputs, 57 reading ledgers, and all 114 backup-journal records
   still match their recorded checksums, with no migration finding requiring
   rollback.
3. The maintainer records the observation-window end and confirms that no
   rollback request is open. No duration is assumed until that date is
   explicitly approved.
4. A new cleanup manifest names the exact backup ID, consequence of deletion,
   and recovery limit, and the user approves that exact manifest hash.

Passing the release checks does not itself authorize deleting the backup.

## Remaining Approval Gates

1. Review the migrated live state while retaining backup
   `paper-v1.1-bb4ef62bcb0c533bf023838f9468b180dcb36441da8f674789cbf5405e340aff`
   through the rollback window.
2. Approve one exact cleanup batch. Cache files, unreferenced duplicate assets,
   and legacy paused automations must not be deleted together implicitly; keep
   retained/reference-backed entries unchanged.

Backup deletion is a later cleanup decision after the rollback window and
requires the exact-manifest approval above.
