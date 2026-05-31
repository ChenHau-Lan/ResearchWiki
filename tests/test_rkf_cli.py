#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rkf.core import hot_event_id, normalize_doi, normalize_hot_query, source_id_from_value


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "rk.py"


class RKFCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = os.environ.copy()
        self.env["RKF_ROOT"] = str(self.root)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_rk(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"rk.py failed: {result.args}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    def test_doi_normalization_and_source_id(self) -> None:
        self.assertEqual(normalize_doi("https://doi.org/10.1234/ABC.Def."), "10.1234/abc.def")
        self.assertEqual(source_id_from_value("doi", "doi:10.1234/ABC.Def"), "doi_10_1234_abc_def")

    def test_acquisition_requires_checkpoint_before_private_pdf(self) -> None:
        doi = "https://doi.org/10.1234/ABC.Def"
        source_id = "doi_10_1234_abc_def"
        sample_pdf = self.root / "sample.pdf"
        sample_pdf.write_bytes(b"%PDF-1.4\n% tiny fixture\n")

        self.run_rk("capture", "doi", doi)
        self.run_rk("acquire", source_id, "--pdf", str(sample_pdf))

        self.assertTrue((self.root / "state" / "gates" / "pdf_acquisition" / f"{source_id}.md").exists())
        self.assertFalse((self.root / ".rkf_private" / "evidence" / "doi_pdf" / f"{source_id}.pdf").exists())

        self.run_rk("acquire", source_id, "--pdf", str(sample_pdf), "--approve")
        self.assertTrue((self.root / ".rkf_private" / "evidence" / "doi_pdf" / f"{source_id}.pdf").exists())

    def test_private_evidence_root_uses_workspace_config(self) -> None:
        private_root = self.root / "DriveRoot" / "evidence"
        (self.root / "rkf.workspace.toml").write_text(
            f'[storage]\nprivate_evidence_root = "{private_root.as_posix()}"\n',
            encoding="utf-8",
        )
        source_id = "doi_10_5555_config_test"
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        self.run_rk("capture", "doi", "10.5555/config.test")
        self.run_rk("acquire", source_id, "--pdf", str(pdf), "--approve")

        self.assertTrue((private_root / "doi_pdf" / f"{source_id}.pdf").exists())

    def test_configured_wiki_root_is_the_cli_database(self) -> None:
        wiki_root = self.root / "DriveRoot" / "wiki"
        (self.root / "rkf.workspace.toml").write_text(
            f'[storage]\nwiki_root = "{wiki_root.as_posix()}"\n',
            encoding="utf-8",
        )

        self.run_rk("synthesize", "Aerosol Note", "--body", "aerosol cloud evidence boundary")
        page = wiki_root / "knowledge" / "synthesis" / "aerosol_note.md"
        self.assertTrue(page.exists())
        self.assertFalse((self.root / "knowledge" / "synthesis" / "aerosol_note.md").exists())

        query = self.run_rk("query", "aerosol").stdout
        self.assertIn("matches: 1", query)
        self.assertIn("knowledge/synthesis/aerosol_note.md", query)

        self.run_rk("index")
        index = (wiki_root / "index.md").read_text(encoding="utf-8")
        self.assertIn("Aerosol Note", index)
        self.assertIn("tier=review-blocker", index)

        log = self.run_rk("log", "--tail", "10").stdout
        self.assertIn("`save`", log)
        self.assertIn("`index`", log)

    def test_hot_event_helpers_are_stable(self) -> None:
        self.assertEqual(normalize_hot_query("  Aerosol   Cloud\nQuestion  "), "aerosol cloud question")
        first = hot_event_id(
            created="2026-05-26T10:00:00",
            origin="local",
            intent="query",
            normalized_query="aerosol cloud question",
            topic_ids=["aerosol-cloud"],
        )
        second = hot_event_id(
            created="2026-05-26T10:00:00",
            origin="local",
            intent="query",
            normalized_query="aerosol cloud question",
            topic_ids=["aerosol-cloud"],
        )
        self.assertEqual(first, second)

    def test_hot_record_refresh_and_topic_mapping(self) -> None:
        self.run_rk(
            "topic",
            "add",
            "aerosol-cloud",
            "Aerosol Cloud",
            "--scope",
            "Aerosol cloud interaction literature",
            "--search",
            "aerosol cloud interaction",
        )

        result = self.run_rk(
            "hot",
            "record",
            "Aerosol cloud paper search",
            "--intent",
            "paper-search",
            "--paper-lead",
            "10.1234/example",
        ).stdout
        self.assertIn("recorded hot query:", result)
        self.assertIn("topics: aerosol-cloud", result)

        hot = (self.root / "hot.md").read_text(encoding="utf-8")
        self.assertIn("Aerosol Cloud", hot)
        self.assertIn("aerosol cloud paper search: 1", hot)
        self.assertIn("10.1234/example: 1", hot)
        self.assertIn("<!-- RKF-HOT-RECORDS:START -->", hot)
        self.assertIn('intent=paper-search | query="Aerosol cloud paper search"', hot)
        self.assertFalse((self.root / "state" / "hot").exists())

    def test_query_and_discover_record_hot_events(self) -> None:
        self.run_rk(
            "topic",
            "add",
            "aerosol-cloud",
            "Aerosol Cloud",
            "--scope",
            "Aerosol cloud interaction literature",
            "--search",
            "aerosol cloud interaction",
        )
        self.run_rk("query", "aerosol cloud")
        self.run_rk("discover", "aerosol cloud interaction", "--topic-id", "aerosol-cloud")
        self.run_rk("query", "do not record this one", "--no-record")

        hot = (self.root / "hot.md").read_text(encoding="utf-8")
        self.assertIn("aerosol-cloud (Aerosol Cloud): 2", hot)
        self.assertIn("aerosol cloud: 1", hot)
        self.assertIn("aerosol cloud interaction: 1", hot)
        self.assertNotIn("do not record this one", hot)

    def test_save_refuses_accidental_overwrite_unless_update_is_explicit(self) -> None:
        self.run_rk("save", "concept", "Aerosol Note", "--body", "first body")
        duplicate = self.run_rk("save", "concept", "Aerosol Note", "--body", "second body", check=False)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("refusing to overwrite without --update", duplicate.stderr + duplicate.stdout)

        self.run_rk("save", "concept", "Aerosol Note", "--body", "second body", "--update")
        page = (self.root / "knowledge" / "concept" / "aerosol_note.md").read_text(encoding="utf-8")
        self.assertIn("second body", page)

    def test_graph_lint_finds_dangling_source_and_evidence_links(self) -> None:
        page = self.root / "knowledge" / "concepts" / "dangling.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\n"
            "type: concept\n"
            "status: draft\n"
            "review_stage: ai-extracted\n"
            "topics: []\n"
            "created: 2026-05-25\n"
            "updated: 2026-05-25\n"
            "source_id: missing_source\n"
            "evidence_ids:\n"
            "  - missing_evidence\n"
            "---\n\n"
            "# Dangling\n",
            encoding="utf-8",
        )

        result = self.run_rk("lint", "--mode", "graph-lint", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing source record missing_source", result.stdout)
        self.assertIn("missing evidence artifact missing_evidence", result.stdout)

    def test_ars_handoff_lint_keeps_ars_output_as_proposal(self) -> None:
        page = self.root / "knowledge" / "synthesis" / "ars_promoted.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\n"
            "type: synthesis\n"
            "status: draft\n"
            "review_stage: ai-extracted\n"
            "topics: []\n"
            "evidence_boundary: wiki-page\n"
            "created: 2026-05-25\n"
            "updated: 2026-05-25\n"
            "---\n\n"
            "# ARS Promoted\n\n"
            "source_from_ars: deep-research\n",
            encoding="utf-8",
        )

        result = self.run_rk("lint", "--mode", "ars-handoff-lint", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ARS-derived material must use ars-proposal or review-blocker boundary", result.stdout)

    def test_propagate_writes_proposal_without_rewriting_pages(self) -> None:
        concept = self.root / "knowledge" / "concepts" / "aerosol_seed.md"
        synthesis = self.root / "knowledge" / "synthesis" / "aerosol_answer.md"
        concept.parent.mkdir(parents=True)
        synthesis.parent.mkdir(parents=True)
        concept.write_text(
            "---\n"
            "type: concept\n"
            "status: draft\n"
            "review_stage: ai-extracted\n"
            "topics:\n"
            "  - aerosol-cloud\n"
            "evidence_boundary: review-blocker\n"
            "created: 2026-05-25\n"
            "updated: 2026-05-25\n"
            "---\n\n"
            "# Aerosol Seed\n\n"
            "Aerosol cloud mechanism note.\n",
            encoding="utf-8",
        )
        synthesis.write_text(
            "---\n"
            "type: synthesis\n"
            "status: draft\n"
            "review_stage: ai-extracted\n"
            "topics:\n"
            "  - aerosol-cloud\n"
            "evidence_boundary: review-blocker\n"
            "created: 2026-05-25\n"
            "updated: 2026-05-25\n"
            "---\n\n"
            "# Aerosol Answer\n\n"
            "Aerosol cloud mechanism synthesis.\n",
            encoding="utf-8",
        )

        result = self.run_rk("propagate", "knowledge/concepts/aerosol_seed.md", "--write").stdout
        self.assertIn("affected pages: 1", result)
        self.assertIn("knowledge/synthesis/aerosol_answer.md", result)
        self.assertIn("review blockers:", result)
        proposals = list((self.root / "state" / "gates" / "propagation").glob("*.md"))
        self.assertEqual(len(proposals), 1)
        self.assertIn("proposal-only", proposals[0].read_text(encoding="utf-8"))

    def test_status_and_world_print_workspace_bootstrap(self) -> None:
        self.run_rk("save", "question", "Aerosol Question", "--body", "What matters next?")
        status = self.run_rk("status").stdout
        world = self.run_rk("world", "--log-tail", "1").stdout
        self.assertIn("RKF Workspace Status", status)
        self.assertIn("Knowledge pages: 1", status)
        self.assertIn("Recent Log", world)

    def test_hot_refresh_preserves_single_file_records(self) -> None:
        self.run_rk(
            "topic",
            "add",
            "aerosol-ice-phase-clouds",
            "Aerosol Effects on Ice-Phase Clouds",
            "--scope",
            "Aerosol effects on ice phase and mixed phase clouds",
            "--search",
            "aerosol ice phase clouds",
        )
        self.run_rk(
            "hot",
            "record",
            "supercooled liquid IWP aerosol mechanism",
            "--topic-id",
            "aerosol-ice-phase-clouds",
            "--origin",
            "external-sandbox",
            "--intent",
            "paper-search",
        )
        hot_path = self.root / "hot.md"

        self.run_rk("hot", "refresh")
        hot = hot_path.read_text(encoding="utf-8")
        self.assertNotIn("RKF-HOT-INBOX", hot)
        self.assertIn("aerosol-ice-phase-clouds (Aerosol Effects on Ice-Phase Clouds): 1", hot)
        self.assertIn("supercooled liquid iwp aerosol mechanism: 1", hot)
        self.assertIn('origin=external-sandbox | topic=aerosol-ice-phase-clouds | intent=paper-search', hot)

    def test_hot_record_rejects_private_paths_and_oversized_text(self) -> None:
        private_path = self.run_rk("hot", "record", "/" + "Users/example/private.pdf", check=False)
        self.assertNotEqual(private_path.returncode, 0)
        self.assertIn("local/private path", private_path.stderr + private_path.stdout)

        oversized = self.run_rk("hot", "record", "x" * 501, check=False)
        self.assertNotEqual(oversized.returncode, 0)
        self.assertIn("too long", oversized.stderr + oversized.stdout)

    def test_public_safety_lint_scans_public_wiki_layers(self) -> None:
        wiki_root = self.root / "DriveRoot" / "wiki"
        (self.root / "rkf.workspace.toml").write_text(
            f'[storage]\nwiki_root = "{wiki_root.as_posix()}"\n',
            encoding="utf-8",
        )
        page = wiki_root / "knowledge" / "concepts" / "private_path.md"
        page.parent.mkdir(parents=True)
        page.write_text(
            "---\n"
            "type: concept\n"
            "status: draft\n"
            "review_stage: ai-extracted\n"
            "topics: []\n"
            "created: 2026-05-25\n"
            "updated: 2026-05-25\n"
            "---\n\n"
            "# Private Path\n\n"
            "This page should not expose " + "/" + "Users/example/private.pdf.\n",
            encoding="utf-8",
        )

        result = self.run_rk("lint", "--mode", "public-safety-lint", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local/private path pattern", result.stdout)

    def test_metadata_only_source_cannot_be_distilled(self) -> None:
        self.run_rk("capture", "doi", "10.1111/metadata.only")
        result = self.run_rk("distill", "paper", "doi_10_1111_metadata_only", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no QCed PDF evidence", result.stderr + result.stdout)

    def test_unqced_pdf_cannot_be_distilled(self) -> None:
        source_id = "doi_10_2222_needs_qc"
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        self.run_rk("capture", "doi", "10.2222/needs.qc")
        self.run_rk("acquire", source_id, "--pdf", str(pdf), "--approve")
        result = self.run_rk("distill", "paper", source_id, check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no QCed PDF evidence", result.stderr + result.stdout)

    def test_qced_pdf_can_be_distilled_and_graphed(self) -> None:
        source_id = "doi_10_3333_pdf_read"
        pdf = self.root / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        self.run_rk("capture", "doi", "10.3333/pdf.read", "--topic-id", "aerosol-cloud", "--title", "Checked PDF Paper")
        self.run_rk("acquire", source_id, "--pdf", str(pdf), "--approve")
        self.run_rk("verify-pdf", source_id, "--locator", "pp. 1-4 methods and results")
        self.run_rk("distill", "paper", source_id)
        self.run_rk("graph")

        page = self.root / "knowledge" / "papers" / f"{source_id}.md"
        self.assertTrue(page.exists())
        text = page.read_text(encoding="utf-8")
        self.assertIn("evidence_boundary: pdf-evidence", text)
        self.assertIn("pp. 1-4 methods and results", text)
        graph = (self.root / "graph" / "research_graph.json").read_text(encoding="utf-8")
        self.assertIn("supported-by", graph)

    def test_topic_lint_and_external_sandbox_capsule(self) -> None:
        self.run_rk(
            "topic",
            "add",
            "aerosol-cloud",
            "Aerosol Cloud",
            "--scope",
            "Aerosol cloud interaction literature",
            "--search",
            "aerosol cloud interaction",
        )
        self.assertIn("topic lint passed", self.run_rk("topic", "lint").stdout)
        self.run_rk("prompt", "external-sandbox")
        capsule = (self.root / "prompts" / "external_sandbox_context.md").read_text(encoding="utf-8")
        self.assertIn("metadata, search candidates, and ARS reports are not evidence", capsule)

    def test_active_repo_has_no_legacy_router_or_full_text_workflow(self) -> None:
        tracked = subprocess.check_output(["git", "ls-files"], cwd=REPO, text=True)
        legacy_router = "ResearchWiki" + "Codex.command"
        legacy_cli = "tools/" + "rw.py"
        legacy_index = "raw/" + "full_text_index.md"
        legacy_builder = "tools/" + "build_" + "full_text_index.py"
        self.assertNotIn(legacy_router, tracked)
        self.assertNotIn(legacy_cli, tracked)
        self.assertNotIn(legacy_index, tracked)
        self.assertNotIn(legacy_builder, tracked)

        active_docs = "\n".join(
            (REPO / path).read_text(encoding="utf-8", errors="replace")
            for path in ["AGENTS.md", "MODE_REGISTRY.md", "README.md", "README.zh-TW.md"]
        )
        self.assertNotIn("vNext", active_docs)
        self.assertNotIn("recently added", active_docs.lower())
        self.assertNotIn("ResearchWiki" + "Codex", active_docs)
        self.assertNotIn("raw/" + "full_text", active_docs)

    def test_active_skills_are_five_and_bridge_is_not_active_skill(self) -> None:
        skill_files = sorted(path.relative_to(REPO).as_posix() for path in (REPO / "skills").glob("*/SKILL.md"))
        self.assertEqual(
            skill_files,
            [
                "skills/rkf-connect/SKILL.md",
                "skills/rkf-evidence-vault/SKILL.md",
                "skills/rkf-knowledge-synthesis/SKILL.md",
                "skills/rkf-lint/SKILL.md",
                "skills/rkf-wiki-core/SKILL.md",
            ],
        )
        self.assertFalse((REPO / "skills" / "rkf-ars-bridge" / "SKILL.md").exists())

    def test_skills_and_manuals_are_not_cli_first(self) -> None:
        docs = list((REPO / "skills").glob("rkf-*/SKILL.md"))
        docs.extend((REPO / "docs" / "manuals").glob("rkf_manual.*.md"))
        text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in docs)
        self.assertNotIn("## CLI", text)
        self.assertNotIn("python3 tools/rk.py", text)
        self.assertIn("Trigger Phrases", text)
        self.assertIn("Skill Triggers", text)

    def test_core_docs_use_knowledge_framework_positioning(self) -> None:
        core_paths = [
            "README.md",
            "README.zh-TW.md",
            "AGENTS.md",
            "docs/ARCHITECTURE.md",
            "docs/manuals/rkf_manual.en.md",
            "docs/manuals/rkf_manual.zh-TW.md",
        ]
        core_text = "\n".join((REPO / path).read_text(encoding="utf-8", errors="replace") for path in core_paths)
        old_pdf_primary = "PDF" + "-to-Wiki"
        old_pdf_heading = "PDF" + "-To-Wiki"
        self.assertNotIn(old_pdf_primary, core_text)
        self.assertNotIn(old_pdf_heading, core_text)
        self.assertIn("LLM Wiki-based research knowledge framework", core_text)
        self.assertIn("PDF is not the source", core_text)
        self.assertIn("RKF retrieves governed wiki context", core_text)
        self.assertIn("ARS reasons", core_text)
        self.assertIn("rkf-connect", core_text)
        self.assertIn("topic-review", core_text)
        self.assertIn("Version Management", (REPO / "README.md").read_text(encoding="utf-8"))
        self.assertIn("版本管理", (REPO / "README.zh-TW.md").read_text(encoding="utf-8"))
        self.assertIn("v1.0.0", (REPO / "README.md").read_text(encoding="utf-8"))
        self.assertIn("v1.0.0", (REPO / "README.zh-TW.md").read_text(encoding="utf-8"))

        manual_text = (REPO / "docs" / "manuals" / "rkf_manual.en.md").read_text(encoding="utf-8")
        manual_zh = (REPO / "docs" / "manuals" / "rkf_manual.zh-TW.md").read_text(encoding="utf-8")
        self.assertIn("Start From A Codex Workspace", manual_text)
        self.assertIn("academic-research-skills", manual_text)
        self.assertIn("missing artifact checkpoint", manual_text)
        self.assertIn("OCR confidence", manual_text)
        self.assertIn("Wiki Page Types And Template Functions", manual_text)
        self.assertIn("Experimental: Shared Database Across Computers", manual_text)
        self.assertIn("從 0 建立一個 Codex 研究知識庫", manual_zh)
        self.assertIn("缺 PDF", manual_zh)
        self.assertIn("維護為什麼重要", manual_zh)
        self.assertIn("Wiki Page 類型與範本功能", manual_zh)
        self.assertIn("建立共享資料庫在不同電腦", manual_zh)
        self.assertNotIn("manual " + "interprets", manual_text)
        self.assertNotIn("本手冊" + "把", manual_zh)

    def test_all_knowledge_page_types_have_templates(self) -> None:
        expected = {
            "claim.md",
            "concept.md",
            "meeting.md",
            "overview.md",
            "paper.md",
            "project-synthesis.md",
            "question.md",
            "seminar.md",
            "synthesis.md",
            "topic.md",
        }
        template_names = {path.name for path in (REPO / "templates" / "rkf").glob("*.md")}
        self.assertEqual(template_names, expected)
        for path in (REPO / "templates" / "rkf").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("evidence_boundary:", text)

    def test_taiwan_example_contains_research_memory_walkthrough(self) -> None:
        example = REPO / "examples" / "taiwan-atmospheric-experiment"
        candidates = (example / "literature_candidates.md").read_text(encoding="utf-8")
        self.assertIn("10.2151/jmsj1965.70.1_25", candidates)
        self.assertIn("10.3390/rs12183004", candidates)
        self.assertIn("10.1029/2024JD042375", candidates)
        self.assertIn("10.1175/MWR-D-24-0049.1", candidates)
        self.assertIn("10.5194/acp-26-2083-2026", candidates)
        self.assertIn("TAHOPE/PRECIP", candidates)
        self.assertIn("SoWMEX/TiMREX", candidates)

        paper_pages = sorted((example / "knowledge" / "papers").glob("*.md"))
        self.assertGreaterEqual(len(paper_pages), 6)
        for page in paper_pages:
            text = page.read_text(encoding="utf-8")
            self.assertIn("evidence_boundary: pdf-evidence", text)
            self.assertIn("PDF Locators", text)

        walkthrough = (example / "skill_mode_walkthrough.md").read_text(encoding="utf-8")
        self.assertIn("academic-research-skills", walkthrough)
        self.assertIn("deep-research:lit-review", walkthrough)
        self.assertIn("rkf-evidence-vault", walkthrough)
        self.assertIn("durable memory", walkthrough)
        self.assertIn("LLM Wiki fills that gap", walkthrough)
        self.assertIn("RKF context plus ARS reasoning", walkthrough)
        self.assertIn("rkf-connect", walkthrough)
        self.assertIn("topic-review", walkthrough)

        overview = (example / "knowledge" / "overviews" / "tahope-project-overview.md").read_text(encoding="utf-8")
        self.assertIn("official TAHOPE introduction PDF", overview)

        synthesis = (example / "knowledge" / "synthesis" / "future-taiwan-meteorological-observation-experiment.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("terrain-rainfall", synthesis)
        self.assertIn("SoWMEX/TiMREX", synthesis)
        self.assertIn("TAHOPE/PRECIP", synthesis)
        self.assertIn("aerosol-cloud", synthesis)


if __name__ == "__main__":
    unittest.main()
