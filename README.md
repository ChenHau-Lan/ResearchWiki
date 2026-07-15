# Research Knowledge Framework (RKF)

RKF turns papers into research knowledge that can be traced to an exact source
location, checked by a person, and compared across papers.

> Paper → locator-backed Evidence → human-reviewed Claim → Synthesis

RKF is for researchers who want a durable, source-aware reading and synthesis
workflow in Codex. It is not a PDF library, a paywall bypass, an autonomous
claim generator, or a replacement for reading the source.

The current compatible release is `v1.1.0`. The earlier `v1.0.0` baseline
remains documented in the changelog; no historical tag is fabricated or moved.
Paper reading maturity remains explicit through separate access and review
states; metadata availability never implies that a paper was read.
Ask can retrieve governed wiki context, but retrieval alone never promotes a
candidate or model answer into Evidence.

## Install the central RKF checkout

```bash
git clone git@github.com:ChenHau-Lan/ResearchWiki.git
cd ResearchWiki
python3 tools/bootstrap_rkf.py
python3 tools/bootstrap_rkf.py --apply
python3 tools/check_install.py --strict
```

The first bootstrap command is a read-only preview. Review it before running
`--apply`. The strict check must finish with `ready: true` before connecting a
research project.

## Connect another research project

Preview the marker and lightweight bridge, then apply the exact same request:

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

This creates a v2 `.rkf-connect.toml` and a small `RKF/` bridge; it does not
copy the central wiki. Every new Codex task still starts with RKF OFF. Say
“activate RKF” at the start of the task and “deactivate RKF” when finished.

## Complete the first loop in 10 minutes

Use one public or synthetic paper for this walkthrough. In Codex, send these
requests in order:

| Workflow | Natural-language request | Expected result |
|---|---|---|
| **Add** | “Activate RKF, then Add DOI `10.0000/example` as a candidate. Do not promote it to evidence.” | A deduplicated capture receipt with `Promotion: none` and project/activation lineage. |
| **Ask** | “Ask RKF what this paper reports about the target relationship. If there is no locator, say that evidence is insufficient.” | Source-bounded results; a claim-supporting answer includes an exact locator or an insufficient-evidence result. |
| **Read** | “Read the paper and record the result at p. 8, Fig. 3 as supporting Evidence; keep it unreviewed.” | An Evidence card with paper ID, locator, stance, and explicit verification state. |
| **Compare & Synthesize** | “Compare this Evidence with another reviewed paper and list agreement, contradiction, gaps, and a provisional conclusion.” | A Claim or Synthesis that links Evidence IDs and preserves unresolved gaps. |
| **Review** | “Review this project: show missing locators, pending verification, disputed claims, and the next reading action.” | An actionable review plus the path-redacted activation timeline. |

The five workflows are the complete v1 research surface. Internal helpers and
compatibility code do not create additional product modes.

## Safety boundary

- Candidate metadata and model output are not stable evidence.
- A verified claim requires locator-backed, human-verified Evidence.
- PDFs, article text, secrets, tokens, absolute paths, private indexes, and raw
  prompts do not enter the public repository or public output.
- RKF does not bypass paywalls, CAPTCHA, or access controls.

For architecture, compatibility/removal decisions, release operations, and
the public synthetic demo, use the single [Maintainer reference](docs/MAINTAINER_REFERENCE.md).

[繁體中文](README.zh-TW.md) · License: MIT
