"""Search atmospheric-science literature candidates for later verification.

This script intentionally writes candidates to a queue instead of creating
formal paper pages. A candidate becomes a paper page only after metadata is
verified.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "wiki" / "literature" / "external_search_queue.md"
RESULTS = ROOT / "raw" / "papers" / "external-search-candidates.jsonl"

JOURNALS = [
    "Journal of the Atmospheric Sciences",
    "Monthly Weather Review",
    "Journal of Climate",
    "Journal of Applied Meteorology and Climatology",
    "Weather and Forecasting",
    "Atmospheric Chemistry and Physics",
    "Atmospheric Measurement Techniques",
    "Geophysical Research Letters",
    "Journal of Geophysical Research: Atmospheres",
    "Quarterly Journal of the Royal Meteorological Society",
    "Atmospheric Research",
    "Atmospheric Environment",
    "Bulletin of the American Meteorological Society",
]

KEYWORDS = [
    "aerosol cloud interaction",
    "cloud microphysics",
    "wildfire smoke aerosol",
    "stratospheric aerosol",
    "remote sensing retrieval validation",
    "drop size distribution",
    "bulk microphysics parameterization",
    "tropical cyclone orographic effect",
]


def crossref(query: str, journal: str, rows: int = 2) -> list[dict]:
    params = {
        "query.bibliographic": f"{query} {journal}",
        "filter": "from-pub-date:2000-01-01,type:journal-article",
        "rows": str(rows),
        "select": "DOI,title,author,container-title,published-print,published-online,issued,URL,is-referenced-by-count",
    }
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "wiki-research-codex/0.1 (mailto:none@example.com)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("message", {}).get("items", [])


def year_of(item: dict) -> str:
    for key in ["published-print", "published-online", "issued"]:
        parts = item.get(key, {}).get("date-parts")
        if parts and parts[0]:
            return str(parts[0][0])
    return "n.d."


def authors_of(item: dict) -> str:
    authors = []
    for author in item.get("author", [])[:4]:
        family = author.get("family", "")
        given = author.get("given", "")
        authors.append(", ".join(part for part in [family, given] if part))
    if len(item.get("author", [])) > 4:
        authors.append("et al.")
    return "; ".join(authors) or "Unknown authors"


def main() -> None:
    seen: set[str] = set()
    if RESULTS.exists():
        for line in RESULTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line).get("doi", "").lower())
                except json.JSONDecodeError:
                    pass

    new_rows = []
    for keyword in KEYWORDS[:4]:
        for journal in JOURNALS[:6]:
            try:
                items = crossref(keyword, journal, rows=1)
            except Exception as exc:  # keep batch resilient
                new_rows.append({"error": str(exc), "keyword": keyword, "journal": journal})
                continue
            for item in items:
                doi = (item.get("DOI") or "").lower()
                if not doi or doi in seen:
                    continue
                seen.add(doi)
                new_rows.append(
                    {
                        "keyword": keyword,
                        "journal_query": journal,
                        "doi": doi,
                        "title": (item.get("title") or ["Untitled"])[0],
                        "authors": authors_of(item),
                        "venue": (item.get("container-title") or [""])[0],
                        "year": year_of(item),
                        "url": item.get("URL", ""),
                        "referenced_by": item.get("is-referenced-by-count", 0),
                    }
                )
            time.sleep(0.2)

    if new_rows:
        with RESULTS.open("a", encoding="utf-8") as f:
            for row in new_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    candidates = [row for row in new_rows if "doi" in row]
    if candidates:
        text = QUEUE.read_text(encoding="utf-8")
        lines = ["", "## Candidate Batch", ""]
        for row in candidates[:25]:
            lines.append(
                f"- `{row['doi']}` | {row['authors']} ({row['year']}). {row['title']}. "
                f"{row['venue']}. keyword=`{row['keyword']}` cited_by={row['referenced_by']}"
            )
        QUEUE.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")

    print(f"new_candidates={len(candidates)} total_rows={len(new_rows)}")


if __name__ == "__main__":
    main()
