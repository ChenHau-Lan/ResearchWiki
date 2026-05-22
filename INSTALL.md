# Install Research Wiki

This guide assumes you are new to GitHub.

## Ask Codex To Help

Open Codex in the folder where you want the project and paste:

```text
Please help me install and start Research Wiki. I do not know GitHub well.
If I do not have the repository yet, help me clone git@github.com:ChenHau-Lan/wiki_research.git. If I am already inside the repo, use the current folder.
Read README.md, USER_GUIDE.md, INSTALL.md, and AGENTS.md first.
Check whether Git, Python 3, ripgrep/rg, Poppler/pdftotext, and the Codex CLI are available.
If a tool is missing, explain what it is for. Ask me before using Homebrew, system installation commands, or permission-requiring steps.
After installing or confirming tools, run python3 tools/check_install.py --strict.
When it succeeds, tell me how to open ResearchWikiCodex.command. Do not upload private PDFs, full text, local paths, sensitive DOI lists, or Codex logs.
```

This prompt can complete most of the install flow, but it should still ask before installing system tools or submitting any GitHub issue.

## Manual Steps

1. Install Git, Python 3, and Codex.
2. Clone the private repository:

   ```bash
   git clone git@github.com:ChenHau-Lan/wiki_research.git
   cd wiki_research
   ```

3. Run:

   ```bash
   python3 tools/check_install.py --strict
   ```

4. Open `ResearchWikiCodex.command` on macOS, or `ResearchWikiCodex.cmd` on Windows.
5. Optionally open `InitializeResearchWiki.command` or `InitializeResearchWiki.cmd` to set initial topics.

## Tools

- Required: Codex, Git, Python 3, ripgrep (`rg`).
- Recommended: Poppler / `pdftotext`, Obsidian, Chrome.

For where data lives and how papers enter the wiki, read [USER_GUIDE.md](USER_GUIDE.md). The README intentionally stays short.

## If Install Fails

You can ask Codex to prepare the issue draft:

```text
Research Wiki install or execution failed. Please help me prepare a GitHub issue draft.
Read SUPPORT.md, then run python3 tools/support_report.py --issue-url.
Check maintenance/support_report.md and the generated issue URL for local paths, private PDFs, full text, sensitive DOI lists, Codex logs, and personal research state.
Do not submit the issue automatically. Give me the draft for review.
```

Manual command:

```bash
python3 tools/support_report.py --issue-url
```

Review the prefilled GitHub issue before submitting it.
