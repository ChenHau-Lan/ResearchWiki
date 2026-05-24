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

Follow its evidence boundary, public-safe boundary, and save proposal format.

## Default Mode

You may help search for papers, read legally available PDFs or publisher
artifacts, organize source candidates, and add durable research knowledge to
RKF.

If you have write access to `<RKF_REPO_PATH>`, use RKF CLI directly:

```bash
cd <RKF_REPO_PATH>
python3 tools/rk.py capture doi "10.xxxx/xxxxx" --title "Paper title" --topic-id "topic-id"
python3 tools/rk.py acquire "source_id" --pdf "/private/path/to/paper.pdf" --approve
python3 tools/rk.py verify-pdf "source_id" --locator "p. 3 Fig. 2; p. 8 Section 4" --note "QC notes"
python3 tools/rk.py distill paper "source_id" --slug "author-year-short-title"
```

If you do not have write access, or the evidence is incomplete, do not edit the
wiki directly. Return a proposal instead.

## Evidence Rules

- Candidates are not evidence.
- ARS/deep-research reports are not evidence by themselves.
- Do not create a stable paper wiki page without a legal artifact, PDF/OCR/visual
  QC, and locator notes.
- Do not save PDFs, full article text, browser captures, private Drive paths,
  tokens, or local secrets.
- Temporary PDF text or OCR may be used for reading, but full text must not be
  committed to RKF.

## Proposal Fallback

Return a proposal when:

- topic fit is unclear
- there are only search results and no legal artifact
- PDF QC is missing
- locators are insufficient
- claim support is unclear
- you cannot write to the RKF repo

Proposal format:

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
