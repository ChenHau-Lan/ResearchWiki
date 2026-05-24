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

並遵守其中的 evidence boundary、public-safe boundary、save proposal 格式。

## Default Mode

你可以協助搜尋文章、閱讀合法取得的 PDF 或 publisher artifact、整理候選來源，並把值得保存的研究知識加入 RKF。

若你有 `<RKF_REPO_PATH>` 的寫入權限，可以直接使用 RKF CLI 操作：

```bash
cd <RKF_REPO_PATH>
python3 tools/rk.py capture doi "10.xxxx/xxxxx" --title "Paper title" --topic-id "topic-id"
python3 tools/rk.py acquire "source_id" --pdf "/private/path/to/paper.pdf" --approve
python3 tools/rk.py verify-pdf "source_id" --locator "p. 3 Fig. 2; p. 8 Section 4" --note "QC notes"
python3 tools/rk.py distill paper "source_id" --slug "author-year-short-title"
```

如果沒有寫入權限，或證據不完整，請不要直接改 wiki。改輸出 proposal。

## Evidence Rules

- Candidates are not evidence.
- ARS/deep-research reports are not evidence by themselves.
- 沒有合法 artifact、PDF/OCR/visual QC、locator notes，就不要生成正式 paper wiki page。
- 不要保存 PDF、全文、browser capture、私人 Drive path、token、local secret。
- 暫時讀取 PDF text/OCR 可以用來理解文章，但不要把完整文本寫入 RKF。

## Proposal Fallback

遇到以下情況請只產生 proposal：

- topic fit 不確定
- 只有搜尋結果，還沒有合法 artifact
- PDF 尚未 QC
- locator 不足
- claim 支撐不明確
- 你無法寫入 RKF repo

Proposal 格式：

```yaml
target_layer: paper | question | concept | claim | synthesis | topic | review
title: short title
doi_or_url: DOI or URL if available
topic_fit: existing topic id or new topic proposal
evidence_boundary: candidate only | PDF acquired | PDF QC needed | locator available | existing RKF page | review blocker
confidence: low | medium | high | mixed
recommended_rkf_mode: capture | acquire | verify-pdf | distill | save | review | synthesize
reason_to_save: one sentence
notes: short notes only; no full article text
```

## Validation

After RKF writes, run:

```bash
cd <RKF_REPO_PATH>
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/rk.py lint
python3 tools/public_safety_scan.py
```
