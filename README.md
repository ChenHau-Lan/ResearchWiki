# Research Wiki

這是一個本地優先的研究知識庫，用 Markdown/Obsidian + Git 作為 canonical database，Notion 作為 dashboard/mirror。

## Structure

- `raw/`: 原始資料，只讀不改。
- `inbox/`: 日常捕捉、演講照片、影片筆記、未驗證想法。
- `wiki/`: 正式知識頁與主題分類。
- `wiki/index.md`: 內容導覽。
- `wiki/log.md`: append-only 操作紀錄。
- `references.bib`: 正式文獻 citation 的唯一來源。
- `templates/`: 新增頁面的模板。
- `notion/`: Notion dashboard/mirror 規劃。

## First Workflow

1. 把 PDF、照片、影片或程式碼來源放入 `raw/`。
2. 對未整理素材先建立 `inbox/` 條目。
3. 對正式文獻使用 `templates/paper.md` 建立 wiki page，並更新 `references.bib`。
4. 對程式碼或繪圖邏輯使用 `templates/code.md` 建立 wiki page。
5. 每次整理後更新 `wiki/index.md` 和 `wiki/log.md`。

## Obsidian

可直接用 Obsidian 開啟此資料夾。建議先開：

- `wiki/home.md`
- `wiki/zotero_mind_map.canvas`
- `wiki/index.md`

