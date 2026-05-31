# RKF Health Agent Prompt

Goal: check whether RKF can be safely shared, continued, or published.

Use:

```bash
python3 -B -m unittest discover -s tests
python3 tools/rk.py lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/rk.py lint --mode ars-handoff-lint
python3 tools/rk.py lint --mode public-safety-lint
python3 tools/public_safety_scan.py
```

Report:

- Public-safety failures.
- Broken graph or topic links.
- AI-integrated stable content missing AI Integration Note or temporal metadata.
- Stale AI Integration Notes that still have blockers.

Rules:

- Do not delete files.
- Do not silently rewrite knowledge pages during a health check.
- Any repair should be explicit, public-safe, and scoped.
