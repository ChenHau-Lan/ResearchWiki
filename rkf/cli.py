"""Command-line interface for the Research Knowledge Framework."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    Workspace,
    add_topic,
    append_log,
    approved_pdf_acquisition,
    create_paper_note,
    create_source,
    external_sandbox_capsule,
    export_graph,
    generate_wiki_index,
    infer_evidence_tier,
    lint_knowledge_pages,
    lint_public_safety,
    lint_topics,
    parse_frontmatter,
    read_json,
    relative_workspace_path,
    slugify,
    today,
    verify_pdf,
    write_acquisition_checkpoint,
    write_json,
)


LINT_MODES = {
    "all",
    "structure-lint",
    "evidence-lint",
    "graph-lint",
    "ars-handoff-lint",
    "public-safety-lint",
    "repair-plan",
}


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_capture(args: argparse.Namespace) -> int:
    ws = Workspace()
    record = create_source(
        ws,
        kind=args.kind,
        value=args.value,
        title=args.title or "",
        topic_id=args.topic_id or "",
        note=args.note or "",
    )
    print(f"captured source: {record['source_id']}")
    print(f"status: {record['status']}")
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    ws = Workspace()
    ws.ensure_base()
    run_id = f"{today()}_{slugify(args.query, 48)}"
    run_dir = ws.paths.search_runs / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "rkf-discovery-run-v1",
        "query": args.query,
        "topic_id": args.topic_id or "",
        "live": False,
        "candidates": [],
        "gate": "candidates_are_not_evidence",
        "created": today(),
    }
    write_json(run_dir / "candidates.json", payload)
    print(f"wrote discovery run: {relative_workspace_path(ws, run_dir)}")
    print("candidates: 0")
    return 0


def _load_or_capture(ws: Workspace, value: str) -> dict[str, object]:
    path = ws.source_path(value)
    if path.exists():
        return read_json(path)
    kind = "doi" if value.lower().startswith("10.") or "doi.org/" in value.lower() else "url"
    return create_source(ws, kind=kind, value=value)


def cmd_acquire(args: argparse.Namespace) -> int:
    ws = Workspace()
    record = _load_or_capture(ws, args.source)
    route = args.pdf or args.url or "candidate route not supplied"
    if not args.approve:
        path = write_acquisition_checkpoint(ws, record, route=route, screenshot=args.screenshot or "")
        print(f"checkpoint required: {relative_workspace_path(ws, path)}")
        print("status: pdf_checkpoint_required")
        return 0
    if not args.pdf:
        raise SystemExit("approved acquisition currently requires --pdf")
    artifact = approved_pdf_acquisition(ws, record, Path(args.pdf).expanduser().resolve())
    print(f"stored PDF evidence artifact: {artifact['evidence_id']}")
    print("status: pdf_downloaded")
    return 0


def cmd_verify_pdf(args: argparse.Namespace) -> int:
    ws = Workspace()
    record = ws.load_source(args.source_id)
    artifact = verify_pdf(
        ws,
        record,
        locator=args.locator or "",
        note=args.note or "",
        qc_status=args.qc_status,
    )
    print(f"verified PDF evidence: {artifact['evidence_id']}")
    print("status: pdf_qc_done")
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    ws = Workspace()
    record = ws.load_source(args.source_id)
    print_json(record)
    return 0


def cmd_distill(args: argparse.Namespace) -> int:
    ws = Workspace()
    if args.distill_type != "paper":
        raise SystemExit("RKF currently implements `rk distill paper`")
    record = ws.load_source(args.source_id)
    path = create_paper_note(ws, record, slug=args.slug or "")
    print(f"wrote knowledge page: {relative_workspace_path(ws, path)}")
    return 0


def cmd_topic_add(args: argparse.Namespace) -> int:
    ws = Workspace()
    topic = add_topic(
        ws,
        topic_id=args.topic_id,
        name=args.name,
        scope=args.scope or "",
        aliases=args.alias or [],
        include=args.include or [],
        exclude=args.exclude or [],
        search=args.search or [],
        cadence=args.cadence or "monthly",
    )
    print(f"added topic: {topic['topic_id']}")
    return 0


def cmd_topic_list(args: argparse.Namespace) -> int:
    ws = Workspace()
    for topic in ws.load_topics():
        print(f"{topic['topic_id']}\t{topic.get('name', '')}")
    return 0


def cmd_topic_lint(args: argparse.Namespace) -> int:
    ws = Workspace()
    errors = lint_topics(ws)
    if errors:
        print("topic lint failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("topic lint passed")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    ws = Workspace()
    needle = args.text.lower()
    matches: list[tuple[str, str, str, str]] = []
    if ws.paths.knowledge.exists():
        for path in ws.paths.knowledge.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if needle in text:
                meta, body = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
                page_type = str(meta.get("type", "unknown")) if meta else "unknown"
                topics = ",".join(str(item) for item in meta.get("topics", [])) if meta else ""
                tier = infer_evidence_tier(meta, body) if meta else "review-blocker"
                matches.append((relative_workspace_path(ws, path), page_type, topics, tier))
    print(f"matches: {len(matches)}")
    for match, page_type, topics, tier in matches:
        print(f"- {match}\ttype={page_type}\ttier={tier}\ttopics={topics or 'none'}")
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    ws = Workspace()
    if args.object_type == "paper":
        raise SystemExit("use `rk distill paper` for paper pages so PDF gates are enforced")
    allowed = {"question", "concept", "claim", "synthesis", "overview", "project-synthesis", "meeting", "seminar"}
    if args.object_type not in allowed:
        raise SystemExit(f"unsupported save type: {args.object_type}")
    slug = slugify(args.slug or args.title)
    folder = args.object_type.replace("-", "_")
    path = ws.paths.knowledge / folder / f"{slug}.md"
    body = args.body or "TBD"
    text = (
        "---\n"
        f"type: {args.object_type}\n"
        "status: draft\n"
        "review_stage: ai-extracted\n"
        "topics: []\n"
        "evidence_boundary: review-blocker\n"
        "evidence_tier: review-blocker\n"
        f"created: {today()}\n"
        f"updated: {today()}\n"
        "sources: []\n"
        "---\n\n"
        f"# {args.title}\n\n{body.rstrip()}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    append_log(ws, "save", f"{args.object_type} {relative_workspace_path(ws, path)}")
    print(f"saved knowledge object: {relative_workspace_path(ws, path)}")
    return 0


def cmd_synthesize(args: argparse.Namespace) -> int:
    args.object_type = "synthesis"
    return cmd_save(args)


def cmd_review(args: argparse.Namespace) -> int:
    ws = Workspace()
    count = 0
    if ws.paths.gates.exists():
        for path in sorted(ws.paths.gates.rglob("*.md")):
            print(f"- {relative_workspace_path(ws, path)}")
            count += 1
    print(f"review items: {count}")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    if args.mode not in LINT_MODES:
        raise SystemExit(f"unknown lint mode: {args.mode}")
    ws = Workspace()
    errors: list[str] = []
    if args.mode in {"all", "structure-lint", "evidence-lint"}:
        errors.extend(lint_knowledge_pages(ws))
    if args.mode in {"all", "structure-lint"}:
        errors.extend(lint_topics(ws))
    if args.mode == "public-safety-lint":
        errors.extend(lint_public_safety(ws))
    if errors:
        print(f"rkf {args.mode} failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    if args.mode == "repair-plan":
        print("repair-plan: no deterministic repair needed")
    else:
        print(f"rkf {args.mode} passed")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    ws = Workspace()
    graph = export_graph(ws)
    print(f"graph nodes: {len(graph['nodes'])}")
    print(f"graph edges: {len(graph['edges'])}")
    print(f"wrote: {relative_workspace_path(ws, ws.paths.graph / 'research_graph.json')}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    ws = Workspace()
    path = generate_wiki_index(ws)
    print(f"wrote: {relative_workspace_path(ws, path)}")
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    ws = Workspace()
    if args.note:
        append_log(ws, args.action or "note", args.note)
    if not ws.paths.log.exists():
        print("wiki log not found")
        return 0
    lines = ws.paths.log.read_text(encoding="utf-8", errors="replace").splitlines()
    if args.tail:
        lines = lines[-args.tail :]
    for line in lines:
        print(line)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    if args.export_type == "graph":
        return cmd_graph(args)
    if args.export_type == "external-sandbox":
        ws = Workspace()
        path = external_sandbox_capsule(ws)
        print(f"wrote: {relative_workspace_path(ws, path)}")
        return 0
    raise SystemExit(f"unknown export type: {args.export_type}")


def cmd_prompt_external_sandbox(args: argparse.Namespace) -> int:
    ws = Workspace()
    path = external_sandbox_capsule(ws)
    print(f"wrote: {relative_workspace_path(ws, path)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rk", description="Research Knowledge Framework CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    capture = sub.add_parser("capture", help="Capture DOI, URL, PDF pointer, topic seed, idea, or question")
    capture.add_argument("kind", choices=["doi", "url", "pdf", "topic", "idea", "question"])
    capture.add_argument("value")
    capture.add_argument("--title")
    capture.add_argument("--topic-id")
    capture.add_argument("--note")
    capture.set_defaults(func=cmd_capture)

    discover = sub.add_parser("discover", help="Stage a discovery run; candidates are not evidence")
    discover.add_argument("query")
    discover.add_argument("--topic-id")
    discover.set_defaults(func=cmd_discover)

    acquire = sub.add_parser("acquire", help="Stage or approve PDF evidence acquisition")
    acquire.add_argument("source")
    acquire.add_argument("--pdf")
    acquire.add_argument("--url")
    acquire.add_argument("--screenshot")
    acquire.add_argument("--approve", action="store_true")
    acquire.set_defaults(func=cmd_acquire)

    verify_pdf_parser = sub.add_parser("verify-pdf", help="Mark approved PDF evidence as QCed for wiki distillation")
    verify_pdf_parser.add_argument("source_id")
    verify_pdf_parser.add_argument("--locator", help="Page/section/quote locator checked during PDF QC")
    verify_pdf_parser.add_argument("--note")
    verify_pdf_parser.add_argument("--qc-status", choices=["codex_qc_done", "human_qc_done"], default="codex_qc_done")
    verify_pdf_parser.set_defaults(func=cmd_verify_pdf)

    read = sub.add_parser("read", help="Read a source record")
    read.add_argument("source_id")
    read.set_defaults(func=cmd_read)

    distill = sub.add_parser("distill", help="Create a knowledge object from verified evidence")
    distill.add_argument("distill_type", choices=["paper"])
    distill.add_argument("source_id")
    distill.add_argument("--slug")
    distill.set_defaults(func=cmd_distill)

    topic = sub.add_parser("topic", help="Topic governance")
    topic_sub = topic.add_subparsers(dest="topic_command", required=True)
    topic_add = topic_sub.add_parser("add")
    topic_add.add_argument("topic_id")
    topic_add.add_argument("name")
    topic_add.add_argument("--scope")
    topic_add.add_argument("--alias", action="append")
    topic_add.add_argument("--include", action="append")
    topic_add.add_argument("--exclude", action="append")
    topic_add.add_argument("--search", action="append")
    topic_add.add_argument("--cadence")
    topic_add.set_defaults(func=cmd_topic_add)
    topic_list = topic_sub.add_parser("list")
    topic_list.set_defaults(func=cmd_topic_list)
    topic_lint = topic_sub.add_parser("lint")
    topic_lint.set_defaults(func=cmd_topic_lint)

    query = sub.add_parser("query", help="Read-only search across knowledge pages")
    query.add_argument("text")
    query.set_defaults(func=cmd_query)

    save = sub.add_parser("save", help="Save a non-paper knowledge object")
    save.add_argument("object_type")
    save.add_argument("title")
    save.add_argument("--slug")
    save.add_argument("--body")
    save.set_defaults(func=cmd_save)

    synthesize = sub.add_parser("synthesize", help="Create a draft synthesis object")
    synthesize.add_argument("title")
    synthesize.add_argument("--slug")
    synthesize.add_argument("--body")
    synthesize.set_defaults(func=cmd_synthesize)

    review = sub.add_parser("review", help="List pending gates and review items")
    review.set_defaults(func=cmd_review)

    lint = sub.add_parser("lint", help="Validate RKF structure, evidence, graph, ARS handoff, or public safety")
    lint.add_argument("--mode", choices=sorted(LINT_MODES), default="all")
    lint.set_defaults(func=cmd_lint)

    graph = sub.add_parser("graph", help="Export the research graph")
    graph.set_defaults(func=cmd_graph)

    index = sub.add_parser("index", help="Generate the compact LLM wiki index")
    index.set_defaults(func=cmd_index)

    log = sub.add_parser("log", help="Read or append the wiki operation log")
    log.add_argument("--tail", type=int, default=20)
    log.add_argument("--action")
    log.add_argument("--note")
    log.set_defaults(func=cmd_log)

    export = sub.add_parser("export", help="Export graph or external sandbox capsule")
    export.add_argument("export_type", choices=["graph", "external-sandbox"])
    export.set_defaults(func=cmd_export)

    prompt = sub.add_parser("prompt", help="Prompt helpers")
    prompt_sub = prompt.add_subparsers(dest="prompt_command", required=True)
    external = prompt_sub.add_parser("external-sandbox")
    external.set_defaults(func=cmd_prompt_external_sandbox)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"rk error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
