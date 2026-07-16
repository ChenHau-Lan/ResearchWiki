# RKF v1 研究者手冊

RKF 是以 Codex 自然語言操作的 LLM Wiki-based research knowledge framework。
核心路徑是 Paper → source context → FindingDraft → exact-locator Evidence →
human-reviewed Claim → Synthesis。日常使用者不需要直接操作 action JSON 或
legacy CLI。

## 一次性設定與每個專案的連接

中央 checkout 只需初始化一次：

```bash
python3 tools/bootstrap_rkf.py --install-connector
python3 tools/bootstrap_rkf.py --apply --install-connector
python3 tools/check_install.py --profile codex --strict --json
```

每個研究專案先 preview，再 apply：

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

這只建立 v2 `.rkf-connect.toml` 與輕量 `RKF/` bridge。Marker 的
`available = true` 代表可以使用 RKF，不代表任何 task 已永久啟動。

## 每個 task 的自然語言流程

在研究專案資料夾開啟 Codex 後，可直接貼上：

> 啟動 RKF 並確認這個 project 的 connection。根據目前對話整理研究問題與搜尋詞。
> 先 Ask RKF，必要時再搜尋公開學術來源；先列出 candidate papers，等我確認後，
> 再用 Add 保存 DOI／URL 與簡短的 source-aware note。不要保存完整對話，
> Promotion: none。

這個請求依序完成：

1. `rkf.activate` 與 `connect.validate`：只為這個 task 啟動並驗證 project。
2. `workflow.ask`：先查已有 RKF knowledge，避免重複收錄。
3. 公開學術搜尋：只有在請求需要且工具可用時才執行，結果仍是 candidate。
4. `workflow.add`：只保存你確認的 DOI／URL、metadata、搜尋詞與短 note。

完整對話、raw prompt、PDF、article text、private path 與 secret 都不會進入 lineage
或 public knowledge。模型摘要與搜尋結果本身也不會變成 Evidence。

## 查看哪些 project 仍處於啟動紀錄

直接說：

> 顯示 RKF 狀態。列出仍有 open activation record 的 project name，標示這個 task
> 所屬 project，並附 project_id；不要顯示 absolute path。

`rkf.status` 會清楚分開：

- 本 task：`mode`、`project_name`、`project_id`、`activation_id`。
- 跨 task 摘要：`active_project_count`、`open_activation_count`、每個 project 的
  mode、open task 數量與最近啟動時間。

為保護本機資訊，只顯示 marker 中的 project name 與穩定 `project_id`，不顯示完整
資料夾路徑。這份清單來自 append-only lineage；若 Codex task 意外中斷而未執行
`rkf.deactivate`，該 activation 可能仍顯示為 open，直到後續寫入 closure 或 expiry
event。Review 可以檢查這段 timeline；這份清單不是作業系統 process monitor。

完成工作後說：

> 停用 RKF。

## 五條研究工作流

以下是 Codex app 的 Common Workflows：

- Add：保存 DOI、URL、PDF pointer、note 或 selected paper；`Promotion: none`。
- Ask：先 deterministic retrieval，明確區分 context-only 與 evidence-ready
  answer；正式 claim support 需要 exact Evidence。
- Read：可記錄 missing／coarse／exact FindingDraft；只有 exact finding 能提升為
  Evidence，也保留 direct exact-Evidence 路徑。
- Compare & Synthesize：保存 Claim／Synthesis 的 agreement、opposition 與 gap。
- Review：顯示研究缺口、待確認項目、下一個閱讀行動與 project lineage。

academic-research-suite 可協助搜尋、推理、寫作或 review，但輸出仍是 proposal，直到
滿足 RKF evidence rules。

## Paper maturity 與保存邊界

`access_state`：`metadata | abstract | partial | fulltext`。
`review_state`：`unread | skimmed | read | annotated | reproduced`。
Legacy reading label 只做保守 mapping；未知值成為 data-quality finding。

Candidate、context-only result、FindingDraft 與 LLM output 都不是 Evidence。
Verified Claim 必須有 human-verified、locator-backed Evidence。Ask 可以顯示沒有
locator 的 governed context，但必須標示為不可支援 claim。

## 常見問題

- 狀態是 OFF：在目前 task 明確說「啟動 RKF」。
- Project 沒出現在清單：先確認已 connect，再在該 task 啟動。
- Project 一直顯示 open：通常是先前 task 未停用；用 Review 檢查 activation timeline，
  並把它視為保守的 stale-state warning。
- 搜尋到論文但沒有存入：candidate 必須先經使用者選定，再走 Add。
- 只有 metadata：不可描述為已讀；取得合法全文後再更新 access/review state。
