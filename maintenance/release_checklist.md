---
type: maintenance
status: draft
source_status: personal-note
reading_status: mixed
review_stage: discussed
topics: []
subtopics: []
keywords: [github_release, privacy_check]
created: 2026-05-21
updated: 2026-05-21
sources: []
---

# GitHub Release Checklist

Run this before publishing the repository.

## Required Checks

- Run `python3 tools/wiki_lint.py`.
- Run `python3 tools/wiki_doctor.py`.
- Run `python3 tools/generate_repair_plan.py`.
- Search for absolute local home-directory paths.
- Ensure `.DS_Store` files are not tracked.
- Ensure private PDFs, raw datasets, and personal notes are not accidentally committed.
- Confirm `raw/full_text/` policy before publishing full text.
- Confirm `skills/THIRD_PARTY_NOTICES.md`.
- Confirm `LICENSE` and `CONTRIBUTING.md`.

## Safe Cleanup Rules

- `wiki_doctor.py` and repair plans only diagnose release hygiene; they must not delete files.
- For `.DS_Store`, review each exact path and remove only one explicit file at a time after human review.
- Do not use recursive, wildcard, or bulk cleanup commands to make the release checklist pass.
- Preserve raw evidence by default; clean the dashboard or index to match evidence, not the other way around.

## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects: [[project_synthesis/project_synthesis]]
