# Research Wiki Agent Instructions

本專案是 GitHub-ready Karpathy-style LLM Wiki 研究資料庫模板。核心原則是：

- `core/` 是 command-independent source of truth，保存資料庫原理、資料契約、agent 契約、skills 與測試契約。
- `raw/` 是 evidence layer，保存 paper source pointers、DOI dashboard、原始檔、staging extraction、QC 後可讀全文與索引。
- `wiki/` 是 LLM-curated knowledge layer，保存單篇文獻事實、跨文獻判斷、meeting/project 脈絡與 seminar context。
- `ResearchWiki.command` 是 core contract 的一個 command/UI implementation，負責低 token / 無 token 的本地操作，也負責把需要理解的任務交接給 Codex。
- Codex / LLM token 應用在真正需要理解的任務：文獻攝入、全文理解、paper page 萃取、synthesis、project discussion。

與一般 LLM Wiki 不同處：

1. 有客製化 paper source queue、DOI dashboard、full text cache 與 full text index。
2. Paper wiki page 對文獻閱讀最佳化，但不複製全文。
3. Command 讓使用者快速操作，避免把機械檢查浪費在 LLM token；預設論文流程進入 `Paper intake`，其中加入來源、開合法來源頁、匯入 PDF、改名、抽 staging、重建 index 都是 local/no-token 步驟。Codex reflow/QC staging -> full_text 與 source-resolution fallback 是明確 LLM 步驟，不應被包進本地 maintenance。
4. Obsidian graph 是一級功能，正式頁必須有 explicit wikilinks。
5. 資料庫要能被定期診斷、產生 repair plan，但不可自動批量刪除。

## Research Wiki Dev Mode

當使用者討論「資料庫要如何更新、目錄/command/DOI workflow/maintenance/Obsidian graph/skills/templates 要如何修改」時，啟用 Research Wiki Dev Mode。

此 mode 的角色：

- 以資深研究資料庫架構師與產品工程師的角度協作。
- 先保護 evidence chain，再追求自動化與便利性。
- 偏好更少目錄、更少概念、更清楚流程；新增功能前先判斷是否真的必要。
- 將 `raw/`、`wiki/`、`maintenance/` 分層清楚：raw 是證據，wiki 是知識，maintenance 是操作與診斷。
- Command 只放低 token / 無 token 或必要 handoff；LLM token 留給文獻理解、研究判斷與使用者討論。
- 對高風險功能主動指出限制：不可自動批量刪除，不可自動化未授權全文取得，不讓 dashboard 取代真實檔案證據。
- README 只放第一眼需要知道的研究材料流程、安裝入口與支援入口；不要把詳細資料分層、branch policy、測試觀察或架構討論塞進 README。資料位置與操作細節放 USER_GUIDE，規則與契約放 `core/`，維護紀錄放 `maintenance/`。
- 安裝與支援文件若提供 Codex prompt，README、USER_GUIDE、INSTALL、SUPPORT 必須保持一致；prompt 可以協助安裝與開 issue 草稿，但系統工具安裝需使用者確認，issue 不得自動送出。
- 處理 review comment 或使用者修正時，先抽象成資料模型、workflow、產品原則或契約規則，再整合進既有架構；不可把回饋中的反應式問句、例子或修正文直接變成 README/USER_GUIDE 段落標題。版本變更、PR 回應與測試觀察應留在 PR、release notes 或 `maintenance/`，不要塞進 onboarding 文件。
- 實作時同步更新 README / USER_GUIDE / AGENTS / command menu，並跑最小必要驗證。
- 回應風格保持溫和、直接、有判斷力；不只照做，也要指出會讓資料庫長期壞掉的設計。

## Core / Command / Personal Boundary

- 核心規則優先讀 `core/principles.md`、`core/data_contract.md`、`core/agent_contract.md`、`core/test_contract.md` 與 `core/skills/`。
- Command prompt 或工具若需要規則，必須引用 `core/*`；不要讓 `ResearchWiki.command` 成為唯一規則來源。
- `main` 是 private protected integration branch 的目標狀態，應保持 template-safe。
- `codex/core-*` 用於 core contract；`codex/command-*` 用於 command/UI；`personal/*` 用於個人研究狀態。
- Issue 回報採 redacted prefilled URL；不自動送出，也不貼 private raw PDF/full_text/Codex logs。

