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
| **Add** | 「將這個 DOI 或 URL 作為 candidate 加入，不要提升成 Evidence。」 | 產生去重後的 capture receipt，包含 `Promotion: none` 與 project/activation lineage。 |
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

目前的 beginner guide 統一由 [快速開始](docs/GETTING_STARTED.zh-TW.md) 進入。
Architecture、compatibility/removal 決策、release operation 與 public synthetic demo
統一由單一 [Maintainer reference](docs/MAINTAINER_REFERENCE.md) 進入。

[English](README.md) · License: MIT
