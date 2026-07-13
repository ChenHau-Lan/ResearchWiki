"""Conservative, inspectable RKF maintenance planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .core import Workspace, lint_graph_links, lint_knowledge_pages, lint_public_safety, paper_queue
from .sync import DoctorReport, run_connect_doctor, sha256_file


MAINTENANCE_CADENCES = {"daily", "weekly", "monthly"}


@dataclass(frozen=True)
class IncomingArtifact:
    logical_id: str
    checksum: str
    size_bytes: int


@dataclass(frozen=True)
class MaintenanceAction:
    action: str
    reason: str
    promotion: str = "none"
    requires_writer: bool = False


@dataclass(frozen=True)
class MaintenancePlan:
    cadence: str
    generated_at: str
    promotion: str
    incoming: tuple[IncomingArtifact, ...]
    actions: tuple[MaintenanceAction, ...]
    doctor: DoctorReport
    paper_queue_count: int
    lint_count: int

    def as_payload(self) -> dict[str, Any]:
        return {
            "cadence": self.cadence,
            "generated_at": self.generated_at,
            "promotion": self.promotion,
            "incoming": [
                {
                    "logical_id": item.logical_id,
                    "checksum": item.checksum,
                    "size_bytes": item.size_bytes,
                }
                for item in self.incoming
            ],
            "actions": [
                {
                    "action": item.action,
                    "reason": item.reason,
                    "promotion": item.promotion,
                    "requires_writer": item.requires_writer,
                }
                for item in self.actions
            ],
            "doctor": self.doctor.as_payload(),
            "paper_queue_count": self.paper_queue_count,
            "lint_count": self.lint_count,
        }


class MaintenanceBlocked(RuntimeError):
    """Raised when a maintenance action should not execute against shared state."""


def scan_incoming_artifacts(raw_root: Path) -> tuple[IncomingArtifact, ...]:
    """Inventory private incoming artifacts by logical name and checksum only."""

    incoming_root = raw_root / "incoming"
    if not incoming_root.exists():
        return ()
    artifacts = []
    for path in sorted(item for item in incoming_root.rglob("*") if item.is_file()):
        artifacts.append(
            IncomingArtifact(
                logical_id=f"raw/incoming/{path.relative_to(incoming_root).as_posix()}",
                checksum=sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )
    return tuple(artifacts)


def _actions_for_cadence(cadence: str) -> tuple[MaintenanceAction, ...]:
    daily = (
        MaintenanceAction(
            "raw.incoming.review",
            "review source identity and checksum before any conservative capture proposal",
            requires_writer=True,
        ),
        MaintenanceAction(
            "capture.project_pending",
            "fold only already-approved immutable capture events; Promotion: none",
            requires_writer=True,
        ),
        MaintenanceAction(
            "index.refresh.preview",
            "review whether public-safe index regeneration is needed",
            requires_writer=True,
        ),
    )
    weekly = daily + (
        MaintenanceAction("lint.run", "run structure, evidence, graph, and public-safety checks"),
        MaintenanceAction("paper.queue", "review papers needing PDFs, locators, or human feedback"),
        MaintenanceAction("hot.review", "review stale hot demand and unreviewed inbox material"),
    )
    monthly = weekly + (
        MaintenanceAction("topic.review", "produce merge, split, and staleness proposals only"),
        MaintenanceAction("synthesis.review", "review coverage and maturity without promoting claims"),
        MaintenanceAction("paper.migration.review", "review migration manifest status without live apply"),
        MaintenanceAction("raw.pdf.checksum.audit", "report immutable PDF identity checksum conflicts"),
        MaintenanceAction("cleanup.manifest.preview", "generate a read-only cleanup review manifest"),
    )
    return {"daily": daily, "weekly": weekly, "monthly": monthly}[cadence]


def plan_maintenance(ws: Workspace, *, cadence: str, now: datetime | None = None) -> MaintenancePlan:
    """Return an all-read-only maintenance plan for the requested cadence."""

    if cadence not in MAINTENANCE_CADENCES:
        raise ValueError("cadence must be one of: daily, weekly, monthly")
    checked = now or datetime.now()
    doctor = run_connect_doctor(ws, now=checked)
    lint_errors = [*lint_knowledge_pages(ws), *lint_graph_links(ws), *lint_public_safety(ws)]
    return MaintenancePlan(
        cadence=cadence,
        generated_at=checked.isoformat(timespec="seconds"),
        promotion="none",
        incoming=scan_incoming_artifacts(ws.paths.raw_root),
        actions=_actions_for_cadence(cadence),
        doctor=doctor,
        paper_queue_count=len(paper_queue(ws)),
        lint_count=len(lint_errors),
    )


def run_maintenance(ws: Workspace, *, cadence: str, now: datetime | None = None) -> dict[str, Any]:
    """Confirm a safe maintenance plan; canonical writes remain explicitly composed."""

    plan = plan_maintenance(ws, cadence=cadence, now=now)
    if plan.doctor.status == "blocked":
        raise MaintenanceBlocked("connection doctor reported blockers; maintenance remains read-only")
    return {
        **plan.as_payload(),
        "doctor_status": plan.doctor.status,
        "executed_actions": [],
        "promotion": "none",
    }
