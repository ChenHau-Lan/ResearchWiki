# RKF 1.1 Phase Closeout

Date: 2026-07-12
Status: Framework phases implemented; three live approval gates remain

## Completed

- Phase 1: task-local activation, deterministic query-first retrieval,
  event-first capture, designated-writer projection, and `Promotion: none`.
- Phase 2: private 57-paper golden preview, canonical paper-v1.1 transform,
  copied ledgers, routing manifest, per-page diffs, and drift-auditable hash.
- Phase 3: approval-bound apply/rollback implementation with private backup,
  journal, atomic replacement, checksum verification, and automatic rollback.
- Phase 4: path-redacted `connect.doctor`, atomic named-file writes, Obsidian
  Base preview/generation, and incoming `paper_relations` graph/lint support.
- Phase 5: daily/weekly/monthly maintenance plans and receipts with no
  promotion, plus read-only cleanup inventory and manifest generation.
- Phase 6: `rkf-maintenance-preview` created and verified in `PAUSED` state.
- Phase 7: cleanup manifest generated under ignored local private reports.

## Remaining Approval Gates

1. Register one opaque machine ID as the shared maintenance writer. Until this
   is done, doctor remains blocked and canonical writer actions stay disabled.
2. Approve the exact private paper-migration manifest hash before live apply.
   Recheck all 57 input checksums immediately before application.
3. Approve one exact cleanup batch. Cache files, unreferenced duplicate assets,
   and legacy paused automations must not be deleted together implicitly; keep
   retained/reference-backed entries unchanged.

Automation activation is a separate decision after the machine/writer doctor
passes. Backup deletion is a later cleanup decision after the rollback window.
