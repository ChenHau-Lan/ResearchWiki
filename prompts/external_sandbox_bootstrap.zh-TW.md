# RKF External Sandbox Bootstrap

請在這個 sandbox 中啟用 Research Knowledge Framework (RKF) 工作模式。

## Workspace

主要 RKF repo:

```text
<RKF_REPO_PATH>
```

請先讀取：

```text
<RKF_REPO_PATH>/prompts/external_sandbox_context.md
```

並遵守其中的 reading maturity boundary、public-safe boundary、save proposal
格式。

## Default Mode

你可以協助搜尋文章、閱讀合法取得的 PDF 或 publisher artifact、整理候選來源、
建立 paper reading draft，並把值得保存的研究知識加入 RKF。

若你有 `<RKF_REPO_PATH>` 的寫入權限，可以直接使用 RKF CLI 操作：

```bash
cd <RKF_REPO_PATH>
python3 tools/rk.py capture doi "10.xxxx/xxxxx" --title "Paper title" --topic-id "topic-id"
python3 tools/rk.py distill paper "source_id" --slug "author-year-short-title"
python3 tools/rk.py acquire "source_id" --pdf "/private/path/to/paper.pdf"
python3 tools/rk.py verify-pdf "source_id" --locator "p. 3 Fig. 2; p. 8 Section 4" --note "Locator/readability notes"
python3 tools/rk.py paper feedback "source_id" --level discussed --note "User question, correction, or reading note"
python3 tools/rk.py paper queue
python3 tools/rk.py world --log-tail 10
python3 tools/rk.py emerge --limit 8
python3 tools/rk.py reconcile --dry-run --limit 8
python3 tools/rk.py hot record "short paper-search question" --topic-id "topic-id" --origin external-sandbox --intent paper-search
```

若要記錄熱門研究問題，使用上面的 CLI，或回傳短的 hot-query proposal。不要建立
hot-query 分檔，也不要設置 sandbox inbox。

如果沒有寫入權限，或 claim boundary 不完整，請不要直接改 stable wiki
knowledge。改輸出 proposal。

低風險 direct update 可以使用 `evolve`，但頁面必須留下 AI Integration Note 並保持
保守 maturity。`reconcile` 可以替矛盾寫 blocker；`challenge` 只產生 critique；
`emerge` 只從既有 RKF state 建立 low-maturity synthesis draft。

## Reading And Evidence Rules

- Candidates 和 metadata 可以建立 paper draft，但不能單獨作為 stable claim
  evidence。
- ARS/deep-research report 是 proposal，不是 evidence 本身。
- Paper draft 必須記錄 reading state、full-text status、human feedback
  level、claim readiness，以及 reading ledger reference。
- 讀不到 full text 時，標記 `fulltext_status: needs-user-pdf`，並請 user 提供
  PDF。
- 沒有 locator、human feedback、既有 governed source，或明確 blocker，就不要
  推升 stable claim 或 trusted synthesis。
- 不要保存 PDF、全文、browser capture、私人 Drive path、token、local secret。
- 不要把 raw chat transcript、私人路徑、PDF、browser capture 或全文放進
  `hot.md` 或 hot-query events。
- 暫時讀取 PDF text/OCR 可以用來理解文章，但不要把完整文本寫入 RKF。

## Proposal Fallback

遇到以下情況請只產生 proposal：

- topic fit 不確定
- 只有搜尋結果，還沒有 source record
- full text 讀不到，需要 user 提供 PDF
- reading maturity 不足以支撐 stable claim
- locator 不足
- claim 支撐不明確
- 你無法寫入 RKF repo

Proposal 格式：

```yaml
target_layer: paper | question | concept | claim | synthesis | topic | review
title: short title
doi_or_url: DOI or URL if available
topic_fit: existing topic id or new topic proposal
reading_state: metadata-only | abstract-read | partial-fulltext | fulltext-read | human-reviewed | blocked
fulltext_status: unknown | needs-user-pdf | user-pdf-provided | publisher-html | publisher-pdf | open-access-pdf | partial-only | fulltext-read | unavailable | blocked
human_feedback_level: none | skimmed | discussed | annotated | trusted
evidence_boundary: metadata-only | locator available | existing RKF page | human-reviewed | review blocker
confidence: low | medium | high | mixed
recommended_rkf_mode: capture | acquire | verify-pdf | distill | paper-feedback | save | review | synthesize | evolve | reconcile | challenge | emerge
reason_to_save: one sentence
hot_query: optional short public-safe question to record in hot.md
notes: short notes only; no full article text
```

## Validation

After RKF writes, run:

```bash
cd <RKF_REPO_PATH>
python3 -B -m py_compile tools/rk.py rkf/cli.py rkf/core.py rkf/__init__.py tools/public_safety_scan.py
python3 -B -m unittest discover -s tests
python3 tools/rk.py lint
python3 tools/public_safety_scan.py
```
