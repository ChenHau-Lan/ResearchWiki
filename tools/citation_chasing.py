"""Build citation-chasing candidates from existing references.bib DOI records."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references.bib"
QUEUE = ROOT / "wiki" / "literature" / "citation_chasing_queue.md"
RESULTS = ROOT / "raw" / "papers" / "citation-chasing-candidates.jsonl"


def bib_entries() -> list[dict]:
    text = REFERENCES.read_text(encoding="utf-8")
    entries = re.split(r"\n(?=@\w+\{)", text.strip())
    rows = []
    for entry in entries:
        key = re.match(r"@\w+\{([^,]+),", entry)
        doi = re.search(r"\n\tdoi = \{(.*?)\},", entry, re.S)
        title = re.search(r"\n\ttitle = \{(.*?)\},", entry, re.S)
        if key and doi:
            rows.append(
                {
                    "key": key.group(1),
                    "doi": doi.group(1).replace("{", "").replace("}", ""),
                    "title": re.sub(r"[{}\n\t]+", " ", title.group(1)).strip() if title else "",
                }
            )
    return rows


def fetch_work(doi: str) -> dict:
    encoded = urllib.parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "wiki-research-codex/0.1 (mailto:none@example.com)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8")).get("message", {})


def main() -> None:
    existing_dois = {row["doi"].lower() for row in bib_entries()}
    seeds = bib_entries()[:20]
    seen = set(existing_dois)
    if RESULTS.exists():
        for line in RESULTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line).get("doi", "").lower())
                except json.JSONDecodeError:
                    pass

    candidates = []
    for seed in seeds:
        try:
            work = fetch_work(seed["doi"])
        except Exception as exc:
            candidates.append({"error": str(exc), "seed": seed})
            continue
        refs = work.get("reference", [])[:20]
        for ref in refs:
            doi = (ref.get("DOI") or ref.get("doi") or "").lower()
            if not doi or doi in seen:
                continue
            seen.add(doi)
            candidates.append(
                {
                    "seed_key": seed["key"],
                    "seed_doi": seed["doi"],
                    "doi": doi,
                    "title": ref.get("article-title") or ref.get("volume-title") or "Untitled reference",
                    "authors": ref.get("author", "Unknown authors"),
                    "year": ref.get("year", "n.d."),
                    "journal": ref.get("journal-title", ""),
                }
            )
        time.sleep(0.2)

    rows = [row for row in candidates if "doi" in row]
    if rows:
        with RESULTS.open("a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        text = QUEUE.read_text(encoding="utf-8")
        lines = ["", "## Candidate Batch", ""]
        for row in rows[:30]:
            lines.append(
                f"- `{row['doi']}` | {row['authors']} ({row['year']}). {row['title']}. "
                f"{row['journal']}. seed=`{row['seed_key']}`"
            )
        QUEUE.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")

    print(f"new_citation_candidates={len(rows)} total_rows={len(candidates)}")


if __name__ == "__main__":
    main()
