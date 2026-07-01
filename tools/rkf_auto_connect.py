"""Cross-project RKF auto-connect helper.

This helper is intentionally small: it resolves the local RKF checkout,
classifies whether a task should be captured, and builds structured RKF action
requests for Codex app workflows. It does not own RKF schemas or promote claims.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rkf.actions import ActionRequest, ActionResult, execute_action_request as execute_rkf_action_request
from rkf.core import Workspace

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


DEFAULT_CONFIG = Path(os.environ.get("RKF_CONNECTOR_CONFIG", "~/.codex/rkf_connector.toml")).expanduser()
PRIVATE_PATH_RE = re.compile(r"/" + r"Users/[^/\s]+|C:" + r"\\Users\\", re.IGNORECASE)
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ARXIV_RE = re.compile(r"\barxiv:\s*\d{4}\.\d{4,5}(?:v\d+)?|\barxiv\.org/abs/\d{4}\.\d{4,5}", re.IGNORECASE)
PUBMED_RE = re.compile(r"\bPMID:\s*\d+\b|\bpubmed\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)>\"]+")
LONG_CAPTURE_LIMIT = 12000

ACTIVE_TERMS = {
    "paper",
    "papers",
    "doi",
    "citation",
    "reference",
    "journal",
    "conference",
    "literature",
    "source",
    "web clip",
    "dataset",
    "arxiv",
    "pubmed",
}

AGGRESSIVE_TERMS = {
    "synthesis",
    "literature review",
    "method",
    "experiment design",
    "manuscript",
    "proposal",
    "hypothesis",
    "claim",
    "evidence",
    "diagnostic",
    "parameterization",
    "calibration",
    "interpretation",
    "研究",
    "文獻",
    "方法",
    "實驗",
    "論文",
    "投稿",
    "假說",
    "證據",
    "綜整",
}

CODING_ONLY_TERMS = {
    "css",
    "button",
    "padding",
    "typescript",
    "react component",
    "build error",
    "lint error",
}


@dataclass(frozen=True)
class ConnectorConfig:
    researchwiki_root: Path
    mode: str
    config_path: Path


@dataclass(frozen=True)
class CaptureDecision:
    level: str
    targets: list[str]
    reasons: list[str]
    summary: str


@dataclass(frozen=True)
class BridgeFolderResult:
    root: Path
    created: list[Path]
    existing: list[Path]


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"RKF connector config not found: {path}")
    if tomllib is not None:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    data: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = data.setdefault(line.strip("[]"), {})
            continue
        if current is not None and "=" in line:
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip().strip('"')
    return data


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def load_connector_config(path: Path | None = None) -> ConnectorConfig:
    config_path = path or Path(os.environ.get("RKF_CONNECTOR_CONFIG", str(DEFAULT_CONFIG))).expanduser()
    data = _load_toml(config_path)
    researchwiki = data.get("researchwiki", {}) if isinstance(data, dict) else {}
    policy = data.get("policy", {}) if isinstance(data, dict) else {}
    root_value = researchwiki.get("root") if isinstance(researchwiki, dict) else None
    if not isinstance(root_value, str) or not root_value.strip():
        raise SystemExit("RKF connector config missing [researchwiki].root")
    root = _expand_path(root_value)
    if not root.exists():
        raise SystemExit(f"RKF checkout not found under configured root: {root}")
    if not ((root / "rkf.workspace.toml").exists() or (root / "workspace.toml").exists()):
        raise SystemExit(f"RKF workspace config not found under configured root: {root}")
    mode = policy.get("mode", "active-aggressive") if isinstance(policy, dict) else "active-aggressive"
    return ConnectorConfig(researchwiki_root=root, mode=str(mode), config_path=config_path)


def _contains_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:220]


def classify_capture(*, text: str, source_url: str = "", project_name: str = "") -> CaptureDecision:
    haystack = f"{text}\n{source_url}\n{project_name}".strip()
    reasons: list[str] = []
    targets: list[str] = []
    if PRIVATE_PATH_RE.search(haystack):
        return CaptureDecision(level="blocked", targets=[], reasons=["private-path"], summary=_summary(text))
    if len(haystack) > LONG_CAPTURE_LIMIT:
        return CaptureDecision(level="blocked", targets=[], reasons=["too-long"], summary=_summary(text))
    if not haystack:
        return CaptureDecision(level="none", targets=[], reasons=[], summary="")

    if DOI_RE.search(haystack):
        reasons.append("doi")
    if ARXIV_RE.search(haystack):
        reasons.append("arxiv")
    if PUBMED_RE.search(haystack):
        reasons.append("pubmed")
    if URL_RE.search(source_url) or URL_RE.search(text):
        reasons.append("url")
    if _contains_any(haystack, ACTIVE_TERMS):
        reasons.append("source-like")
    if _contains_any(haystack, AGGRESSIVE_TERMS):
        reasons.append("research-discussion")

    if "research-discussion" in reasons:
        targets.append("inbox")
        if any(reason in reasons for reason in ("doi", "arxiv", "pubmed", "source-like")):
            targets.append("hot")
        return CaptureDecision(level="aggressive", targets=sorted(set(targets)), reasons=sorted(set(reasons)), summary=_summary(text))

    if reasons:
        targets.append("inbox")
        if any(reason in reasons for reason in ("doi", "arxiv", "pubmed", "source-like")):
            targets.append("hot")
        return CaptureDecision(level="active", targets=sorted(set(targets)), reasons=sorted(set(reasons)), summary=_summary(text))

    if _contains_any(haystack, CODING_ONLY_TERMS):
        return CaptureDecision(level="none", targets=[], reasons=["ordinary-coding"], summary=_summary(text))
    return CaptureDecision(level="none", targets=[], reasons=[], summary=_summary(text))


def build_inbox_request(
    *,
    config: ConnectorConfig,
    title: str,
    origin: str,
    clip: str,
    reader_note: str = "",
    agent_note: str = "",
    doi: str = "",
    source_url: str = "",
    topic_id: str = "",
    no_inject: bool = False,
) -> ActionRequest:
    _ = config
    return ActionRequest(
        action="inbox.capture",
        params={
            "title": title,
            "origin": origin,
            "clip": clip,
            "reader_note": reader_note,
            "agent_note": agent_note,
            "doi": doi,
            "source_url": source_url,
            "topic_id": topic_id,
            "inject": not no_inject,
        },
    )


def build_hot_request(
    *,
    config: ConnectorConfig,
    query: str,
    origin: str,
    intent: str = "research-discussion",
    topic_id: str = "",
    notes: str = "",
) -> ActionRequest:
    _ = config
    return ActionRequest(
        action="hot.record",
        params={
            "query": query,
            "origin": origin,
            "intent": intent,
            "topic_id": topic_id,
            "notes": notes,
        },
    )


def execute_action_request(*, config: ConnectorConfig, request: ActionRequest) -> ActionResult:
    return execute_rkf_action_request(request, workspace=Workspace(config.researchwiki_root))


def write_project_marker(project_root: Path, *, mode: str = "active-aggressive") -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    marker = project_root / ".rkf-connect.toml"
    marker.write_text(
        "[rkf_auto_connect]\n"
        "enabled = true\n"
        f"mode = \"{mode}\"\n"
        "config = \"global\"\n",
        encoding="utf-8",
    )
    return marker


def _bridge_template_readme(*, project_name: str, mode: str) -> str:
    return f"""# RKF Bridge

