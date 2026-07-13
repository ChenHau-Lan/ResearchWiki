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
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rkf.actions import ActionRequest, ActionResult, RKFActionRuntime
from rkf.capture import CaptureInput, classify_capture as classify_rkf_capture
from rkf.core import Workspace, load_toml


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


BRIDGE_FILENAMES = ("README.md", "hot.md", "memory.md", "captures.md")
CAPTURE_MODES = {"active-aggressive", "active", "off"}
PROJECT_NAME_RE = re.compile(r"^[\w .()\-]{1,100}$", re.UNICODE)


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit("RKF TOML config was not found")
    try:
        return load_toml(path)
    except (OSError, UnicodeDecodeError, ValueError, TypeError) as error:
        raise SystemExit("RKF TOML config is unreadable or invalid") from error


def _validated_mode(mode: str) -> str:
    if mode not in CAPTURE_MODES:
        raise SystemExit("RKF capture mode must be active-aggressive, active, or off")
    return mode


def _validated_project_root(project_root: Path) -> Path:
    requested = project_root.expanduser()
    if requested.is_symlink() or not requested.is_dir():
        raise SystemExit("RKF project root must be an existing, non-symlink directory")
    return requested.resolve()


def _validated_project_name(value: str) -> str:
    if not isinstance(value, str):
        raise SystemExit("RKF project name must be text")
    name = " ".join(value.split())
    if not PROJECT_NAME_RE.fullmatch(name):
        raise SystemExit(
            "RKF project name must use letters, numbers, spaces, dots, parentheses, hyphens, or underscores"
        )
    return name


def _assert_no_symlink(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise SystemExit(f"RKF refuses a symlink at the project-local {label}")


def _directory_is_writable(path: Path) -> bool:
    return (
        path.is_dir()
        and not path.is_symlink()
        and os.access(path, os.W_OK | os.X_OK)
    )


def _remove_created_file(path: Path, expected: bytes) -> None:
    if path.is_symlink() or not path.is_file():
        return
    try:
        if path.read_bytes() == expected:
            path.unlink()
    except OSError:
        return


def _write_new_owned_text(path: Path, text: str) -> bytes:
    """Exclusively create a file and remove a partial file on write failure."""

    payload = text.encode("utf-8")
    created = False
    identity: tuple[int, int] | None = None
    try:
        with path.open("xb") as handle:
            created = True
            stat = os.fstat(handle.fileno())
            identity = (stat.st_dev, stat.st_ino)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if created and identity is not None and not path.is_symlink():
            try:
                current = path.stat(follow_symlinks=False)
                if (current.st_dev, current.st_ino) == identity:
                    path.unlink()
            except OSError:
                pass
        raise
    return payload


def _atomic_replace_text(path: Path, text: str, *, expected_old: bytes) -> None:
    """Replace a known marker through a same-directory, fsynced temporary file."""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".rkf-connect.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    payload = text.encode("utf-8")
    descriptor_owned = True
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor_owned = False
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink() or not path.is_file() or path.read_bytes() != expected_old:
            raise OSError("project marker changed during atomic replacement")
        try:
            os.chmod(temporary, path.stat().st_mode & 0o777)
        except OSError:
            pass
        os.replace(temporary, path)
    finally:
        if descriptor_owned:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary.exists() and not temporary.is_symlink():
            try:
                temporary.unlink()
            except OSError:
                pass


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
        raise SystemExit("RKF checkout is unavailable under the configured root")
    if not ((root / "rkf.workspace.toml").exists() or (root / "workspace.toml").exists()):
        raise SystemExit("RKF workspace config is unavailable under the configured root")
    mode = policy.get("mode", "active-aggressive") if isinstance(policy, dict) else "active-aggressive"
    return ConnectorConfig(
        researchwiki_root=root,
        mode=_validated_mode(str(mode)),
        config_path=config_path,
    )


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
        summary="redacted" if decision.level == "blocked" else _summary(text),
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
    create_paper_draft: bool = True,
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
            "create_paper_draft": create_paper_draft,
        },
    )


def execute_action_request(
    *,
    config: ConnectorConfig,
    request: ActionRequest,
    runtime: RKFActionRuntime | None = None,
) -> ActionResult:
    active_runtime = runtime or open_action_runtime(
        config=config,
        project_root=config.researchwiki_root,
    )
    return active_runtime.execute(request)


