# Research Knowledge Framework Manual

RKF is an LLM Wiki-based research knowledge framework. Its job is to preserve
durable, source-aware academic knowledge while letting paper understanding grow
actively across sessions.

The current model is reading maturity first, claim boundary second. A paper can
enter the wiki early as a draft from metadata, an abstract, partial full text,
or a user-provided PDF. The draft must state what has actually been read. Stable
claims, trusted synthesis, citation confidence, and publication still require a
locator, human feedback, an existing governed RKF source, or an explicit review
blocker.

RKF works beside `academic-research-skills`: ARS can search, reason, write, and
review; RKF decides what becomes durable wiki memory and what remains a reading
draft or proposal.

## Mental Model

| Layer | Purpose | Boundary |
|---|---|---|
| Source record | Register DOI, URL, PDF pointer, topic seed, idea, or question | Source identity and topic fit |
| Paper draft | Preserve current understanding of one paper | Reading state, full-text status, feedback level, claim readiness |
| Reading ledger | Keep public-safe interaction history | Operational memory, not evidence by itself |
| Claim | Preserve a supported or reviewable statement | Locator, human feedback, existing page, or blocker |
| Synthesis | Preserve cross-source judgment | Source coverage, maturity, feedback, claim readiness |
| Topic | Control discovery scope and drift | Scope, aliases, include/exclude, default searches |

## Paper Maturity

Paper frontmatter should record:

```yaml
reading_state: metadata-only | abstract-read | partial-fulltext | fulltext-available | fulltext-read | human-reviewed | synthesis-ready | blocked
fulltext_status: unknown | needs-user-pdf | user-pdf-provided | publisher-html | publisher-pdf | open-access-pdf | partial-only | fulltext-read | unavailable | blocked
human_feedback_level: none | skimmed | discussed | annotated | trusted
understanding_confidence: low | medium | high | mixed
claim_readiness: not-ready | locator-needed | claim-ready | synthesis-ready
last_reading_interaction: YYYY-MM-DD
reading_ledger: state/reading/<source_id>.json
```

Use conservative values when the system knows little. A metadata-only draft is
useful because it makes the next reading action visible.

## Synthesis Maturity

Synthesis frontmatter should record:

```yaml
synthesis_maturity: draft | single-source | multi-source | human-reviewed | publication-ready
source_coverage: unknown | partial | representative | systematic
human_feedback_level: none | skimmed | discussed | annotated | trusted
claim_readiness: not-ready | locator-needed | claim-ready | synthesis-ready
last_synthesis_interaction: YYYY-MM-DD
observed_at: YYYY-MM-DD
valid_from: YYYY-MM-DD
valid_until: optional
supersedes: optional
```

Synthesis can remain draft-quality while it collects questions and source gaps.
It becomes trusted only when coverage, feedback, and claim readiness are clear.

## Common Workflows

### Register a paper and create an early draft

```bash
python3 tools/rk.py capture doi "10.1234/example" --title "Example Paper" --topic-id "topic-id"
python3 tools/rk.py distill paper doi_10_1234_example
```

If no full text is available, the draft should show `fulltext_status:
needs-user-pdf` and the paper should appear in the queue.

### Ask the user for a PDF only when needed

```bash
python3 tools/rk.py acquire doi_10_1234_example
```

This marks the source as needing a user PDF. It does not create a new required
checkpoint. Older checkpoint files remain valid for legacy records.

### Record a user-provided PDF

```bash
python3 tools/rk.py acquire doi_10_1234_example --pdf "/private/path/to/paper.pdf"
```

The PDF remains in private evidence storage. The public wiki records only safe
metadata, reading state, and locator notes.

### Check locators and upgrade readiness

```bash
python3 tools/rk.py verify-pdf doi_10_1234_example --locator "p. 3 Fig. 2; p. 8 Section 4" --note "Identity and key locators checked."
```

Use this when a PDF, publisher HTML page, or visual artifact has been checked
enough to support claims. For scanned or image-only papers, record visual
locators, OCR confidence, and human reading notes.

### Record feedback

```bash
python3 tools/rk.py paper feedback doi_10_1234_example --level discussed --note "User corrected the interpretation of the method section."
```

Feedback updates the paper frontmatter and appends a public-safe event to
`state/reading/`. The ledger helps RKF know which papers are trusted by the
user, but a ledger entry alone is not claim evidence.

### Use the active paper queue

```bash
python3 tools/rk.py paper status
python3 tools/rk.py paper queue
python3 tools/rk.py paper next
python3 tools/rk.py paper nudge --limit 5
```

