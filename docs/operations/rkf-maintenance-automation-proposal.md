# RKF 定期維護自動化（已建立、保持暫停）

狀態：`PAUSED`。Automation ID：`rkf-maintenance-preview`。已在 Codex app
建立並重新讀取實際設定確認為暫停；尚未啟用，也不取代或刪除既有暫停工作。

## 目的

建立一個單一的 RKF 維護工作，在指定的 maintenance writer 上以新 task 執行。每次都從 RKF OFF 開始，先完成正常 activation 與 `connect.doctor`，才可產生 public-safe 維護結果。

## 提議行為

- 每日：列出 `raw/incoming/` 的 checksum／來源身分審核候選、既有 capture event、paper queue 與待處理 blocker。
- 每週：增加 structure、evidence、graph、public-safety lint 與 hot/inbox review。
- 每月：增加 topic/synthesis/migration 狀態、RAW PDF checksum audit 與 cleanup manifest preview。
- 所有 cadence：`Promotion: none`；不可自動建立 stable claim、trusted synthesis、paper migration、刪除、封存或重啟舊 automation。

## 啟用前仍需你明確指定的項目

1. 目標 maintenance writer（哪一台已登記的電腦）。
2. 是否接受目前本地時間每日 06:30 的 preview-only 排程，或要調整。
3. 是否允許 writer 在通過 doctor 後投影既有 immutable capture events，以及是否允許刷新 index／Obsidian views。
4. 收件方式；目前不預設寄信、傳 Slack 或發通知。

## 建議的安全條件

- automation 已以 `PAUSED` 建立並重新讀回設定驗證；不直接啟用。
- 第一次手動 dry-run 的 doctor、maintenance preview 與 public-safety 結果必須可審核。
- 僅在你之後單獨批准啟用時才把它轉成 active。
- 現有兩個 paused RKF automation 保持不動，直到 cleanup manifest 指定其 replacement 或移除批次。

## 非目標

- 不監控剪貼簿、瀏覽器、檔案系統或外部聊天。
- 不讀取或保存全文 PDF 到 public wiki。
- 不把 Obsidian 或 project-local `RKF/` bridge 當成第二個資料庫。
