#!/usr/bin/env python3
"""Generate a human-reviewed repair plan for Research Wiki.

This script writes a Markdown plan. It never deletes files.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import wiki_doctor


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "maintenance"


def issue_guidance(issue: str, *, required: bool) -> tuple[str, str, str]:
    """Return risk/action/deletion-policy text for a doctor issue."""
    lowered = issue.lower()
    default_risk = "database behavior may be incorrect." if required else "graph, release hygiene, or evidence dispatch may be degraded."
    default_action = "inspect and fix the referenced file." if required else "inspect, repair links/metadata, or mark as intentionally unresolved."
    default_deletion = "do not batch delete; remove only one explicit file after human review."

    if ".ds_store present" in lowered:
        return (
            "macOS metadata files can pollute release checks or accidentally appear in archives.",
            "Review the exact path, remove that single `.DS_Store` file only if it is safe, then rerun `python3 tools/wiki_doctor.py`.",
            "no bulk cleanup; remove at most one explicit `.DS_Store` path per command after human review. Never use recursive, wildcard, or find-delete cleanup.",
        )
    if "local /users path" in lowered:
        return (
            "absolute local paths can leak private machine details and make the repo less portable.",
            "Replace the referenced value with a repo-relative path, a generic placeholder, or a short note explaining why it is intentionally local.",
            "do not delete the file just because it contains a local path; edit the specific reference instead.",
        )
    if "stale pdf path" in lowered or "stale full text path" in lowered or "stale wiki page path" in lowered:
        return (
            "dashboard state may no longer match the real evidence files.",
            "Check the actual file under `raw/doi_pdf/`, `raw/full_text/`, or `wiki/literature/`; update the dashboard/index to the real path or downgrade the DOI status.",
            "preserve raw evidence by default; do not delete files to make the dashboard look clean.",
        )
    if "index readable_md missing" in lowered or "index wiki_page missing" in lowered:
        return (
            "full-text dispatch can point Codex to missing inputs.",
            "Run `python3 tools/build_full_text_index.py`, then inspect any remaining missing path against real files.",
            "do not delete indexed evidence automatically; rebuild or repair the specific path.",
        )
    if "unresolved wikilink" in lowered:
        return (
            "Obsidian graph navigation may contain broken relationship edges.",
            "Fix the target page path, create the intended hub only if it is an approved topic/subtopic, or remove the specific wikilink if it is not meaningful.",
            "do not bulk-edit links; repair one page relationship at a time.",
        )
    if "missing graph links" in lowered:
        return (
            "formal wiki pages may not appear correctly in the Obsidian relationship graph.",
            "Add the standard `## Graph Links` section with explicit wikilinks that match the page evidence.",
            "no deletion needed.",
        )
    if "potential orphan page" in lowered:
        return (
            "the page may be hard to discover from the graph or index pages.",
            "Add a meaningful wikilink from an index, synthesis, project page, or related literature page, or document why the page is intentionally standalone.",
            "do not delete orphan pages automatically.",
        )

    return (default_risk, default_action, default_deletion)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    errors, warnings = wiki_doctor.collect_issues()
    out = OUT_DIR / f"repair_plan_{date.today().isoformat()}.md"
    lines = [
        "---",
        "type: maintenance",
        "status: draft",
        "source_status: personal-note",
        "reading_status: mixed",
        "review_stage: ai-extracted",
        "topics: []",
        "subtopics: []",
        "keywords: [repair_plan]",
        f"created: {date.today().isoformat()}",
        f"updated: {date.today().isoformat()}",
        "sources: []",
        "---",
        "",
        f"# Repair Plan {date.today().isoformat()}",
        "",
        "This plan is advisory. It does not delete files automatically.",
        "",
        "## Summary",
        "",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
        "## Required Fixes",
        "",
    ]
    if errors:
        for issue in errors:
            risk, action, deletion_policy = issue_guidance(issue, required=True)
            lines.extend(
                [
                    f"### {issue}",
                    "",
                    f"- Risk: {risk}",
                    f"- Suggested action: {action}",
                    f"- Deletion policy: {deletion_policy}",
                    "",
                ]
            )
    else:
        lines.append("- No required fixes found.")
        lines.append("")

    lines.extend(["## Cleanup / Review Candidates", ""])
    if warnings:
        for issue in warnings:
            risk, action, deletion_policy = issue_guidance(issue, required=False)
            lines.extend(
                [
                    f"### {issue}",
                    "",
                    f"- Risk: {risk}",
                    f"- Suggested action: {action}",
                    f"- Deletion policy: {deletion_policy}",
                    "",
                ]
            )
    else:
        lines.append("- No cleanup candidates found.")
        lines.append("")

    lines.extend(
        [
            "## Graph Links",
            "",
            "- Topics:",
            "- Subtopics:",
            "- Related literature:",
            "- Related synthesis:",
            "- Related seminars:",
            "- Related projects: [[project_synthesis/project_synthesis]]",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
