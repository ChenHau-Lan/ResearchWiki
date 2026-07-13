#!/usr/bin/env python3
"""Build or publish a path-redacted RKF public dashboard snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rkf.core import Workspace
from rkf.public_dashboard import (
    DashboardSafetyError,
    preview_public_dashboard,
    publish_public_dashboard,
    render_dashboard_preview,
    validate_site_publication,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser("preview", help="Create a private aggregate preview for review")
    preview.add_argument("--window-days", type=int, default=30)

    review = subparsers.add_parser(
        "review",
        help="Render one private preview as a self-contained local review page",
    )
    review.add_argument("--preview-id", required=True)

    publish = subparsers.add_parser("publish", help="Publish one exact approved preview to the static site")
    publish.add_argument("--preview-id", required=True)
    publish.add_argument("--snapshot-hash", required=True)
    subparsers.add_parser(
        "validate-publication",
        help="Fail unless the committed site snapshot has exact-hash publication approval",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Workspace(Path(args.repo_root))
    try:
        if args.command == "preview":
            result = preview_public_dashboard(workspace, window_days=args.window_days)
        elif args.command == "review":
            result = render_dashboard_preview(workspace, preview_id=args.preview_id)
        elif args.command == "publish":
            result = publish_public_dashboard(
                workspace,
                preview_id=args.preview_id,
                approved_snapshot_hash=args.snapshot_hash,
            )
        else:
            result = validate_site_publication(Path(args.repo_root))
    except DashboardSafetyError as exc:
        result = {
            "schema": "rkf-dashboard-command-error-v1",
            "status": "blocked",
            "reason": str(exc),
            "paths_redacted": True,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
