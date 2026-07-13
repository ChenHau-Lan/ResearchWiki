# Paper Intake Workflow

這份流程說明 RKF v1.1 的日常文獻整理方式：Codex app 是互動介面，Markdown pages 是
durable artifact。使用者不需要手動執行 CLI 才能整理 paper。

## 使用者入口

日常可以直接用自然語言交給 agent：

```text
幫我把這篇 DOI 建成 RKF paper note，客觀文獻整理、我的想法、AI 推論要分開。
```

也可以在 Obsidian、VS Code 或任何 Markdown editor 裡直接編輯
`knowledge/papers/*.md`。真正的 operational wiki 由 `rkf.workspace.toml` 的
`wiki_root` 指定；repo 本身保留 framework、docs、templates、tests、examples，
不要把個人 live wiki 搬回 repo。

## Paper Page 分層

每篇 paper note 應維持下列邊界：

| Section | 放什麼 | 不放什麼 |
|---|---|---|
| `Source Identity` | DOI、作者、期刊、年份、source record | project/manuscript 使用情境 |
| `Reading Maturity` | reading/fulltext/human feedback/claim readiness 與 ledger reference | 未驗證的 trust upgrade |
| `Research Question`、`Methods And Data`、`Main Findings` | 文獻本身的研究問題、方法資料與結果 | 個人建議、跨文獻推論 |
| `Evidence And Locators` | page/section/figure/table locator，以及來源明確支持或不支持的範圍 | 未定位的 stable claim |
| `Limitations And Boundaries` | 作者或已核對的限制、evidence boundary | 把限制藏在 project note |
| `Questions About This Paper` | 只問此 paper 的方法、資料、結果、圖、假設、限制或可重現性 | 更廣泛的研究方向或 manuscript strategy |
| `Intrinsic Links` | 此 paper 固有的 concept、method、dataset、subject topic | project-specific backlinks 或 cross-paper judgment |

使用者/AI 閱讀互動、project 關聯、tentative idea、broader question 與 claim proposal
預設走 `state/reading/`、inbox、question、project-synthesis、claim 或 synthesis。它們可以
指向 paper，但不能重新定義 paper 的重心。

## Claim Promotion Rule

reading ledger、inbox 或 question 中的 claim proposal 只是候選。要升級成 claim page 或
synthesis support，至少需要下列其中一種支持邊界：

- locator-backed evidence；
- 既有 supported RKF wiki page；
- annotated 或 trusted human feedback。

如果目前只有 explicit review blocker，應保留為候選或 blocked claim draft，清楚標示
不能升級的原因；不得作為 synthesis support。

Candidate、ARS output、hot query、route note、AI/Agent reading note 都不能單獨作為
stable claim evidence。

## Codex App 的角色

使用者在 Codex app 用自然語言要求 paper intake、reading queue、lint、index 或 graph
更新。Agent 會依 RKF skill routing 和 evidence boundary 執行必要的內部 action，並在
最後回報修改與驗證結果。

現有 Python runtime / legacy CLI 僅作為 Codex app、測試與維護使用的內部 shim。日常
閱讀與整理優先保持 Codex app + Markdown artifact 的流程。

## 安全邊界

- 不把 PDF、article full text、browser capture、private evidence path 寫進 public wiki。
- 不把 live 個人 wiki 當成測試 fixture 搬進 repo。
- 不把 AI 推論寫成來源已支持的結論。
- 不把 `hot.md`、candidate、ARS report、`fulltext_routes/*.md` 當成 evidence。
