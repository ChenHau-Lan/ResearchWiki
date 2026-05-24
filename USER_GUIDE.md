# User Guide

[中文操作摘要](USER_GUIDE.zh-TW.md)

Research Wiki is operated through **pipeline skills + modes**. This guide is a reference for everyday operation: when to use each mode, what it may read or write, and which human checkpoint is required. If you are starting from zero, begin with the [Skill-first illustrated quickstart](docs/manuals/research_wiki_skill_first_quickstart.en.md).

## 1. Runtime Model

```text
topic-governance -> literature-discovery -> source-intake -> paper-ingest -> knowledge-workbench -> synthesis-research -> wiki-lint
```

- `raw/` is the evidence layer: DOI/URL/PDF queue, dashboard, PDFs, staging extraction, QCed full text, and original meeting/seminar files.
- `wiki/` is the curated knowledge layer: purpose, overview, hot, literature, concepts, synthesis, meetings, project synthesis, and seminars.
- `maintenance/` is the governance layer: review queue, fan-out candidates, repair plan, runtime state/graph, support report, and release hygiene notes.
- `ResearchWikiCodex.command` / `.cmd` is a compatibility router. The rules live in `core/`, `core/skills/`, and the pipeline architecture guide.
- `tools/rw.py` handles deterministic local operations such as source queue
  updates, acquisition checkpoints, topic lint, paper ingest gates, and external
  sandbox prompts.

## 2. Mode Matrix

| Skill/mode | Use when | Main input | May write | Human checkpoint |
| --- | --- | --- | --- | --- |
| `literature-discovery/topic-search` | Search from a topic, question, DOI, or URL | topic/question seed | `maintenance/search_runs/`, candidate dashboard rows | Candidates are not evidence |
| `literature-discovery/resolve-candidates` | Accept selected candidates into the queue | DOI/URL candidates | `raw/paper_sources.md`, dashboard | Confirm identity and relevance |
| `literature-discovery/acquire-pdf` | Import/download approved legal PDFs | approved local PDF or legal URL | configured PDF root | Must pass `pdf_checkpoint_required` first |
| `literature-discovery/checkpoint` | Review candidate source route | candidate PDF/URL/screenshot | `maintenance/acquisition_checkpoints/` | Source legality and article identity |
| `source-intake/add-source` | Add a DOI, DOI URL, article URL, PDF URL, or source note | User-provided source pointer | `raw/paper_sources.md`, dashboard status | Confirm the source belongs in the research queue |
| `source-intake/refresh-dashboard` | Reconcile source queue, PDF evidence, indexes, and status board | `raw/paper_sources.md`, `raw/doi_pdf/` | `raw/doi_dashboard.md`, `raw/full_text_index.*` | Remember that dashboard status is not evidence |
| `source-intake/qced-full-text` | Create readable Markdown full text from authorized or user-provided sources | PDF, authorized HTML/XML/DOM, user-provided text | `raw/full_text/paper_file_key.md` | Source legality, metadata, paragraph order, tables, equations, captions |
| `paper-ingest/ingest-qced-full-text` | Convert QCed full text into a single paper page | `raw/full_text/paper_file_key.md` | `wiki/literature/paper_slug.md`, dashboard status | Full text is truly QCed; paper page does not write synthesis |
| `topic-governance/add-topic` | Add topic ID, scope, aliases, and search strings | topic definition | `wiki/topics/topic_registry.md`, optional topic page | Search boundary is not too broad |
| `topic-governance/lint-topics` | Validate topic registry health | topic registry | terminal / maintenance | Duplicate aliases or empty search scope need review |
| `knowledge-workbench/query` | Ask the existing wiki without changing files | `wiki/`, indexed evidence | Nothing | Answer must label evidence tier and gaps |
| `knowledge-workbench/query-to-save` | Turn an answer into a save proposal | Prior answer or discussion | Usually no formal wiki writes; may propose a review item | Decide whether the item is worth saving and where |
| `knowledge-workbench/save` | Deliberately save durable knowledge | Approved content and target layer | `wiki/concepts/`, `wiki/synthesis/`, `wiki/project_synthesis/`, `maintenance/*` | Choose target layer before writing |
| `knowledge-workbench/review-queue` | Stage uncertain, conflicting, low-confidence, or supersession candidates | Item needing review | `maintenance/review_queue.md` | Do not promote unreviewed claims into formal wiki pages |
| `synthesis-research/fanout-review` | One source may affect multiple pages | paper page, full text, claim | `maintenance/fanout_candidates.md` or review proposal | Target pages, supported/challenged claims, confidence, counter-evidence |
| `synthesis-research/apply-approved-fanout` | Apply an approved fan-out item | Explicitly approved item | Approved wiki pages only | Apply one approved scope at a time |
| `synthesis-research/thesis-review` | Test whether a research claim holds | claim, scope, wiki evidence | thesis report, review queue, or Save proposal | Supporting, opposing, mechanistic, meta-review, and adjacent evidence |
| `synthesis-research/synthesis-page-start` | Start a synthesis or project-synthesis discussion | research question and source set | `wiki/synthesis/` or `wiki/project_synthesis/` draft | Claims must not exceed evidence tier |
| `wiki-lint/structure-lint` | Check wiki structural health | repo files | No formal wiki writes | frontmatter, indexes, paths, wikilinks, Graph Links, orphan pages |
| `wiki-lint/semantic-lint` | Check stale claims, contradictions, evidence tier, counter-evidence, supersession | `wiki/` | audit report / review queue | Do not directly apply lint suggestions to formal pages |
| `wiki-lint/repair-plan` | Generate a human repair plan | repo diagnostics | `maintenance/repair_plan_*.md` | Do not delete files automatically |
| `wiki-lint/state-graph` | Update runtime state and graph export | repo files | `maintenance/state.json`, `maintenance/graph.json` | Exports are not formal evidence |
| `wiki-lint/support-report` | Advanced support context | repo diagnostics | support report | Exclude private raw evidence, full text, and Codex logs |
| `wiki-lint/feedback-issue` | Advanced GitHub issue draft | user feedback and diagnostics | issue draft / prefilled URL | Do not submit automatically |

