# RKF v1 Codex app 工作流

使用者只需要理解五條研究工作流與 Connect & Activate。完整 action/schema reference
由 `rkf.actions.available_actions()` 與 `schemas/rkf_v1.schema.json` 提供，不再人工維護多份清單。

| 需求 | Structured action | 主要結果 |
|---|---|---|
| 啟動／檢查／停用 | `rkf.activate`、`connect.validate`、`rkf.status`、`rkf.deactivate` | project/activation receipt 與 lineage |
| 加入資料 | `workflow.add` | event-first capture；Promotion: none |
| 查詢 | `workflow.ask` | deterministic results；有 claim 時需 locator |
| 閱讀與確認 | `workflow.read` | canonical Evidence card |
| 比較與整合 | `workflow.compare-synthesize` | Claim 或 Synthesis |
| 今天要做什麼 | `workflow.review` | gaps、pending verification、disputed claims、project activity |

自然語言例子：

- 「啟動 RKF，確認這個 project 的 connection。」
- 「Add 這個 DOI，但 candidate 不要升級成 evidence。」
- 「Ask RKF 這個 finding；沒有 locator 就說證據不足。」
- 「Read 這篇，記錄 p. 8 Fig. 3 的 opposing evidence，先標 unreviewed。」
- 「Compare & Synthesize 這些 claims，列出 contradiction 與 gap。」
- 「Review 這個 project 最近做過哪些 RKF actions。」

舊的 world/stats/queue/graph、discovery lifecycle、dashboard、Obsidian、maintenance、
cleanup 與 migration 名稱不是 v1 使用者入口。相容與移除版本見 `docs/V1_SCOPE_INVENTORY.md`。
