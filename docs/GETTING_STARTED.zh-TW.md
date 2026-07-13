# RKF 新手安裝與第一個研究專案

這份教學適用於第一次從 GitHub 安裝 RKF 的使用者。建議先使用本機單機模式；
Google Drive／多電腦共享是進階實驗功能，不是初次安裝的必要條件。

## 1. 需要準備什麼

- Git
- Python 3.9 或更新版本
- Codex app
- 一個可寫入的本機資料夾

RKF 核心不需要 `pip install`。網站也是原生 HTML、CSS、JavaScript，不需要 Node.js。

先檢查：

```bash
git --version
python3 --version
```

Windows 可把下列 `python3` 改成 `py -3`。

## 2. 從 GitHub 取得 RKF

```bash
git clone https://github.com/ChenHau-Lan/ResearchWiki.git
cd ResearchWiki
```

先不要手動建立 `knowledge/` 或把 PDF 放進 repo。RKF 會依
`rkf.workspace.toml` 決定 live wiki、raw 與 private evidence 的位置。

## 3. Preview 本機設定

```bash
python3 tools/bootstrap_rkf.py
```

這一步不寫入任何檔案。正常的新 clone 會回報：

- `status: ready`
- `workspace_config: would-create`
- `storage: would-initialize`
- `paths_redacted: true`（由 `private_paths_reported: false` 表示）

若看到 `blocked`，先處理 `blocker_codes`。Bootstrap 會拒絕：

- wiki、raw、private evidence 彼此重疊；
- 指向已有資料的 storage；
- config、connector、storage 或 skill bundle symlink；
- 相對 storage path 使用 `..` 離開 checkout（若確實需要外部 storage，請提供明確
  absolute path）；
- 目標 parent 沒有寫入權限；
- 不存在的 repo root。

它不會猜測既有資料應由哪個 checkout 接管。Apply 使用 staged skill、connector-last
與 transaction rollback；若中途失敗，只移除本次能以 exact bytes／manifest 證明
新建的檔案與空目錄，不碰既有內容。

## 4. 建立本機 workspace

只使用目前 repo：

```bash
python3 tools/bootstrap_rkf.py --apply
```

若也要讓其他研究專案找到這個 checkout：

```bash
python3 tools/bootstrap_rkf.py --apply --install-connector
```

後者會建立 machine-local `~/.codex/rkf_connector.toml`，並從 repo 安裝完全相符的
`skills/rkf-auto-connect` 到 Codex skill 目錄。兩者都不應 commit；命令回傳不會
顯示本機路徑。若目標 skill 已存在但內容不同，bootstrap 會保留它並回報
`existing-unverified`；下一步診斷會 fail，避免假裝跨專案整合已可用。Bootstrap
也要求 skill tree 只有 `SKILL.md` 與 `agents/openai.yaml`；額外或 stale 檔案會被視為
unverified，必須人工 review，未來新增合法 skill metadata 時也要同步更新 manifest。
成功時會建立：

- ignored `rkf.workspace.toml`；
- ignored `.rkf_data/wiki/` 與 `.rkf_data/raw/`；
- ignored `.rkf_private/evidence/`；
- 隨機、非個人的 machine ID；
- 相符的 single-writer registry。

如果 config 已存在，bootstrap 只會回報 `existing-unverified` 並保留原檔。
它不會偷偷修復或註冊既有 storage；請執行下一步診斷。

## 5. 驗證安裝

```bash
python3 tools/check_install.py --strict
```

`ready` 代表必要檔案、storage handle 與 connection doctor 可用；如果這台機器
被設定為 designated writer，也代表 writer registry 可用。`warn` 通常代表
optional connector 或網站尚未設定；`fail` 才會讓
`--strict` 回傳非零狀態。診斷不會列出 storage path、machine ID 或 token。
若剛使用 `--install-connector` 安裝 global skill，請重新開啟專案或開始新的
Codex task，讓新 task 載入最新 skill catalog，再說「啟動 RKF」。

若要給自動化或測試讀取：

```bash
python3 tools/check_install.py --json
```

## 6. 在 Codex 開始第一個 task

在 Codex app 打開這個資料夾，然後說：

```text
啟動 RKF
顯示目前的 world context、paper queue 與 lint 狀態。
```

每個新 task 都從 RKF OFF 開始。`.rkf-connect.toml` 只表示專案可使用 RKF，
不會讓 session 永久 ACTIVE。

第一個安全練習：

```text
把一個有效 DOI（以 `DOI_PLACEHOLDER` 代入）當作 metadata-only paper lead 加入 RKF；
保留 candidate/evidence boundary，不要產生 stable claim。
```

## 7. 連結另一個研究專案

先 preview，不修改目標專案：

```bash
python3 tools/rkf_auto_connect.py connect-project "/path/to/MyResearchProject" --project-name "MyResearchProject"
```

