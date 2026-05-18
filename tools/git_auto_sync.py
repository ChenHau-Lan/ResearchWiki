#!/usr/bin/env python3
"""Conservative two-computer Git sync helper.

The script is designed for scheduled runs on multiple computers. It compares
the local branch with its upstream, commits local edits when present, rebases on
top of remote updates, then pushes. If Git reports a conflict or a branch has no
upstream, the script stops and prints the command that needs human attention.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAX_MB = int(os.environ.get("MAX_UPLOAD_FILE_MB", "25"))


class SyncError(RuntimeError):
    pass


def run(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and result.returncode != 0:
        raise SyncError(f"$ {' '.join(args)}\n{result.stdout.strip()}")
    return result


def git_output(args: list[str]) -> str:
    return run(["git", *args]).stdout.strip()


def current_branch() -> str:
    branch = git_output(["branch", "--show-current"])
    if not branch:
        raise SyncError("Not on a named branch. Check out main before syncing.")
    return branch


def upstream_ref() -> str:
    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if upstream.returncode != 0:
        branch = current_branch()
        raise SyncError(
            f"Branch {branch!r} has no upstream. Run: git push -u origin {branch}"
        )
    return upstream.stdout.strip()


def porcelain() -> str:
    return git_output(["status", "--porcelain", "-z"])


def has_worktree_changes() -> bool:
    return bool(porcelain())


def candidate_files() -> list[Path]:
    paths: list[Path] = []
    entries = porcelain().split("\0")
    for entry in entries:
        if not entry:
            continue
        path_text = entry[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        path = ROOT / path_text
        if path.is_file():
            paths.append(path)
    return paths


def check_file_sizes(max_mb: int) -> None:
    max_bytes = max_mb * 1024 * 1024
    oversized: list[tuple[Path, int]] = []
    for path in candidate_files():
        size = path.stat().st_size
        if size > max_bytes:
            oversized.append((path.relative_to(ROOT), size))

    if not oversized:
        return

    lines = [f"Refusing sync: files larger than {max_mb} MiB were found."]
    for path, size in oversized:
        lines.append(f"- {path} ({size / 1024 / 1024:.1f} MiB)")
    lines.append("Move large source artifacts under raw/ or keep them outside Git.")
    raise SyncError("\n".join(lines))


def rev_counts(upstream: str) -> tuple[int, int]:
    counts = git_output(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
    left, right = counts.split()
    return int(left), int(right)


def status_summary() -> str:
    branch = current_branch()
    upstream = upstream_ref()
    run(["git", "fetch", "--prune"])
    ahead, behind = rev_counts(upstream)
    dirty = "yes" if has_worktree_changes() else "no"
    return "\n".join(
        [
            f"branch: {branch}",
            f"upstream: {upstream}",
            f"local_ahead: {ahead}",
            f"remote_ahead: {behind}",
            f"worktree_changes: {dirty}",
        ]
    )


def commit_local_changes(message_prefix: str, max_mb: int, skip_lint: bool) -> bool:
    if not has_worktree_changes():
        return False

    check_file_sizes(max_mb)
    if not skip_lint:
        run([sys.executable, "tools/wiki_lint.py"])

    run(["git", "add", "-A"])
    staged = run(["git", "diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        return False

    host = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown-host"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    run(["git", "commit", "-m", f"{message_prefix} {stamp} from {host}"])
    return True


def sync(message_prefix: str, max_mb: int, skip_lint: bool) -> str:
    branch = current_branch()
    upstream = upstream_ref()
    run(["git", "fetch", "--prune"])

    committed = commit_local_changes(message_prefix, max_mb, skip_lint)

    run(["git", "fetch", "--prune"])
    ahead, behind = rev_counts(upstream)
    if behind:
        rebase = run(["git", "pull", "--rebase", "--autostash"], check=False)
        if rebase.returncode != 0:
            raise SyncError(
                "Rebase stopped. Resolve conflicts, then run:\n"
                "  git rebase --continue\n"
                "  python tools/git_auto_sync.py sync\n\n"
                + rebase.stdout.strip()
            )

    run(["git", "fetch", "--prune"])
    ahead, behind = rev_counts(upstream)
    if behind:
        raise SyncError(f"Remote still has {behind} commit(s). Inspect with: git log --oneline HEAD..{upstream}")
    if ahead:
        run(["git", "push"])

    final_ahead, final_behind = rev_counts(upstream)
    return "\n".join(
        [
            f"branch: {branch}",
            f"upstream: {upstream}",
            f"committed_local_changes: {'yes' if committed else 'no'}",
            f"local_ahead_after_sync: {final_ahead}",
            f"remote_ahead_after_sync: {final_behind}",
            "sync: complete",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely sync this research wiki through GitHub.")
    parser.add_argument("mode", choices=["status", "sync"], help="Compare only, or commit/rebase/push.")
    parser.add_argument("--message-prefix", default="Auto wiki sync", help="Commit message prefix.")
    parser.add_argument("--max-upload-file-mb", type=int, default=DEFAULT_MAX_MB)
    parser.add_argument("--skip-lint", action="store_true", help="Skip tools/wiki_lint.py before committing.")
    args = parser.parse_args()

    try:
        if args.mode == "status":
            print(status_summary())
        else:
            print(sync(args.message_prefix, args.max_upload_file_mb, args.skip_lint))
        return 0
    except SyncError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
