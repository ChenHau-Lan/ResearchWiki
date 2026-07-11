# RKF Codex App Workflows And Capabilities

這份文件是目前 Research Knowledge Framework 的功能盤點與 Codex app 工作流速查。
檔名仍保留 `FEATURES_AND_COMMANDS` 以維持既有連結相容；內容不再把 CLI 當成
使用者互動介面。

## 使用入口原則

RKF 1.1 的互動入口是 Codex app。每個新 task 預設 RKF OFF；使用者明確說
「啟動 RKF」後，agent 才以 `rkf.activate` 完成 read-only preflight，並接受 capture、整理、查詢、review、
lint 或連接其他專案。`knowledge/` 下的 Markdown pages 是 durable artifact，不是要求
使用者手動操作 CLI 的前台介面。

Python runtime 透過 `rkf.actions` 提供 structured action request/result。現有
legacy CLI 只作為 Codex app、測試與維護使用的內部 shim。新的使用者文件應描述
「要在 Codex app 怎麼問」，不要要求使用者記 command syntax。

## 核心功能

| 功能 | 用途 | 主要輸出 |
|---|---|---|
| Source capture | 攝取 DOI、URL、PDF pointer、topic seed、idea、question | `state/sources/*.json` |
| Inbox capture | 把 ChatGPT 對話片段、網頁 clip、DOI、URL 與想法先放進低風險 inbox；DOI 只做保守 source/paper backlink injection | `knowledge/inbox/*.md`、可選 `state/sources/*.json`、`knowledge/papers/*.md` backlink |
| Auto-connect helper | 啟動後才分類跨專案研究內容並建立 structured request；helper 本身不能啟動 session 或直接繞過 guard 寫入 | global `rkf-auto-connect` skill、`tools/rkf_auto_connect.py`、`.rkf-connect.toml`、`RKF/` |
| Discovery staging | 建立候選文獻搜尋 run；候選可啟動 draft，但不是 claim evidence | `state/search_runs/*/candidates.json`、`hot.md` |
| Paper reading draft | 從 metadata、abstract、partial full text 或 PDF 先建立 paper draft；頁面分開 source-grounded summary、locator/evidence、reader notes、AI/Agent notes 與 claim candidates | `knowledge/papers/*.md` |
| Full-text status | 標記 `needs-user-pdf`、`user-pdf-provided`、`fulltext-read` 等狀態 | source frontmatter/JSON、paper frontmatter |
| Reading ledger | 記錄 public-safe reading event、問題、AI 回答、人為修正、trust 變化與 blocker | `state/reading/*.json` |
| User PDF handling | 只有讀不到全文時要求 user 提供 PDF；可直接更新 full-text state | `state/evidence/*.json` |
| Locator/readability check | 記錄 artifact identity、readability、locator notes，提升 claim readiness | `state/evidence/*.json`、paper maturity |
| Paper queue/nudge | 推播 metadata-only、缺 PDF、缺人為 feedback、重複被問、可進 synthesis review 的 paper | Codex app report / automation digest |
| Non-paper save | 保存 question、concept、claim、synthesis、overview、meeting、seminar | `knowledge/*/*.md` |
| Hot-query layer | 追蹤近期 public-safe 研究問題與 paper-search demand | `hot.md` |
| Session activation | 每個新 task 從 OFF 開始；read-only preflight 後才進 ACTIVE 或 ACTIVE_READ_ONLY | `rkf.activate`、`rkf.status`、`rkf.deactivate` |
| Deterministic retrieval | 先從 RKF 找 exact identifier、alias、keyword、topic 與 graph context，並回報 maturity/evidence boundary | `query.search` |
| Event-first capture | 分類、去重、先寫 immutable event，再由單一 writer 投影 inbox/hot/wiki；writer 可用 checkpoint 安全重試 queued/partial event；不自動 promotion | `capture.route`、`capture.project_pending`、`state/events/` |
| Action runtime | 讓 Codex app 以 session-owned structured runtime 執行 guarded read/write path | `rkf/actions.py` |
| Topic governance | 維護 topic id、scope、aliases、include/exclude、default search strings | `governance/topic_registry.json`、`knowledge/topics/*.md` |
| L0-L3 world context | 快速重建 identity、critical facts、active reading、claim readiness、graph/detail links 與 validation state | Codex app report |
| Health snapshot | 以 Codex app report 顯示 sources、paper queue、claim readiness、maturity、hot-query 與 lint 摘要 | `stats.snapshot` action |
| Critical facts | 保存短句、public-safe、可重用且有時間 metadata 的 facts | `CRITICAL_FACTS.md` |
| Future Agent Retrieval Brief | 在 paper / synthesis / topic template 說明何時讀頁、可信度、缺口與下一步 | `templates/rkf/*.md`、knowledge pages |
| Priority evolve | 低風險 rewrite existing page，並在頁內留下 `AI Integration Note`；高風險只留下 blocker / maturity downgrade | knowledge pages |
| Reconcile | 自動找同 topic/page 間的 contradiction hints，並以 AI Integration Note 寫入 blocker | knowledge pages |
| Challenge | 用 RKF 自己的知識反駁目前頁面或 synthesis，不建立 stable claim | Codex app critique |
| Emerge | 從 reading queue、hot queries、topic state 找 unnamed patterns，建立 low-maturity synthesis draft | Codex app report / `knowledge/synthesis/*.md` |
| Agent prompt templates | Morning/nightly/weekly/health agent prompt，不建立實際 automation | `prompts/agents/*.md` |
| Bi-temporal memory | claim / synthesis / critical facts 可記錄 `observed_at`、`valid_from`、`valid_until`、`supersedes` | frontmatter / `CRITICAL_FACTS.md` |
| Propagation review | 新 evidence、reading maturity 或 synthesis 後列出可能受影響頁面，作為 preview/audit fallback | Codex app report 或 `state/gates/propagation/*.md` |
| Graph export / traversal | 輸出 source/evidence/wiki/topic typed links，並用 `graph.neighbors`、`graph.paths`、`graph.page_context` 在 Codex app 內讀取 public-safe graph context | `graph/research_graph.json` / Codex app report |
| Index generation | 產生 LLM retrieval 入口，包含 maturity hints | `index.md` |
| Codex handoff capsule | 產生其他 Codex session / project handoff 使用的 RKF context | `prompts/codex_handoff_context.md` |
| Lint and safety scan | 檢查 structure、maturity、claim boundary、graph、ARS handoff、public safety | Codex app report |
| Open-source template scan | 記錄可借鏡的 PKM/wiki/digital-garden 模式與目前不採用的 runtime | `docs/references/open-source-template-scan.zh-TW.md` |

