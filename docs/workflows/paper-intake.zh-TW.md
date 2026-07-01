# Paper Intake Workflow

這份流程說明 RKF v0 的日常文獻整理方式：Markdown 是主要工作介面，CLI 是 agent
與 automation 的薄後端。使用者不需要手動執行 CLI 才能整理 paper。

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
| `Source-Grounded Summary` | 文獻本身支持的研究問題、方法、結果、限制 | 個人建議、跨文獻推論 |
| `Extracted Evidence And Locators` | page/section/figure/table locator，以及來源明確支持或不支持的範圍 | 未定位的 stable claim |
| `Reader Notes` | 使用者自己的理解、研究關聯、主觀判斷 | 偽裝成文獻結論的個人看法 |
| `AI/Agent Notes` | AI 摘要、未驗證推論、需要人工查核的點 | claim evidence |
| `Questions And Feedback` | public-safe 問題、人為回饋、open blocker | 私人全文、private path |
| `Claims To Promote` | 候選 claim、必要 locator/blocker、caveat | 沒有邊界的 stable claim |

## Claim Promotion Rule

`Claims To Promote` 裡的內容只是候選。要升級成 claim page 或 synthesis support，
至少需要下列其中一種支持邊界：

- locator-backed evidence；
- 既有 supported RKF wiki page；
- annotated 或 trusted human feedback。

如果目前只有 explicit review blocker，應保留為候選或 blocked claim draft，清楚標示
不能升級的原因；不得作為 synthesis support。

Candidate、ARS output、hot query、route note、AI/Agent Notes 都不能單獨作為
stable claim evidence。

## CLI 的角色

CLI 是 agent-safe backend，不是使用者一定要手動操作的入口。Agent 或 automation
可以在背後使用：

```bash
python3 tools/rk.py distill paper <source_id>
python3 tools/rk.py paper queue
python3 tools/rk.py lint
python3 tools/rk.py index
python3 tools/rk.py graph
```

手動使用 CLI 適合可重現檢查、批次整理、debug、或 automation 設定。日常閱讀與整理
優先保持 Markdown-first。

## 安全邊界

- 不把 PDF、article full text、browser capture、private evidence path 寫進 public wiki。
- 不把 live 個人 wiki 當成測試 fixture 搬進 repo。
- 不把 AI 推論寫成來源已支持的結論。
- 不把 `hot.md`、candidate、ARS report、`fulltext_routes/*.md` 當成 evidence。
