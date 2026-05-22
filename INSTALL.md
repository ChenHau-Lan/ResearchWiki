# Install Research Wiki

This guide assumes you are new to GitHub.

## Ask Codex To Help

Open Codex in the folder where you want the project and paste:

```text
Please help me install Research Wiki from this GitHub repository. I do not know GitHub well. Clone or open the repo, read core/README.md, README.md, USER_GUIDE.md, and AGENTS.md, then run python3 tools/check_install.py. Explain any missing tools and do not publish private files.
```

## Manual Steps

1. Install Git, Python 3, and Codex.
2. Clone the private repository:

   ```bash
   git clone git@github.com:ChenHau-Lan/wiki_research.git
   cd wiki_research
   ```

3. Run:

   ```bash
   python3 tools/check_install.py
   ```

4. Open `ResearchWiki.command`.

## Optional Tools

- `rg` / ripgrep: faster search.
- `pdftotext`: better PDF extraction.
- Obsidian: graph browsing.
- Chrome: authorized publisher pages.

## If Install Fails

Run:

```bash
python3 tools/support_report.py --issue-url
```

Review the prefilled GitHub issue before submitting it.
