# Research Wiki：把研究材料變成可維護的 LLM Wiki

[English README](README.md)

Research Wiki 是一個 GitHub-ready LLM Wiki 研究資料庫模板。它不是單純放 PDF 的資料夾，也不是一次性的聊天摘要；它把文獻來源、全文、閱讀頁、meeting、seminar 和 synthesis 放進同一個可以版本控制、可以診斷、可以交給 Codex 協作的資料庫。

一句話版：

> `raw/` 保留證據，`wiki/` 保存理解，command 處理機械整理，Codex 處理閱讀與判斷。

## 為什麼要用 GitHub-ready LLM Wiki

研究資料很容易散掉：PDF 在資料夾、DOI 在訊息裡、LLM 摘要在另一個聊天視窗、Obsidian 筆記又不知道對應哪個來源。時間一久，很難知道「這篇到底讀完了嗎」、「這個判斷是從哪篇來的」、「這份資料能不能交給別人安裝使用」。

Research Wiki 的目標是讓研究資料有清楚的 evidence chain：

- 來源先進 `raw/`：DOI/URL/PDF source pointer、合法 PDF、staging extraction、QC 後全文、meeting transcript、seminar slides 或其他原始檔。
- 理解再進 `wiki/`：paper page、synthesis、meeting note、project synthesis、seminar note。
- GitHub 管規則與版本：README、core contract、templates、tools、CI、issue 都可以 review。
- Codex 只做需要理解的事：全文 QC、重排、paper page、跨文獻判斷、project discussion。

## 研究材料如何進入資料庫

```mermaid
flowchart TD
    SOURCE["source pointer<br/>DOI / DOI URL / article URL / PDF URL / local PDF"] --> QUEUE["raw/paper_sources.md<br/>尚未解析的來源線索"]
    QUEUE --> RESOLVE["legal source resolution<br/>publisher / author / OA / institution / user-provided"]
    RESOLVE --> PDF["raw/doi_pdf/<br/>原始 PDF evidence"]
    RESOLVE --> STAGE["raw/staging/extracted_text/<br/>機械抽字暫存"]
    PDF --> STAGE
    STAGE --> FT["raw/full_text/<br/>已重排、已 QC、可閱讀全文"]
    FT --> LIT["wiki/literature/<br/>paper reading page"]
    LIT --> SYN["wiki/synthesis/"]
    OTHER["其他原始材料<br/>raw/files/"] --> WIKI2["meeting / seminar / project pages"]
```

論文可以從 DOI、網址、PDF URL 或本機 PDF 開始。這些一開始只是 source pointer；資料庫要做的事，是把它們解析成合法 evidence package，保留 PDF 或原始來源，再把機械抽字放到 staging。只有經過 Codex 重排與 QC 的可閱讀 Markdown，才會進 `raw/full_text/`，也只有這種 full text 才能進一步產生 `wiki/literature/` paper page。

PDF 是 evidence package 的一種重要材料，因為它保留版面、表格、公式、圖說與出版格式。Paper page 不複製整篇全文，而是保存閱讀判斷與來源指標，讓你可以回查 PDF 或 QC 後 full text。

## 安裝與開始使用

需要的基本工具：

- Codex
- Git
- Python 3
- ripgrep (`rg`)

建議工具：

- Poppler / `pdftotext`：從 PDF 抽文字。
- Obsidian：看 wiki graph。
- Chrome：用已登入或已授權的 browser session 打開 publisher 頁面。

如果你不熟 GitHub，打開 Codex，把這段貼給它：

```text
請幫我使用這個 Research Wiki repository。我不熟 GitHub。
請先讀 README.zh-TW.md、core/README.md、USER_GUIDE.zh-TW.md、AGENTS.md，
然後執行 python3 tools/check_install.py。
請用中文告訴我缺什麼工具、下一步要做什麼；不要上傳 private PDF、全文、local path 或 Codex logs。
```

自己手動操作時，打開 `ResearchWiki.command`。它會協助你加入 source pointer、開合法來源頁面、匯入 evidence、產生 QC 後 full text，最後再把 full text 轉成 paper page；詳細選項看 [使用指南](USER_GUIDE.zh-TW.md)。

## Command 的用意

`ResearchWiki.command` 是低 token / 無 token 的操作入口。它的重點不是取代 Codex，而是讓 Codex 不要浪費在掃資料夾、改檔名、重建索引這些機械工作上。

Command 是這個資料模型的預設操作介面，不是資料庫規則來源。它可以做來源輸入、合法來源頁面開啟、PDF/evidence 匯入、staging extraction、Codex full-text QC、wiki ingest、健康檢查與 support issue 草稿；完整選項放在 [使用指南](USER_GUIDE.zh-TW.md)。

## 資料分層

```mermaid
flowchart LR
    CORE["core/<br/>規則、原理、契約、skills"] --> CMD["command layer<br/>ResearchWiki.command + tools/"]
    RAW["raw/<br/>source pointer / PDF / staging / QCed full_text / 原始檔"] --> WIKI["wiki/<br/>paper / synthesis / meeting / seminar"]
    CMD --> RAW
    CMD --> WIKI
    PERSONAL["personal/* branch<br/>個人研究狀態"] -. "不要混進 template main" .-> RAW
```

- `core/`：資料庫規則。若 command 和 core 衝突，以 core 為準。
- `raw/`：證據層，包含 source pointer、PDF、staging、QC 後 full text 與其他原始檔。
- `wiki/`：知識層，保存經過整理的閱讀與研究判斷。
- `maintenance/`：診斷、repair plan、release、branch 說明。
- `personal/*`：個人研究狀態，不應直接混進可發布模板。

## 遇到問題

執行：

```bash
python3 tools/support_report.py --issue-url
```

它會跑安裝檢查、lint、doctor，產生 `maintenance/support_report.md`，並開 GitHub issue 草稿。它會遮蔽常見 private 資訊，例如本機路徑、DOI、raw PDF/full_text 路徑與 Codex logs。

它不會自動送出 issue。送出前，請人工確認草稿沒有 private PDF、全文、敏感 DOI 清單或個人研究狀態。

## 更多文件

- [使用指南](USER_GUIDE.zh-TW.md)
- [安裝指南](INSTALL.zh-TW.md)
- [支援回報](SUPPORT.zh-TW.md)
- [Agent 規則](AGENTS.md)
- [目前 GitHub branch 安排](maintenance/github_current_arrangement.md)
- [Branch strategy](maintenance/branch_strategy.md)
