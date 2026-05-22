#!/usr/bin/env python3
"""Create a redacted Research Wiki support report and optional issue URL.

This script writes a local report but never submits a GitHub issue.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "maintenance" / "support_report.md"
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


def run(args: list[str], *, timeout: int = 120) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout
    except Exception as exc:
        return 999, f"{type(exc).__name__}: {exc}"


def sanitize(text: str) -> str:
    home = str(Path.home())
    clean = text.replace(str(ROOT), "<repo>")
    clean = clean.replace(home, "<home>")
    clean = DOI_RE.sub("<doi-redacted>", clean)
    clean = re.sub(r"raw/doi_pdf/[^\s|)]+", "raw/doi_pdf/<redacted>", clean)
    clean = re.sub(r"raw/full_text/[^\s|)]+", "raw/full_text/<redacted>", clean)
    clean = re.sub(r"maintenance/codex[^\s|)]*", "maintenance/<codex-log-redacted>", clean)
    clean = re.sub(r"account [A-Za-z0-9_.-]+", "account <github-account>", clean)
    clean = re.sub(r"-u [A-Za-z0-9_.-]+", "-u <github-account>", clean)
    return clean


def origin_repo() -> str:
    code, output = run(["git", "remote", "get-url", "origin"])
    if code != 0:
        return os.environ.get("RESEARCHWIKI_GITHUB_REPO", "")
    value = output.strip()
    match = re.search(r"github\.com[:/]([^/\s]+/[^/\s.]+)(?:\.git)?$", value)
    if match:
        return match.group(1)
    return os.environ.get("RESEARCHWIKI_GITHUB_REPO", "")


def section(title: str, command: list[str], *, max_chars: int = 6000) -> list[str]:
    code, output = run(command)
    return [
        f"## {title}",
        "",
        f"Command: `{' '.join(command)}`",
        f"Exit code: `{code}`",
        "",
        "```text",
        sanitize(output.strip() or "(no output)")[-max_chars:],
        "```",
        "",
    ]


def git_status_summary() -> list[str]:
    code, output = run(["git", "status", "--short"])
    counts: dict[str, int] = {}
    for line in sanitize(output).splitlines():
        key = line[:2].strip() or "changed"
        counts[key] = counts.get(key, 0) + 1
    body = ["Counts:"]
    for key in sorted(counts):
        body.append(f"- {key}: {counts[key]}")
    if counts:
        body.extend(
            [
                "",
                "File names are intentionally omitted from the support report.",
                "Attach specific paths only after reviewing them for private research context.",
            ]
        )
    return [
        "## Git Status Summary",
        "",
        "Command: `git status --short`",
        f"Exit code: `{code}`",
        "",
        "```text",
        "\n".join(body) if body else "(no output)",
        "```",
        "",
    ]


def issue_url(report_text: str, *, title: str) -> str:
    repo = origin_repo()
    if not repo:
        return ""
    issue_report = report_text.split("## Git Status Summary", 1)[0].strip()
    body = "\n".join(
        [
            "This issue was prepared by `python3 tools/support_report.py`.",
            "",
            "Please review the redacted report before submitting.",
            "Full local report path: `maintenance/support_report.md`.",
            "",
            issue_report[-5000:],
        ]
    )
    query = urllib.parse.urlencode(
        {
            "title": title,
            "body": body,
            "labels": "needs-triage,new-user-test",
        }
    )
    return f"https://github.com/{repo}/issues/new?{query}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a redacted Research Wiki support report.")
    parser.add_argument("--issue-url", action="store_true", help="Print a prefilled GitHub issue URL.")
    parser.add_argument("--open", action="store_true", help="Open the prefilled GitHub issue URL in a browser.")
    parser.add_argument("--title", default="[install] Research Wiki support report", help="Issue title.")
    args = parser.parse_args()

    now = datetime.now().isoformat(timespec="seconds")
    lines: list[str] = [
        "# Research Wiki Support Report",
        "",
        f"- Generated: {now}",
        f"- Python: {sys.version.split()[0]}",
        "- Privacy: local paths, DOI values, raw PDF paths, full text paths, and Codex logs are redacted.",
        "",
    ]
    lines.extend(section("Install Check", ["python3", "tools/check_install.py"]))
    lines.extend(section("Wiki Lint", ["python3", "tools/wiki_lint.py"]))
    lines.extend(section("Wiki Doctor", ["python3", "tools/wiki_doctor.py"]))
    lines.extend(section("Git Branch", ["git", "branch", "--show-current"]))
    lines.extend(git_status_summary())
    lines.extend(section("GitHub CLI Auth", ["gh", "auth", "status"]))

    report_text = sanitize("\n".join(lines).rstrip() + "\n")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report_text, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")

    if args.issue_url or args.open:
        url = issue_url(report_text, title=args.title)
        if not url:
            print("Could not infer GitHub repo. Set RESEARCHWIKI_GITHUB_REPO=owner/repo and retry.")
            return 1
        print("")
        print("Prefilled issue URL:")
        print(url)
        if args.open:
            webbrowser.open(url)
            print("Opened prefilled issue URL. Review before submitting.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
