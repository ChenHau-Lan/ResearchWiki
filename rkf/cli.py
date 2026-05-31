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
    evolve_page,
    export_graph,
    generate_wiki_index,
    infer_evidence_tier,
    lint_ars_handoff,
    lint_graph_links,
    lint_knowledge_pages,
    lint_public_safety,
    lint_topics,
    parse_frontmatter,
    paper_queue,
    propose_propagation,
    read_json,
    record_hot_query,
    render_paper_nudge,
    relative_workspace_path,
    render_workspace_status,
    refresh_hot_markdown,
    slugify,
    today,
    update_paper_maturity,
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
    record_hot_query(ws, query=args.query, topic_id=args.topic_id or "", origin="local", intent="discover")
    refresh_hot_markdown(ws)
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
    if args.checkpoint:
        path = write_acquisition_checkpoint(ws, record, route=route, screenshot=args.screenshot or "")
        print(f"legacy checkpoint written: {relative_workspace_path(ws, path)}")
        print("status: pdf_checkpoint_required")
        return 0
    if not args.pdf:
        record["fulltext_status"] = "needs-user-pdf"
        record["reading_state"] = "metadata-only"
        ws.save_source(record)
        print(f"source needs user-provided full text: {record['source_id']}")
        print("status: needs_user_pdf")
        return 0
    artifact = approved_pdf_acquisition(ws, record, Path(args.pdf).expanduser().resolve())
    print(f"stored user-provided PDF artifact: {artifact['evidence_id']}")
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


def cmd_paper_status(args: argparse.Namespace) -> int:
    ws = Workspace()
    items = paper_queue(ws)
    if args.source_id:
        items = [item for item in items if item["source_id"] == args.source_id]
    if not items:
        print("paper queue: empty")
        return 0
    for item in items:
        print(f"{item['source_id']}\taction={item['action']}\tpriority={item['priority']}\tpath={item.get('path', '')}")
        print(f"  reasons: {'; '.join(item['reasons'])}")
    return 0


def cmd_paper_feedback(args: argparse.Namespace) -> int:
    ws = Workspace()
    path = update_paper_maturity(
        ws,
        args.source_id,
        reading_state=args.reading_state or "",
        fulltext_status=args.fulltext_status or "",
        human_feedback_level=args.level,
        understanding_confidence=args.confidence or "",
        claim_readiness=args.claim_readiness or "",
        note=args.note,
        actor="human",
    )
    print(f"updated paper maturity: {relative_workspace_path(ws, path)}")
    return 0


def cmd_paper_queue(args: argparse.Namespace) -> int:
    ws = Workspace()
    items = paper_queue(ws)[: args.limit]
    print(f"paper queue: {len(items)}")
    for item in items:
        print(f"- {item['source_id']}\taction={item['action']}\tpriority={item['priority']}\tpath={item.get('path', '')}")
        print(f"  reasons: {'; '.join(item['reasons'])}")
    return 0


def cmd_paper_next(args: argparse.Namespace) -> int:
    ws = Workspace()
    items = paper_queue(ws)
    if not items:
        print("paper queue: empty")
        return 0
    item = items[0]
    print(f"{item['source_id']}\taction={item['action']}\tpriority={item['priority']}\tpath={item.get('path', '')}")
    print(f"reasons: {'; '.join(item['reasons'])}")
    return 0


