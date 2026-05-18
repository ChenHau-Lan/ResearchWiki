"""Generate a wiki inventory page from Zotero local API JSON exports."""

from __future__ import annotations

import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "wiki" / "synthesis" / "zotero_library_inventory.md"
OVERRIDES = ROOT / "tools" / "zotero_metadata_overrides.json"


def load_inventory() -> list[dict]:
    root_snapshot = ROOT / "zotero-inventory.json"
    if root_snapshot.exists():
        inventory_json = root_snapshot
    else:
        candidates = sorted((ROOT / "raw" / "papers").glob("zotero-inventory-*.json"))
        if not candidates:
            raise FileNotFoundError("No Zotero inventory JSON snapshot found")
        inventory_json = candidates[-1]

    with inventory_json.open(encoding="utf-8-sig") as f:
        items = json.load(f)

    if OVERRIDES.exists():
        with OVERRIDES.open(encoding="utf-8") as f:
            overrides = json.load(f)
        for item in items:
            if item.get("key") in overrides:
                item.update(overrides[item["key"]])

    return items


def classify(item: dict) -> str:
    title = (item.get("title") or "").lower()
    item_type = item.get("itemType") or "unknown"

    if title.startswith("http"):
        return "Needs Metadata Cleanup"
    if any(
        term in title
        for term in [
            "aerosol",
            "ccn",
            "hygroscopic",
            "smoke",
            "dust",
            "biomass",
            "pollution",
            "cloud condensation",
            "black carbon",
        ]
    ):
        return "Aerosol / Aerosol-Cloud"
    if any(
        term in title
        for term in [
            "microphysics",
            "drop size",
            "raindrop",
            "precipitation",
            "rain",
            "hail",
            "ice nucleation",
            "riming",
            "coalescence",
            "droplet",
            "snow",
        ]
    ):
        return "Cloud Microphysics / Precipitation"
    if any(
        term in title
        for term in [
            "satellite",
            "modis",
            "radar",
            "lidar",
            "retrieval",
            "remote sensor",
            "remote sensing",
        ]
    ):
        return "Remote Sensing / Retrieval"
    if any(
        term in title
        for term in [
            "wrf",
            "model",
            "simulation",
            "parameterization",
            "scheme",
            "numerical",
            "parameterisation",
        ]
    ):
        return "Modeling / Parameterization"
    if any(
        term in title
        for term in [
            "typhoon",
            "hurricane",
            "tropical cyclone",
            "cyclone",
            "orographic",
            "topography",
            "landfall",
            "vortex",
        ]
    ):
        return "Tropical Cyclone / Orography"
    if item_type == "book":
        return "Books / Background"
    return "Needs Triage"


def format_creators(creators: list[str]) -> str:
    if len(creators) > 3:
        return ", ".join(creators[:3]) + ", et al."
    if creators:
        return ", ".join(creators)
    return "Unknown authors"


def needs_cleanup(item: dict) -> bool:
    title = (item.get("title") or "").strip()
    year = item.get("year") or "n.d."
    return title.lower().startswith("http") or not item.get("creators") or year == "n.d."


def main() -> None:
    items = load_inventory()
    for item in items:
        item["_category"] = classify(item)

    order = [
        "Aerosol / Aerosol-Cloud",
        "Cloud Microphysics / Precipitation",
        "Remote Sensing / Retrieval",
        "Modeling / Parameterization",
        "Tropical Cyclone / Orography",
        "Books / Background",
        "Needs Metadata Cleanup",
        "Needs Triage",
    ]
    counts = collections.Counter(item["_category"] for item in items)
    cleanup_count = sum(1 for item in items if needs_cleanup(item))

    lines = [
        "---",
        "type: synthesis",
        "status: needs-verification",
        "source_status: non-academic",
        "topics: [zotero, bibliography, aerosol, cloud_microphysics, remote_sensing, modeling]",
        "created: 2026-05-17",
        "updated: 2026-05-17",
        "sources: [references.bib, zotero-local-api]",
        "---",
        "",
        "# Zotero Library Inventory",
        "",
        "本頁是從 Zotero Desktop local API 匯入的文獻索引，作為正式讀文獻與建立 paper pages 的暫存入口。",
        "",
        "## Import Status",
        "",
        f"- Zotero top-level items: {len(items)}",
        "- BibTeX entries synced to `references.bib`: 247",
        f"- Items with URL-only title / incomplete metadata: {cleanup_count}",
        "- Read status: metadata-only",
        "- Integrity note: 本頁只整理 Zotero metadata，不代表已讀全文；非平凡學術主張仍需回到原文、DOI 或 PDF 驗證後才能寫入 paper/concept/synthesis 頁。",
        "",
        "## Topic Buckets",
        "",
    ]

    for name in order:
        if counts.get(name, 0):
            lines.append(f"- {name}: {counts[name]}")
    lines.append("")

    for name in order:
        bucket = [item for item in items if item["_category"] == name]
        if not bucket:
            continue
        lines.extend([f"## {name}", ""])
        for item in bucket:
            creators = format_creators(item.get("creators") or [])
            year = item.get("year") or "n.d."
            title = (item.get("title") or "Untitled").replace("\n", " ").strip()
            item_type = item.get("itemType") or "unknown"
            key = item.get("key") or "unknown"
            cleanup_note = " metadata-cleanup" if needs_cleanup(item) else ""
            lines.append(f"- `{key}` | {creators} ({year}). {title}. `{item_type}`.{cleanup_note}")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote wiki/synthesis/zotero_library_inventory.md with {len(items)} Zotero items")


if __name__ == "__main__":
    main()
