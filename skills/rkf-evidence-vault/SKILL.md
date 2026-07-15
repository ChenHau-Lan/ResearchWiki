---
name: rkf-evidence-vault
description: Route paper leads and reading evidence through RKF v1 Add and Read. Use for adding a DOI, URL, PDF pointer, note, or selected paper as a candidate, and for recording exact-locator Evidence with explicit verification state. Candidate metadata never becomes Evidence automatically.
---

# RKF Evidence Vault

Use this skill for the source-to-Evidence portion of the RKF v1 path. Add can
start from a DOI, URL, PDF pointer, note, or selected paper. Read records what
was actually inspected at an exact source location.

## Workflow Routing

| User intent | Structured action | Result |
|---|---|---|
| Add a source lead or note | `workflow.add` | deduplicated candidate receipt with `Promotion: none` |
| Record a source finding | `workflow.read` | Evidence card with paper ID, locator, stance, and verification |
| Correct an Evidence card | `workflow.read` | explicit correction with preserved lineage |
| Mark human verification | `workflow.read` | verification transition tied to the inspected locator |

## Trigger Phrases

- "Add this DOI as a candidate; do not promote it."
- "Add this URL or PDF pointer to RKF."
- "Read this paper and record p. 8, Fig. 3 as supporting Evidence."
- "Correct the locator on this Evidence card."
- "Mark this Evidence human-verified after I confirm it."
- "把這個 DOI 收進 RKF，先保持 candidate。"
- "記錄 section 2、Table 1 的 opposing Evidence。"
- "這筆 Evidence 我已人工核對。"

## Add Rules

- Candidate metadata, abstracts, provider receipts, and model output are not
  stable Evidence.
- Keep `Promotion: none` unless a later Read action records locator-backed
  Evidence.
- Do not bypass paywalls, CAPTCHA, robots, or access restrictions.
- Do not store PDFs, full article text, credentials, or private paths in public
  RKF state.

## Read Rules

- Evidence requires a page, section, figure, table, or paragraph locator.
- Record stance and verification separately; source access does not imply human
  verification.
- Scanned or image-only material needs a visual locator and an honest
  readability/OCR limitation.
- If identity, legality, readability, or locator support is uncertain, stop with
  a Review finding instead of upgrading trust.
- Optional source and full-text providers are internal adapters. Provider
  success never changes Evidence or Claim trust by itself.
