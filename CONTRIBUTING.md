# Contributing

Thanks for improving Research Wiki.

## Development Rules

- Treat `core/` as the source of truth for database rules and acceptance criteria.
- Treat `ResearchWikiCodex.command` and `tools/` as command/UI implementations of the core contract.
- Use `codex/core-*` branches for core changes, `codex/command-*` branches for command/UI changes, and `personal/*` branches for private research state.
- Keep the active workflow focused on papers, synthesis, meetings, project synthesis, seminars, DOI intake, maintenance, and Obsidian graph navigation.
- Do not add code wiki, inbox, Notion, sync, or sub-database workflows back into the active path.
- Do not batch-delete files. Generate repair plans and let humans review deletion candidates.
- Keep full text in `raw/full_text/` and paper notes in `wiki/literature/`.
- Put cross-paper reasoning in `wiki/synthesis/`.
- Put cross-meeting project evolution in `wiki/project_synthesis/`.

## Tests

Run before submitting changes:

```bash
python3 -m py_compile tools/research_wiki_shortcut.py tools/build_full_text_index.py tools/wiki_lint.py tools/wiki_doctor.py tools/generate_repair_plan.py
python3 tools/check_install.py --strict
python3 tools/wiki_lint.py
python3 tools/wiki_doctor.py
python3 tools/generate_repair_plan.py
python3 tools/test_codex_first_command.py
printf '0\n' | python3 tools/research_wiki_codex_shortcut.py
printf '2\n\n0\n' | python3 tools/research_wiki_codex_shortcut.py
printf '6\nissue title\n\n0\n' | python3 tools/research_wiki_codex_shortcut.py
```

## Documentation

- Keep `README.md` and `USER_GUIDE.md` English-first.
- Keep `README.zh-TW.md` and `USER_GUIDE.zh-TW.md` as concise Chinese confirmation docs.
- Update `AGENTS.md` whenever workflow rules change.

## Skills

Project-local skills live in `skills/`. If copied from another source, document the source and license in `skills/THIRD_PARTY_NOTICES.md`.
