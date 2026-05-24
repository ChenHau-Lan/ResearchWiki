#!/usr/bin/env python3
"""ResearchWiki command line router.

This tool handles deterministic repository maintenance. It deliberately keeps
paper interpretation and synthesis in Codex/skill space.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None


ROOT = Path(os.environ.get("RESEARCHWIKI_ROOT", Path(__file__).resolve().parents[1])).resolve()
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
TOPIC_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | PDF | Full Text |"
BOARD_SEPARATOR = "|---|---|---|---|---|---|"
NOTES_HEADER = "| DOI | Next Action | Updated | Note |"
NOTES_SEPARATOR = "|---|---|---|---|"
STATUSES = {
    "new",
    "metadata_ok",
    "candidate_found",
    "pdf_checkpoint_required",
    "pdf_downloaded",
    "full_text_needed",
    "full_text_done",
    "wiki_done",
    "abstract_only",
    "blocked",
}
QC_DONE = {"codex_qc_done", "human_qc_done", "abstract_only"}
PENDING_MARKERS = {
    "machine_extracted_needs_codex_qc",
    "needs_codex_qc",
    "pending_codex_qc",
    "needs-human-review",
}


def repo_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def today() -> str:
    return date.today().isoformat()


def now_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slugify(value: str, max_len: int = 80) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return (value[:max_len].strip("_") or "item")


def normalize_doi(value: str) -> str:
    value = value.strip().rstrip(".,;")
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.lower()


def extract_doi(value: str) -> str:
    match = DOI_RE.search(value)
    return normalize_doi(match.group(0)) if match else ""


def source_key(value: str) -> str:
    doi = extract_doi(value)
    if doi:
        return slugify(doi.replace("/", "_"))
    return slugify(value)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[4:end].strip().splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta


def load_config() -> dict[str, object]:
    config_path = repo_path("researchwiki.config.toml")
    if not config_path.exists() or tomllib is None:
        return {}
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def expand_config_path(value: str | None, fallback: Path) -> Path:
    if not value:
        return fallback
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def storage_path(name: str, fallback: Path) -> Path:
    config = load_config()
    storage = config.get("storage", {}) if isinstance(config, dict) else {}
    value = storage.get(name) if isinstance(storage, dict) else None
    return expand_config_path(value if isinstance(value, str) else None, fallback)


def ensure_raw_files() -> None:
    repo_path("raw", "doi_pdf").mkdir(parents=True, exist_ok=True)
    repo_path("raw", "full_text").mkdir(parents=True, exist_ok=True)
    repo_path("raw", "files").mkdir(parents=True, exist_ok=True)
    repo_path("raw", "staging", "extracted_text").mkdir(parents=True, exist_ok=True)
    sources = repo_path("raw", "paper_sources.md")
    if not sources.exists():
        write_text(
            sources,
            "# Paper Sources\n\n"
            "Paste paper source pointers in the block below, one per line.\n\n"
            "## Add Sources Here\n\n```text\n\n```\n",
        )
    dashboard = repo_path("raw", "doi_dashboard.md")
    if not dashboard.exists():
        write_text(
            dashboard,
            "# DOI Dashboard\n\n"
            "This board tracks where each resolved DOI is in the paper-source ingest process.\n\n"
            "## DOI Status Board\n\n"
            f"{BOARD_HEADER}\n{BOARD_SEPARATOR}\n\n"
            "## DOI Notes\n\n"
            f"{NOTES_HEADER}\n{NOTES_SEPARATOR}\n\n"
            "## Status Legend\n\n"
            + "\n".join(f"- `{status}`" for status in sorted(STATUSES))
            + "\n",
        )
    for name, body in {
        "raw/full_text_index.md": "# full_text Index\n\n## Entries\n\n| Citation Key | DOI | Dispatch Status | Wiki Page | Full Text MD | Optional Translation MD |\n|---|---|---|---|---|---|\n",
        "raw/full_text_index.json": '{\n  "schema": "full-text-index-v2",\n  "summary": {},\n  "entries": [],\n  "all_text_sources": []\n}\n',
    }.items():
        path = repo_path(*name.split("/"))
        if not path.exists():
            write_text(path, body)


def split_row(line: str) -> list[str]:
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return []
    return [part.strip().replace(r"\|", "|") for part in line.strip("|").split("|")]


def parse_dashboard() -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    ensure_raw_files()
    text = read_text(repo_path("raw", "doi_dashboard.md"))
    rows: list[dict[str, str]] = []
    notes: dict[str, dict[str, str]] = {}
    section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == BOARD_HEADER:
            section = "board"
            continue
        if stripped == NOTES_HEADER:
            section = "notes"
            continue
        if stripped.startswith("## ") and stripped not in {BOARD_HEADER, NOTES_HEADER}:
            section = ""
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        parts = split_row(line)
        if section == "board" and len(parts) == 6:
            rows.append(
                {
                    "key": parts[0],
                    "journal": parts[1],
                    "doi": normalize_doi(parts[2]) if parts[2] else "",
                    "status": parts[3],
                    "pdf": parts[4],
                    "full_text": parts[5],
                }
            )
        elif section == "notes" and len(parts) == 4:
            notes[normalize_doi(parts[0])] = {
                "action": parts[1],
                "updated": parts[2],
                "note": parts[3],
            }
    return rows, notes


def render_dashboard(rows: list[dict[str, str]], notes: dict[str, dict[str, str]]) -> str:
    rows = sorted(rows, key=lambda row: (row.get("key", ""), row.get("doi", "")))
    board_lines = [BOARD_HEADER, BOARD_SEPARATOR]
    for row in rows:
        board_lines.append(
            f"| {row.get('key', '')} | {row.get('journal', '')} | {row.get('doi', '')} | "
            f"{row.get('status', 'new')} | {row.get('pdf', '')} | {row.get('full_text', '')} |"
        )
    note_lines = [NOTES_HEADER, NOTES_SEPARATOR]
    for doi, note in sorted(notes.items()):
        note_lines.append(
            f"| {doi} | {note.get('action', '')} | {note.get('updated', '')} | {note.get('note', '')} |"
        )
    legend = "\n".join(f"- `{status}`" for status in sorted(STATUSES))
    return (
        "# DOI Dashboard\n\n"
        "This board tracks where each resolved DOI is in the paper-source ingest process.\n\n"
        "## DOI Status Board\n\n"
        + "\n".join(board_lines)
        + "\n\n## DOI Notes\n\n"
        + "\n".join(note_lines)
        + "\n\n## Status Legend\n\n"
        + legend
        + "\n"
    )


def update_dashboard(
    value: str,
    status: str,
    *,
    key: str | None = None,
    journal: str = "",
    pdf: bool | None = None,
    full_text: bool | None = None,
    action: str = "",
    note: str = "",
) -> None:
    if status not in STATUSES:
        raise SystemExit(f"invalid status: {status}")
    rows, notes = parse_dashboard()
    doi = extract_doi(value) or normalize_doi(value) if "/" in value or value.startswith("10.") else value
    key = key or source_key(value)
    existing = None
    for row in rows:
        if row.get("doi") == doi or row.get("key") == key:
            existing = row
            break
    if existing is None:
        existing = {"key": key, "journal": journal, "doi": doi, "status": status, "pdf": "", "full_text": ""}
        rows.append(existing)
    existing["key"] = existing.get("key") or key
    existing["journal"] = journal or existing.get("journal", "")
    existing["doi"] = doi or existing.get("doi", "")
    existing["status"] = status
    if pdf is not None:
        existing["pdf"] = "x" if pdf else ""
    if full_text is not None:
        existing["full_text"] = "x" if full_text else ""
    if action or note:
        notes[doi or key] = {"action": action, "updated": today(), "note": note}
    write_text(repo_path("raw", "doi_dashboard.md"), render_dashboard(rows, notes))


def append_source(pointer: str, note: str = "") -> None:
    ensure_raw_files()
    path = repo_path("raw", "paper_sources.md")
    text = read_text(path)
    entry = pointer.strip()
    if note:
        entry = f"{entry} # {note.strip()}"
    if entry in text or pointer.strip() in text:
        return
    marker = "## Add Sources Here"
    if marker not in text:
        text = text.rstrip() + f"\n\n{marker}\n\n```text\n\n```\n"
    fence_start = text.find("```text", text.find(marker))
    fence_end = text.find("```", fence_start + 7)
    if fence_start == -1 or fence_end == -1:
        text = text.rstrip() + f"\n\n```text\n{entry}\n```\n"
    else:
        before = text[:fence_end].rstrip()
        after = text[fence_end:]
        text = before + "\n" + entry + "\n" + after
    write_text(path, text)


def cmd_source_add(args: argparse.Namespace) -> int:
    append_source(args.pointer, args.note or "")
    key = args.key or source_key(args.pointer)
    doi = extract_doi(args.pointer)
    update_dashboard(
        doi or args.pointer,
        args.status,
        key=key,
        action="resolve_metadata" if args.status == "new" else "",
        note="added by rw.py source add",
    )
    print(f"added source: {args.pointer}")
    print(f"paper_file_key: {key}")
    return 0


def openalex_search(query: str, limit: int) -> list[dict[str, str]]:
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"search": query, "per-page": str(limit)})
    with urllib.request.urlopen(url, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    candidates = []
    for item in data.get("results", []):
        doi = normalize_doi(item.get("doi", "").replace("https://doi.org/", "")) if item.get("doi") else ""
        candidates.append(
            {
                "title": item.get("title") or "",
                "doi": doi,
                "year": str(item.get("publication_year") or ""),
                "source": (item.get("primary_location") or {}).get("source", {}).get("display_name", ""),
                "url": (item.get("primary_location") or {}).get("landing_page_url", ""),
            }
        )
    return candidates


def cmd_source_search(args: argparse.Namespace) -> int:
    run_dir = repo_path("maintenance", "search_runs", f"{now_slug()}_{slugify(args.query, 40)}")
    run_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, str]]
    if args.live:
        try:
            candidates = openalex_search(args.query, args.limit)
        except Exception as exc:  # noqa: BLE001 - report and preserve run
            candidates = []
            write_text(run_dir / "error.md", f"# Search Error\n\n{type(exc).__name__}: {exc}\n")
    else:
        candidates = []
    record = {
        "schema": "researchwiki-search-run-v1",
        "query": args.query,
        "topic_id": args.topic_id or "",
        "live": bool(args.live),
        "generated": today(),
        "candidates": candidates,
    }
    write_text(run_dir / "candidates.json", json.dumps(record, indent=2, sort_keys=True) + "\n")
    write_text(
        run_dir / "search_plan.md",
        "# Literature Search Run\n\n"
        f"- Query: {args.query}\n"
        f"- Topic ID: {args.topic_id or ''}\n"
        f"- Live search: {args.live}\n"
        f"- Candidates: {len(candidates)}\n\n"
        "## Gate\n\nCandidates are not evidence. Resolve and checkpoint before acquisition.\n",
    )
    if candidates:
        for candidate in candidates:
            if candidate.get("doi"):
                update_dashboard(
                    candidate["doi"],
                    "candidate_found",
                    key=source_key(candidate["doi"]),
                    journal=candidate.get("source", ""),
                    action="human_review_candidate",
                    note="found by rw.py source search",
                )
    print(f"wrote {run_dir.relative_to(ROOT)}")
    print(f"candidates: {len(candidates)}")
    return 0


def cmd_source_resolve(args: argparse.Namespace) -> int:
    ensure_raw_files()
    value = args.pointer
    doi = extract_doi(value)
    status = "metadata_ok" if doi else "candidate_found"
    update_dashboard(
        doi or value,
        status,
        key=args.key or source_key(value),
        action="acquire_or_checkpoint",
        note="resolved source identity; not full text evidence",
    )
    print(f"resolved: {doi or value}")
    print(f"status: {status}")
    return 0


def acquisition_checkpoint(identifier: str, key: str, route: str, screenshot: str = "") -> Path:
    path = repo_path("maintenance", "acquisition_checkpoints", f"{key}.md")
    write_text(
        path,
        "# Acquisition Checkpoint\n\n"
        f"- Identifier: {identifier}\n"
        f"- Paper file key: {key}\n"
        f"- Candidate route: {route}\n"
        f"- Screenshot: {screenshot}\n"
        f"- Decision: pending\n\n"
        "## Human Checks\n\n"
        "- Is this source legal/authorized for your access?\n"
        "- Does the PDF match the intended DOI/article?\n"
        "- Is this full text, not only metadata or abstract?\n"
        "- Should acquisition proceed with `--checkpoint approved`?\n",
    )
    return path


def cmd_source_acquire(args: argparse.Namespace) -> int:
    key = args.key or source_key(args.identifier)
    route = args.pdf or args.url or "candidate route not supplied"
    if args.checkpoint != "approved":
        checkpoint = acquisition_checkpoint(args.identifier, key, route, args.screenshot or "")
        update_dashboard(
            args.identifier,
            "pdf_checkpoint_required",
            key=key,
            action="human_pdf_checkpoint",
            note=f"review {checkpoint.relative_to(ROOT)}",
        )
        print(f"checkpoint required: {checkpoint.relative_to(ROOT)}")
        return 0

    pdf_root = storage_path("doi_pdf_dir", repo_path("raw", "doi_pdf"))
    pdf_root.mkdir(parents=True, exist_ok=True)
    dest = pdf_root / f"{key}.pdf"
    if args.pdf:
        source = Path(args.pdf).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"PDF not found: {source}")
        shutil.copy2(source, dest)
    elif args.url and args.download:
        with urllib.request.urlopen(args.url, timeout=30) as response:
            dest.write_bytes(response.read())
    else:
        raise SystemExit("approved acquisition requires --pdf or --url --download")
    update_dashboard(
        args.identifier,
        "pdf_downloaded",
        key=key,
        pdf=True,
        action="codex_or_human_full_text_qc",
        note=f"approved PDF stored at {dest}",
    )
    print(f"stored PDF: {dest}")
    return 0


def wrap_qced_text(text: str, key: str, args: argparse.Namespace) -> str:
    if text.startswith("---\n"):
        return text
    title = args.title or key.replace("_", " ")
    doi = extract_doi(args.identifier or "")
    status = "abstract_only" if args.abstract_only else "codex_qc_done"
    reading_status = "abstract-only" if args.abstract_only else "full-read"
    return (
        "---\n"
        f"title: \"{title}\"\n"
        f"doi: {doi}\n"
        f"paper_file_key: {key}\n"
        f"extraction_status: {status}\n"
        f"qc_status: {status}\n"
        f"readability_status: {'abstract-only' if args.abstract_only else 'readable'}\n"
        "equation_quality: not_applicable\n"
        "table_quality: not_applicable\n"
        f"reading_status: {reading_status}\n"
        f"created: {today()}\n"
        f"updated: {today()}\n"
        "---\n\n"
        + text.rstrip()
        + "\n"
    )


def cmd_source_qc(args: argparse.Namespace) -> int:
    key = args.key or source_key(args.identifier or args.full_text or "source")
    if args.abstract_only:
        text = args.abstract or "# Abstract-only Source\n\nNo complete full text was available.\n"
    else:
        if not args.full_text:
            raise SystemExit("source qc requires --full-text or --abstract-only")
        source = Path(args.full_text).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"full text file not found: {source}")
        text = read_text(source)
        lowered = text.lower()
        if any(marker in lowered for marker in PENDING_MARKERS):
            raise SystemExit("refusing to write un-QCed extraction to raw/full_text")
    final = wrap_qced_text(text, key, args)
    dest = repo_path("raw", "full_text", f"{key}.md")
    write_text(dest, final)
    status = "abstract_only" if args.abstract_only else "full_text_done"
    update_dashboard(
        args.identifier or key,
        status,
        key=key,
        full_text=not args.abstract_only,
        action="paper_ingest" if not args.abstract_only else "abstract_limited_ingest_optional",
        note=f"QCed text stored at {dest.relative_to(ROOT)}",
    )
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


def cmd_source_dashboard(args: argparse.Namespace) -> int:
    ensure_raw_files()
    if args.rebuild_index:
        subprocess.run([sys.executable, str(repo_path("tools", "build_full_text_index.py"))], check=True)
    print(read_text(repo_path("raw", "doi_dashboard.md")))
    return 0


def frontmatter_value(meta: dict[str, str], key: str, fallback: str = "") -> str:
    return meta.get(key, fallback).strip()


def cmd_paper_ingest(args: argparse.Namespace) -> int:
    source = Path(args.source)
    if not source.exists():
        source = repo_path("raw", "full_text", f"{args.source}.md")
    if not source.exists():
        raise SystemExit(f"full text source not found: {args.source}")
    text = read_text(source)
    meta = parse_frontmatter(text)
    qc_status = frontmatter_value(meta, "qc_status")
    extraction_status = frontmatter_value(meta, "extraction_status")
    is_abstract_only = qc_status == "abstract_only" or extraction_status == "abstract_only"
    if is_abstract_only and not args.allow_abstract_only:
        raise SystemExit("abstract-only sources require --allow-abstract-only")
    if qc_status not in QC_DONE and extraction_status not in QC_DONE:
        raise SystemExit("refusing paper ingest: source is not QCed full text")
    key = args.key or frontmatter_value(meta, "paper_file_key", source.stem)
    title = frontmatter_value(meta, "title", key.replace("_", " ").title())
    doi = frontmatter_value(meta, "doi", extract_doi(text))
    slug = slugify(args.slug or key)
    reading_status = "abstract-only" if is_abstract_only else "full-read"
    dest = repo_path("wiki", "literature", f"{slug}.md")
    page = f"""---
