# Research Knowledge Framework Manual

RKF 是一個 LLM Wiki-based research knowledge framework。它的工作是保存
durable、source-aware 的 academic knowledge，同時讓 paper 理解可以在多次 session
中主動累積。

現在的模型是 reading maturity first, claim boundary second。Paper 可以先從
metadata、abstract、partial full text 或 user-provided PDF 進入 wiki 成為 draft。
Draft 必須誠實記錄現在讀到哪裡。Stable claim、trusted synthesis、citation
confidence、publication 則仍然需要 locator、人為 feedback、既有 governed RKF source，
或明確 review blocker。

RKF 與 `academic-research-skills` 並行使用：ARS 負責 search、reason、write、review；
RKF 決定什麼會變成 durable wiki memory，什麼仍是 reading draft 或 proposal。

## Mental Model

| Layer | 用途 | Boundary |
|---|---|---|
| Source record | 登錄 DOI、URL、PDF pointer、topic seed、idea、question | Source identity 與 topic fit |
| Paper draft | 保存單篇 paper 目前理解 | Reading state、full-text status、feedback level、claim readiness |
| Reading ledger | 保存 public-safe interaction history | Operational memory，不是 evidence 本身 |
| Claim | 保存 supported 或 reviewable statement | Locator、human feedback、existing page 或 blocker |
| Synthesis | 保存跨來源判斷 | Source coverage、maturity、feedback、claim readiness |
| Topic | 控制 discovery scope 與 drift | Scope、aliases、include/exclude、default searches |

## Paper Maturity

Paper frontmatter 應記錄：

```yaml
reading_state: metadata-only | abstract-read | partial-fulltext | fulltext-available | fulltext-read | human-reviewed | synthesis-ready | blocked
fulltext_status: unknown | needs-user-pdf | user-pdf-provided | publisher-html | publisher-pdf | open-access-pdf | partial-only | fulltext-read | unavailable | blocked
human_feedback_level: none | skimmed | discussed | annotated | trusted
understanding_confidence: low | medium | high | mixed
claim_readiness: not-ready | locator-needed | claim-ready | synthesis-ready
last_reading_interaction: YYYY-MM-DD
reading_ledger: state/reading/<source_id>.json
```

當系統知道得很少時，使用保守值。Metadata-only draft 仍然有價值，因為它會讓下一個
閱讀動作變得可見。

## Synthesis Maturity

Synthesis frontmatter 應記錄：

```yaml
synthesis_maturity: draft | single-source | multi-source | human-reviewed | publication-ready
source_coverage: unknown | partial | representative | systematic
human_feedback_level: none | skimmed | discussed | annotated | trusted
claim_readiness: not-ready | locator-needed | claim-ready | synthesis-ready
last_synthesis_interaction: YYYY-MM-DD
```

Synthesis 可以先保持 draft-quality，用來累積問題與 source gap。當 coverage、feedback
和 claim readiness 都清楚時，才成為 trusted synthesis。

## Common Workflows

### 登錄 paper 並建立早期 draft

```bash
python3 tools/rk.py capture doi "10.1234/example" --title "Example Paper" --topic-id "topic-id"
python3 tools/rk.py distill paper doi_10_1234_example
```

若 full text 不可得，draft 應顯示 `fulltext_status: needs-user-pdf`，並出現在
paper queue。

### 只有在需要時請 user 提供 PDF

```bash
python3 tools/rk.py acquire doi_10_1234_example
```

這會把來源標成需要 user PDF，不會建立新的必經 checkpoint。舊 checkpoint file 仍可
供 legacy record 使用。

### 記錄 user-provided PDF

```bash
python3 tools/rk.py acquire doi_10_1234_example --pdf "/private/path/to/paper.pdf"
```

PDF 留在 private evidence storage。Public wiki 只記錄 safe metadata、reading state
和 locator notes。

### 檢查 locator 並提升 readiness

```bash
python3 tools/rk.py verify-pdf doi_10_1234_example --locator "p. 3 Fig. 2; p. 8 Section 4" --note "Identity and key locators checked."
```

當 PDF、publisher HTML 或 visual artifact 已足以支撐 claim 時使用。若是掃描或
image-only paper，請記錄 visual locator、OCR confidence 和 human reading notes。

### 記錄 feedback

```bash
python3 tools/rk.py paper feedback doi_10_1234_example --level discussed --note "User corrected the interpretation of the method section."
```

Feedback 會更新 paper frontmatter，並 append public-safe event 到 `state/reading/`。
Ledger 幫 RKF 判斷哪些 paper 被 user 深入介入過，但 ledger entry 本身仍不是 claim
evidence。

### 使用 active paper queue

```bash
python3 tools/rk.py paper status
python3 tools/rk.py paper queue
python3 tools/rk.py paper next
python3 tools/rk.py paper nudge --limit 5
```

Queue 會優先列出 metadata-only、需要 user PDF、缺人為 feedback、反覆被問，或已準備
進 synthesis review 的 paper。

## Skill Routing

| Task | Skill | Mode |
|---|---|---|
| Capture DOI/URL/PDF lead | `rkf-evidence-vault` | `capture` |
| Find candidate papers | `rkf-evidence-vault` | `discover` |
| Record missing or user-provided full text | `rkf-evidence-vault` | `acquire` |
| Check locators/readability | `rkf-evidence-vault` | `verify-pdf` |
| Create/update paper draft | `rkf-knowledge-synthesis` | `distill-paper` |
| Save question/concept/claim/synthesis | `rkf-knowledge-synthesis` | `save-*` / `synthesize` |
| Query wiki and record hot demand | `rkf-wiki-core` | `query` / `hot-query` |
| Track paper queue and feedback | `rkf-wiki-core` | `paper-*` |
| Run maintenance checks | `rkf-lint` | `structure`, `evidence`, `graph`, `ARS`, `public-safety` |
| Connect external sandboxes | `rkf-connect` | `sandbox-*` |

## Save Rules

- Query answer 不會自動變成 wiki page，必須明確保存。
- Paper draft 只描述單一 source；跨來源判斷屬於 synthesis。
- Candidate 不是 evidence，但可以啟動 reading draft。
- ARS output 是 proposal，除非 RKF review 將它提升。
- Stable claim 需要 locator support、human feedback、existing RKF source，或明確
  blocker。
- Durable article text、PDF、browser capture、private Drive path、local secret 不得
  commit。

## External Sandboxes

外部 sandbox 應先讀取 generated context capsule：

```bash
python3 tools/rk.py prompt external-sandbox
```

有寫入權限的 trusted sandbox 可以使用 CLI，但必須保留相同的 maturity 與 claim
boundary。如果 sandbox 只有 search results、topic fit 不清楚、缺 full text、reading
maturity 太低，或 locator 不足，就應回傳 proposal，而不是直接改 stable claims。

## Validation

發布或開 PR 前執行：

```bash
python3 -B -m py_compile tools/rk.py rkf/cli.py rkf/core.py rkf/__init__.py tools/public_safety_scan.py
python3 -B -m unittest discover -s tests
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/rk.py lint --mode ars-handoff-lint
python3 tools/rk.py lint --mode public-safety-lint
python3 tools/public_safety_scan.py
```
