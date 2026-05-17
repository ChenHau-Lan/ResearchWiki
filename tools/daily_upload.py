#!/usr/bin/env python3
"""Commit and push safe knowledge-base updates.

This script is intended for scheduled daily uploads. It refuses to stage files
larger than MAX_UPLOAD_FILE_MB, so accidental large artifacts do not get pushed.
The raw/ tree is also ignored by .gitignore by default.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_MB = int(os.environ.get("MAX_UPLOAD_FILE_MB", "25"))
MAX_BYTES = MAX_MB * 1024 * 1024


def run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def candidate_files() -> list[Path]:
    """Return files Git would consider for staging, excluding ignored files."""
    output = run(["git", "status", "--porcelain", "-z"]).stdout
    paths: list[Path] = []
    entries = output.split("\0")
    for entry in entries:
        if not entry:
            continue
        path_text = entry[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        path = ROOT / path_text
        if path.is_file():
            paths.append(path)
    return paths


def check_file_sizes(paths: list[Path]) -> None:
    oversized = []
    for path in paths:
        size = path.stat().st_size
        if size > MAX_BYTES:
            oversized.append((path.relative_to(ROOT), size))

    if not oversized:
        return

    print(f"Refusing upload: files larger than {MAX_MB} MiB were found.")
    for path, size in oversized:
        print(f"- {path} ({size / 1024 / 1024:.1f} MiB)")
    print("Move large source artifacts under raw/ or keep them outside Git.")
    raise SystemExit(1)


def main() -> int:
    run(["python3", "tools/wiki_lint.py"])
    paths = candidate_files()
    if not paths:
        print("No changes to upload.")
        return 0

    check_file_sizes(paths)
    run(["git", "add", "-A"])

    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        print("No staged changes to upload.")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d")
    run(["git", "commit", "-m", f"Daily wiki sync {stamp}"])
    run(["git", "push"])
    print("Daily upload completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

