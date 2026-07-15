from __future__ import annotations

import unittest

from tools.benchmark_rkf_ask import run_baseline


class RKFAskScalingBaselineTests(unittest.TestCase):
    def test_relative_io_targets_and_trust_parity_pass(self) -> None:
        result = run_baseline(document_count=30, canonical_count=12, limit=5)

        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["targets"]["ranking_and_trust_parity"])
        self.assertTrue(
            result["targets"]["evidence_only_trust_contract_preserved"]
        )
        self.assertTrue(result["targets"]["canonical_validation_exercised"])
        self.assertGreater(result["full_scan"]["index"]["source_files_read"], 0)
        self.assertEqual(result["indexed_warm"]["index"]["state"], "hit")
        self.assertEqual(result["indexed_warm"]["index"]["source_files_read"], 0)
        self.assertGreater(
            result["indexed_warm"]["index"]["canonical_validated"],
            0,
        )
        self.assertTrue(
            result["targets"]["canonical_validation_within_candidate_window"]
        )
        self.assertEqual(
            result["indexed_rebuilt_after_delete"]["index"]["state"],
            "rebuilt",
        )
        self.assertTrue(result["targets"]["deleted_index_rebuilds"])
        self.assertTrue(
            result["targets"]["deleted_index_rebuild_preserves_canonical_bytes"]
        )
        self.assertTrue(
            result["targets"]["deleted_index_rebuild_preserves_result"]
        )
        self.assertEqual(result["evidence_contract"]["answer_policy"], "evidence-only")
        self.assertEqual(result["evidence_contract"]["answer_mode"], "evidence")
        self.assertEqual(
            result["evidence_contract"]["answer_boundary"],
            "locator-backed",
        )
        self.assertTrue(result["evidence_contract"]["all_cards_are_evidence"])
        self.assertTrue(
            result["evidence_contract"]["all_cards_are_locator_backed"]
        )
        self.assertTrue(result["evidence_contract"]["all_cards_are_claim_ready"])
        self.assertTrue(result["timing_semantics"]["non_overlapping"])
        self.assertIn("excludes scan_ms", result["timing_semantics"]["index_ms"])
        self.assertTrue(result["targets"]["milliseconds_are_diagnostic_not_a_threshold"])


if __name__ == "__main__":
    unittest.main()
