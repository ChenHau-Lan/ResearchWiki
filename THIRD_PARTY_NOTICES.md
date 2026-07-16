# Third-Party Notices

RKF v1 keeps third-party integrations optional and off by default. The current
implementation defines local adapter contracts and deterministic gates; it
does not vendor source files, credentials, browser profiles, indexes, PDFs, or
article text from the projects below.

## Design references pinned for RKF v1

### paper-fetch

- Source: <https://github.com/drpwchen/paper-fetch>
- Pinned reference commit: `53d846115e81c6891977c33d2ee8a820afc3187a`
- License at that commit: MIT, Copyright (c) 2026 drpwchen
- RKF-adopted patterns: typed acquisition status, route history, SHA-256
  artifact identity, retryable versus unavailable distinction, official
  OA/TDM route ordering, holdings-aware diagnostics, and an external-command
  JSON boundary.
- Local implementation: `rkf.acquisition`, `rkf.providers.FullTextProvider`,
  `ExternalCommandFullTextProvider`, and `register_evidence_artifact`.
- vNext local extensions: multi-identifier resolution, atmospheric P0 policy
  profiles, OpenAlex fallback, artifact version/quality provenance,
  cross-project acquisition runs, cross-platform secret/browser protocols,
  and bounded private smoke tooling.
- Institution login, browser/session automation, CAPTCHA handling, and library
  endpoints were not copied into RKF core. They remain an optional
  machine-local `paper_fetch.py --json` adapter; RKF ships no credentials or
  institution-specific configuration.

### paper-review-and-digest

- Source: <https://github.com/drpwchen/paper-review-and-digest>
- Pinned reference commit: `287d42f51c426dca6a042204578e77cb6bd21346`
- License at that commit: MIT, Copyright (c) 2026 Po-Wei Chen (drpwchen.com)
- RKF-adopted patterns: separate digest/appraise intents, explicit reading
  scope, visible external-check failures, citation existence versus support,
  and deterministic inference-gap checks.
- Local implementation: `rkf.reading.run_read_pass`,
  `validate_citation_checks`, and `lint_inference_gaps`.
- Not adopted into generic v1 core: clinical personas, review-card websites,
  or one appraisal checklist applied to every research domain.

### vault-search

- Source: <https://github.com/drpwchen/vault-search>
- Pinned reference commit: `8bfcc6cfcabec11f9a1c2e083137c3280cd65cf5`
- License at that commit: MIT, Copyright (c) 2026 P.W. Chen (drpwchen.com)
- RKF-adopted patterns: optional structured retrieval-provider boundary,
  exact-first ordering, result lineage, and public/private index separation.
- Local implementation: `rkf.providers.RetrievalProvider` and the optional
  provider path in `rkf.retrieval.search_central_rkf`.
- Not adopted into v1 core: Obsidian plugin UI, always-on API service,
  required embedding runtime, or one index per connected project.

## Attribution and modification boundary

The pinned commits and their LICENSE files were checked on 2026-07-15. RKF's
adapter and validation code was implemented locally against the issue-defined
contracts; no upstream source file was copied into this repository. If a later
change copies or substantially adapts upstream code, preserve the applicable
MIT copyright and permission notice with that code and update this file and
the release notes.
