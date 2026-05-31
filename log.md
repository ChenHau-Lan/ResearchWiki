# Wiki Log

## [2026-05-29] implementation | 將 LLM Wiki 對照轉成正式入口文件

### 觸發

使用者讀完上一筆 LLM Wiki 功能對照後，要求依照推薦方向製作改善。優先處理三件事：
README 定位、Obsidian-facing workflow、`log.md` 使用慣例。

### Evidence boundary

這是 RKF operation/design documentation record，不是 paper evidence，不支持學術 claim。
內容依據目前 repo 的 RKF skills、manual、README、CLI 行為和上一筆功能對照整理。

### Context

- `README.zh-TW.md` 已經說明 RKF 是 LLM Wiki-based research knowledge framework。
- `docs/manuals/rkf_manual.zh-TW.md` 已有 topic governance、evidence QC、hot-query、
  shared database 和 maintenance 說明。
- `log.md` 已有一筆 generic LLM Wiki 與 RKF 功能對照，但正式手冊尚未吸收該結論。

### Decision / Output

- 在 `README.zh-TW.md` 新增「RKF 與一般 LLM Wiki 的差異」，用表格說明 RKF 的
  evidence-governed 定位。
- 在 `docs/manuals/rkf_manual.zh-TW.md` 新增同名章節，強調 candidate、SourceRecord、
  evidence gate、claim boundary 與 public-safety。
- 在 `docs/manuals/rkf_manual.zh-TW.md` 新增「用 Obsidian 閱讀 RKF」，讓 Obsidian 成為
  閱讀、檢查與 graph view 介面，而不是繞過 gates 的寫入通道。
- 在 `docs/manuals/rkf_manual.zh-TW.md` 新增「`log.md` 與操作日誌慣例」，區分 compact
  event 與 narrative record。

### Follow-up

- 若要進一步貼近 Obsidian-first 使用者，可新增 Dataview query 範例與 graph review checklist。
- 若要支援 raw inbox，可新增 optional workflow，但必須把 raw/capture 明確限制為 candidate intake。
- 若要支援 Marp/report/chart，應作為 output layer，不得取代 evidence boundary。

## [2026-05-29] query | LLM Wiki 功能對照與 RKF 功能總覽

### 觸發

使用者提供一則 X 貼文，要求依照外部 LLM Wiki 範例，整理「外部範例與我們的
Research Knowledge Framework 目前共同具備的功能、各自具備的功能」，並用日誌形式
介紹 RKF 的完整功能。

外部參照：

- User-provided X pointer: <https://x.com/jinchenma_ai/status/2059842551218422004>
- Karpathy LLM Wiki gist: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
- Public LLM Wiki summaries that describe the same six-step pattern: read-only
  raw sources, LLM-maintained wiki pages, schema file, ingest, query, lint,
  index, log, and Obsidian browsing.

Evidence boundary：這是一則 workflow/design comparison log，不是 academic evidence。
外部貼文與公開整理只作為 LLM Wiki 架構參照；不升級成 paper evidence，也不支持任何
學術 claim。

### 兩者目前都有的功能

1. Persistent Markdown wiki：兩者都把知識沉澱成可讀、可版本管理的 Markdown，而不是
   只留在聊天紀錄或一次性 RAG 回答裡。
2. Source/wiki/schema 分層：外部範例用 `raw/ -> wiki/ -> CLAUDE.md`；RKF 用
   source/evidence state、`knowledge/`、`AGENTS.md`、skills 與 mode registry 形成更
   明確的治理層。
3. Ingest/capture 到 wiki 的流程：外部範例把 raw 資料交給 LLM 讀取、摘要、更新多個
   wiki pages；RKF 則從 DOI、URL、PDF、topic、idea、question 進入 `capture`，再依 gate
   決定能否寫入 paper、concept、question、claim 或 synthesis。
4. Query 與保存：兩者都能先讀既有 wiki context，再回答問題；有價值的回答可以回寫
   成穩定頁面，而不是消失在 chat history。
5. Lint/health check：兩者都有定期檢查矛盾、孤立頁、過期內容與缺失連結的維護概念。
6. `index.md` 與 `log.md`：兩者都把 index 當成 LLM 快速導航入口，把 log 當成跨 session
   的操作軌跡。
