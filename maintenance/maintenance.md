---
type: maintenance
status: draft
source_status: personal-note
reading_status: mixed
review_stage: discussed
topics: []
subtopics: []
keywords: [health_check, repair_plan, release_checklist]
created: 2026-05-21
updated: 2026-05-21
sources: []
---

# Maintenance

Maintenance files track database health, repair plans, release checks, Codex handoff logs, and Obsidian graph hygiene. They live outside `wiki/` so they do not become formal knowledge pages or Obsidian graph nodes.

## Routine

- Run `python3 tools/wiki_lint.py` for strict structural checks.
- Run `python3 tools/wiki_doctor.py` for health diagnostics.
- Run `python3 tools/generate_repair_plan.py` to create a human-readable repair plan.
- Never batch-delete files automatically.

## Guides

- `maintenance/obsidian_graph_guide.md`
- `maintenance/release_checklist.md`

## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects: [[project_synthesis/project_synthesis]]
