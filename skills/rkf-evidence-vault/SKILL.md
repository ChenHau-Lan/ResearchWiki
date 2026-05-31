---
name: rkf-evidence-vault
description: Capture DOI/URL/topic/PDF leads, stage candidate discovery, track full-text availability, request user PDFs when needed, and verify paper-reading artifacts for claim readiness. Use when the task mentions source intake, DOI, URL, PDF, article acquisition, evidence vault, full text, missing PDF, PDF/OCR/visual check, legal access, candidate discovery, 文獻搜尋, 找文章, 下載PDF, 取得PDF, 缺PDF, 全文狀態, 證據庫, 來源攝取, or PDF檢查.
---

# RKF Evidence Vault

Use this skill for the source and reading-artifact side of RKF. It creates
source records, candidate backlogs, full-text route notes, user-PDF requests,
and verified reading artifacts. It does not decide cross-source synthesis.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `capture` | DOI, URL, PDF pointer, topic seed, idea, or question | `SourceRecord` with conservative reading fields |
| `discover` | Search plan, candidate list, missing full text, or paper backlog | candidate backlog and queue hints |
| `acquire` | Record user-provided full text/PDF or legacy route review | full-text status update, artifact pointer, or legacy route note |
| `verify-pdf` | Confirm artifact identity, legality, readability, and locators | checked paper-reading artifact and maturity upgrade |

## Trigger Phrases

Use this skill when the user says things like:

- "Find papers about..."
- "Show which papers still need PDFs."
- "Capture this DOI/URL/PDF."
- "Can we legally get the PDF?"
- "Mark this as full text unavailable."
- "Check whether this PDF or scan is usable for claims."
- "幫我找這個主題的文獻"
- "列出還缺 PDF 或全文的文獻"
- "把這個 DOI / URL / PDF 加到知識庫"
- "下載或取得合法 PDF"
- "確認這份 PDF / 掃描檔能不能支持 claims"

## Rules

- Metadata and search candidates can start paper drafts, but are not evidence
  for stable claims.
- Missing full text should set `fulltext_status: needs-user-pdf` and enter the
  active paper queue.
- Acquisition checkpoints are legacy compatibility, not the normal path.
- User-provided PDFs may update `fulltext_status` and reading maturity without a
  prior checkpoint.
- For scanned or image-only PDFs, record visual locators, OCR confidence, and
  human reading notes; do not claim full-read text evidence when OCR is weak.
- Do not bypass paywalls, CAPTCHA, robots, or access restrictions.
- Do not create durable article-text Markdown. Temporary reading extraction may
  be used to read and summarize, then discarded.
- Stop at review if source identity, legality, readability, or locator support
  is uncertain.
