"""Build literature pages from Zotero inventory and references.bib.

The output model is intentionally flat:
- all literature pages live in wiki/literature/
- code pages live in wiki/code/
- graph structure is driven by topics and keywords
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
LITERATURE = WIKI / "literature"
RAW_PAPERS = ROOT / "raw" / "papers"
REFERENCES = ROOT / "references.bib"
OVERRIDES = ROOT / "tools" / "zotero_metadata_overrides.json"


OVERRIDE_BIBTEX = {
    "noauthor_aerosol_2009": """@book{levin_aerosol_2009,
\ttitle = {Aerosol Pollution Impact on Precipitation: A Scientific Review},
\teditor = {Levin, Zev and Cotton, William R.},
\turl = {https://doi.org/10.1007/978-1-4020-8690-8},
\tdoi = {10.1007/978-1-4020-8690-8},
\tpublisher = {Springer Dordrecht},
\tyear = {2009},
\tkeywords = {Aerosol-cloud interactions, Impact on precipitation},
}
""",
    "noauthor_httpsagupubsonlinelibrarywileycomdoifull1010292022gl100175_nodate": """@article{liu_significant_2022,
\ttitle = {Significant Effective Radiative Forcing of Stratospheric Wildfire Smoke},
\turl = {https://doi.org/10.1029/2022GL100175},
\tdoi = {10.1029/2022GL100175},
\tjournal = {Geophysical Research Letters},
\tauthor = {Liu, Cheng-Cheng and Portmann, Robert W. and Liu, Shang and Rosenlof, Karen H. and Peng, Yifeng and Yu, Pengfei},
\tyear = {2022},
\tvolume = {49},
\tnumber = {17},
\tkeywords = {pyroCb},
}
""",
    "noauthor_httpsamtcopernicusorgarticles1334712020amt-13-3471-2020pdf_nodate": """@article{chen_evaluation_2020,
\ttitle = {Evaluation of the {OMPS}/{LP} stratospheric aerosol extinction product using {SAGE} {III}/{ISS} observations},
\turl = {https://doi.org/10.5194/amt-13-3471-2020},
\tdoi = {10.5194/amt-13-3471-2020},
\tjournal = {Atmospheric Measurement Techniques},
\tauthor = {Chen, Zhong and Bhartia, Pawan K. and Torres, Omar and Jaross, Glen and Loughman, Robert and DeLand, Matthew and Colarco, Peter and Damadeo, Robert and Taha, Ghassan},
\tyear = {2020},
\tvolume = {13},
\tpages = {3471--3485},
\tkeywords = {pyroCb},
}
""",
    "noauthor_httpsacpcopernicusorgarticles19151832019_nodate": """@article{baars_unprecedented_2019,
\ttitle = {The unprecedented 2017--2018 stratospheric smoke event: decay phase and aerosol properties observed with the {EARLINET}},
\turl = {https://doi.org/10.5194/acp-19-15183-2019},
\tdoi = {10.5194/acp-19-15183-2019},
\tjournal = {Atmospheric Chemistry and Physics},
\tauthor = {Baars, Holger and Ansmann, Albert and Ohneiser, Kevin and Haarig, Moritz and Engelmann, Ronny and Althausen, Dietrich and Hanssen, Ingrid and Gausa, Michael and Pietruczuk, Aleksander and Szkop, Artur and Stachlewska, Iwona S. and Wang, Dongxiang and Reichardt, Jens and Skupin, Annett and Mattis, Ina and Trickl, Thomas and Vogelmann, Hannes and Navas-Guzman, Francisco and Haefele, Alexander and Acheson, Karen and Ruth, Albert A. and Tatarov, Boyan and Muller, Detlef and Hu, Qiaoyun and Podvin, Thierry and Goloub, Philippe and Veselovskii, Igor and Pietras, Christophe and Haeffelin, Martial and Freville, Patrick and Sicard, Michael and Comeron, Adolfo and Fernandez Garcia, Alfonso Javier and Molero Menendez, Francisco and Cordoba-Jabonero, Carmen and Guerrero-Rascado, Juan Luis and Alados-Arboledas, Lucas and Bortoli, Daniele and Costa, Maria Joao and Dionisi, Davide and Liberti, Gian Luigi and Wang, Xuan and Sannino, Alessia and Papagiannopoulos, Nikolaos and Boselli, Antonella and Mona, Lucia and D'Amico, Giuseppe and Romano, Salvatore and Perrone, Maria Rita and Belegante, Livio and Nicolae, Doina and Grigorov, Ivan and Gialitaki, Anna and Amiridis, Vassilis and Soupiona, Ourania and Papayannis, Alexandros and Mamouri, Rodanthi-Elisaveth and Nisantzi, Argyro and Heese, Birgit and Hofer, Julian and Schechner, Yoav Y. and Wandinger, Ulla and Pappalardo, Gelsomina},
\tyear = {2019},
\tvolume = {19},
\tpages = {15183--15198},
\tkeywords = {pyroCb},
}
""",
    "noauthor_httpseguspherecopernicusorgpreprints2025egusphere-2025-5076egusphere-2025-5076pdf_nodate": """@article{wang_wildfire_2025,
\ttitle = {Wildfire aerosols lofted by North American pyrocumulonimbus clouds: long-range transport and aerosol-cloud-radiative effects},
\turl = {https://doi.org/10.5194/egusphere-2025-5076},
\tdoi = {10.5194/egusphere-2025-5076},
\tjournal = {EGUsphere},
\tauthor = {Wang, Yan and Cao, Yujia and Yu, Haixiao and Wang, Shuo and Hu, Qiaoyun and Chang, Yuyang and Zhao, Chun and Li, Zhengqiang and Chen, Cheng},
\tyear = {2025},
\tkeywords = {pyroCb},
}
""",
}


def normalize_title(value: str) -> str:
    value = re.sub(r"[{}]", "", value or "")
    value = unicodedata.normalize("NFKD", value)
    value = value.lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return value[:90] or "untitled"


def field(entry: str, name: str) -> str:
    match = re.search(rf"\n\t{name}\s*=\s*\{{(.*?)\}},", entry, re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def apply_bibtex_overrides() -> None:
    text = REFERENCES.read_text(encoding="utf-8")
    for old_key, new_entry in OVERRIDE_BIBTEX.items():
        pattern = re.compile(r"@\w+\{" + re.escape(old_key) + r",[\s\S]*?\n\}\n", re.M)
        text, count = pattern.subn(new_entry, text, count=1)
        if count == 0 and new_entry.split("{", 1)[1].split(",", 1)[0] not in text:
            text += "\n" + new_entry
    REFERENCES.write_text(text, encoding="utf-8")


def parse_bibtex() -> list[dict]:
    text = REFERENCES.read_text(encoding="utf-8")
    entries = re.split(r"\n(?=@\w+\{)", text.strip())
    rows = []
    for entry in entries:
        head = re.match(r"@(\w+)\{([^,]+),", entry)
        if not head:
            continue
        rows.append(
            {
                "entry_type": head.group(1),
                "citation_key": head.group(2),
                "title": field(entry, "title"),
                "year": field(entry, "year"),
                "authors": field(entry, "author") or field(entry, "editor"),
                "venue": field(entry, "journal") or field(entry, "publisher"),
                "doi": field(entry, "doi"),
                "url": field(entry, "url"),
                "keywords": field(entry, "keywords"),
            }
        )
    return rows


def load_inventory() -> list[dict]:
    path = RAW_PAPERS / "zotero-inventory-latest.json"
    if not path.exists():
        candidates = sorted(RAW_PAPERS.glob("zotero-inventory-*.json"))
        path = candidates[-1]
    with path.open(encoding="utf-8-sig") as f:
        items = json.load(f)
    if OVERRIDES.exists():
        overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        for item in items:
            if item.get("key") in overrides:
                item.update(overrides[item["key"]])
    return items


def keywords_for(title: str, bib_keywords: str) -> tuple[list[str], list[str]]:
    text = f"{title} {bib_keywords}".lower()
    main: list[str] = []
    sub: list[str] = []
    rules = [
        ("aerosol", ["aerosol", "ccn", "smoke", "dust", "biomass", "pollution", "hygroscopic"]),
        ("cloud_microphysics", ["microphysics", "droplet", "ice nucleation", "hail", "riming", "coalescence", "precipitation", "rain"]),
        ("remote_sensing", ["satellite", "modis", "radar", "lidar", "retrieval", "sage", "omps"]),
        ("modeling", ["wrf", "model", "simulation", "parameterization", "scheme", "numerical"]),
        ("tropical_cyclone", ["typhoon", "hurricane", "tropical cyclone", "cyclone", "landfall", "orographic", "topography", "vortex"]),
        ("instrumentation", ["instrument", "measurement", "observations", "aircraft"]),
    ]
    for name, terms in rules:
        if any(term in text for term in terms):
            main.append(name)

    sub_rules = {
        "pyrocb": ["pyrocb", "pyrocumulonimbus"],
        "wildfire_smoke": ["wildfire", "smoke", "biomass burning"],
        "aerosol_cloud_interaction": ["aerosol-cloud", "indirect effect", "twomey", "cloud condensation"],
        "stratospheric_aerosol": ["stratospheric", "stratosphere", "sage", "omps"],
        "retrieval_validation": ["retrieval", "validation", "evaluation"],
        "drop_size_distribution": ["drop size", "raindrop size", "dsd"],
        "bulk_microphysics": ["bulk", "two-moment", "double-moment", "microphysics scheme"],
        "orographic_effect": ["orographic", "topography", "terrain"],
        "landfall": ["landfall"],
    }
    for name, terms in sub_rules.items():
        if any(term in text for term in terms):
            sub.append(name)
    if not main:
        main.append("needs_triage")
    if not sub:
        sub.append("needs_subkeyword")
    return sorted(set(main)), sorted(set(sub))


def source_status(item: dict, bib: dict | None) -> str:
    item_type = item.get("itemType") or ""
    venue = (bib or {}).get("venue", "").lower()
    if item_type == "preprint" or "egusphere" in venue:
        return "preprint"
    if item_type in {"webpage", "attachment"}:
        return "non-academic"
    if item_type in {"book", "bookSection"}:
        return "peer-reviewed"
    return "peer-reviewed" if item_type == "journalArticle" else "needs-verification"


def yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(values) + "]"


def write_keyword_pages(groups: dict[str, list[str]]) -> None:
    for keyword, pages in sorted(groups.items()):
        path = LITERATURE / f"keyword_{slugify(keyword)}.md"
        title = keyword.replace("_", " ").title()
        links = "\n".join(f"- [[{page}|{page}]]" for page in sorted(set(pages)))
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
                    links,
                    "",
                ]
            ),
            encoding="utf-8",
        )


def main() -> None:
    apply_bibtex_overrides()
    LITERATURE.mkdir(parents=True, exist_ok=True)

    inventory = load_inventory()
    bib_rows = parse_bibtex()
    bib_by_title = {normalize_title(row["title"]): row for row in bib_rows if row["title"]}

    keyword_groups: dict[str, list[str]] = {}
    written = 0

    for item in inventory:
        title = item.get("title") or "Untitled"
        bib = bib_by_title.get(normalize_title(title))
        citation_key = (bib or {}).get("citation_key") or f"zotero_{item.get('key', 'unknown').lower()}"
        page = slugify(citation_key)
        path = LITERATURE / f"{page}.md"
        creators = item.get("creators") or []
        year = item.get("year") or (bib or {}).get("year") or "n.d."
        topics, keywords = keywords_for(title, (bib or {}).get("keywords", ""))
        status = source_status(item, bib)
        read_status = "metadata-only" if item.get("itemType") not in {"attachment", "webpage"} else "not-a-paper"

        for keyword in keywords:
            keyword_groups.setdefault(keyword, []).append(page)

        author_text = ", ".join(creators) if creators else (bib or {}).get("authors", "Unknown authors")
        venue = (bib or {}).get("venue", "")
        doi = (bib or {}).get("doi", "")
        url = (bib or {}).get("url", "")
        zotero_key = item.get("key", "")
        item_type = item.get("itemType", "unknown")
        source_key = citation_key if not citation_key.startswith("zotero_") else f"zotero/{zotero_key}"

        path.write_text(
            "\n".join(
                [
                    "---",
                    "type: paper",
                    "status: needs-verification",
                    f"source_status: {status}",
                    f"topics: {yaml_list(topics)}",
                    f"keywords: {yaml_list(keywords)}",
                    "created: 2026-05-17",
                    "updated: 2026-05-17",
                    f"sources: [{source_key}]",
                    f"zotero_key: {zotero_key}",
                    f"citation_key: {citation_key}",
                    "---",
                    "",
                    f"# {title}",
                    "",
                    "## Bibliographic Metadata",
                    "",
                    f"- Citation Key: {citation_key}",
                    f"- Zotero Key: {zotero_key}",
                    f"- Item Type: {item_type}",
                    f"- Title: {title}",
                    f"- Authors: {author_text}",
                    f"- Venue/Year: {venue}, {year}".strip(),
                    f"- Status: {status}",
                    f"- DOI: {doi}",
                    f"- URL: {url}",
                    "- Raw Source: Zotero Desktop local API / references.bib",
                    f"- Read Status: {read_status}",
                    "",
                    "## Keywords",
                    "",
                    f"- Topics: {', '.join(topics)}",
                    f"- Keywords: {', '.join(keywords)}",
                    "",
                    "## Research Question",
                    "",
                    "Not yet extracted. This page was generated from Zotero metadata.",
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
                    *[f"- [[keyword_{keyword}|{keyword}]]" for keyword in keywords],
                    "",
                ]
            ),
            encoding="utf-8",
        )
        written += 1

    write_keyword_pages(keyword_groups)
    print(f"Wrote {written} literature pages and {len(keyword_groups)} keyword pages")


if __name__ == "__main__":
    main()
