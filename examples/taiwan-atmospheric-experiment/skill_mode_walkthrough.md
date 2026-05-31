# Skill And Mode Walkthrough

Starting prompt:

> 我想整理在台灣的大氣實驗，如 TAMEX, SOMEX, TAHOPE。

Interpretation:

- `SOMEX` is recorded as an ambiguous alias from the starting prompt. ARS/RKF
  checks the literature context before durable naming in topic pages.
- The task has both ARS work and RKF persistence. ARS searches and evaluates;
  RKF stores active reading state and promotes only boundary-ready claims.

## Step-By-Step Routing

| Step | User Intent | Skill | Mode | Output | Stop Condition |
|---|---|---|---|---|---|
| 1 | Clarify topic boundary | `academic-research-skills` | `deep-research:socratic` or `deep-research:quick` | Research scope and search terms | If campaign names are ambiguous |
| 2 | Find SCI papers | `academic-research-skills` | `deep-research:lit-review` | Candidate paper list with DOI/routes | Candidates can seed drafts; not claim evidence |
| 3 | Check source quality | `academic-research-skills` | `deep-research:fact-check` | Source verification notes | If source identity or DOI is unclear |
| 4 | Capture DOI/URL/PDF lead | `rkf-evidence-vault` | `capture` | SourceRecord | No wiki write yet |
| 5 | Create paper draft | `rkf-knowledge-synthesis` | `distill-paper` | `knowledge/papers/*.md` with maturity fields | Mark metadata-only or needs-user-pdf honestly |
| 6 | Record full text route | `rkf-evidence-vault` | `acquire` | full-text status update or route note | Ask user for PDF only when full text is unavailable |
| 7 | Confirm artifact usability | `rkf-evidence-vault` | `verify-pdf` | checked reading artifact and locators | Stop stable claims if unreadable, locator-poor, or OCR is weak |
| 8 | Connect concepts | `rkf-knowledge-synthesis` | `save-concept`, `topic-governance` | Topic/concept pages | Claims need locators |
| 9 | Review topic health | `rkf-knowledge-synthesis` | `topic-review` | Merge/split, alias, search-string, and backlog proposals | Propose before large registry edits |
| 10 | Ask wiki question | `rkf-wiki-core` | `query` | RKF context plus ARS reasoning | Answer is not a wiki page yet |
| 11 | Record feedback or nudge | `rkf-wiki-core` | `paper-feedback`, `paper-queue` | reading ledger update or paper queue | Ledger is operational memory, not evidence itself |
| 12 | Save recommendation | `rkf-knowledge-synthesis` | `synthesize` | Synthesis page with maturity fields | Save only durable cross-source results |
| 13 | Check safety | `rkf-lint` | `evidence-lint`, `public-safety-lint` | Findings or repair plan | Block if PDFs/private paths leak |
| 14 | Share across machines | `rkf-connect` | `shared-database-plan`, `sandbox-grant` | Drive RAW/wiki plan or sandbox capsule | Experimental; no private paths in Git |

## Why Not Use ARS Alone?

ARS can produce a literature review, research report, or source evaluation, but
ARS alone does not turn what you learned into durable memory. Without RKF, the
next session often has to rediscover the same sources, topic boundaries,
reading status, and reasoning. LLM Wiki fills that gap: it preserves reusable
knowledge objects, topic governance, maturity boundaries, and review queues.

ARS output therefore becomes an RKF proposal. RKF saves it only after choosing a
target layer and recording the reading boundary, evidence boundary, or review
blocker.

## Example Routing Decisions

- TAMEX J-STAGE PDF: ARS finds and grades it; RKF captures DOI, creates a paper
  draft, records the free publisher full-text route, verifies locators, then
  raises claim readiness.
- SoWMEX/TiMREX MDPI article: ARS finds DOI and paper context; RKF notes that
  automated retrieval was blocked, so the route needs user/browser reading
  before claim readiness can increase.
- TAHOPE/PRECIP Miao et al. 2025: ARS identifies it as a recent SCI article;
  RKF records the open full-text route and creates a TAHOPE paper page with
  maturity fields.
- TAHOPE official PDF: ARS treats it as project context, not SCI evidence; RKF
  saves it as project overview context after reading maturity update.
- Topic review: RKF treats the campaign topic as a living control surface, so
  aliases, candidate backlog, and default searches are reviewed before the next
  literature round.
- Shared setup: `rkf-connect` is only used if the example wiki needs to be read
  from another computer or sandbox.
