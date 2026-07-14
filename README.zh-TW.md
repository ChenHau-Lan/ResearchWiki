# Research Knowledge Framework（RKF）

RKF 把論文轉成能回到原文確切位置、經人工確認、並可跨論文比較的研究知識。

> Paper → locator-backed Evidence → human-reviewed Claim → Synthesis

RKF 適合希望在 Codex 中建立長期、source-aware 閱讀與 synthesis 流程的研究者。
它不是 PDF library、paywall bypass、自動 claim 產生器，也不能取代研究者閱讀原文。

相容更新目標為 `v1.1.0`；已發布的 `v1.0.0` tag 保持不變。
Paper reading maturity 會以分開的 access state 與 review state 明確呈現；只有
metadata 不代表研究者已讀過 paper。
Ask 可以 retrieve governed wiki context，但 retrieval 本身不會把 candidate 或
model answer 提升成 Evidence。

## 安裝中央 RKF checkout

```bash
git clone git@github.com:ChenHau-Lan/ResearchWiki.git
cd ResearchWiki
python3 tools/bootstrap_rkf.py
python3 tools/bootstrap_rkf.py --apply
python3 tools/check_install.py --strict
```

第一個 bootstrap 指令只做 read-only preview。確認內容後才執行 `--apply`。
連接研究專案前，strict check 必須以 `ready: true` 結束。

## 連接另一個研究專案

先 preview marker 與輕量 bridge，再 apply 完全相同的請求：

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

這會建立 v2 `.rkf-connect.toml` 與小型 `RKF/` bridge，不會複製中央 wiki。
每個新的 Codex task 仍從 RKF OFF 開始；task 開始時說「啟動 RKF」，完成後說
「停用 RKF」。

## 在 10 分鐘內完成第一個閉環

請用一篇公開或 synthetic paper 走完此流程，並依序在 Codex 輸入：

| 工作流 | 自然語言請求 | 預期結果 |
|---|---|---|
| **Add** | 「啟動 RKF，將 DOI `10.0000/example` 作為 candidate 加入，不要提升成 evidence。」 | 產生去重後的 capture receipt，包含 `Promotion: none` 與 project/activation lineage。 |
| **Ask** | 「Ask RKF 這篇 paper 對目標關係報告了什麼；沒有 locator 就明確說證據不足。」 | 回傳有 source boundary 的結果；支持 claim 的回答附 exact locator，否則回報 insufficient evidence。 |
| **Read** | 「Read 這篇 paper，將 p. 8, Fig. 3 的結果記為 supporting Evidence，先保持 unreviewed。」 | 產生包含 paper ID、locator、stance 與明確 verification state 的 Evidence card。 |
| **Compare & Synthesize** | 「將這筆 Evidence 與另一篇已確認 paper 比較，列出 agreement、contradiction、gap 與 provisional conclusion。」 | 產生連結 Evidence IDs 的 Claim 或 Synthesis，並保留尚未解決的 gap。 |
| **Review** | 「Review 這個 project：顯示缺 locator、待確認 evidence、disputed claims 與下一個閱讀行動。」 | 產生可執行 review，以及遮蔽路徑的 activation timeline。 |

這五條工作流就是完整的 v1 研究介面。Internal helper 與 compatibility code 不會形成
額外的產品模式。

## 安全邊界

- Candidate metadata 與 model output 不是 stable evidence。
- Verified claim 必須有 locator-backed、human-verified Evidence。
- PDF、article text、secret、token、absolute path、private index 與 raw prompt
  不進 public repository 或 public output。
- RKF 不繞過 paywall、CAPTCHA 或 access control。

Architecture、compatibility/removal 決策、release operation 與 public synthetic demo
統一由單一 [Maintainer reference](docs/MAINTAINER_REFERENCE.md) 進入。

[English](README.md) · License: MIT
