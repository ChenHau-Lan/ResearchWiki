# RKF External Sandbox Bootstrap

Enable Research Knowledge Framework (RKF) mode in this sandbox.

## Workspace

Primary RKF repo:

```text
<RKF_REPO_PATH>
```

First read:

```text
<RKF_REPO_PATH>/prompts/external_sandbox_context.md
```

Follow its reading maturity boundary, public-safe boundary, and save proposal
format.

## Default Mode

You may help search for papers, read legally available PDFs or publisher
artifacts, organize source candidates, create paper reading drafts, and add
durable research knowledge to RKF.

If you have write access to `<RKF_REPO_PATH>`, use RKF CLI directly:

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

For hot-query tracking, use the CLI command above or return a short hot-query
proposal. Do not create separate hot-query files or a sandbox inbox.

If you do not have write access, or the claim boundary is incomplete, do not
edit stable wiki knowledge directly. Return a proposal instead.

Low-risk direct updates may use `evolve` only when the page will show an AI
Integration Note and conservative maturity. `reconcile` may write blockers for
contradictions; `challenge` is critique only; `emerge` creates low-maturity
synthesis drafts from existing RKF state.

## Reading And Evidence Rules

- Candidates and metadata can create paper drafts, but are not stable claim
  evidence by themselves.
- ARS/deep-research reports are proposals, not evidence by themselves.
- A paper draft must state reading state, full-text status, human feedback
  level, claim readiness, and a reading ledger reference.
- When full text is unavailable, mark `fulltext_status: needs-user-pdf` and ask
  the user for the PDF.
- Do not promote stable claims or trusted synthesis without a locator, human
  feedback, existing governed source, or explicit review blocker.
- Do not save PDFs, full article text, browser captures, private Drive paths,
  tokens, or local secrets.
- Do not put raw chat transcripts, private paths, PDFs, browser captures, or
  full article text into `hot.md` or hot-query events.
- Temporary PDF text or OCR may be used for reading, but full text must not be
  committed to RKF.

## Proposal Fallback

Return a proposal when:

- topic fit is unclear
- there are only search results and no source record yet
- full text is unavailable and the user needs to provide a PDF
- reading maturity is too low for a stable claim
- locators are insufficient
- claim support is unclear
- you cannot write to the RKF repo

Proposal format:

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
