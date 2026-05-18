#!/usr/bin/env python3
"""Lightweight lint checks for the research wiki."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
INDEX = WIKI / "index.md"
REFERENCES = ROOT / "references.bib"


REQUIRED_FRONTMATTER_KEYS = {
    "type",
    "status",
    "source_status",
    "topics",
    "created",
    "updated",
    "sources",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    block = text[4:end].strip()
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def bib_keys() -> set[str]:
    if not REFERENCES.exists():
        return set()
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", read(REFERENCES)))


def source_keys(value: str) -> list[str]:
    if not value.startswith("[") or not value.endswith("]"):
        return []
    raw = value[1:-1].strip()
    if not raw:
        return []
    return [part.strip().strip("\"'") for part in raw.split(",") if part.strip()]


def main() -> int:
    errors: list[str] = []
    index_text = read(INDEX) if INDEX.exists() else ""
    keys = bib_keys()

    for path in sorted(WIKI.rglob("*.md")):
        rel = path.relative_to(ROOT)
        text = read(path)
        meta = parse_frontmatter(text)
        if meta is None:
            errors.append(f"{rel}: missing YAML frontmatter")
            continue

        missing = REQUIRED_FRONTMATTER_KEYS - set(meta)
        if missing:
            errors.append(f"{rel}: missing frontmatter keys: {', '.join(sorted(missing))}")

        page_id = path.relative_to(WIKI).with_suffix("").as_posix()
        if path.name != "index.md" and page_id not in index_text:
            if "[[" not in text:
                errors.append(f"{rel}: not linked from index.md and has no wiki links")

        if meta.get("type") == "paper":
            for key in source_keys(meta.get("sources", "")):
                if "/" in key or key.startswith("raw"):
                    continue
                if key not in keys:
                    errors.append(f"{rel}: paper source '{key}' missing from references.bib")

    if errors:
        print("wiki_lint failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("wiki_lint passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