type: paper
status: draft
source_status: peer-reviewed
reading_status: {reading_status}
review_stage: ai-extracted
confidence: not-applicable
evidence_scope: single-source
evidence_tier: {'abstract-only' if is_abstract_only else 'peer-reviewed'}
claim_status: source-report
counter_evidence: not-applicable
source_hash:
source_lines: []
provenance_state: extracted
review_queue: false
review_priority: low
last_reviewed:
review_due:
doi: {doi}
citation_key: {key}
paper_file_key: {key}
aliases: []
supersedes: []
superseded_by: []
topics: []
subtopics: []
keywords: []
created: {today()}
updated: {today()}
sources:
  - {source.relative_to(ROOT) if source.is_relative_to(ROOT) else source}
---

# {title}

## Metadata

- Title: {title}
- Authors:
- Venue/Year:
- DOI: {doi}
- Reading Status: {reading_status}
- Full Text: {source.relative_to(ROOT) if source.is_relative_to(ROOT) else source}
- PDF:

## Research Question

TBD from QCed reading.

## Method

TBD from QCed reading.

## Key Findings

- Finding:
  - Evidence:
  - Caveat:

## Important Evidence

- Figure/table/result:
  - Why it matters:
  - Caveat:

## Limitations

- Limitation:

## Citable Claims

