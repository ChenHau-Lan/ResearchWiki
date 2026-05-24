---
name: literature-discovery
description: Use when turning a topic, question, DOI, or URL into search candidates, legal full-text routes, acquisition checkpoints, or approved PDF imports before paper ingest.
---

# Literature Discovery

Literature Discovery automates source discovery without bypassing evidence
gates. It may search metadata APIs, inspect legal source candidates, save
screenshots, and prepare acquisition checkpoints, but it must not create paper
pages or QCed full text.

## Modes

- `topic-search`: search from a topic/question seed, using topic registry scope
  and include/exclude rules.
- `resolve-candidates`: turn accepted DOI/URL candidates into source queue rows.
- `acquire-pdf`: import or download approved legal PDFs into the configured PDF
  storage root.
- `checkpoint`: prepare a human decision record before a candidate source is
  promoted to evidence.

## Rules

- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Do not treat screenshots as full text.
- Do not create `wiki/literature/` pages.
- Candidate PDFs must pass a human checkpoint before `pdf_downloaded`.
- Metadata-only candidates may become `candidate_found`, not `full_text_done`.
- Topic searches must cite the topic registry entry or create a reviewable topic
  proposal first.
