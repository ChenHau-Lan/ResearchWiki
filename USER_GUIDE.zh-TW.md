# User Guide 中文摘要

[English User Guide](USER_GUIDE.md)

這份文件是給第一次拿到 Research Wiki 的人。你不需要先懂 GitHub、Markdown database 或 Obsidian；先照這份走就可以。

## 1. 先記住兩件事

Research Wiki 做的是這條流程：

```mermaid
flowchart LR
    A["來源<br/>DOI / URL / PDF"] --> B["raw/<br/>證據 + QC 後全文"]
    B --> C["wiki/literature/<br/>paper page"]
    C --> D["wiki/synthesis/<br/>跨文獻判斷"]
```

- `raw/` 放證據：來源、PDF、暫存抽字、QC 後全文、meeting transcript、seminar slides。
- `wiki/` 放理解：單篇文獻頁、跨文獻 synthesis、meeting、project、seminar。

不要把剛從 PDF 機械抽出的文字當成正式全文。正式全文只放在 `raw/full_text/`，而且必須已經由 Codex 重排與 QC。

## 2. 第一次安裝

最簡單的方式是把安裝交給 Codex 帶你做。打開 Codex，貼上：

```text
請幫我安裝並啟動 Research Wiki。我不熟 GitHub。
如果我還沒有 repository，請協助 clone git@github.com:ChenHau-Lan/wiki_research.git；如果已在 repo 中，請直接使用目前目錄。
請先讀 README.zh-TW.md、USER_GUIDE.zh-TW.md、INSTALL.zh-TW.md、AGENTS.md。
請檢查 Git、Python 3、ripgrep/rg、Poppler/pdftotext、Codex CLI 是否可用。
如果缺工具，請先說明用途；需要 Homebrew、系統安裝或權限時先問我再執行。
安裝或確認後，請執行 python3 tools/check_install.py --strict。
成功後請告訴我怎麼打開 ResearchWiki.command。不要上傳 private PDF、全文、本機路徑、敏感 DOI 清單或 Codex logs。
```

需要的工具是 Codex、Git、Python 3、ripgrep。建議安裝 Poppler / `pdftotext`、Obsidian、Chrome。

## 3. 資料放在哪裡

README 只講最短流程；細節放在這裡。

| 位置 | 放什麼 | 注意 |
| --- | --- | --- |
| `core/` | 規則、原理、contract、skills | command 如果和 core 衝突，以 core 為準 |
| `raw/paper_sources.md` | 新 DOI、DOI URL、article URL、PDF URL | 這是待處理來源 queue |
| `raw/doi_pdf/` | 合法取得或使用者提供的論文 PDF | 檔名應整理成 `<paper_file_key>.pdf` |
| `raw/staging/extracted_text/` | PDF/HTML/XML 機械抽字暫存 | 不是正式全文，不進 index，不產生 wiki |
| `raw/full_text/` | 已重排、已 QC、可閱讀的全文 Markdown | 這才是 wiki ingest 的正式輸入 |
| `wiki/literature/` | 單篇論文閱讀頁 | 不複製全文，只放閱讀判斷與來源指標 |
| `wiki/synthesis/` | 跨文獻判斷 | 有新理解時更新這裡 |
| `maintenance/` | 診斷、repair plan、support report | 不屬於正式 wiki 知識層 |

個人研究狀態、私人 DOI batch、還不能公開的 raw evidence，應留在 ignored files 或 `personal/*` branch，不要混進可發布的 template/main。

## 4. 論文怎麼進資料庫

大多數時候先記住兩段：

1. 用 `Paper intake` 先把 DOI/URL/PDF 整理成合法 evidence、PDF、staging text，然後明確選 Codex reflow/QC 才產生 `raw/full_text/`。
2. 用 `Ingest QCed full_text to wiki` 把已 QC 的 `raw/full_text/` 變成 `wiki/literature/`。

更完整的流程是：

