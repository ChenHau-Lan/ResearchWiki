# RKF Auto-Connect Design

Date: 2026-07-01

## Goal

Make RKF usable across projects without requiring the user to explicitly name it
for every research search, web clip, DOI, or valuable research discussion.
When a project is connected to RKF, agents should automatically route
research-relevant material back to the current RKF database while preserving
evidence boundaries.

## User-Approved Direction

Use an Active/Aggressive hybrid policy:

- Active by default for source-like material: DOI, URL, paper leads, citation
  strings, literature searches, important web pages, and reusable source clips.
- Aggressive when the conversation is clearly research work: literature
  synthesis, method discussion, experiment design, data interpretation,
  manuscript/proposal reasoning, claim comparison, or reusable ideas.
- Conservative at the promotion boundary: auto-capture is allowed, but stable
  claim or trusted synthesis promotion still needs locators, supported RKF
  pages, or annotated/trusted human feedback.

## Scope

In scope:

- Define a global `rkf-auto-connect` personal skill/protocol.
- Define how non-RKF projects discover and connect to the RKF database.
- Define automatic capture triggers and write targets.
- Define safety gates for private data, local paths, full transcripts, and
  unsupported claim promotion.
- Define documentation and validation needed before implementation.

Out of scope for the first implementation:

- Browser extension, clipboard monitor, or background daemon.
- Automatic capture of whole ChatGPT histories or entire web articles.
- Direct automatic promotion to claim or synthesis pages.
- Rewriting every existing project `AGENTS.md`.
- Changing the RKF storage contract beyond using existing `rkf.workspace.toml`
  and current CLI commands.

## Architecture

The design has three layers.

### 1. Global Connector Skill

Create a reusable personal skill named `rkf-auto-connect`.

The skill is available from any Codex project. Its job is not to own RKF logic;
it is a routing layer that:

- resolves the ResearchWiki repo from a small global config;
- reads the RKF workspace config from that repo;
- knows the Active/Aggressive capture policy;
- decides whether a current task should be captured;
- calls the RKF CLI for capture, hot-query recording, and guarded DOI injection.

The skill should be lightweight and policy-focused. RKF remains the source of
truth for schemas, page templates, evidence gates, and CLI behavior.

### 2. Connection State

A project becomes RKF-connected when the user says a phrase such as:

```text
連結我的 RKF 資料庫
connect my RKF database
use my RKF database in this project
```

The first version should support two connection scopes:

- Session scope: the current agent remembers the connection during the active
  thread.
- Project scope: the project can store a small public-safe marker in its own
  docs or project memory saying that RKF auto-connect is enabled for research
  work.

The marker must not store private Drive paths. It should reference the global
connector and say that RKF paths are resolved through local config.

### 3. RKF Write Targets

The connector writes through existing RKF pathways:

- Search demand and repeated research questions go to `hot.md`.
- ChatGPT/web/project clips go to `knowledge/inbox/`.
- DOI or URL source identity creates or updates `SourceRecord`.
- DOI-related paper material uses guarded paper backlink injection.
- Reading questions, corrections, or trust updates can become reading-ledger
  events when a target source is clear.

The connector does not write stable claims directly.

## Trigger Policy

### Active Triggers

Auto-capture when any of these appear in the task or search result:

- DOI, arXiv ID, PubMed ID, ISBN, dataset DOI, or formal citation.
- Paper title, author-year reference, journal/conference name, or literature
  search query.
- Important source URL that the user or agent uses as evidence.
- Web clip that the agent summarizes, quotes briefly, or plans to reuse.
- Repeated research question suitable for `hot.md`.

Default target:

- DOI/source URL: `rk inbox capture` with guarded DOI/source injection.
- Search query or repeated demand: `rk hot record`.
- Source-backed excerpt: `rk inbox capture`.

### Aggressive Research Triggers

Auto-capture even without DOI/URL when the interaction is a valuable research
discussion, such as:

- literature synthesis or comparison;
- method design or model/experiment planning;
- manuscript or proposal argument structure;
- research claim evaluation;
- interpretation of figures, datasets, diagnostics, or equations;
- reusable idea, hypothesis, caveat, or open question.

Default target:

- `knowledge/inbox/` with origin identifying the host project or conversation.
- If it is mainly a question or recurring demand, also `hot.md`.

### Do Not Auto-Capture

Do not auto-write to RKF when the material is:

- ordinary coding/debugging without research value;
- secrets, keys, tokens, credentials, private paths, or sensitive personal data;
- full article text, whole ChatGPT transcripts, whole browser captures, or PDFs;
- copyrighted text beyond short excerpts;
- transient task chatter with no future research value;
- prohibited by the active project `AGENTS.md` or user instruction.

