# Research Knowledge Framework（RKF）

RKF 把論文轉成能回到原文確切位置、經人工確認、並可跨論文比較的研究知識。

> Paper → source context → FindingDraft → exact-locator Evidence → human-reviewed Claim → Synthesis

RKF 適合希望在 Codex 中建立長期、source-aware 閱讀與 synthesis 流程的研究者。
它不是 PDF library、paywall bypass、自動 claim 產生器，也不能取代研究者閱讀原文。

目前最新 published release 為 `v1.1.0`；這個 branch 說明尚未 release 的 `v1.2`
target。較早的 `v1.0.0` baseline 保留在 changelog，不補造或移動不存在的歷史 tag。
Paper reading maturity 會以分開的 access state 與 review state 明確呈現；只有
metadata 不代表研究者已讀過 paper。
Ask 可以 retrieve governed wiki context，但 retrieval 本身不會把 candidate 或
model answer 提升成 Evidence。

## 選擇安裝方式

先 clone 一次 public repository：

```bash
git clone https://github.com/ChenHau-Lan/ResearchWiki.git
cd ResearchWiki
```

### A. Local core

這個 profile 用於 local framework 與隔離的 synthetic demo；不會安裝 Codex
connector 或自然語言 skill。

```bash
python3 tools/bootstrap_rkf.py
python3 tools/bootstrap_rkf.py --apply
python3 tools/check_install.py --profile core --strict --json
```

第一個 bootstrap 指令只做 read-only preview。確認內容後才執行 `--apply`。
成功的 diagnostic 會回傳 `"profile": "core"`、`"ready": true` 與
`"status": "ready"`。

### B. Codex integration

若要在 Codex 內說「啟動 RKF」或連接其他研究專案，請使用此 profile，並以
相同 connector request 先 preview、再 apply：

```bash
python3 tools/bootstrap_rkf.py --install-connector
python3 tools/bootstrap_rkf.py --apply --install-connector
python3 tools/check_install.py --profile codex --strict --json
python3 tools/rkf_auto_connect.py resolve
```

在 `codex` profile 下，缺少或過期的 connector／skill 會直接失敗，不再只是
optional warning。成功時 diagnostic 會回傳 `"profile": "codex"` 與
`"ready": true`；`resolve` 會再確認 connector 能找到此 checkout 與 workspace
configuration。

## 連接另一個研究專案

先 preview marker 與輕量 bridge，再 apply 完全相同的請求：

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

這會建立 v2 `.rkf-connect.toml` 與小型 `RKF/` bridge，不會複製中央 wiki。
每個新的 Codex task 仍從 RKF OFF 開始；task 開始時說「啟動 RKF」，完成後說
「停用 RKF」。

## 用自然語言操作 RKF

連接完成後，以研究專案資料夾作為 Codex workspace。上面的 shell command 只用於
設定；日常研究工作直接用對話即可。例如：

- 「啟動 RKF 並確認這個 project 的 connection。」
- 「根據目前對話整理研究問題與搜尋詞。先 Ask RKF，必要時再搜尋公開學術來源；
  先列出 candidate papers，等我確認後，再用 Add 保存 DOI／URL 與簡短的
  source-aware note。不要保存完整對話，Promotion: none。」
- 「顯示 RKF 狀態。列出仍有 open activation record 的 project name，標示這個
  task 所屬 project，並附 `project_id`；不要顯示 absolute path。」
- 「停用 RKF。」

`rkf.status` 會把「本 task 的 mode」與「仍有 open activation record 的 project」
分開呈現，顯示 `active_project_count`、`open_activation_count`、project name、穩定
`project_id`、mode 與 open task 數量，但遮蔽絕對路徑。若 task 中斷而沒有停用，
紀錄可能仍保持 open，直到後續寫入 closure 或 expiry event；因此這是 lineage 狀態，
不是作業系統 process monitor。

對話內容只用來形成 query 與簡短 candidate note；不保存 raw transcript、PDF 或
article text。搜尋結果在用 Add 收錄前仍是 candidate，且維持 `Promotion: none`。

## 執行 zero-network quickstart

執行與 CI 相同的 deterministic smoke test：

```bash
python3 tools/demo_quickstart.py --check
```

它會在 temporary workspace 建立兩篇明確標示為 synthetic 的 paper，啟動 RKF、
跑完五條 workflow、確認 locator promotion gate、停用 RKF，最後清除 workspace。
整個流程不使用 network、global connector、PDF 或使用者研究資料。成功輸出包含：

