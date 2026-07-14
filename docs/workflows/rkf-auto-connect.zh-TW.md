# RKF v1 跨專案 Connect & Activate

## 連接

1. 對外部 project 執行 `connect-project` preview。
2. 使用者確認後 apply，建立 v2 `.rkf-connect.toml` 與 non-overwriting `RKF/` bridge。
3. Marker 取得隨機、穩定且不含 absolute path 的 `project_id`。
4. Bridge 只連到中央 RKF，不複製第二份 wiki 或 index。

## 每個 Codex task

1. 新 task 預設 RKF OFF。
2. 使用者說「啟動 RKF」。
3. Agent 執行 `rkf.activate`，建立唯一 `activation_id`。
4. `connect.validate` 檢查 marker、central availability、version 與 path redaction。
5. 研究工作使用 `workflow.add`、`workflow.ask`、`workflow.read`、
   `workflow.compare-synthesize` 或 `workflow.review`。
6. 每個 action 記錄 input fingerprint、status、affected IDs 與 `Promotion: none`；
   raw prompt 預設不保存。
7. 使用者說「停用 RKF」後執行 `rkf.deactivate`，寫入 `ended_at`。

Marker 只表示 availability，不代表永久 ACTIVE。舊 v2 marker 若缺 `project_id`，必須先
人工 review/upgrade；不能把 absolute path 當作 project identity。
