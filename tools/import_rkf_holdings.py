#!/usr/bin/env python3
"""Preview or apply a machine-local RKF holdings CSV import."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from rkf.acquisition import ingest_holdings_csv  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="CSV export with canonical holdings columns")
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="atomically replace the SQLite target")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = ingest_holdings_csv(
            args.csv,
            args.database,
            apply=args.apply,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
