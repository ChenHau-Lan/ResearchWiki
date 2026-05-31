# RKF Current Features And Commands

這份文件是目前 Research Knowledge Framework 的功能盤點與指令速查。它描述目前
repo 已有的能力、日常怎麼用、哪些檔案或目錄看起來只是本機狀態或清理候選。

## 核心功能

| 功能 | 用途 | 主要輸出 |
|---|---|---|
| Source capture | 攝取 DOI、URL、PDF pointer、topic seed、idea、question | `state/sources/*.json` |
| Discovery staging | 建立候選文獻搜尋 run；候選不是 evidence | `state/search_runs/*/candidates.json`、`hot.md` |
| Acquisition checkpoint | 在 PDF 或 publisher artifact 被當成 evidence 前要求合法取得確認 | `state/gates/pdf_acquisition/*.md` |
| PDF QC | 記錄 artifact identity、QC status、locator notes | `state/evidence/*.json` |
| Paper distillation | 只從 QCed PDF evidence 建立 paper wiki page | `knowledge/papers/*.md` |
| Non-paper save | 保存 question、concept、claim、synthesis、overview、meeting、seminar | `knowledge/*/*.md` |
| Hot-query layer | 追蹤近期 public-safe 研究問題與 paper-search demand | `hot.md` |
| Topic governance | 維護 topic id、scope、aliases、include/exclude、default search strings | `governance/topic_registry.json`、`knowledge/topics/*.md` |
| Workspace status | 快速重建目前 wiki 狀態與近期 log | terminal report |
| Propagation review | 新 evidence 或 synthesis 後列出可能受影響頁面 | terminal report 或 `state/gates/propagation/*.md` |
| Graph export | 輸出 source/evidence/wiki/topic typed links | `graph/research_graph.json` |
| Index generation | 產生 LLM retrieval 入口 | `index.md` |
| External sandbox capsule | 產生外部 sandbox 使用的 RKF context | `prompts/external_sandbox_context.md` |
| Lint and safety scan | 檢查 structure、evidence、graph、ARS handoff、public safety | terminal report |

## Evidence Rules

- Search candidate 不是 evidence。
- ARS output 本身不是 evidence；進 RKF 前只能是 proposal 或 review blocker。
- Paper page 需要 reviewed source artifact，通常是 QCed PDF。
- Durable full article text 不進 public knowledge layer。
- Claim 需要 locator、既有 wiki source，或明確 review blocker。
- `save` 和 `synthesize` 預設不覆寫既有 knowledge object；要更新必須明確使用
  `--update`。
- Propagation review 只產生 proposal，不自動重寫穩定頁面。

## Common Commands

所有指令以下列形式執行：

```bash
python3 tools/rk.py <command>
```

### Source And Evidence

Capture DOI or URL:

```bash
python3 tools/rk.py capture doi "10.1234/example" --title "Example Paper" --topic-id "topic-id"
python3 tools/rk.py capture url "https://example.org/report.pdf" --title "Official Report"
```

Stage a discovery run:

```bash
python3 tools/rk.py discover "aerosol cloud interaction Taiwan" --topic-id "aerosol-cloud"
```

Create an acquisition checkpoint before treating a PDF as evidence:

```bash
python3 tools/rk.py acquire doi_10_1234_example --pdf "/path/to/paper.pdf"
```

Approve a legal PDF route and copy the artifact into the private evidence root:

```bash
python3 tools/rk.py acquire doi_10_1234_example --pdf "/path/to/paper.pdf" --approve
```

Verify a PDF with locator notes:

```bash
python3 tools/rk.py verify-pdf doi_10_1234_example --locator "pp. 3-5 methods" --note "identity checked"
```

Distill a verified PDF into a paper page:

```bash
python3 tools/rk.py distill paper doi_10_1234_example
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

Show pending gates:

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
| `tools/__pycache__/` | ignored Python cache | 可刪除，不應提交 |
| `rkf.workspace.toml` | ignored local workspace config | 保留本機，不提交 |
| `prompts/external_sandbox_context.md` | ignored generated runtime capsule | 可重新產生，不提交 |
| `raw` | ignored local symlink to shared/private raw data | 保留本機，不提交 |
| `wiki` | ignored local symlink to shared/private wiki data | 保留本機，不提交 |
| `output/` | empty local output directory | 可刪除或繼續忽略 |
| `skills/research-knowledge-framework/` | empty local directory | 可刪除或確認是否仍需保留 |
| `maintenance/test_fixtures/` | empty local directory | 可刪除或補 fixture 後再追蹤 |

目前沒有發現已追蹤且明顯應立即移除的檔案。若要清掉上表的 local cache 或空目錄，請先
確認刪除範圍，再用明確路徑逐項刪除。
