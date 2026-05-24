# RKF Agent Contract

Agents working in RKF must preserve evidence boundaries while turning research
work into governed LLM Wiki memory.

## Allowed Promotion

- Metadata may become a `SourceRecord`.
- Discovery results may become candidates.
- Candidate PDFs may become evidence only after an acquisition checkpoint.
- PDF evidence may become wiki input only after PDF QC.
- ARS outputs may become proposals only.
- Topic edits may become review proposals, merge/split suggestions, alias
  updates, or search-string updates.
- External sandbox outputs may become save/review proposals only unless the
  user approves a stable write path.

## Required Refusals

- Do not create paper pages from metadata-only sources.
- Do not create paper pages from unapproved or un-QCed PDFs.
- Do not treat ARS output as evidence.
- Do not save durable article text as a knowledge layer.
- Do not paste full article text into public pages.
- Do not commit machine-specific Drive paths, cross-platform links, or sandbox
  access tokens.

## Bridge Rule

When ARS output should influence RKF, produce a proposal with target layer,
evidence boundary, confidence, and recommended RKF mode. Then route through the
appropriate RKF skill.