確認 receipt 後再套用：

```bash
python3 tools/rkf_auto_connect.py connect-project "/path/to/MyResearchProject" --project-name "MyResearchProject" --apply
```

這會建立 v2 `.rkf-connect.toml` 與缺少的 `RKF/` bridge files，但不會覆寫既有
bridge note，也不會在目標專案複製一份 wiki。若偵測到 legacy v1 marker，升級需要
再次明確加上 `--apply-upgrade`；未知未來版本或不同的 v2 policy 必須人工處理。
Bridge 會先完整建立，marker 最後才更新；任何中途失敗都只回滾本次新建內容。

完整說明見 [RKF Auto-Connect Workflow](workflows/rkf-auto-connect.zh-TW.md)。

## 8. 看研究熱點 Dashboard

直接用 Codex：

```text
啟動 RKF
建立 aggregate-only 的 dashboard preview，不要發布。
```

維護者也可使用：

```bash
python3 tools/build_public_dashboard.py preview
```

Preview 只寫入 ignored `.rkf_private/dashboard_previews/`，receipt 會提供
`preview_id` 與 `snapshot_hash`。先把 exact preview render 成不發布的本機頁面：

```bash
python3 tools/build_public_dashboard.py review --preview-id PREVIEW_ID
```

直接打開該 preview 內的 `review/index.html`；頁首必須顯示
`PRIVATE REVIEW · NOT PUBLISHED`。這個步驟不會更新 `site/`。只有人工檢查後，
才能用完全相同的 hash 更新
本機 `site/data/rkf-public-snapshot.json`：

```bash
python3 tools/build_public_dashboard.py publish --preview-id PREVIEW_ID --snapshot-hash SNAPSHOT_HASH
python3 -m http.server 8000 --directory site
```

瀏覽 `http://localhost:8000/`。GitHub Pages 的遠端啟用是另一個部署步驟；見
[Public Dashboard 與 GitHub Pages](workflows/public-dashboard.zh-TW.md)。

## 9. 自動找 paper，但保留研究關卡

乾淨安裝一開始還沒有 topic registry。第一次請先用明確、public-safe 的 query 做
candidate preview，不要假設範例 topic 已存在：

```text
啟動 RKF
搜尋「aerosol ice-phase cloud observations」的 candidate papers；
使用 Crossref 與 arXiv，先不要記錄或建立 paper draft。
```

等你已建立並審核自己的 topic registry 後，再要求 Codex 以該 topic ID 的
`default_search_strings` 查詢。不存在或已退役的 topic ID 會被拒絕，不會靜默改用
其他研究題目。

你確認候選後，可要求記錄 exact preview，再只接受選定的 candidate IDs。
接受後預設建立 inbox／SourceRecord，不建立 paper draft；只有明確要求才建立 early
paper draft。Candidate、摘要、provider ranking 都不是 stable claim evidence。

完整 provider、paper-radar adapter 與排程邊界見
[Paper Discovery 與安全攝取](workflows/paper-discovery.zh-TW.md)。

## 10. 常見問題

| 情況 | 安全處理 |
|---|---|
| workspace `existing-unverified` | 執行 `tools/check_install.py --strict`；不要重跑 bootstrap 來覆寫既有設定 |
| connector 指向另一個 checkout | 保留原檔；人工決定哪個 checkout 是 authority，再更新 connector，不要讓 bootstrap 猜測 |
| installed skill 與 repo 不同 | 先 review 兩個 `SKILL.md`；bootstrap 不會覆寫使用者既有 global skill |
| `RKF_NOT_ACTIVE` | 在目前 task 說「啟動 RKF」 |
| `ACTIVE_READ_ONLY` | 先查看 connection doctor blocker；不要繞過 writer gate |
| `RKF_WRITER_REQUIRED` | 由已登記的 maintenance writer 執行 projection |
| Discovery 只能 preview | `discover.record`／`discover.accept` 另需 ACTIVE、passing doctor 與 designated writer |
| 找不到全文 | 提供授權 PDF 或可讀文字；不要繞過 paywall、CAPTCHA 或 robots |
| Dashboard 顯示 synthetic | 尚未批准 live aggregate snapshot；這是安全的預設狀態 |
| 想先看真實 dashboard | 對 `preview_id` 執行 private `review`；不要為了預覽先 publish |
| OpenAlex 未啟用 | 設定 machine-local `OPENALEX_API_KEY`，或只用 Crossref/arXiv |

## 11. 不應 commit 的內容

- `rkf.workspace.toml`
- `.rkf_data/`
- `.rkf_private/`
- PDFs、OCR/article text、private Drive paths
- API key、token、machine-local connector

提交前可執行：

```bash
python3 -m unittest discover -s tests
python3 tools/public_safety_scan.py
```
