# RKF v1 Architecture

## Product boundary

RKF is an evidence-governed synthesis layer above bibliography/PDF tools. It is
not a replacement for Zotero, a multi-machine database, an Obsidian product or
a generic vector-chat application.

## Canonical objects

- **Paper**: bibliographic identity, `access_state`, `review_state`.
- **Evidence**: paper ID, exact locator, summary, stance and verification.
- **Claim**: statement plus supporting/opposing/context evidence IDs and status.
- **Synthesis**: research question, claims, agreements, contradictions, gaps and
  next action.
- **Topic**: scope and saved-view rules; it does not copy papers or claims.
- **ProjectConnection**: stable ID and marker/connector metadata, without a path.
- **ActivationEvent** and **ActionEvent**: append-only operational lineage.
  Start, close, expiry, and failure are separate activation transitions; close
  never rewrites the start snapshot.

The canonical enum source is `schemas/rkf_v1.schema.json`; Python validation and
legacy mapping live in `rkf/schema.py`.

## Derived views

Review/Home, reading queue, project activity, graph, index, world context,
handoff, public demo and critical-fact summaries are projections. They are not
independent durable truth.

## Data flow

The control actions are `rkf.activate`, `rkf.status`, `connect.validate` and
`rkf.deactivate`. The five workflow actions are `workflow.add`, `workflow.ask`,
`workflow.read`, `workflow.compare-synthesize` and `workflow.review`.

```text
Connect project → explicit activation → project/activation lineage
      ↓
Add → Paper → Read → locator-backed Evidence
                     ↓
              human verification
                     ↓
Compare & Synthesize → Claim → Synthesis
      ↓
Review/Home: gaps, next actions, and origin timeline
```

## Retrieval

Exact identifier/DOI/page ID → exact title/alias → deterministic keyword →
optional semantic provider → optional graph expansion → evidence-aware ranking.
Semantic similarity never promotes evidence or claim status.

## Provider boundary

`rkf/providers.py` defines optional `FullTextProvider`, `RetrievalProvider` and
`AppraisalProvider` protocols. Adapters return typed results; they do not own
canonical objects or trust decisions. The full paper-fetch acquisition engine
is vNext work. See [the v1 provider contracts](references/v1-provider-contracts.md)
and [third-party notices](../THIRD_PARTY_NOTICES.md).

## Invariants

1. Supported/disputed/verified claims require locator-backed Evidence.
2. Verified claims require at least one human-verified Evidence card.
3. Candidate metadata and LLM output cannot satisfy stable evidence.
4. Each connected action has project and activation lineage; Review can filter
   by project, activation, action, status, or target object.
5. Retry is idempotent; raw prompt and private paths are excluded from events.
6. Public output contains no PDF/article text, secret, private path or project
   activity.
