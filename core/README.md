# Research Wiki Core

Research Wiki Core is the command-independent contract for this database.

It defines the evidence model, page model, agent behavior, skill behavior, and
test expectations that any interface must follow. `ResearchWiki.command` is one
implementation of this core contract, not the source of truth.

## Core Files

- `principles.md`: evidence chain, layer boundaries, and maintenance philosophy.
- `data_contract.md`: canonical files, DOI status, frontmatter, links, and naming.
- `agent_contract.md`: agent rules for literature, synthesis, repair, and safety.
- `test_contract.md`: required acceptance scenarios for command or UI layers.
- `skills/`: command-independent skill contracts for agent work.

## Layer Model

1. Core: rules, principles, contracts, skills, and tests.
2. Command: local UI and automation that implements the core contract.
3. Personal: user-specific research state, preferences, private evidence, and
   project history.

Branch discipline mirrors this model:

- `codex/core-*` changes core contracts.
- `codex/command-*` changes command/UI implementation.
- `personal/*` stores private user-specific state.
