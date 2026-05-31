# Research Knowledge Framework

RKF is an LLM Wiki-based research knowledge framework. Its job is to preserve
durable, source-aware academic knowledge while staying compatible with Academic
Research Skills (ARS) as an external research, reasoning, writing, and review
engine.

PDFs are major reading artifacts for papers, but RKF is not limited to PDFs.
It governs source candidates, reviewed evidence artifacts, topics, questions,
concepts, claims, synthesis, and query-to-save decisions.

## Skills Overview

| Skill | Purpose | Natural-Language Triggers |
|---|---|---|
| `rkf-evidence-vault` | Source capture, candidate discovery, legal evidence routes, PDF/OCR/visual QC for paper reading | DOI, URL, PDF, literature discovery, source intake, 文獻搜尋, 找文章, 下載PDF, 證據庫 |
| `rkf-knowledge-synthesis` | Reviewed-evidence paper pages, maintained knowledge objects, and topic review | paper note, synthesis, topic, topic review, claim, 整理成wiki, 論文筆記, 概念頁, 問題頁, topic整理, 綜整 |
| `rkf-wiki-core` | LLM Wiki memory retrieval, ARS reasoning handoff, save, graph, sandbox context | LLM Wiki, query, save, graph, sandbox, 問知識庫, 回寫wiki, 保存討論, 知識圖譜 |
| `rkf-lint` | Ongoing health checks and repair planning | lint, audit, repair plan, public safety, 檢查, 修復計畫, 證據邊界, 發布安全 |
| `rkf-connect` | Experimental shared database, multi-computer Drive links, and external sandbox access boundaries | shared database, Google Drive, symlink, junction, sandbox access, 共享資料庫, 多台電腦, 外部sandbox, 連結wiki |

`rkf-ars-bridge` is not an active skill. It is an implicit protocol for
translating ARS outputs into RKF proposals.

## Routing Discipline

1. If the user asks to capture DOI/URL/topic/PDF evidence or candidate papers,
   route to `rkf-evidence-vault`.
2. If the user asks to write or update wiki knowledge, route to
   `rkf-knowledge-synthesis`.
3. If the user asks to query the wiki, first retrieve governed RKF context with
   `rkf-wiki-core`; when interpretation or recommendation is needed, let ARS
   reason over that context; save only through RKF proposal/synthesis rules.
4. If the user asks to save discussion memory, export graph, or hand off to
   another sandbox, route to `rkf-wiki-core`.
5. If the user asks to track frequently asked research questions or hot paper
   search demand, route to `rkf-wiki-core` hot-query behavior.
6. If the user asks to review, clean up, merge/split, refresh, or recommend
   changes to topics, route to `rkf-knowledge-synthesis` `topic-review`; use
   `rkf-lint` when the request is structural drift detection or repair planning.
7. If the user asks to set up shared RAW/wiki folders, connect multiple
   computers, manage Google Drive links, or grant an external sandbox access to
   the wiki, route to `rkf-connect`.
8. If the user asks to check, audit, diagnose, publish, schedule maintenance,
   or repair the wiki, route to `rkf-lint`.
9. If the user asks for deep research, paper writing, peer review, or a full
   research-to-paper workflow, use ARS skills externally; return durable results
   to RKF only through the bridge protocol.
10. If a request mixes ARS work and RKF persistence, treat ARS output as a
   proposal first. Do not save it as evidence.

## Key Rules

- Candidates are not evidence.
- ARS reports are not evidence by themselves.
- A paper wiki page requires a reviewed source artifact, usually an approved
  and QCed PDF or a legal publisher artifact represented by an evidence record.
- Durable full article text is not an RKF knowledge layer.
- Temporary PDF text, OCR text, or browser extraction may be used to read; it
  must not be committed or saved as a public knowledge object.
- Every stable claim needs a locator, an existing wiki source, or a review
  blocker.
- A query answer is not a wiki page until deliberately saved as a question,
  claim, concept, or synthesis.
- `hot.md` is a public-safe operational demand retrieval file, not evidence or
  stable knowledge.
- Topics must be reviewed as living research controls: aliases, scope,
  include/exclude rules, default search strings, candidate backlog, and
  canonical synthesis links should be checked on a cadence.
- Shared database setup is experimental. Drive may hold real RAW and wiki data,
  but machine-specific links and private paths must not become the committed
  source of truth.
- External sandboxes get read access by default. Their useful outputs return as
  RKF proposals unless the user explicitly approves a write path.
- Lint is maintenance, not just pre-release cleanup. It may report and plan
  repairs; it must not silently rewrite knowledge or delete files.

## Evidence Gates

| Gate | Required Before |
|---|---|
| topic fit check | assigning a candidate to an existing or new topic |
| source identity check | source promotion beyond candidate |
| acquisition checkpoint | private evidence storage or paper ingest |
| PDF/OCR/visual QC | paper wiki distillation |
| claim support check | stable claim or synthesis |
| public-safety check | publication or push |

## Paper Evidence Path

The canonical paper path is:

```text
DOI/URL/topic/PDF lead
  -> topic fit check
  -> SourceRecord
  -> candidate backlog or acquisition checkpoint
  -> reviewed evidence artifact
  -> PDF/OCR/visual QC with locator notes
  -> paper wiki page
```

For scanned or image-only papers, record visual locators, page images, OCR
confidence, and human reading notes. If OCR is unreliable, do not claim
full-read text evidence.

## Connection Protocol

Use `rkf-connect` only when the user wants portability or external access. The
current experimental pattern is:

```text
shared Drive research folder
  -> RAW and wiki as real shared folders
  -> local RKF project links to those folders per computer
  -> external sandbox receives read context and save/review proposal rules
```

Do not commit cross-platform symlinks, private Drive paths, or sandbox access
tokens. If a sandbox produces a durable question, claim, or synthesis, route it
back through RKF save/review gates.

## ARS Integration

ARS provides research, reasoning, writing, peer review, and pipeline
orchestration. RKF provides durable memory and evidence governance.

Use the bridge protocol when ARS output should affect RKF:

```yaml
target_layer: paper | question | concept | claim | synthesis | topic | review
title: short title
source_from_ars: deep-research | academic-paper | academic-paper-reviewer | academic-pipeline
evidence_boundary: locator, existing RKF page, or review blocker
confidence: low | medium | high | mixed
recommended_rkf_mode: save | review | synthesize | distill
reason_to_save: one sentence
```

ARS output may suggest what to save. It cannot by itself satisfy an evidence
gate. RKF query retrieves governed context; ARS reasons over that context; RKF
saves durable results only when they meet save/synthesis criteria.

## Reference Sources

- Karpathy LLM Wiki gist: persistent, compounding Markdown memory for LLM work.
- `Imbad0202/academic-research-skills`: ARS-style skill routing, mode registry,
  checkpoints, integrity gates, and cross-skill orchestration.
- `LigphiDonk/Oh-my--paper`: literature discovery and survey-memory inspiration.
- Public LLM Wiki repositories such as `lucasastorian/llmwiki`: LLM-readable
  wiki organization patterns.

Use these as conceptual references. Do not vendor large upstream text or
license-restricted content into this repository without an explicit license
review.

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
python3 tools/public_safety_scan.py
```
