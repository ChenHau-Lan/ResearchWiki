from __future__ import annotations

import sys
import unittest

from rkf.processes import run_bounded_process


class BoundedProcessTests(unittest.TestCase):
    def test_stdout_overflow_kills_child_and_caps_capture(self) -> None:
        result = run_bounded_process(
            [sys.executable, "-c", "import sys; sys.stdout.write('x' * 100000)"],
            timeout_seconds=5,
            max_stdout_bytes=128,
            max_stderr_bytes=128,
        )

        self.assertTrue(result.stdout_overflow)
        self.assertEqual(len(result.stdout.encode("utf-8")), 128)

    def test_timeout_is_typed(self) -> None:
        result = run_bounded_process(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            timeout_seconds=0.05,
            max_stdout_bytes=128,
            max_stderr_bytes=128,
        )

        self.assertTrue(result.timed_out)


if __name__ == "__main__":
    unittest.main()
