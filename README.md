# Research Knowledge Framework (RKF)

RKF turns papers into research knowledge that can be traced to an exact source
location, checked by a person, and compared across papers.

> Paper → source context → FindingDraft → exact-locator Evidence → human-reviewed Claim → Synthesis

RKF is for researchers who want a durable, source-aware reading and synthesis
workflow in Codex. It is not a PDF library, a paywall bypass, an autonomous
claim generator, or a replacement for reading the source.

The latest published release is `v1.1.0`; this branch documents the unreleased
`v1.2` target. The earlier `v1.0.0` baseline remains documented in the
changelog; no historical tag is fabricated or moved.
Paper reading maturity remains explicit through separate access and review
states; metadata availability never implies that a paper was read.
Ask can retrieve governed wiki context, but retrieval alone never promotes a
candidate or model answer into Evidence.

## Choose your setup

Clone the public repository once:

```bash
git clone https://github.com/ChenHau-Lan/ResearchWiki.git
cd ResearchWiki
```

### A. Local core

Use this profile for the local framework and the isolated synthetic demo. It
does not install the Codex connector or its natural-language skill.

```bash
python3 tools/bootstrap_rkf.py
python3 tools/bootstrap_rkf.py --apply
python3 tools/check_install.py --profile core --strict --json
```

The first bootstrap command is a read-only preview. Review it before running
`--apply`. A successful diagnostic reports `"profile": "core"`,
`"ready": true`, and `"status": "ready"`.

### B. Codex integration

Use this profile when you want to say “activate RKF” inside Codex or connect
other research projects. Preview and apply the same connector request:

```bash
python3 tools/bootstrap_rkf.py --install-connector
python3 tools/bootstrap_rkf.py --apply --install-connector
python3 tools/check_install.py --profile codex --strict --json
python3 tools/rkf_auto_connect.py resolve
```

For the `codex` profile, a missing or stale connector/skill is a failure rather
than an optional warning. A successful diagnostic reports `"profile": "codex"`
and `"ready": true`; `resolve` then verifies that the connector can find this
checkout and its workspace configuration.

## Connect another research project

Preview the marker and lightweight bridge, then apply the exact same request:

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

This creates a v2 `.rkf-connect.toml` and a small `RKF/` bridge; it does not
copy the central wiki. Every new Codex task still starts with RKF OFF. Say
“activate RKF” at the start of the task and “deactivate RKF” when finished.

## Use RKF with natural language

After connection, open Codex with the research project folder as the workspace.
The shell commands above are setup commands; routine research work is a
conversation. For example:

- “Activate RKF and validate this project.”
- “From this conversation, extract the research question and search terms. Ask
  RKF first, then search public scholarly sources if needed. Show me candidate
  papers; after I confirm them, Add their DOI or URL and a short source-aware
  note. Do not save the whole conversation. Promotion: none.”
- “Show RKF status. List project names with open activation records, mark this
  task’s project, and include project IDs. Do not show absolute paths.”
- “Deactivate RKF.”

`rkf.status` separates this task’s mode from the path-redacted list of projects
with open activation records. It reports `active_project_count`,
`open_activation_count`, project names, stable `project_id` values, modes, and
open-task counts. An interrupted task can remain listed until its activation is
closed or expired by a later event, so this is lineage state rather than an
operating-system process monitor.

Conversation context is used to form queries and short candidate notes. Raw
transcripts, PDFs, and article text are not saved. Search results remain
candidates until selected papers are routed through Add; `Promotion: none`
still applies.

## Run the zero-network quickstart

Run the same deterministic smoke test used by CI:

```bash
python3 tools/demo_quickstart.py --check
```

It creates a temporary workspace with two clearly synthetic papers, activates
RKF, runs all five workflows, preserves the locator promotion gate, deactivates
RKF, and removes the workspace. It uses no network, global connector, PDF, or
user research data. Success includes:

