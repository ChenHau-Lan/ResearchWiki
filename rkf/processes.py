"""Bounded subprocess execution for optional machine-local adapters."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BoundedProcessResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    stdout_overflow: bool = False
    stderr_overflow: bool = False


def run_bounded_process(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    timeout_seconds: float,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> BoundedProcessResult:
    """Run ``command`` without allowing unbounded captured output.

    Reader threads cap both streams and kill the child as soon as either cap
    is exceeded. The returned text never contains more than the configured
    bound and is decoded with replacement so diagnostics cannot crash the
    caller.
    """

    if not command or not all(isinstance(part, str) and part for part in command):
        raise ValueError("bounded process command must be a non-empty string sequence")
    if timeout_seconds <= 0 or min(max_stdout_bytes, max_stderr_bytes) <= 0:
        raise ValueError("bounded process limits must be positive")

    process = subprocess.Popen(
        tuple(command),
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        shell=False,
    )
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    overflow = {"stdout": False, "stderr": False}

    def drain(stream, target: bytearray, limit: int, label: str) -> None:  # noqa: ANN001
        try:
            while True:
                chunk = stream.read(64 * 1024)
                if not chunk:
                    break
                remaining = max(0, limit - len(target))
                if remaining:
                    target.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow[label] = True
                    try:
                        process.kill()
                    except OSError:
                        pass
                    break
        finally:
            stream.close()

    assert process.stdout is not None
    assert process.stderr is not None
    readers = (
        threading.Thread(
            target=drain,
            args=(process.stdout, stdout_buffer, max_stdout_bytes, "stdout"),
            daemon=True,
        ),
        threading.Thread(
            target=drain,
            args=(process.stderr, stderr_buffer, max_stderr_bytes, "stderr"),
            daemon=True,
        ),
    )
    for reader in readers:
        reader.start()

    if process.stdin is not None:
        try:
            process.stdin.write((input_text or "").encode("utf-8"))
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            process.stdin.close()

    timed_out = False
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()
    for reader in readers:
        reader.join()

    return BoundedProcessResult(
        returncode=int(process.returncode),
        stdout=bytes(stdout_buffer).decode("utf-8", errors="replace"),
        stderr=bytes(stderr_buffer).decode("utf-8", errors="replace"),
        timed_out=timed_out,
        stdout_overflow=overflow["stdout"],
        stderr_overflow=overflow["stderr"],
    )
