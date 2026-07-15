"""Optional provider contracts for RKF v1; implementations remain adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class FullTextProviderResult:
    status: str
    provider: str
    provider_version: str
    route: str = ""
    tried_routes: tuple[str, ...] = ()
    artifact_sha256: str = ""
    private_artifact_handle: str = ""
    blocker_codes: tuple[str, ...] = ()


class FullTextProvider(Protocol):
    def obtain(self, *, source_id: str, identifier: str) -> FullTextProviderResult: ...


@dataclass(frozen=True)
class RetrievalHit:
    object_id: str
    locator: str
    score: float
    match_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievalProvider(Protocol):
    def search(self, *, query: str, limit: int = 10) -> list[RetrievalHit]: ...


class AppraisalProvider(Protocol):
    def appraise(self, *, paper_id: str, profile: str = "generic") -> dict[str, Any]: ...