## Updating AGENTS.md During Tests

`AGENTS.md` 會影響未來 Codex 如何理解與操作整個 repo，因此不要把它當成測試筆記本。

- 臨時測試觀察：寫到 `maintenance/`、test report 或 issue，不直接改 `AGENTS.md`。
- 核心規則改變：先改 `core/agent_contract.md`、`core/data_contract.md` 或相關 `core/*`，再讓 `AGENTS.md` 保持簡短索引。
- Command 操作細節改變：改 `USER_GUIDE*` 或 command prompt，不把細節塞進 `AGENTS.md`。
- 個人偏好或個人研究流程：放到 `personal/*` branch，不進 template `main`。
- 若確實需要改 `AGENTS.md`，必須走 PR，並同步更新 README / USER_GUIDE 中對使用者有影響的部分。

## Deletion Safety

禁止批量刪除文件或目錄。
不要使用：

- `del /s`
- `rd /s`
- `rmdir /s`
- `Remove-Item -Recurse`
- `rm -rf`

需要刪除文件時，只能一次刪除一個明確路徑的文件。若需要批量刪除文件，停止操作並請使用者手動刪除。

Repair tools must never delete files automatically. They may only write a human-readable repair plan.

如果 `wiki_doctor.py` 或 repair plan 回報 `.DS_Store`，只把它當作 release hygiene。工具可以列出明確路徑與人工建議，但不可自動清理；若要處理，必須由人確認後一次只刪除一個指定檔案，不可使用 recursive、wildcard 或批量清理命令。

例外：`InitializeResearchWiki.command` 是本地測試用初始化工具，使用者已明確允許它在受限範圍內批量刪除測試資料。它必須要求互動式確認，只能清理 generated raw artifacts、`raw/doi_pdf/`、`raw/full_text/`、`raw/files/` 與正式 wiki 分區中的生成頁，並保留 tools、templates、skills、docs、topic registry 與 Obsidian 設定。它也應重寫各分區 index pages，避免 index 指向已刪除的生成頁。

## Active Scope

正式主流程只維護：

- Paper page：單篇論文閱讀頁，放在 `wiki/literature/`。
- Synthesis page：跨文獻研究判斷，放在 `wiki/synthesis/`。
- Meeting page：單次會議紀錄，放在 `wiki/meetings/`。
- Project synthesis page：跨會議、project evolution、decision history、project 間關聯，放在 `wiki/project_synthesis/`。
- Seminar page：seminar / talk 紀錄，放在 `wiki/seminars/`。

操作維護層不屬於正式 wiki：repair plan、release checklist、Codex logs、Obsidian graph 說明放在 repo 根目錄的 `maintenance/`。

不要恢復 code wiki、inbox、Notion mirror、同步腳本或副資料庫流程。若被提到，只記錄到 `DEFERRED_FEATURES.md`。

## Canonical Files

- `raw/paper_sources.md`：主要論文來源入口，可貼 DOI、DOI URL、article URL、PDF URL 或來源註記。
- `raw/doi_list.md`：legacy DOI-only 入口，保留相容性。
- `raw/doi_dashboard.md`：DOI 處理狀態看板，不是 evidence source of truth。
- `raw/doi_pdf/`：DOI 對應 PDF，命名為 `<paper_file_key>.pdf`。
- `raw/staging/extracted_text/`：PDF/HTML/XML 機械抽字暫存，不是正式 full text，不進 full_text index。
- `raw/full_text/`：已重排、已 QC、可供閱讀與 wiki ingest 的全文 Markdown，命名為 `<paper_file_key>.md`。
- `raw/full_text_index.md` 與 `raw/full_text_index.json`：全文、DOI、paper page 的 dispatch index。
- `raw/files/`：seminar slides、meeting transcript 或使用者提供的其他原始檔；DOI 論文 PDF 優先放 `raw/doi_pdf/`。
- `wiki/literature/topic_registry.md`：topics、subtopics 與 graph hub 規則。
- `references.bib`：後期正式 citation registry。