## Reading And Evidence Rules

- Search candidate 和 metadata 可以建立 paper draft，但不是 stable claim evidence。
- Inbox item 是低風險 capture object；可保留 short clip、來源、DOI、reader note 與
  AI/Agent note，但不能單獨作為 stable claim evidence。
- ARS output 本身不是 evidence；進 RKF 前只能是 proposal 或 review blocker。
- Paper draft 要明確記錄 `reading_state`、`fulltext_status`、`human_feedback_level`、
  `understanding_confidence`、`claim_readiness` 和 `reading_ledger`。
- Paper draft body 要分開 `Source-Grounded Summary`、`Extracted Evidence And Locators`、
  `Reader Notes`、`AI/Agent Notes`、`Questions And Feedback` 與
  `Claims To Promote`。
- `Reader Notes` 可以保存使用者主觀判斷；`AI/Agent Notes` 可以保存 AI 推論；
  兩者都不能單獨作為 stable claim evidence。
- 讀不到全文時，標記 `fulltext_status: needs-user-pdf`，並請 user 提供 PDF。
- Stable claim / trusted synthesis 需要 locator、人為 feedback、或既有 wiki source。
  明確 review blocker 只能保留候選/blocked 狀態，不能作為 synthesis support。
- Durable full article text 不進 public knowledge layer。
- `save` 和 `synthesize` 預設不覆寫既有 knowledge object；要更新必須明確使用
  `--update`。
- Propagation review 是 manual preview / audit fallback；正常狀態查看請先用 `world`。

## Codex App Workflow Inventory

在 Codex app 中用自然語言提出工作，agent 會依 `MODE_REGISTRY.md` 路由到正確 skill
與內部 RKF action。下面是使用者應看到的工作流，而不是命令清單。

| 使用者說法 | Structured action | 行為邊界 |
|---|---|---|
| 啟動 RKF | `rkf.activate` | 唯讀 preflight；回傳遮蔽路徑的 session receipt |
| 問 RKF：... | `query.search` | 先查中央 RKF；不足才讀 project-local |
| 收進 RKF：... | `capture.route` | 先寫 immutable event；回報 dedupe、queued/materialized、`Promotion: none` |
| 停用 RKF | `rkf.deactivate` | 本 task 後續不再查詢或攝入 RKF |

