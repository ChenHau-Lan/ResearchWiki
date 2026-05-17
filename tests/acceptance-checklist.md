# Acceptance Checklist

Use this checklist after setup or major restructuring.

## Sample Ingest Scenarios

- Peer-reviewed paper:
  - Add a verified BibTeX entry to `references.bib`.
  - Create a paper page from `templates/paper.md`.
  - Link it from the most relevant topic README and `wiki/index.md`.
  - Append an `ingest-paper` entry to `wiki/log.md`.

- Code or plotting logic:
  - Create a code page from `templates/code.md`.
  - Record source path, commit/version when available, data flow, parameters, outputs and limitations.
  - Link it from `wiki/code_methods/README.md` and `wiki/index.md`.
  - Append an `ingest-code` entry to `wiki/log.md`.

- Talk photo, video, or daily idea:
  - Save raw material under `raw/` when available.
  - Create an inbox note from `templates/inbox.md`.
  - Mark confidence and next step.
  - Do not state the idea as verified knowledge until promoted.

## Structural Checks

- `wiki/index.md` is the entry point.
- `wiki/log.md` has a chronological append-only entry.
- Each `wiki/**/*.md` file has YAML frontmatter.
- Formal paper pages use citation keys that exist in `references.bib`.
- Inbox material remains distinguishable from reviewed knowledge.

## Command

```bash
python3 tools/wiki_lint.py
```

