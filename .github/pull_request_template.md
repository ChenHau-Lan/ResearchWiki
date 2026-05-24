# Summary

- What changed?
- Which layer changed: core, command, personal, docs, GitHub/support?

# Upload Inventory

- Intentionally uploaded:
- Intentionally not uploaded:
- Generated PDFs refreshed or unchanged:
- README/USER_GUIDE links changed or unchanged:

# Checks

- [ ] I read `core/principles.md` and `core/data_contract.md`.
- [ ] I did not add private raw PDFs or full text to Git.
- [ ] I did not move personal research state into the template branch.
- [ ] I updated docs when workflow behavior changed.
- [ ] I updated `VERSION_LOG.md` / `VERSION_LOG.zh-TW.md` when the change is release-visible.
- [ ] I checked generated PDF outputs when user-facing long-form docs changed.
- [ ] I recorded intentional non-uploaded artifacts, generated files, or private data exclusions in the PR body.

# Tests

```bash
python3 -m py_compile tools/*.py
python3 tools/check_install.py --strict
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
python3 tools/test_research_wiki_workflow.py
```

# Privacy Review

- [ ] No local home-directory paths.
- [ ] No `.DS_Store`.
- [ ] No private Codex logs.
- [ ] No publisher PDF/full-text evidence committed by accident.
