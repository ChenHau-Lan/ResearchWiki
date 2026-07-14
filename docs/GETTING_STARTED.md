# Getting Started with RKF v1

## 1. Bootstrap the central checkout

```bash
python3 tools/bootstrap_rkf.py preview
python3 tools/bootstrap_rkf.py apply
python3 tools/check_install.py
```

Keep PDFs, article text, secrets and private storage paths outside committed
knowledge.

## 2. Connect a research project

Preview, then explicitly apply `connect-project`. It creates a v2
`.rkf-connect.toml` with a stable random `project_id` and a small `RKF/` bridge.
It does not copy the wiki or semantic index.

## 3. Activate each task

Every Codex task starts OFF. Say “activate RKF”, then validate the connection.
The task receives a unique `activation_id`; actions are path-redacted and
idempotent. Say “deactivate RKF” when finished.

## 4. Complete the first paper loop

- Add a DOI/URL/PDF pointer or note.
- Ask a source-bounded question.
- Read and record Evidence with an exact locator.
- Compare & Synthesize a Claim; human verification is required for `verified`.
- Review missing locators, pending verification, contradictions and next steps.

Optional providers can acquire full text, appraise a paper or add semantic
retrieval, but none is required and none may promote trust automatically.

See `MODE_REGISTRY.md` and `docs/V1_SCOPE_INVENTORY.md` for the exact scope.
