# RKF Weekly Agent Prompt

Goal: review topic drift, synthesis gaps, and reading maturity debt.

Use:

```bash
python3 tools/rk.py world --log-tail 20
python3 tools/rk.py topic lint
python3 tools/rk.py emerge --limit 12
python3 tools/rk.py reconcile --dry-run --limit 12
```

Report:

- Topics with stale synthesis or ambiguous scope.
- Papers ready for human synthesis review.
- Repeated hot queries without canonical pages.
- Candidate backlog cleanup suggestions, without treating candidates as evidence.

Rules:

- Keep output as recommendations unless the user asks for direct updates.
- Stable claim promotion still needs locator, human feedback, supported wiki source, or blocker.
