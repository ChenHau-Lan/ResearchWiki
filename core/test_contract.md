# Research Wiki Test Contract

Any command or UI implementation must satisfy these scenarios.

## Core Checks

- Syntax checks pass for project Python tools.
- `tools/wiki_lint.py` passes.
- `tools/wiki_doctor.py` reports no errors for a clean template state.
- `python3 -m unittest discover -s tests` passes.
- `tools/public_safety_scan.py` passes before public pushes.
- `tools/generate_repair_plan.py` writes an advisory plan and does not delete.
- No private raw PDF or full-text file is tracked by Git by default.

## Runtime Governance Scenarios

- Query mode is read-only. It may inspect wiki, raw indexes, and verified raw
  evidence, but it must not write wiki pages, dashboards, review queues, logs,
  state files, or graph exports.
- Save mode requires an explicit target layer before writing: paper page,
  synthesis, concept, meeting/project history, review queue, or maintenance log.
  Unsupported or uncertain answers must not enter formal wiki pages.
- Semantic lint may report unsupported high-confidence claims, missing
  counter-evidence, abstract-only evidence misuse, seminar evidence promotion,
  and possible supersession. It writes advisory reports or review-queue items
  only.
- Concept pages are supported as formal wiki pages, but orphan concept pages are
  reported for graph review.
- Governance files `maintenance/review_queue.md` and `maintenance/log.md` are
  expected in a clean vNext template state.
- Topic governance files `wiki/topics/topic_registry.md` and `wiki/topics/`
  are expected in a clean template state.
- Question pages are supported as formal uncertainty pages under
  `wiki/questions/`; they must not settle claims without synthesis evidence.
- Compiler navigation pages `wiki/purpose.md`, `wiki/overview.md`, and
  `wiki/hot.md` are expected in a clean research-compiler template state.
- Fan-out candidates are staged in `maintenance/fanout_candidates.md` before
  they become review queue items or formal wiki edits.
- Runtime exports `maintenance/state.json` and `maintenance/graph.json` are
  generated from current indexes, frontmatter, and wikilinks; doctor reports
  missing or stale exports but does not edit formal wiki pages.
- Source fan-out review must not directly update formal synthesis or concept
  pages. It creates a deterministic candidate and a proposal that can later be
  applied by an explicit approved fan-out or Save action.
- Approved fan-out updates must preserve evidence tiers and must not convert a
  single paper claim into a high-confidence cross-paper conclusion.
- Thesis review mode writes stance evidence and verdict proposals under
  maintenance. It must not directly edit formal wiki pages.
- A thesis run creates or updates only files under
  `maintenance/thesis_runs/<date>_<slug>/` unless a later Save or approved
  fan-out action is explicitly started.
- Thesis verdicts are limited to `supported`, `partially supported`,
  `contradicted`, `insufficient evidence`, and `mixed`.

## Skill-First Acceptance Scenarios

- The official operation surface is the seven-skill pipeline:
  `literature-discovery`, `source-intake`, `paper-ingest`,
  `topic-governance`, `knowledge-workbench`, `synthesis-research`, and
  `wiki-lint`.
- `audit-release` remains an advanced compatibility alias for support and
  release maintenance, not the beginner-facing lint model.
- Every former command capability maps to a skill/mode in
  `docs/guides/research_wiki_pipeline_architecture.en.md`.
- `knowledge-workbench/query` is read-only. It may inspect wiki, raw indexes,
  and verified raw evidence, but it must not write wiki pages, dashboards,
  review queues, logs, state files, or graph exports.
- `knowledge-workbench/save` and `knowledge-workbench/query-to-save` require
  an explicit target layer before writing.
- `knowledge-workbench/review-queue` is maintenance-only and must not edit
  formal wiki pages.
- `literature-discovery` may write candidate runs and acquisition checkpoints
  but must not create paper pages or QCed full text.
- `topic-governance` must reject invalid or duplicate topic IDs and duplicate
  aliases.

## Command Router Acceptance Scenarios

- Paper intake exposes local/no-token steps separately from LLM steps:
  source input, source-page opening, PDF import, duplicate review, and index
  rebuild must not launch Codex; full-text QC and source-resolution fallback
  are explicit LLM actions.
