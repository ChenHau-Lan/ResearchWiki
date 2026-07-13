"""Pure, review-first helpers for RKF paper-page migration previews.

The module intentionally transforms Markdown in memory.  A later preview runner
may write copies and reports outside the canonical wiki, but no function in
this first layer receives a :class:`Workspace` or writes a live paper page.
"""

from __future__ import annotations

import difflib
import json
import re
from datetime import datetime
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .core import Workspace, first_heading, frontmatter, parse_frontmatter


CANONICAL_HEADINGS = (
    "Source Identity",
    "Reading Maturity",
    "Research Question",
    "Methods And Data",
    "Main Findings",
    "Evidence And Locators",
    "Limitations And Boundaries",
    "Questions About This Paper",
    "Future Agent Retrieval Brief",
    "Intrinsic Links",
)

LEGACY_READING_MAP = {
    "abstract-only": "abstract-read",
    "fulltext-available": "partial-fulltext",
    "first-pass-pdf-qc": "partial-fulltext",
    "ocr-qc": "partial-fulltext",
    "visual-qc": "partial-fulltext",
    "full-read": "fulltext-read",
    "synthesis-ready": "fulltext-read",
    "reproduced": "fulltext-read",
}

LEGACY_SOURCE_SECTION_TARGETS = {
    "close-reading summary": "Main Findings",
    "targeted-reading summary": "Main Findings",
    "claim-support locators": "Evidence And Locators",
    "what this supports": "Evidence And Locators",
    "what this does not support": "Limitations And Boundaries",
    "local pdf full text status": "Reading Maturity",
}
LEGACY_AUTOMATIC_ROUTES = {
    "integration notes for transport-smoke manuscript": (
        "project-or-cross-paper-context",
        "knowledge/project-synthesis",
        "proposed-review",
    ),
    "manuscript-relevant role": (
        "project-or-cross-paper-context",
        "knowledge/project-synthesis",
        "proposed-review",
    ),
}

PAPER_QUESTION_TERMS = (
    "method",
    "data",
    "result",
    "figure",
    "assumption",
    "limitation",
    "reproduc",
    "sample",
    "experiment",
    "model",
    "source",
)
BROAD_CONTEXT_TERMS = (
    "manuscript",
    "project",
    "cross-paper",
    "cross paper",
    "research direction",
    "future study",
)
SAFE_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


@dataclass(frozen=True)
class Section:
    """A level-two Markdown section with its body preserved verbatim."""

    heading: str
    content: str


@dataclass(frozen=True)
class RoutedBlock:
    """A proposal for material that should leave the paper page after review."""

    source_heading: str
    content: str
    content_hash: str
    classification: str
    proposed_target: str
    review_status: str


@dataclass(frozen=True)
class TransformResult:
    """A deterministic, non-writing paper transformation result."""

    text: str
    input_checksum: str
    output_checksum: str
    meta: dict[str, Any]
    routed_blocks: tuple[RoutedBlock, ...] = ()
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreviewPage:
    """One copied paper page in a migration-preview corpus."""

    relative_path: str
    input_checksum: str
    output_checksum: str
    routed_blocks: tuple[RoutedBlock, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True)
class PreviewReport:
    """Private, review-only artifacts created by one corpus preview."""

    run_id: str
    report_dir: Path
    manifest_hash: str
    input_count: int
    output_count: int
    diff_count: int
    routing_count: int
    unresolved_count: int
    validation_error_count: int
    ready_for_live_apply: bool


