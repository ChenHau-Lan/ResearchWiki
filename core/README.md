# RKF Core

RKF Core defines the command-independent contract for LLM Wiki-based research
memory: source candidates, active paper reading maturity, claim boundaries,
topic governance, knowledge objects, graph export, and optional connection
plans.

Active surfaces:

- `rkf/`: Python runtime and validation helpers.
- `tools/rk.py`: CLI wrapper.
- `schemas/`: SourceRecord, EvidenceArtifact, KnowledgeObject, ReadingLedger,
  Topic, GateDecision, and GraphEdge contracts.
- `templates/rkf/`: public-safe knowledge page templates.
- `MODE_REGISTRY.md`: skill/mode routing table.
- `AGENTS.md`: agent routing, reading maturity rules, and claim/publication
  boundaries.

The core posture is active accumulation. Paper drafts may begin from metadata,
abstracts, partial text, or user-provided PDFs; their frontmatter and ledger
must say exactly how much has actually been read and how much human feedback
exists. Evidence governance moves to the trust boundary: stable claims,
trusted synthesis, citation confidence, and publication require a locator,
human feedback, or an existing governed source. Explicit blockers prevent
promotion until reviewed.
