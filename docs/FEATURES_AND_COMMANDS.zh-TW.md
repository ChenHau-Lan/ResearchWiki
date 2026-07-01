# RKF Current Features And Commands

這份文件是目前 Research Knowledge Framework 的功能盤點與指令速查。它描述目前
repo 已有的能力、日常怎麼用、以及哪些檔案或目錄看起來只是本機狀態或清理候選。

## 使用入口原則

RKF v0 採用 Markdown-first workflow：`knowledge/` 下的 Markdown pages 是主要使用者介面，
agent 可以用自然語言協助建立、整理與更新頁面。CLI 保留為薄後端，用於可重現的
source capture、paper draft 產生、queue、lint、index、graph 與 automation；使用者
不需要手動執行 CLI 才能完成日常文獻整理。

## 核心功能

| 功能 | 用途 | 主要輸出 |
|---|---|---|
| Source capture | 攝取 DOI、URL、PDF pointer、topic seed、idea、question | `state/sources/*.json` |
| Inbox capture | 把 ChatGPT 對話片段、網頁 clip、DOI、URL 與想法先放進低風險 inbox；DOI 只做保守 source/paper backlink injection | `knowledge/inbox/*.md`、可選 `state/sources/*.json`、`knowledge/papers/*.md` backlink |
| Auto-connect helper | 跨專案偵測研究相關搜尋、DOI/URL、web clip 與有價值研究討論，並自動回饋到 RKF inbox/hot.md；可在外部專案建立 `RKF/` bridge folder 作為 project-local index | global `rkf-auto-connect` skill、`tools/rkf_auto_connect.py`、`.rkf-connect.toml`、`RKF/` |
| Discovery staging | 建立候選文獻搜尋 run；候選可啟動 draft，但不是 claim evidence | `state/search_runs/*/candidates.json`、`hot.md` |
| Paper reading draft | 從 metadata、abstract、partial full text 或 PDF 先建立 paper draft；頁面分開 source-grounded summary、locator/evidence、reader notes、AI/Agent notes 與 claim candidates | `knowledge/papers/*.md` |
| Full-text status | 標記 `needs-user-pdf`、`user-pdf-provided`、`fulltext-read` 等狀態 | source frontmatter/JSON、paper frontmatter |
| Reading ledger | 記錄 public-safe reading event、問題、AI 回答、人為修正、trust 變化與 blocker | `state/reading/*.json` |
| User PDF handling | 只有讀不到全文時要求 user 提供 PDF；可直接更新 full-text state | `state/evidence/*.json` |
| Locator/readability check | 記錄 artifact identity、readability、locator notes，提升 claim readiness | `state/evidence/*.json`、paper maturity |
| Paper queue/nudge | 推播 metadata-only、缺 PDF、缺人為 feedback、重複被問、可進 synthesis review 的 paper | terminal report / automation digest |
| Non-paper save | 保存 question、concept、claim、synthesis、overview、meeting、seminar | `knowledge/*/*.md` |
| Hot-query layer | 追蹤近期 public-safe 研究問題與 paper-search demand | `hot.md` |
| Topic governance | 維護 topic id、scope、aliases、include/exclude、default search strings | `governance/topic_registry.json`、`knowledge/topics/*.md` |
| L0-L3 world context | 快速重建 identity、critical facts、active reading、claim readiness、graph/detail links 與 validation state | terminal report |
| Critical facts | 保存短句、public-safe、可重用且有時間 metadata 的 facts | `CRITICAL_FACTS.md` |
| Future Agent Retrieval Brief | 在 paper / synthesis / topic template 說明何時讀頁、可信度、缺口與下一步 | `templates/rkf/*.md`、knowledge pages |
| Priority evolve | 低風險 rewrite existing page，並在頁內留下 `AI Integration Note`；高風險只留下 blocker / maturity downgrade | knowledge pages |
| Reconcile | 自動找同 topic/page 間的 contradiction hints，並以 AI Integration Note 寫入 blocker | knowledge pages |
| Challenge | 用 RKF 自己的知識反駁目前頁面或 synthesis，不建立 stable claim | terminal critique |
| Emerge / auto-synthesis | 從 reading queue、hot queries、topic state 找 unnamed patterns，建立 low-maturity synthesis draft | terminal report / `knowledge/synthesis/*.md` |
| Agent prompt templates | Morning/nightly/weekly/health agent prompt，不建立實際 automation | `prompts/agents/*.md` |
| Bi-temporal memory | claim / synthesis / critical facts 可記錄 `observed_at`、`valid_from`、`valid_until`、`supersedes` | frontmatter / `CRITICAL_FACTS.md` |
| Propagation review | 新 evidence、reading maturity 或 synthesis 後列出可能受影響頁面，作為 preview/audit fallback | terminal report 或 `state/gates/propagation/*.md` |
| Graph export | 輸出 source/evidence/wiki/topic typed links | `graph/research_graph.json` |
| Index generation | 產生 LLM retrieval 入口，包含 maturity hints | `index.md` |
| External sandbox capsule | 產生外部 sandbox 使用的 RKF context | `prompts/external_sandbox_context.md` |
| Lint and safety scan | 檢查 structure、maturity、claim boundary、graph、ARS handoff、public safety | terminal report |
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

