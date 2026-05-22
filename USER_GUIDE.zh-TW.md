# User Guide 中文摘要

[English User Guide](USER_GUIDE.md)

## 1. 這是什麼

這是一個 LLM Wiki 研究資料庫：

- `core/` 放資料庫規則、原理、skills 與測試契約。
- `raw/` 放證據與輸入。
- `wiki/` 放整理後的知識。
- `ResearchWiki.command` 做本地維護與 Codex handoff，減少不必要 token。
- Codex 負責取得 full text、產生 paper page、做 synthesis。

## 2. 第一次使用

請先打開 Codex 並貼：

```text
請讀 core/README.md、README.md、USER_GUIDE.md、AGENTS.md，然後執行 python3 tools/check_install.py，幫我確認這台電腦是否可以使用 Research Wiki。
```

需要：Codex、Git、Python 3、ripgrep。建議：Obsidian、Poppler、Chrome。

## 3. DOI 流程

1. 把 DOI 貼到 `raw/doi_list.md`。
2. 打開 `ResearchWiki.command`。
3. 選 `Open authorized PDF pages (recommended first)`，只從 publisher、作者、open-access、institutional access 或使用者已授權來源下載。
4. 把合法 PDF 直接放到 `raw/doi_pdf/`。
5. 回 command 選 `Import PDFs + extract full_text + rebuild index`，由本地工具從 PDF DOI metadata 建 row、改名、抽機械 full text、標記 Codex QC、更新 dashboard/index。
6. 進度看 `raw/doi_dashboard.md`。
7. 機械 full text 產生後，選 `Launch Codex full_text QC + wiki ingest`，由 Codex 重排/QC full text 並產生或更新 paper page。
8. 只有 open publisher HTML/XML、授權瀏覽器 session 或真的需要來源判斷時，才用 `Launch Codex fallback acquisition (slow)`。

DOI 產生的檔名採 paper-based 命名：`last_name_year_journal_abbrev`。例如 Conrick et al. 2021 in Weather and Forecasting 會變成 `conrick_2021_waf.pdf` 與 `conrick_2021_waf.md`。

如果 shell 下載被 403 / CloudFront 擋住，但你在正常網頁可以看到全文並按 PDF，這會被視為授權瀏覽器 session。預設仍建議先用第 5 項開頁面、手動下載合法 PDF，再用第 6 項本地抽 full text；第 3 項只作為 fallback。

建議不要讓 wiki page 直接從 PDF 生成後就結束。更好的流程是先保存 evidence package：PDF 能合法取得就存 `raw/doi_pdf/`，可閱讀全文統一存 `raw/full_text/`，再由 `raw/full_text/` 生成 wiki page。這樣之後重讀、翻譯、索引、修復和引用檢查都比較穩。

DOI dashboard 欄位固定為：

```text
Last Name_Year | Journal | DOI | Wiki Status | 論文取得合法性 | PDF | Full Text
```

較長的下一步與失敗原因會放在同檔案下方的 `DOI Notes`，主看板只保留快速判讀欄位。

## 4. Command 重點項目

