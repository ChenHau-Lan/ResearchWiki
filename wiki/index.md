---
type: synthesis
status: draft
source_status: personal-note
topics: [index]
created: 2026-05-16
updated: 2026-05-18
sources: []
---

# Research Wiki Index

本頁是 wiki 的總目錄。正式知識分成 paper、code、synthesis 三種主要頁面：paper page 是單篇文獻事實，code page 是實作事實，synthesis page 是研究判斷。三者分開存放，但用 links 互相連接。

## Top-Level Folders

- [[literature/literature|Literature]] - 所有 Zotero 文獻、整理過的 paper pages、keyword pages。
- [[literature/paper_topics|Paper Topics Registry]] - paper frontmatter `topics:` 的主方向清單。
- [[code/code|Code]] - 程式碼、演算法、繪圖邏輯、資料處理流程。
- [[synthesis/synthesis|Synthesis]] - 跨文獻、跨程式碼、跨資料的研究判斷。
- [[concepts/concepts|Concepts]] - 穩定概念、定義、術語與背景知識。
- [[research_records/research_records|Research Records]] - 每次搜尋注入與問題紀錄的主目錄。
- [[concepts/research_wiki_operating_manual|Research Wiki Operating Manual]] - 研究 wiki 的使用習慣、定時搜尋與維護流程。

## Page Roles

- Paper pages: 單篇文獻的研究問題、方法、結果、限制與可引用 claims。
- Code pages: 實作、資料流、參數、繪圖邏輯與輸出解讀。
- Synthesis pages: 跨來源比較、矛盾證據、工作假說與自己的研究判斷。
- Concept pages: 可重複使用的背景概念與機制說明。

## Graph Rules

- Paper pages live flat in `wiki/literature/`.
- Each paper page has `topics` and `keywords` in YAML frontmatter.
- Each paper links to keyword pages named `keyword_*`.
- Cross-paper claims live in `wiki/synthesis/`, not inside a single paper page.
- To isolate a topic in Obsidian, use search/filter on `topics:` or open a `keyword_*` page and use local graph.

## Search Queues

- [[literature/external_search_queue|External Search Queue]] - 大氣常見期刊的 2000 年後 fuzzy-search 工作佇列。
- [[literature/citation_chasing_queue|Citation Chasing Queue]] - 從已整理文獻引用文獻中擴充最相關來源。

## Research Records

- [[research_records/research_records|Research Records]] - 每次搜尋注入與問題紀錄分檔保存。

## Inbox Policy

未驗證素材先放入 `inbox/`，不可直接寫成正式結論。升級成正式頁前需補上來源狀態、可信度、引用或驗證步驟。

## Maintenance

- 每次 ingest 更新本頁。
- 每次重要整理追加 `wiki/log.md`。
- 定期執行 lint：檢查孤兒頁、缺 citation、矛盾 claims 與可升級 inbox 條目。
- 定時搜尋與研究回答需建立 question record、search ingest record 與 synthesis 更新紀錄。