## Common Commands

所有指令以下列形式執行：

```bash
python3 tools/rk.py <command>
```

## Full Command Inventory

這份 inventory 對齊目前 `rkf/cli.py` parser。若新增 CLI，請同步更新這一段。

| Command | Major Options | Purpose |
|---|---|---|
| `capture <kind> <value>` | `kind=doi/url/pdf/topic/idea/question`, `--title`, `--topic-id`, `--note` | 建立 SourceRecord 或 public-safe lead |
| `inbox capture <title>` | `--origin`, `--source-url`, `--doi`, `--clip`, `--reader-note`, `--agent-note`, `--topic-id`, `--no-inject` | 建立 inbox item；有 DOI 時預設建立/連回 SourceRecord 與 paper backlink |
| `discover <query>` | `--topic-id` | 建立 discovery run 與 candidate backlog |
| `acquire <source>` | `--pdf`, `--url`, `--screenshot`, `--approve`, `--checkpoint` | 記錄 full-text route、user PDF 或 legacy checkpoint |
| `verify-pdf <source_id>` | `--locator`, `--note`, `--qc-status codex_qc_done/human_qc_done` | 記錄 locator/readability check 並提升 reading maturity |
| `read <source_id>` | none | 顯示 source record |
| `distill paper <source_id>` | `--slug` | 建立或更新分層 paper reading draft；通常由 agent/automation 在背後呼叫 |
| `paper status [source_id]` | optional `source_id` | 顯示 paper queue/status |
| `paper feedback <source_id>` | `--level`, `--note`, `--reading-state`, `--fulltext-status`, `--confidence`, `--claim-readiness` | 記錄 human/AI reading feedback 並追加 ledger |
| `paper queue` | `--limit` | 列出 active paper nudges |
| `paper next` | none | 顯示最高優先 paper nudge |
| `paper nudge` | `--limit` | 輸出可排程推播文字 |
| `topic add <topic_id> <name>` | `--scope`, `--alias`, `--include`, `--exclude`, `--search`, `--cadence` | 新增 governed topic |
| `topic list` | none | 列出 topic registry |
| `topic lint` | none | 檢查 topic registry |
| `query <text>` | `--no-record` | 搜尋 wiki 並預設記錄 hot-query |
| `save <object_type> <title>` | `--slug`, `--body`, `--update` | 保存 question/concept/claim/overview 等非 paper object |
| `synthesize <title>` | `--slug`, `--body`, `--update` | 建立或更新 draft synthesis |
| `synthesize auto` | `--write`, `--topic-id`, `--limit` | `emerge` 的 auto-synthesis alias |
| `review` | none | 列出 pending gate/review items |
| `lint` | `--mode all/structure-lint/evidence-lint/graph-lint/ars-handoff-lint/public-safety-lint/repair-plan` | 執行 RKF health checks |
| `evolve <target>` | `--note`, `--source`, `--priority low/medium/high`, `--blocker`, `--dry-run` | maturity-aware 直接整合低風險頁面更新並留下 AI Integration Note |
| `reconcile` | `--topic-id`, `--limit`, `--dry-run` | 找矛盾並把高風險矛盾寫成 AI-marked blocker |
| `challenge <target>` | `--limit` | 用 RKF 既有頁面列出 counterpoints、missing evidence、maturity downgrade 建議 |
| `emerge` | `--topic-id`, `--limit`, `--write` | 找 unnamed patterns；`--write` 建立 low-maturity synthesis draft |
| `propagate <target>` | `--write` | 產生 affected-page propagation preview/audit |
| `graph` | none | 匯出 research graph |
| `status` | `--log-tail` | 輸出 RKF L0-L3 context capsule |
| `world` | `--log-tail` | `status` alias，用於 future-agent session bootstrap |
| `index` | none | 產生 compact LLM wiki index |
| `log` | `--tail`, `--action`, `--note` | 讀取或追加 operation log |
| `hot record <query>` | `--topic-id`, `--origin`, `--intent`, `--paper-lead`, `--notes` | 記錄 public-safe hot query event |
| `hot refresh` | `--days` | 重新產生 `hot.md` dashboard |
| `export graph` | none | 同 `graph` |
| `export external-sandbox` | none | 產生外部 sandbox capsule |
| `prompt external-sandbox` | none | 產生外部 sandbox prompt context |