The queue should prioritize papers that are metadata-only, need a user PDF,
lack human feedback, have repeated questions, or are ready for synthesis review.

### Start a session with world context

```bash
python3 tools/rk.py world --log-tail 10
```

`world` returns the L0-L3 context capsule: critical facts, active reading,
claim readiness, contradiction hints, graph links, and validation state.

### Evolve an existing page

```bash
python3 tools/rk.py evolve knowledge/concepts/example.md --note "Add retrieval brief after reading review." --source "daily-agent"
```

Low-risk updates may rewrite existing pages when they leave an AI Integration
Note. High-risk stable claim promotion, source identity conflicts,
publication-ready synthesis, and delete/merge choices should be written as
blockers or maturity downgrades.

### Reconcile contradictions and challenge a synthesis

```bash
python3 tools/rk.py reconcile --topic-id aerosol-cloud
python3 tools/rk.py reconcile --dry-run
python3 tools/rk.py challenge knowledge/synthesis/example.md --limit 5
```

`reconcile` marks contradictions as AI-integrated blockers. `challenge` returns
counterpoints and downgrade suggestions only; it does not create stable claims.

### Discover unnamed patterns

```bash
python3 tools/rk.py emerge --limit 8
python3 tools/rk.py emerge --write --topic-id aerosol-cloud
python3 tools/rk.py synthesize auto --write --limit 8
```

Auto-synthesis uses existing RKF reading, hot-query, feedback, and topic state.
It does not require candidate records and starts as low maturity.

## Skill Routing

| Task | Skill | Mode |
|---|---|---|
| Capture DOI/URL/PDF lead | `rkf-evidence-vault` | `capture` |
| Find candidate papers | `rkf-evidence-vault` | `discover` |
| Record missing or user-provided full text | `rkf-evidence-vault` | `acquire` |
| Check locators/readability | `rkf-evidence-vault` | `verify-pdf` |
| Create/update paper draft | `rkf-knowledge-synthesis` | `distill-paper` |
| Save question/concept/claim/synthesis | `rkf-knowledge-synthesis` | `save-*` / `synthesize` |
| Find unnamed patterns | `rkf-knowledge-synthesis` | `emerge` / `synthesize auto` |
| Query wiki and record hot demand | `rkf-wiki-core` | `query` / `hot-query` |
| Evolve or challenge existing pages | `rkf-wiki-core` | `evolve` / `challenge` |
| Track paper queue and feedback | `rkf-wiki-core` | `paper-*` |
| Run maintenance checks or reconcile contradictions | `rkf-lint` | `structure`, `evidence`, `graph`, `ARS`, `public-safety`, `reconcile` |
| Connect external sandboxes | `rkf-connect` | `sandbox-*` |

## Save Rules

- A query answer is not a wiki page until explicitly saved.
- A paper draft reports one source; cross-source judgment belongs in synthesis.
- A candidate is not evidence, but it can start a reading draft.
- ARS output is a proposal unless RKF review promotes it.
- `emerge` does not require candidate records and starts as draft synthesis.
- Every AI rewrite needs an AI Integration Note.
- Stable AI-integrated claim/synthesis content needs `observed_at` and
  `valid_from`.
- Stable claims require locator support, human feedback, an existing RKF source,
  or an explicit blocker.
- Durable article text, PDFs, browser captures, private Drive paths, and local
  secrets must not be committed.

## External Sandboxes

External sandboxes should read the generated context capsule:

```bash
python3 tools/rk.py prompt external-sandbox
```

Trusted sandboxes with write access may use the CLI, but they must preserve the
same maturity and claim boundaries. If a sandbox only has search results,
unclear topic fit, missing full text, low reading maturity, or insufficient
locators, it should return a proposal instead of editing stable claims.

Trusted sandboxes may return `evolve`, `reconcile`, or `emerge` updates when the
changes remain AI-marked and maturity-aware. They should not implement open-web
or multimodal ingestion pipelines inside RKF; use ARS for external research.

## Validation

Before publishing or opening a PR, run:

```bash
python3 -B -m py_compile tools/rk.py rkf/cli.py rkf/core.py rkf/__init__.py tools/public_safety_scan.py
python3 -B -m unittest discover -s tests
python3 tools/rk.py topic lint
python3 tools/rk.py lint
python3 tools/rk.py lint --mode graph-lint
python3 tools/rk.py lint --mode ars-handoff-lint
python3 tools/rk.py lint --mode public-safety-lint
python3 tools/public_safety_scan.py
```
