# RKF 的本機 Obsidian View 工作流

## 目的

Obsidian 是 RKF canonical wiki 的本機閱讀與連結視圖，不是第二個資料庫。真實資料仍只在
Google Drive 的 `wiki/` root；每台電腦自己的 vault link、`.obsidian/` 設定與 local cache
都不應寫回或同步到 canonical wiki。

## 先決條件

1. 在 Codex 說「啟動 RKF」。
2. 執行「檢查 RKF 多電腦狀態」；`connect.doctor` 必須沒有 blocker。
3. 確認本機不是第二個 maintenance writer。只有 designated writer 可產生 canonical Base 檔。

## 本機 vault 設定

在每台電腦任意本機位置建立一個空 vault，並只在 vault 內建立 `wiki/` 指向已設定的
canonical wiki root 的本機 link。macOS 可使用 symlink，Windows 可使用 junction；link
與 `.obsidian/` 皆是該電腦的私有設定。

不要把 `.obsidian/` 建在 Google Drive wiki root，也不要同時對同一批 wiki 檔案啟用
Google Drive 與 Obsidian Sync。這樣可避免兩個同步系統同時改動相同 metadata。

## Canonical Bases

請 designated writer 在 Codex 說「產生 RKF Obsidian views」。這會以 atomic checksum write
產生下列 public-safe artifacts：

- `views/papers.base`
- `views/reading-queue.base`
- `views/inbox.base`
- `views/questions.base`
- `views/synthesis.base`

它們使用 Obsidian core Bases 的 YAML syntax，並只依 Markdown frontmatter 的 `type`、
`reading_state`、`fulltext_status`、`claim_readiness`、`updated` 等 properties 篩選與顯示。
可先使用「預覽 RKF Obsidian views」取得 deterministic checksum，而不寫任何檔案。

Bases 的語法與 `file.inFolder()` filters 依循 [Obsidian 官方 Bases syntax](https://obsidian.md/help/bases/syntax)。

## 使用方式

- 用 Backlinks 看 incoming `paper_relations`；project/synthesis/question page 指向 paper，
  paper page 本身不需要加入 project-specific 段落。
- 用 Local Graph 觀察 paper、concept、topic、source 的 intrinsic links。
- 用 Reading Queue Base 看缺 PDF、locator 或 human feedback 的 papers。
- 用 Search／Outline 檢視單一 paper 的 paper-centred sections。

## 禁止事項

- 不在 Obsidian 直接把 private PDF、全文、browser capture 或私有路徑寫入 canonical Markdown。
- 不把 Smart Connections 或任何 local semantic index 當作 evidence；若未來試用，它只能是可重建的本機建議層。
- 不手動解決 Drive conflict copy；停止寫入、用 `connect.doctor` 回報，並由人決定後續處理。
