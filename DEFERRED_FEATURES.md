# Deferred Features

These features were removed from the active workflow to keep the research wiki simple for new users.

## Sync Across Computers

Old idea: use Git or scheduled scripts to sync the whole database across machines.

Deferred reason: research data changes often and creates conflicts. The active template should first be easy to install and operate through Codex. Future sync should be designed separately, likely with Git for rules/tools and a storage layer for data.

## Sub Databases / Sandboxes

Old idea: create linked secondary databases for writing projects or sandboxes.

Deferred reason: it adds path, ownership, and merge complexity. For now, keep one canonical database and use Codex context for project-specific discussion.

## Notion Dashboard

Old idea: mirror reading status into Notion.

Deferred reason: it creates another source of truth. The active DOI status board is `raw/doi_dashboard.md`.

## Code Wiki

Old idea: maintain `wiki/code/` pages for code logic, plotting logic, and implementation notes.

Deferred reason: the simplified template is for papers, meetings, and seminars only.

## Inbox

Old idea: capture random thoughts, images, videos, and unverified observations in `inbox/`.

Deferred reason: it makes the first-time workflow too broad. Meeting/seminar records can capture structured discussion, and DOI-like items should go to `raw/doi_list.md`.

## Candidate Registry

Old idea: keep a detailed `raw/candidates/literature_candidates.md` table.

Deferred reason: DOI intake and status are now split into `raw/doi_list.md` for new DOI input and `raw/doi_dashboard.md` for progress tracking.

## Zotero-First Management

Old idea: manage literature from Zotero at the start.

Deferred reason: early discovery is lighter with DOI list + Codex. Zotero remains optional for papers that are actually cited.
