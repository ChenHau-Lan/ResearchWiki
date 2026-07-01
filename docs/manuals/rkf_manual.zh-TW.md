# Research Knowledge Framework Manual

RKF 是一個 LLM Wiki-based research knowledge framework。它的工作是保存
durable、source-aware 的 academic knowledge，同時讓 paper 理解可以在多次 session
中主動累積。

現在的模型是 reading maturity first, claim boundary second。Paper 可以先從
metadata、abstract、partial full text 或 user-provided PDF 進入 wiki 成為 draft。
Draft 必須誠實記錄現在讀到哪裡。Stable claim、trusted synthesis、citation
confidence、publication 則仍然需要 locator、人為 feedback、既有 governed RKF source，
或明確 review blocker。

RKF 與 Codex `academic-research-suite` skill 並行使用：ARS 負責 search、reason、
write、review；RKF 決定什麼會變成 durable wiki memory，什麼仍是 reading draft
或 proposal。

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
observed_at: YYYY-MM-DD
valid_from: YYYY-MM-DD
valid_until: optional
supersedes: optional
```

Synthesis 可以先保持 draft-quality，用來累積問題與 source gap。當 coverage、feedback
和 claim readiness 都清楚時，才成為 trusted synthesis。

## Common Workflows

### 保存 ChatGPT 或網頁片段到 inbox

在 Codex app 說：「把這段 ChatGPT 或 web clip 存到 RKF inbox。來源摘要、DOI/URL、
我的 reader note、AI/agent note 要分開。」

Inbox item 是低風險 capture object。DOI 只會建立或連回 `SourceRecord` 和 paper
backlink，不會自動升級成 stable claim。

### 登錄 paper 並建立早期 draft

在 Codex app 說：「把這個 DOI/URL 登錄到 RKF，並建立保守 paper draft；就算目前只有
metadata 或 abstract 也可以。」

若 full text 不可得，draft 應顯示 `fulltext_status: needs-user-pdf`，並出現在
paper queue。

### 只有在需要時請 user 提供 PDF

在 Codex app 說：「列出哪些已登錄 paper 需要我提供 PDF 或 authorized full text。」

這會把來源標成需要 user PDF，不會建立新的必經 checkpoint。舊 checkpoint file 仍可
供 legacy record 使用。

### 記錄 user-provided PDF

在 Codex app 說：「我有這篇 paper 的 PDF，請更新 full-text status，並保留 private
evidence 邊界。」

PDF 留在 private evidence storage。Public wiki 只記錄 safe metadata、reading state
和 locator notes。

### 檢查 locator 並提升 readiness

在 Codex app 說：「檢查這篇 paper 的 locator/readability，判斷是否足以提升 claim
readiness。」

當 PDF、publisher HTML 或 visual artifact 已足以支撐 claim 時使用。若是掃描或
image-only paper，請記錄 visual locator、OCR confidence 和 human reading notes。

### 記錄 feedback

在 Codex app 說：「記錄我剛討論、註解、修正或信任這篇 paper，並追加 public-safe
event 到 reading ledger。」

Feedback 會更新 paper frontmatter，並 append public-safe event 到 `state/reading/`。
Ledger 幫 RKF 判斷哪些 paper 被 user 深入介入過，但 ledger entry 本身仍不是 claim
evidence。

### 使用 active paper queue

在 Codex app 說：「顯示 RKF active paper queue，以及下一批需要 PDF、feedback、
locator 或 synthesis review 的 paper。」

Queue 會優先列出 metadata-only、需要 user PDF、缺人為 feedback、反覆被問，或已準備
進 synthesis review 的 paper。

### 用 world context 開始 session

在 Codex app 說：「開始這個 session 前，先給我 RKF world context。」

`world` 會回傳 L0-L3 context capsule：critical facts、active reading、
claim readiness、contradiction hints、graph links 與 validation state。

### Evolve 既有頁面

在 Codex app 說：「用 `evolve` 把這個低風險更新整合到既有頁面，並留下 AI
Integration Note。」

低風險更新可以直接 rewrite existing pages，但必須留下 AI Integration Note。高風險
stable claim promotion、source identity conflict、publication-ready synthesis、
delete/merge choices 應寫成 blocker 或 maturity downgrade。

### Reconcile 矛盾並 challenge synthesis

在 Codex app 說：「Reconcile 這個 topic 的矛盾，並只用既有 RKF knowledge challenge
這個 synthesis。」

`reconcile` 會把矛盾標成 AI-integrated blockers。`challenge` 只回傳 counterpoints
與 downgrade suggestions，不建立 stable claims。

### 發現 unnamed patterns

在 Codex app 說：「從目前 reading queue、hot demand、feedback gaps 和 topic state
找 unnamed patterns；如果寫入，保持 low maturity。」

Auto-synthesis 只使用既有 RKF reading、hot-query、feedback 與 topic state。它不需要
candidate records，且一律從 low maturity 開始。

## Skill Routing

| Task | Skill | Mode |
|---|---|---|
| Capture DOI/URL/PDF lead | `rkf-evidence-vault` | `capture` |
| Find candidate papers | `rkf-evidence-vault` | `discover` |
| Record missing or user-provided full text | `rkf-evidence-vault` | `acquire` |
| Check locators/readability | `rkf-evidence-vault` | `verify-pdf` |
| Create/update paper draft | `rkf-knowledge-synthesis` | `distill-paper` |
| Save question/concept/claim/synthesis | `rkf-knowledge-synthesis` | `save-*` / `synthesize` |
| Find unnamed patterns | `rkf-knowledge-synthesis` | `emerge` |
| Query wiki and record hot demand | `rkf-wiki-core` | `query` / `hot-query` |
| Evolve or challenge existing pages | `rkf-wiki-core` | `evolve` / `challenge` |
| Track paper queue and feedback | `rkf-wiki-core` | `paper-*` |
| Run maintenance checks or reconcile contradictions | `rkf-lint` | `structure`, `evidence`, `graph`, `ARS`, `public-safety`, `reconcile` |
| Connect other Codex sessions or projects | `rkf-connect` | `handoff-*` |

## Save Rules

- Query answer 不會自動變成 wiki page，必須明確保存。
- Paper draft 只描述單一 source；跨來源判斷屬於 synthesis。
- Candidate 不是 evidence，但可以啟動 reading draft。
- ARS output 是 proposal，除非 RKF review 將它提升。
- `emerge` 不需要 candidate records，且一律先是 draft synthesis。
- 每次 AI rewrite 都需要 AI Integration Note。
- Stable AI-integrated claim/synthesis content 需要 `observed_at` 和
  `valid_from`。
- Stable claim 需要 locator support、human feedback、existing RKF source，或明確
  blocker。
- Durable article text、PDF、browser capture、private Drive path、local secret 不得
  commit。

## Codex Handoff Contexts

其他 Codex session 或 connected project 應先收到 generated RKF context capsule 與相同
reading-boundary rules。預設是 read/proposal 邊界。如果 handoff context 只有 search
results、topic fit 不清楚、缺 full text、reading maturity 太低，或 locator 不足，就應
回傳 proposal，而不是直接改 stable claims。

Trusted handoff context 可以回傳 `evolve`、`reconcile` 或 `emerge` 更新，但必須保持
AI-marked 且 maturity-aware。RKF 內不新增 open-web 或 multimodal ingest pipeline；
外部研究擴展主要交給 ARS。

## Validation

發布或開 PR 前，請 Codex 執行最小相關驗證。最後回報要列出跑了哪些 tests、lint、
public-safety checks，哪些檢查因環境或範圍沒有執行。
