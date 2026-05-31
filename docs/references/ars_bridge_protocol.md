# ARS Bridge Protocol

`rkf-ars-bridge` is an implicit protocol, not an active skill.

Use it when output from Academic Research Skills should influence RKF. ARS may
produce research, writing, review, or pipeline output; RKF decides what is saved
as durable wiki knowledge.

## Proposal Shape

```yaml
target_layer: paper | question | concept | claim | synthesis | topic | review
title: short title
source_from_ars: deep-research | academic-paper | academic-paper-reviewer | academic-pipeline
reading_state: metadata-only | abstract-read | partial-fulltext | fulltext-read | human-reviewed | blocked
fulltext_status: unknown | needs-user-pdf | user-pdf-provided | publisher-html | publisher-pdf | open-access-pdf | partial-only | fulltext-read | unavailable | blocked
human_feedback_level: none | skimmed | discussed | annotated | trusted
synthesis_maturity: draft | single-source | multi-source | human-reviewed | publication-ready
source_coverage: unknown | partial | representative | systematic
evidence_boundary: locator, existing RKF page, human-reviewed, or review blocker
confidence: low | medium | high | mixed
recommended_rkf_mode: save | review | synthesize | distill | paper-feedback
reason_to_save: one sentence
```

## Rules

- ARS output is not evidence.
- ARS output may suggest a paper draft or maturity update, but cannot by itself
  satisfy a stable claim boundary.
- Save ARS-derived claims only when they point to a locator, existing RKF page,
  human feedback, or review blocker.
- If the ARS output changes a topic boundary, synthesis, paper understanding,
  or research question, save it as a proposal first unless the user explicitly
  approves the RKF update path.
- Reading-ledger events are useful operational memory, not evidence by
  themselves.
