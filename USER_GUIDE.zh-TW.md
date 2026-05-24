# 使用指南

[English User Guide](USER_GUIDE.md)

Research Wiki 的正式操作面是 **pipeline skills + modes**。這份文件是 reference：告訴你每個 mode 何時使用、可以讀寫哪裡、需要什麼人工確認。第一次操作請先看 [Skill-first 圖文快速開始](docs/manuals/research_wiki_skill_first_quickstart.zh-TW.md)。

## 1. 核心心智模型

```text
source-intake -> paper-ingest -> knowledge-workbench -> synthesis-research -> wiki-lint
```

- `raw/` 是 evidence layer：DOI/URL/PDF queue、dashboard、PDF、staging extraction、QCed full text、原始 meeting/seminar 檔案。
- `wiki/` 是 curated knowledge layer：purpose、overview、hot、literature、concepts、synthesis、meetings、project synthesis、seminars。
- `maintenance/` 是 governance layer：review queue、fan-out candidates、repair plan、runtime state/graph、support report、release hygiene notes。
- `ResearchWikiCodex.command` / `.cmd` 是相容 router；規則來源是 `core/`、`core/skills/` 與 pipeline architecture。

## 2. Mode 總表

| Skill/mode | 何時使用 | 主要輸入 | 允許寫入 | 人工 checkpoint |
| --- | --- | --- | --- | --- |
| `source-intake/add-source` | 加入 DOI、DOI URL、article URL、PDF URL 或來源註記 | 使用者提供的 source pointer | `raw/paper_sources.md`、dashboard 狀態 | source 是否真的是你要追蹤的研究材料 |
| `source-intake/refresh-dashboard` | 同步 source queue、PDF evidence、index 與狀態看板 | `raw/paper_sources.md`、`raw/doi_pdf/` | `raw/doi_dashboard.md`、`raw/full_text_index.*` | dashboard 只代表狀態，不代表已讀證據 |
| `source-intake/qced-full-text` | 從合法或使用者提供來源建立可讀 Markdown 全文 | PDF、authorized HTML/XML/DOM、使用者提供 text | `raw/full_text/paper_file_key.md` | 來源合法性、metadata、段落、表格、公式、圖說可讀性 |
| `paper-ingest/ingest-qced-full-text` | 把 QCed full text 轉成單篇 paper page | `raw/full_text/paper_file_key.md` | `wiki/literature/paper_slug.md`、dashboard 狀態 | full text 是否真的 QC 完成；paper page 不寫 synthesis |
| `knowledge-workbench/query` | 問既有知識庫問題 | `wiki/`、已 index 的 evidence | 不寫檔 | answer 必須標示 evidence tier 與缺口 |
| `knowledge-workbench/query-to-save` | 把 query 結果整理成保存提案 | 上一個 answer 或討論 | 通常不寫正式 wiki；可提 review item | 是否值得保存、target layer 是否明確 |
| `knowledge-workbench/save` | 明確保存 durable knowledge | 已核准內容、target layer | `wiki/concepts/`、`wiki/synthesis/`、`wiki/project_synthesis/`、`maintenance/*` | 寫入前必須選 target layer |
| `knowledge-workbench/review-queue` | 暫存不確定、衝突、低 confidence 或 supersession candidate | 待審內容 | `maintenance/review_queue.md` | 不要把未審 claim 升級成正式 wiki |
| `synthesis-research/fanout-review` | 一篇 source 可能影響多頁時 | paper page、full text、claim | `maintenance/fanout_candidates.md` 或 review proposal | target pages、支持/反對 claim、confidence、counter-evidence |
| `synthesis-research/apply-approved-fanout` | 套用已批准 fan-out item | 明確核准項目 | 核准範圍內的 wiki pages | 每次只套用已批准的一個範圍 |
| `synthesis-research/thesis-review` | 檢查一個研究論點是否成立 | claim、scope、wiki evidence | thesis report、review queue 或 Save proposal | supporting、opposing、mechanistic、meta-review、adjacent evidence 都要看 |
| `synthesis-research/synthesis-page-start` | 開新 synthesis 或 project synthesis 討論 | research question、source set | `wiki/synthesis/` 或 `wiki/project_synthesis/` draft | claim 不可超過 evidence tier |
| `wiki-lint/structure-lint` | 檢查 wiki 結構健康 | repo files | 不寫正式 wiki | frontmatter、index、path、wikilink、Graph Links、orphan pages |
| `wiki-lint/semantic-lint` | 檢查 stale claims、contradictions、evidence tier、反證與 supersession | `wiki/` | audit report / review queue | 不直接把 lint 建議套進正式 wiki |
| `wiki-lint/repair-plan` | 產生人工修復計劃 | repo diagnostics | `maintenance/repair_plan_*.md` | 不自動刪除檔案 |
| `wiki-lint/state-graph` | 更新 runtime state 與 graph export | repo files | `maintenance/state.json`、`maintenance/graph.json` | export 不是正式證據 |
| `wiki-lint/support-report` | 進階支援資訊 | repo diagnostics | support report | 不包含 private raw evidence、完整全文、Codex logs |
| `wiki-lint/feedback-issue` | 進階 GitHub issue 草稿 | 使用者回饋、diagnostics | issue draft / prefilled URL | 不自動送出 issue |