### Source, Draft, And Reading

Capture DOI or URL:

```bash
python3 tools/rk.py capture doi "10.1234/example" --title "Example Paper" --topic-id "topic-id"
python3 tools/rk.py capture url "https://example.org/report.pdf" --title "Official Report"
```

Capture a ChatGPT or web clip into the inbox:

```bash
python3 tools/rk.py inbox capture "ChatGPT note on aerosol paper" \
  --origin chatgpt-web \
  --source-url "https://chatgpt.com/share/CONVERSATION_ID" \
  --doi "10.1234/example" \
  --clip "Short public-safe excerpt or source-grounded summary." \
  --reader-note "My idea or project relation."
```

Keep a DOI lead in the inbox without paper backlink injection:

```bash
python3 tools/rk.py inbox capture "Untriaged DOI lead" --doi "10.1234/example" --no-inject
```

Classify whether a cross-project discussion should be captured:

```bash
python3 tools/rkf_auto_connect.py classify "Find DOI 10.1234/example papers for aerosol-cloud parameterization" --project-name ResearchProject
```

Create a project-local RKF bridge folder without storing private paths:

```bash
python3 tools/rkf_auto_connect.py bridge-folder /path/to/project --project-name ResearchProject
```

Stage a discovery run:

```bash
python3 tools/rk.py discover "aerosol cloud interaction Taiwan" --topic-id "aerosol-cloud"
```

Create a conservative paper draft even before full text is available:

```bash
python3 tools/rk.py distill paper doi_10_1234_example
```

Mark that full text is missing and user PDF is needed:

```bash
python3 tools/rk.py acquire doi_10_1234_example
```

Record a user-provided PDF and update full-text state:

```bash
python3 tools/rk.py acquire doi_10_1234_example --pdf "/path/to/paper.pdf"
```

Check locator/readability after a PDF is available:

```bash
python3 tools/rk.py verify-pdf doi_10_1234_example --locator "pp. 3-5 methods" --note "identity checked"
```

Record human feedback or trust change:

```bash
python3 tools/rk.py paper feedback doi_10_1234_example --level discussed --note "User clarified the method interpretation."
```

Show active reading queue and scheduled nudge text:

```bash
python3 tools/rk.py paper queue
python3 tools/rk.py paper next
python3 tools/rk.py paper nudge --limit 5
```

Legacy compatibility remains available:

```bash
python3 tools/rk.py acquire doi_10_1234_example --pdf "/path/to/paper.pdf" --checkpoint
```

### Query, Save, And Hot Questions

Query wiki pages and record a hot-query event:

```bash
python3 tools/rk.py query "terrain rainfall field campaigns"
```

Query without recording:

```bash
python3 tools/rk.py query "private scratch question" --no-record
```

Save a non-paper object:

