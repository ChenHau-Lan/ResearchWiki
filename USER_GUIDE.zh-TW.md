# User Guide 中文摘要

[English User Guide](USER_GUIDE.md)

## 1. 這是什麼

這是一個 LLM Wiki 研究資料庫：

- `core/` 放資料庫規則、原理、skills 與測試契約。
- `raw/` 放證據與輸入。
- `wiki/` 放整理後的知識。
- `ResearchWiki.command` 做本地維護與 Codex handoff，減少不必要 token。
- Codex 負責來源判斷、full text reflow/QC、產生 paper page、做 synthesis。

## 2. 第一次使用

請先打開 Codex 並貼：

```text
請讀 core/README.md、README.md、USER_GUIDE.md、AGENTS.md，然後執行 python3 tools/check_install.py，幫我確認這台電腦是否可以使用 Research Wiki。
```

需要：Codex、Git、Python 3、ripgrep。建議：Obsidian、Poppler、Chrome。

## 3. 論文來源流程

1. 把 DOI、DOI URL、article URL、PDF URL 或來源註記貼到 `raw/paper_sources.md`。
2. 打開 `ResearchWiki.command`。
3. 選 `Paper intake: sources -> QCed full_text`；它會在需要時開合法 source page。
4. 只從 publisher、作者、open-access、institutional access 或使用者已授權來源下載/確認 evidence，合法 PDF 直接放到 `raw/doi_pdf/`。
5. 讓同一個 intake workflow 建 dashboard row、改名、抽 staging text，並交給 Codex CLI 或可貼上的 Codex prompt 重排/QC；成功後才寫入 `raw/full_text/` 並更新 dashboard/index。
6. 進度看 `raw/doi_dashboard.md`。
7. QC 後 full text 產生後，選 `Ingest QCed full_text to wiki`，由 Codex 產生或更新 paper page。

DOI 產生的檔名採 paper-based 命名：`last_name_year_journal_abbrev`。例如 Conrick et al. 2021 in Weather and Forecasting 會變成 `conrick_2021_waf.pdf` 與 `conrick_2021_waf.md`。

如果 shell 下載被 403 / CloudFront 擋住，但你在正常網頁可以看到全文並按 PDF，這會被視為授權瀏覽器 session。預設仍建議讓 `Paper intake` 開頁面、手動下載合法 PDF，再重新跑 `Paper intake` 產生 QC 後 full text；Codex browser capture 只作為 fallback。

不要讓 wiki page 直接從 PDF 生成後就結束。更好的流程是先保存 evidence package：PDF 能合法取得就存 `raw/doi_pdf/`，機械抽字先進 `raw/staging/extracted_text/`，Codex 重排/QC 後才進 `raw/full_text/`，再由 `raw/full_text/` 生成 wiki page。這樣之後重讀、翻譯、索引、修復和引用檢查都比較穩。

DOI dashboard 欄位固定為：

```text
Last Name_Year | Journal | DOI | Wiki Status | 論文取得合法性 | PDF | Full Text
```

較長的下一步與失敗原因會放在同檔案下方的 `DOI Notes`，主看板只保留快速判讀欄位。

## 4. Command 重點項目

- 第 1 項 `Paper intake: sources -> QCed full_text`：主要一鍵流程。可貼 DOI/URL，會開合法來源頁、匯入 PDF/evidence、抽 staging text，並用 Codex CLI 或可貼上的 Codex prompt 產生 QC 後 `raw/full_text/`。
- 第 2 項 `Ingest QCed full_text to wiki`：只從已 QC 的 `raw/full_text/` 產生或更新 `wiki/literature/` paper page；不取得新來源，也不做 full text reflow/QC。
- 第 3 項 `Project / idea conversation`：啟動新的 project / idea 討論，不要求先選 topic；Codex 會在對話後自動判斷 topics、subtopics、相關文獻與 DOI。
- 第 4 項 `Topics / graph`：管理 topic/subtopic registry，或打開 Obsidian graph 說明。
- 第 5 項 `Maintenance / support`：打開 DOI dashboard、執行 health check、產生 repair plan、打開 paper source queue，或產生遮蔽後的 GitHub issue 草稿。

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
