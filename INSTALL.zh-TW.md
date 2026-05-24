# 安裝 Research Wiki

這份文件假設你完全不熟 GitHub。

## 最簡單方式：交給 Codex

打開 Codex，把下面這段貼進去：

```text
請幫我安裝並啟動 Research Wiki。我不熟 GitHub。
如果我還沒有 repository，請協助 clone git@github.com:ChenHau-Lan/wiki_research.git；如果已在 repo 中，請直接使用目前目錄。
請先讀 README.zh-TW.md、USER_GUIDE.zh-TW.md、INSTALL.zh-TW.md、AGENTS.md。
請檢查 Git、Python 3、ripgrep/rg、Poppler/pdftotext、Codex CLI 是否可用。
如果缺工具，請先說明用途；需要 Homebrew、系統安裝或權限時先問我再執行。
安裝或確認後，請執行 python3 tools/check_install.py --strict。
成功後請告訴我怎麼使用 Research Wiki pipeline skills，以及可選的 ResearchWikiCodex.command router。
不要上傳 private PDF、全文、本機路徑、敏感 DOI 清單或 Codex logs。
```

這個 prompt 可以完成大部分安裝流程，但它不應該在沒有你確認的情況下安裝系統工具或送出任何 GitHub issue。

## 自己操作

1. 安裝 Git、Python 3、Codex。
2. 下載 private repository：

   ```bash
   git clone git@github.com:ChenHau-Lan/wiki_research.git
   cd wiki_research
   ```

3. 執行安裝檢查：

   ```bash
   python3 tools/check_install.py --strict
   ```

4. 如果想使用薄 skill/mode router，macOS 打開 `ResearchWikiCodex.command`，Windows 打開 `ResearchWikiCodex.cmd`。
5. 需要初始 topic 時，打開 `InitializeResearchWiki.command` 或 `InitializeResearchWiki.cmd`。
6. 可選的 runtime smoke check：

   ```bash
   python3 tools/wiki_lint.py
   python3 tools/wiki_doctor.py
   python3 tools/build_runtime_state.py
   ```

## 需要的工具

- 必要：Codex、Git、Python 3、ripgrep (`rg`)。
- 建議：Poppler / `pdftotext`、Obsidian、Chrome。

資料怎麼放、論文怎麼進 wiki，請看 [USER_GUIDE.zh-TW.md](USER_GUIDE.zh-TW.md)。README 只保留最短流程。

vNext 使用上先記住四個 action：Query 只讀不寫，Save 保存有來源支撐的知識，Lint 檢查結構與語義，Research 產出 evidence-labeled 更新或 review item。

## 遇到問題

也可以交給 Codex 產生 issue 草稿：

```text
Research Wiki 安裝或執行遇到問題，請幫我產生 GitHub issue 草稿。
請先讀 SUPPORT.zh-TW.md，然後執行 python3 tools/support_report.py --issue-url。
請檢查 maintenance/support_report.md 和產生的 issue URL 是否已遮蔽本機路徑、private PDF、全文、敏感 DOI 清單、Codex logs 和個人研究狀態。
不要自動送出 issue；請把草稿交給我確認。
```

手動執行：

```bash
python3 tools/support_report.py --issue-url
```

它會產生遮蔽過的 report，並開啟 GitHub issue 草稿。送出前請自己檢查，不要貼 private PDF、全文、local path 或 Codex log。
