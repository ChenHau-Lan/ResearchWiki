---
name: topic-governance
description: Use when adding, renaming, linting, or scoping topics, aliases, default searches, canonical pages, and review cadence.
---

# Topic Governance

Topic Governance keeps automated discovery from drifting. It owns topic IDs,
aliases, include/exclude boundaries, default search strings, canonical pages,
and review cadence.

## Modes

- `add-topic`: add a topic row and optional `wiki/topics/<topic_id>.md` page.
- `update-topic`: change aliases, scope, default search, or canonical pages.
- `lint-topics`: check duplicate IDs, duplicate aliases, invalid IDs, and empty
  scope/search fields.
- `topic-review`: review stale topics and propose search refreshes.

## Rules

- Check `wiki/topics/topic_registry.md` before inventing a new topic.
- Use lowercase ASCII topic IDs with hyphens.
- Keep topic pages as maps and retrieval governance, not evidence-bearing
  synthesis.
- Broad topic changes should stage review notes when they affect existing
  literature, concepts, questions, or synthesis pages.
