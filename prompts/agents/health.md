# RKF Health Agent Prompt

Goal: check whether RKF can be safely shared, continued, or published.

Use the Codex app RKF workflow to request:

- Full test discovery when code changed.
- RKF lint across structure, reading maturity, evidence boundary, graph, ARS handoff, and public safety.
- The standalone public-safety scan before sharing or publishing.

Report:

- Public-safety failures.
- Broken graph or topic links.
- AI-integrated stable content missing AI Integration Note or temporal metadata.
- Stale AI Integration Notes that still have blockers.

Rules:

- Do not delete files.
- Do not silently rewrite knowledge pages during a health check.
- Any repair should be explicit, public-safe, and scoped.
