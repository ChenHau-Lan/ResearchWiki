---
name: knowledge-workbench
description: Use when answering from the wiki, turning answers into Save proposals, saving source-backed knowledge, or staging uncertain items in the review queue.
---

# Knowledge Workbench

Knowledge Workbench combines Query and Save into one user-facing workspace.
Permissions are mode-specific: `query` is read-only, while Save modes must
choose a target layer before writing.

## Modes

- `query`: read-only answer from existing synthesis, literature, seminars, raw
  indexes, and project pages. Label evidence tier and suggest a Save target when
  useful.
- `save`: write source-backed material to the chosen target layer: synthesis,
  concept, project synthesis, review queue, or log.
- `query-to-save`: convert a useful Query answer into a Save proposal, verify
  evidence, then save only after the target layer is explicit.
- `review-queue`: maintenance-only write for uncertain, conflicting,
  low-confidence, missing-counter-evidence, or supersession-candidate material.

## Rules

- `query` must not write, edit, stage, or generate files.
- Do not save unsupported chat claims into formal wiki pages.
- Paper-specific facts belong in paper pages; cross-source judgment belongs in
  synthesis; recurring methods/mechanisms/datasets/models belong in concepts.
- Important formal claims need evidence tier, evidence links, confidence, and
  counter-evidence or a missing-evidence note.
- Abstract-only, seminar, and personal-note material must stay visibly lower
  evidence tier.
