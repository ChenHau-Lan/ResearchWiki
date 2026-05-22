# Support

Research Wiki uses privacy-safe issue reporting.

## Prepare A Support Issue

Run:

```bash
python3 tools/support_report.py --issue-url
```

The script writes `maintenance/support_report.md` and prints a prefilled GitHub
issue URL. It does not submit the issue.

## Privacy Rules

Before submitting an issue, check that it does not include:

- private PDFs
- full article text
- local home-directory paths
- Codex logs
- sensitive DOI lists or personal research state

The report redacts common private data automatically, but human review is still
required.

## Labels

Use these labels when relevant:

- `new-user-test`
- `install`
- `core-contract`
- `command-ui`
- `privacy`
- `needs-triage`
