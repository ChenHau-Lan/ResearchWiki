from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import bootstrap_rkf, check_install, demo_quickstart, rkf_auto_connect


REPO = Path(__file__).resolve().parents[1]


class RKFOnboardingV12Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "ResearchWiki"
        self.repo.mkdir()
        for relative in ("AGENTS.md", "README.md", "rkf/actions.py", "tools/rk.py"):
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("onboarding fixture\n", encoding="utf-8")
        shutil.copytree(
            REPO / "skills" / "rkf-auto-connect",
            self.repo / "skills" / "rkf-auto-connect",
        )
        bootstrap_rkf.bootstrap_local(self.repo, apply=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_core_profile_is_ready_without_optional_codex_integration(self) -> None:
        result = check_install.inspect_install(
            self.repo,
            connector_path=self.root / "missing-connector.toml",
            codex_skill_dir=self.root / "missing-skill",
            profile="core",
        )
        checks = {item["name"]: item for item in result["checks"]}
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = check_install.main(
                [
                    "--repo-root",
                    str(self.repo),
                    "--connector-path",
                    str(self.root / "missing-connector.toml"),
                    "--codex-skill-dir",
                    str(self.root / "missing-skill"),
                    "--profile",
                    "core",
                    "--strict",
                    "--json",
                ]
            )

        self.assertEqual(result["profile"], "core")
        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(checks["cross_project_connector"]["status"], "warn")
        self.assertEqual(checks["codex_auto_connect_skill"]["status"], "warn")
        self.assertEqual(exit_code, 0)
        self.assertTrue(json.loads(stdout.getvalue())["ready"])

    def test_codex_profile_fails_strict_when_connector_and_skill_are_missing(self) -> None:
        result = check_install.inspect_install(
            self.repo,
            connector_path=self.root / "missing-connector.toml",
            codex_skill_dir=self.root / "missing-skill",
            profile="codex",
        )
        checks = {item["name"]: item for item in result["checks"]}
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = check_install.main(
                [
                    "--repo-root",
                    str(self.repo),
                    "--connector-path",
                    str(self.root / "missing-connector.toml"),
                    "--codex-skill-dir",
                    str(self.root / "missing-skill"),
                    "--profile",
                    "codex",
                    "--strict",
                    "--json",
                ]
            )

        rendered = json.loads(stdout.getvalue())
        self.assertEqual(result["profile"], "codex")
        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(checks["cross_project_connector"]["status"], "fail")
        self.assertEqual(checks["codex_auto_connect_skill"]["status"], "fail")
        self.assertEqual(exit_code, 1)
        self.assertFalse(rendered["ready"])
        self.assertNotIn(str(self.root), stdout.getvalue())

    def test_codex_profile_passes_after_connector_and_exact_skill_install(self) -> None:
        connector = self.root / "connector.toml"
        installed_skill = self.root / "codex-skills" / "rkf-auto-connect"
        bootstrap_rkf.bootstrap_local(
            self.repo,
            apply=True,
            install_connector=True,
            connector_path=connector,
            codex_skill_dir=installed_skill,
        )

        result = check_install.inspect_install(
            self.repo,
            connector_path=connector,
            codex_skill_dir=installed_skill,
            profile="codex",
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            resolve_exit = rkf_auto_connect.main(
                ["resolve", "--config", str(connector)]
            )

        self.assertTrue(result["ready"])
        self.assertEqual(result["profile"], "codex")
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(resolve_exit, 0)
        self.assertEqual(json.loads(stdout.getvalue())["researchwiki"], "configured")

    def test_zero_network_quickstart_completes_two_paper_workflow(self) -> None:
        missing_global_connector = self.root / "global-connector-must-not-be-read.toml"
        with patch.dict(
            os.environ,
            {"RKF_CONNECTOR_CONFIG": str(missing_global_connector)},
            clear=False,
        ):
            result = demo_quickstart.run_quickstart()

        self.assertEqual(result["quickstart"], "passed")
        self.assertEqual(result["paper_count"], 2)
        self.assertEqual(result["workflows_completed"], 5)
        self.assertTrue(result["context_boundary_preserved"])
        self.assertTrue(result["finding_promotion_preserved"])
        self.assertTrue(result["promotion_boundary_preserved"])
        self.assertTrue(result["locator_gate_preserved"])
        self.assertTrue(result["activation_closed"])
        self.assertTrue(result["paths_redacted"])
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_readme_onboarding_commands_execute_in_an_isolated_checkout(self) -> None:
        checkout = self.root / "CLIResearchWiki"
        checkout.mkdir()
        for relative in ("AGENTS.md", "README.md", "rkf/actions.py", "tools/rk.py"):
            path = checkout / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("isolated onboarding fixture\n", encoding="utf-8")
        shutil.copytree(
            REPO / "skills" / "rkf-auto-connect",
            checkout / "skills" / "rkf-auto-connect",
        )
        connector = self.root / "isolated-connector.toml"
        installed_skill = self.root / "isolated-skills" / "rkf-auto-connect"

        def run(tool: str, *arguments: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, str(REPO / "tools" / tool), *arguments],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            )

        shared = (
            "--repo-root",
            str(checkout),
            "--connector-path",
            str(connector),
            "--codex-skill-dir",
            str(installed_skill),
        )
        core_preview = run("bootstrap_rkf.py", *shared)
        self.assertEqual(core_preview.returncode, 0, core_preview.stderr)
        self.assertEqual(json.loads(core_preview.stdout)["status"], "ready")
        self.assertFalse((checkout / "rkf.workspace.toml").exists())

        core_apply = run("bootstrap_rkf.py", "--apply", *shared)
        self.assertEqual(core_apply.returncode, 0, core_apply.stderr)
        self.assertEqual(json.loads(core_apply.stdout)["status"], "configured")
        core_check = run(
            "check_install.py",
            *shared,
            "--profile",
            "core",
            "--strict",
            "--json",
        )
        self.assertEqual(core_check.returncode, 0, core_check.stderr)
        self.assertTrue(json.loads(core_check.stdout)["ready"])

        codex_preview = run("bootstrap_rkf.py", "--install-connector", *shared)
        self.assertEqual(codex_preview.returncode, 0, codex_preview.stderr)
        self.assertFalse(connector.exists())
        codex_apply = run(
            "bootstrap_rkf.py",
            "--apply",
            "--install-connector",
            *shared,
        )
        self.assertEqual(codex_apply.returncode, 0, codex_apply.stderr)
        self.assertTrue(connector.is_file())
        codex_check = run(
            "check_install.py",
            *shared,
            "--profile",
            "codex",
            "--strict",
            "--json",
        )
        self.assertEqual(codex_check.returncode, 0, codex_check.stderr)
        self.assertTrue(json.loads(codex_check.stdout)["ready"])
        resolved = run("rkf_auto_connect.py", "resolve", "--config", str(connector))
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(json.loads(resolved.stdout)["researchwiki"], "configured")

    def test_bilingual_onboarding_documents_expose_the_same_runnable_commands(self) -> None:
        english = (REPO / "README.md").read_text(encoding="utf-8")
        chinese = (REPO / "README.zh-TW.md").read_text(encoding="utf-8")
        getting_started = (REPO / "docs" / "GETTING_STARTED.md").read_text(
            encoding="utf-8"
        )
        getting_started_zh = (
            REPO / "docs" / "GETTING_STARTED.zh-TW.md"
        ).read_text(encoding="utf-8")
        commands = (
            "python3 tools/bootstrap_rkf.py",
            "python3 tools/bootstrap_rkf.py --apply",
            "python3 tools/check_install.py --profile core --strict --json",
            "python3 tools/bootstrap_rkf.py --install-connector",
            "python3 tools/bootstrap_rkf.py --apply --install-connector",
            "python3 tools/check_install.py --profile codex --strict --json",
            "python3 tools/rkf_auto_connect.py resolve",
            "python3 tools/demo_quickstart.py --check",
        )

        for command in commands:
            for document in (english, chinese, getting_started, getting_started_zh):
                self.assertIn(command, document)
        for document in (english, chinese):
            self.assertNotIn("10.0000/example", document)
            self.assertNotIn("p. 8, Fig. 3", document)


if __name__ == "__main__":
    unittest.main()
