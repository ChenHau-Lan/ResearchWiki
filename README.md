# Research Knowledge Framework (RKF)

RKF turns papers into research knowledge that can be traced back to an exact
source location, compared as supporting or opposing evidence, and explicitly
human-reviewed.

Ask is used to retrieve governed wiki context; optional ARS reasoning may work
over that context, while RKF keeps promotion and evidence decisions explicit.

> Paper → locator-backed Evidence → human-reviewed Claim → Synthesis

The current compatible release target is `v1.1.0`; the published `v1.0.0` tag
is not rewritten.
Paper reading maturity remains explicit through canonical access and review
states.

## What researchers do

1. **Add** a DOI, URL, PDF pointer, Zotero item, note or selected paper.
2. **Ask** within papers or topics. Evidence-backed answers must expose a
   locator; otherwise RKF reports insufficient evidence.
3. **Read** by recording annotations, corrections, Evidence and verification.
4. **Compare & Synthesize** agreements, contradictions and evidence gaps.
5. **Review** the next research actions and the activity of connected projects.

## Use RKF from another project

Preview and apply `connect-project` to create a v2 `.rkf-connect.toml` and a
small `RKF/` bridge. The bridge does not copy the wiki. Every Codex task still
starts with RKF OFF; say “activate RKF” before using it.

Each marker receives a random stable `project_id`. Every activation receives an
`activation_id`, and every action records a path-redacted, append-only event.
Review can reconstruct which project and activation queried or changed an
object. Raw prompts are not stored by default.

## Core action surface

```text
rkf.activate / rkf.status / rkf.deactivate / connect.validate
workflow.add
workflow.ask
workflow.read
workflow.compare-synthesize
workflow.review
```

Python modules and the legacy CLI are internal compatibility surfaces, not the
beginner interface.

## Optional providers

RKF v1 defines small contracts for full-text acquisition, appraisal and
semantic retrieval. The deterministic core works without them. `paper-fetch`,
`paper-review-and-digest` and `vault-search` are integration references; their
heavy runtimes, browser login flows and separate UIs are not core dependencies.
The full scientific artifact acquisition engine is deferred to vNext.

## Safety boundaries

- Candidates, metadata and LLM output are not stable evidence.
- Verified claims require locator-backed, human-verified Evidence.
- PDFs, article text, secrets, private paths and raw prompts are not published.
- RKF does not bypass paywalls, CAPTCHA or access controls.
- A provider obtaining a PDF does not mean it is readable, reviewed or
  supportive of a claim.

## Start here

- [Traditional Chinese guide](README.zh-TW.md)
- [Getting started](docs/GETTING_STARTED.md)
- [Architecture](docs/ARCHITECTURE.md)
- [v1 scope inventory](docs/V1_SCOPE_INVENTORY.md)
- [Workflow registry](MODE_REGISTRY.md)
- [Public guided demo](https://chenhau-lan.github.io/ResearchWiki/)

## Validation

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/public_safety_scan.py
```

License: MIT. See `docs/references/third_party_sources.md` before copying code
from an upstream integration reference.

## Version Management

`v1.0.0` remains immutable. This compatible schema and workflow update targets
`v1.1.0`.
