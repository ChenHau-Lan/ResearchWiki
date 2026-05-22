# Research Wiki Principles

## Purpose

Research Wiki is a DOI-first academic research database. It preserves evidence,
turns that evidence into concise research notes, and supports synthesis without
fabricating citations or mixing evidence tiers.

## Evidence Chain

- `raw/` is evidence. It stores DOI input, dashboards, PDFs, full text, indexes,
  and user-provided source files.
- `wiki/` is knowledge. It stores curated paper notes, synthesis, meetings,
  project synthesis, and seminars.
- `maintenance/` is operations. It stores repair plans, logs, release checks,
  support reports, and test reports.
- Dashboard rows are not evidence. Real evidence is the presence of files in
  `raw/doi_pdf/`, `raw/full_text/`, `raw/files/`, `raw/full_text_index.*`, and
  curated pages in `wiki/`.

## Token Discipline

- Use local tools for mechanical work: scanning, path checks, indexes, status
  refreshes, and diagnostics.
- Use Codex or another LLM for interpretation: full-text QC, paper-note writing,
  synthesis, project discussion, and source-access judgment.
- A command or UI should not spend LLM time on tasks that deterministic local
  tooling can do safely.

## Safety

- Do not automate unauthorized full-text acquisition.
- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Do not copy full articles into `wiki/`.
- Repair tools diagnose and plan; they do not delete files automatically.
- Release tooling must not publish private PDFs, full text, local paths, logs,
  or personal research state unless explicitly intended.

## Separation

- Core rules belong in `core/`.
- Command/UI behavior belongs in command scripts and user docs.
- Personal research state belongs on `personal/*` branches or ignored raw data.
- When a rule and a command behavior conflict, the core contract wins.