## 3. Choosing A Mode

| Intent | Use |
| --- | --- |
| I have a DOI/URL/PDF to put in the queue | `source-intake/add-source` |
| I have a topic idea and want candidate papers | `literature-discovery/topic-search` |
| I found a candidate PDF and need to approve it safely | `literature-discovery/checkpoint` |
| I need a new topic or better search boundary | `topic-governance/add-topic` |
| I put PDFs in place and want the dashboard to notice them | `source-intake/refresh-dashboard` |
| I want authorized full text converted into readable Markdown | `source-intake/qced-full-text` |
| I have QCed full text and want a paper page | `paper-ingest/ingest-qced-full-text` |
| I only want an answer, no file edits | `knowledge-workbench/query` |
| I want a draft of what should be saved | `knowledge-workbench/query-to-save` |
| I know the target layer and want to save | `knowledge-workbench/save` |
| I am unsure whether the answer is reliable | `knowledge-workbench/review-queue` |
| One paper affects many pages | `synthesis-research/fanout-review` |
| I need to test a claim | `synthesis-research/thesis-review` |
| I want to check database health | `wiki-lint/structure-lint` or `wiki-lint/semantic-lint` |
| I want a human repair plan | `wiki-lint/repair-plan` |

Ask Codex directly with a skill/mode phrase such as `Use source-intake/add-source ...`, or open `ResearchWikiCodex.command` / `ResearchWikiCodex.cmd` if you want the clickable router.

CLI equivalents:

```bash
python3 tools/rw.py source add https://doi.org/10.xxxx/example
python3 tools/rw.py source search "wildfire aerosol cloud interaction" --topic-id wildfire-cloud
python3 tools/rw.py source acquire 10.xxxx/example --pdf ~/Downloads/paper.pdf
python3 tools/rw.py source acquire 10.xxxx/example --pdf ~/Downloads/paper.pdf --checkpoint approved
python3 tools/rw.py topic add wildfire-cloud "Wildfire Cloud" --scope "Wildfire aerosol-cloud interaction" --search "wildfire aerosol cloud interaction"
python3 tools/rw.py prompt external-sandbox --target review_queue --task "Assess this idea against the wiki and propose what to save."
```

