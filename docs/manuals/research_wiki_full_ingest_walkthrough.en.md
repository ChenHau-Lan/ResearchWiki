# Research Wiki Full-Ingest Walkthrough (Legacy)

[繁體中文](research_wiki_full_ingest_walkthrough.zh-TW.md)

This v1 walkthrough has been replaced by the v2 [Skill-first illustrated quickstart](research_wiki_skill_first_quickstart.en.md).

This file remains only so old links do not break. Do not follow the old command option numbers. Research Wiki v2 is operated through pipeline skills + modes:

```text
source-intake -> paper-ingest -> knowledge-workbench -> synthesis-research -> wiki-lint
```

## Important Correction: Fan-out Is Not A Routine Next Step

The old section 8 made fan-out apply look too much like a normal workflow step. The v2 flow is:

1. Use `synthesis-research/fanout-review` to create a candidate or review proposal.
2. Human review checks target pages, supported/challenged claims, confidence, counter-evidence, and supersession risk.
3. Use `synthesis-research/apply-approved-fanout` only for an explicitly approved candidate.

`apply-approved-fanout` is an advanced write mode, not the default beginner workflow.

## Read Instead

- [Skill-first illustrated quickstart](research_wiki_skill_first_quickstart.en.md)
- [User Guide](../../USER_GUIDE.md)
- [Pipeline Architecture](../guides/research_wiki_pipeline_architecture.en.md)
