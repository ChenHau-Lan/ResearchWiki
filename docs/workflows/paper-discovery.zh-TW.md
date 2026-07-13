# RKF Paper Discovery 與安全攝取

Paper discovery 的目標是根據 RKF topic、`hot.md` demand 或明確 query 自動找候選
paper，同時維持 `candidate != evidence`。Discovery 不抓取或保存 article text，
也不繞過 paywall、CAPTCHA、robots 或機構存取限制。

## 支援來源

- Crossref REST：bibliographic metadata；不需要 API key。
- arXiv Atom API：preprint metadata；批次多次查詢時需遵守 arXiv 的節流建議。
- OpenAlex：optional；目前需要 machine-local `OPENALEX_API_KEY`。
- [`drpwchen/paper-radar`](https://github.com/drpwchen/paper-radar)：目前是
  **adapter-only**。呼叫端可把已取得的 metadata records 傳給
  `discover.preview` 的 `paper_radar_records`；RKF 不會 clone 該 repo、啟動其服務、
  讀取其資料庫或自行抓 export。

Paper-radar 的 abstract、PDF route、deep-read content、vote/personal state、private key
與任意 upstream 欄位都會在 RKF persistence 前移除。

## Canonical flow

```text
topic/default search | hot demand | explicit query | paper-radar metadata
  -> discover.preview       # network read, no RKF state write
  -> normalized candidates # DOI/title-year-author dedupe
  -> exact preview_hash
  -> discover.record        # designated writer; immutable candidates.json
  -> discover.accept        # ACTIVE + doctor + designated writer; selected IDs only
  -> immutable capture event
  -> inbox + optional SourceRecord
  -> optional early paper draft
  -> reading/fulltext/locator/human-review gates
```

Acceptance state 與 immutable run 分開存放，重跑不會改寫已記錄的 candidate payload。
`discover.record` 和 `discover.accept` 都需要 ACTIVE、passing connection doctor 與
designated writer；只有 preview/status 是不改 canonical discovery state 的讀取面。

Public landing URL 會移除全部 query parameters，並拒絕 user-info、localhost、
reserved/internal hostname、private/non-global IP 與 `127.1` 等 obscured-IP 表示法。
Run 與 `acceptance.json` 讀回時都會重新驗證 schema 與欄位語意；acceptance actor
也會保留到 capture event。已成功完成的同一 candidate 再次接受時不會新增 event。

每個 `(run_id, candidate_id)` acceptance 都有 deterministic transaction key。
如果程序在 capture event 寫入後、`acceptance.json` 更新前終止，重試會嚴格核對
actor、writer、origin、source identity、payload 與 dedupe 狀態，沿用同一 event，再完成
尚未完成的 projection 與 acceptance sidecar；不會把相同 retry 當成新 capture。
若找到重複 transaction event，或任何欄位與 retry 不一致，action 會 fail closed，
不會猜測哪一份正確。Designated writer 仍應序列化同一 run 的 acceptance 操作。

Paper-radar adapter 只讀取下列 allowlisted 書目欄位的交集：title、authors、year／
published、journal／venue、DOI、public landing URL、provider ID 與 ranking score。
abstract、PDF/deep-read route、vote、personal state、key 與其他任意欄位一律丟棄。

## 日常使用

使用 topic 的 `default_search_strings`：

```text
啟動 RKF
針對 topic cloud-microphysics，使用 Crossref 與 arXiv 建立 discovery preview；
最多 20 筆，先不要記錄。
```

使用明確 query：

```text
搜尋「aerosol cloud interaction observation parameterization」的 candidate papers；
只顯示 bibliographic metadata 與 dedupe 狀態。
```

同意記錄後：

```text
記錄這個 exact discovery preview 與 hash，但不要接受任何 candidate。
```

選定攝取：

```text
接受 run RUN_ID 中的 candidate IDs CAND_1、CAND_2；
只建立 inbox／SourceRecord，不建立 paper draft，不升級 claim。
```

若確實要 early paper draft，必須明確說明 `create_paper_drafts: true`。Draft 仍是
metadata-only active reading object，不代表已讀全文。

## 自動化層級

建議先選第一級：

1. **Candidate harvest（建議）**：排程自動 preview + exact record；不 accept。
2. **Metadata capture（需另行批准）**：只對明確 topic、`dedupe_status: new` 且有
   DOI/公開 URL 的候選執行 `discover.accept`；每次限制筆數、actor 記為
   `automation`、`create_paper_drafts: false`。Action 會 fail closed：automation
   只接受 `dedupe_status: new` 且有 DOI／public landing URL 的候選，並有每 run
   最多 20 筆的內建上限。
3. **不可自動化**：全文取得、stable claim promotion、trusted synthesis、publication。

Repo 的 schedule-ready prompt 位於
[`prompts/agents/paper-discovery.md`](../../prompts/agents/paper-discovery.md)。目前沒有
啟用 recurring automation；建立排程前必須批准 topics、providers、頻率、每次上限、
是否 metadata-capture，以及輸出位置。
第一次啟用可直接審核
[`RKF Paper Discovery Automation Proposal`](../operations/rkf-paper-discovery-automation-proposal.md)，
其中的預設是每週 candidate-harvest，不自動接受或建立 paper draft。

若一個 automation 連續查詢多個 arXiv topic，查詢間至少保留 3 秒，並遵守
[arXiv API User's Manual](https://info.arxiv.org/help/api/user-manual.html)。

## Provider 邊界

- Crossref 官方文件：<https://www.crossref.org/documentation/retrieve-metadata/rest-api/>
- OpenAlex Works API：<https://developers.openalex.org/api-reference/works/list-works>
- Provider failure 只回傳 redacted error code；不把 exception、path 或 key 寫入 run。
- 一個 provider 失敗時可回傳 `partial`，但不會刪除舊 run 或提高其他 candidate 信任。
