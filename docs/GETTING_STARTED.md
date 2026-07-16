# Getting Started with RKF v1

> Status: Current
> Applies to: RKF v1.2 target (unreleased; latest tag v1.1.0)
> Last verified: 2026-07-15

## 1. Choose an installation profile

### Local core

```bash
python3 tools/bootstrap_rkf.py
python3 tools/bootstrap_rkf.py --apply
python3 tools/check_install.py --profile core --strict --json
```

This initializes the local workspace only. Success reports `"profile": "core"`
and `"ready": true`; a missing Codex connector remains an optional warning.

### Codex integration

Preview and apply the same connector request, then validate the Codex-specific
profile and resolve the installed connector:

```bash
python3 tools/bootstrap_rkf.py --install-connector
python3 tools/bootstrap_rkf.py --apply --install-connector
python3 tools/check_install.py --profile codex --strict --json
python3 tools/rkf_auto_connect.py resolve
```

In this profile, a missing or stale connector/skill fails the strict check.
Keep PDFs, article text, secrets and private storage paths outside committed
knowledge in either profile.

## 2. Connect a research project

Preview, then explicitly apply `connect-project`:

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

It creates a v2 `.rkf-connect.toml` with a stable random `project_id` and a
small `RKF/` bridge. It does not copy the wiki or a private index.

## 3. Activate each task

Every Codex task starts OFF. Say “activate RKF”, then validate the connection.
The task receives a unique `activation_id`; actions are path-redacted and
idempotent. Say “deactivate RKF” when finished.

You can say: “From this conversation, extract the research question and search
terms. Ask RKF first, then show candidate papers from public sources. After I
confirm them, Add their DOI/URL and a short note; do not save the whole
conversation. Promotion: none.”

To inspect state, say: “Show RKF status and list projects with open activation
records.” The response separates this task from the cross-task summary and
includes `active_project_count`, `open_activation_count`, project names, and
`project_id` values without absolute paths. An interrupted task can remain open
until a later closure or expiry event is recorded.

## 4. Run the isolated first loop

```bash
python3 tools/demo_quickstart.py --check
```

The command uses two temporary synthetic papers and no network, global
connector, PDF, or user data. It exercises activation, the five workflows,
deactivation, and the rule that only exact-locator Evidence can support formal
claims.

## 5. Use the five workflows with real sources

- Add a DOI/URL/PDF pointer or note.
- Ask a source-bounded question; context without a locator remains explicitly
  not claim-ready.
- Read and capture a FindingDraft without interrupting for a locator; add an
  exact locator before promoting it to Evidence. Direct exact-locator Evidence
  capture remains available.
- Compare & Synthesize a Claim; human verification is required for `verified`.
- Review missing locators, pending verification, contradictions and next steps.

See `MODE_REGISTRY.md` and `docs/V1_SCOPE_INVENTORY.md` for the exact scope.
