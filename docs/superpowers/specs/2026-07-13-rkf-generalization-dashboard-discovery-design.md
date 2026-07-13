# RKF Generalization, Public Dashboard, And Paper Discovery Design

Date: 2026-07-13

## Goal

Make RKF easier to install and connect to research projects, add an inspectable
web dashboard, and add topic-driven paper discovery without weakening RKF's
evidence and publication boundaries.

## Constraints

- The Codex app and `rkf.actions` remain the user-facing runtime. Setup tools
  may exist for cloning, local initialization, diagnostics, and publication
  preparation.
- `rkf.workspace.toml` remains the storage-routing authority. Relative paths
  resolve from the repository root so a clean clone can use a portable local
  profile.
- A project-local `RKF/` folder is an operational bridge, not a second wiki or
  an evidence store.
- Discovery candidates are metadata-only operational records. They are not
  SourceRecords, paper pages, full-text evidence, or stable claims.
- `public_safe` means content passed RKF's safety checks; it does not mean the
  user approved Internet publication.
- No workflow downloads paywalled or institution-only full text, bypasses
  access controls, or stores article text in the public knowledge layer.
- Pages deployment, recurring automation activation, and remote pushes remain
  separate user-approved operations.

## Architecture

```text
clean GitHub clone
  -> local bootstrap and install diagnostic
  -> rkf.workspace.toml + local single-writer registry
  -> optional cross-project v2 marker + RKF/ bridge

topic registry / explicit research question / paper-radar metadata
  -> discover.preview
  -> provider normalization + DOI/title dedupe + conservative ranking
  -> exact preview hash
  -> discover.record (approved candidate-only search run)
  -> discover.accept (selected candidates only)
  -> immutable capture event
  -> inbox + SourceRecord
  -> optional paper draft
  -> reading/full-text/locator/human-review gates

live RKF aggregates
  -> dashboard.preview
  -> strict allowlist and private preview directory
  -> exact snapshot hash + human publication approval
  -> dashboard.publish
  -> site/data/rkf-public-snapshot.json
  -> static GitHub Pages site
```

## Project Linking And Onboarding

The repository provides:

1. A local single-machine example using relative paths.
2. A read-only install diagnostic that never prints storage paths, tokens, or
   machine identifiers.
3. One preview-first `connect-project` setup path that can create the v2 marker
   and missing bridge files without overwriting existing bridge notes.
4. Beginner documentation that separates local single-machine setup from
   experimental shared-Drive setup.

The v2 marker means RKF is available. It never persists an ACTIVE session.

## Public Dashboard Contract

The public snapshot is aggregate-only. Its allowlist includes:

- topic ID, public topic name, and 30-day demand count;
- counts and distributions for candidate intake, paper queue, reading state,
  full-text state, claim readiness, and knowledge object type;
- machine-neutral gate values, schema version, review cadence, and whether a
  storage handle is configured;
- graph node/edge counts and lint/connection-health counts;
- generation time, freshness, publication status, and snapshot hash.

It excludes:

- raw hot questions, notes, paper leads, paper titles, DOI/source/event IDs,
  reading-ledger entries, critical facts, full graph contents, and paths;
- machine ID, writer registry content, private Drive roots, secrets, email
  addresses, tokens, PDFs, abstracts, OCR, and article text.

`dashboard.preview` may write only under local `.rkf_private`. Publication must
name the exact preview hash. The committed site starts with a clearly labelled
synthetic snapshot until an exact live aggregate is approved.

## Discovery Contract

Supported MVP inputs are:

- Crossref metadata search;
- arXiv Atom search;
- optional OpenAlex search when `OPENALEX_API_KEY` is present;
- allowlisted metadata records exported by `drpwchen/paper-radar`.

Provider failures are isolated and reported. A partial provider failure never
deletes earlier runs or upgrades the remaining candidates. Persisted candidate
fields are limited to bibliographic identity, provenance, public URL, ranking
explanation, topic, and boundary fields. Abstracts and private availability
pointers are discarded before persistence.

Actions:

- `discover.preview`: fetch and normalize without writing RKF state.
- `discover.record`: persist the exact approved preview under
  `state/search_runs/`; designated writer only.
- `discover.accept`: route selected candidate IDs through immutable capture;
  paper-page creation defaults off.
- `discover.status`: aggregate run health without exposing candidate identity.

No recurring scheduler is activated by this implementation. The actions are
schedule-ready, but creation and activation of an automation require separate
approval.

## Static Site

The site is dependency-free HTML, CSS, and JavaScript. It works at both a local
root and a GitHub project-site base path by using relative URLs. It renders:

- RKF overview and freshness;
- research-hotspot aggregates;
- discovery-to-evidence pipeline;
- reading and claim-readiness distributions;
- redacted framework settings and health;
- beginner project-link and first-session instructions;
- a visible statement that demand/candidates are not evidence.

## Acceptance Criteria

- A clean-clone local profile resolves relative paths from the checkout root.
- Install diagnostics report pass/warn/fail without exposing private values.
- Project connection preview is non-mutating; apply preserves existing bridge
  files.
- Discovery preview is non-mutating, deterministic for fixtures, deduplicates
  providers, strips abstracts/private pointers, and retains candidate-only
  boundaries.
- Recording requires activation, a healthy doctor, a designated writer, and an
  exact preview hash.
- Accepting selected candidates writes capture events and inbox/SourceRecords;
  it creates paper drafts only when explicitly requested.
- Dashboard preview is aggregate-only and path-redacted. Publishing rejects a
  mismatched hash or unsafe content.
- The static site renders with a synthetic snapshot without external assets or
  dependencies.
- Focused tests, full unit tests, Python compilation, public-safety scan, and
  `git diff --check` pass before handoff.

## Out Of Scope

- Turning RKF into a generic RAG/vector-chat application.
- Publishing the live private wiki or full `hot.md`.
- Uploading PDFs, abstracts, reading notes, personal preference weights, or
  paper-radar D1/R2 state.
- Enabling GitHub Pages, pushing a branch, or activating a recurring paper
  discovery automation without separate confirmation.
