# Research Knowledge Framework

RKF is an LLM Wiki-based research knowledge framework. Its job is to preserve
active, source-aware academic knowledge while staying compatible with Academic
Research Skills (ARS) as an external research, reasoning, writing, and review
engine.

RKF is not only an evidence vault. Its normal paper path starts early: source
capture creates a SourceRecord, paper drafts record what has been read so far,
reading ledgers store public-safe user/agent interactions, and evidence
boundaries control when claims or synthesis become stable.

## Skills Overview

| Skill | Purpose | Natural-Language Triggers |
|---|---|---|
| `rkf-evidence-vault` | Source capture, candidate discovery, full-text availability, user PDF routing, PDF/OCR/visual reading state | DOI, URL, PDF, literature discovery, source intake, 文獻搜尋, 找文章, 提供PDF, full text |
| `rkf-knowledge-synthesis` | Paper drafts, maintained knowledge objects, topic review, and maturity-aware synthesis | paper note, synthesis, topic, claim, 整理成wiki, 論文筆記, 概念頁, topic整理 |
| `rkf-wiki-core` | LLM Wiki retrieval, ARS reasoning handoff, save, graph, L0-L3 world context, evolve, paper queue, sandbox context | LLM Wiki, query, save, graph, world, evolve, status, paper queue, 回寫wiki |
| `rkf-lint` | Health checks and repair planning for structure, maturity, evidence boundary, graph, public safety | lint, audit, repair plan, 檢查, 修復計畫, 發布安全 |
| `rkf-connect` | Experimental shared database, multi-computer Drive links, and external sandbox access boundaries | shared database, Google Drive, symlink, sandbox access, 共享資料庫 |

`rkf-ars-bridge` is not an active skill. It is an implicit protocol for
translating ARS outputs into RKF proposals or reading-feedback events.

## Routing Discipline

1. If the user asks to capture DOI/URL/topic/PDF leads or candidate papers,
   route to `rkf-evidence-vault`.
2. If the user asks to record how much a paper has been read, whether full text
   is available, or what human feedback was given, route to `rkf-evidence-vault`
   for reading-state updates or `rkf-wiki-core` for paper queue/status.
3. If the user asks to write or update wiki knowledge, route to
   `rkf-knowledge-synthesis`. Use `evolve` for low-risk direct integration into
   an existing page when the update can be marked AI-integrated and maturity-aware.
4. If the user asks to query the wiki, retrieve governed RKF context with
   `rkf-wiki-core`; when interpretation or recommendation is needed, let ARS
   reason over that context; save only through RKF proposal/synthesis rules.
5. If the user asks to save discussion memory, export graph, check status, or
   hand off to another sandbox, route to `rkf-wiki-core`. Use `world` when a
   future agent needs session bootstrap context.
6. If the user asks to track frequently asked research questions or hot paper
   search demand, route to `rkf-wiki-core` hot-query behavior.
7. If the user asks to review, clean up, merge/split, refresh, or recommend
   changes to topics, route to `rkf-knowledge-synthesis` topic-review; use
   `rkf-lint` when the request is structural drift detection or repair planning.
8. If the user asks to set up shared RAW/wiki folders, connect multiple
   computers, or grant external sandbox access, route to `rkf-connect`.
9. If the user asks for deep research, paper writing, peer review, or a full
   research-to-paper workflow, use ARS externally; return durable results to
   RKF only through the bridge protocol.

## Key Rules

- Paper drafts are allowed early. A draft may be based on metadata, abstract,
  partial full text, publisher HTML, or a user-provided PDF.
- Candidates are not stable claim evidence.
- ARS reports are proposals or reading feedback by default.
- User feedback matters: skimmed, discussed, annotated, and trusted feedback
  should be recorded and used to raise understanding maturity.
- Stable claims need a locator, existing supported wiki page, strong human
  feedback, or an explicit review blocker.
- Trusted synthesis needs source coverage and maturity, not merely a long answer.
- Durable full article text is not an RKF knowledge layer.
- Temporary PDF text, OCR text, or browser extraction may be used to read; it
  must not be committed as a public knowledge object.
- A query answer is not a wiki page until deliberately saved as a question,
  claim, concept, synthesis, or reading feedback.
- `hot.md` is a public-safe operational demand retrieval file, not evidence.
- `state/reading/` is operational memory. It can record questions, answers,
  human corrections, annotations, trust changes, and blockers, but it does not
  automatically promote claims.
- `CRITICAL_FACTS.md` stores short public-safe facts with `observed_at`,
  `valid_from`, `confidence`, and `source_or_blocker` for future-agent retrieval.
- Paper, synthesis, and topic pages should include a Future Agent Retrieval
  Brief when they are newly created or rewritten.
- Low-risk rewrites may update existing pages through `evolve`, but every AI
  rewrite must leave an `AI Integration Note`.
- High-risk stable claim promotion, source identity conflicts,
  publication-ready synthesis, and delete/merge choices must remain blocked or
  maturity-downgraded until reviewed.
- Shared database setup is experimental. Machine-specific links and private
  paths must not become the committed source of truth.
- Lint may report and plan repairs; it must not silently rewrite knowledge or
  delete files.

## Reading Maturity Gates

| Gate | Required Before |
|---|---|
| source identity check | using a source beyond rough discovery |
| full-text availability check | claiming a source has been read beyond metadata or abstract |
| reading-state update | changing reading_state, fulltext_status, or human_feedback_level |
| claim support check | stable claim or claim-ready paper state |
| synthesis maturity check | trusted synthesis or research recommendation |
| public-safety check | publication or push |

## Paper Reading Path

The canonical paper path is:

```text
DOI/URL/topic/PDF lead
  -> SourceRecord
  -> early paper draft
  -> fulltext_status: unknown | needs-user-pdf | user-pdf-provided | publisher-html | publisher-pdf | open-access-pdf | partial-only | fulltext-read | unavailable | blocked
  -> reading_state: metadata-only | abstract-read | partial-fulltext | fulltext-read | human-reviewed
  -> state/reading ledger with questions, feedback, and blockers
  -> claim_readiness: not-ready | locator-needed | claim-ready | synthesis-ready
```

If full text cannot be read, ask the user to provide a PDF or authorized text.
Do not bypass paywalls, CAPTCHA, robots, or access restrictions.

## ARS Integration

Use this bridge protocol when ARS output should affect RKF:

```yaml
target_layer: paper | question | concept | claim | synthesis | topic | review | reading-ledger
title: short title
source_from_ars: deep-research | academic-paper | academic-paper-reviewer | academic-pipeline
evidence_boundary: locator, existing RKF page, human feedback, or review blocker
reading_maturity: metadata-only | abstract-read | partial-fulltext | fulltext-read | human-reviewed | mixed
confidence: low | medium | high | mixed
recommended_rkf_mode: save | review | synthesize | distill | reading-feedback
reason_to_save: one sentence
```

ARS output may suggest what to save or how to update reading maturity. It cannot
by itself satisfy a stable claim boundary.

## Safety

- Do not commit PDFs, article text, private Drive paths, browser captures,
  local secrets, or private runtime state.
- Do not use `rm -rf`, `del /s`, `rd /s`, `rmdir /s`, or
  `Remove-Item -Recurse`.
- For tracked cleanup, use explicit `git rm` or `git rm -r` paths only when the
  user has approved the deletion scope.

## Validation

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/rk.py paper queue
python3 tools/public_safety_scan.py
```
