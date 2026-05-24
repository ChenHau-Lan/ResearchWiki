# RKF Data Contract

## Objects

- `SourceRecord`: source candidate or resolved identity.
- `EvidenceArtifact`: private PDF or related artifact pointer plus public-safe
  provenance.
- `KnowledgeObject`: maintained Markdown page with an explicit evidence
  boundary.
- `Topic`: governed research scope.
- `GateDecision`: source identity, PDF acquisition, PDF QC, claim-support, or
  synthesis checkpoint.
- `GraphEdge`: typed relation among sources, evidence, topics, and wiki pages.

## Source Status

- `new`
- `metadata_ok`
- `candidate_found`
- `pdf_checkpoint_required`
- `pdf_downloaded`
- `pdf_qc_needed`
- `pdf_qc_done`
- `wiki_done`
- `abstract_only`
- `blocked`

## Knowledge Types

- `paper`
- `question`
- `concept`
- `claim`
- `topic`
- `synthesis`
- `overview`
- `project-synthesis`
- `meeting`
- `seminar`

## Paper Rule

Paper pages require:

- a `SourceRecord`;
- a private PDF `EvidenceArtifact`;
- PDF QC status `codex_qc_done` or `human_qc_done`;
- `evidence_boundary: pdf-evidence`;
- at least one PDF locator or explicit locator TODO.

Durable article text is not a data layer.
