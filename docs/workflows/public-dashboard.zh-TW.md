# RKF Public Dashboard 與 GitHub Pages

RKF dashboard 是 public-safe aggregate snapshot，不是 live wiki viewer。它可以顯示
研究熱點、candidate pipeline、reading maturity、claim readiness、graph/health count
與 machine-neutral settings，但不會發布問題原文、paper title、DOI、路徑、machine
ID、reading ledger、abstract、PDF 或 article text。

目前已核准的 reference instance：
[RKF Observatory](https://chenhau-lan.github.io/ResearchWiki/)。本 repository 的
`.github/workflows/pages.yml` 已啟用；fork 或新部署仍須自行設定 GitHub Pages source、
environment protection 與新的 exact-hash review。

當最近視窗沒有 public-safe hot demand 時，網站會把最多 12 個 topic 顯示為
「已登錄研究領域」，不會誤標成 recent hotspot。Settings 只顯示 storage handles
是否已設定、doctor blocker/warning 數量與 gate 開關，不顯示實際路徑或 finding
內容；舊版或無法分類的 capture decision 會獨立列為 `Legacy / unclassified`。
網站內附相對連結的 beginner getting-started 頁面，因此 project Pages base path 下
不需要依賴外部 README URL。

## 安全流程

```text
live RKF
  -> dashboard.preview
  -> .rkf_private/dashboard_previews/<preview_id>/
  -> dashboard.review
  -> ignored self-contained review/index.html
  -> 人工檢查 exact snapshot_hash
  -> dashboard.publish
  -> site/data/rkf-public-snapshot.json
  -> commit / push / GitHub Pages（另外批准）
```

`public_safe` 不等於已同意公開上網；publish 必須命名同一個 preview hash。

## Codex 操作

```text
啟動 RKF
建立最近 30 天、aggregate-only 的 dashboard preview，不要發布。
```

取得 `preview_id` 後，先建立可直接打開的 private review page：

```text
把 dashboard preview PREVIEW_ID render 成 private review page；不要更新 site、
不要 commit、push 或啟用 Pages。
```

Review bundle 只存在 ignored `.rkf_private`，固定顯示
`PRIVATE REVIEW · NOT PUBLISHED`，同時含 `noindex` 與 embedded exact snapshot；
直接打開 `review/index.html` 即可，不需要先發布或啟動 server。

檢查 receipt 後：

```text
我批准 dashboard preview PREVIEW_ID，hash 是 SNAPSHOT_HASH；
只更新本機 static site snapshot，不要 commit、push 或啟用 Pages。
```

## 維護者 fallback

```bash
python3 tools/build_public_dashboard.py preview --window-days 30
python3 tools/build_public_dashboard.py review --preview-id PREVIEW_ID
python3 tools/build_public_dashboard.py publish --preview-id PREVIEW_ID --snapshot-hash SNAPSHOT_HASH
python3 -m http.server 8000 --directory site
```

`review` 不修改 `site/`、preview snapshot 或 manifest；它只建立權限受限、固定檔案樹的
private visual bundle。網站使用相對 URL，可在 repository project site base path 下工作。Committed snapshot
預設標示 `synthetic-preview`，避免尚未審查的 live state 被誤認為已發布。

## GitHub Pages 啟用前要決定

1. 使用哪個 remote／branch。Public dashboard 建議使用只含 public-safe code/site 的
   public repository；不要因 private repo 名稱就假設 Pages 網站是私有的。
2. GitHub Settings → Pages 的 source 要設為 **GitHub Actions**。
3. 是否允許 `site/**` push 後自動部署，或只允許 manual dispatch。
4. 每次部署前，site snapshot 是否來自 exact-hash approval。

建議的首次發布路徑是：先把目前 RKF 變更放到公開 repository 的 integration
branch，與遠端 default branch 對齊後開 PR；不要從一個 behind／diverged 的本機
branch 直接 push 到 `main`。發布前先確認：

```bash
git fetch origin main
git rev-list --left-right --count origin/main...HEAD
```

如果左側數字不是 `0`，先透過 integration branch／PR reconcile；不要 force push。
若要改用其他 remote 或非 `main` branch，啟用 workflow 前必須同步修改 trigger，並
確認該 repository 的公開性與 Pages plan。建議在 `github-pages` environment 設定
required reviewer，讓通過 exact-hash 的 snapshot 仍需一次遠端部署核准。

Repo 提供不會自動執行的範本：
[`github-pages-rkf-dashboard.example.yml`](github-pages-rkf-dashboard.example.yml)。
只有使用者批准 remote、branch 與部署策略後，才應複製到
`.github/workflows/pages.yml`。範本在 upload 前執行
`tools/build_public_dashboard.py validate-publication`；synthetic、pending、hash
不符、schema 不符或缺少 exact approval metadata 都會 fail closed。

GitHub 官方參考：

- [Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## Dashboard 不代表什麼

- 熱點 demand count 不是證據強度。
- Candidate count 不是已讀 paper 數。
- `public_safe` lint 通過不等於 publication approval。
- Dashboard 不提供全文、私人筆記或 source identity drill-down。
