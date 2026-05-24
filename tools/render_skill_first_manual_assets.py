#!/usr/bin/env python3
"""Generate illustrative panels for the Research Wiki quickstart manual."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "manuals" / "assets" / "skill_first"


PANELS = [
    (
        "01_router_overview.png",
        "Research Wiki Workflow",
        [
            "Start with the research task, then choose the matching mode.",
            "",
            "1. source-intake       DOI / URL / PDF source queue",
            "2. paper-ingest        QCed full text -> paper page",
            "3. knowledge-workbench Query / Save / review queue",
            "4. synthesis-research  fan-out / thesis / synthesis",
            "5. wiki-lint           structure / semantic / repair / graph",
            "",
            "The same workflow works from Codex prompts or the optional router.",
        ],
    ),
    (
        "02_source_intake_flow.png",
        "source-intake",
        [
            "Modes:",
            "  add-source        Add DOI / DOI URL / article URL / PDF URL",
            "  refresh-dashboard Reconcile source queue, PDFs, and index",
            "  qced-full-text    Create readable Markdown only after QC",
            "",
            "Checkpoint:",
            "  Use sources you are allowed to read or download.",
            "",
            "Output boundary:",
            "  raw/paper_sources.md",
            "  raw/doi_dashboard.md",
            "  raw/full_text/<paper_file_key>.md after QC only",
        ],
    ),
    (
        "03_paper_ingest_boundary.png",
        "paper-ingest",
        [
            "Mode:",
            "  ingest-qced-full-text",
            "",
            "Reads:",
            "  raw/full_text/<paper_file_key>.md",
            "  only when qc_status: codex_qc_done",
            "",
            "Writes:",
            "  wiki/literature/<slug>.md",
            "",
            "Does not:",
            "  acquire new sources",
            "  copy complete article text into wiki",
            "  write cross-paper synthesis",
        ],
    ),
    (
        "04_knowledge_workbench_modes.png",
        "knowledge-workbench",
        [
            "Modes:",
            "  query          Read-only answer with evidence tier",
            "  query-to-save  Turn answer into a Save proposal",
            "  save           Write only after choosing target layer",
            "  review-queue   Maintenance-only write for uncertain items",
            "",
            "Rule:",
            "  Query never writes files.",
            "  Save is deliberate and target-scoped.",
        ],
    ),
    (
        "05_save_target_layer.png",
        "Save target layer",
        [
            "Before writing, choose one target:",
            "",
            "  wiki/concepts/             recurring concept",
            "  wiki/synthesis/            cross-literature judgment",
            "  wiki/project_synthesis/    project history or decision",
            "  maintenance/review_queue.md uncertain or conflicting claim",
            "  maintenance/log.md         operation note, not evidence",
            "",
            "If evidence is weak, write a review item instead of a formal page.",
        ],
    ),
    (
        "06_fanout_review_gate.png",
        "synthesis-research",
        [
            "Flow:",
            "",
            "  1. fanout-review",
            "     Stage possible concept, synthesis, overview, hot-question,",
             "     project, graph, and supersession impacts.",
            "",
            "  2. human approval",
            "     Check target pages, supported/challenged claims, confidence,",
            "     counter-evidence, and supersession risk.",
            "",
            "  3. apply-approved-fanout",
            "     Advanced write mode for one approved item only.",
            "",
            "  Keep cross-page changes reviewable before formal wiki updates.",
        ],
    ),
    (
        "07_wiki_lint_checks.png",
        "wiki-lint",
        [
            "Modes:",
            "  structure-lint   Frontmatter, indexes, paths, wikilinks",
            "  semantic-lint    Stale claims, contradictions, evidence tiers",
            "  repair-plan      Human-readable fix plan",
            "  state-graph      Regenerate maintenance/state.json and graph.json",
            "",
            "Findings route to source intake, review queue, or deliberate Save.",
        ],
    ),
    (
        "08_reference_docs.png",
        "Reference docs",
        [
            "Quickstart:",
            "  first path through source, paper page, query, save, lint",
            "",
            "USER_GUIDE:",
            "  mode permissions, evidence tiers, target layers",
            "",
            "Pipeline Architecture:",
            "  artifacts, gates, write boundaries, compatibility aliases",
        ],
    ),
]


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_panel(filename: str, title: str, lines: list[str]) -> None:
    width, height = 1600, 950
    image = Image.new("RGB", (width, height), "#f4f1ec")
    draw = ImageDraw.Draw(image)

    shadow = (82, 84, 88)
    panel = (38, 43, 52)
    header = (63, 71, 84)
    accent = (42, 153, 118)
    body = (238, 242, 246)
    muted = (177, 186, 196)

    draw.rounded_rectangle((94, 95, width - 74, height - 68), radius=18, fill=shadow)
    draw.rounded_rectangle((70, 70, width - 98, height - 92), radius=18, fill=panel)
    draw.rounded_rectangle((70, 70, width - 98, 152), radius=18, fill=header)
    draw.rectangle((70, 128, width - 98, 152), fill=header)

    for index, color in enumerate(("#ff6b6b", "#ffd166", "#06d6a0")):
        x = 112 + index * 38
        draw.ellipse((x, 100, x + 20, 120), fill=color)

    title_font = load_font(36, bold=True)
    body_font = load_font(29)
    small_font = load_font(22)

    draw.text((220, 94), title, font=title_font, fill="#ffffff")
    draw.text((114, 168), "$ research-wiki skill-first", font=small_font, fill=accent)

    y = 220
    for raw in lines:
        if not raw:
            y += 24
            continue
        text_color = accent if raw.endswith(":") or raw.startswith("Flow") else body
        if raw.startswith("  "):
            text_color = muted if raw.strip().startswith(("Confirm", "only", "Evidence", "local", "operation")) else body
        for part in wrap(raw, width=74, subsequent_indent="  " if raw.startswith("  ") else ""):
            draw.text((114, y), part, font=body_font, fill=text_color)
            y += 42
        y += 6

    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / filename)


def main() -> int:
    for filename, title, lines in PANELS:
        draw_panel(filename, title, lines)
        print(f"Wrote {OUT / filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