When blocked, the agent may produce a pending capture proposal instead of
writing.

## Capture Payload Shape

Every automatic capture should preserve provenance and separation:

- origin project or session;
- title;
- source URL or DOI when available;
- short public-safe clip or source-grounded summary;
- reader note for the user's idea or project relation;
- AI/agent note for inference and human-check needs;
- promotion target suggestion;
- explicit boundary saying the item is not claim evidence.

For ChatGPT web conversations, store selected excerpts or summaries plus an
optional shared-link URL. Do not store entire private transcripts.

## Data Flow

1. User connects a project to RKF.
2. Agent resolves the ResearchWiki checkout from global config.
3. Agent reads RKF project memory and `rkf.workspace.toml`.
4. During searches or research discussion, agent runs the trigger policy.
5. If capture is warranted, agent builds a short public-safe payload.
6. Agent calls the RKF CLI:
   - `python3 tools/rk.py inbox capture ...`
   - `python3 tools/rk.py hot record ...`
7. RKF writes to the configured live `wiki_root`.
8. Agent reports what was captured and what remained unpromoted.

## Error Handling

- If the ResearchWiki path cannot be resolved, stop and ask for setup.
- If `rkf.workspace.toml` is missing or invalid, stop and report the missing
  config.
- If the target project forbids external writes, create a capture proposal
  instead of writing.
- If a capture contains private paths or is too long, summarize to a short
  public-safe payload or ask the user to choose what to preserve.
- If the RKF CLI fails, show the failed command and leave no hidden success
  claim.
- If DOI parsing is uncertain, write to inbox without DOI injection.

## User Experience

The user's desired workflow should feel like:

```text
User: 連結我的 RKF 資料庫
Agent: 已連結。之後研究相關搜尋、DOI、網頁來源與有價值研究討論會自動回饋到 RKF inbox/hot.md。
```

Then, later in the same or another connected project:

```text
User: 幫我找 aerosol-cloud interaction 最近的 parameterization papers
Agent: ...searches and summarizes...
Agent: 已自動記錄到 RKF: hot-query + 3 DOI inbox items; no claims promoted.
```

For valuable discussions:

```text
User: 我覺得這個方法可以用在 WRF microphysics calibration...
Agent: ...responds...
Agent: 已將這段研究想法保存到 RKF inbox，標為 Reader Notes，不作為 evidence。
```

## Testing Strategy

Implementation should include tests for:

- connector config resolution without storing private paths in committed docs;
- trigger classification for Active, Aggressive, and do-not-capture cases;
- command generation for `inbox capture` and `hot record`;
- refusal or proposal behavior for private paths, long transcripts, and full
  article text;
- DOI capture path with guarded injection;
- project-scope marker behavior that does not overwrite existing project
  memory.

RKF repo verification should keep using:

```bash
python3 -m py_compile tools/rk.py rkf/*.py tools/public_safety_scan.py
python3 -m unittest discover -s tests
python3 tools/rk.py lint
python3 tools/rk.py topic lint
python3 tools/public_safety_scan.py
```

## Documentation Updates

Document:

- how to say "connect my RKF database" in a project;
- what gets automatically captured;
- what is never captured;
- how to inspect recent auto-captures;
- how to disable auto-connect for a project or session;
- how ChatGPT web snippets should be captured safely.

Likely files:

- `docs/workflows/rkf-auto-connect.zh-TW.md`
- `docs/FEATURES_AND_COMMANDS.zh-TW.md`
- `docs/PROJECT_MEMORY.md`
- global skill docs for `rkf-auto-connect`

## Locked Implementation Decisions

The first implementation should use these choices:

- Global config lives at `~/.codex/rkf_connector.toml`.
- Project-scope markers live in `.rkf-connect.toml` at the connected project
  root. The marker stores only public-safe policy state such as
  `enabled = true` and `mode = "active-aggressive"`, not private paths.
- Project memory may mention RKF auto-connect only when the user asks for a
  durable project note or the project already maintains `docs/PROJECT_MEMORY.md`.
- The first version creates the actual global personal skill immediately and
  updates RKF repo-side docs. It does not add a daemon, browser extension, or
  clipboard monitor.
- The global skill resolves RKF from the global config, then uses RKF's existing
  CLI commands. It does not duplicate RKF schemas or page templates.

## Spec Self-Review

- No placeholder requirements remain.
- The design keeps RKF storage authority inside the existing RKF CLI and
  `rkf.workspace.toml`.
- The Active/Aggressive policy is explicit and includes negative triggers.
- Stable claim promotion remains blocked unless normal RKF evidence boundaries
  are satisfied.
- The first implementation remains small enough for one implementation plan.
