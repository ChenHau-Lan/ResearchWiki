# RKF Morning Agent Prompt

Goal: prepare a public-safe research day bootstrap from RKF state.

Use the Codex app RKF workflow to request:

- `world` context with recent log tail.
- `paper queue` for papers needing user PDF, feedback, locators, or synthesis review.
- `paper nudge` for the highest-priority active reading reminders.

Report:

- L0 critical facts and active blockers.
- L1 papers needing user PDF, reading feedback, or synthesis review.
- Hot-query demand that should shape today reading.
- One concise next action per paper.

Rules:

- Do not fetch open web or private files.
- Do not promote claims.
- If a user PDF is needed, ask for it explicitly.