```bash
python3 tools/rk.py save question "Future Taiwan observation experiment" --body "Reusable question body."
python3 tools/rk.py save concept "Orographic locking" --body "Reusable concept note."
python3 tools/rk.py synthesize "Taiwan field campaign priorities" --body "Draft synthesis body."
```

Update an existing non-paper object intentionally:

```bash
python3 tools/rk.py save concept "Orographic locking" --body "Updated body." --update
python3 tools/rk.py synthesize "Taiwan field campaign priorities" --body "Updated synthesis." --update
```

Record and refresh hot-query demand:

```bash
python3 tools/rk.py hot record "Which wildfire smoke papers still need full read?" --intent paper-search --topic-id wildfire-smoke-cloud-microphysics
python3 tools/rk.py hot refresh --days 30
```

### Topic Governance

Add a governed topic:

```bash
python3 tools/rk.py topic add aerosol-cloud "Aerosol Cloud" --scope "Aerosol-cloud interaction literature" --search "aerosol cloud interaction"
```

List and lint topics:

```bash
python3 tools/rk.py topic list
python3 tools/rk.py topic lint
```

### Maintenance And Review

Show pending review notes:

```bash
python3 tools/rk.py review
```

Run lint checks:

```bash
python3 tools/rk.py lint
python3 tools/rk.py lint --mode structure-lint
python3 tools/rk.py lint --mode evidence-lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/rk.py lint --mode ars-handoff-lint
python3 tools/rk.py lint --mode public-safety-lint
python3 tools/rk.py lint --mode repair-plan
```

Run public repo safety scan:

```bash
python3 tools/public_safety_scan.py
```

Apply a maturity-aware low-risk rewrite with an AI Integration Note:

```bash
python3 tools/rk.py evolve knowledge/concepts/example.md --note "Add retrieval brief after reading queue review." --source "daily-agent"
python3 tools/rk.py evolve knowledge/claims/example.md --priority high --note "Potential stable claim conflict." --blocker "Needs locator or human review before promotion."
```

Find contradictions and challenge a page:

```bash
python3 tools/rk.py reconcile --topic-id aerosol-cloud
python3 tools/rk.py reconcile --dry-run
python3 tools/rk.py challenge knowledge/synthesis/example.md --limit 5
```

Find unnamed patterns and save a low-maturity synthesis draft:

```bash
python3 tools/rk.py emerge --limit 8
python3 tools/rk.py emerge --write --topic-id aerosol-cloud
python3 tools/rk.py synthesize auto --write --limit 8
```

Generate propagation preview/audit fallback:

```bash
python3 tools/rk.py propagate knowledge/synthesis/example.md
python3 tools/rk.py propagate knowledge/synthesis/example.md --write
python3 tools/rk.py propagate doi_10_1234_example --write
```

Print L0-L3 session bootstrap:

```bash
python3 tools/rk.py status
python3 tools/rk.py world --log-tail 10
```

Export graph and index:

```bash
python3 tools/rk.py graph
python3 tools/rk.py index
```

Read or append wiki log:

```bash
python3 tools/rk.py log --tail 20
python3 tools/rk.py log --action note --note "Short public-safe note."
```

Generate external sandbox context:

```bash
python3 tools/rk.py prompt external-sandbox
python3 tools/rk.py export external-sandbox
```

## Validation Commands

Before publishing or opening a PR, run:

```bash
python3 -B -m py_compile tools/rk.py rkf/cli.py rkf/core.py rkf/__init__.py tools/public_safety_scan.py
python3 -B -m unittest discover -s tests
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/rk.py lint --mode ars-handoff-lint
python3 tools/rk.py lint --mode public-safety-lint
python3 tools/public_safety_scan.py
```

## Current Cleanup Candidates

這些是目前工作目錄中看起來不需要提交，或只應該留在本機的檔案/目錄。本文件只列出
建議；沒有刪除任何檔案。

| Path | 狀態 | 建議 |
|---|---|---|
| `.DS_Store` | ignored local macOS metadata | 可刪除，不應提交 |
| `rkf/__pycache__/` | ignored Python cache | 可刪除，不應提交 |
| `tests/__pycache__/` | ignored Python cache | 可刪除，不應提交 |
