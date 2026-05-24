---
name: audit-release
description: Compatibility alias for advanced Research Wiki maintenance. Prefer wiki-lint for public lint, repair, and graph/state checks.
---

# Audit Release

Audit Release is retained as a compatibility alias for advanced maintenance.
The public health-check skill is `wiki-lint`.

## Modes

- `semantic-audit`: compatibility name for `wiki-lint/semantic-lint`.
- `runtime-state-graph`: compatibility name for `wiki-lint/state-graph`.
- `release-hygiene`: compatibility name for `wiki-lint/repair-plan`.
- `support-report`: advanced support mode for redacted support reports.
- `feedback-issue`: advanced support mode for human-confirmed issue drafts.

## Rules

- Prefer `core/skills/wiki-lint/SKILL.md` for lint behavior.
- Repair plans diagnose and suggest; they do not delete files.
- Do not use recursive, wildcard, or bulk deletion.
- Redact local paths, private PDFs/full text, sensitive DOI lists, and Codex
  logs from support artifacts.
- Semantic audit does not directly rewrite formal wiki pages; use
  Knowledge Workbench Save or approved fan-out for fixes.
