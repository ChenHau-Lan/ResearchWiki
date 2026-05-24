# Research Wiki 版本紀錄

這份文件紀錄 Research Wiki 對使用者可見的重要版本變化。它不是每個 commit 的 changelog，而是讓使用者判斷自己想使用或回到哪個版本的地圖。

## 版本政策

- `v1.x.y`：相容修正、guide 改善、advisory tool、或小型行為釐清。
- `v1.(x+1).0`：相容的使用者可見功能新增。
- `v2.0.0`：data contract、command semantics、必要 frontmatter、資料夾角色或 migration expectation 發生破壞性變更。

## v2.0.0 - Skill-First Pipeline Refactor

日期：2026-05-24
Baseline branch：`codex/skill-first-pipeline-refactor`
狀態：skill-first workflow model 的 proposed PR baseline

### v2.0.0 改變什麼

- 以五個 pipeline skills 取代舊的 14-option command menu 心智模型：
  `source-intake`、`paper-ingest`、`knowledge-workbench`、
  `synthesis-research`、`wiki-lint`；`audit-release` 保留為進階相容入口。
- 把 Query 與 Save 合併到 `knowledge-workbench`，並用 mode-level
  permissions 區分 `query`、`save`、`query-to-save`、`review-queue`。
- 新增 ARS-style pipeline architecture guide，包含 flow、skill/mode matrix、
  artifacts、write permissions、gates、data boundaries。
- 將 `ResearchWikiCodex.command` 降級為薄 skill/mode router 與相容入口。
- 以 skill-first workflow 重寫 README，將 USER_GUIDE 收斂為 mode reference，
  並新增雙語 Skill-first 圖文快速開始。
- 在 `output/pdf/` 產生雙語 README PDF 與 Skill-first quickstart PDF。
- 將舊 full-ingest walkthrough 改成 legacy pointer，修正 fan-out apply
  被誤解為一般下一步的問題。
- 將 LLM Wiki health check 的公開心智模型改為 `wiki-lint`：structure lint、
  semantic lint、repair plan 與 state/graph diagnostics。
- 新增 `maintenance/documentation_cleanup_candidates_2026-05-24.md`，列出
  舊手冊、舊截圖與 `.DS_Store` 的明確清理候選；依安全規則不做模糊批量刪除。

### 相容性說明

- Data model 不變：`raw/` 是證據，`wiki/` 是知識，`maintenance/` 是治理。
- 既有 command-backed 能力仍可透過 skill/mode router 使用，但舊 option
  numbers 不再是主要 UI contract。
- Query 維持 read-only，Save 維持 deliberate，source fan-out 維持 reviewed，
  repair tools 仍不可自動刪除檔案。
- 舊 walkthrough 檔案若保留，只能作為 compatibility pointer；新手教學以
  `docs/manuals/research_wiki_skill_first_quickstart.*.md` 為準。
- `audit-release/semantic-audit`、`audit-release/runtime-state-graph` 與
  `audit-release/release-hygiene` 仍可對應到 `wiki-lint` modes。

## v1.0.0 - Research Wiki vNext Baseline

日期：2026-05-23  
Baseline branch：`origin/codex/vnext-research-compiler-governance` after PR #14  
狀態：v1 improvement stack 的目前穩定基準

### v1.0.0 包含什麼

- Evidence chain：`raw/` 保存來源證據，`wiki/` 保存整理後知識，`maintenance/` 保存治理與 runtime artifacts。
- 四個一級 action：Query、Save、Lint、Research。
- 保守 paper ingest：source -> QCed full text -> paper page；一篇 source 對多頁的影響要先經 fan-out candidate/review。
- Frontmatter vNext 欄位：identity、confidence、evidence tier、counter-evidence、review queue、provenance、supersession。
- Concept、purpose、overview、hot question、synthesis、meeting、project-synthesis、seminar、paper page 類型。
- `maintenance/state.json` 與 `maintenance/graph.json` runtime exports。
- Thesis mode scaffolding：supporting、opposing、mechanistic、meta-review、adjacent evidence、evidence table、verdict proposal。
- 雙語 full-ingest walkthrough manual，示範目前可見的 `pdf_template/` 範例集。

### 相容性說明

- 這個版本是 template-safe：raw PDFs 與 raw full text 不屬於可發布 baseline。
- Query 依契約維持 read-only。
- Save、fan-out apply、semantic lint、thesis mode、state/graph export 都是明確 action。
- Dashboard row 是狀態視圖，不是 evidence source of truth。

## 如何更新本檔

當 PR 改變使用者可見 workflow、command behavior、data contract、guide structure 或 version policy，就新增一筆版本紀錄。內容保持短而清楚，PR body 再連回相關 PR。
