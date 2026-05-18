---
type: synthesis
status: draft
source_status: personal-note
topics: [index]
created: 2026-05-16
updated: 2026-05-17
sources: []
---

# Research Wiki Index

本頁是 wiki 的總目錄。新架構以 `literature/` 與 `code/` 為主；Obsidian Graph View 預設只看 `literature/`，用 keyword pages 呈現論文相關性。

## Top-Level Folders

- [[literature/literature|Literature]] - 所有 Zotero 文獻、整理過的 paper pages、keyword pages。
- [[code/code|Code]] - 程式碼、演算法、繪圖邏輯、資料處理流程。

## Graph Rules

- Paper pages live flat in `wiki/literature/`.
- Each paper page has `topics` and `keywords` in YAML frontmatter.
- Each paper links to keyword pages named `keyword_*`.
- To isolate a topic in Obsidian, use search/filter on `topics:` or open a `keyword_*` page and use local graph.

## Search Queues

- [[literature/external_search_queue|External Search Queue]] - 大氣常見期刊的 2000 年後 fuzzy-search 工作佇列。
- [[literature/citation_chasing_queue|Citation Chasing Queue]] - 從已整理文獻引用文獻中擴充最相關來源。

## Inbox Policy

未驗證素材先放入 `inbox/`，不可直接寫成正式結論。升級成正式頁前需補上來源狀態、可信度、引用或驗證步驟。

## Maintenance

- 每次 ingest 更新本頁。
- 每次重要整理追加 `wiki/log.md`。
- 定期執行 lint：檢查孤兒頁、缺 citation、矛盾 claims 與可升級 inbox 條目。
