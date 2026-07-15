#!/usr/bin/env python3
"""Run a reproducible, zero-network RKF Ask scaling baseline."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rkf.actions import ActionRequest, RKFActionRuntime  # noqa: E402
from rkf.core import Workspace, create_source, frontmatter, write_text  # noqa: E402
from rkf.query_index import RetrievalQueryIndex  # noqa: E402
from rkf.retrieval import search_central_rkf  # noqa: E402


PROJECT_ID = "prj_1234567890abcdef12345678"
QUERY = "ask-scaling-target"


def _write_marker(root: Path) -> None:
    (root / ".rkf-connect.toml").write_text(
        "version = 2\n\n[rkf]\n"
        "available = true\nactivation = \"manual\"\nquery_first = true\n"
        "capture_mode = \"active-aggressive\"\n"
        f'project_id = "{PROJECT_ID}"\n'
        "project_name = \"Synthetic Ask Scaling Baseline\"\n"
        "marker_schema = \"rkf-connect-v2\"\n"
        "connector_version = \"1.1.0\"\n"
        "connected_at = \"2026-07-15T00:00:00Z\"\n",
        encoding="utf-8",
    )


def _populate(
    workspace: Workspace,
    *,
    document_count: int,
) -> list[str]:
    paper_ids: list[str] = []
    for index in range(document_count):
        source = create_source(
            workspace,
            kind="doi",
            value=f"10.5555/rkf.scale.{index:04d}",
            title=f"Synthetic Ask Scaling Paper {index:04d}",
            topic_id="ask-scaling",
            note=f"{QUERY} public-safe synthetic source {index:04d}.",
        )
        source_id = str(source["source_id"])
        paper_id = f"papers/{source_id}"
        write_text(
            workspace.paths.knowledge / f"{paper_id}.md",
            frontmatter(
                {
                    "schema": "rkf-paper-v1.1",
                    "type": "paper",
                    "source_id": source_id,
                    "access_state": "fulltext",
                    "review_state": "annotated",
                    "reading_state": "human-reviewed",
                    "reading_status": "human-reviewed",
                    "fulltext_status": "available",
                    "evidence_boundary": "review-blocker",
                    "claim_readiness": "evidence-required",
                    "public_safe": True,
                    "topics": ["ask-scaling"],
                }
            )
            + f"# Synthetic Ask Scaling Paper {index:04d}\n\n"
            + f"{QUERY} public-safe synthetic paper context {index:04d}.\n",
        )
        paper_ids.append(paper_id)
    return paper_ids


def _stable_projection(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "cards": result["cards"],
        "graph_context": result["graph_context"],
        "answer_mode": result["answer_mode"],
        "answer_boundary": result["answer_boundary"],
        "answer_card_ids": result["answer_card_ids"],
        "retrieval_result_fingerprint": result["retrieval_result_fingerprint"],
    }


def _canonical_bytes(workspace: Workspace) -> dict[str, bytes]:
    """Snapshot canonical research objects while excluding derived private state."""

    roots = (
        workspace.paths.knowledge,
        workspace.paths.state / "findings",
        workspace.paths.evidence_index / "cards",
        workspace.paths.state / "claims",
        workspace.paths.state / "syntheses",
    )
    snapshot: dict[str, bytes] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            snapshot[path.relative_to(workspace.paths.wiki_root).as_posix()] = (
                path.read_bytes()
            )
    return snapshot


def _evidence_contract(result: dict[str, Any]) -> dict[str, Any]:
    cards = result["cards"]
    return {
        "answer_policy": result["answer_policy"],
        "answer_mode": result["answer_mode"],
        "answer_boundary": result["answer_boundary"],
        "answer_count": result["answer_count"],
        "all_cards_are_evidence": bool(cards)
        and all(card.get("type") == "evidence" for card in cards),
        "all_cards_are_locator_backed": bool(cards)
        and all(card.get("evidence_use") == "locator-backed" for card in cards),
        "all_cards_are_claim_ready": bool(cards)
        and all(card.get("claim_ready") is True for card in cards),
    }


def _run_search(
    workspace: Workspace,
    *,
    limit: int,
    query_index: RetrievalQueryIndex | None,
) -> dict[str, Any]:
    return search_central_rkf(
        workspace,
        QUERY,
        limit=limit,
        page_types=["evidence"],
        answer_policy="evidence-only",
        query_index=query_index,
        persist_retrieval_run=False,
    )


def run_baseline(
    *,
    document_count: int = 120,
    canonical_count: int = 24,
    limit: int = 10,
) -> dict[str, Any]:
    if document_count < 1:
        raise ValueError("document_count must be positive")
    if canonical_count < 1 or canonical_count > document_count:
        raise ValueError("canonical_count must be between one and document_count")
    if limit < 1:
        raise ValueError("limit must be positive")

    with tempfile.TemporaryDirectory(prefix="rkf-ask-baseline-") as directory:
        root = Path(directory)
        raw_root = root / "raw"
        raw_root.mkdir()
        (root / "rkf.workspace.toml").write_text(
            "[storage]\n"
            f'wiki_root = "{root.as_posix()}"\n'
            f'raw_root = "{raw_root.as_posix()}"\n',
            encoding="utf-8",
        )
        _write_marker(root)
        workspace = Workspace(root)
        paper_ids = _populate(workspace, document_count=document_count)
        runtime = RKFActionRuntime(workspace=workspace, project_root=root)
        activated = runtime.execute(ActionRequest("rkf.activate"))
        if activated.status != "ok":
            raise RuntimeError("synthetic baseline activation failed")
        for index, paper_id in enumerate(paper_ids[:canonical_count]):
            evidence = runtime.execute(
                ActionRequest(
                    "workflow.read",
                    {
                        "paper_id": paper_id,
                        "summary": f"{QUERY} locator-backed observation {index:04d}.",
                        "locator_kind": "page",
                        "locator_value": str(index + 1),
                        "stance": "supports",
                        "verification_state": "unreviewed",
                    },
                )
            )
            if evidence.status != "ok":
                raise RuntimeError("synthetic baseline Evidence creation failed")

        canonical_before = _canonical_bytes(workspace)
        full_scan = _run_search(workspace, limit=limit, query_index=None)
        query_index = RetrievalQueryIndex(root)
        indexed_cold = _run_search(
            workspace,
            limit=limit,
            query_index=query_index,
        )
        indexed_warm = _run_search(
            workspace,
            limit=limit,
            query_index=query_index,
        )
        query_index.path.unlink()
        indexed_rebuilt_after_delete = _run_search(
            workspace,
            limit=limit,
            query_index=query_index,
        )
        canonical_after_delete_rebuild = _canonical_bytes(workspace)
        runtime.execute(ActionRequest("rkf.deactivate"))

        parity = (
            _stable_projection(full_scan)
            == _stable_projection(indexed_cold)
            == _stable_projection(indexed_warm)
            == _stable_projection(indexed_rebuilt_after_delete)
        )
        evidence_contracts = [
            _evidence_contract(result)
            for result in (
                full_scan,
                indexed_cold,
                indexed_warm,
                indexed_rebuilt_after_delete,
            )
        ]
        evidence_contract = evidence_contracts[0]
        evidence_trust_preserved = (
            all(contract == evidence_contract for contract in evidence_contracts)
            and evidence_contract["answer_policy"] == "evidence-only"
            and evidence_contract["answer_mode"] == "evidence"
            and evidence_contract["answer_boundary"] == "locator-backed"
            and evidence_contract["answer_count"] > 0
            and evidence_contract["all_cards_are_evidence"]
            and evidence_contract["all_cards_are_locator_backed"]
            and evidence_contract["all_cards_are_claim_ready"]
        )
        full_reads = int(full_scan["deterministic_index"]["source_files_read"])
        warm_reads = int(indexed_warm["deterministic_index"]["source_files_read"])
        candidate_limit = max(limit * 3, limit + 10)
        canonical_validated = int(
            indexed_warm["deterministic_index"]["canonical_validated"]
        )
        targets = {
            "ranking_and_trust_parity": parity,
            "evidence_only_trust_contract_preserved": evidence_trust_preserved,
            "canonical_validation_exercised": canonical_validated > 0,
            "warm_reads_fewer_corpus_files": warm_reads < full_reads,
            "warm_reads_zero_corpus_files": warm_reads == 0,
            "canonical_validation_within_candidate_window": (
                canonical_validated <= candidate_limit
            ),
            "deleted_index_rebuilds": (
                indexed_rebuilt_after_delete["deterministic_index"]["state"]
                == "rebuilt"
            ),
            "deleted_index_rebuild_preserves_canonical_bytes": (
                bool(canonical_before)
                and canonical_after_delete_rebuild == canonical_before
            ),
            "deleted_index_rebuild_preserves_result": (
                _stable_projection(indexed_rebuilt_after_delete)
                == _stable_projection(full_scan)
            ),
            "milliseconds_are_diagnostic_not_a_threshold": True,
        }
        passed = all(targets.values())
        return {
            "schema": "rkf-ask-scaling-baseline-v1",
            "status": "passed" if passed else "failed",
            "offline": True,
            "temporary_workspace": True,
            "paths_redacted": True,
            "dataset": {
                "documents": document_count,
                "canonical_evidence": canonical_count,
                "limit": limit,
                "query": QUERY,
            },
            "full_scan": {
                "timing": full_scan["timing"],
                "index": full_scan["deterministic_index"],
            },
            "indexed_cold": {
                "timing": indexed_cold["timing"],
                "index": indexed_cold["deterministic_index"],
            },
            "indexed_warm": {
                "timing": indexed_warm["timing"],
                "index": indexed_warm["deterministic_index"],
            },
            "indexed_rebuilt_after_delete": {
                "timing": indexed_rebuilt_after_delete["timing"],
                "index": indexed_rebuilt_after_delete["deterministic_index"],
            },
            "evidence_contract": evidence_contract,
            "timing_semantics": {
                "non_overlapping": True,
                "index_ms": (
                    "deterministic manifest/load/store overhead; excludes scan_ms"
                ),
                "scan_ms": "corpus-snapshot content read and serialization time",
            },
            "targets": targets,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=int, default=120)
    parser.add_argument("--canonical", type=int, default=24)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_baseline(
            document_count=args.documents,
            canonical_count=args.canonical,
            limit=args.limit,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        result = {
            "schema": "rkf-ask-scaling-baseline-v1",
            "status": "failed",
            "paths_redacted": True,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