```json
{
  "quickstart": "passed",
  "workflows_completed": 5,
  "promotion_boundary_preserved": true
}
```

## 五條 workflow

Codex integration ready 且 project 已啟動後，可將下列模板換成自己的真實 source
identifier。這些是操作模板，不代表 RKF 已閱讀尚未提供的來源。

| 工作流 | 自然語言請求 | 預期結果 |
|---|---|---|
| **Add** | 「根據目前對話，把我選定的 DOI／URL 加為 candidate，附簡短搜尋脈絡；不要保存完整對話，也不要提升成 Evidence。」 | 產生去重後的 capture receipt，包含 `Promotion: none` 與 project/activation lineage。 |
| **Ask** | 「Ask RKF 這些來源報告了什麼，並區分 source context 與 locator-backed support。」 | 沒有 locator 的 governed context 仍可顯示，但會標示為不可支援 claim；正式支持必須連結 exact Evidence。 |
| **Read** | 「先把這個觀察記為 FindingDraft，exact locator 稍後補。」 | 產生 missing／coarse／exact FindingDraft；只有 exact finding 能提升成既有 Evidence，原本的 direct exact-locator Evidence 路徑仍可用。 |
| **Compare & Synthesize** | 「比較這些 Evidence cards，列出 agreement、contradiction、gap 與 provisional conclusion。」 | 產生連結 Evidence 的 Claim 或 Synthesis，並保留尚未解決的 gap。 |
| **Review** | 「Review 這個 project：顯示缺 locator、待確認 evidence、disputed claims 與下一個閱讀行動。」 | 產生可執行 review，以及遮蔽路徑的 activation timeline。 |

這五條工作流就是完整的 v1 研究介面。Internal helper 與 compatibility code 不會形成
額外的產品模式。

## 安全邊界

- Candidate metadata 與 model output 不是 stable evidence。
- Missing／coarse FindingDraft 是研究筆記，不是 Evidence，也不能支援 claim。
- Verified claim 必須有 locator-backed、human-verified Evidence。
- PDF、article text、secret、token、absolute path、private index 與 raw prompt
  不進 public repository 或 public output。
- RKF 不繞過 paywall、CAPTCHA 或 access control。

## vNext acquisition 開發

GitHub issue #18 現在有一個 opt-in 的科學 artifact acquisition
**portable-core slice**：支援多種 identifier、有限的 OA／官方 publisher／授權
repository route、artifact/version provenance、PDF QC、private storage 與
acquisition lineage。它仍是 Add 的 internal provider，不是第六個 workflow，且在
connector 中預設關閉。Public core 現已支援 native desktop secret boundary、跨
process backoff、holdings import、獨立 related-artifact pointer，以及明確 serial
的 machine-local browser-adapter contract。Institution endpoint 與授權設定仍只留在
本機；SSO、CAPTCHA 與其他 access control 只會 detect + stop 並交給人工處理，
不會被繞過。

可重現的大氣期刊 corpus 包含 11 個 P0 與 3 個 P1 代表案例。2026-07-16 的
bounded live observation 中，14/14 artifact 均成功取得並通過 research-ready PDF
checks，使用 publisher、current NCBI PMC Cloud 與授權 repository routes。這只
支持該 14 篇在該次測試的結果，不代表這些期刊的所有文章或未來皆可下載。Smoke
helper 強制 report 與 checksum-addressed artifact 留在 repository 外，所有結果
維持 `Promotion: none`。

詳見 [vNext acquisition reference](docs/references/vnext-acquisition.md)、
[14-case journal corpus](docs/benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json)、
[14-case live result](docs/benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md)、
[期刊 route playbook](docs/operations/atmospheric-journal-acquisition-route-playbook.zh-TW.md)、
[本次 public-safe 對話與決策摘要](docs/operations/2026-07-16-issue-18-atmospheric-journal-closeout.zh-TW.md)
與歷史 [79-citation atmospheric baseline](docs/benchmarks/acquisition-issue-18-atmospheric-smoke.md)。

目前的 beginner guide 統一由 [快速開始](docs/GETTING_STARTED.zh-TW.md) 進入。
日常操作細節見[研究者手冊](docs/manuals/rkf_manual.zh-TW.md)。
Architecture、compatibility/removal 決策、release operation 與 public synthetic demo
統一由單一 [Maintainer reference](docs/MAINTAINER_REFERENCE.md) 進入。

[English](README.md) · License: MIT
