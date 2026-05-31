# RKF Architecture

RKF is an LLM Wiki-based research knowledge framework for active reading. It
separates source capture, reading maturity, operational reading ledgers,
maintained wiki knowledge, claim/publication boundaries, topic review, graph
export, ARS handoff proposals, and optional shared-database connections.

## Layer Model

| Layer | Purpose | Public Git Policy |
|---|---|---|
| Intake | Capture DOI, URL, topic, idea, question, PDF, or discussion leads | public-safe source records only |
| Paper Drafts | Create early paper pages even from metadata or abstract state | concise Markdown with maturity fields |
| Reading Maturity | Track full-text availability, reading state, human feedback, and trust | frontmatter and summaries only |
| Reading Ledger | Store public-safe reading events, questions, corrections, and blockers | `state/reading/` operational memory |
| Claim Boundary | Decide when a reading result can support claims or synthesis | locators, supported pages, feedback, or blockers |
| Topic Governance | Match leads to topic scope or propose a new topic | topic registry and topic pages are public-safe |
| Knowledge Objects | Maintain paper, question, concept, claim, topic, synthesis, overview, meeting, seminar pages | concise Markdown only |
| Research Graph | Export typed source/evidence/wiki/topic edges and maturity metadata | generated public-safe graph |
| Hot Query Layer | Track recent public-safe research questions and paper-search demand | single retrieval file: `hot.md` |
| L0-L3 World Context | Rebuild session context from identity, critical facts, active reading, synthesis, graph links, and validation state | terminal capsule, public-safe |
| Critical Facts | Store short public-safe facts with temporal metadata for future agents | `CRITICAL_FACTS.md` |
| Priority Evolve | Rewrite low-risk existing pages with visible AI Integration Notes and maturity-aware blockers | governed page update |
| Reconcile | Detect contradictions across same-topic pages and write AI-marked blockers when needed | page-local blockers |
| Challenge | Use existing RKF pages to argue against a target answer or synthesis | terminal critique only |
| Emerge | Detect unnamed patterns from active reading, hot queries, and topic state | low-maturity synthesis draft |
| Agent Prompts | Morning, nightly, weekly, and health operating prompts | `prompts/agents/*.md` |
| Bi-Temporal Memory | Track when RKF observed a claim and when the described fact is valid | frontmatter and critical facts |
| Propagation Review | Identify pages affected by new reading, evidence, or synthesis | manual preview/audit fallback |
| ARS Bridge | Convert ARS research/reasoning/writing/review output into RKF proposals or reading feedback | proposals only |
| Connect | Manage experimental shared RAW/wiki folders and external sandbox access boundaries | connection plans only; no private paths |

## Knowledge Flow

```mermaid
flowchart TD
    A["capture<br/>SourceRecord"] --> B["paper draft<br/>metadata or abstract is enough"]
    B --> C["fulltext status<br/>needs user PDF / PDF provided / HTML read / full text read"]
    C --> D["reading ledger<br/>questions + human feedback + blockers"]
    D --> E["claim readiness<br/>not-ready / locator-needed / claim-ready / synthesis-ready"]
    E --> F["knowledge synthesis<br/>claims, concepts, synthesis"]
    F --> M["world<br/>L0-L3 context capsule"]
    F --> N["evolve<br/>AI Integration Note"]
    N --> O["reconcile<br/>AI-marked blocker"]
    N --> Q["emerge<br/>low-maturity pattern synthesis"]
    H --> P["challenge<br/>counterpoints only"]
    G["RKF query"] --> H["retrieve governed wiki context"]
    G --> I["hot-query event<br/>public-safe demand signal"]
    H --> J["ARS reasoning"]
    J --> D
    K["lint and topic review"] --> B
    K --> E
    L["propagation review<br/>preview/audit fallback"] --> F
```

## Core Objects

- `SourceRecord`: source candidate or resolved identity plus reading-state hints.
- `EvidenceArtifact`: public-safe pointer to a private PDF, official document,
  OCR/visual artifact, screenshot, or related reading artifact.
- `ReadingLedger`: operational record of public-safe reading events, questions,
  human corrections, trust changes, and blockers.
- `KnowledgeObject`: Markdown page with type, status, review stage, topics,
  maturity fields, and evidence boundary.
- `Topic`: governed search scope with aliases, include/exclude rules, default
  search strings, canonical pages, and review cadence.
- `GateDecision`: legacy or exceptional route/review decision. Normal paper
  drafts do not wait on this object.
- `GraphEdge`: typed relation among sources, evidence, topics, and wiki pages.
- `HotQueryEvent`: public-safe query/search demand signal summarized into
  `hot.md`; it is operational memory, not evidence.

## Boundary Rules

- Paper drafts are active reading objects and may be created early.
- Search candidates are not stable claim evidence.
- ARS outputs are not evidence by themselves; they may become reading feedback
  or save/review proposals.
- Full text availability is tracked explicitly; if it is unavailable, RKF asks
  the user for a PDF or authorized text.
- Claims need a locator, supported wiki source, strong human feedback, or a
  review blocker.
- Durable full article text is not an RKF public knowledge layer.
- Public pages must not contain copied article text or private evidence paths.
- `world` is the default session bootstrap: it summarizes L0 critical facts, L1
  active reading, L2 synthesis/readiness, and L3 graph/detail links.
- `evolve` is the normal low-risk direct integration path. Every rewrite leaves
  an AI Integration Note and keeps stable claim or publication-ready content
  blocked until a locator, human feedback, supported source, or explicit blocker
  is reviewed.
- Propagation remains available as a manual preview/audit fallback.
- `reconcile` may write AI-marked blockers for contradictions; it does not
  silently resolve stable claims.
- `challenge` is adversarial retrieval over RKF's own pages. It produces
  counterpoints and downgrade suggestions, not new stable knowledge.
- `emerge` may create low-maturity synthesis drafts from existing RKF signals
  without requiring candidate records. It starts as partial/unknown coverage and
  not-ready claim readiness.
- Claim, synthesis, and critical facts use minimal temporal metadata:
  `observed_at`, `valid_from`, optional `valid_until`, and optional `supersedes`.

## Storage And Connection Strategy

RKF separates public memory from private or machine-specific artifacts:

- Git root: framework code, schemas, templates, docs, public-safe knowledge
  pages, graph exports, examples, and tests.
- Private evidence root: PDFs, authorized full text, screenshots, browser
  captures, OCR outputs, attachments, and other non-public reading artifacts.
- Reading state: `state/reading/` contains public-safe operational ledgers.
- Hot-query state: `hot.md` is the source of truth and the readable 30-day
  dashboard.

The multi-computer version is an experimental `rkf-connect` concern. The current
pattern is to keep real shared `RAW` and `wiki` folders in one Google Drive for
desktop research folder, then link those folders into each local RKF project.

## ARS Integration

ARS skills can produce research reports, paper drafts, reviews, and pipeline
outputs. RKF stores only durable wiki knowledge and public-safe reading state.
For wiki questions, RKF retrieves governed context first. ARS may reason over
that context and suggest analysis, but RKF decides whether the result should be
saved, logged as reading feedback, or treated as a blocker.
