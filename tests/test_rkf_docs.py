from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    REPO / "README.md",
    REPO / "README.zh-TW.md",
    REPO / "docs" / "GETTING_STARTED.md",
    REPO / "docs" / "GETTING_STARTED.zh-TW.md",
    REPO / "docs" / "workflows" / "public-dashboard.zh-TW.md",
    REPO / "docs" / "workflows" / "paper-discovery.zh-TW.md",
    REPO / "docs" / "workflows" / "rkf-auto-connect.zh-TW.md",
)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class RKFDocumentationTests(unittest.TestCase):
    def test_beginner_documentation_local_links_exist_inside_repository(self) -> None:
        missing: list[str] = []
        escaped: list[str] = []

        for document in DOCUMENTS:
            self.assertTrue(document.is_file(), document.relative_to(REPO).as_posix())
            text = document.read_text(encoding="utf-8")
            for match in MARKDOWN_LINK_RE.finditer(text):
                raw_target = match.group(1).strip().strip("<>")
                parsed = urlsplit(raw_target)
                if parsed.scheme or raw_target.startswith("#"):
                    continue
                relative_target = unquote(parsed.path)
                if not relative_target:
                    continue
                target = (document.parent / relative_target).resolve()
                try:
                    target.relative_to(REPO)
                except ValueError:
                    escaped.append(
                        f"{document.relative_to(REPO).as_posix()} -> {raw_target}"
                    )
                    continue
                if not target.exists():
                    missing.append(
                        f"{document.relative_to(REPO).as_posix()} -> {raw_target}"
                    )

        self.assertEqual(escaped, [], "local documentation links must stay in the repository")
        self.assertEqual(missing, [], "local documentation links must resolve")

    def test_clean_install_starts_with_the_five_workflows(self) -> None:
        english = (REPO / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        chinese = (REPO / "docs" / "GETTING_STARTED.zh-TW.md").read_text(encoding="utf-8")

        self.assertIn("Complete the first paper loop", english)
        self.assertIn("完成第一個 paper 閉環", chinese)
        self.assertIn("Compare & Synthesize", english)

    def test_discovery_docs_describe_deterministic_retry_recovery(self) -> None:
        workflow = (
            REPO / "docs" / "workflows" / "paper-discovery.zh-TW.md"
        ).read_text(encoding="utf-8")

        self.assertIn("deterministic transaction key", workflow)
        self.assertIn("沿用同一 event", workflow)
        self.assertIn("fail closed", workflow)
        self.assertNotIn("後續若要把這個窗口完全關閉", workflow)

    def test_beginner_docs_do_not_expose_legacy_dashboard_actions(self) -> None:
        english = (REPO / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
        chinese = (REPO / "docs" / "GETTING_STARTED.zh-TW.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("build_public_dashboard.py", english)
        self.assertNotIn("build_public_dashboard.py", chinese)
        self.assertIn("Optional provider", english)


if __name__ == "__main__":
    unittest.main()
