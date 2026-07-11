# RKF Auto-Connect Workflow

這份文件說明如何在任何 Codex 專案按需連結 RKF。新 task 預設 RKF OFF；只有使用者明確啟動後，研究搜尋、DOI/URL lead、網頁 clip、ChatGPT 片段與研究討論才會查詢或送入 RKF。

## 啟用方式

在每個新 task 中對 agent 說：

```text
啟動 RKF
```

Agent 會使用全域 `rkf-auto-connect` skill 解析 ResearchWiki checkout，再由
`rkf.workspace.toml` 找到 live storage。它只會把 `rkf.activate` request 交給目前
task 的 session-owned runtime；preflight 不寫入任何 knowledge page。

狀態規則：

- `OFF`：所有 query/capture action 都被拒絕。
- `ACTIVE`：可使用 `query.search` 與 `capture.route`；是否能投影由 writer registry 決定。
- `ACTIVE_READ_ONLY`：可查詢，capture 只能排入 event queue 或被 guard 阻擋。
- 新 task 不繼承前一個 task 的 ACTIVE 狀態。

## 一般流程

1. 新 task 預設 RKF OFF。
2. 使用者說「啟動 RKF」。
3. Agent 執行 `rkf.activate`，先回報 ACTIVE 或 ACTIVE_READ_ONLY 與 warning。
4. 研究型請求先執行 `query.search`，再視不足處讀 project-local 資料。
5. DOI、URL、paper lead 或可重用研究討論經 `capture.route` 進入 event queue。
6. 回報 event ID、dedupe、queued/materialized 與 `Promotion: none`。
7. 使用者說「停用 RKF」後執行 `rkf.deactivate`。

## 啟動後的記錄政策

啟動後，RKF 使用 Active/Aggressive hybrid classifier；它決定建議 capture 的內容，
不代表 agent 可以在 OFF 狀態自動寫入。

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

- 所有接受的 capture：先進 append-only `state/events/`
- 搜尋需求與反覆研究問題：由 designated writer 投影到 `hot.md`
- ChatGPT/web/project clip：由 designated writer 投影到 `knowledge/inbox/`
- DOI/URL source identity：`state/sources/*.json`
- DOI 相關 paper：guarded paper backlink
- 清楚 target source 的閱讀問題或修正：`state/reading/*.json`

## 不會自動做的事

- 不自動升級 stable claim。
- 不保存整篇 article text。
- 不保存整段私人 ChatGPT transcript。
- 不保存 PDF、browser capture、private path、secret 或個資。
- 不覆寫 project `AGENTS.md` 或既有 project memory。
- 不把 project/manuscript 延伸問題塞回 paper page；paper page 只維持該篇文章本身的資料、證據、閱讀問題與理解狀態。
- 不因 capture、query 或 agent 推理自動 promotion；receipt 必須顯示 `Promotion: none`。

## 專案範圍標記

如果要讓某專案長期記得 RKF auto-connect，可以在專案根目錄建立 `.rkf-connect.toml`：

```toml
[rkf_auto_connect]
enabled = false
mode = "active-aggressive"
config = "global"
```

這個檔案只是 discovery/routing hint，不能讓新 task 變成 ACTIVE。它不得存 private
Drive path；真正的 RKF 路徑由全域 config 與 `rkf.workspace.toml` 解析。

也可以請 Codex 建立：

```text
幫這個專案建立 RKF auto-connect marker。
```

## 專案內 RKF bridge folder

如果希望未來 agent 在該專案更快找到 RKF 相關線索，可以在專案內建立 `RKF/`
bridge folder：

```text
幫這個專案建立 RKF bridge folder，project name 用 ProjectName。
```

這會建立：

```text
RKF/
  README.md
  hot.md
  memory.md
  captures.md
```

這個資料夾是 project-local index，不是第二份 RKF database：

- `RKF/hot.md`：本專案的研究需求、search strings、候選問題；可再請 Codex app
  送進中央 RKF `hot.md`。
- `RKF/memory.md`：本專案要如何查 RKF 的 pointer、topic、paper、query hints。
- `RKF/captures.md`：記錄哪些項目已送進 RKF inbox/hot，以及哪些沒有被 promote。
- 既有檔案不會被覆寫；helper 只補缺少的 bridge 檔案。

Bridge folder 不得保存 private path、PDF、全文、secret、個資或整段私人 transcript。
其中任何內容都只是 operational index，不是 stable evidence。

## 查詢與攝入

啟動成功後：

- 查詢以 `query.search` 為唯一 retrieval-first 入口。
- 攝入以 `capture.route` 分類、去重，並先保留 immutable event。
- External GPT 內容必須保留明確 provenance；RKF 不會監看外部 GPT 對話。
- 非 designated writer 不直接改 inbox/hot/wiki，只排隊等待同步。

## 取消或暫停

在目前 session 可直接說：

```text
停用 RKF
```

Agent 會呼叫 `rkf.deactivate`；目前 task 回到 OFF。

專案層級則移除或停用 `.rkf-connect.toml`：

```toml
[rkf_auto_connect]
enabled = false
mode = "active-aggressive"
config = "global"
```

## 回報格式

Agent 記錄後應簡短回報：

```text
已記錄 RKF event；projection: queued/created；Promotion: none。
```

如果因 private path、全文過長或 project rule 被擋，agent 應改成 pending capture proposal。
