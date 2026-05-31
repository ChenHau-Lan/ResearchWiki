# RKF Nightly Agent Prompt

Goal: let the wiki evolve safely from the day active reading signals.

Use:

```bash
python3 tools/rk.py emerge --write --limit 8
python3 tools/rk.py reconcile --limit 8
python3 tools/rk.py lint
```

Report:

- Low-maturity emergent patterns created or previewed.
- Contradictions marked with AI Integration Notes.
- Stale synthesis or unresolved blockers.

Rules:

- Do not create app automations from this prompt.
- Do not use open-web retrieval.
- Every direct update must be AI-marked and maturity-aware.