7. Graph 思維：外部範例依賴 Obsidian graph view；RKF 另有 typed research graph export，
   用來連接 source、evidence、topic 與 wiki pages。
8. Git-friendly operation：兩者都把 wiki 當成可 diff、可 review、可長期追蹤的文字庫。

### 外部範例目前較強或較明確的功能

1. Obsidian-first browsing：外部範例把 Obsidian 當成主要閱讀與圖譜 UI；RKF 目前以 CLI、
   Markdown docs、graph JSON 與 public-safe wiki state 為主，尚未把 Obsidian workflow
   做成核心產品介面。
2. Web clipper/raw inbox：外部範例常見 `raw/` 收件箱、Web Clipper、文章剪藏、圖片下載與
   asset folder；RKF 目前更重視 source identity、legal acquisition 與 private evidence
   boundary，沒有把一般網頁剪藏做成主要入口。
3. Query output formats：外部範例明確提到比較表、Marp slides、matplotlib chart 或 canvas
   等輸出；RKF 目前能保存 synthesis、overview、meeting、seminar 等 Markdown knowledge
   objects，但沒有把 Marp/chart/canvas 作為內建 mode。
4. Simple personal wiki ergonomics：外部範例偏向個人知識庫，使用門檻低；RKF 因為加入
   academic evidence gates，操作較嚴謹，也較重。
5. Obsidian plugin ecosystem：外部範例可直接利用 Dataview、graph view、Local REST API、
   Web Clipper 等插件；RKF 目前沒有綁定這些插件。

### RKF 目前獨有或更完整的功能

1. Academic evidence governance：RKF 明確區分 candidate、SourceRecord、EvidenceArtifact、
   GateDecision 與 KnowledgeObject。搜尋結果、ARS report、聊天回答都不是 evidence。
2. Paper evidence path：RKF 有 `capture -> acquire -> verify-pdf -> distill`，要求合法取得、
   PDF/OCR/visual QC、locator notes，才允許 paper wiki page。
3. Claim boundary：穩定 claim 需要 locator、既有 wiki source，或明確 review blocker。
   這避免把模型推測直接變成知識。
4. Private/public 分離：PDF、全文、browser capture、私人 Drive path、token 與本機機密不進
   public wiki；public repo 只保留 public-safe metadata、gate summary 與摘要性知識。
5. Topic governance：topic 有 aliases、scope、include/exclude rules、default search strings、
   canonical synthesis links、review cadence 與 candidate backlog。
6. Hot-query layer：`hot.md` 追蹤最近反覆出現的 public-safe 研究問題與 paper-search 需求，
   但不把它當 evidence。
7. ARS bridge：Academic Research Skills 可以做深度研究、推理、寫作與 review；RKF 只把
   ARS output 當 proposal，通過 bridge protocol 後才可能保存。
8. Typed graph export：RKF 可以輸出 `graph/research_graph.json`，把 source、evidence、
   topic、paper、concept、question、claim、synthesis 的關係以 typed edges 表示。
9. External sandbox protocol：RKF 可產生 context capsule，讓外部 sandbox 讀取 governed context；
   外部結果必須回到 save/review proposal，不能直接污染 evidence layer。
10. Shared database plan：`rkf-connect` 支援實驗性的 Google Drive shared RAW/wiki 設計、多電腦
    link-workspace、sandbox-grant 與 direct-write boundary。
11. Public-safety lint：RKF 提供 public safety scan，防止 PDF、全文、本機路徑、private Drive
    path、browser capture 或 secrets 被發布。
12. Tested CLI baseline：RKF 有 `tools/rk.py`、schemas、templates、unit tests、compile checks、
    topic lint、RKF lint 與 public safety scan。

### RKF 完整功能清單

`rkf-evidence-vault`

- `capture`：攝取 DOI、URL、PDF pointer、topic seed、idea 或 question，建立 SourceRecord。
- `discover`：建立 candidate discovery run；候選文獻仍然不是 evidence。
- `acquire`：記錄或核准合法 PDF/evidence route，建立 acquisition checkpoint。
- `verify-pdf`：做 PDF/OCR/visual QC、source identity/readability check 與 locator notes。