def open_action_runtime(
    *,
    config: ConnectorConfig,
    project_root: Path | None = None,
) -> RKFActionRuntime:
    """Open one task-owned runtime for the current or explicit connected project.

    Callers must reuse the returned object for activation and later actions in
    the same Codex task.  Project-marker validation remains inside
    ``rkf.activate``; opening the runtime never persists ACTIVE state.
    """

    active_project = _validated_project_root(project_root or Path.cwd())
    if active_project != config.researchwiki_root.resolve():
        policy = read_project_marker(active_project)
        if policy["version"] not in {1, 2} or policy["available"] is not True:
            raise SystemExit("RKF project is not connected or available")
    return RKFActionRuntime(
        workspace=Workspace(config.researchwiki_root),
        project_root=active_project,
    )


def render_project_marker(*, mode: str) -> str:
    mode = _validated_mode(mode)
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
    root = _validated_project_root(project_root)
    mode = _validated_mode(mode)
    marker = root / ".rkf-connect.toml"
    _assert_no_symlink(marker, label="marker")
    current = read_project_marker(root)
    proposed = render_project_marker(mode=mode)
    if current["version"] == 2:
        semantic_match = (
            current["available"] is True
            and current["activation"] == "manual"
            and current["query_first"] is True
            and current["capture_mode"] == mode
        )
        return {
            "path": ".rkf-connect.toml",
            "from_version": 2,
            "to_version": 2,
            "would_change": not semantic_match,
            "requires_manual_edit": not semantic_match,
            "proposed": proposed,
        }
    return {
        "path": ".rkf-connect.toml",
        "from_version": int(current["version"]),
        "to_version": 2,
        "would_change": not marker.exists()
        or marker.read_text(encoding="utf-8") != proposed,
        "requires_manual_edit": False,
        "proposed": proposed,
    }


def write_project_marker(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
    approve_upgrade: bool = False,
) -> Path:
    root = _validated_project_root(project_root)
    mode = _validated_mode(mode)
    marker = root / ".rkf-connect.toml"
    _assert_no_symlink(marker, label="marker")
    current = read_project_marker(root)
    if int(current["version"]) == 2:
        preview = preview_project_marker(root, mode=mode)
        if preview["would_change"]:
            raise SystemExit(
                "existing v2 marker has a different policy; edit it manually to preserve user content"
            )
        return marker
    if marker.exists() and int(current["version"]) < 2 and not approve_upgrade:
        raise SystemExit("v1 marker upgrade requires preview and explicit approval")
    if not _directory_is_writable(root):
        raise SystemExit("project root is not writable for the RKF marker")
    rendered = render_project_marker(mode=mode)
    try:
        if marker.exists():
            original = marker.read_bytes()
            _atomic_replace_text(marker, rendered, expected_old=original)
        else:
            _write_new_owned_text(marker, rendered)
    except (OSError, RuntimeError) as error:
        raise SystemExit("RKF marker write failed safely without a partial replacement") from error
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


def _bridge_templates(*, bridge: Path, project_name: str, mode: str) -> dict[Path, str]:
    return {
        bridge / "README.md": _bridge_template_readme(project_name=project_name, mode=mode),
        bridge / "hot.md": _bridge_template_hot(project_name=project_name),
        bridge / "memory.md": _bridge_template_memory(project_name=project_name),
        bridge / "captures.md": _bridge_template_captures(project_name=project_name),
    }


def _write_if_missing(path: Path, text: str) -> bool:
    if path.is_symlink():
        raise SystemExit("RKF bridge files must not be symlinks")
    if path.exists():
        return False
    try:
        _write_new_owned_text(path, text)
    except FileExistsError:
        if path.is_symlink() or not path.is_file():
            raise SystemExit("RKF bridge target changed to an unsafe file")
        return False
    return True


def _rollback_bridge_files(
    *,
    bridge: Path,
    created: list[Path],
    templates: dict[Path, str],
    remove_bridge: bool,
) -> None:
    for path in reversed(created):
        _remove_created_file(path, templates[path].encode("utf-8"))
    if remove_bridge:
        try:
            bridge.rmdir()
        except OSError:
            pass