- Claim:
  - Evidence:
  - Use in:

## Notes

- Paper-specific note:

## Knowledge Impact

- What this paper changes:
  - Evidence tier:
  - Confidence:
  - Counter-evidence or caveat:
- Existing synthesis or concept possibly affected:

## Fan-out Candidates

- Candidate concept update:
  - Target:
  - Reason:
  - Review needed:
- Candidate synthesis update:
  - Target:
  - Supported or challenged claim:
  - Review needed:
- Supersession candidate:
  - Older page or claim:
  - Why this paper may supersede it:
  - Review needed:

## Graph Links

- Topics:
- Subtopics:
- Related literature:
- Related concepts:
- Related synthesis:
- Related seminars:
- Related projects:
"""
    write_text(dest, page)
    update_dashboard(
        doi or key,
        "wiki_done",
        key=key,
        full_text=not is_abstract_only,
        action="fanout_review",
        note=f"paper page created at {dest.relative_to(ROOT)}",
    )
    print(f"wrote {dest.relative_to(ROOT)}")
    return 0


def topic_registry() -> Path:
    return repo_path("wiki", "topics", "topic_registry.md")


def parse_topic_rows() -> list[dict[str, str]]:
    path = topic_registry()
    if not path.exists():
        return []
    rows = []
    in_table = False
    for line in read_text(path).splitlines():
        if line.startswith("| Topic ID |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            parts = split_row(line)
            if len(parts) == 9:
                rows.append(
                    {
                        "id": parts[0],
                        "name": parts[1],
                        "aliases": parts[2],
                        "scope": parts[3],
                        "include": parts[4],
                        "exclude": parts[5],
                        "search": parts[6],
                        "pages": parts[7],
                        "cadence": parts[8],
                    }
                )
        elif in_table and line.strip():
            break
    return rows


def cmd_topic_add(args: argparse.Namespace) -> int:
    if not TOPIC_ID_RE.fullmatch(args.topic_id):
        raise SystemExit("topic id must be lowercase ASCII with hyphens")
    path = topic_registry()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_text(path, "# Topic Registry\n\n## Topic Table\n\n| Topic ID | Name | Aliases | Scope | Include | Exclude | Default Search | Canonical Pages | Review Cadence |\n|---|---|---|---|---|---|---|---|---|\n")
    rows = parse_topic_rows()
    if any(row["id"] == args.topic_id for row in rows):
        raise SystemExit(f"topic already exists: {args.topic_id}")
    row = (
        f"| {args.topic_id} | {args.name} | {args.aliases or ''} | {args.scope or ''} | "
        f"{args.include or ''} | {args.exclude or ''} | {args.search or ''} | "
        f"{args.pages or ''} | {args.cadence or ''} |"
    )
    text = read_text(path)
    marker = "|---|---|---|---|---|---|---|---|---|"
    insert_at = text.find(marker)
    if insert_at == -1:
        text = text.rstrip() + "\n\n## Topic Table\n\n| Topic ID | Name | Aliases | Scope | Include | Exclude | Default Search | Canonical Pages | Review Cadence |\n|---|---|---|---|---|---|---|---|---|\n" + row + "\n"
    else:
        line_end = text.find("\n", insert_at)
        text = text[: line_end + 1] + row + "\n" + text[line_end + 1 :]
    write_text(path, text)
    if not args.no_page:
        page = repo_path("wiki", "topics", f"{args.topic_id}.md")
        template = read_text(repo_path("templates", "topic.md")) if repo_path("templates", "topic.md").exists() else "# Topic Title\n"
        template = template.replace("# Topic Title", f"# {args.name}")
        template = template.replace("created: YYYY-MM-DD", f"created: {today()}")
        template = template.replace("updated: YYYY-MM-DD", f"updated: {today()}")
        write_text(page, template)
    print(f"added topic: {args.topic_id}")
    return 0


def lint_topics() -> list[str]:
    errors: list[str] = []
    rows = parse_topic_rows()
    seen_ids: set[str] = set()
    seen_aliases: dict[str, str] = {}
    for row in rows:
        topic_id = row["id"]
        if not TOPIC_ID_RE.fullmatch(topic_id):
            errors.append(f"invalid topic id: {topic_id}")
        if topic_id in seen_ids:
            errors.append(f"duplicate topic id: {topic_id}")
        seen_ids.add(topic_id)
        if not row["scope"]:
            errors.append(f"{topic_id}: missing scope")
        if not row["search"]:
            errors.append(f"{topic_id}: missing default search")
        for alias in [part.strip().lower() for part in row["aliases"].split(",") if part.strip()]:
            if alias in seen_aliases:
                errors.append(f"duplicate alias {alias!r}: {seen_aliases[alias]} and {topic_id}")
            seen_aliases[alias] = topic_id
    return errors


def cmd_topic_lint(_: argparse.Namespace) -> int:
    errors = lint_topics()
    if errors:
        print("topic lint failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("topic lint passed")
    return 0


def cmd_topic_list(_: argparse.Namespace) -> int:
    for row in parse_topic_rows():
        print(f"{row['id']}\t{row['name']}\t{row['search']}")
    return 0


def cmd_wiki_lint(_: argparse.Namespace) -> int:
    result = subprocess.run([sys.executable, str(repo_path("tools", "wiki_lint.py"))])
    return result.returncode


def cmd_wiki_graph(_: argparse.Namespace) -> int:
    result = subprocess.run([sys.executable, str(repo_path("tools", "build_runtime_state.py"))])
    return result.returncode


def cmd_prompt_external_sandbox(args: argparse.Namespace) -> int:
    path = repo_path("maintenance", "external_sandbox_sync_prompt.md")
    prompt = f"""# ResearchWiki External Sandbox Context Capsule