def cmd_paper_nudge(args: argparse.Namespace) -> int:
    ws = Workspace()
    print(render_paper_nudge(ws, limit=args.limit), end="")
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
    if not args.no_record:
        record_hot_query(ws, query=args.text, origin="local", intent="query")
        refresh_hot_markdown(ws)
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
    update = bool(getattr(args, "update", False))
    if path.exists() and not update:
        raise SystemExit(
            f"knowledge object already exists: {relative_workspace_path(ws, path)}; "
            "refusing to overwrite without --update"
        )
    body = args.body or "TBD"
    created = today()
    if path.exists():
        existing_meta, _ = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        created = str(existing_meta.get("created", created))
    text = (
        "---\n"
        f"type: {args.object_type}\n"
        "status: draft\n"
        "review_stage: ai-extracted\n"
        "topics: []\n"
        "evidence_boundary: review-blocker\n"
        "evidence_tier: review-blocker\n"
        + (
            "synthesis_maturity: draft\n"
            "source_coverage: unknown\n"
            "human_feedback_level: none\n"
            "claim_readiness: not-ready\n"
            f"last_synthesis_interaction: {today()}\n"
            if args.object_type == "synthesis"
            else ""
        )
        + f"created: {created}\n"
        f"updated: {today()}\n"
        "sources: []\n"
        "---\n\n"
        f"# {args.title}\n\n{body.rstrip()}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    action = "update" if update else "save"
    append_log(ws, action, f"{args.object_type} {relative_workspace_path(ws, path)}")
    print(f"{action}d knowledge object: {relative_workspace_path(ws, path)}")
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
    if args.mode in {"all", "graph-lint"}:
        errors.extend(lint_graph_links(ws))
    if args.mode in {"all", "ars-handoff-lint"}:
        errors.extend(lint_ars_handoff(ws))
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


def cmd_propagate(args: argparse.Namespace) -> int:
    ws = Workspace()
    proposal = propose_propagation(ws, args.target, write=args.write)
    print(f"propagation target: {proposal['target']}")
    print(f"affected pages: {len(proposal['affected_pages'])}")
    for item in proposal["affected_pages"]:
        print(f"- {item['path']}\treasons={'; '.join(item['reasons'])}")
    blockers = proposal.get("blockers", [])
    if blockers:
        print("review blockers:")
        for blocker in blockers:
            print(f"- {blocker}")
    if proposal.get("proposal_path"):
        print(f"wrote: {proposal['proposal_path']}")
    else:
        print("rule: preview/audit fallback; rerun with --write to create a review gate")
    return 0


def cmd_evolve(args: argparse.Namespace) -> int:
    ws = Workspace()
    result = evolve_page(
        ws,
        args.target,
        note=args.note,
        input_source=args.source,
        priority=args.priority,
        blocker=args.blocker or "",
        write=not args.dry_run,
    )
    print(f"evolve target: {result['path']}")
    print(f"priority: {result['priority']}")
    print(f"ai_integrated: {str(result['ai_integrated']).lower()}")
    print(f"wrote: {str(result['wrote']).lower()}")
    blockers = result.get("blockers", [])
    if blockers:
        print("blockers:")
        for blocker in blockers:
            print(f"- {blocker}")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    ws = Workspace()
    graph = export_graph(ws)
    print(f"graph nodes: {len(graph['nodes'])}")
    print(f"graph edges: {len(graph['edges'])}")
    print(f"wrote: {relative_workspace_path(ws, ws.paths.graph / 'research_graph.json')}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ws = Workspace()
    print(render_workspace_status(ws, log_tail=args.log_tail), end="")
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


def cmd_hot_record(args: argparse.Namespace) -> int:
    ws = Workspace()
    event = record_hot_query(
        ws,
        query=args.query,
        topic_id=args.topic_id or "",
        origin=args.origin,
        intent=args.intent,
        paper_leads=args.paper_lead or [],
        notes=args.notes or "",
    )
    refresh_hot_markdown(ws)
    print(f"recorded hot query: {event['event_id']}")
    print(f"topics: {','.join(event.get('topic_ids', [])) or 'unknown'}")
    return 0


def cmd_hot_refresh(args: argparse.Namespace) -> int:
    ws = Workspace()
    path = refresh_hot_markdown(ws, days=args.days)
    print(f"wrote: {relative_workspace_path(ws, path)}")
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

    discover = sub.add_parser("discover", help="Stage a discovery run; candidates need reading before they can support claims")
    discover.add_argument("query")
    discover.add_argument("--topic-id")
    discover.set_defaults(func=cmd_discover)

    acquire = sub.add_parser("acquire", help="Record user-provided full text or legacy route review")
    acquire.add_argument("source")
    acquire.add_argument("--pdf")
    acquire.add_argument("--url")
    acquire.add_argument("--screenshot")
    acquire.add_argument("--approve", action="store_true", help="Accepted for legacy compatibility; PDF storage no longer requires it")
    acquire.add_argument("--checkpoint", action="store_true", help="Write a legacy route-review checkpoint instead of storing a PDF")
    acquire.set_defaults(func=cmd_acquire)

    verify_pdf_parser = sub.add_parser("verify-pdf", help="Mark a PDF as checked and update paper reading maturity")
    verify_pdf_parser.add_argument("source_id")
    verify_pdf_parser.add_argument("--locator", help="Page/section/quote locator checked during PDF or visual review")
    verify_pdf_parser.add_argument("--note")
    verify_pdf_parser.add_argument("--qc-status", choices=["codex_qc_done", "human_qc_done"], default="codex_qc_done")
    verify_pdf_parser.set_defaults(func=cmd_verify_pdf)

    read = sub.add_parser("read", help="Read a source record")
    read.add_argument("source_id")
    read.set_defaults(func=cmd_read)

    distill = sub.add_parser("distill", help="Create or update a paper reading draft")
    distill.add_argument("distill_type", choices=["paper"])
    distill.add_argument("source_id")
    distill.add_argument("--slug")
    distill.set_defaults(func=cmd_distill)

    paper = sub.add_parser("paper", help="Paper reading maturity and active queue")
    paper_sub = paper.add_subparsers(dest="paper_command", required=True)
    paper_status = paper_sub.add_parser("status", help="Show queued status for papers")
    paper_status.add_argument("source_id", nargs="?")
    paper_status.set_defaults(func=cmd_paper_status)
    paper_feedback = paper_sub.add_parser("feedback", help="Record human feedback and update maturity")
    paper_feedback.add_argument("source_id")
    paper_feedback.add_argument("--level", choices=["none", "skimmed", "discussed", "annotated", "trusted"], default="discussed")
    paper_feedback.add_argument("--note", required=True)
    paper_feedback.add_argument("--reading-state", choices=["metadata-only", "abstract-read", "skimmed", "partial-fulltext", "fulltext-read", "full-read", "human-reviewed", "mixed"])
    paper_feedback.add_argument(
        "--fulltext-status",
        choices=[
            "unknown",
            "needs-user-pdf",
            "user-pdf-provided",
            "publisher-html",
            "publisher-pdf",
            "open-access-pdf",
            "partial-only",
            "fulltext-read",
            "unavailable",
            "blocked",
            "not-applicable",
        ],
    )
    paper_feedback.add_argument("--confidence", choices=["low", "medium", "high", "mixed"])
    paper_feedback.add_argument("--claim-readiness", choices=["not-ready", "locator-needed", "claim-ready", "synthesis-ready"])
    paper_feedback.set_defaults(func=cmd_paper_feedback)
    paper_queue_parser = paper_sub.add_parser("queue", help="List active paper reading nudges")
    paper_queue_parser.add_argument("--limit", type=int, default=20)
    paper_queue_parser.set_defaults(func=cmd_paper_queue)
    paper_next = paper_sub.add_parser("next", help="Show the highest-priority paper nudge")
    paper_next.set_defaults(func=cmd_paper_next)
    paper_nudge = paper_sub.add_parser("nudge", help="Render scheduled paper nudge output")
    paper_nudge.add_argument("--limit", type=int, default=10)
    paper_nudge.set_defaults(func=cmd_paper_nudge)

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

    query = sub.add_parser("query", help="Search knowledge pages and record a hot-query event by default")
    query.add_argument("text")
    query.add_argument("--no-record", action="store_true", help="Do not record this query in the hot-query layer")
    query.set_defaults(func=cmd_query)

    save = sub.add_parser("save", help="Save a non-paper knowledge object")
    save.add_argument("object_type")
    save.add_argument("title")
    save.add_argument("--slug")
    save.add_argument("--body")
    save.add_argument("--update", action="store_true", help="Intentionally replace an existing object with the same slug")
    save.set_defaults(func=cmd_save)

    synthesize = sub.add_parser("synthesize", help="Create a draft synthesis object")
    synthesize.add_argument("title")
    synthesize.add_argument("--slug")
    synthesize.add_argument("--body")
    synthesize.add_argument("--update", action="store_true", help="Intentionally replace an existing synthesis with the same slug")
    synthesize.set_defaults(func=cmd_synthesize)

    review = sub.add_parser("review", help="List pending gates and review items")
    review.set_defaults(func=cmd_review)

    lint = sub.add_parser("lint", help="Validate RKF structure, evidence, graph, ARS handoff, or public safety")
    lint.add_argument("--mode", choices=sorted(LINT_MODES), default="all")
    lint.set_defaults(func=cmd_lint)

    evolve = sub.add_parser("evolve", help="Directly integrate low-risk page updates with an AI Integration Note")
    evolve.add_argument("target", help="Knowledge page path to rewrite")
    evolve.add_argument("--note", required=True, help="Public-safe reason for the integration")
    evolve.add_argument("--source", default="codex", help="Public-safe input source label")
    evolve.add_argument("--priority", choices=["low", "medium", "high"], default="low")
    evolve.add_argument("--blocker", help="Explicit blocker to leave on the page")
    evolve.add_argument("--dry-run", action="store_true", help="Render decision without writing the page")
    evolve.set_defaults(func=cmd_evolve)

    propagate = sub.add_parser("propagate", help="Generate affected-page propagation preview/audit review")
    propagate.add_argument("target", help="Source ID or knowledge page path to review for propagation")
    propagate.add_argument("--write", action="store_true", help="Write a propagation gate under state/gates")
    propagate.set_defaults(func=cmd_propagate)

    graph = sub.add_parser("graph", help="Export the research graph")
    graph.set_defaults(func=cmd_graph)

    status = sub.add_parser("status", help="Print RKF L0-L3 workspace context for session bootstrap")
    status.add_argument("--log-tail", type=int, default=5)
    status.set_defaults(func=cmd_status)

    world = sub.add_parser("world", help="Alias for the RKF L0-L3 workspace context capsule")
    world.add_argument("--log-tail", type=int, default=5)
    world.set_defaults(func=cmd_status)

    index = sub.add_parser("index", help="Generate the compact LLM wiki index")
    index.set_defaults(func=cmd_index)

    log = sub.add_parser("log", help="Read or append the wiki operation log")
    log.add_argument("--tail", type=int, default=20)
    log.add_argument("--action")
    log.add_argument("--note")
    log.set_defaults(func=cmd_log)

    hot = sub.add_parser("hot", help="Record and summarize hot research questions")
    hot_sub = hot.add_subparsers(dest="hot_command", required=True)
    hot_record = hot_sub.add_parser("record", help="Record a public-safe hot query event")
    hot_record.add_argument("query")
    hot_record.add_argument("--topic-id")
    hot_record.add_argument("--origin", choices=["local", "external-sandbox"], default="local")
    hot_record.add_argument(
        "--intent",
        choices=["query", "discover", "paper-search", "proposal"],
        default="query",
    )
    hot_record.add_argument("--paper-lead", action="append")
    hot_record.add_argument("--notes")
    hot_record.set_defaults(func=cmd_hot_record)
    hot_refresh = hot_sub.add_parser("refresh", help="Regenerate hot.md summary from its records")
    hot_refresh.add_argument("--days", type=int, default=30)
    hot_refresh.set_defaults(func=cmd_hot_refresh)

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
