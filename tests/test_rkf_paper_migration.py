from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from rkf.core import Workspace, frontmatter, parse_frontmatter
from rkf.paper_migration import (
    MigrationPreviewError,
    run_preview,
    sha256_bytes,
    transform_paper_markdown,
    validate_paper_v1_1,
)


LEGACY_PAPER = """---
type: paper
status: draft
source_id: doi_example
reading_status: abstract-only
evidence_ids: []
topics: []
created: 2026-07-01
updated: 2026-07-01
---

# Example Paper

## Source Identity

- DOI: 10.1234/example
- Authors: Example et al. (2026)

## Reading Maturity

- Reading state: abstract-only

## Source-Grounded Summary

- Research question: Does the method reproduce the observed response?
- Method/data: A two-stage observation campaign.
- Key findings: The response increased in the treated case.
- Limitations: The sample only covers one season.

## Extracted Evidence And Locators

- Locator: page 4, Fig. 2
- What the source explicitly supports: a treated-case increase.
- What it does not support: universal causality.

## Future Agent Retrieval Brief

- Read this page when: assessing the observation method.
"""


BROAD_QUESTION_PAPER = LEGACY_PAPER + """

## Reader Notes

- My interpretation: This should redirect the current manuscript argument.

## Questions And Feedback

- User questions: How should my current manuscript be reframed around this result?
"""


PROJECT_SECTION_PAPER = LEGACY_PAPER + """

## Current Manuscript Use

- This paper supports the discussion section of my current manuscript.
"""


CATALOG_PAPER = LEGACY_PAPER + """

## Close-Reading Summary

- This source reports a close-reading result.

## Targeted-Reading Summary

- This source reports a targeted-reading result.

## Claim-Support Locators

- p. 7, Table 2

## What This Supports

- The source supports the reported response in its studied setting.

## What This Does Not Support

- The source does not support universal generalization.

## Local PDF Full Text Status

- Local reader verified a partial PDF route.

## Integration Notes For Transport-Smoke Manuscript

- Use this source only as a manuscript context proposal.

## Manuscript-Relevant Role

- Candidate role: discussion background.

## Graph Links

- Concepts: [[example-concept]]
"""


CANONICAL_PAPER = """---
schema: rkf-paper-v1.1
type: paper
status: draft
source_id: doi_canonical
access_state: metadata
review_state: unread
reading_state: metadata-only
reading_status: metadata-only
fulltext_status: needs-user-pdf
human_feedback_level: none
understanding_confidence: low
claim_readiness: not-ready
review_stage: ai-extracted
evidence_boundary: review-blocker
evidence_tier: reading-draft
evidence_ids: []
reading_ledger: state/reading/doi_canonical.json
topics: []
created: 2026-07-01
updated: 2026-07-01
sources: []
---

# Canonical Paper

## Source Identity

- DOI: 10.1234/canonical

## Reading Maturity

- Reading state: metadata-only

## Research Question

- Does the canonical question survive migration?

## Methods And Data

- A preserved method.

## Main Findings

- A preserved result.

## Evidence And Locators

- Locator: p. 8

## Limitations And Boundaries

- A preserved boundary.

## Questions About This Paper

- Does Figure 3 support the reported result?

## Future Agent Retrieval Brief

- Read this page when: checking the canonical example.

## Intrinsic Links

- [[canonical-method]]
"""


