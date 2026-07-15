#!/usr/bin/env python3
"""Run the complete RKF v1 workflow against two temporary synthetic papers."""

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

from rkf.actions import ActionRequest, ActionResult, RKFActionRuntime
from rkf.core import Workspace
from tools.bootstrap_rkf import bootstrap_local
from tools.rkf_auto_connect import connect_project


WORKFLOW_NAMES = ["Add", "Ask", "Read", "Compare & Synthesize", "Review"]
SYNTHETIC_PAPERS = (
    {
        "doi": "10.5555/rkf.synthetic.alpha",
        "paper_id": "papers/doi_10_5555_rkf_synthetic_alpha",
        "source_id": "doi_10_5555_rkf_synthetic_alpha",
        "title": "Synthetic Treatment Response Alpha",
        "body": (
            "This zero-network synthetic fixture reports a larger response under "
            "the quickstart treatment. No real-world research claim is represented."
        ),
    },
    {
        "doi": "10.5555/rkf.synthetic.beta",
        "paper_id": "papers/doi_10_5555_rkf_synthetic_beta",
        "source_id": "doi_10_5555_rkf_synthetic_beta",
        "title": "Synthetic Treatment Response Beta",
        "body": (
            "This zero-network synthetic fixture reports no larger response under "
            "the quickstart treatment. No real-world research claim is represented."
        ),
    },
)


class QuickstartFailure(RuntimeError):
    """A path-safe assertion failure from one named quickstart stage."""


def _require_status(result: ActionResult, expected: str, stage: str) -> None:
    if result.status != expected:
        raise QuickstartFailure(stage)


def _write_synthetic_paper(workspace: Workspace, paper: dict[str, str]) -> None:
    path = workspace.paths.knowledge / f"{paper['paper_id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "schema: rkf-paper-v1.1\n"
        "type: paper\n"
        f"source_id: {paper['source_id']}\n"
        "access_state: fulltext\n"
        "review_state: annotated\n"
        "reading_state: human-reviewed\n"
        "reading_status: human-reviewed\n"
        "fulltext_status: available\n"
        "---\n\n"
        f"# {paper['title']}\n\n"
        "## Research Question\n\n"
        "How does the synthetic quickstart treatment affect the synthetic response?\n\n"
        "## Evidence Summary\n\n"
        f"{paper['body']}\n",
        encoding="utf-8",
    )


