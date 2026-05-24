# Research Wiki 文件規則

這份規則用來讓 Research Wiki 的文件在持續改版時仍然一致。目標讀者是會修改 README、USER_GUIDE、core contract、manual、support guide 或 PR 說明的維護者與 Codex agent。

## 文件分層

Research Wiki 的文件各自有不同任務。資訊應放在最不容易混淆的位置：

| 層級 | 用途 | 代表檔案 |
|---|---|---|
| 第一眼入口 | 說明這是什麼、如何開始 | `README.md`, `README.zh-TW.md` |
| 使用操作 | 說明 pipeline skills、可選 command router、資料夾、mode 權限與 workflow 怎麼用 | `USER_GUIDE.md`, `USER_GUIDE.zh-TW.md` |
| 安裝與支援 | 協助安裝、檢查、回報問題 | `INSTALL*`, `SUPPORT*` |
| 持久規則 | 定義工具與 agent 必須遵守的契約 | `core/*`, `AGENTS.md` |
| 教學手冊 | 用截圖與範例解釋完整流程 | `docs/manuals/*`, `output/pdf/*` |
| 參考指南 | 說明概念、結構、檔案用途、版本政策 | `docs/guides/*`, `VERSION_LOG*` |
| 執行歷史 | 紀錄操作與維護結果 | `maintenance/log.md`, PR bodies |

不要把 README 寫成完整手冊。README 只需要讓新使用者知道 Research Wiki 是什麼、skill-first pipeline 心智模型、怎麼開始、可選 command router 在哪裡，以及下一步要讀哪份文件。

## 產品教學語氣

README、Quickstart 與 beginner manual 必須像產品教學，而不是 PR 記錄或遷移說明。它們只描述使用者現在要做什麼、會看到什麼、下一步去哪裡。

不要在這些文件中放：

- 內部版本遷移敘事，例如「舊版」、「v1/v2 改版」、「這份手冊取代...」。
- 舊 command、舊 option number、舊 menu 對照。
- 截圖 redaction 或「本截圖沒有包含 private data」這類安全聲明。
- PR、release、測試觀察或 cleanup history。
- 維護者給 agent 的修正理由或使用者回饋原句。

這些內容應放到 `VERSION_LOG*`、`SUPPORT*`、`docs/guides/*`、`maintenance/*` 或 legacy pointer。產品教學可以保留必要安全邊界，但要寫成操作規則，例如「只使用你有權使用的來源」，不要寫成上傳或截圖聲明。

## 雙語與 PDF 政策

面向使用者的長篇教學或參考文件，預設要有英文與繁體中文版本。每一份這類文件應包含：

- 英文 Markdown；
- 繁中 Markdown；
- `output/pdf/` 下的 PDF 成品；
- 開 PR 前至少一次 Poppler render check；
- 用 `pdftotext` 確認重要章節標題可搜尋。

短期 maintenance note、repair plan、PR-specific record 可以只用單一語言，除非它會成為使用者指南。

## 安全更新文件的順序

如果 workflow 改變，請依照這個順序更新：

1. 如果行為或規則改變，先改 durable contract。
2. 規則存在後，再改 command prompt 或工具。
3. 使用者需要操作新行為時，更新 USER_GUIDE。
4. 第一眼使用者需要知道時，README 只加短入口。
5. 需要教完整流程時，更新 manual 或 guide。
6. 改變 release-visible workflow、contract 或使用者心智模型時，更新 `VERSION_LOG.md` 與 `VERSION_LOG.zh-TW.md`。

不要把 PR 討論或使用者抱怨原句直接貼進文件。應先轉成持久規則、workflow 邊界或使用者看得懂的解釋。

## PR 文件檢查

每個 PR 都應說明：

- 有意上傳了什麼；
- 有意不上傳什麼；
- README/USER_GUIDE 連結是否改變；
- PDF 是否重新生成；
- private raw PDF、raw full text、本機路徑、Codex logs 是否排除；
- 跑了哪些測試與 render check。

如果 PR 改 workflow 行為，請寫明受影響的 skill/mode mapping，以及每個 mode 是否寫檔。如果 PR 改 evidence 或 wiki 規則，請寫明影響哪個 `core/*` contract。

## 版本政策

Research Wiki 在 vNext compiler/manual baseline 合併後定為 `v1.0.0`。`v2.0.0` 是 skill-first pipeline baseline，因為 command semantics 改變。版本號規則：

- `v1.x.y`：相容的文件改善、新 guide、advisory tool、或不破壞既有契約的 skill/mode router 變更；
- `v1.(x+1).0`：使用者看得到的相容功能新增；
- `v2.0.0`：data contract、command semantics、必要 frontmatter、資料夾角色或 migration expectation 發生破壞性變更。

使用者應能透過 version log 與其中列出的 PR，回到自己偏好的版本。
