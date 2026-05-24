# Summary

- What changed?
- Which RKF surface changed: core, CLI, skills, docs, tests, GitHub?

# Checks

- [ ] I preserved the PDF-to-Wiki evidence boundary.
- [ ] I did not add private PDFs, article text, local paths, or runtime state to Git.
- [ ] I updated docs when workflow behavior changed.
- [ ] I updated tests when gates, schemas, or CLI behavior changed.

# Tests

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/public_safety_scan.py
```

# Privacy Review

- [ ] No local home-directory paths.
- [ ] No `.DS_Store`.
- [ ] No private evidence artifacts.
- [ ] No copied article text.