- DOI list input creates or refreshes dashboard rows without fabricating
  metadata.
- DOI-only intake creates a dashboard row but does not create PDF, staging, or
  full-text artifacts.
- Candidate PDF acquisition without `--checkpoint approved` must write an
  acquisition checkpoint and mark `pdf_checkpoint_required`, not copy the PDF.
- Approved PDF acquisition may copy an approved legal PDF into the configured
  PDF root and mark `pdf_downloaded`.
- DOI plus DOI URL/article URL intake deduplicates DOI rows; unresolved
  non-DOI source pointers remain queued or are recorded as source notes.
- DOI and PDF import canonicalizes publisher filename-copy suffixes, so
  duplicate files such as Copernicus `...-2005-2.pdf` do not create duplicate
  paper rows.
- Paper-source intake accepts DOI values, DOI URLs, article URLs, and PDF URLs;
  unresolved non-DOI source pointers remain queued until a DOI or reliable
  metadata is resolved.
- Authorized source-page workflow opens source pages or explains what the user
  should do without downloading unauthorized files.
- Local PDF import can:
  - reject non-PDF files;
  - reject valid PDFs that have no DOI and no matching dashboard row;
  - create a dashboard row from a PDF DOI;
  - rename matched PDFs to `<paper_file_key>.pdf`;
  - avoid creating new persistent un-QCed staging text in the canonical
    Codex-first command;
  - create `raw/full_text/<paper_file_key>.md` only after Codex reflow/QC.
- QC failure leaves `raw/full_text/` empty for that paper, does not index the
  un-QCed source text, and marks the row `full_text_needed` with next action
  `codex_convert_to_full_text`.
- Full-text QC records `table_quality` and keeps wide/continued/numeric tables
  separate from prose; table values marked `partial` or `poor` require PDF,
  HTML/XML, or supplement verification before reuse.
- Dashboard/PDF refresh must list exact byte-identical duplicate PDFs when
  present, keep a canonical PDF, and delete duplicate candidates only after an
  explicit confirmation phrase. It must not delete by wildcard or recursive
  command.
- Running local PDF import twice is idempotent for already imported and QCed
  rows.
- Wiki ingest prompts select only QCed full text and must not acquire sources
  or perform full-text reflow/QC.
- Initializer/reset commands must require explicit confirmation and must only
  delete scoped test evidence and generated pages.

## Skill-First Command Router Scenarios

- `ResearchWikiCodex.command` is a thin skill/mode router and compatibility
  entrypoint, not the canonical workflow model.
- The router must not expose the old 14-option command menu as the primary UI.
- The router must expose the seven pipeline skills and their modes.
- The deleted legacy staging-based command must not be required by docs,
  install checks, or tests.
- Dashboard refresh may sync DOI rows, rebuild indexes, scan
  `raw/doi_pdf/`, and ask for confirmed byte-identical PDF duplicate cleanup,
  but must not create new persistent files under `raw/staging/extracted_text/`.
- Full-text creation writes only QCed Markdown under
  `raw/full_text/`; failure leaves `raw/full_text/` empty for that paper and
  records a dashboard blocker instead of saving un-QCed staging text.
- Wiki ingest still selects only QCed full text.
- GitHub feedback asks for a title, writes/copies a Codex prompt,
  and opens Codex for a follow-up conversation; the command itself must not
  block on long free-form input or submit a real issue.
- External sandbox handoff writes/copies a prompt for another Codex
  sandbox on the same computer to use the exact repository path directly. It
  must not require branch, PR, clone, rsync, or patch-based sync.
- Windows launchers use repo-relative `%~dp0` paths and fall back to manual
  prompt paste when Codex app auto-launch is unavailable.
- `InitializeResearchWiki.command` and `InitializeResearchWiki.cmd` support
  first-time topic setup; reset mode requires explicit confirmation and only
  deletes scoped generated local artifacts.

## GitHub / New User Acceptance Scenarios

- A new user can read `INSTALL.zh-TW.md` and understand core vs command vs
  personal branches.
- A user without GitHub CLI login can still run local diagnostics.
- Support report generation redacts private paths and raw evidence.
- Support issue creation opens a prefilled issue URL and does not submit it.
- CI uses synthetic fixtures, not real publisher PDFs.
