"""Promote verified Crossref external-search candidates into literature pages."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "raw" / "papers" / "external-search-candidates.jsonl"
REFERENCES = ROOT / "references.bib"
LITERATURE = ROOT / "wiki" / "literature"
LOG = ROOT / "wiki" / "log.md"


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")[:80] or "untitled"


def existing_dois() -> set[str]:
    text = REFERENCES.read_text(encoding="utf-8")
    return {m.group(1).lower() for m in re.finditer(r"\n\tdoi = \{(.*?)\},", text, re.S)}


def candidate_key(row: dict) -> str:
    author = (row.get("authors") or "unknown").split(";")[0].split(",")[0].strip() or "unknown"
    title_word = slug(row.get("title", "")).split("_")[0] or "paper"
    year = row.get("year") or "nodate"
    return slug(f"{author}_{title_word}_{year}")


def topics_keywords(row: dict) -> tuple[list[str], list[str]]:
    text = f"{row.get('keyword','')} {row.get('title','')}".lower()
    topics: list[str] = []
    keywords: list[str] = []
    if "aerosol" in text or "smoke" in text:
        topics.append("aerosol")
    if "cloud microphysics" in text or "microphysics" in text or "cloud" in text:
        topics.append("cloud_microphysics")
    if "retrieval" in text or "satellite" in text or "radar" in text or "observations" in text:
        topics.append("remote_sensing")
    if "model" in text or "wrf" in text or "simulation" in text or "parameterization" in text:
        topics.append("modeling")
    if "wildfire" in text or "smoke" in text or "biomass" in text:
        keywords.append("wildfire_smoke")
    if "aerosol" in text and "cloud" in text:
        keywords.append("aerosol_cloud_interaction")
    if "microphysics" in text:
        keywords.append("bulk_microphysics")
    if "stratospheric" in text:
        keywords.append("stratospheric_aerosol")
    if not topics:
        topics.append("needs_triage")
    if not keywords:
        keywords.append("needs_subkeyword")
    return sorted(set(topics)), sorted(set(keywords))


def append_reference(row: dict, key: str) -> None:
    text = REFERENCES.read_text(encoding="utf-8")
    entry = f"""
@article{{{key},
\ttitle = {{{row['title']}}},
\turl = {{{row.get('url', '')}}},
\tdoi = {{{row['doi']}}},
\tjournal = {{{row.get('venue', '')}}},
\tauthor = {{{row.get('authors', '').replace(';', ' and')}}},
\tyear = {{{row.get('year', '')}}},
\tkeywords = {{{row.get('keyword', '')}}},
}}
"""
    REFERENCES.write_text(text.rstrip() + "\n\n" + entry.strip() + "\n", encoding="utf-8")


def write_page(row: dict, key: str) -> None:
    topics, keywords = topics_keywords(row)
    path = LITERATURE / f"{key}.md"
    if path.exists():
        return
    keyword_links = "\n".join(f"- [[keyword_{kw}|{kw}]]" for kw in keywords)
    path.write_text(
        "\n".join(
            [
                "---",
                "type: paper",
                "status: needs-verification",
                "source_status: peer-reviewed",
                f"topics: [{', '.join(topics)}]",
                f"keywords: [{', '.join(keywords)}]",
                "created: 2026-05-17",
                "updated: 2026-05-17",
                f"sources: [{key}]",
                f"citation_key: {key}",
                "external_source: crossref",
                "---",
                "",
                f"# {row['title']}",
                "",
                "## Bibliographic Metadata",
                "",
                f"- Citation Key: {key}",
                f"- Title: {row['title']}",
                f"- Authors: {row.get('authors', 'Unknown authors')}",
                f"- Venue/Year: {row.get('venue', '')}, {row.get('year', '')}",
                "- Status: peer-reviewed",
                f"- DOI: {row['doi']}",
                f"- URL: {row.get('url', '')}",
                "- Raw Source: Crossref external-search candidate",
                "- Read Status: metadata-only",
                "",
                "## Keywords",
                "",
                f"- Topics: {', '.join(topics)}",
                f"- Keywords: {', '.join(keywords)}",
                "",
                "## Research Question",
                "",
                "Not yet extracted. This page was added from verified Crossref metadata.",
                "",
                "## Method",
                "",
                "Not yet extracted.",
                "",
                "## Main Findings",
                "",
                "- Not yet summarized from full text.",
                "",
                "## Limitations",
                "",
                "- Metadata-only page; do not use for non-trivial claims until the source is read.",
                "",
                "## Citable Claims",
                "",
                "- No citable claim extracted yet.",
                "",
                "## Graph Links",
                "",
                keyword_links,
                "",
            ]
        ),
        encoding="utf-8",
    )


def ensure_keyword_pages(rows: list[dict]) -> None:
    touched: dict[str, set[str]] = {}
    for row in rows:
        key = candidate_key(row)
        _, keywords = topics_keywords(row)
        for kw in keywords:
            touched.setdefault(kw, set()).add(key)
    for kw, keys in touched.items():
        path = LITERATURE / f"keyword_{kw}.md"
        if not path.exists():
            path.write_text(
                "\n".join(
                    [
                        "---",
                        "type: concept",
                        "status: draft",
                        "source_status: personal-note",
                        f"topics: [keyword, {kw}]",
                        f"keywords: [{kw}]",
                        "created: 2026-05-17",
                        "updated: 2026-05-17",
                        "sources: []",
                        "---",
                        "",
                        f"# {kw.replace('_', ' ').title()}",
                        "",
                        "## Literature",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        text = path.read_text(encoding="utf-8")
        for key in sorted(keys):
            link = f"- [[{key}|{key}]]"
            if link not in text:
                text = text.rstrip() + "\n" + link + "\n"
        path.write_text(text, encoding="utf-8")


def main() -> None:
    if not RESULTS.exists():
        print("no candidates")
        return
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [r for r in rows if "doi" in r]
    rows.sort(key=lambda r: int(r.get("referenced_by") or 0), reverse=True)
    existing = existing_dois()
    promoted = []
    for row in rows:
        if row["doi"].lower() in existing:
            continue
        if len(promoted) >= 8:
            break
        key = candidate_key(row)
        append_reference(row, key)
        write_page(row, key)
        promoted.append(row)
        existing.add(row["doi"].lower())
    ensure_keyword_pages(promoted)
    if promoted:
        log = LOG.read_text(encoding="utf-8")
        lines = ["", "## [2026-05-17] ingest-paper | Promoted external search candidates", ""]
        for row in promoted:
            lines.append(f"- Added `{candidate_key(row)}` from Crossref metadata: {row['title']}")
        LOG.write_text(log.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"promoted={len(promoted)}")


if __name__ == "__main__":
    main()
