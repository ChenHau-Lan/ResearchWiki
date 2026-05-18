"""Mark literature pages by full-text availability and add scheme keywords."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LITERATURE = ROOT / "wiki" / "literature"
REFERENCES = ROOT / "references.bib"
REPORT = ROOT / "raw" / "papers" / "no-fulltext-delete-candidates-2026-05-17.md"


def bib_entries() -> dict[str, str]:
    text = REFERENCES.read_text(encoding="utf-8")
    entries = re.split(r"\n(?=@\w+\{)", text.strip())
    out: dict[str, str] = {}
    for entry in entries:
        m = re.match(r"@\w+\{([^,]+),", entry)
        if m:
            out[m.group(1)] = entry
    return out


def yaml_values(line: str) -> list[str]:
    if "[" not in line or "]" not in line:
        return []
    raw = line.split("[", 1)[1].split("]", 1)[0]
    return [part.strip() for part in raw.split(",") if part.strip()]


def yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(sorted(dict.fromkeys(values))) + "]"


def add_or_replace_line(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    if pattern.search(text):
        return pattern.sub(f"{key}: {value}", text, count=1)
    return text.replace("---\n", f"---\n{key}: {value}\n", 1)


def ensure_keyword_page(keyword: str) -> Path:
    path = LITERATURE / f"keyword_{keyword}.md"
    if not path.exists():
        title = keyword.replace("_", " ").title()
        path.write_text(
            "\n".join(
                [
                    "---",
                    "type: concept",
                    "status: draft",
                    "source_status: personal-note",
                    f"topics: [keyword, {keyword}]",
                    f"keywords: [{keyword}]",
                    "created: 2026-05-17",
                    "updated: 2026-05-17",
                    "sources: []",
                    "---",
                    "",
                    f"# {title}",
                    "",
                    "## Literature",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    return path


def append_keyword_link(keyword: str, page_stem: str) -> None:
    path = ensure_keyword_page(keyword)
    text = path.read_text(encoding="utf-8")
    link = f"- [[{page_stem}|{page_stem}]]"
    if link not in text:
        path.write_text(text.rstrip() + "\n" + link + "\n", encoding="utf-8")


def classify_scheme(text: str) -> list[str]:
    low = text.lower()
    keywords = []
    if any(term in low for term in ["microphysics scheme", "microphysics parameterization", "two-moment", "double-moment", "bulk microphysics", "cloud microphysics scheme", "cumulus cloud microphysics"]):
        keywords.append("microphysics_scheme")
    if any(term in low for term in ["aerosol scheme", "aerosol-aware", "aerosol-cloud interactions", "wrf-aci", "wrf/chem", "wrf-chem", "aerosol transport simulation", "size-resolved sectional model"]):
        keywords.append("aerosol_scheme")
    return keywords


def main() -> None:
    entries = bib_entries()
    delete_candidates: list[str] = []
    marked_true = 0
    marked_false = 0
    scheme_added = 0

    for path in sorted(LITERATURE.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "type: paper" not in text:
            continue
        ck_match = re.search(r"^citation_key:\s*(.+)$", text, re.M)
        if not ck_match:
            continue
        citation_key = ck_match.group(1).strip()
        bib = entries.get(citation_key, "")
        has_pdf = bool(re.search(r"\n\tfile\s*=\s*\{.*?\.pdf.*?\}", bib, re.S | re.I))
        text = add_or_replace_line(text, "full_text", "true" if has_pdf else "false")
        if has_pdf:
            marked_true += 1
            combined = text + "\n" + bib
            extra = classify_scheme(combined)
            if extra:
                kw_line = re.search(r"^keywords:\s*(.+)$", text, re.M)
                values = yaml_values(kw_line.group(0)) if kw_line else []
                for kw in extra:
                    if kw not in values:
                        values.append(kw)
                        scheme_added += 1
                    append_keyword_link(kw, path.stem)
                text = add_or_replace_line(text, "keywords", yaml_list(values))
                for kw in extra:
                    link = f"- [[keyword_{kw}|{kw}]]"
                    if link not in text:
                        text = text.rstrip() + "\n" + link + "\n"
        else:
            marked_false += 1
            title = re.search(r"^#\s+(.+)$", text, re.M)
            delete_candidates.append(f"- `{path.as_posix()}` | `{citation_key}` | {title.group(1) if title else path.stem}")
        path.write_text(text, encoding="utf-8")

    REPORT.write_text(
        "\n".join(
            [
                "# No-Fulltext Delete Candidates",
                "",
                "依 `references.bib` 是否有 PDF `file` 欄位判定。專案規則禁止批量刪除；若要刪除，請逐一確認或手動處理。",
                "",
                f"- full_text=true pages: {marked_true}",
                f"- full_text=false pages: {marked_false}",
                "",
                "## Candidates",
                "",
                *delete_candidates,
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"full_text_true={marked_true} full_text_false={marked_false} scheme_keyword_additions={scheme_added} report=raw/papers/no-fulltext-delete-candidates-2026-05-17.md")


if __name__ == "__main__":
    main()
