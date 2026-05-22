#!/usr/bin/env python3
"""Check whether this machine can run Research Wiki.

This script is diagnostic only. It does not edit repository files.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "core/principles.md",
    "core/data_contract.md",
    "core/agent_contract.md",
    "core/test_contract.md",
    "raw/paper_sources.md",
    "AGENTS.md",
    "README.md",
    "USER_GUIDE.md",
    "ResearchWikiCodex.command",
    "ResearchWikiCodex.cmd",
    "InitializeResearchWiki.command",
    "InitializeResearchWiki.cmd",
    "tools/research_wiki_codex_shortcut.py",
    "tools/research_wiki_shortcut.py",
    "tools/check_full_text_tables.py",
    "tools/wiki_lint.py",
    "tools/wiki_doctor.py",
    "tools/generate_repair_plan.py",
]


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout.strip()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def print_line(level: str, message: str) -> None:
    print(f"{level}: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local Research Wiki install prerequisites.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if required checks fail.")
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    print("Research Wiki install check")
    print("===========================")
    print(f"Root: {ROOT}")
    print(f"Python: {sys.version.split()[0]}")

    code, output = run(["git", "rev-parse", "--is-inside-work-tree"]) if command_exists("git") else (1, "")
    if code == 0 and output == "true":
        print_line("PASS", "Git repository detected.")
    else:
        failures.append("Git repository was not detected.")
        print_line("FAIL", "Git repository was not detected.")

    print_line("PASS", f"Python interpreter running this script: {sys.executable}")

    for command in ["git", "rg"]:
        if command_exists(command):
            print_line("PASS", f"Required command found: {command}")
        else:
            failures.append(f"Required command missing: {command}")
            print_line("FAIL", f"Required command missing: {command}")

    for command in ["pdftotext", "gh"]:
        if command_exists(command):
            print_line("PASS", f"Optional command found: {command}")
        else:
            warnings.append(f"Optional command missing: {command}")
            print_line("WARN", f"Optional command missing: {command}")

    if command_exists("gh"):
        code, output = run(["gh", "auth", "status"])
        if code == 0:
            print_line("PASS", "GitHub CLI is authenticated.")
        else:
            warnings.append("GitHub CLI is not authenticated; issue support should use prefilled browser URLs.")
            print_line("WARN", "GitHub CLI is not authenticated; issue support should use prefilled browser URLs.")

    for rel_path in REQUIRED_FILES:
        path = ROOT / rel_path
        if path.exists():
            print_line("PASS", f"Required file exists: {rel_path}")
        else:
            failures.append(f"Required file missing: {rel_path}")
            print_line("FAIL", f"Required file missing: {rel_path}")

    code, output = run(["git", "ls-files", "raw/doi_pdf", "raw/full_text"])
    tracked_private = [
        line
        for line in output.splitlines()
        if line and not line.endswith("/.gitkeep")
    ]
    if tracked_private:
        failures.append("Raw DOI PDF/full_text evidence is tracked by Git.")
        print_line("FAIL", "Raw DOI PDF/full_text evidence is tracked by Git.")
        for item in tracked_private:
            print(f"  - {item}")
    else:
        print_line("PASS", "No raw DOI PDF/full_text evidence is tracked by Git.")

    print("")
    print("Summary")
    print("-------")
    print(f"Failures: {len(failures)}")
    print(f"Warnings: {len(warnings)}")

    if failures and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
