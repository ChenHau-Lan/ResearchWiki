---
type: maintenance
status: draft
source_status: personal-note
reading_status: mixed
review_stage: discussed
topics: []
subtopics: []
keywords: [graph_links, backlinks, local_graph]
created: 2026-05-21
updated: 2026-05-21
sources: []
---

# Obsidian Graph Guide

Use Obsidian graph to see research relationships at a glance. The graph should be built from explicit wikilinks, not only YAML metadata.

## Recommended Global Graph Filter

```text
path:wiki -path:.obsidian -file:workspace
```

## Useful Focus Filters

```text
path:wiki/literature
path:wiki/synthesis OR path:wiki/literature
path:wiki/project_synthesis OR path:wiki/meetings
path:wiki/seminars OR path:wiki/literature
```

## Color Groups

- `path:wiki/literature` - paper evidence.
- `path:wiki/synthesis` - cross-paper judgment.
- `path:wiki/seminars` - talk context.
- `path:wiki/meetings` - single-meeting records.
- `path:wiki/project_synthesis` - project evolution.
- `file:topic_ OR file:subtopic_` - promoted research map nodes only.

## Link Rule

Every formal page should include a `Graph Links` section with links to topics, subtopics, related literature, related synthesis, seminars, and projects.

## Graph Links

- Topics:
- Subtopics:
- Related literature: [[literature/literature]]
- Related synthesis: [[synthesis/synthesis]]
- Related seminars: [[seminars/seminars]]
- Related projects: [[project_synthesis/project_synthesis]]