def write_bridge_folder(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
    project_name: str = "",
) -> BridgeFolderResult:
    root = _validated_project_root(project_root)
    mode = _validated_mode(mode)
    name = _validated_project_name(project_name or root.name)
    bridge = root / "RKF"
    _assert_no_symlink(bridge, label="RKF bridge folder")
    if bridge.exists() and not bridge.is_dir():
        raise SystemExit("project-local RKF bridge target must be a directory")
    for filename in BRIDGE_FILENAMES:
        path = bridge / filename
        _assert_no_symlink(path, label=f"RKF/{filename}")
        if path.exists() and not path.is_file():
            raise SystemExit("project-local RKF bridge file target must be a regular file")
    missing = [bridge / filename for filename in BRIDGE_FILENAMES if not (bridge / filename).exists()]
    if not bridge.exists() and not _directory_is_writable(root):
        raise SystemExit("project root is not writable for the RKF bridge")
    if bridge.exists() and missing and not _directory_is_writable(bridge):
        raise SystemExit("project-local RKF bridge folder is not writable")
    bridge_created = False
    if not bridge.exists():
        try:
            bridge.mkdir()
            bridge_created = True
        except FileExistsError:
            _assert_no_symlink(bridge, label="RKF bridge folder")
            if not bridge.is_dir():
                raise SystemExit("project-local RKF bridge target changed unsafely")
        except OSError as error:
            raise SystemExit("RKF bridge folder could not be created safely") from error
    templates = _bridge_templates(bridge=bridge, project_name=name, mode=mode)
    created: list[Path] = []
    existing: list[Path] = []
    try:
        for path, text in templates.items():
            if _write_if_missing(path, text):
                created.append(path)
            else:
                existing.append(path)
    except (OSError, RuntimeError) as error:
        _rollback_bridge_files(
            bridge=bridge,
            created=created,
            templates=templates,
            remove_bridge=bridge_created,
        )
        raise SystemExit("RKF bridge write failed safely and was rolled back") from error
    except BaseException:
        _rollback_bridge_files(
            bridge=bridge,
            created=created,
            templates=templates,
            remove_bridge=bridge_created,
        )
        raise
    return BridgeFolderResult(root=bridge, created=created, existing=existing)


def preview_project_connection(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
    project_name: str = "",
) -> dict[str, Any]:
    root = _validated_project_root(project_root)
    mode = _validated_mode(mode)
    _validated_project_name(project_name or root.name)
    marker = preview_project_marker(root, mode=mode)
    bridge = root / "RKF"
    _assert_no_symlink(bridge, label="RKF bridge folder")
    if bridge.exists() and not bridge.is_dir():
        raise SystemExit("project-local RKF bridge target must be a directory")
    for name in BRIDGE_FILENAMES:
        path = bridge / name
        _assert_no_symlink(path, label=f"RKF/{name}")
        if path.exists() and not path.is_file():
            raise SystemExit("project-local RKF bridge file target must be a regular file")
    missing = [name for name in BRIDGE_FILENAMES if not (bridge / name).exists()]
    if marker["would_change"] and not _directory_is_writable(root):
        raise SystemExit("project root is not writable for the RKF marker")
    if missing and not bridge.exists() and not _directory_is_writable(root):
        raise SystemExit("project root is not writable for the RKF bridge")
    if missing and bridge.exists() and not _directory_is_writable(bridge):
        raise SystemExit("project-local RKF bridge folder is not writable")
    return {
        "schema": "rkf-project-connection-preview-v1",
        "mode": mode,
        "marker": {
            "from_version": marker["from_version"],
            "to_version": marker["to_version"],
            "would_change": marker["would_change"],
            "requires_upgrade_approval": marker["from_version"] == 1,
            "requires_manual_edit": marker["requires_manual_edit"],
        },
        "bridge": {
            "missing_files": missing,
            "existing_count": len(BRIDGE_FILENAMES) - len(missing),
            "would_overwrite": False,
        },
        "activation": "manual",
        "canonical_database_created": False,
        "paths_redacted": True,
    }


def connect_project(
    project_root: Path,
    *,
    mode: str = "active-aggressive",
    approve_upgrade: bool = False,
    project_name: str = "",
) -> dict[str, Any]:
    root = _validated_project_root(project_root)
    mode = _validated_mode(mode)
    preview = preview_project_connection(root, mode=mode, project_name=project_name)
    if preview["marker"]["requires_manual_edit"]:
        raise SystemExit("existing v2 marker requires a manual policy edit")
    if preview["marker"]["requires_upgrade_approval"] and not approve_upgrade:
        raise SystemExit("v1 marker upgrade requires preview and explicit approval")
    normalized_name = _validated_project_name(project_name or root.name)
    bridge_path = root / "RKF"
    bridge_existed = bridge_path.exists()
    bridge: BridgeFolderResult | None = None
    templates = _bridge_templates(
        bridge=bridge_path,
        project_name=normalized_name,
        mode=mode,
    )
    try:
        bridge = write_bridge_folder(
            root,
            mode=mode,
            project_name=normalized_name,
        )
        if preview["marker"]["would_change"]:
            write_project_marker(
                root,
                mode=mode,
                approve_upgrade=approve_upgrade,
            )
    except BaseException:
        if bridge is not None:
            _rollback_bridge_files(
                bridge=bridge.root,
                created=bridge.created,
                templates=templates,
                remove_bridge=not bridge_existed,
            )
        raise
    assert bridge is not None
    return {
        "schema": "rkf-project-connection-result-v1",
        "status": "connected",
        "marker_version": 2,
        "activation": "manual",
        "bridge_created_count": len(bridge.created),
        "bridge_existing_count": len(bridge.existing),
        "canonical_database_created": False,
        "paths_redacted": True,
    }


