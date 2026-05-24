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
evidence_boundary: PDF locator, existing RKF page, or review blocker
confidence: low | medium | high | mixed
recommended_rkf_mode: save | review | synthesize | distill
reason_to_save: one sentence
```

## Rules

- ARS output is not evidence.
- ARS output cannot satisfy PDF QC.
- Save ARS-derived claims only when they point to PDF evidence, an existing RKF
  page, or a review blocker.
- If the ARS output changes a topic boundary, synthesis, or research question,
  save it as a proposal first.
