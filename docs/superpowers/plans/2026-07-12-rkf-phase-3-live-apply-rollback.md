# RKF Phase 3 Live Apply And Rollback Implementation Plan

Date: 2026-07-12
Status: Implemented and fixture-verified; live execution remains approval-gated

## Goal

Apply one reviewed paper-migration preview only when its exact manifest hash is
approved and every live input checksum still matches. Preserve a private,
non-indexed backup and journal so any partial failure rolls back automatically
and an explicit rollback can later restore exact original bytes.

## Implemented Contract

- `paper.migration.apply` requires an active designated writer, a healthy
  `connect.doctor`, an explicit private report directory, and the exact reviewed
  manifest hash.
- Apply rejects changed, added, missing, unsafe, unvalidated, or checksum-
  mismatched paper outputs before creating a backup.
- Original pages and pre-existing reading ledgers are copied under
  `raw/migration_backups/<backup-id>/`; newly created ledgers are marked as
  originally absent.
- Every target uses a sibling temporary file, flush/fsync, atomic replace, and
  post-write checksum verification.
- The apply journal records pending/applied state per exact target. Any failure
  restores all applied targets in reverse order and records the rollback result.
- `paper.migration.rollback` requires the exact backup ID and matching manifest
  hash, then verifies every restored or removed target.
- No claim promotion occurs. Backup deletion is not implemented.

## Execution Gate

Implementing and testing these actions does not authorize their use against the
live 57-paper corpus. Live apply still requires an explicit approval that names
the reviewed manifest hash. Backup deletion remains a later cleanup batch.