```json
{
  "quickstart": "passed",
  "workflows_completed": 5,
  "promotion_boundary_preserved": true
}
```

## The five workflows

After Codex integration is ready and a project is activated, use requests like
these with your own real source identifiers. These are templates, not a claim
that RKF has read a source you have not supplied.

| Workflow | Natural-language request | Expected result |
|---|---|---|
| **Add** | “From this conversation, Add the DOI or URL I selected as a candidate with a short search-context note. Do not save the transcript or promote it to Evidence.” | A deduplicated capture receipt with `Promotion: none` and project/activation lineage. |
| **Ask** | “Ask RKF what these sources report, and separate source context from locator-backed support.” | Useful governed context may be shown without a locator, but it is marked not claim-ready; formal support links exact Evidence. |
| **Read** | “Capture this observation as a FindingDraft; I will add the exact locator later.” | A missing/coarse/exact FindingDraft. Only an exact finding can be promoted to the existing Evidence format; the direct exact-locator Evidence route remains available. |
| **Compare & Synthesize** | “Compare these Evidence cards and list agreement, contradiction, gaps, and a provisional conclusion.” | An Evidence-linked Claim or Synthesis that preserves unresolved gaps. |
| **Review** | “Review this project: show missing locators, pending verification, disputed claims, and the next reading action.” | An actionable review plus the path-redacted activation timeline. |

The five workflows are the complete v1 research surface. Internal helpers and
compatibility code do not create additional product modes.

## Safety boundary

- Candidate metadata and model output are not stable evidence.
- Missing/coarse FindingDrafts are research notes, not Evidence or claim support.
- A verified claim requires locator-backed, human-verified Evidence.
- PDFs, article text, secrets, tokens, absolute paths, private indexes, and raw
  prompts do not enter the public repository or public output.
- RKF does not bypass paywalls, CAPTCHA, or access controls.

## vNext acquisition development

GitHub issue #18 now has an opt-in **portable-core slice** for scientific-
artifact acquisition: multi-identifier resolution, bounded OA/official and
authorized-repository routes, artifact/version provenance, PDF QC, private
storage, and acquisition lineage. It remains an internal Add provider, not a
sixth workflow, and is off by default in the connector. Browser, institutional,
and publisher-specific adapters are not complete; access controls and
SSO/CAPTCHA surfaces are detected and stopped as typed manual handoffs, never
bypassed.

A reproducible atmospheric-journal corpus contains 11 P0 and 3 P1
representative cases. In the bounded 2026-07-16 live observation, all 14
artifacts were obtained and met the helper's research-ready PDF checks, using
publisher, current NCBI PMC Cloud, and authorized repository routes. This is
observational evidence for those exact cases and time, not proof that every
article from those journals is retrievable. The helper requires its reports
and checksum-addressed artifacts to stay outside the repository, and every
result retains `Promotion: none`.

See the [vNext acquisition reference](docs/references/vnext-acquisition.md),
the [14-case journal corpus](docs/benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json),
the [14-case live result](docs/benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md),
the [journal-family route playbook](docs/operations/atmospheric-journal-acquisition-route-playbook.zh-TW.md),
the [public-safe implementation and conversation summary](docs/operations/2026-07-16-issue-18-atmospheric-journal-closeout.zh-TW.md),
and the broader historical
[79-citation atmospheric baseline](docs/benchmarks/acquisition-issue-18-atmospheric-smoke.md).
The compact Traditional Chinese capability entry is in
[FEATURES_AND_COMMANDS.zh-TW.md](docs/FEATURES_AND_COMMANDS.zh-TW.md).

Use [Getting Started](docs/GETTING_STARTED.md) as the current beginner guide.
For detailed daily use, see the [Researcher manual](docs/manuals/rkf_manual.en.md).
For architecture, compatibility/removal decisions, release operations, and the
public synthetic demo, use the single
[Maintainer reference](docs/MAINTAINER_REFERENCE.md).

[繁體中文](README.zh-TW.md) · License: MIT