This folder is a project-local RKF bridge index for `{project_name}`. It is not
a copy of the RKF database and is not stable evidence.

## Source Of Truth

- Project marker: `../.rkf-connect.toml`
- Global connector config: `$HOME/.codex/rkf_connector.toml`
- Live RKF storage: resolved by the ResearchWiki checkout through
  `rkf.workspace.toml`

Do not store private Drive paths, secrets, PDFs, full article text, or whole
private transcripts here.

## Capture Mode

- mode: `{mode}`
- source-like material goes to RKF inbox and, when useful, central `hot.md`
- valuable research discussion can go to RKF inbox as reader/agent notes
- stable claims still need locators, supported RKF pages, or human feedback

## Files

- `hot.md`: project-local research demand queue
- `memory.md`: project-local retrieval hints for RKF
- `captures.md`: project-local capture log
"""


def _bridge_template_hot(*, project_name: str) -> str:
    return f"""# RKF Project Hot Queue

Scope: project-local demand queue for `{project_name}`; not stable evidence.

Use this file for research questions, search strings, DOI leads, and recurring
needs that should be routed to the central RKF `hot.md` through
`rk hot record`.

## Candidate Questions

- [ ] <research question>

## Search Strings

- <search string>

## Notes To Route

- <note>
"""


def _bridge_template_memory(*, project_name: str) -> str:
    return f"""# RKF Project Memory Index

Scope: project-local retrieval hints for `{project_name}`; not stable evidence.

Use this file to help future agents quickly find the right RKF context. Keep
entries short, public-safe, and pointer-oriented.

## Project Scope

- <scope note>

## Relevant RKF Topics

- <topic id or title>

## Relevant Papers Or Sources

- <paper, source id, DOI, or URL>

## Useful Queries

- <query>

## Boundaries

- Do not treat this file as source evidence.
- Do not paste article text, private paths, secrets, or whole transcripts.
- Promote only through RKF review, reading feedback, or source-backed pages.
"""


def _bridge_template_captures(*, project_name: str) -> str:
    return f"""# RKF Capture Log

Scope: project-local capture log for `{project_name}`; not stable evidence.

Record what was routed into RKF, where it went, and what remained unpromoted.

