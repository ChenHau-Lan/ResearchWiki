# ResearchWiki Mode Registry

This registry maps user intent to skill/mode. Durable permissions live in
`core/data_contract.md` and `core/agent_contract.md`.

| Skill | Mode | Use For | Writes |
|---|---|---|---|
| `source-intake` | `add-source` | Add DOI, DOI URL, article URL, PDF URL, or source note | `raw/paper_sources.md`, dashboard |
| `source-intake` | `refresh-dashboard` | Rebuild source status and full-text dispatch indexes | dashboard/indexes |
| `source-intake` | `qced-full-text` | Save QCed readable full text or honest abstract-only fallback | `raw/full_text/`, indexes |
| `literature-discovery` | `topic-search` | Search from a topic/question seed and stage candidates | `maintenance/search_runs/` |
| `literature-discovery` | `resolve-candidates` | Resolve DOI/URL candidates into source queue rows | `raw/paper_sources.md`, dashboard |
| `literature-discovery` | `acquire-pdf` | Acquire or import approved legal PDFs | `raw/doi_pdf/` or configured Drive root |
| `literature-discovery` | `checkpoint` | Human review of candidate PDF/source/screenshot before evidence use | `maintenance/acquisition_checkpoints/` |
| `paper-ingest` | `ingest-qced-full-text` | Convert one QCed full text into one paper page | `wiki/literature/` |
| `topic-governance` | `add-topic` | Add topic ID, aliases, scope, and default search | `wiki/topics/topic_registry.md`, optional topic page |
| `topic-governance` | `lint-topics` | Validate topic IDs, duplicate aliases, and canonical links | terminal / maintenance |
| `knowledge-workbench` | `query` | Answer from existing wiki/raw indexes only | none |
| `knowledge-workbench` | `query-to-save` | Turn useful discussion into a source-backed Save proposal | proposal, then target layer |
| `knowledge-workbench` | `save` | Save source-backed knowledge to the selected layer | wiki/maintenance target |
| `knowledge-workbench` | `review-queue` | Stage uncertain or conflicting claims | `maintenance/review_queue.md` |
| `synthesis-research` | `fanout-review` | Stage multi-page source impact | `maintenance/fanout_candidates.md` |
| `synthesis-research` | `apply-approved-fanout` | Apply approved source impact to formal wiki pages | approved wiki targets |
| `synthesis-research` | `thesis-review` | Test a high-risk claim with supporting/opposing evidence | `maintenance/thesis_runs/` |
| `synthesis-research` | `external-sandbox-sync` | Generate same-computer handoff prompt | ignored prompt file |
| `wiki-lint` | `structure-lint` | Check frontmatter, page type, graph links, indexes | terminal |
| `wiki-lint` | `semantic-lint` | Check evidence tier, confidence, counter-evidence, stale claims | maintenance findings |
| `wiki-lint` | `state-graph` | Export runtime state and graph | `maintenance/state.json`, `maintenance/graph.json` |

## Default Gates

- `query` is read-only.
- Metadata-only sources cannot become paper pages.
- Candidate PDFs require human approval before `pdf_downloaded`.
- `raw/full_text/` requires QC metadata.
- Cross-page updates go through Save, review queue, thesis review, or approved
  fan-out.
