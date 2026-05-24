# RKF Core

RKF Core defines the command-independent contract for LLM Wiki-based research
memory: source candidates, evidence gates, topic governance, knowledge objects,
graph export, and optional connection plans.

Active surfaces:

- `rkf/`: Python runtime and validation helpers.
- `tools/rk.py`: CLI wrapper.
- `schemas/`: SourceRecord, EvidenceArtifact, KnowledgeObject, Topic,
  GateDecision, and GraphEdge contracts.
- `templates/rkf/`: public-safe knowledge page templates.
- `MODE_REGISTRY.md`: skill/mode routing table.
- `AGENTS.md`: agent routing and evidence rules.