`rkf-knowledge-synthesis`

- `distill-paper`：從 QCed paper artifact 建立 `knowledge/papers/*.md`。
- `save-question`：保存開放問題、不確定性或 search plan。
- `save-concept`：保存可重用的方法、機制、dataset、instrument 或 variable。
- `save-claim`：保存有 locator 或 review blocker 的 claim。
- `synthesize`：保存跨來源判斷、研究建議或 durable answer。
- `topic-governance`：維護 topic ID、aliases、scope、include/exclude、default search。
- `topic-review`：檢查 topic drift、merge/split、stale candidates、search quality。

`rkf-wiki-core`

- `query`：取回 governed wiki context，必要時交給 ARS reasoning，再回傳 answer 與保存建議。
- `hot-query`：記錄反覆研究問題與 paper-search demand 到 `hot.md`。
- `save`：保存非 paper 的 durable wiki object。
- `graph`：輸出 typed source/evidence/wiki/topic graph。
- `external-sandbox`：產生可交給其他 sandbox 的 compact context capsule。

`rkf-lint`

- `structure-lint`：檢查 frontmatter、page type、required sections 與 topic registry。
- `evidence-lint`：檢查 evidence gates、metadata-only promotion、claim boundary。
- `graph-lint`：檢查 typed graph links 與 broken wiki links。
- `ars-handoff-lint`：確認 ARS output 被標為 proposal，而不是 evidence。
- `public-safety-lint`：檢查 PDF、全文、本機路徑、private state 與 secrets。
- `repair-plan`：只輸出修復建議，不自動重寫知識或刪檔。

`rkf-connect`

- `shared-database-plan`：規劃 shared Drive research folder 與 RAW/wiki layout。
- `link-workspace`：規劃各台電腦把 Drive RAW/wiki 連回 RKF workspace 的本機 link。
- `sandbox-grant`：定義外部 sandbox 的 read/write boundary。
- `sandbox-bootstrap`：產生外部 sandbox 啟動提示。
- `sandbox-direct-write`：可信任 sandbox 仍需走 RKF CLI gates 才能寫入。
- `sandbox-save-proposal`：外部 sandbox 只能回傳 save/review proposal，除非寫入路徑明確核准。

Knowledge object types

- `paper`
- `question`
- `concept`
- `claim`
- `topic`
- `synthesis`
- `overview`
- `project-synthesis`
- `meeting`
- `seminar`

Core maintained files and outputs

- `index.md`：LLM session 的 compact retrieval entrypoint。
- `log.md`：append-oriented operation timeline。
- `hot.md`：public-safe rolling dashboard for repeated research demand。
- `state/sources/*.json`：SourceRecord metadata。
- `state/evidence/*.json`：public-safe evidence artifact pointer。
- `state/gates/**/*.md`：evidence gate summaries and checkpoints。
- `knowledge/**/*.md`：public-safe wiki knowledge pages。
- `governance/topic_registry.json`：topic controls。
- `graph/research_graph.json`：typed research graph。
- `prompts/external_sandbox_bootstrap.*.md`：外部 sandbox bootstrap prompts。

### 判斷

外部範例是通用、Obsidian-friendly、低門檻的 LLM Wiki 操作範式。RKF 是同一範式在
academic research 場景下的治理化版本：它犧牲一部分輕量與即時性，換取 evidence boundary、
locator-backed claims、topic governance、ARS proposal boundary、public safety 與可審計的
研究記憶。

### 後續補強建議

1. 若要更像外部範例，可補一個 Obsidian-facing setup guide，說明如何把 `knowledge/`、`index.md`、
   `log.md`、`hot.md` 與 graph view 配合使用。
2. 可新增 optional raw inbox workflow，但要維持 RKF 原則：raw/capture 是 candidate intake，
   不能跳過 acquisition、QC 與 claim support gates。
3. 可新增 Marp/report/chart export proposal，作為 `query` 或 `synthesize` 的輸出形式，而不是
   讓投影片或圖表取代 evidence boundary。
4. 可把這篇 log 的功能對照濃縮進 README 或 manual，作為「RKF vs generic LLM Wiki」的導覽。
