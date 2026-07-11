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

from rkf.actions import ActionRequest, ActionResult, RKFActionRuntime
from rkf.capture import CaptureInput, classify_capture as classify_rkf_capture
from rkf.core import Workspace

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


DEFAULT_CONFIG = Path(os.environ.get("RKF_CONNECTOR_CONFIG", "~/.codex/rkf_connector.toml")).expanduser()


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


def _summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:220]


def classify_capture(*, text: str, source_url: str = "", project_name: str = "") -> CaptureDecision:
    decision = classify_rkf_capture(
        CaptureInput(
            text=text,
            origin=f"project:{project_name}" if project_name else "codex",
            source_url=source_url,
        )
    )
    return CaptureDecision(
        level=decision.level,
        targets=decision.targets,
        reasons=decision.reasons,
        summary=_summary(text),
    )


def build_activate_request(*, config: ConnectorConfig) -> ActionRequest:
    _ = config
    return ActionRequest(action="rkf.activate")


def build_query_request(
    *,
    config: ConnectorConfig,
    query: str,
    limit: int = 10,
) -> ActionRequest:
    _ = config
    return ActionRequest(action="query.search", params={"query": query, "limit": limit})


def build_capture_request(
    *,
    config: ConnectorConfig,
    title: str,
    text: str,
    origin: str,
    doi: str = "",
    source_url: str = "",
    authors: str = "",
    year: str = "",
    intent: str = "research-discussion",
    reader_note: str = "",
    agent_note: str = "",
    topic_id: str = "",
) -> ActionRequest:
    _ = config
    return ActionRequest(
        action="capture.route",
        params={
            "title": title,
            "text": text,
            "origin": origin,
            "doi": doi,
            "source_url": source_url,
            "authors": authors,
            "year": year,
            "intent": intent,
            "reader_note": reader_note,
            "agent_note": agent_note,
            "topic_id": topic_id,
        },
    )


def execute_action_request(
    *,
    config: ConnectorConfig,
    request: ActionRequest,
    runtime: RKFActionRuntime | None = None,
) -> ActionResult:
    active_runtime = runtime or RKFActionRuntime(
        workspace=Workspace(config.researchwiki_root)
    )
    return active_runtime.execute(request)


def render_project_marker(*, mode: str) -> str:
    return (
        "version = 2\n\n"
        "[rkf]\n"
        "available = true\n"
        'activation = "manual"\n'
        "query_first = true\n"
        f'capture_mode = "{mode}"\n'
    )


def preview_project_marker(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
) -> dict[str, Any]:
    marker = project_root / ".rkf-connect.toml"
    current = read_project_marker(project_root)
    proposed = render_project_marker(mode=mode)
    return {
        "path": ".rkf-connect.toml",
        "from_version": int(current["version"]),
        "to_version": 2,
        "would_change": not marker.exists()
        or marker.read_text(encoding="utf-8") != proposed,
        "proposed": proposed,
    }


def write_project_marker(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
    approve_upgrade: bool = False,
) -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    marker = project_root / ".rkf-connect.toml"
    current = read_project_marker(project_root)
    if marker.exists() and int(current["version"]) < 2 and not approve_upgrade:
        raise SystemExit("v1 marker upgrade requires preview and explicit approval")
    marker.write_text(render_project_marker(mode=mode), encoding="utf-8")
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

- every new Codex task starts with RKF OFF
- say `啟動 RKF` before central query or capture
- mode: `{mode}`
- activated research requests use `query.search` before project-local retrieval
- reusable source/discussion material uses `capture.route`
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
`capture.route` after RKF is activated in the current task.

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
        return {
            "version": 0,
            "available": False,
            "activation": "manual",
            "query_first": True,
            "capture_mode": "off",
        }
    data = _load_toml(marker)
    version = int(data.get("version", 1))
    if version >= 2:
        section = data.get("rkf", {})
        return {
            "version": version,
            "available": bool(section.get("available", False)),
            "activation": "manual",
            "query_first": bool(section.get("query_first", True)),
            "capture_mode": str(section.get("capture_mode", "active-aggressive")),
        }
    section = data.get("rkf_auto_connect", {})
    return {
        "version": 1,
        "available": bool(section.get("enabled", False)),
        "activation": "manual",
        "query_first": True,
        "capture_mode": str(section.get("mode", "active-aggressive")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rkf-auto-connect",
        description="Classify and route cross-project RKF captures",
    )
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
    marker.add_argument("--apply-upgrade", action="store_true")

    bridge = sub.add_parser("bridge-folder")
    bridge.add_argument("project_root")
    bridge.add_argument("--mode", default="active-aggressive")
    bridge.add_argument("--project-name", default="")

    sub.add_parser("activate-request")

    query_request = sub.add_parser("query-request")
    query_request.add_argument("query")
    query_request.add_argument("--limit", type=int, default=10)

    capture_request = sub.add_parser("capture-request")
    capture_request.add_argument("title")
    capture_request.add_argument("--text", required=True)
    capture_request.add_argument("--origin", required=True)
    capture_request.add_argument("--doi", default="")
    capture_request.add_argument("--source-url", default="")
    capture_request.add_argument("--authors", default="")
    capture_request.add_argument("--year", default="")
    capture_request.add_argument("--intent", default="research-discussion")
    capture_request.add_argument("--reader-note", default="")
    capture_request.add_argument("--agent-note", default="")
    capture_request.add_argument("--topic-id", default="")

    args = parser.parse_args(argv)
    if args.command == "resolve":
        config = load_connector_config(
            Path(args.config).expanduser() if args.config else None
        )
        print(
            json.dumps(
                {
                    "researchwiki": "configured",
                    "workspace_config": True,
                    "mode": config.mode,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "classify":
        decision = classify_capture(text=args.text, source_url=args.source_url, project_name=args.project_name)
        print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
        return 0
    if args.command == "mark-project":
        project_root = Path(args.project_root).expanduser().resolve()
        marker_path = project_root / ".rkf-connect.toml"
        if marker_path.exists() and not args.apply_upgrade:
            print(
                json.dumps(
                    preview_project_marker(project_root, mode=args.mode),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        path = write_project_marker(
            project_root,
            mode=args.mode,
            approve_upgrade=args.apply_upgrade,
        )
        print(path.name)
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
    if args.command == "activate-request":
        print(
            json.dumps(
                asdict(build_activate_request(config=config)),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "query-request":
        request = build_query_request(
            config=config,
            query=args.query,
            limit=args.limit,
        )
        print(json.dumps(asdict(request), ensure_ascii=False, indent=2))
        return 0
    if args.command == "capture-request":
        request = build_capture_request(
            config=config,
            title=args.title,
            text=args.text,
            origin=args.origin,
            doi=args.doi,
            source_url=args.source_url,
            authors=args.authors,
            year=args.year,
            intent=args.intent,
            reader_note=args.reader_note,
            agent_note=args.agent_note,
            topic_id=args.topic_id,
        )
        print(json.dumps(asdict(request), ensure_ascii=False, indent=2))
        return 0
    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
