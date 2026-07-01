# RKF Auto-Connect Workflow

這份文件說明如何在任何 Codex 專案連結 RKF 資料庫，讓研究相關搜尋、DOI/URL lead、網頁 clip、ChatGPT 片段與有價值研究討論自動回饋到 RKF。

## 啟用方式

在專案中對 agent 說：

```text
連結我的 RKF 資料庫
```

Agent 會使用全域 `rkf-auto-connect` skill，從 `$HOME/.codex/rkf_connector.toml` 找到 ResearchWiki checkout，再由 ResearchWiki 的 `rkf.workspace.toml` 解析 live `wiki_root`。

## 自動記錄政策

RKF auto-connect 使用 Active/Aggressive hybrid policy。

Active trigger 會自動記錄：

- DOI、arXiv、PubMed、ISBN、dataset DOI；
- paper title、citation、journal/conference、literature search；
- 被用作 evidence 的重要 URL；
- 網頁短摘錄或 source-backed summary；
- 反覆出現、適合進 `hot.md` 的研究問題。

Aggressive research trigger 也會自動記錄：

- 文獻 synthesis 或比較；
- method、model、experiment design；
- manuscript/proposal argument；
- claim evaluation；
- figures、datasets、diagnostics、equations 的研究解讀；
- 可回用 idea、hypothesis、caveat、open question。

## 寫入位置

- 搜尋需求與反覆研究問題：`hot.md`
- ChatGPT/web/project clip：`knowledge/inbox/`
- DOI/URL source identity：`state/sources/*.json`
- DOI 相關 paper：guarded paper backlink
- 清楚 target source 的閱讀問題或修正：`state/reading/*.json`

## 不會自動做的事

- 不自動升級 stable claim。
- 不保存整篇 article text。
- 不保存整段私人 ChatGPT transcript。
- 不保存 PDF、browser capture、private path、secret 或個資。
- 不覆寫 project `AGENTS.md` 或既有 project memory。

## 專案範圍標記

如果要讓某專案長期記得 RKF auto-connect，可以在專案根目錄建立 `.rkf-connect.toml`：

```toml
[rkf_auto_connect]
enabled = true
mode = "active-aggressive"
config = "global"
```

這個檔案不得存 private Drive path；真正的 RKF 路徑由全域 config 與 `rkf.workspace.toml` 解析。

## 取消或暫停

在目前 session 可直接說：

```text
這個 thread 暫停 RKF auto-capture
```

專案層級則移除或停用 `.rkf-connect.toml`：

```toml
[rkf_auto_connect]
enabled = false
mode = "active-aggressive"
config = "global"
```

## 回報格式

Agent 自動記錄後應簡短回報：

```text
已自動記錄到 RKF: inbox + hot-query；沒有 promote stable claim。
```

如果因 private path、全文過長或 project rule 被擋，agent 應改成 pending capture proposal。