class MigrationPreviewError(RuntimeError):
    """Raised when a preview would be incomplete or unsafe to review."""


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 checksum for exact byte preservation checks."""

    return sha256(data).hexdigest()


def parse_sections(body: str) -> list[Section]:
    """Split a Markdown document into level-two sections without parsing content."""

    sections: list[Section] = []
    heading = ""
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading:
                sections.append(Section(heading=heading, content="\n".join(lines).strip()))
            heading = line[3:].strip()
            lines = []
        elif heading:
            lines.append(line)
    if heading:
        sections.append(Section(heading=heading, content="\n".join(lines).strip()))
    return sections


def map_legacy_maturity(meta: dict[str, Any]) -> dict[str, Any]:
    """Return conservative paper-v1.1 maturity fields for legacy frontmatter."""

    legacy_state = str(meta.get("reading_state") or meta.get("reading_status") or "metadata-only")
    reading_state = LEGACY_READING_MAP.get(legacy_state, legacy_state)
    if not reading_state:
        reading_state = "metadata-only"
    fulltext_status = str(meta.get("fulltext_status") or "")
    if not fulltext_status:
        fulltext_status = "fulltext-read" if reading_state == "fulltext-read" else "needs-user-pdf"
    return {
        "schema": "rkf-paper-v1.1",
        "reading_state": reading_state,
        "reading_status": reading_state,
        "fulltext_status": fulltext_status,
        "human_feedback_level": "none",
        "understanding_confidence": str(meta.get("understanding_confidence") or "low"),
        "claim_readiness": str(meta.get("claim_readiness") or "not-ready"),
        "review_stage": str(meta.get("review_stage") or "ai-extracted"),
        "evidence_boundary": str(meta.get("evidence_boundary") or "review-blocker"),
        "evidence_tier": str(meta.get("evidence_tier") or "reading-draft"),
    }


def validate_paper_v1_1(text: str) -> list[str]:
    """Validate the strict preview contract without touching a workspace."""

    meta, body = parse_frontmatter(text)
    errors: list[str] = []
    if meta.get("schema") != "rkf-paper-v1.1":
        errors.append("schema must equal rkf-paper-v1.1")
    if meta.get("type") != "paper":
        errors.append("type must equal paper")
    source_id = str(meta.get("source_id") or "")
    if not SAFE_SOURCE_ID_RE.fullmatch(source_id):
        errors.append("source_id must be a safe non-path identifier")
    if meta.get("reading_state") != meta.get("reading_status"):
        errors.append("reading_status must equal reading_state")
    for key in (
        "source_id",
        "reading_state",
        "fulltext_status",
        "human_feedback_level",
        "understanding_confidence",
        "claim_readiness",
        "reading_ledger",
    ):
        if not meta.get(key):
            errors.append(f"missing required paper field {key}")
    for heading in CANONICAL_HEADINGS:
        if f"## {heading}" not in body:
            errors.append(f"missing canonical paper section {heading}")
    return errors


def _section_map(sections: list[Section]) -> dict[str, list[Section]]:
    grouped: dict[str, list[Section]] = {}
    for section in sections:
        grouped.setdefault(section.heading.strip().lower(), []).append(section)
    return grouped


def _section_content(sections: dict[str, list[Section]], heading: str) -> str:
    """Join repeated headings so a transform cannot silently drop one block."""

    return "\n\n".join(
        section.content for section in sections.get(heading.strip().lower(), []) if section.content.strip()
    ).strip()


def _preamble_content(body: str) -> str:
    """Return substantive content between the title and first level-two section."""

    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            break
        if line.startswith("# "):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _labeled_summary(content: str) -> tuple[dict[str, list[str]], list[str]]:
    labels = {
        "research question": "Research Question",
        "method/data": "Methods And Data",
        "methods/data": "Methods And Data",
        "method": "Methods And Data",
        "methods": "Methods And Data",
        "key findings": "Main Findings",
        "finding": "Main Findings",
        "findings": "Main Findings",
        "limitations": "Limitations And Boundaries",
        "limitation": "Limitations And Boundaries",
    }
    extracted: dict[str, list[str]] = {heading: [] for heading in CANONICAL_HEADINGS}
    unmatched: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        probe = stripped[2:] if stripped.startswith("- ") else stripped
        if ":" not in probe:
            if stripped:
                unmatched.append(line)
            continue
        label, value = probe.split(":", 1)
        heading = labels.get(label.strip().lower())
        if heading:
            extracted[heading].append(f"- {value.strip()}" if value.strip() else "- Not recorded yet.")
        else:
            unmatched.append(line)
    return extracted, unmatched


def _content_or_placeholder(lines: list[str], placeholder: str = "- Not recorded yet.") -> str:
    return "\n".join(lines).strip() or placeholder


def _has_substantive_content(content: str) -> bool:
    for line in content.splitlines():
        value = line.strip().lstrip("- ").strip()
        if not value:
            continue
        if value.endswith(":"):
            continue
        if value.lower() in {"not recorded yet.", "not recorded yet", "tbd"}:
            continue
        if ":" in value:
            _label, remainder = value.split(":", 1)
            if not remainder.strip():
                continue
        return True
    return False


def _question_is_paper_specific(content: str) -> bool:
    lowered = content.lower()
    if any(term in lowered for term in BROAD_CONTEXT_TERMS):
        return False
    return any(term in lowered for term in PAPER_QUESTION_TERMS)


def route_nonpaper_block(section: Section, *, page_id: str) -> RoutedBlock | None:
    """Classify a non-paper section without creating its destination object."""

    del page_id
    if not _has_substantive_content(section.content):
        return None
    heading = section.heading.strip()
    lowered = heading.lower()
    content_hash = sha256_bytes(section.content.encode("utf-8"))
    automatic = LEGACY_AUTOMATIC_ROUTES.get(lowered)
    if automatic is not None:
        classification, proposed_target, review_status = automatic
        return RoutedBlock(heading, section.content, content_hash, classification, proposed_target, review_status)
    if lowered == "reader notes":
        return RoutedBlock(
            heading, section.content, content_hash, "reader-interpretation", "state/reading", "proposed-ledger-entry"
        )
    if lowered == "ai/agent notes":
        return RoutedBlock(
            heading, section.content, content_hash, "agent-reading-note", "state/reading", "proposed-ledger-entry"
        )
    if lowered == "questions and feedback":
        if _question_is_paper_specific(section.content):
            return None
        return RoutedBlock(
            heading, section.content, content_hash, "broad-question", "knowledge/questions", "needs-human-routing"
        )
    if lowered == "claims to promote":
        return RoutedBlock(heading, section.content, content_hash, "claim-candidate", "knowledge/claims", "proposed-review")
    if lowered == "graph links":
        return RoutedBlock(
            heading, section.content, content_hash, "outgoing-context-links", "knowledge/topics", "proposed-review"
        )
    if "project" in lowered or "manuscript" in lowered or "cross" in lowered:
        return RoutedBlock(
            heading, section.content, content_hash, "project-or-cross-paper-context", "knowledge/inbox", "needs-human-routing"
        )
    return RoutedBlock(
        heading, section.content, content_hash, "unclassified-legacy-section", "knowledge/inbox", "needs-human-routing"
    )


def _canonical_meta(meta: dict[str, Any]) -> dict[str, Any]:
    mapped = map_legacy_maturity(meta)
    source_id = str(meta.get("source_id") or "")
    ordered: dict[str, Any] = {
        "schema": mapped["schema"],
        "type": "paper",
        "status": str(meta.get("status") or "draft"),
        "source_id": source_id,
        "source_status": str(meta.get("source_status") or "paper_draft"),
        "reading_state": mapped["reading_state"],
        "reading_status": mapped["reading_status"],
        "fulltext_status": mapped["fulltext_status"],
        "human_feedback_level": mapped["human_feedback_level"],
        "understanding_confidence": mapped["understanding_confidence"],
        "claim_readiness": mapped["claim_readiness"],
        "review_stage": mapped["review_stage"],
        "evidence_boundary": mapped["evidence_boundary"],
        "evidence_tier": mapped["evidence_tier"],
        "evidence_ids": meta.get("evidence_ids") or [],
        "reading_ledger": str(meta.get("reading_ledger") or f"state/reading/{source_id}.json"),
        "topics": meta.get("topics") or [],
        "created": str(meta.get("created") or ""),
        "updated": str(meta.get("updated") or ""),
        "sources": meta.get("sources") or [],
    }
    for key, value in meta.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def transform_paper_markdown(text: str, *, page_id: str) -> TransformResult:
    """Convert a legacy paper draft into the paper-centered v1.1 section shape.

    This initial transform only rehomes clearly labeled source-grounded summary
    content.  Material requiring a destination decision is added in the next
    conservative routing step rather than discarded here.
    """

    meta, body = parse_frontmatter(text)
    parsed_sections = parse_sections(body)
    sections = _section_map(parsed_sections)
    labeled, unmatched = _labeled_summary(_section_content(sections, "Source-Grounded Summary"))
    title = first_heading(body, fallback=str(meta.get("source_id") or "Paper"))
    routed: list[RoutedBlock] = []
    preamble = _preamble_content(body)
    if _has_substantive_content(preamble):
        routed.append(
            RoutedBlock(
                "Preamble",
                preamble,
                sha256_bytes(preamble.encode("utf-8")),
                "unclassified-preamble",
                "knowledge/inbox",
                "needs-human-routing",
            )
        )
    question_routes = {
        id(section): route_nonpaper_block(section, page_id=page_id)
        for section in sections.get("questions and feedback", [])
    }
    known_legacy = {
        "source identity",
        "reading maturity",
        "source-grounded summary",
        "extracted evidence and locators",
        "future agent retrieval brief",
        *LEGACY_SOURCE_SECTION_TARGETS,
    }
    canonical_names = {heading.lower() for heading in CANONICAL_HEADINGS}
    for section in parsed_sections:
        lowered = section.heading.lower()
        if lowered in canonical_names or lowered in known_legacy:
            continue
        if lowered == "questions and feedback":
            route = question_routes[id(section)]
        else:
            route = route_nonpaper_block(section, page_id=page_id)
        if route is not None:
            routed.append(route)

    def existing(heading: str) -> str:
        return _section_content(sections, heading)

    def preferred(heading: str, fallback: str) -> str:
        return existing(heading) or fallback

    def with_legacy_blocks(heading: str, content: str) -> str:
        blocks = []
        for legacy_heading, target_heading in LEGACY_SOURCE_SECTION_TARGETS.items():
            if target_heading != heading:
                continue
            for section in sections.get(legacy_heading, []):
                if _has_substantive_content(section.content):
                    blocks.append(f"### {section.heading}\n\n{section.content}")
        if not blocks:
            return content
        if content.strip() in {"", "- Not recorded yet."}:
            return "\n\n".join(blocks)
        return content.rstrip() + "\n\n" + "\n\n".join(blocks)

    paper_specific_questions = "\n\n".join(
        section.content
        for section in sections.get("questions and feedback", [])
        if question_routes[id(section)] is None and section.content.strip()
    ).strip()
    questions_content = existing("Questions About This Paper") or paper_specific_questions
    canonical = {
        "Source Identity": existing("Source Identity"),
        "Reading Maturity": with_legacy_blocks("Reading Maturity", existing("Reading Maturity")),
        "Research Question": preferred("Research Question", _content_or_placeholder(labeled["Research Question"])),
        "Methods And Data": preferred("Methods And Data", _content_or_placeholder(labeled["Methods And Data"])),
        "Main Findings": with_legacy_blocks(
            "Main Findings",
            preferred("Main Findings", _content_or_placeholder(labeled["Main Findings"] + unmatched)),
        ),
        "Evidence And Locators": with_legacy_blocks(
            "Evidence And Locators",
            preferred("Evidence And Locators", existing("Extracted Evidence And Locators")),
        ),
        "Limitations And Boundaries": with_legacy_blocks(
            "Limitations And Boundaries",
            preferred("Limitations And Boundaries", _content_or_placeholder(labeled["Limitations And Boundaries"])),
        ),
        "Questions About This Paper": questions_content or "- Not recorded yet.",
        "Future Agent Retrieval Brief": existing("Future Agent Retrieval Brief"),
        "Intrinsic Links": existing("Intrinsic Links") or "- Not recorded yet.",
    }
    rendered_sections = []
    for heading in CANONICAL_HEADINGS:
        rendered_sections.append(f"## {heading}\n\n{_content_or_placeholder([canonical[heading]])}")
    output = frontmatter(_canonical_meta(meta)) + f"# {title}\n\n" + "\n\n".join(rendered_sections) + "\n"
    issues = tuple(validate_paper_v1_1(output))
    return TransformResult(
        text=output,
        input_checksum=sha256_bytes(text.encode("utf-8")),
        output_checksum=sha256_bytes(output.encode("utf-8")),
        meta=_canonical_meta(meta),
        routed_blocks=tuple(routed),
        issues=issues,
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_preview_ledger_filename(source_id: str) -> str:
    """Return a report-local ledger filename without trusting source metadata as a path."""

    if SAFE_SOURCE_ID_RE.fullmatch(source_id):
        return f"{source_id}.json"
    return f"unsafe-source-{sha256_bytes(source_id.encode('utf-8'))}.json"


def _safe_child(root: Path, name: str) -> Path:
    """Resolve one generated report child and reject traversal or absolute escapes."""

    candidate = (root / name).resolve()
    if not _is_within(candidate, root.resolve()):
        raise MigrationPreviewError("preview output path escaped its private report root")
    return candidate


def _validate_report_root(ws: Workspace, report_root: Path) -> Path:
    resolved = report_root.expanduser().resolve()
    private_root = (ws.root / ".rkf_private").resolve()
    if not _is_within(private_root, ws.root.resolve()):
        raise MigrationPreviewError("migration private report root must remain inside the local workspace")
    if not _is_within(resolved, private_root):
        raise MigrationPreviewError("migration report root must be inside local .rkf_private")
    if _is_within(resolved, ws.paths.wiki_root.resolve()) or _is_within(resolved, ws.paths.raw_root.resolve()):
        raise MigrationPreviewError("migration report root must not be inside canonical wiki_root or raw_root")
    return resolved


def _paper_paths(ws: Workspace) -> list[Path]:
    root = ws.paths.knowledge / "papers"
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def _snapshot(paths: list[Path]) -> dict[Path, str]:
    return {path: sha256_bytes(path.read_bytes()) for path in paths}


def _verify_unchanged(snapshot: dict[Path, str]) -> None:
    drifted = [path.name for path, checksum in snapshot.items() if not path.exists() or sha256_bytes(path.read_bytes()) != checksum]
    if drifted:
        raise MigrationPreviewError(f"live paper inputs changed during preview: {', '.join(sorted(drifted))}")


def _route_payload(block: RoutedBlock) -> dict[str, str]:
    return {
        "source_heading": block.source_heading,
        "content": block.content,
        "content_hash": block.content_hash,
        "classification": block.classification,
        "proposed_target": block.proposed_target,
        "review_status": block.review_status,
    }


def _preview_ledger(
    result: TransformResult,
    *,
    source_id: str,
    relative_path: str,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    """Construct a copied migration ledger; never read or write the live ledger."""

    ledger = json.loads(json.dumps(existing)) if existing is not None else {}
    events = ledger.get("events", [])
    if not isinstance(events, list):
        raise MigrationPreviewError(f"existing reading ledger for {source_id} has non-list events")
    ledger.update(
        {
            "schema": "rkf-reading-ledger-v1.1",
            "source_id": source_id,
            "knowledge_path": relative_path,
            "events": events,
            "created": str(ledger.get("created") or "preview-only"),
            "updated": "preview-only",
        }
    )
    events.append(
        {
            "created": "preview-only",
            "type": "migration",
            "actor": "codex",
            "summary": "Preview-only RKF paper migration; Promotion: none.",
            "public_safe": True,
            "details": {
                "transform": "rkf-paper-migration-v1.1-preview",
                "input_checksum": result.input_checksum,
                "output_checksum": result.output_checksum,
                "promotion": "none",
            },
        }
    )
    return ledger


def _existing_ledger(path: Path, *, source_id: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MigrationPreviewError(f"cannot preserve existing reading ledger for {source_id}") from error
    if not isinstance(payload, dict):
        raise MigrationPreviewError(f"existing reading ledger for {source_id} is not an object")
    return payload


def _stable_manifest_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def run_preview(
    ws: Workspace,
    *,
    report_root: Path,
    expected_count: int | None = 57,
) -> PreviewReport:
    """Preview paper-page migration using copied files outside canonical storage.

    The report root must be a local ignored directory below the checkout's
    `.rkf_private`.  The function only reads configured wiki inputs and emits
    copied Markdown, ledgers, diffs, and a manifest under that report root.
    """

    safe_report_root = _validate_report_root(ws, report_root)
    inputs = _paper_paths(ws)
    if expected_count is not None and len(inputs) != expected_count:
        raise MigrationPreviewError(
            f"expected {expected_count} paper pages, found {len(inputs)}; refusing incomplete golden preview"
        )
    before = _snapshot(inputs)
    paper_root = ws.paths.knowledge / "papers"
    pages: list[PreviewPage] = []
    transformed: list[tuple[Path, str, bytes, str, TransformResult]] = []
    for path in inputs:
        relative_path = path.relative_to(paper_root).as_posix()
        input_bytes = path.read_bytes()
        text = input_bytes.decode("utf-8")
        result = transform_paper_markdown(text, page_id=f"papers/{path.relative_to(paper_root).with_suffix('').as_posix()}")
        transformed.append((path, relative_path, input_bytes, text, result))
        pages.append(
            PreviewPage(
                relative_path=relative_path,
                input_checksum=result.input_checksum,
                output_checksum=result.output_checksum,
                routed_blocks=result.routed_blocks,
                issues=result.issues,
            )
        )
    _verify_unchanged(before)
    manifest_pages = [
        {
            "source_page": f"knowledge/papers/{page.relative_path}",
            "input_checksum": page.input_checksum,
            "output_checksum": page.output_checksum,
            "routed_blocks": [_route_payload(block) for block in page.routed_blocks],
            "issues": list(page.issues),
        }
        for page in pages
    ]
    unresolved_count = sum(
        1
        for page in pages
        for block in page.routed_blocks
        if block.review_status == "needs-human-routing"
    )
    validation_error_count = sum(len(page.issues) for page in pages)
    manifest_core = {
        "schema": "rkf-paper-migration-preview-v1",
        "transform": "rkf-paper-migration-v1.1-preview",
        "expected_count": expected_count,
        "input_count": len(inputs),
        "output_count": len(transformed),
        "diff_count": len(transformed),
        "routing_count": sum(len(page.routed_blocks) for page in pages),
        "unresolved_count": unresolved_count,
        "validation_error_count": validation_error_count,
        "ready_for_live_apply": (
            unresolved_count == 0 and validation_error_count == 0 and len(inputs) == len(transformed)
        ),
        "pages": manifest_pages,
    }
    manifest_hash = _stable_manifest_hash(manifest_core)
    run_id = f"preview-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{manifest_hash[:12]}"
    report_dir = safe_report_root / run_id
    if report_dir.exists():
        raise MigrationPreviewError("preview report directory already exists; retry to preserve immutable review artifacts")
    transformed_root = report_dir / "workspace" / "knowledge" / "papers"
    copied_input_root = report_dir / "input" / "knowledge" / "papers"
    ledgers_root = report_dir / "workspace" / "state" / "reading"
    diffs_root = report_dir / "diffs"
    transformed_root.mkdir(parents=True)
    copied_input_root.mkdir(parents=True)
    ledgers_root.mkdir(parents=True)
    diffs_root.mkdir(parents=True)
    for path, relative_path, input_bytes, input_text, result in transformed:
        input_copy_path = copied_input_root / relative_path
        input_copy_path.parent.mkdir(parents=True, exist_ok=True)
        input_copy_path.write_bytes(input_bytes)
        output_path = transformed_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.text, encoding="utf-8")
        source_id = str(result.meta.get("source_id") or path.stem)
        ledger_path = _safe_child(ledgers_root, _safe_preview_ledger_filename(source_id))
        existing_ledger = None
        if SAFE_SOURCE_ID_RE.fullmatch(source_id):
            live_ledger_path = _safe_child(ws.paths.reading, f"{source_id}.json")
            existing_ledger = _existing_ledger(live_ledger_path, source_id=source_id)
        ledger_path.write_text(
            json.dumps(
                _preview_ledger(
                    result,
                    source_id=source_id,
                    relative_path=f"knowledge/papers/{relative_path}",
                    existing=existing_ledger,
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        diff = "".join(
            difflib.unified_diff(
                input_text.splitlines(keepends=True),
                result.text.splitlines(keepends=True),
                fromfile=f"live/knowledge/papers/{relative_path}",
                tofile=f"preview/knowledge/papers/{relative_path}",
            )
        )
        diff_path = diffs_root / f"{relative_path}.diff"
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(diff, encoding="utf-8")
    _verify_unchanged(before)
    manifest = {**manifest_core, "manifest_hash": manifest_hash}
    (report_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "rkf-paper-migration-preview-summary-v1",
        "run_id": run_id,
        "manifest_hash": manifest_hash,
        "input_count": len(inputs),
        "output_count": len(transformed),
        "diff_count": len(transformed),
        "routing_count": manifest_core["routing_count"],
        "unresolved_count": unresolved_count,
        "validation_error_count": validation_error_count,
        "ready_for_live_apply": manifest_core["ready_for_live_apply"],
        "promotion": "none",
    }
    (report_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return PreviewReport(
        run_id=run_id,
        report_dir=report_dir,
        manifest_hash=manifest_hash,
        input_count=len(inputs),
        output_count=len(transformed),
        diff_count=len(transformed),
        routing_count=int(manifest_core["routing_count"]),
        unresolved_count=unresolved_count,
        validation_error_count=validation_error_count,
        ready_for_live_apply=bool(manifest_core["ready_for_live_apply"]),
    )
