# RKF Morning Agent Prompt

Goal: prepare a public-safe research day bootstrap from RKF state.

Use:

```bash
python3 tools/rk.py world --log-tail 10
python3 tools/rk.py paper queue --limit 10
python3 tools/rk.py paper nudge --limit 5
```

Report:

- L0 critical facts and active blockers.
- L1 papers needing user PDF, reading feedback, or synthesis review.
- Hot-query demand that should shape today reading.
- One concise next action per paper.

Rules:

- Do not fetch open web or private files.
- Do not promote claims.
- If a user PDF is needed, ask for it explicitly.