| Date | RKF target | Title or query | Boundary |
|---|---|---|---|
"""


def _write_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.write_text(text, encoding="utf-8")
    return True


def write_bridge_folder(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
    project_name: str = "",
) -> BridgeFolderResult:
    project_root.mkdir(parents=True, exist_ok=True)
    bridge = project_root / "RKF"
    bridge.mkdir(exist_ok=True)
    name = project_name or project_root.name
    templates = {
        bridge / "README.md": _bridge_template_readme(project_name=name, mode=mode),
        bridge / "hot.md": _bridge_template_hot(project_name=name),
        bridge / "memory.md": _bridge_template_memory(project_name=name),
        bridge / "captures.md": _bridge_template_captures(project_name=name),
    }
    created: list[Path] = []
    existing: list[Path] = []
    for path, text in templates.items():
        if _write_if_missing(path, text):
            created.append(path)
        else:
            existing.append(path)
    return BridgeFolderResult(root=bridge, created=created, existing=existing)


def read_project_marker(project_root: Path) -> dict[str, Any]:
    marker = project_root / ".rkf-connect.toml"
    if not marker.exists():
        return {"enabled": False, "mode": ""}
    data = _load_toml(marker)
    section = data.get("rkf_auto_connect", {}) if isinstance(data, dict) else {}
    return section if isinstance(section, dict) else {"enabled": False, "mode": ""}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rkf-auto-connect", description="Classify and route cross-project RKF captures")
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--config")

    classify = sub.add_parser("classify")
    classify.add_argument("text")
    classify.add_argument("--source-url", default="")
    classify.add_argument("--project-name", default="")

    marker = sub.add_parser("mark-project")
    marker.add_argument("project_root")
    marker.add_argument("--mode", default="active-aggressive")

    bridge = sub.add_parser("bridge-folder")
    bridge.add_argument("project_root")
    bridge.add_argument("--mode", default="active-aggressive")
    bridge.add_argument("--project-name", default="")

    inbox_request = sub.add_parser("inbox-request")
    inbox_request.add_argument("title")
    inbox_request.add_argument("--origin", required=True)
    inbox_request.add_argument("--clip", required=True)
    inbox_request.add_argument("--reader-note", default="")
    inbox_request.add_argument("--agent-note", default="")
    inbox_request.add_argument("--doi", default="")
    inbox_request.add_argument("--source-url", default="")
    inbox_request.add_argument("--topic-id", default="")
    inbox_request.add_argument("--no-inject", action="store_true")

    hot_request = sub.add_parser("hot-request")
    hot_request.add_argument("query")
    hot_request.add_argument("--origin", required=True)
    hot_request.add_argument("--intent", default="research-discussion")
    hot_request.add_argument("--topic-id", default="")
    hot_request.add_argument("--notes", default="")

    inbox_execute = sub.add_parser("inbox-execute")
    inbox_execute.add_argument("title")
    inbox_execute.add_argument("--origin", required=True)
    inbox_execute.add_argument("--clip", required=True)
    inbox_execute.add_argument("--reader-note", default="")
    inbox_execute.add_argument("--agent-note", default="")
    inbox_execute.add_argument("--doi", default="")
    inbox_execute.add_argument("--source-url", default="")
    inbox_execute.add_argument("--topic-id", default="")
    inbox_execute.add_argument("--no-inject", action="store_true")

    hot_execute = sub.add_parser("hot-execute")
    hot_execute.add_argument("query")
    hot_execute.add_argument("--origin", required=True)
    hot_execute.add_argument("--intent", default="research-discussion")
    hot_execute.add_argument("--topic-id", default="")
    hot_execute.add_argument("--notes", default="")

    args = parser.parse_args(argv)
    if args.command == "resolve":
        config = load_connector_config(Path(args.config).expanduser() if args.config else None)
        print(json.dumps({"researchwiki_root": str(config.researchwiki_root), "mode": config.mode}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "classify":
        decision = classify_capture(text=args.text, source_url=args.source_url, project_name=args.project_name)
        print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
        return 0
    if args.command == "mark-project":
        path = write_project_marker(Path(args.project_root).expanduser().resolve(), mode=args.mode)
        print(path)
        return 0
    if args.command == "bridge-folder":
        result = write_bridge_folder(
            Path(args.project_root).expanduser().resolve(),
            mode=args.mode,
            project_name=args.project_name,
        )
        payload = {
            "root": str(result.root),
            "created": [str(path) for path in result.created],
            "existing": [str(path) for path in result.existing],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    config = load_connector_config()
    if args.command in {"inbox-request", "inbox-execute"}:
        request = build_inbox_request(
            config=config,
            title=args.title,
            origin=args.origin,
            clip=args.clip,
            reader_note=args.reader_note,
            agent_note=args.agent_note,
            doi=args.doi,
            source_url=args.source_url,
            topic_id=args.topic_id,
            no_inject=args.no_inject,
        )
        if args.command == "inbox-request":
            print(json.dumps(asdict(request), ensure_ascii=False, indent=2))
            return 0
        result = execute_action_request(config=config, request=request)
        print(result.message)
        if result.payload.get("source_id"):
            print(f"source_id: {result.payload['source_id']}")
        return 0
    if args.command in {"hot-request", "hot-execute"}:
        request = build_hot_request(
            config=config,
            query=args.query,
            origin=args.origin,
            intent=args.intent,
            topic_id=args.topic_id,
            notes=args.notes,
        )
        if args.command == "hot-request":
            print(json.dumps(asdict(request), ensure_ascii=False, indent=2))
            return 0
        result = execute_action_request(config=config, request=request)
        print(result.message)
        return 0
    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
