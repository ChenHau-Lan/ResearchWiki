#!/usr/bin/env python3
"""Advisory table-QC checks for raw/full_text Markdown.

This script reports issues only. It does not edit or delete files.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_TEXT_DIR = ROOT / "raw" / "full_text"
TABLE_CAPTION_RE = re.compile(r"^\s*(?:#{1,6}\s*)?Table\s+\d+[\.:]\s*", re.IGNORECASE)
CONTINUED_RE = re.compile(r"\bTable\s+\d+\.\s*Continued\b|\bContinued\b", re.IGNORECASE)


@dataclass
class FencedBlock:
    start: int
    end: int
    language: str
    lines: list[str]


def repo_rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for raw_line in text[4:end].splitlines():
        if ":" not in raw_line or raw_line.startswith(" "):
            continue
        key, value = raw_line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def fenced_blocks(lines: list[str]) -> list[FencedBlock]:
    blocks: list[FencedBlock] = []
    in_block = False
    start = 0
    language = ""
    content: list[str] = []
    for index, line in enumerate(lines, start=1):
        if line.startswith("```"):
            if not in_block:
                in_block = True
                start = index
                language = line.strip().removeprefix("```").strip()
                content = []
            else:
                blocks.append(FencedBlock(start=start, end=index, language=language, lines=content))
                in_block = False
            continue
        if in_block:
            content.append(line)
    return blocks


def is_tableish_block(block: FencedBlock) -> bool:
    joined = "\n".join(block.lines[:25])
    if re.search(r"\bTable\b", joined, flags=re.IGNORECASE):
        return True
    if CONTINUED_RE.search(joined):
        return True
    header_words = {"species", "method", "notes", "phase", "savanna", "forest", "source", "compound"}
    tokens = {token.lower() for token in re.findall(r"[A-Za-z]{4,}", joined)}
    return len(tokens & header_words) >= 3 and len(block.lines) >= 15


def one_word_line_ratio(lines: list[str]) -> float:
    nonempty = [line.strip() for line in lines if line.strip()]
    if not nonempty:
        return 0.0
    short = [line for line in nonempty if len(re.findall(r"\S+", line)) <= 2]
    return len(short) / len(nonempty)


def nearby(lines: list[str], start: int, end: int) -> str:
    before = max(0, start - 8)
    after = min(len(lines), end + 6)
    return "\n".join(lines[before:after])


def inspect_file(path: Path) -> list[str]:
    text = read(path)
    lines = text.splitlines()
    fm = parse_frontmatter(text)
    warnings: list[str] = []
    has_table_mention = bool(re.search(r"(?m)^\s*(?:#{1,6}\s*)?Table\s+\d+[\.:]", text, re.IGNORECASE))
    has_fragmented_caption = bool(re.search(r"(?im)^Table\s*$\n^\d+\.?\s*$", text))
    if (has_table_mention or has_fragmented_caption) and not fm.get("table_quality"):
        warnings.append("table mentions found but frontmatter has no table_quality field")

    for block in fenced_blocks(lines):
        if not is_tableish_block(block):
            continue
        nonempty = [line for line in block.lines if line.strip()]
        context = nearby(lines, block.start - 1, block.end - 1)
        if not re.search(r"(?m)^#{2,4}\s+Table\s+\d+", context, flags=re.IGNORECASE):
            warnings.append(f"line {block.start}: table-like fenced block is not under a `### Table N` heading")
        if "Table status:" not in context:
            warnings.append(f"line {block.start}: table-like fenced block is missing a Table status note")
        if len(nonempty) > 60:
            warnings.append(f"line {block.start}: long table-like block has {len(nonempty)} nonempty lines")
        if one_word_line_ratio(nonempty) > 0.45 and len(nonempty) > 20:
            warnings.append(f"line {block.start}: fragmented table block has many one-word lines")
        if CONTINUED_RE.search("\n".join(block.lines)):
            warnings.append(f"line {block.start}: continued table needs one combined table section and PDF/supplement check")

    in_fence = False
    for index, line in enumerate(lines, start=1):
        if line.startswith("```"):
            in_fence = not in_fence
        if in_fence:
            continue
        if TABLE_CAPTION_RE.match(line) and not line.lstrip().startswith("#"):
            warnings.append(f"line {index}: table caption should be a heading, e.g. `### {line.strip()}`")
    return warnings


def candidate_paths(args: list[str]) -> list[Path]:
    if args:
        return [Path(arg) if Path(arg).is_absolute() else ROOT / arg for arg in args]
    if not FULL_TEXT_DIR.exists():
        return []
    return sorted(path for path in FULL_TEXT_DIR.glob("*.md") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="Report table QC issues in raw/full_text Markdown.")
    parser.add_argument("paths", nargs="*", help="Optional files to check. Defaults to raw/full_text/*.md.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when table QC warnings are found.")
    args = parser.parse_args()

    total = 0
    print("Full-text table QC report")
    for path in candidate_paths(args.paths):
        warnings = inspect_file(path)
        if not warnings:
            print(f"OK {repo_rel(path)}")
            continue
        total += len(warnings)
        print(f"WARN {repo_rel(path)}")
        for warning in warnings:
            print(f"- {warning}")
    if total:
        print(f"Found {total} table-QC warning(s).")
    else:
        print("No table-QC warnings found.")
    return 1 if total and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
