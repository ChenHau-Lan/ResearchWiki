#!/usr/bin/env python3
"""Render simple repository Markdown files to PDF with XeLaTeX.

This renderer is intentionally small and dependency-light. It is designed for
README/reference documents in this repository when Pandoc is not available.
It does not try to be a full Markdown implementation.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def inline_markup(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[\]\([^)]+\)", "", text)
    placeholders: list[str] = []

    def stash(value: str) -> str:
        placeholders.append(value)
        return f"@@RW_PLACEHOLDER_{len(placeholders) - 1}@@"

    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: stash(rf"\href{{{escape_latex(m.group(2))}}}{{{escape_latex(m.group(1))}}}"),
        text,
    )
    text = escape_latex(text)
    text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", text)
    for index, value in enumerate(placeholders):
        text = text.replace(escape_latex(f"@@RW_PLACEHOLDER_{index}@@"), value)
    return text


def image_to_latex(source: Path, image_ref: str, alt: str) -> str:
    image_ref = image_ref.strip()
    if image_ref.startswith(("http://", "https://")):
        return rf"\emph{{Image omitted: {escape_latex(alt or image_ref)}}}\par"
    image_path = Path(image_ref)
    if not image_path.is_absolute():
        image_path = source.parent / image_path
    image_path = image_path.resolve()
    if not image_path.exists():
        return rf"\emph{{Missing image: {escape_latex(image_ref)}}}\par"
    return "\n".join(
        [
            r"\begin{center}",
            rf"\includegraphics[width=0.92\linewidth]{{{escape_latex(image_path.as_posix())}}}",
            r"\end{center}",
            rf"\vspace{{-0.35em}}\emph{{{escape_latex(alt or image_ref)}}}\par",
        ]
    )


def split_table_line(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def table_to_latex(table_lines: list[str]) -> str:
    rows = [split_table_line(line) for line in table_lines if line.strip()]
    if len(rows) < 2:
        return "\n".join([r"\begin{Verbatim}[fontsize=\scriptsize,breaklines=true]", *table_lines, r"\end{Verbatim}"])

    headers = rows[0]
    data_rows = [row for row in rows[1:] if not is_table_separator(row)]
    if not data_rows:
        return ""

    rendered = [r"\begin{itemize}[leftmargin=1.2em,itemsep=0.35em]"]
    for row in data_rows:
        padded = (row + [""] * len(headers))[: len(headers)]
        parts = []
        for header, cell in zip(headers, padded):
            if not cell:
                continue
            parts.append(rf"\textbf{{{inline_markup(header)}:}} {inline_markup(cell)}")
        if parts:
            rendered.append(r"\item " + r"\\ ".join(parts))
    rendered.append(r"\end{itemize}")
    return "\n".join(rendered)


def markdown_to_latex(markdown: str, source: Path) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    in_code = False
    in_itemize = False
    in_quote = False
    table_lines: list[str] = []

    def close_itemize() -> None:
        nonlocal in_itemize
        if in_itemize:
            out.append(r"\end{itemize}")
            in_itemize = False

    def close_quote() -> None:
        nonlocal in_quote
        if in_quote:
            out.append(r"\end{quote}")
            in_quote = False

    def close_table() -> None:
        nonlocal table_lines
        if table_lines:
            out.append(table_to_latex(table_lines))
            table_lines = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            close_itemize()
            close_quote()
            close_table()
            if in_code:
                out.append(r"\end{Verbatim}")
                in_code = False
            else:
                out.append(r"\begin{Verbatim}[fontsize=\small,breaklines=true]")
                in_code = True
            continue
        if in_code:
            out.append(line)
            continue

        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if image:
            close_itemize()
            close_quote()
            close_table()
            out.append(image_to_latex(source, image.group(2), image.group(1)))
            continue

        if line.startswith("|"):
            close_itemize()
            close_quote()
            table_lines.append(line)
            continue
        close_table()

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_itemize()
            close_quote()
            level = len(heading.group(1))
            text = inline_markup(heading.group(2))
            command = {
                1: "section*",
                2: "subsection*",
                3: "subsubsection*",
            }.get(level, "paragraph")
            out.append(rf"\{command}{{{text}}}")
            if level <= 2:
                out.append(r"\vspace{-0.25em}")
            continue

        if not line.strip():
            close_itemize()
            close_quote()
            out.append("")
            continue

        if line.startswith(">"):
            close_itemize()
            if not in_quote:
                out.append(r"\begin{quote}")
                in_quote = True
            out.append(inline_markup(line.lstrip("> ").strip()) + r"\\")
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", line)
        if bullet:
            close_quote()
            if not in_itemize:
                out.append(r"\begin{itemize}[leftmargin=1.4em,itemsep=0.15em]")
                in_itemize = True
            out.append(r"\item " + inline_markup(bullet.group(1)))
            continue

        numbered = re.match(r"^\d+\.\s+(.*)$", line)
        if numbered:
            close_quote()
            if not in_itemize:
                out.append(r"\begin{itemize}[leftmargin=1.4em,itemsep=0.15em]")
                in_itemize = True
            out.append(r"\item " + inline_markup(numbered.group(1)))
            continue

        close_itemize()
        close_quote()
        out.append(inline_markup(line) + r"\par")

    close_itemize()
    close_quote()
    close_table()
    if in_code:
        out.append(r"\end{Verbatim}")
    return "\n".join(out)


def tex_document(body: str, title: str) -> str:
    return rf"""
\documentclass[11pt]{{article}}
\usepackage[letterpaper,margin=0.78in]{{geometry}}
\usepackage{{fontspec}}
\usepackage{{xeCJK}}
\usepackage{{hyperref}}
\usepackage{{enumitem}}
\usepackage{{fvextra}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage{{titlesec}}
\usepackage{{parskip}}
\setmainfont{{Helvetica Neue}}
\setsansfont{{Helvetica Neue}}
\setmonofont{{Menlo}}
\setCJKmainfont{{Heiti TC}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
\titleformat{{\section}}{{\Large\bfseries}}{{}}{{0pt}}{{}}
\titleformat{{\subsection}}{{\large\bfseries}}{{}}{{0pt}}{{}}
\titleformat{{\subsubsection}}{{\normalsize\bfseries}}{{}}{{0pt}}{{}}
\setlength{{\parindent}}{{0pt}}
\setlist[itemize]{{topsep=0.2em}}
\title{{{escape_latex(title)}}}
\date{{}}
\begin{{document}}
\maketitle
\vspace{{-2em}}
{body}
\end{{document}}
"""


def render(source: Path, output: Path) -> None:
    if not shutil.which("xelatex"):
        raise SystemExit("xelatex is required to render README PDFs.")
    markdown = source.read_text(encoding="utf-8")
    first_heading = next((line.lstrip("# ").strip() for line in markdown.splitlines() if line.startswith("# ")), source.stem)
    first_heading = re.sub(r"\[!\[[^\]]*\]\([^)]+\)\]\([^)]+\)", "", first_heading).strip()
    body = markdown_to_latex(markdown, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="research_wiki_pdf_") as tmp_name:
        tmp = Path(tmp_name)
        tex = tmp / "document.tex"
        tex.write_text(tex_document(body, first_heading), encoding="utf-8")
        for _ in range(2):
            proc = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                cwd=tmp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stdout[-4000:])
        (tmp / "document.pdf").replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a simple Markdown file to PDF with XeLaTeX.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render((ROOT / args.source).resolve(), (ROOT / args.output).resolve())
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
