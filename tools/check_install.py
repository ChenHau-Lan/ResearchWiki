#!/usr/bin/env python3
"""Run a read-only, path-redacted RKF installation diagnostic."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rkf.core import Workspace, load_toml
from rkf.sync import run_connect_doctor


CODEX_SKILL_NAME = "rkf-auto-connect"
CODEX_SKILL_FILES = (Path("SKILL.md"), Path("agents/openai.yaml"))
CODEX_SKILL_DIRS = (Path("agents"),)
CODEX_SKILL_MANIFEST = {
    **{path: "file" for path in CODEX_SKILL_FILES},
    **{path: "directory" for path in CODEX_SKILL_DIRS},
}
CAPTURE_MODES = {"active-aggressive", "active", "off"}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    message: str


def _skill_tree_manifest(root: Path) -> dict[Path, str] | None:
    if root.is_symlink() or not root.is_dir():
        return None
    manifest: dict[Path, str] = {}
    pending = [root]
    try:
        while pending:
            directory = pending.pop()
            for child in directory.iterdir():
                relative = child.relative_to(root)
                if child.is_symlink():
                    manifest[relative] = "symlink"
                elif child.is_dir():
                    manifest[relative] = "directory"
                    pending.append(child)
                elif child.is_file():
                    manifest[relative] = "file"
                else:
                    manifest[relative] = "other"
    except (OSError, RuntimeError):
        return None
    return manifest


def _exact_skill_manifest(root: Path) -> bool:
    return _skill_tree_manifest(root) == CODEX_SKILL_MANIFEST


def _result(checks: list[Check]) -> dict[str, object]:
    failures = sum(check.status == "fail" for check in checks)
    warnings = sum(check.status == "warn" for check in checks)
    return {
        "schema": "rkf-install-diagnostic-v1",
        "status": "ready" if failures == 0 else "blocked",
        "failure_count": failures,
        "warning_count": warnings,
        "checks": [asdict(check) for check in checks],
        "paths_redacted": True,
        "secrets_checked": False,
    }


def _redacted_runtime_failure() -> dict[str, object]:
    return _result(
        [
            Check(
                "diagnostic_runtime",
                "fail",
                "installation diagnostic could not resolve the configured paths safely",
            )
        ]
    )


def _connector_status(path: Path, *, expected_root: Path) -> Check:
    try:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            return Check("cross_project_connector", "fail", "connector config target is unsafe")
        if not path.exists():
            return Check("cross_project_connector", "warn", "optional connector config is not installed")
        data = load_toml(path)
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError, TypeError):
        return Check("cross_project_connector", "fail", "connector config is unreadable or invalid")
    section = data.get("researchwiki", {}) if isinstance(data, dict) else {}
    policy = data.get("policy", {}) if isinstance(data, dict) else {}
    root = section.get("root") if isinstance(section, dict) else None
    if not isinstance(root, str) or not root.strip():
        return Check("cross_project_connector", "fail", "connector config is missing researchwiki.root")
    mode = policy.get("mode", "active-aggressive") if isinstance(policy, dict) else None
    if not isinstance(mode, str) or mode not in CAPTURE_MODES:
        return Check("cross_project_connector", "fail", "connector policy mode is invalid")
    configured = Path(os.path.expandvars(os.path.expanduser(root)))
    try:
        available = (
            configured.is_dir()
            and configured.resolve() == expected_root.resolve()
            and any(
                (configured / name).is_file() and not (configured / name).is_symlink()
                for name in ("rkf.workspace.toml", "workspace.toml")
            )
        )
    except (OSError, RuntimeError):
        available = False
    if not available:
        return Check(
            "cross_project_connector",
            "fail",
            "connector points to a different or unavailable RKF checkout",
        )
    return Check("cross_project_connector", "pass", "connector config is present")


def _codex_skill_status(repo_root: Path, target_dir: Path, *, required: bool) -> Check:
    source_dir = repo_root / "skills" / CODEX_SKILL_NAME
    source_files = [source_dir / relative for relative in CODEX_SKILL_FILES]
    target_files = [target_dir / relative for relative in CODEX_SKILL_FILES]
    if not _exact_skill_manifest(source_dir) or not all(
        path.is_file() and not path.is_symlink() for path in source_files
    ):
        return Check("codex_auto_connect_skill", "fail", "repository auto-connect skill bundle is incomplete")
    if target_dir.exists() or target_dir.is_symlink():
        if not _exact_skill_manifest(target_dir):
            return Check("codex_auto_connect_skill", "fail", "installed auto-connect skill target is unsafe or not exact")
    if target_dir.is_symlink() or any(path.is_symlink() for path in target_files):
        return Check("codex_auto_connect_skill", "fail", "installed auto-connect skill target is unsafe")
    if not all(path.is_file() for path in target_files):
        return Check(
            "codex_auto_connect_skill",
            "fail" if required else "warn",
            "auto-connect skill bundle is required by the connector but is incomplete"
            if required
            else "optional auto-connect skill bundle is not installed",
        )
    try:
        matches = all(
            source.read_bytes() == target.read_bytes()
            for source, target in zip(source_files, target_files)
        )
    except OSError:
        matches = False
    return Check(
        "codex_auto_connect_skill",
        "pass" if matches else ("fail" if required else "warn"),
        "installed auto-connect skill matches this checkout"
        if matches
        else "installed auto-connect skill differs from this checkout; review before replacing it",
    )


def inspect_install(
    repo_root: Path,
    *,
    connector_path: Path | None = None,
    codex_skill_dir: Path | None = None,
) -> dict[str, object]:
    try:
        root = repo_root.resolve()
    except (OSError, RuntimeError):
        return _redacted_runtime_failure()
    checks: list[Check] = []
    checks.append(
        Check(
            "python",
            "pass" if sys.version_info >= (3, 9) else "fail",
            "supported Python runtime" if sys.version_info >= (3, 9) else "Python 3.9 or newer is required",
        )
    )
    required = ["AGENTS.md", "README.md", "rkf/actions.py", "tools/rk.py"]
    try:
        missing = [
            name
            for name in required
            if not (root / name).is_file() or (root / name).is_symlink()
        ]
    except (OSError, RuntimeError):
        missing = list(required)
    checks.append(
        Check(
            "repository",
            "fail" if missing else "pass",
            "required repository files are missing" if missing else "repository files are present",
        )
    )
    workspace_config = root / "rkf.workspace.toml"
    if workspace_config.is_symlink():
        checks.append(Check("workspace_config", "fail", "workspace configuration target is unsafe"))
    elif not workspace_config.exists():
        checks.append(Check("workspace_config", "fail", "rkf.workspace.toml has not been initialized"))
    else:
        try:
            workspace = Workspace(root)
        except (OSError, RuntimeError, UnicodeDecodeError, ValueError, TypeError):
            workspace = None
            checks.append(Check("workspace_config", "fail", "workspace configuration is unreadable or invalid"))
        else:
            checks.append(Check("workspace_config", "pass", "workspace configuration is present"))
        if workspace is not None:
            handles = [
                workspace.paths.wiki_root,
                workspace.paths.raw_root,
                workspace.paths.private_evidence,
            ]
            handles_ready = all(
                path.is_dir() and os.access(path, os.R_OK) for path in handles
            )
            checks.append(
                Check(
                    "storage_handles",
                    "pass" if handles_ready else "fail",
                    "configured storage handles are available"
                    if handles_ready
                    else "one or more configured storage handles are unavailable",
                )
            )
            machine = workspace.config.get("machine", {}) if isinstance(workspace.config, dict) else {}
            requested_writer = bool(machine.get("maintenance_writer", False)) if isinstance(machine, dict) else False
            if requested_writer:
                writable = handles_ready and all(os.access(path, os.W_OK) for path in handles)
                checks.append(
                    Check(
                        "writer_storage_access",
                        "pass" if writable else "fail",
                        "designated writer storage is writable"
                        if writable
                        else "designated writer storage is not writable",
                    )
                )
            try:
                doctor = run_connect_doctor(workspace)
            except (OSError, RuntimeError, UnicodeDecodeError, ValueError, TypeError):
                checks.append(
                    Check(
                        "connection_doctor",
                        "fail",
                        "connection doctor could not complete safely",
                    )
                )
            else:
                blocker_count = sum(
                    finding.severity == "blocker" for finding in doctor.findings
                )
                doctor_status = {
                    "ok": "pass",
                    "warning": "warn",
                    "blocked": "fail",
                }[doctor.status]
                checks.append(
                    Check(
                        "connection_doctor",
                        doctor_status,
                        (
                            "connection doctor passed"
                            if doctor.status == "ok"
                            else (
                                f"connection doctor reported {len(doctor.findings)} warning(s)"
                                if doctor.status == "warning"
                                else f"connection doctor reported {blocker_count} blocker(s)"
                            )
                        ),
                    )
                )
    try:
        skill_count = sum(
            path.is_file() and not path.is_symlink()
            for path in (root / "skills").glob("rkf-*/SKILL.md")
        )
    except (OSError, RuntimeError):
        skill_count = 0
    checks.append(
        Check(
            "rkf_skill_docs",
            "pass" if skill_count >= 4 else "warn",
            f"found {skill_count} repository RKF skill guide(s)",
        )
    )
    connector = connector_path or Path(
        os.environ.get("RKF_CONNECTOR_CONFIG", "~/.codex/rkf_connector.toml")
    ).expanduser()
    try:
        connector_check = _connector_status(connector, expected_root=root)
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError, TypeError):
        connector_check = Check(
            "cross_project_connector",
            "fail",
            "connector config could not be checked safely",
        )
    checks.append(connector_check)
    installed_skill = (
        codex_skill_dir
        or Path(f"~/.codex/skills/{CODEX_SKILL_NAME}")
    ).expanduser()
    try:
        connector_required = connector.exists() or connector.is_symlink()
        skill_check = _codex_skill_status(
            root,
            installed_skill,
            required=connector_required,
        )
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError, TypeError):
        skill_check = Check(
            "codex_auto_connect_skill",
            "fail",
            "auto-connect skill bundle could not be checked safely",
        )
    checks.append(skill_check)
    try:
        site_ready = (
            (root / "site" / "index.html").is_file()
            and not (root / "site" / "index.html").is_symlink()
        )
    except (OSError, RuntimeError):
        site_ready = False
    checks.append(
        Check(
            "public_site",
            "pass" if site_ready else "warn",
            "static dashboard files are present"
            if site_ready
            else "static dashboard has not been built in this checkout",
        )
    )
    return _result(checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--connector-path")
    parser.add_argument("--codex-skill-dir")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = inspect_install(
            Path(args.repo_root),
            connector_path=Path(args.connector_path).expanduser() if args.connector_path else None,
            codex_skill_dir=Path(args.codex_skill_dir).expanduser() if args.codex_skill_dir else None,
        )
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError, TypeError):
        result = _redacted_runtime_failure()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"RKF install status: {result['status']}")
        for check in result["checks"]:
            print(f"- [{str(check['status']).upper()}] {check['name']}: {check['message']}")
    return 1 if args.strict and result["failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