class RKFPaperMigrationTests(unittest.TestCase):
    def test_legacy_summary_becomes_paper_centered_sections(self) -> None:
        result = transform_paper_markdown(LEGACY_PAPER, page_id="papers/example")

        self.assertIn("## Research Question", result.text)
        self.assertIn("## Methods And Data", result.text)
        self.assertIn("## Main Findings", result.text)
        self.assertIn("## Limitations And Boundaries", result.text)
        self.assertIn("page 4, Fig. 2", result.text)
        self.assertIn("10.1234/example", result.text)
        self.assertEqual(result.input_checksum, sha256_bytes(LEGACY_PAPER.encode("utf-8")))
        self.assertEqual(result.meta["access_state"], "abstract")
        self.assertEqual(result.meta["review_state"], "unread")
        self.assertEqual(result.meta["reading_state"], "abstract-read")
        self.assertEqual(result.meta["reading_status"], "abstract-read")

    def test_broad_question_becomes_human_routing_proposal(self) -> None:
        result = transform_paper_markdown(BROAD_QUESTION_PAPER, page_id="papers/example")

        broad_question = next(
            block for block in result.routed_blocks if block.source_heading == "Questions And Feedback"
        )
        self.assertEqual(broad_question.classification, "broad-question")
        self.assertEqual(broad_question.proposed_target, "knowledge/questions")
        self.assertEqual(broad_question.review_status, "needs-human-routing")
        self.assertNotIn("How should my current manuscript", result.text)
        self.assertIn("This should redirect the current manuscript argument", BROAD_QUESTION_PAPER)

    def test_project_centered_section_is_manifested_instead_of_silently_dropped(self) -> None:
        result = transform_paper_markdown(PROJECT_SECTION_PAPER, page_id="papers/example")

        routed = next(block for block in result.routed_blocks if block.source_heading == "Current Manuscript Use")
        self.assertEqual(routed.classification, "project-or-cross-paper-context")
        self.assertEqual(routed.proposed_target, "knowledge/inbox")
        self.assertEqual(routed.review_status, "needs-human-routing")
        self.assertNotIn("discussion section of my current manuscript", result.text)

    def test_canonical_paper_sections_are_preserved_as_is(self) -> None:
        result = transform_paper_markdown(CANONICAL_PAPER, page_id="papers/canonical")

        self.assertIn("Does the canonical question survive migration?", result.text)
        self.assertIn("A preserved method.", result.text)
        self.assertIn("A preserved result.", result.text)
        self.assertIn("Locator: p. 8", result.text)
        self.assertIn("[[canonical-method]]", result.text)
        self.assertEqual(result.routed_blocks, ())

    def test_known_legacy_catalog_routes_without_unresolved_human_work(self) -> None:
        result = transform_paper_markdown(CATALOG_PAPER, page_id="papers/example")

        self.assertIn("This source reports a close-reading result.", result.text)
        self.assertIn("p. 7, Table 2", result.text)
        self.assertIn("does not support universal generalization", result.text)
        self.assertIn("partial PDF route", result.text)
        self.assertNotIn("Use this source only as a manuscript context proposal.", result.text)
        routes = {block.source_heading: block for block in result.routed_blocks}
        self.assertEqual(routes["Integration Notes For Transport-Smoke Manuscript"].proposed_target, "knowledge/project-synthesis")
        self.assertEqual(routes["Integration Notes For Transport-Smoke Manuscript"].review_status, "proposed-review")
        self.assertEqual(routes["Manuscript-Relevant Role"].review_status, "proposed-review")
        self.assertEqual(routes["Graph Links"].review_status, "proposed-review")
        self.assertFalse(any(block.review_status == "needs-human-routing" for block in result.routed_blocks))

    def test_preamble_and_duplicate_canonical_sections_are_not_silently_lost(self) -> None:
        source = LEGACY_PAPER.replace(
            "# Example Paper\n\n",
            "# Example Paper\n\n- Preamble locator: p. 1\n\n",
        ) + """

## Main Findings

- First canonical finding must survive.

## Main Findings

- Second canonical finding must survive.
"""

        result = transform_paper_markdown(source, page_id="papers/example")

        self.assertIn("First canonical finding must survive.", result.text)
        self.assertIn("Second canonical finding must survive.", result.text)
        preamble = next(block for block in result.routed_blocks if block.source_heading == "Preamble")
        self.assertEqual(
            preamble.content_hash,
            sha256_bytes(b"- Preamble locator: p. 1"),
        )

    def test_preview_validator_rejects_invalid_canonical_state_section_and_maturity_mirror(self) -> None:
        invalid = CANONICAL_PAPER.replace("access_state: metadata", "access_state: other").replace(
            "reading_status: metadata-only", "reading_status: abstract-read"
        ).replace(
            "## Intrinsic Links", "## Legacy Links"
        )

        errors = validate_paper_v1_1(invalid)

        self.assertIn("access_state must use the canonical RKF v1 enum", errors)
        self.assertIn("reading_status must equal reading_state", errors)
        self.assertIn("missing canonical paper section Intrinsic Links", errors)

    def test_paper_relations_round_trip_as_mapping_list(self) -> None:
        raw = """---
type: project-synthesis
paper_relations:
  - paper_id: papers/example
    relation: uses-paper
---

# Project synthesis
"""

        meta, body = parse_frontmatter(raw)
        rendered = frontmatter(meta)
        reparsed, _ = parse_frontmatter(rendered + body)

        self.assertEqual(
            reparsed["paper_relations"],
            [{"paper_id": "papers/example", "relation": "uses-paper"}],
        )

    def test_paper_template_uses_v1_1_paper_centered_contract(self) -> None:
        template = (Path(__file__).resolve().parents[1] / "templates" / "rkf" / "paper.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("schema: rkf-paper-v1.1", template)
        self.assertIn("access_state: metadata", template)
        self.assertIn("review_state: unread", template)
        for heading in (
            "Source Identity",
            "Reading Maturity",
            "Research Question",
            "Methods And Data",
            "Main Findings",
            "Evidence And Locators",
            "Limitations And Boundaries",
            "Questions About This Paper",
            "Future Agent Retrieval Brief",
            "Intrinsic Links",
        ):
            self.assertIn(f"## {heading}", template)
        self.assertNotIn("## Reader Notes", template)
        self.assertNotIn("## AI/Agent Notes", template)

    def test_knowledge_schema_describes_v1_1_paper_and_portable_relations(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "knowledge_object.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["schema"]["type"], "string")
        self.assertIn("evidence_tier", schema["properties"])
        relation_items = schema["properties"]["paper_relations"]["items"]
        self.assertEqual(relation_items["properties"]["relation"]["enum"], [
            "uses-paper",
            "compares-paper",
            "extends-from-paper",
            "discusses-paper",
        ])

    def test_reading_ledger_schema_accepts_preview_migration_event(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "reading_ledger.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["schema"]["enum"], [
            "rkf-reading-ledger-v1",
            "rkf-reading-ledger-v1.1",
        ])
        event_types = schema["properties"]["events"]["items"]["properties"]["type"]["enum"]
        self.assertIn("inbox-injection", event_types)
        self.assertIn("migration", event_types)


class RKFPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.wiki = self.root / "wiki"
        self.raw = self.root / "raw"
        self.repo.mkdir()
        self.wiki.mkdir()
        self.raw.mkdir()
        (self.repo / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{self.wiki.as_posix()}"\n'
            f'raw_root = "{self.raw.as_posix()}"\n',
            encoding="utf-8",
        )
        self.paper_root = self.wiki / "knowledge" / "papers"
        self.paper_root.mkdir(parents=True)
        for index in range(57):
            page = LEGACY_PAPER.replace("doi_example", f"doi_example_{index:02d}")
            (self.paper_root / f"paper-{index:02d}.md").write_text(page, encoding="utf-8")
        self.workspace = Workspace(self.repo)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_controlled_fifty_seven_page_corpus_keeps_live_inputs_unchanged(self) -> None:
        inputs = sorted(self.paper_root.glob("*.md"))
        before = {path.name: sha256_bytes(path.read_bytes()) for path in inputs}
        report_root = self.repo / ".rkf_private" / "migration_reports"

        report = run_preview(self.workspace, report_root=report_root, expected_count=57)

        after = {path.name: sha256_bytes(path.read_bytes()) for path in inputs}
        self.assertEqual(report.input_count, 57)
        self.assertEqual(report.output_count, 57)
        self.assertEqual(report.diff_count, 57)
        self.assertEqual(before, after)
        self.assertTrue((report.report_dir / "manifest.json").exists())
        self.assertTrue((report.report_dir / "summary.json").exists())
        self.assertEqual(len(list((report.report_dir / "diffs").glob("*.diff"))), 57)
        manifest = json.loads((report.report_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["paper_state_migration"]["before_legacy_reading_counts"], {"abstract-only": 57})
        self.assertEqual(manifest["paper_state_migration"]["after_access_state_counts"], {"abstract": 57})

    def test_ambiguous_routing_blocks_readiness_and_manifest_hash_is_stable(self) -> None:
        broad_path = self.paper_root / "paper-00.md"
        broad_path.write_text(BROAD_QUESTION_PAPER.replace("doi_example", "doi_example_00"), encoding="utf-8")

        first = run_preview(
            self.workspace,
            report_root=self.repo / ".rkf_private" / "migration_reports_one",
            expected_count=57,
        )
        second = run_preview(
            self.workspace,
            report_root=self.repo / ".rkf_private" / "migration_reports_two",
            expected_count=57,
        )
        manifest = json.loads((first.report_dir / "manifest.json").read_text(encoding="utf-8"))
        broad_page = next(item for item in manifest["pages"] if item["source_page"].endswith("paper-00.md"))

        self.assertFalse(first.ready_for_live_apply)
        self.assertEqual(first.unresolved_count, 1)
        self.assertEqual(first.manifest_hash, second.manifest_hash)
        self.assertEqual(broad_page["routed_blocks"][1]["review_status"], "needs-human-routing")
        self.assertEqual(broad_page["routed_blocks"][1]["proposed_target"], "knowledge/questions")

    def test_preview_classifies_legacy_candidates_as_isolated_without_identity_output(self) -> None:
        legacy_dir = self.wiki / "state" / "search_runs" / "legacy-fixture"
        legacy_dir.mkdir(parents=True)
        legacy_dir.joinpath("candidates.json").write_text(
            json.dumps(
                {
                    "schema": "rkf-discovery-run-v1",
                    "query": "private fixture query",
                    "topic_id": "fixture-topic",
                    "live": False,
                    "gate": "candidates_are_not_evidence",
                    "created": "2026-07-13",
                    "candidates": [
                        {
                            "source_id": "private-source",
                            "title": "Private Candidate",
                            "year": 2026,
                            "doi": "10.1234/private",
                            "evidence_role": "candidate only",
                            "status": "metadata_ok",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        report = run_preview(
            self.workspace,
            report_root=self.repo / ".rkf_private" / "migration_reports",
            expected_count=57,
        )
        manifest = json.loads((report.report_dir / "manifest.json").read_text(encoding="utf-8"))
        serialized = json.dumps(manifest, sort_keys=True)

        self.assertEqual(report.legacy_discovery_count, 1)
        self.assertEqual(manifest["legacy_discovery"]["isolated_candidate_count"], 1)
        self.assertEqual(manifest["legacy_discovery"]["after_active_legacy_candidate_count"], 0)
        self.assertNotIn("Private Candidate", serialized)
        self.assertNotIn("private fixture query", serialized)

    def test_preview_copies_existing_ledger_before_appending_migration_event(self) -> None:
        ledger_root = self.wiki / "state" / "reading"
        ledger_root.mkdir(parents=True)
        source_id = "doi_example_00"
        original_ledger = {
            "schema": "rkf-reading-ledger-v1",
            "source_id": source_id,
            "knowledge_path": "knowledge/papers/paper-00.md",
            "events": [
                {
                    "created": "2026-07-01T10:00:00",
                    "type": "human-feedback",
                    "actor": "human",
                    "summary": "Existing reading feedback.",
                    "public_safe": True,
                }
            ],
            "created": "2026-07-01",
            "updated": "2026-07-01",
        }
        live_ledger_path = ledger_root / f"{source_id}.json"
        live_ledger_path.write_text(json.dumps(original_ledger), encoding="utf-8")

        report = run_preview(
            self.workspace,
            report_root=self.repo / ".rkf_private" / "migration_reports",
            expected_count=57,
        )
        copied = json.loads(
            (report.report_dir / "workspace" / "state" / "reading" / f"{source_id}.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(json.loads(live_ledger_path.read_text(encoding="utf-8")), original_ledger)
        self.assertEqual(copied["events"][0]["summary"], "Existing reading feedback.")
        self.assertEqual(copied["events"][-1]["type"], "migration")

    def test_preview_rejects_a_report_root_inside_canonical_storage(self) -> None:
        forbidden_root = self.wiki / ".rkf_private" / "migration_reports"

        with self.assertRaises(MigrationPreviewError):
            run_preview(self.workspace, report_root=forbidden_root, expected_count=57)

        self.assertFalse(forbidden_root.exists())

    def test_preview_rejects_a_private_root_symlink_outside_the_workspace(self) -> None:
        external = self.root / "external-report-target"
        external.mkdir()
        private_link = self.repo / ".rkf_private"
        private_link.symlink_to(external, target_is_directory=True)

        with self.assertRaises(MigrationPreviewError):
            run_preview(
                self.workspace,
                report_root=private_link / "migration_reports",
                expected_count=57,
            )

        self.assertEqual(list(external.iterdir()), [])

    def test_preview_keeps_unsafe_source_ids_inside_the_private_report(self) -> None:
        unsafe_target = self.wiki / "escaped-ledger.json"
        unsafe_source_id = str(unsafe_target.with_suffix(""))
        (self.paper_root / "paper-00.md").write_text(
            LEGACY_PAPER.replace("doi_example", unsafe_source_id),
            encoding="utf-8",
        )

        report = run_preview(
            self.workspace,
            report_root=self.repo / ".rkf_private" / "migration_reports",
            expected_count=57,
        )

        self.assertFalse(unsafe_target.exists())
        self.assertFalse(report.ready_for_live_apply)


if __name__ == "__main__":
    unittest.main()
