# RKF Current Features And Commands

這份文件是目前 Research Knowledge Framework 的功能盤點與指令速查。它描述目前
repo 已有的能力、日常怎麼用、以及哪些檔案或目錄看起來只是本機狀態或清理候選。

## 核心功能

| 功能 | 用途 | 主要輸出 |
|---|---|---|
| Source capture | 攝取 DOI、URL、PDF pointer、topic seed、idea、question | `state/sources/*.json` |
| Discovery staging | 建立候選文獻搜尋 run；候選可啟動 draft，但不是 claim evidence | `state/search_runs/*/candidates.json`、`hot.md` |
| Paper reading draft | 從 metadata、abstract、partial full text 或 PDF 先建立 paper draft | `knowledge/papers/*.md` |
| Full-text status | 標記 `needs-user-pdf`、`user-pdf-provided`、`fulltext-read` 等狀態 | source frontmatter/JSON、paper frontmatter |
| Reading ledger | 記錄 public-safe reading event、問題、AI 回答、人為修正、trust 變化與 blocker | `state/reading/*.json` |
| User PDF handling | 只有讀不到全文時要求 user 提供 PDF；可直接更新 full-text state | `state/evidence/*.json` |
| Locator/readability check | 記錄 artifact identity、readability、locator notes，提升 claim readiness | `state/evidence/*.json`、paper maturity |
| Paper queue/nudge | 推播 metadata-only、缺 PDF、缺人為 feedback、重複被問、可進 synthesis review 的 paper | terminal report / automation digest |
| Non-paper save | 保存 question、concept、claim、synthesis、overview、meeting、seminar | `knowledge/*/*.md` |
| Hot-query layer | 追蹤近期 public-safe 研究問題與 paper-search demand | `hot.md` |
| Topic governance | 維護 topic id、scope、aliases、include/exclude、default search strings | `governance/topic_registry.json`、`knowledge/topics/*.md` |
| Workspace status | 快速重建目前 wiki 狀態、maturity 分布與近期 log | terminal report |
| Propagation review | 新 evidence、reading maturity 或 synthesis 後列出可能受影響頁面 | terminal report 或 `state/gates/propagation/*.md` |
| Graph export | 輸出 source/evidence/wiki/topic typed links | `graph/research_graph.json` |
| Index generation | 產生 LLM retrieval 入口，包含 maturity hints | `index.md` |
| External sandbox capsule | 產生外部 sandbox 使用的 RKF context | `prompts/external_sandbox_context.md` |
| Lint and safety scan | 檢查 structure、maturity、claim boundary、graph、ARS handoff、public safety | terminal report |

## Reading And Evidence Rules

- Search candidate 和 metadata 可以建立 paper draft，但不是 stable claim evidence。
- ARS output 本身不是 evidence；進 RKF 前只能是 proposal 或 review blocker。
- Paper draft 要明確記錄 `reading_state`、`fulltext_status`、`human_feedback_level`、
  `understanding_confidence`、`claim_readiness` 和 `reading_ledger`。
- 讀不到全文時，標記 `fulltext_status: needs-user-pdf`，並請 user 提供 PDF。
- Stable claim / trusted synthesis 需要 locator、人為 feedback、既有 wiki source，或明確
  review blocker。
- Durable full article text 不進 public knowledge layer。
- `save` 和 `synthesize` 預設不覆寫既有 knowledge object；要更新必須明確使用
  `--update`。
- Propagation review 只產生 proposal，不自動重寫穩定頁面。

## Common Commands

所有指令以下列形式執行：

```bash
python3 tools/rk.py <command>
```

### Source, Draft, And Reading

Capture DOI or URL:

```bash
python3 tools/rk.py capture doi "10.1234/example" --title "Example Paper" --topic-id "topic-id"
python3 tools/rk.py capture url "https://example.org/report.pdf" --title "Official Report"
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

Generate proposal-first propagation review:

```bash
python3 tools/rk.py propagate knowledge/synthesis/example.md
python3 tools/rk.py propagate knowledge/synthesis/example.md --write
python3 tools/rk.py propagate doi_10_1234_example --write
```

Print compact session bootstrap:

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
