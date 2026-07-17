# RKF v1 跨專案 Connect & Activate

## 連接

1. 對外部 project 執行 `connect-project` preview。
2. 使用者確認後 apply，建立 v2 `.rkf-connect.toml` 與 non-overwriting `RKF/` bridge。
3. Marker 取得隨機、穩定且不含 absolute path 的 `project_id`。
4. Bridge 只連到中央 RKF，不複製第二份 wiki 或 index。

## 每個 Codex task

1. 新 task 預設 RKF OFF。
2. 只有使用者直接說「啟動 RKF」才構成 activation 授權；「Ask RKF」、
   「問 RKF」或其他研究 workflow 請求不等於啟動授權。
3. Agent 執行 `rkf.activate`，建立唯一 `activation_id`。
4. `connect.validate` 檢查 marker、central availability、version 與 path redaction。
5. 研究工作使用 `workflow.add`、`workflow.ask`、`workflow.read`、
   `workflow.compare-synthesize` 或 `workflow.review`。
6. 每個 action 記錄 input fingerprint、status、affected IDs 與 `Promotion: none`；
   raw prompt 預設不保存。
7. 使用者說「顯示 RKF 狀態」時執行 `rkf.status`，分開呈現本 task receipt 與
   path-redacted open-activation project 摘要。
8. 使用者說「停用 RKF」後執行 `rkf.deactivate`，寫入 `ended_at`。

Marker 只表示 availability，不代表永久 ACTIVE。舊 v2 marker 若缺 `project_id`，必須先
人工 review/upgrade；不能把 absolute path 當作 project identity。

若 task 仍為 OFF，任何 `workflow.add`、`workflow.ask`、`workflow.read`、
`workflow.compare-synthesize` 或 `workflow.review` 請求都必須直接回傳
`RKF_NOT_ACTIVE`。Agent 不得自動執行 `rkf.activate` 或 `connect-project`，也不得讀取、
掃描或寫入 RKF research data；必須等待使用者另外明確要求啟動。
其中 `Ask RKF`／`問 RKF` 被 OFF 阻擋時，Agent 必須詢問
「是否要『啟動 RKF』？」並等待回答。這個詢問、原始 Ask 或使用者未回覆都不構成
activation 授權。

## 依目前對話搜尋並保存論文

自然語言入口可使用：「根據目前對話整理研究問題與搜尋詞，先 Ask RKF；必要時搜尋
公開學術來源並列出 candidates，等我確認後再 Add DOI／URL 與短 note，不保存完整
對話，Promotion: none。」

搜尋與寫入仍是兩個邊界：Ask／外部搜尋只產生候選；使用者選定後才以
`workflow.add` 收錄。Raw transcript、raw prompt、PDF 與 article text 不進 lineage
或 public knowledge。

## 狀態清單語意

`rkf.status` 顯示 `active_project_count`、`open_activation_count` 與每個 project 的
name、`project_id`、mode、open task 數量及最近啟動時間。清單來自 append-only
lineage，若 task 中斷且未停用，可能仍顯示 open，直到後續寫入 closure／expiry
event；Review 可檢查 timeline。完整 project path 保持遮蔽。