Repository path: {ROOT}
Target layer: {args.target}
Suggested mode: knowledge-workbench/query-to-save

## Task

{args.task}

## Evidence Boundaries

- Query can read existing wiki pages and public-safe raw indexes.
- Do not treat chat discussion as source evidence.
- Do not copy full articles, private PDFs, local Drive paths, screenshots from
  authenticated sessions, or Codex logs into the wiki.
- If a result is worth keeping, propose a Save target first: paper page,
  question, concept, synthesis, topic, project synthesis, review queue, or log.
- Unsupported, uncertain, or conflicting ideas go to
  `maintenance/review_queue.md`.

## Return Format

1. Answer or analysis.
2. Evidence links used.
3. Recommended Save target.
4. Draft Save payload, or reason not to save.
"""
    write_text(path, prompt)
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ResearchWiki deterministic CLI")
    sub = parser.add_subparsers(dest="area", required=True)

    source = sub.add_parser("source", help="source intake and acquisition")
    source_sub = source.add_subparsers(dest="command", required=True)
    add = source_sub.add_parser("add")
    add.add_argument("pointer")
    add.add_argument("--note")
    add.add_argument("--key")
    add.add_argument("--status", choices=sorted(STATUSES), default="new")
    add.set_defaults(func=cmd_source_add)
    search = source_sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--topic-id")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--live", action="store_true")
    search.set_defaults(func=cmd_source_search)
    resolve = source_sub.add_parser("resolve")
    resolve.add_argument("pointer")
    resolve.add_argument("--key")
    resolve.set_defaults(func=cmd_source_resolve)
    acquire = source_sub.add_parser("acquire")
    acquire.add_argument("identifier")
    acquire.add_argument("--key")
    acquire.add_argument("--pdf")
    acquire.add_argument("--url")
    acquire.add_argument("--download", action="store_true")
    acquire.add_argument("--screenshot")
    acquire.add_argument("--checkpoint", choices=["pending", "approved"], default="pending")
    acquire.set_defaults(func=cmd_source_acquire)
    qc = source_sub.add_parser("qc")
    qc.add_argument("--identifier", default="")
    qc.add_argument("--key")
    qc.add_argument("--full-text")
    qc.add_argument("--abstract-only", action="store_true")
    qc.add_argument("--abstract")
    qc.add_argument("--title")
    qc.set_defaults(func=cmd_source_qc)
    dashboard = source_sub.add_parser("dashboard")
    dashboard.add_argument("--rebuild-index", action="store_true")
    dashboard.set_defaults(func=cmd_source_dashboard)

    paper = sub.add_parser("paper", help="paper page operations")
    paper_sub = paper.add_subparsers(dest="command", required=True)
    ingest = paper_sub.add_parser("ingest")
    ingest.add_argument("source")
    ingest.add_argument("--key")
    ingest.add_argument("--slug")
    ingest.add_argument("--allow-abstract-only", action="store_true")
    ingest.set_defaults(func=cmd_paper_ingest)

    topic = sub.add_parser("topic", help="topic governance")
    topic_sub = topic.add_subparsers(dest="command", required=True)
    topic_add = topic_sub.add_parser("add")
    topic_add.add_argument("topic_id")
    topic_add.add_argument("name")
    topic_add.add_argument("--aliases")
    topic_add.add_argument("--scope")
    topic_add.add_argument("--include")
    topic_add.add_argument("--exclude")
    topic_add.add_argument("--search")
    topic_add.add_argument("--pages")
    topic_add.add_argument("--cadence")
    topic_add.add_argument("--no-page", action="store_true")
    topic_add.set_defaults(func=cmd_topic_add)
    topic_list = topic_sub.add_parser("list")
    topic_list.set_defaults(func=cmd_topic_list)
    topic_lint = topic_sub.add_parser("lint")
    topic_lint.set_defaults(func=cmd_topic_lint)

    wiki = sub.add_parser("wiki", help="wiki maintenance")
    wiki_sub = wiki.add_subparsers(dest="command", required=True)
    wiki_lint = wiki_sub.add_parser("lint")
    wiki_lint.set_defaults(func=cmd_wiki_lint)
    wiki_graph = wiki_sub.add_parser("graph")
    wiki_graph.set_defaults(func=cmd_wiki_graph)

    prompt = sub.add_parser("prompt", help="prompt generators")
    prompt_sub = prompt.add_subparsers(dest="command", required=True)
    ext = prompt_sub.add_parser("external-sandbox")
    ext.add_argument("--target", default="review_queue")
    ext.add_argument("--task", required=True)
    ext.set_defaults(func=cmd_prompt_external_sandbox)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
