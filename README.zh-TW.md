# Research Wiki：把 DOI 變成可以查的研究資料庫

[English README](README.md)

Research Wiki 是一個給研究者用的 GitHub-ready LLM Wiki 模板。它把 DOI、合法 PDF、抽出的 full text、paper page、meeting、seminar 和 synthesis 放在同一個可版本控制的研究資料庫裡。

一句話版：

> 機械整理交給 command，本地 evidence 留在 `raw/`，需要理解的閱讀與判斷再交給 Codex。

## 為什麼要用 GitHub-ready LLM Wiki

一般把論文丟進資料夾或聊天紀錄裡，常見問題是：PDF 找得到但不知道讀到哪、LLM 產生的摘要沒有 evidence chain、不同電腦之間狀態不同步、Obsidian 裡有頁面但不知道來源是否可靠。

這個模板想解決的是：

- 研究資料可以版本控制：規則、模板、工具、wiki page 都能 review 和回溯。
- evidence 和知識分層：PDF / full text 留在 `raw/`，整理後的理解放在 `wiki/`。
- LLM token 用在值得的地方：Codex 負責 QC、閱讀、判斷和寫作；掃描、改名、重建 index 交給本地 command。
- 新手遇到問題可以回報：support report 會產生遮蔽過的 issue 草稿，而不是把 private 資料直接丟上 GitHub。

## 這次模板做了什麼改變

- 新增 `core/`：把資料庫原理、規則、skills 和測試契約從 command 裡抽出來。
- 重新定義 command：`ResearchWiki.command` 只是操作介面，不再是規則來源。
- 改成 PDF-first workflow：先取得合法 PDF，再由第 6 項本地抽 full text，第 7 項才交給 Codex QC / ingest。
- 加入 GitHub 支援：CI、issue template、PR template、安裝文件、support report。
- 加入新手文件：用 README 快速理解，用 USER_GUIDE 查細節。
- 把 private evidence 排除在 Git 外：raw PDF、full_text、support report、Codex logs 不應進入 repo。

## 從 DOI 到 Wiki 的核心流程

```mermaid
flowchart TD
    A["貼 DOI 到 raw/doi_list.md"] --> B["ResearchWiki.command 第 5 項<br/>開合法 PDF 頁面"]
    B --> C["手動下載合法 PDF<br/>放進 raw/doi_pdf/<br/>PDF 是原始 evidence"]
    C --> D["第 6 項<br/>改名、抽 full_text、更新 dashboard/index"]
    D --> E["第 7 項<br/>Codex 重排/QC full_text"]
    E --> F["產生 wiki/literature paper page"]
    F --> G["需要跨文獻判斷時<br/>再寫 wiki/synthesis"]

    B -. "找不到 PDF 或需要來源判斷" .-> H["第 3/4 項<br/>Codex fallback acquisition"]
    H --> D
```

正常情況下，不要一開始就叫 Codex 慢慢找全文。先用第 5 項打開合法來源頁面，把 PDF 放進 `raw/doi_pdf/`，再用第 6 項讓本地工具抽文字。Codex 最值得用在第 7 項：重排全文、做 QC、理解論文、寫 paper page。

## 快速安裝與操作

需要的基本工具：

- Codex
- Git
- Python 3
- ripgrep (`rg`)

建議工具：

- Poppler / `pdftotext`：從 PDF 抽文字。
- Obsidian：看 wiki graph。
- Chrome：用已登入或已授權的 browser session 打開 publisher 頁面。

檢查安裝：

```bash
python3 tools/check_install.py
```

操作順序：

1. 打開 `ResearchWiki.command`。
2. 選第 1 項，把 DOI 貼進 `raw/doi_list.md`。
3. 選第 5 項，從合法頁面下載 PDF。
4. 把 PDF 放進 `raw/doi_pdf/`。
5. 選第 6 項，讓本地工具整理 PDF 和 full_text。
6. 選第 7 項，讓 Codex 做 full_text QC 和 paper page。

## 完全不懂 GitHub 時

打開 Codex，把這段貼給它：

```text
請幫我使用這個 Research Wiki repository。我不熟 GitHub。
請先讀 README.zh-TW.md、core/README.md、USER_GUIDE.zh-TW.md、AGENTS.md，
然後執行 python3 tools/check_install.py。
請用中文告訴我缺什麼工具、下一步要做什麼；不要上傳 private PDF、全文、local path 或 Codex logs。
```

然後照 Codex 說的做。你不需要先懂 branch、PR 或 GitHub Actions；這些可以等資料庫真的需要同步或 review 時再處理。

## PDF 也是來源嗎？

