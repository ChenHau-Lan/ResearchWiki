# RKF v1 Codex app 工作流

使用者只需要理解五條研究工作流與 Connect & Activate。完整 action/schema reference
由 `rkf.actions.available_actions()` 與 `schemas/rkf_v1.schema.json` 提供，不再人工維護多份清單。

| 需求 | Structured action | 主要結果 |
|---|---|---|
| 啟動／檢查／停用 | `rkf.activate`、`connect.validate`、`rkf.status`、`rkf.deactivate` | 本 task receipt；path-redacted open-activation project 摘要；lineage |
| 加入資料 | `workflow.add` | event-first capture；可選 `FullTextProvider` acquisition；Promotion: none |
| 查詢 | `workflow.ask` | 預設 context-first；以 `context-only \| mixed \| evidence` 分開來源脈絡與正式支持，`evidence-only` 保留 strict gate |
| 閱讀與確認 | `workflow.read` | missing／coarse／exact FindingDraft、exact-locator Evidence，或 `digest \| appraise \| both` scope-gated Read run |
| 比較與整合 | `workflow.compare-synthesize` | Claim、Synthesis 與 evidence matrix |
| 今天要做什麼 | `workflow.review` | next paper、gaps、pending verification、failed checks、project/activation/object timeline |

自然語言例子：

- 「啟動 RKF，確認這個 project 的 connection。」
- 「根據目前對話整理搜尋詞，先 Ask RKF；列出候選論文，等我確認後再 Add DOI／URL 與短 note，不保存完整對話。」
- 「顯示 RKF 狀態，列出仍有 open activation record 的 project name 與 project_id，並標示這個 task。」
- 「Add 這個 DOI，但 candidate 不要升級成 evidence。」
- 「Ask RKF 這個 finding；可顯示 source context，但不要把缺 locator 的內容當成 claim support。」
- 「Read 這篇，先記錄 FindingDraft；locator 稍後補成 exact 再提升 Evidence。」
- 「Compare & Synthesize 這些 claims，列出 contradiction 與 gap。」
- 「Review 這個 project 最近做過哪些 RKF actions。」

`workflow.review` 可依 `project_id`、`activation_id`、action、status 或
`target_object_id` 篩選。Optional provider 的完整 v1 邊界見
[`docs/references/v1-provider-contracts.md`](references/v1-provider-contracts.md)。

`rkf.status` 的 `active_project_count` 與 `open_activation_count` 來自 append-only
activation lineage，不是 process monitor。未正常停用的中斷 task 可能保持 open；
absolute path 一律遮蔽。

Issue #18 目前完成的是 opt-in **portable-core slice**：支援 URL／DOI／
preprint／report identifier、有限的 OA／官方 publisher／授權 repository route、
artifact version／PDF QC 與 private acquisition lineage。Identifier-only
adapter 支援 ADS、OSF／EarthArXiv、ESSOAr DOI、NOAA IR PID、WMO
record／publication slug 與已註冊 IPCC report ID。它仍由 `workflow.add` 內部
呼叫，不是第六個產品模式；browser／institutional adapter 尚未完整實作，遇到
SSO、CAPTCHA 或其他 access control 時只會 detect + stop，回傳 typed manual
handoff，不會繞過。

公開測試 corpus 包含 11 個 P0 與 3 個 P1 大氣期刊代表案例。2026-07-16 的
一次 bounded live observation 為 14/14 `obtained`、14/14 通過 research-ready
PDF checks，路徑包含 current NCBI PMC Cloud 與授權 repository；這只代表該次、
該 14 篇，不是所有期刊文章皆可下載的證明。Smoke helper 的 report 與
checksum-addressed artifact 必須寫在 repository 外，結果一律維持
`Promotion: none`。完整設定、corpus、結果與限制見
[`docs/references/vnext-acquisition.md`](references/vnext-acquisition.md) 與
[`docs/benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md`](benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md)；
未來遇到同一期刊 DOI 時，依
[`期刊 route playbook`](operations/atmospheric-journal-acquisition-route-playbook.zh-TW.md)
重試，並保持 article-specific identifier 不可猜測的邊界。本次對話保存為
[`public-safe 決策摘要`](operations/2026-07-16-issue-18-atmospheric-journal-closeout.zh-TW.md)，
不包含逐字 transcript、PDF 或 private path。

PR #30 合併後的 completion layer 另外加入 hard wall-clock HTTP deadline、external
adapter stdout/stderr 上限、跨 process `Retry-After`、macOS Keychain／Linux Secret
Service／optional Windows Credential Manager、holdings CSV preview/apply、Review route
health，以及獨立的 related-artifact pointer records。Institutional browser 只會在明確
`institutional-external` policy 且提供 machine-local adapter 時 serial 執行；SSO、
CAPTCHA、Ovid seat 與 access control 仍回 typed handoff。Pointer、下載成功與 PDF QC
都不會自行建立 Evidence 或升格 Claim。

舊的 world/stats/queue/graph、discovery lifecycle、dashboard、Obsidian、maintenance、
cleanup 與 migration 名稱不是 v1 使用者入口。相容與移除版本見 `docs/V1_SCOPE_INVENTORY.md`。
