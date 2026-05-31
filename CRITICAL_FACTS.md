# RKF Critical Facts

This file stores short, public-safe facts that future agents should reuse
before searching deeper context. Keep each line compact and include temporal
metadata.

Format:

```text
- fact_id=short-id | observed_at=YYYY-MM-DD | valid_from=YYYY-MM-DD | confidence=low|medium|high|mixed | source_or_blocker=path-or-blocker | Fact sentence.
```

## Active Facts

- fact_id=rkf-purpose | observed_at=2026-05-31 | valid_from=2026-05-31 | confidence=high | source_or_blocker=README.md | RKF is an active academic LLM Wiki that preserves reading maturity, evidence boundaries, and public-safe research memory.
- fact_id=evidence-boundary | observed_at=2026-05-31 | valid_from=2026-05-31 | confidence=high | source_or_blocker=AGENTS.md | Evidence is an upgrade boundary for stable claims and trusted synthesis, not a requirement for creating an early paper draft.
- fact_id=ars-role | observed_at=2026-05-31 | valid_from=2026-05-31 | confidence=high | source_or_blocker=README.md | ARS remains the external research, reasoning, writing, and review engine while RKF stores durable governed memory.
