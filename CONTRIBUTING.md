# Contributing

Thanks for improving Research Knowledge Framework.

## Development Rules

- Treat `docs/ARCHITECTURE.md`, `MODE_REGISTRY.md`, `schemas/`, and `rkf/` as
  the active framework contract.
- Use `tools/rk.py` for deterministic local operations.
- Keep evidence artifacts out of Git. Do not commit PDFs, article text, browser
  captures, private Drive paths, or local workspace config.
- Prefer small changes with a clear mode or object boundary.
- Do not batch-delete files. Generate a cleanup plan and let a human approve
  exact paths.

## Tests

Run before submitting changes:

```bash
python3 -m py_compile tools/rk.py rkf/*.py
python3 -m unittest discover -s tests
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/public_safety_scan.py
```

## Documentation

- README is the stable project front door.
- Architecture docs explain layers, objects, and gates.
- Mode Registry explains read/write permissions and failure stops.
- AGENTS.md gives coding agents the active boundaries.
- Keep Chinese and English README files aligned at the capability level.