| Workflow | 在 Codex app 可以這樣說 | 主要邊界 |
|---|---|---|
| Capture source | 「把這個 DOI/URL 加入 RKF，先建立保守 source record。」 | 只確認 source identity，不升級 claim |
| Save to inbox | 「把這段 ChatGPT/web clip 存到 inbox，我的想法和來源內容分開。」 | Inbox item 不是 evidence |
| Activate RKF | 「啟動 RKF。」 | 只啟動目前 task；先做 storage/writer preflight |
| Query wiki | 「先用 RKF 找這個 DOI／概念。」 | 使用 `query.search`；答案不自動成為 wiki page |
| Auto-connect capture | 「這個外部專案討論有研究價值，幫我回饋到 RKF。」 | 啟動後透過 `capture.route` 先記 event；`Promotion: none` |
| Deactivate RKF | 「停用 RKF。」 | 使用 `rkf.deactivate`；後續 action 再次被 OFF guard 阻擋 |
| Discover papers | 「針對這個 topic 找候選文獻，但不要把 candidates 當 evidence。」 | Candidate 只能啟動 draft |
| Create paper draft | 「就算目前只有 metadata，也幫我建 paper draft 並標清楚 maturity。」 | Paper page 必須保守標記 reading state |
| Request user PDF | 「列出哪些 paper 需要我提供 PDF。」 | 不繞過 paywall 或授權限制 |
| Record provided PDF | 「我提供了 PDF，請更新 full-text status 並保留 private evidence 邊界。」 | Public wiki 只留 safe pointer/locator |
| Verify locators | 「檢查這篇 paper 的 locator/readability，能不能支撐 claim readiness？」 | Claim readiness 需要 locator 或人為 review |
| Record feedback | 「我剛討論/註解了這篇，請寫入 reading ledger。」 | Ledger 是 operational memory |
| Paper queue | 「列出今天最需要處理的 paper queue/nudges。」 | 只回報 public-safe 摘要 |
| Health snapshot | 「幫我看 RKF 今天最需要處理什麼。」 | Read-only report；不提升 evidence maturity |
| Query governed context | 「問 RKF 現在知道什麼，必要時讓 ARS 對 retrieved context 推理。」 | 回答不自動變 wiki page |
| Save knowledge | 「把這個問題/概念/claim/synthesis 保存成 RKF page。」 | 覆寫既有頁要明確要求 |
| Record hot demand | 「把這個 paper-search 問題記到 hot.md。」 | `hot.md` 是 demand dashboard，不是 evidence |
| Topic governance | 「幫我新增/整理 topic registry，檢查 aliases 與 search strings。」 | 大型 merge/split 先提案 |
| Maintenance review | 「跑 RKF health check，找 maturity/evidence/graph/public-safety 問題。」 | Lint 可回報/規劃，不靜默重寫 |
| Evolve page | 「低風險地更新這頁，留下 AI Integration Note。」 | 高風險內容要 blocker 或 maturity downgrade |
| Reconcile | 「找這個 topic 的矛盾，標成 AI-marked blockers。」 | 不假裝矛盾已被 human-resolved |
| Challenge | 「用 RKF 既有知識反駁這個 synthesis。」 | Critique 不是 stable claim |
| Emerge | 「從 reading queue/hot/topic state 找 unnamed patterns，保持 low maturity。」 | Auto-synthesis 從 draft 開始 |
| Propagation review | 「新 evidence 可能影響哪些頁，先列出 preview。」 | 只是 audit fallback |
| World context | 「開始前給我 L0-L3 world context。」 | 用於 Codex session bootstrap |
| Graph/index | 「更新 graph/index 讓未來 retrieval 更準。」 | 只產生 public-safe graph/index |
| Codex handoff | 「把目前 RKF context 交給另一個 Codex session/project。」 | 預設 read/proposal boundary |

## Legacy Runtime Boundary

現有 `tools/rk.py` / `rkf/cli.py` 保留為 legacy/dev shim，供 Codex app agent、測試與維護使用。
`rkf.actions` 以 session-owned `RKFActionRuntime` 執行；`rkf.activate`、
`query.search`、`capture.route` 與 `rkf.deactivate` 是 Phase 1 的正式 action
boundary。Auto-connect helper 只建立 request，不能自行取得 ACTIVE 狀態。CLI 不是正式使用者控制介面。
新增或修改能力時，優先描述 Codex app 工作流與 RKF action 邊界；不要新增面向使用者的 CLI 教學。

## Validation

發布、開 PR 或完成較大修改前，請在 Codex app 要求 agent 執行最小相關驗證，並回報：

- 使用了哪些 test/lint/public-safety 檢查。
- 是否涉及 live `wiki_root` 或只動到 repo fixture/example。
- 是否有 existing failure、環境限制或未執行的檢查。

## Current Cleanup Candidates

這些是目前工作目錄中看起來不需要提交，或只應該留在本機的檔案/目錄。本文件只列出
建議；沒有刪除任何檔案。

| Path | 狀態 | 建議 |
|---|---|---|
| `.DS_Store` | ignored local macOS metadata | 可刪除，不應提交 |
| `rkf/__pycache__/` | ignored Python cache | 可刪除，不應提交 |
| `tests/__pycache__/` | ignored Python cache | 可刪除，不應提交 |
