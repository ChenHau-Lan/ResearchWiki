# RKF Paper Discovery Automation Proposal

Status: **proposal only — no recurring automation is active**

這份文件定義第一次啟用 paper discovery automation 時的保守預設。下列 topic 與
時間只是依目前 public-safe registry 產生的待核准 proposal；它不是排程設定，也不
授權 shared RKF 寫入、全文取得或 paper draft 建立。

## Recommended first automation

| Field | Proposed value |
|---|---|
| Topic scope | `aerosol-ice-phase-clouds`、`wildfire-smoke-cloud-microphysics`；啟用前仍需使用者明確核准 |
| Providers | Crossref + arXiv；OpenAlex 只有 machine-local key 已存在時才加入 |
| Cadence | 每週一 09:00，`America/Denver`；啟用前仍可調整 |
| Maximum | 每個 topic/run 最多 20 candidates；兩個 topics 各自保留 run receipt |
| Intake policy | `candidate-harvest`：preview + exact record；不 accept |
| Paper draft | `false` |
| Claim/synthesis promotion | 禁止 |
| Output | provider status、candidate/dedupe aggregate、run ID 與 blocker；不在通知中列 paper identity |

## Activation prerequisites

所有條件都必須成立：

1. `python3 tools/check_install.py --strict` 回傳 ready。
2. Installed `rkf-auto-connect` bundle 與目前 checkout 完全相同。
3. Connection doctor 通過，且執行機器是 designated writer。
4. 使用者核准 topic IDs、providers、頻率、當地執行時間與每次上限。
5. 相同 manual flow 已至少成功執行兩次，provider errors 只留下 redacted receipt。
6. Automation 使用 [`prompts/agents/paper-discovery.md`](../../prompts/agents/paper-discovery.md)，
   並由 Codex automation 管理器建立；不得以手寫 cron 或未追蹤背景程序取代。

## Optional second phase

`metadata-capture` 只能在第一階段穩定後另行核准。它仍只能接受
`dedupe_status: new` 且有 DOI 或經驗證 public landing URL 的 candidates，actor 必須
記為 `automation`，每次最多 20 筆，且 `create_paper_drafts: false`。

全文、PDF/OCR、stable claim、trusted synthesis 與 publication 永遠不屬於自動
攝取範圍。

## Approval sentence template

使用者可用自然語言核准，例如：

> 同意以 topic IDs `aerosol-ice-phase-clouds`、
> `wildfire-smoke-cloud-microphysics`，每週一 09:00 `America/Denver` 執行
> Crossref + arXiv；每個 topic/run 最多 20 篇，只做 candidate-harvest，
> 不自動接受或建立 paper draft。
