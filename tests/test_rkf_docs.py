from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

from rkf.actions import available_actions


REPO = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    REPO / "README.md",
    REPO / "README.zh-TW.md",
    REPO / "docs" / "GETTING_STARTED.md",
    REPO / "docs" / "GETTING_STARTED.zh-TW.md",
    REPO / "docs" / "MAINTAINER_REFERENCE.md",
    REPO / "docs" / "V1_SCOPE_INVENTORY.md",
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
        beginner_docs = (
            REPO / "README.md",
            REPO / "README.zh-TW.md",
            REPO / "docs" / "GETTING_STARTED.md",
            REPO / "docs" / "GETTING_STARTED.zh-TW.md",
        )
        forbidden = (
            "dashboard.preview",
            "discover.preview",
            "world.render",
            "hot.record",
            "maintenance.preview",
            "paper.migration.preview",
            "views.preview",
            "build_public_dashboard.py",
        )
        for document in beginner_docs:
            text = document.read_text(encoding="utf-8")
            for name in forbidden:
                self.assertNotIn(name, text, f"{name} leaked into {document.name}")

    def test_readmes_are_aligned_and_include_executable_onboarding(self) -> None:
        english = (REPO / "README.md").read_text(encoding="utf-8")
        chinese = (REPO / "README.zh-TW.md").read_text(encoding="utf-8")
        commands = (
            "python3 tools/bootstrap_rkf.py",
            "python3 tools/bootstrap_rkf.py --apply",
            "python3 tools/check_install.py --strict",
            "python3 tools/rkf_auto_connect.py connect-project /path/to/research-project",
            "python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply",
        )
        workflow_rows = (
            "| **Add** |",
            "| **Ask** |",
            "| **Read** |",
            "| **Compare & Synthesize** |",
            "| **Review** |",
        )
        for command in commands:
            self.assertIn(command, english)
            self.assertIn(command, chinese)
        for text in (english, chinese):
            positions = [text.index(workflow) for workflow in workflow_rows]
            self.assertEqual(positions, sorted(positions))
            self.assertIn("Maintainer reference", text)

    def test_documented_setup_commands_have_matching_help_surfaces(self) -> None:
        commands = (
            [sys.executable, "tools/bootstrap_rkf.py", "--help"],
            [sys.executable, "tools/check_install.py", "--help"],
            [sys.executable, "tools/rkf_auto_connect.py", "connect-project", "--help"],
        )
        for command in commands:
            result = subprocess.run(
                command,
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_machine_readable_scope_inventory_is_complete(self) -> None:
        inventory_path = REPO / "docs" / "operations" / "v1-scope-inventory.yaml"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        allowed = set(inventory["allowed_classifications"])
        entries = inventory["entries"]
        self.assertEqual(allowed, {"keep", "merge", "delete", "temporary-shim"})
        self.assertEqual(
            inventory["user_workflows"],
            ["Connect & Activate", "Add", "Ask", "Read", "Compare & Synthesize", "Review"],
        )
        self.assertEqual(len({entry["id"] for entry in entries}), len(entries))

        required = {
            "id", "kind", "current_names", "path", "classification", "target",
            "migration_impact", "test_docs_impact", "removal_version", "owner",
            "follow_up_issue",
        }
        covered_names: set[str] = set()
        for entry in entries:
            self.assertEqual(set(entry), required, entry["id"])
            self.assertIn(entry["classification"], allowed)
            self.assertTrue(entry["current_names"])
            self.assertTrue(entry["owner"])
            self.assertTrue(entry["follow_up_issue"])
            if entry["classification"] == "temporary-shim":
                self.assertRegex(entry["removal_version"], r"^v\d+\.\d+\.\d+$")
            else:
                self.assertIsNone(entry["removal_version"])
            covered_names.update(entry["current_names"])

        self.assertTrue(set(available_actions()).issubset(covered_names))
        action_source = (REPO / "rkf" / "actions.py").read_text(encoding="utf-8")
        routed_actions = set(re.findall(r'request\.action == "([^"]+)"', action_source))
        self.assertEqual(routed_actions - covered_names, set())


if __name__ == "__main__":
    unittest.main()
