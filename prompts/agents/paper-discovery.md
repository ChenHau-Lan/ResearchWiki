# RKF Scheduled Paper Discovery

Use this prompt only inside an explicitly approved Codex automation. The
automation must name its approved topic IDs, providers, cadence, maximum
candidates per run, and intake policy.

1. Activate RKF and stop if the session is OFF or the connection doctor blocks
   canonical writes.
2. Resolve each approved topic from `governance/topic_registry.json`. Use its
   public-safe `default_search_strings`; never infer a private project path or
   unpublished manuscript text as a query.
3. Run `discover.preview` with the approved providers. Crossref and arXiv are
   the default; OpenAlex is optional only when its machine-local key is already
   available. Keep at least three seconds between repeated arXiv calls.
4. Record only the exact returned preview hash through `discover.record`.
5. Default policy is `candidate-harvest`: do not accept candidates.
6. If and only if the automation was explicitly approved for
   `metadata-capture`, accept no more than the approved per-run limit, require
   `dedupe_status: new` plus a DOI or public landing URL, use
   `actor: automation`, and keep `create_paper_drafts: false`. The approved
   limit must never exceed the action's built-in cap of 20 candidates per run.
7. Never fetch or store abstracts, PDFs, OCR, article text, private paper-radar
   state, paywalled content, secrets, or local paths.
8. Never promote a claim or synthesis. Report `Promotion: none` and aggregate
   counts only; candidate identity stays in governed discovery state.
9. On provider failure, keep a redacted partial receipt. Do not retry in a
   tight loop, delete prior runs, or treat the remaining providers as stronger
   evidence.
