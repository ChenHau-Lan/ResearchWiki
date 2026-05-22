# Research Wiki 中文快速說明

[English README](README.md)

這是一個 GitHub 可上架的 Karpathy-style LLM Wiki 研究資料庫模板。

核心精神：

- `core/` 是 command-independent source of truth，保存原理、資料契約、agent 契約、skills 與測試契約。
- `ResearchWiki.command` 做低 token / 無 token 的本地操作。
- Codex / LLM 做真正需要理解的文獻攝入、萃取、討論與 synthesis。
- `raw/` 保存證據；`wiki/` 保存整理後的知識。
- Obsidian graph 是一級功能，每個重要頁面都要有明確 wikilinks。
- 資料庫要能被定期診斷與修復，但不自動批量刪除。

## 最快開始

1. 用 Codex 打開 repo。
2. 請 Codex 檢查需要的工具：

   ```text
   請讀 core/README.md、README.md、USER_GUIDE.md、AGENTS.md，然後執行 python3 tools/check_install.py，幫我確認這台電腦是否可以使用 Research Wiki。
   ```

3. 打開 `ResearchWiki.command`。
4. 把 DOI 貼到 `raw/doi_list.md`。
5. 選 `Open authorized PDF pages (recommended first)`，只從 publisher、作者、open-access、institutional access 或使用者已授權來源下載 PDF，並放到 `raw/doi_pdf/`。
6. 回 command 選 `Import PDFs + extract full_text + rebuild index`，由本地工具從 PDF DOI metadata 建 row、改名、抽機械文字、標記 Codex QC、更新 dashboard/index。
7. 機械 full text 產生後，再選 `Launch Codex full_text QC + wiki ingest`，由 Codex 重排/QC full text 並產生或更新 paper page。
8. 只有 open publisher HTML/XML、授權瀏覽器 session 或真的需要來源判斷時，才用 `Launch Codex fallback acquisition (slow)`。

## Command 重要項目

- 第 1 項 `Open/add DOI to raw/doi_list.md`：加入或打開 DOI 輸入檔。
- 第 2 項 `Open/manage DOI dashboard`：打開目前 DOI 進度看板。
- 第 3 項 `Launch Codex fallback acquisition (slow)`：只處理例外情況，例如 open publisher HTML/XML、授權瀏覽器 session，或需要判斷合法來源路徑的 DOI。遇到出版社阻擋時不要長時間硬找，應回到 PDF-first 流程。
- 第 4 項 `Generate Codex app fallback acquisition prompt`：不執行 CLI；產生 fallback acquisition prompt，寫到 `maintenance/codex_app_handoff_prompt.md`，初始化 `maintenance/codex_app_last_run.log`，可用時複製到剪貼簿，並開啟 Codex app 到本專案。
- 第 5 項 `Open authorized PDF pages (recommended first)`：針對 dashboard 中沒有 PDF 的 DOI 開啟 DOI landing page 與 `raw/doi_pdf/`。只使用 publisher、作者、open-access、institutional access 或使用者已授權 PDF；本專案不自動化 shadow-library / 未授權下載。
- 第 6 項 `Import PDFs + extract full_text + rebuild index`：本地維護，會先檢查 `raw/doi_pdf/` 裡是否有新放入、尚未按規則命名的 PDF；若 PDF 內有 DOI 但 dashboard 沒有 row，會自動建立 row；接著改名為 `<paper_file_key>.pdf`，抽成 machine-extracted `raw/full_text/<paper_file_key>.md`，標記 `codex_qc_full_text`，更新 PDF path / full_text / DOI dashboard，再重建 full_text index。不做文獻理解，目標是不消耗 token。
- 第 7 項 `Launch Codex full_text QC + wiki ingest`：前台執行 Codex，先重排與 QC machine-extracted full text，判斷 readability / equation quality / metadata 設定，再從 QCed `raw/full_text/` 產生或更新 `wiki/literature/` paper page；終端只顯示精簡 QC/ingest 結果。生成頁面應只放該篇論文本身內容與必要來源指標，不放空欄位或模板說明。
- 第 8 項 `Launch Codex project conversation`：啟動新的 project / idea 討論，英文 prompt 會要求 Codex 先和使用者釐清問題，再自動判斷 topics、subtopics、相關文獻與是否需要新增 DOI。
- 第 9 項 `Manage topic/subtopic registry`：管理必要的 topic/subtopic registry。
- 第 10 項 `Open Obsidian graph guide`：打開 graph 使用說明，讓使用者知道如何看 literature、synthesis、seminar、meeting、project synthesis 的關係。
- 第 11 項 `Run database health check (diagnose only)`：只診斷問題，例如 stale path、缺 Graph Links、release hygiene、本機絕對路徑與結構異常；不刪檔。
- 第 12 項 `Generate repair plan (no deletes)`：把第 11 項可能發現的問題整理成 `maintenance/repair_plan_YYYY-MM-DD.md`，並附上分類後的人工修復建議；仍不自動刪檔。
- 第 13 項 `Prepare GitHub support issue (redacted)`：產生遮蔽後的 support report，並開啟 GitHub issue 草稿；送出前必須人工確認。