## 3. 如何選 Mode

| 你的意圖 | 選這個 |
| --- | --- |
| 我有一個 DOI/URL/PDF 想放進 queue | `source-intake/add-source` |
| 我放了 PDF，想知道 dashboard 是否看到它 | `source-intake/refresh-dashboard` |
| 我想把合法全文變成可閱讀 Markdown | `source-intake/qced-full-text` |
| 我已經有 QCed full text，想做 paper page | `paper-ingest/ingest-qced-full-text` |
| 我只是問問題，不想改檔 | `knowledge-workbench/query` |
| 我想把回答整理成保存前草稿 | `knowledge-workbench/query-to-save` |
| 我已決定要保存，而且知道寫到哪一層 | `knowledge-workbench/save` |
| 我不確定答案是否可靠 | `knowledge-workbench/review-queue` |
| 一篇 paper 會影響很多頁 | `synthesis-research/fanout-review` |
| 我要測試一個 claim 是否站得住 | `synthesis-research/thesis-review` |
| 我要檢查資料庫健康 | `wiki-lint/structure-lint` 或 `wiki-lint/semantic-lint` |
| 我要產生人工修復計劃 | `wiki-lint/repair-plan` |

直接對 Codex 說像 `Use source-intake/add-source ...` 這樣的 skill/mode 句子即可；如果想用點擊式入口，再打開 `ResearchWikiCodex.command` 或 `ResearchWikiCodex.cmd`。

## 4. Knowledge Workbench 規則

`knowledge-workbench` 合併 Query 與 Save，但用 mode 保留清楚邊界：

- `query`：只讀，不寫檔；回答要標 evidence tier、confidence、missing evidence。
- `query-to-save`：把 answer 轉成 proposal；如果 evidence 不足，應轉入 review queue。
- `save`：寫入前必須選 target layer；不可讓聊天內容直接落到正式 wiki。
- `review-queue`：maintenance-only write，用於低信心、衝突、缺反證、可能取代舊結論的內容。

正式保存時優先考慮：這是單篇 paper 事實、反覆出現的 concept、跨文獻 synthesis、project decision，還是只是一則 maintenance note。

## 5. Evidence 與寫入位置

| Evidence 狀態 | 可以支持什麼 |
| --- | --- |
| `metadata-only` | 只可支持 bibliographic / intake 狀態，不支持內容 claim |
| `abstract-only` | 可做低 tier 摘要線索，不可標 full-read |
| `full-read` | 可支持 paper page 與 synthesis，但仍需反證與範圍限制 |
| seminar / talk | 可作討論脈絡，evidence tier 低於 peer-reviewed full-read literature |
| personal note / hypothesis | 可進 review queue 或 project context，不可偽裝成 literature evidence |

| 要保存的內容 | 目標位置 |
| --- | --- |
| 單篇論文事實 | `wiki/literature/` |
| 反覆使用的術語、方法、資料集、變數 | `wiki/concepts/` |
| 跨文獻判斷 | `wiki/synthesis/` |
| project decision、會議後演化 | `wiki/project_synthesis/` 或 `wiki/meetings/` |
| 不確定、衝突、低 confidence | `maintenance/review_queue.md` |
| 工具執行與維護紀錄 | `maintenance/log.md` |

## 6. 截圖與教學手冊

圖文 walkthrough 放在 `docs/manuals/`，PDF 成品放在 `output/pdf/`。README 只連到最重要入口，不承擔長篇教學。

提交截圖前確認沒有暴露：

- private PDF 或完整 article text；
- 本機 home path；
- 敏感 DOI/source batches；
- browser session、credentials 或 account details；
- Codex logs 或 private conversations。

## 7. 安全與清理

- 不自動化未授權全文取得。
- 不繞過 paywall、CAPTCHA、robots 或 credential barriers。
- 不把完整 article 複製進 `wiki/`。
- 不把 dashboard row 當成 evidence。
- 不把 abstract-only、seminar、personal-note 或 hypothesis material 升級成 full-read peer-reviewed evidence。
- 不使用 recursive、wildcard 或批量刪除命令。
- Repair plan 只診斷與建議，不刪除檔案。

若目錄需要清理，先產出明確候選清單：每個候選都要有 exact path、刪除理由、風險與替代保留位置。真正刪除時一次只處理一個明確路徑。

## 8. Advanced Maintenance

`audit-release` 是進階相容入口。既有名稱仍可理解為：

- `audit-release/semantic-audit` -> `wiki-lint/semantic-lint`
- `audit-release/runtime-state-graph` -> `wiki-lint/state-graph`
- `audit-release/release-hygiene` -> `wiki-lint/repair-plan`

支援報告與 issue 草稿屬於 support workflow。它們可透過 `wiki-lint/support-report`、`wiki-lint/feedback-issue` 或 SUPPORT 文件使用，但不是新手主流程。

## 9. 相關文件

- [Skill-first 圖文快速開始](docs/manuals/research_wiki_skill_first_quickstart.zh-TW.md)
- [Pipeline Architecture](docs/guides/research_wiki_pipeline_architecture.zh-TW.md)
- [README](README.zh-TW.md)
- [安裝指南](INSTALL.zh-TW.md)
- [支援回報](SUPPORT.zh-TW.md)
- [版本紀錄](VERSION_LOG.zh-TW.md)