是。PDF 是重要的原始 evidence source，尤其用來檢查頁面版面、表格、公式、圖說和抽字是否錯誤。

但資料庫裡有兩種不同用途：

- `raw/doi_pdf/<paper_file_key>.pdf`：原始 PDF evidence，保留版面與出版格式。
- `raw/full_text/<paper_file_key>.md`：給 Codex 和 wiki ingest 用的可讀全文。

Paper page 通常不直接複製 PDF 或全文內容，而是從 QC 過的 full text 萃取研究重點，並保留 `source_pdf` / `source_path` 讓人可以回查 evidence。若 publisher HTML/XML 已經提供完整合法全文，PDF 可以後補；但只要 PDF 存在，它就是 evidence chain 的一部分。

## 三層結構

```mermaid
flowchart LR
    C["core/<br/>規則、原理、契約、skills"] --> CMD["command layer<br/>ResearchWiki.command + tools/"]
    CMD --> W["raw/ + wiki/<br/>你的資料庫內容"]
    P["personal/* branch<br/>個人研究狀態"] -. "不要混進 template main" .-> W
```

- `core/`：資料庫規則。若 command 和 core 衝突，以 core 為準。
- `ResearchWiki.command` / `tools/`：操作介面，只實作 core 規則。
- `raw/`：證據層，例如 DOI、PDF、full_text、原始檔。
- `wiki/`：知識層，例如 paper page、synthesis、meeting、seminar。
- `maintenance/`：診斷、repair plan、release、branch 說明，不是正式 wiki 知識。
- `personal/*` branch：個人研究狀態，不應直接混進可發布模板。

## 支援回報是什麼

遇到問題時，不要手動貼一堆本機路徑或 PDF 內容到 issue。先跑：

```bash
python3 tools/support_report.py --issue-url
```

它會做這件事：

```mermaid
flowchart TD
    A["你遇到問題"] --> B["support_report.py 跑 install/lint/doctor"]
    B --> C["產生 maintenance/support_report.md"]
    C --> D["遮蔽 local path、DOI、raw PDF/full_text、Codex logs"]
    D --> E["產生 GitHub issue 草稿 URL"]
    E --> F["你人工檢查"]
    F --> G["確認沒 private 內容後才送出"]
```

重點：它只準備 issue 草稿，**不會自動送出**。最後要不要送出，永遠由人確認。

## 測試時不小心動到 AGENTS.md 怎麼辦

先不要直接把測試中的 `AGENTS.md` 改動推進 `main`。

判斷方式：

- 臨時測試想法：寫到 `maintenance/` 或 issue，不改 `AGENTS.md`。
- 核心規則真的變了：先改 `core/agent_contract.md` 或 `core/data_contract.md`，再讓 `AGENTS.md` 簡短指向它。
- command 操作細節變了：改 `USER_GUIDE.zh-TW.md` 或 command prompt。
- 只是你的個人偏好：放到 `personal/chenhau-lan` branch。

`AGENTS.md` 會影響未來 Codex 如何工作，所以它應該走 PR，不要當成測試筆記。

## 什麼時候用 Codex

適合用 Codex：

- 判斷全文來源是否合法、可用。
- 把 machine-extracted full_text 重排成可讀 Markdown。
- 檢查 equation/table/section 是否被抽壞。
- 從 full_text 寫 paper page。
- 做 synthesis、project discussion、meeting/seminar 脈絡整理。

不適合浪費 Codex token：

- 掃描資料夾。
- 重建 index。
- 檢查 dashboard path 是否 stale。
- 把 PDF 改成 canonical 檔名。
- 產生 repair plan 的機械診斷。

這些應該交給 `ResearchWiki.command` 和 `tools/`。

## 常用命令

```bash
python3 tools/check_install.py
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
python3 tools/support_report.py --issue-url
```

`generate_repair_plan.py` 只產生建議，不會自動刪檔。

## 要重測資料庫流程

只有真的要重測時才用：

```text
InitializeResearchWiki.command
```

它會要求你輸入：

```text
INIT TEST DATABASE
```

然後只清理受限範圍內的測試 evidence、生成 raw artifacts 和生成 wiki pages。它會保留工具、模板、skills、docs、topic registry 和 Obsidian 設定。

## 更多文件

- [使用指南](USER_GUIDE.zh-TW.md)
- [安裝指南](INSTALL.zh-TW.md)
- [支援回報](SUPPORT.zh-TW.md)
- [Agent 規則](AGENTS.md)
- [目前 GitHub branch 安排](maintenance/github_current_arrangement.md)
- [Branch strategy](maintenance/branch_strategy.md)