真正證據永遠是實際存在的 raw/doi_pdf、raw/staging、raw/full_text、wiki/literature、raw/full_text_index.* 與 raw/files。Dashboard 只記錄處理狀態；若 dashboard 指到不存在的檔案，工具必須降級狀態。

## Query Priority

一般研究問題預設查詢順序：

1. `wiki/synthesis/`
2. `wiki/literature/`
3. `wiki/seminars/`

只有使用者問 project history、meeting decision、action tracking、跨 project 關聯時，才優先查：

1. `wiki/project_synthesis/`
2. `wiki/meetings/`

Seminar 可作為 synthesis 的討論材料，但 evidence tier 低於 peer-reviewed literature。Abstract-only paper 不可當成 full-read evidence。

## DOI Status Board

`raw/doi_dashboard.md` 的狀態只使用：

- `new`：剛加入，尚未處理。
- `metadata_ok`：已確認 title/authors/year/venue/DOI。
- `full_text_needed`：metadata 有了，但還沒有可讀全文。
- `full_text_done`：已生成 `raw/full_text/<paper_file_key>.md`。
- `wiki_done`：已生成 `wiki/literature/<slug>.md`。
- `abstract_only`：只能取得摘要，paper page 必須標明限制。
- `blocked`：DOI 錯誤、來源不可用、權限不足或需要人工處理。

Dashboard 主看板欄位固定為 `Last Name_Year`、`Journal`、`DOI`、`Wiki Status`、`Access Legality`、`PDF`、`Full Text`。較長的 `Next Action`、`Updated`、`Note` 放在同檔案的 `DOI Notes` 區塊，避免主看板太難讀。每次處理 DOI 後，至少更新 wiki status、論文取得合法性、PDF、Full Text、Next Action、Updated 與 Note。

## Paper Ingest Workflow

本資料庫將論文攝入分成三段：

### A. Source Resolution And Evidence Import

1. 從 `raw/paper_sources.md` 讀取 DOI、DOI URL、article URL、PDF URL 或來源註記；legacy `raw/doi_list.md` 仍可讀取 DOI。
2. 查重：`raw/doi_dashboard.md`、`raw/doi_pdf/`、`raw/staging/`、`raw/full_text/`、`raw/full_text_index.*`、`raw/files/`。
3. 驗證 citation metadata；不可捏造 title、authors、venue/year、DOI 或 URL。
4. 優先採用 source-first 半自動流程：開啟 DOI/publisher/article/source 頁面，讓使用者從 publisher、作者、open-access、institutional access 或使用者已授權來源下載 PDF 到 `raw/doi_pdf/`，或確認合法 HTML/XML/full text。Codex fallback 才處理 publisher HTML/XML、授權瀏覽器 PDF download、授權瀏覽器 DOM 或特殊來源判斷。不要自動化 shadow-library 或未授權 PDF 下載。
5. DOI PDF 若能合法取得，統一存到 `raw/doi_pdf/<paper_file_key>.pdf`。PDF 是原始版面 evidence，建議保存，但若 publisher HTML/XML/DOM 已提供完整全文，PDF 缺失不應阻止 wiki ingest；應標為 PDF backfill。
6. PDF/HTML/XML 機械抽字只能寫到 `raw/staging/extracted_text/<paper_file_key>.md`，不得寫入 `raw/full_text/`，也不得進 full_text index。
7. 若使用者手動下載 PDF，直接放到 `raw/doi_pdf/`。本地 command 應掃描該資料夾中的額外 PDF；若 PDF 內有 DOI 但 dashboard 沒有 row，必須建立 dashboard row，之後改名為 `<paper_file_key>.pdf`，抽成 staging text，下一步設為 `codex_convert_to_full_text`。
8. 這一段不要建立或更新 paper page，也不要寫 synthesis。

### B. Full-Text Reflow/QC

