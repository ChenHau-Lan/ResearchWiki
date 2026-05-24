# Research Wiki Core

Research Wiki Core is the interface-independent contract for this database.

It defines the evidence model, page model, agent behavior, skill behavior, and
test expectations that any interface must follow. Pipeline skills and modes are
the canonical user-facing workflow model; `ResearchWikiCodex.command` is only a
thin router and compatibility entrypoint, not the source of truth.

## Core Files

- `principles.md`: evidence chain, layer boundaries, and maintenance philosophy.
- `data_contract.md`: canonical files, DOI status, frontmatter, links, and naming.
- `agent_contract.md`: agent rules for literature, synthesis, repair, and safety.
- `test_contract.md`: required acceptance scenarios for command or UI layers.
- `skills/`: command-independent skill contracts for agent work.

## Layer Model

1. Core: rules, principles, contracts, skills, and tests.
2. Pipeline skills/modes: the official workflow surface.
3. Command: thin local router and low-token automation that implements the core
   contract.
4. Personal: user-specific research state, preferences, private evidence, and
   project history.

Branch discipline mirrors this model:

- `codex/core-*` changes core contracts.
- `codex/command-*` changes command/UI implementation.
- `personal/*` stores private user-specific state.