- 第 1 項 `Open/add DOI to raw/doi_list.md`：加入或打開 DOI 輸入檔。
- 第 2 項 `Open/manage DOI dashboard`：打開目前 DOI 進度看板。
- 第 3 項 `Launch Codex fallback acquisition (slow)`：只處理例外情況，例如 open publisher HTML/XML、授權瀏覽器 session，或需要判斷合法來源路徑的 DOI。遇到出版社阻擋時不要長時間硬找，應回到 PDF-first 流程。
- 第 4 項 `Generate Codex app fallback acquisition prompt`：不執行 CLI；產生英文 fallback acquisition prompt，寫到 `maintenance/codex_app_handoff_prompt.md`，初始化 `maintenance/codex_app_last_run.log`，可用時複製到剪貼簿，並開啟 Codex app 到本專案。
- 第 5 項 `Open authorized PDF pages (recommended first)`：針對 dashboard 中沒有 PDF 的 DOI 開啟 DOI landing page 與 `raw/doi_pdf/`。只使用 publisher、作者、open-access、institutional access 或使用者已授權 PDF；本專案不自動化 shadow-library / 未授權下載。
- 第 6 項 `Import PDFs + extract full_text + rebuild index`：本地維護，會先檢查 `raw/doi_pdf/` 裡是否有新放入、尚未按規則命名的 PDF；若 PDF 內有 DOI 但 dashboard 沒有 row，會自動建立 row；接著改名為 `<paper_file_key>.pdf`，抽成 machine-extracted `raw/full_text/<paper_file_key>.md`，標記 `codex_qc_full_text`，更新 PDF path / full_text / DOI dashboard，再重建 full_text index。不做文獻理解。
- 第 7 項 `Launch Codex full_text QC + wiki ingest`：前台執行 Codex，先重排與 QC machine-extracted full text，判斷 readability / equation quality / metadata 設定，再從 QCed `raw/full_text/` 產生或更新 `wiki/literature/` paper page；終端只顯示精簡結果。生成頁面只放該篇論文本身內容與必要來源指標，不放空欄位或模板說明。
- 第 8 項 `Launch Codex project conversation`：啟動新的 project / idea 討論，不要求先選 topic；Codex 會在對話後自動判斷 topics、subtopics、相關文獻與 DOI。
- 第 9 項 `Manage topic/subtopic registry`：管理必要的 topic/subtopic registry。
- 第 10 項 `Open Obsidian graph guide`：打開 Obsidian graph 說明，用來理解文獻、synthesis、seminar、meeting、project synthesis 的連結。
- 第 11 項 `Run database health check (diagnose only)`：診斷資料庫問題，例如 stale path、缺 Graph Links、release hygiene、本機絕對路徑與結構異常；不刪檔。
- 第 12 項 `Generate repair plan (no deletes)`：產生分類後的可讀修復計畫，列出建議、風險與安全清理規則；不自動修、不自動刪。
- 第 13 項 `Prepare GitHub support issue (redacted)`：產生遮蔽後的 support report，並開啟 GitHub issue 草稿；不會自動送出。

## 5. Wiki 分區

- `wiki/literature/`：單篇文獻。
- `wiki/synthesis/`：跨文獻判斷。
- `wiki/seminars/`：seminar / talk，證據層級低於 literature。
- `wiki/meetings/`：單次 meeting。
- `wiki/project_synthesis/`：跨 meeting 的 project 整合。

查詢優先順序：

```text
synthesis > literature > seminars
```

問 project history 時：

```text
project_synthesis > meetings
```

## 6. 修復資料庫

```bash
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
```

修復計畫只列建議，不會自動刪除。

如果修復計畫列出 `.DS_Store`，把它當成 release hygiene。先檢查明確路徑，確認安全後一次只刪除一個指定檔案；不要使用 recursive、wildcard 或批量清理命令。

## 7. 測試初始化

只有真的要重測流程時才使用 `InitializeResearchWiki.command`。它會要求你輸入 `INIT TEST DATABASE`，然後只在限定範圍內批量清除測試 evidence、生成 raw artifacts 與生成 wiki pages，保留 tools、templates、skills、docs、topic registry 與 Obsidian 設定。它也會重寫各分區 index pages，避免 index 還指向已刪除的生成頁。

## 8. Obsidian Graph

每個正式頁要有 `Graph Links`，並使用 `[[...]]` wikilinks。這樣 Obsidian graph 才能一眼看出文獻、synthesis、seminar、project、topic、subtopic 的關係。

## 9. 遇到問題

```bash
python3 tools/support_report.py --issue-url
```

工具會產生 `maintenance/support_report.md`，遮蔽本機路徑、DOI、raw PDF/full_text 路徑與 Codex logs，並開啟 GitHub issue 草稿。送出前請人工確認。