DOI 產生的檔名採 paper-based 命名：`last_name_year_journal_abbrev`。例如 Conrick et al. 2021 in Weather and Forecasting 會變成 `conrick_2021_waf`。

若 shell 下載被 403 / CloudFront 擋住，但使用者在正常網頁可以看到全文並按 PDF，這代表可走授權瀏覽器 session。不過預設仍建議先用第 5 項開頁面、手動下載合法 PDF，再用第 6 項本地抽 full text；第 3 項只作為 fallback。

如果第 3 項是在 command-line Codex session 被 browser automation 權限擋住，可改用第 4 項：它會產生 prompt、開啟 Codex app，你把 prompt 貼到 Codex app 對話裡執行。此 prompt 會要求 Codex app 把重要過程追加到 `maintenance/codex_app_last_run.log`。完成後回到 command 跑第 6 項更新 dashboard，再跑第 7 項產生 wiki page。

如果你手動下載 PDF，不需要放到 Downloads 給 command 找。直接把 PDF 放進 `raw/doi_pdf/`，再執行第 6 項；command 會檢查 `raw/doi_pdf/` 裡的額外 PDF，能比對 DOI/title 時自動改名、抽 full text，並更新資料庫。

架構上，wiki page 不需要直接從 PDF 生成。較穩定的流程是 `DOI -> evidence package(PDF if available + full_text.md) -> wiki page`。若 publisher HTML/XML/DOM 已提供完整全文，`full_text.md` 可以先進 wiki；PDF 缺失則作為後續 backfill。

DOI dashboard 採精簡欄位：

```text
Last Name_Year | Journal | DOI | Wiki Status | 論文取得合法性 | PDF | Full Text
```

較長的失敗原因與下一步會放在同檔案下方的 `DOI Notes`，主看板保持可讀。

## 查詢優先順序

一般研究問題：

```text
synthesis > literature > seminars
```

如果問 project history、meeting decision、跨 project 關聯：

```text
project_synthesis > meetings
```

## 主要目錄

```text
core/                 資料庫原理、契約、skills、測試契約
raw/                  DOI、PDF、全文、原始檔
raw/doi_pdf/          DOI PDF，使用 paper-based 檔名
raw/full_text/        可閱讀全文 Markdown，使用 paper-based 檔名
wiki/literature/      單篇文獻
wiki/synthesis/       跨文獻研究判斷
wiki/meetings/        單次會議紀錄
wiki/project_synthesis/ 跨會議 project 整合
wiki/seminars/        seminar / talk 紀錄
maintenance/          修復、release、Obsidian graph 說明
```

`ResearchWiki.command` 和 `tools/` 只是 core contract 的實作；若 command 與 `core/` 規則衝突，以 `core/` 為準。

## 定期修復

```bash
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
```

`generate_repair_plan.py` 只產生建議，不會自動刪除。

如果 doctor / repair plan 列出 `.DS_Store`，那是 release hygiene。先檢查明確路徑，確認安全後一次只刪除一個指定檔案；不要使用 recursive、wildcard 或批量清理命令。

## 測試初始化

`InitializeResearchWiki.command` 可以把本地資料庫重設成乾淨測試狀態。它會要求你輸入 `INIT TEST DATABASE`，然後只在限定範圍內批量清除測試 evidence、生成 raw artifacts 與生成 wiki pages，保留 tools、templates、skills、docs、topic registry 與 Obsidian 設定。它也會重寫各分區 index pages，避免 index 還指向已刪除的生成頁。只有真的要重測流程時才使用。

## 遇到問題

```bash
python3 tools/support_report.py --issue-url
```

此工具會寫入 `maintenance/support_report.md`，並開啟預填 GitHub issue URL。它會遮蔽本機路徑、DOI、raw PDF/full_text 路徑與 Codex logs，但送出前仍要人工確認。
