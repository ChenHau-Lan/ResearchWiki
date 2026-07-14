# Research Knowledge Framework（RKF）

RKF 把論文轉成可回到原文位置、可看出支持與反駁證據，並經人工確認的研究知識。

> Paper → locator-backed Evidence → human-reviewed Claim → Synthesis

目前相容更新目標為 `v1.1.0`；既有公開 `v1.0.0` tag 不重寫。

## 五條研究工作流

1. **Add**：加入 DOI、URL、PDF pointer、Zotero item、note 或選定 paper。
2. **Ask**：限定 paper/topic 查詢；有證據的回答必須附 locator，否則明確回報證據不足。
3. **Read**：記錄 annotation、correction、Evidence 與 human verification。
4. **Compare & Synthesize**：整理 agreement、contradiction 與 evidence gap。
5. **Review**：顯示下一步研究行動與 connected-project activity。

## 從其他專案使用 RKF

先 preview/apply `connect-project`，建立 v2 `.rkf-connect.toml` 與輕量 `RKF/` bridge。
Bridge 不複製第二份 wiki。每個 Codex task 仍從 OFF 開始，必須明確說「啟動 RKF」。

每個 project 有隨機且穩定的 `project_id`；每次啟動有 `activation_id`；每個 action
都留下 append-only、path-redacted event。Review 可追查哪個 project、哪次 activation
查詢或修改了研究物件。Raw prompt 預設不保存。

## v1 核心 action

```text
rkf.activate / rkf.status / rkf.deactivate / connect.validate
workflow.add
workflow.ask
workflow.read
workflow.compare-synthesize
workflow.review
```

Python modules 與 legacy CLI 只保留為 internal compatibility surface，不是新手入口。

## Optional providers

v1 只定義全文取得、appraisal 與 semantic retrieval 的小型 contract；沒有安裝 adapter 時，
deterministic core 仍可完整使用。`paper-fetch`、`paper-review-and-digest`、`vault-search`
是整合參考，不會把 browser login、重依賴或另一套 UI 搬進 core。完整 Scientific Artifact
Acquisition Engine 留在 vNext。

## 安全邊界

- Candidate、metadata 與 LLM output 不是 stable evidence。
- Verified claim 必須有 locator-backed、human-verified Evidence。
- PDF、article text、secret、private path 與 raw prompt 不公開。
- 不繞過 paywall、CAPTCHA 或 access control。
- 取得 PDF 不等於可讀、已讀或已支持 claim。

## 文件

- [快速開始](docs/GETTING_STARTED.zh-TW.md)
- [架構](docs/ARCHITECTURE.md)
- [v1 scope inventory](docs/V1_SCOPE_INVENTORY.md)
- [工作流 registry](MODE_REGISTRY.md)
- [Public guided demo](https://chenhau-lan.github.io/ResearchWiki/)

## 版本管理

`v1.0.0` 保持不變；本次相容 schema 與 workflow 更新目標為 `v1.1.0`。