## 4. Knowledge Workbench Rules

`knowledge-workbench` combines Query and Save while keeping the boundary explicit:

- `query`: read-only; labels evidence tier, confidence, and missing evidence.
- `query-to-save`: turns an answer into a proposal; weak evidence should become a review item.
- `save`: writes only after a target layer is chosen.
- `review-queue`: maintenance-only write for low-confidence, conflicting, missing-counter-evidence, or supersession-prone items.

Before saving, decide whether the content is a single-paper fact, recurring concept, cross-literature synthesis, project decision, or only a maintenance note.

## 5. Evidence And Targets

| Evidence state | What it can support |
| --- | --- |
| `metadata-only` | Bibliographic/intake status only, not content claims |
| `abstract-only` | Low-tier summary leads, never `full-read` claims |
| `full-read` | Paper pages and synthesis, still with scope limits and counter-evidence |
| seminar / talk | Discussion context below peer-reviewed full-read literature |
| personal note / hypothesis | Review queue or project context, not literature evidence |

| Content to save | Target |
| --- | --- |
| Single-paper fact | `wiki/literature/` |
| Recurring term, method, dataset, instrument, variable | `wiki/concepts/` |
| Cross-literature judgment | `wiki/synthesis/` |
| Open research question or hypothesis | `wiki/questions/` |
| Search boundary or topic governance | `wiki/topics/` |
| Project decision or meeting evolution | `wiki/project_synthesis/` or `wiki/meetings/` |
| Uncertain, conflicting, low-confidence item | `maintenance/review_queue.md` |
| Tool or maintenance note | `maintenance/log.md` |

## 6. Screenshots And Manuals

Illustrated walkthroughs belong in `docs/manuals/`. Rendered PDFs are optional
generated outputs and should not be required for a public-safe checkout.

## 6. Storage And Sync

Copy `researchwiki.config.example.toml` to `researchwiki.config.toml` on each
computer. Keep the copied file out of Git.

Use Google Drive for desktop as the shared evidence root:

```text
Google Drive/My Drive/ResearchSync/
  literature/doi_pdf
  literature/full_text
  literature/files
  projects/
```

Do not use Google Drive's `Computers/My Mac/My PC` backup area as the shared
workspace. If old paths must stay alive, create local symlinks or junctions on
each computer and point them into Drive. Do not commit cross-platform symlinks
as the shared data model.

## 7. Screenshots And Manuals

Before committing screenshots, confirm they do not reveal:

- private PDFs or full article text;
- local home paths;
- sensitive DOI/source batches;
- browser sessions, credentials, or account details;
- Codex logs or private conversations.

## 8. Safety And Cleanup

- Do not automate unauthorized full-text acquisition.
- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Do not copy full articles into `wiki/`.
- Do not treat dashboard rows as evidence.
- Do not upgrade abstract-only, seminar, personal-note, or hypothesis material into full-read peer-reviewed evidence.
- Do not use recursive, wildcard, or bulk deletion commands.
- Repair plans diagnose and suggest; they do not delete files.

For directory cleanup, first produce explicit candidates with exact paths, reasons, risk, and a preservation alternative. Delete only one clearly approved path at a time.

## 9. Advanced Maintenance

`audit-release` is an advanced compatibility entrypoint. Existing names map as:

- `audit-release/semantic-audit` -> `wiki-lint/semantic-lint`
- `audit-release/runtime-state-graph` -> `wiki-lint/state-graph`
- `audit-release/release-hygiene` -> `wiki-lint/repair-plan`

Support reports and issue drafts belong to support workflows. They are available through `wiki-lint/support-report`, `wiki-lint/feedback-issue`, or SUPPORT docs, but they are not part of the beginner path.

## 10. Related Documents

- [Skill-first illustrated quickstart](docs/manuals/research_wiki_skill_first_quickstart.en.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Mode Registry](MODE_REGISTRY.md)
- [README](README.md)
- [Install Guide](INSTALL.md)
- [Support Guide](SUPPORT.md)
- [Version Log](VERSION_LOG.md)
