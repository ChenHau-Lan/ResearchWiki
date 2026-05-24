---
name: rkf-evidence-vault
description: Capture DOI/URL/topic/PDF leads, stage candidate discovery, manage legal evidence routes, track missing PDFs/full text, and verify paper-reading artifacts before paper wiki ingest. Use when the task mentions source intake, DOI, URL, PDF, article acquisition, evidence vault, PDF QC, OCR QC, legal access, candidate discovery, 文獻搜尋, 找文章, 下載PDF, 取得PDF, 缺PDF, 證據庫, 來源攝取, or PDF檢查.
---

# RKF Evidence Vault

Use this skill for the evidence side of RKF. It creates source records,
candidate backlogs, acquisition checkpoints, and reviewed reading artifacts. It
does not write paper wiki pages.

## Modes

| Mode | Use For | Output |
|---|---|---|
| `capture` | DOI, URL, PDF pointer, topic seed, idea, or question | `SourceRecord` |
| `discover` | Search plan, candidate list, or missing-PDF checkpoint | candidate backlog; candidates are not evidence |
| `acquire` | Stage or approve a legal evidence route | checkpoint or private evidence artifact |
| `verify-pdf` | Confirm artifact identity, legality, readability, and locators | QCed paper-reading artifact |

## Trigger Phrases

Use this skill when the user says things like:

- "Find papers about..."
- "Show which papers still need PDFs."
- "Capture this DOI/URL/PDF."
- "Can we legally get the PDF?"
- "Check whether this PDF or scan is usable evidence."
- "幫我找這個主題的文獻"
- "列出還缺 PDF 或全文的文獻"
- "把這個 DOI / URL / PDF 加到知識庫前先檢查"
- "下載或取得合法 PDF"
- "確認這份 PDF / 掃描檔能不能當 evidence"

## Rules

- Metadata and search candidates are not evidence.
- Missing-PDF papers remain candidates, review queue items, or topic backlog.
- Acquisition needs explicit checkpoint approval before private evidence is
  treated as reviewed input.
- For scanned or image-only PDFs, record visual locators, OCR confidence, and
  human reading notes; do not claim full-read text evidence when OCR is weak.
- Do not bypass paywalls, CAPTCHA, robots, or access restrictions.
- Do not create durable article-text Markdown. Temporary reading extraction may
  be used in memory only.
- Stop at review if source identity, legality, or readability is uncertain.
