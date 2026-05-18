# Research Wiki Agent Instructions

本專案是研究知識庫，用來整理文獻、程式碼邏輯、繪圖邏輯、演講素材、影片紀錄與日常想法。核心模式採用 Karpathy LLM Wiki：原始資料不可變，wiki 是可累積的整理層，`AGENTS.md` 是維護規則。

## Deletion Safety

禁止批量刪除文件或目錄。
不要使用：
- `del /s`
- `rd /s`
- `rmdir /s`
- `Remove-Item -Recurse`
- `rm -rf`

需要刪除文件時，只能一次刪除一個明確路徑的文件。若需要批量刪除文件，停止操作並請使用者手動刪除。

## Canonical Layers

- `raw/` 是原始來源層，保存 PDF、Zotero 匯出、照片、影片、逐字稿、網頁剪輯、程式碼片段與資料檔。LLM 可讀取，但不應修改原始內容。
- `inbox/` 是未整理素材層，保存演講照片、影片筆記、口頭想法、靈感與未驗證觀察。預設狀態是 `needs-verification`。
- `wiki/` 是正式知識層，由 LLM 維護 Markdown 頁面，適合 Obsidian 瀏覽與 Git 追蹤。
- `references.bib` 是正式文獻 citation 的唯一 BibTeX 來源。
- `templates/` 保存新頁模板。建立新頁時優先沿用模板，而不是臨時發明格式。
- `notion/` 保存 Notion dashboard/mirror 的規劃或匯出內容。本地 Markdown repo 是 source of truth。

## Knowledge Boundaries

本 wiki 採用三種正式知識頁分工：

- Paper page 是單篇文獻事實，放在 `wiki/literature/`。內容應忠實記錄該文獻的研究問題、方法、結果、限制、可引用 claims，以及針對該單篇文章的個人評論。
- Code page 是實作事實，放在 `wiki/code/`。內容應記錄程式碼、資料流、參數、繪圖邏輯、輸出與限制；不要把整個 codebase 複製進 wiki。
- Synthesis page 是研究判斷，放在 `wiki/synthesis/`。跨文獻比較、跨程式碼解讀、研究假說、矛盾證據與工作中的結論都應放在 synthesis page。

Paper、code、synthesis 應分開存放，但用 wiki links 互相連接。不要把跨文獻推論寫成單篇 paper 的作者結論。

## Research Integrity

- 不捏造 citation。引用前必須確認 title、authors、venue/year、DOI 或 canonical URL。
- 必須標記來源狀態：`peer-reviewed`、`preprint`、`dataset`、`software`、`talk`、`personal-note`、`non-academic`。
- 非平凡學術主張需有 citation、明確原始來源，或清楚標記為假說/想法。
- 每個非平凡研究主張應在同段或同 bullet 內標註 citation key、raw path、code path，或明確標記為 hypothesis。
- `references.bib` 與文獻頁 metadata 必須一致。
- 只讀摘要或二手資料時，必須明確標註閱讀限制，不可假裝已讀全文。

## Taxonomy

正式 wiki 以頁面角色分區，但 frontmatter 的 `topics` 仍以研究主題分類。

Top-level wiki folders:

- `wiki/literature/`：單篇文獻頁、文獻 keyword pages、文獻佇列。
- `wiki/code/`：程式碼、資料流、演算法、繪圖邏輯、實驗實作。
- `wiki/synthesis/`：跨文獻、跨程式碼、跨資料的研究判斷。
- `wiki/concepts/`：穩定概念、定義、術語與背景知識。

`topics` 是少量、穩定、高層研究領域。Paper page 的 `topics:` 必須優先從 `wiki/literature/paper_topics.md` 的 active list 選取，例如 `aerosol`、`microphysics`、`cloud_physics`、`remote_sensing`、`modeling`、`instrumentation`、`tropical_cyclone`、`precipitation`、`wildfire`、`radar_meteorology`、`field_campaign`、`climate_change`。

`keywords` 是較細的研究概念、方法、資料集、機制或現象，用來建立 Obsidian graph，例如 `aerosol_cloud_interaction`、`drop_size_distribution`、`microphysics_scheme`。只有當某個 keyword 預期會連到多篇 paper、code page 或 synthesis page，才建立 `keyword_*` 或 concept page。

## Wiki Page Frontmatter

每個正式 wiki page 必須使用 YAML frontmatter：

```yaml
---
type: paper | concept | method | code | dataset | talk | idea | synthesis
status: draft | reviewed | needs-verification | deprecated
source_status: peer-reviewed | preprint | dataset | software | talk | personal-note | non-academic
reading_status: metadata-only | abstract-only | skimmed | full-read | reproduced | mixed
review_stage: ai-extracted | human-checked | discussed | integrated | cited
topics: []
keywords: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
---
```

## Standard Workflows

### ingest-paper

1. 讀取 PDF、Zotero item、DOI、URL 或使用者提供的 metadata。
2. 驗證 citation metadata；若無法驗證，標記為 `needs-verification`。
3. 更新或建立 `references.bib` entry。
4. 使用 `templates/paper.md` 建立文獻頁。
5. 單篇文獻事實寫入 paper page；跨文獻判斷只寫入 `wiki/synthesis/`。
6. 更新相關 keyword/concept pages 與 synthesis pages。
7. 更新 `wiki/index.md`。
8. 在 `wiki/log.md` 追加一筆 `ingest-paper` 紀錄。

### ingest-code

1. 讀取相關程式碼、README、notebook 或 commit context。
2. 摘要目的、資料流、核心函式、參數選擇、繪圖邏輯與輸出解讀。
3. 使用 `templates/code.md` 建立或更新 code knowledge page。
4. 引用來源檔案、commit 或 raw code path；不要把整個 codebase 重寫進 wiki。
5. 若需要解釋此實作如何影響研究判斷，更新對應 synthesis page，而不是塞進 code page。
6. 更新 `wiki/index.md` 與 `wiki/log.md`。

### capture-inbox

1. 將照片、影片、逐字稿或臨時想法放入 `raw/` 或 `inbox/`。
2. 使用 `templates/inbox.md` 建立 inbox 條目。
3. 標記可信度與下一步：查文獻、問人、實作測試或丟棄。
4. 不把 inbox 內容寫成正式結論。
5. 更新 `wiki/log.md`。

### lint-wiki

檢查：
- 缺 citation 或 citation key 不存在於 `references.bib`。
- Paper page 的 title/year/authors/DOI 是否與 `references.bib` 一致。
- Synthesis claim 是否至少連到一個 paper page、code page 或 raw source。
- 孤兒頁或未被 `wiki/index.md` 收錄的正式頁。
- 互相矛盾或過時的 claims。
- `inbox/` 中可升級為正式 wiki 的條目。
- topic pages 中缺少 cross-reference 的概念。

Lint 後需在 `wiki/log.md` 追加 `lint-wiki` 紀錄。

## Query Behavior

回答問題時先讀 `wiki/index.md`，再讀相關 topic/page。回答需區分：

- 已驗證 peer-reviewed 文獻。
- preprint 或非同行審查來源。
- 程式碼實作經驗。
- inbox 或 personal-note 中的未驗證觀察。

若 wiki 不足以回答，說明缺口並建議應補充的來源或下一步搜尋策略。
