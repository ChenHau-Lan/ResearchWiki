# 安裝 Research Wiki

這份文件假設你完全不熟 GitHub。

## 最簡單方式：交給 Codex

打開 Codex，把下面這段貼進去：

```text
請幫我從這個 GitHub repository 安裝 Research Wiki。我不熟 GitHub。請 clone 或打開 repo，讀 core/README.md、README.md、USER_GUIDE.md、AGENTS.md，然後執行 python3 tools/check_install.py。請用中文說明缺什麼工具，不要上傳或公開 private files。
```

## 自己操作

1. 安裝 Git、Python 3、Codex。
2. 下載 private repository：

   ```bash
   git clone git@github.com:ChenHau-Lan/wiki_research.git
   cd wiki_research
   ```

3. 執行安裝檢查：

   ```bash
   python3 tools/check_install.py
   ```

4. 打開 `ResearchWiki.command`。

## 三層概念

- `core/`：資料庫規則、原理、skills、測試契約。
- command：`ResearchWiki.command` 和 `tools/`，只是操作介面。
- personal：你的個人研究資料，應放在 `personal/*` branch 或 ignored raw files。

## 遇到問題

執行：

```bash
python3 tools/support_report.py --issue-url
```

它會產生遮蔽過的 report，並開啟 GitHub issue 草稿。送出前請自己檢查，不要貼 private PDF、全文、local path 或 Codex log。