def read_project_marker(project_root: Path) -> dict[str, Any]:
    root = _validated_project_root(project_root)
    marker = root / ".rkf-connect.toml"
    _assert_no_symlink(marker, label="marker")
    if not marker.exists():
        return {
            "version": 0,
            "available": False,
            "activation": "manual",
            "query_first": True,
            "capture_mode": "off",
        }
    data = _load_toml(marker)
    raw_version = data.get("version", 1)
    if type(raw_version) is not int:
        raise SystemExit("RKF project marker version must be an integer")
    version = raw_version
    if version > 2:
        raise SystemExit("RKF project marker uses a newer unsupported version")
    if version not in {1, 2}:
        raise SystemExit("RKF project marker version is unsupported")
    if version == 2:
        section = data.get("rkf", {})
        if not isinstance(section, dict):
            raise SystemExit("RKF v2 project marker is invalid")
        available = section.get("available", False)
        activation = section.get("activation", "manual")
        query_first = section.get("query_first", True)
        capture_mode = section.get("capture_mode", "active-aggressive")
        if (
            not isinstance(available, bool)
            or activation != "manual"
            or not isinstance(query_first, bool)
            or not isinstance(capture_mode, str)
            or capture_mode not in CAPTURE_MODES
        ):
            raise SystemExit("RKF v2 project marker is invalid")
        return {
            "version": version,
            "available": available,
            "activation": "manual",
            "query_first": query_first,
            "capture_mode": str(capture_mode),
        }
    section = data.get("rkf_auto_connect", {})
    if not isinstance(section, dict):
        raise SystemExit("legacy RKF project marker is invalid")
    enabled = section.get("enabled", False)
    legacy_mode = section.get("mode", "active-aggressive")
    if not isinstance(enabled, bool) or not isinstance(legacy_mode, str):
        raise SystemExit("legacy RKF project marker is invalid")
    _validated_mode(legacy_mode)
    return {
        "version": 1,
        "available": enabled,
        "activation": "manual",
        "query_first": True,
        "capture_mode": legacy_mode,
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
    marker.add_argument("--mode", choices=sorted(CAPTURE_MODES), default="active-aggressive")
    marker.add_argument("--apply-upgrade", action="store_true")

    bridge = sub.add_parser("bridge-folder")
    bridge.add_argument("project_root")
    bridge.add_argument("--mode", choices=sorted(CAPTURE_MODES), default="active-aggressive")
    bridge.add_argument("--project-name", default="")

    connect = sub.add_parser(
        "connect-project",
        help="Preview or create the v2 marker and non-canonical RKF bridge",
    )
    connect.add_argument("project_root")
    connect.add_argument("--mode", choices=sorted(CAPTURE_MODES), default="active-aggressive")
    connect.add_argument("--project-name", default="")
    connect.add_argument("--apply", action="store_true")
    connect.add_argument("--apply-upgrade", action="store_true")

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
    capture_request.add_argument("--no-paper-draft", action="store_true")

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
        project_root = Path(args.project_root).expanduser()
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
            Path(args.project_root).expanduser(),
            mode=args.mode,
            project_name=args.project_name,
        )
        payload = {
            "schema": "rkf-project-bridge-result-v2",
            "status": "ready",
            "created_count": len(result.created),
            "existing_count": len(result.existing),
            "paths_redacted": True,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "connect-project":
        project_root = Path(args.project_root).expanduser()
        payload = (
            connect_project(
                project_root,
                mode=args.mode,
                approve_upgrade=args.apply_upgrade,
                project_name=args.project_name,
            )
            if args.apply
            else preview_project_connection(
                project_root,
                mode=args.mode,
                project_name=args.project_name,
            )
        )
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
            create_paper_draft=not args.no_paper_draft,
        )
        print(json.dumps(asdict(request), ensure_ascii=False, indent=2))
        return 0
    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
