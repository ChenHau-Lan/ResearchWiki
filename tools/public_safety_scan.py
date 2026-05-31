#!/usr/bin/env python3
"""Public-repo safety scan for RKF."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"/Users/(?!\[\^)[^/\s]+"),
    re.compile(r"C:\\Users\\", re.IGNORECASE),
]
PRIVATE_REPORTS = {
    "prompts/external_sandbox_context.md",
    "rkf.workspace.toml",
    "workspace.toml",
}
PRIVATE_PREFIXES = {
    ".rkf_private/",
    "state/gates/",
    "state/search_runs/",
}


def tracked_files() -> list[Path]:
    try:
        output = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True)
    except Exception:  # noqa: BLE001
        return sorted(path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts)
    return [ROOT / line for line in output.splitlines() if line.strip()]


def is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:2048]
    except OSError:
        return True
    return b"\0" in chunk


def main() -> int:
    errors: list[str] = []
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in PRIVATE_REPORTS:
            errors.append(f"private runtime file is tracked: {rel}")
        if any(rel.startswith(prefix) for prefix in PRIVATE_PREFIXES):
            errors.append(f"private runtime path is tracked: {rel}")
        if path.suffix.lower() == ".pdf":
            errors.append(f"PDF is tracked in public repo: {rel}")
        if not path.exists() or is_binary(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if rel == "tools/public_safety_scan.py":
            continue
        for pattern in FORBIDDEN_PATH_PATTERNS:
            for match in pattern.findall(text):
                if rel == "rkf.workspace.example.toml":
                    continue
                errors.append(f"{rel}: local/private path pattern: {match}")
        if rel.startswith("knowledge/papers/") and len(text) > 120000:
            errors.append(f"{rel}: unusually large paper page may contain copied article text")
    if errors:
        print("public_safety_scan failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("public_safety_scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