1. Codex 必須從 `raw/staging/extracted_text/`、合法 HTML/XML/DOM 或使用者提供全文產生可閱讀 Markdown。
2. 只有完成 reflow/QC 後，才可寫入 `raw/full_text/<paper_file_key>.md`。
3. 正式 full text frontmatter 必須標記 `extraction_status: codex_qc_done` 與 `qc_status: codex_qc_done`，並設定 `readability_status` 與 `equation_quality`。
4. QC 失敗時，不建立 `raw/full_text/`，dashboard 保持 `full_text_needed`，下一步設為 `codex_convert_to_full_text`，並記錄 blocker。
5. 新增或修正文獻全文後，執行 `python3 tools/build_full_text_index.py`。
6. Codex QC 完成後，回填 `raw/doi_dashboard.md`：標 `full_text_done`，下一步設為 `ingest_full_text_to_wiki`。
7. 這一段不要建立或更新 paper page，也不要寫 synthesis。

### C. Wiki Ingest

1. 只從已存在且 QC 完成的 `raw/full_text/<paper_file_key>.md` 讀取全文。
2. 從 full text 萃取 `wiki/literature/<slug>.md`，並設定 `reading_status: full-read`。
3. 若只有 metadata 或 abstract，也可建立 paper page，但必須設定 `reading_status: metadata-only` 或 `abstract-only`，不可假裝已讀全文。
4. Paper page 只放該篇論文本身內容與必要來源指標；不要放 template field guide、空欄位、操作紀錄、通用 Zotero boilerplate 或沒有資訊量的維護段落。
5. 回填 `raw/doi_dashboard.md`：paper page 完成且 full-read 時標 `wiki_done`。
6. 若跨文獻判斷改變，更新 `wiki/synthesis/`，不是塞進單篇 paper page。

`paper_file_key` 規則：`first_author_last_name_year_journal_abbrev`，全部小寫 ASCII，空白與標點改為 `_`。期刊有常見縮寫時使用縮寫；例如 `Weather and Forecasting` 可用 `waf`，`Atmospheric Chemistry and Physics` 可用 `acp`。若同名衝突，追加短 DOI slug，例如 `_waf_d_21_0044_1`。

## Frontmatter

正式 wiki page 必須使用 YAML frontmatter：

```yaml
---
type: paper | synthesis | meeting | project-synthesis | seminar
status: draft | reviewed | needs-verification | deprecated
source_status: peer-reviewed | preprint | dataset | software | talk | personal-note | non-academic
reading_status: metadata-only | abstract-only | skimmed | full-read | reproduced | mixed
review_stage: ai-extracted | human-checked | discussed | integrated | cited
topics: []
subtopics: []
keywords: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
---
```

Navigation/support pages may keep support metadata, but they must not introduce new content categories.

## Topics, Subtopics, Keywords

- `topics`：少量、穩定、高層研究領域。
- `subtopics`：更精準的檢索分類，只有反覆使用才提升為 active。
- `keywords`：自由但可控的細節詞，不一定建立 graph node。

優先使用 `wiki/literature/topic_registry.md`。不要把每個 keyword 都升級成 subtopic。

## Obsidian Graph Links

每個正式頁都要包含：

```md
## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related synthesis:
- Related seminars:
- Related projects:
```

使用 explicit wikilinks，例如 `[[topic_aerosol]]`、`[[subtopic_wildfire_smoke_microphysics]]`、`[[synthesis/synthesis]]`。不要只依賴 YAML，因為 Obsidian graph 對明確 wikilinks 最友善。

## Maintenance And Repair

定期執行：

```bash
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
```

修復檢查重點：

- DOI dashboard duplicate / invalid DOI / stale paths。
- full_text index 是否與實際檔案一致。
- paper page 是否缺 DOI、reading_status、source_status、full text evidence。
- synthesis 是否至少引用 paper / seminar / raw source。
- seminar 是否標明 `talk` / non-peer-reviewed context。
- project_synthesis 是否連回 meetings 或 project sources。
- Obsidian unresolved links、orphan pages、missing Graph Links。
- GitHub release 前檢查本機路徑、`.DS_Store`、private raw data、workspace noise。
- `.DS_Store` 修復只列明確路徑與安全清理建議，不自動刪除；禁止用批量清理讓 release checklist 變乾淨。

Repair plan 只產生建議，不自動刪除。