1. 把 DOI、DOI URL、article URL、PDF URL 或來源註記貼到 `raw/paper_sources.md`，或在 command 中貼上。
2. 打開 `ResearchWiki.command`。
3. 選 `Paper intake`。
4. 只使用合法來源：publisher、作者頁、open-access、institutional access、你已授權的 browser session、或你自己提供的 PDF/text。
5. 如果需要手動下載 PDF，把合法 PDF 放到 `raw/doi_pdf/`，再重新跑同一個 intake。
6. 先選 local/no-token 的 import：建立或更新 dashboard、整理檔名、抽 staging text、重建 index。
7. staging 準備好後，再選 Codex reflow/QC；QC 成功後才會寫入 `raw/full_text/`，並更新 `raw/full_text_index.*`。
8. 再選 `Ingest QCed full_text to wiki` 產生 paper page。

進度看 `raw/doi_dashboard.md`。主表只放快速判讀欄位：

```text
Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text
```

較長的下一步、失敗原因與備註會放在同檔案下方的 `DOI Notes`。

## 5. Command 五個選項

1. `Paper intake`：論文來源入口。裡面分成 local/no-token：加入來源、開合法來源頁、匯入 PDF、抽 staging、重建 index；以及 LLM：Codex reflow/QC staging -> full_text、Codex source-resolution fallback。
2. `Ingest QCed full_text to wiki`：只從已 QC 的 `raw/full_text/` 產生或更新 `wiki/literature/`。它不找新 PDF，也不做 full text reflow/QC。
3. `Project / idea conversation`：和 Codex 討論 project 或 idea，讓 Codex 事後整理 topics、subtopics、相關文獻與 DOI。
4. `Topics / graph`：管理 topic/subtopic registry，或打開 Obsidian graph 說明。
5. `Maintenance / support`：打開 dashboard、跑 health check、產生 repair plan、開 paper source queue，或產生遮蔽後的 GitHub issue 草稿。

如果你只是要處理論文，先只記第 1 和第 2 項。

## 6. Wiki 分區

- `wiki/literature/`：單篇文獻。
- `wiki/synthesis/`：跨文獻判斷。
- `wiki/seminars/`：seminar / talk，證據層級低於 literature。
- `wiki/meetings/`：單次 meeting。
- `wiki/project_synthesis/`：跨 meeting 的 project 整合。

一般研究問題優先看：

```text
synthesis > literature > seminars
```

問 project history 或 meeting decision 時優先看：

```text
project_synthesis > meetings
```

## 7. Obsidian Graph

把 `wiki/` 當成 Obsidian vault 打開。

正式頁應有 `Graph Links`，並使用 `[[...]]` wikilinks。這樣 Obsidian graph 才能看出文獻、synthesis、seminar、project、topic、subtopic 的關係。

## 8. 維護與修復

平常可以跑：

```bash
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
```

修復計畫只列建議，不會自動刪除。若 repair plan 提到 `.DS_Store` 或其他雜訊，先檢查明確路徑，確認安全後一次只刪除一個指定檔案；不要使用 recursive、wildcard 或批量清理命令。

只有真的要重測流程時才使用 `InitializeResearchWiki.command`。它會要求輸入 `INIT TEST DATABASE`，再重置測試 evidence、生成 raw artifacts 與生成 wiki pages；不要拿它當日常清理工具。

## 9. 遇到問題或要發 Issue

可以讓 Codex 產生 issue 草稿。貼上：

```text
Research Wiki 安裝或執行遇到問題，請幫我產生 GitHub issue 草稿。
請先讀 SUPPORT.zh-TW.md，然後執行 python3 tools/support_report.py --issue-url。
請檢查 maintenance/support_report.md 和產生的 issue URL 是否已遮蔽本機路徑、private PDF、全文、敏感 DOI 清單、Codex logs 和個人研究狀態。
不要自動送出 issue；請把草稿交給我確認。
```

手動執行時：

```bash
python3 tools/support_report.py --issue-url
```

它會產生 `maintenance/support_report.md`，遮蔽常見 private 資訊，並開啟 GitHub issue 草稿。送出前仍要人工確認。
