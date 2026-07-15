# RKF v1 Codex app 工作流

使用者只需要理解五條研究工作流與 Connect & Activate。完整 action/schema reference
由 `rkf.actions.available_actions()` 與 `schemas/rkf_v1.schema.json` 提供，不再人工維護多份清單。

| 需求 | Structured action | 主要結果 |
|---|---|---|
| 啟動／檢查／停用 | `rkf.activate`、`connect.validate`、`rkf.status`、`rkf.deactivate` | project/activation receipt 與 lineage |
| 加入資料 | `workflow.add` | event-first capture；可選 `FullTextProvider` acquisition；Promotion: none |
| 查詢 | `workflow.ask` | 預設 context-first；以 `context-only \| mixed \| evidence` 分開來源脈絡與正式支持，`evidence-only` 保留 strict gate |
| 閱讀與確認 | `workflow.read` | missing／coarse／exact FindingDraft、exact-locator Evidence，或 `digest \| appraise \| both` scope-gated Read run |
| 比較與整合 | `workflow.compare-synthesize` | Claim、Synthesis 與 evidence matrix |
| 今天要做什麼 | `workflow.review` | next paper、gaps、pending verification、failed checks、project/activation/object timeline |

自然語言例子：

- 「啟動 RKF，確認這個 project 的 connection。」
- 「Add 這個 DOI，但 candidate 不要升級成 evidence。」
- 「Ask RKF 這個 finding；可顯示 source context，但不要把缺 locator 的內容當成 claim support。」
- 「Read 這篇，先記錄 FindingDraft；locator 稍後補成 exact 再提升 Evidence。」
- 「Compare & Synthesize 這些 claims，列出 contradiction 與 gap。」
- 「Review 這個 project 最近做過哪些 RKF actions。」

`workflow.review` 可依 `project_id`、`activation_id`、action、status 或
`target_object_id` 篩選。Optional provider 的完整 v1 邊界見
[`docs/references/v1-provider-contracts.md`](references/v1-provider-contracts.md)。

舊的 world/stats/queue/graph、discovery lifecycle、dashboard、Obsidian、maintenance、
cleanup 與 migration 名稱不是 v1 使用者入口。相容與移除版本見 `docs/V1_SCOPE_INVENTORY.md`。