def run_quickstart() -> dict[str, Any]:
    """Execute the five workflows without network, global config, or persistent data."""

    with tempfile.TemporaryDirectory(prefix="rkf-quickstart-") as temporary:
        root = Path(temporary)
        bootstrap = bootstrap_local(root, apply=True)
        if bootstrap.get("status") != "configured":
            raise QuickstartFailure("bootstrap")
        connection = connect_project(root, project_name="RKF Synthetic Quickstart")
        if connection.get("status") != "connected":
            raise QuickstartFailure("connect")

        workspace = Workspace(root)
        runtime = RKFActionRuntime(workspace=workspace, project_root=root)
        activated = runtime.execute(ActionRequest("rkf.activate"))
        _require_status(activated, "ok", "activate")

        add_results: list[ActionResult] = []
        for paper in SYNTHETIC_PAPERS:
            result = runtime.execute(
                ActionRequest(
                    "workflow.add",
                    {
                        "title": paper["title"],
                        "text": (
                            f"Synthetic paper fixture DOI {paper['doi']} for the "
                            "zero-network RKF quickstart."
                        ),
                        "origin": "synthetic:quickstart",
                        "doi": paper["doi"],
                        "authors": "RKF Synthetic Fixture",
                        "year": "2026",
                        "intent": "paper-search",
                        "topic_id": "rkf-quickstart",
                    },
                )
            )
            _require_status(result, "ok", "workflow.add")
            if result.payload.get("promotion") != "none":
                raise QuickstartFailure("add-promotion-boundary")
            if result.payload.get("materialization") not in {"queued", "materialized"}:
                raise QuickstartFailure("workflow.add-materialization")
            add_results.append(result)
            _write_synthetic_paper(workspace, paper)

        ask = runtime.execute(
            ActionRequest("workflow.ask", {"query": "synthetic quickstart treatment response"})
        )
        _require_status(ask, "ok", "workflow.ask")
        if int(ask.payload.get("count", 0)) < 2:
            raise QuickstartFailure("workflow.ask-results")
        if ask.payload.get("answer_mode") != "context-only":
            raise QuickstartFailure("workflow.ask-context-boundary")
        if any(bool(card.get("claim_ready")) for card in ask.payload.get("cards", [])):
            raise QuickstartFailure("workflow.ask-claim-boundary")

        missing_locator = runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": SYNTHETIC_PAPERS[0]["paper_id"],
                    "summary": "A locator-free note must not become canonical Evidence.",
                },
            )
        )
        _require_status(missing_locator, "blocked", "locator-promotion-gate")

        finding_a = runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "paper_id": SYNTHETIC_PAPERS[0]["paper_id"],
                    "summary": "The synthetic alpha fixture reports a larger response.",
                    "reading_scope": "fulltext",
                    "locator_state": "missing",
                },
            )
        )
        _require_status(finding_a, "ok", "workflow.read-finding")
        finding_a_exact = runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "capture-finding",
                    "finding_id": finding_a.payload["finding_id"],
                    "locator_state": "exact",
                    "locator": {"kind": "figure", "value": "Fig. A1"},
                },
            )
        )
        _require_status(finding_a_exact, "ok", "workflow.read-locate-finding")
        evidence_a = runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "operation": "promote-evidence",
                    "finding_id": finding_a.payload["finding_id"],
                    "stance": "supports",
                    "verification_state": "human-verified",
                },
            )
        )
        evidence_b = runtime.execute(
            ActionRequest(
                "workflow.read",
                {
                    "paper_id": SYNTHETIC_PAPERS[1]["paper_id"],
                    "summary": "The synthetic beta fixture reports no larger response.",
                    "locator_kind": "table",
                    "locator_value": "Table B1",
                    "stance": "opposes",
                    "verification_state": "human-verified",
                },
            )
        )
        _require_status(evidence_a, "ok", "workflow.read-alpha")
        _require_status(evidence_b, "ok", "workflow.read-beta")

        claim = runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "claim",
                    "statement": "The two synthetic fixtures disagree about the treatment response.",
                    "evidence_ids": [
                        evidence_a.payload["evidence_id"],
                        evidence_b.payload["evidence_id"],
                    ],
                    "status": "disputed",
                },
            )
        )
        _require_status(claim, "ok", "workflow.compare-synthesize-claim")
        synthesis = runtime.execute(
            ActionRequest(
                "workflow.compare-synthesize",
                {
                    "operation": "synthesis",
                    "research_question": (
                        "How does the synthetic quickstart treatment affect the synthetic response?"
                    ),
                    "claim_ids": [claim.payload["claim_id"]],
                    "provisional_conclusion": (
                        "The fixtures disagree, so no general conclusion is promoted."
                    ),
                    "next_action": "Inspect another synthetic fixture.",
                },
            )
        )
        _require_status(synthesis, "ok", "workflow.compare-synthesize-synthesis")
        if len(synthesis.payload.get("evidence_matrix", [])) != 2:
            raise QuickstartFailure("evidence-matrix")

        review = runtime.execute(ActionRequest("workflow.review"))
        _require_status(review, "ok", "workflow.review")
        deactivated = runtime.execute(ActionRequest("rkf.deactivate"))
        _require_status(deactivated, "ok", "deactivate")

        return {
            "schema": "rkf-quickstart-v1",
            "status": "passed",
            "quickstart": "passed",
            "offline": True,
            "temporary_workspace": True,
            "paper_count": len(SYNTHETIC_PAPERS),
            "workflows_completed": len(WORKFLOW_NAMES),
            "workflow_names": WORKFLOW_NAMES,
            "context_boundary_preserved": ask.payload.get("answer_mode") == "context-only",
            "finding_promotion_preserved": (
                evidence_a.payload.get("source_finding_id")
                == finding_a.payload.get("finding_id")
            ),
            "promotion_boundary_preserved": all(
                item.payload.get("promotion") == "none" for item in add_results
            ),
            "locator_gate_preserved": missing_locator.status == "blocked",
            "activation_closed": True,
            "paths_redacted": True,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the isolated workflow check and return a non-zero status on failure",
    )
    parser.parse_args(argv)
    try:
        result = run_quickstart()
    except QuickstartFailure as error:
        result = {
            "schema": "rkf-quickstart-v1",
            "status": "failed",
            "quickstart": "failed",
            "failed_stage": str(error),
            "paths_redacted": True,
        }
    except (Exception, SystemExit):
        result = {
            "schema": "rkf-quickstart-v1",
            "status": "failed",
            "quickstart": "failed",
            "paths_redacted": True,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
