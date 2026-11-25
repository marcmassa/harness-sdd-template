# Harness SDD — Sub-Agent System

Specialized sub-agents that work on project features following the SDD process.

## Agent Architecture

```
                      ┌──────────────────────┐
                      │      HARNESS         │
                      │   (orchestrator)     │
                      └────────┬─────────────┘
                               │
               ┌────────────────┼────────────────┐
               │                │                │
               ▼                ▼                ▼
     ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
     │  SPEC_AUTHOR   │ │  IMPLEMENTER   │ │  REVIEWER      │
     │  (quality)     │ │  (orchestrator)│ │  (quality)     │
     └────────────────┘ └────────────────┘ └────────────────┘
```

## Sub-agents

Each sub-agent is defined in `.agents/subagents/<name>/SUBAGENT.md` with a dual
frontmatter (CLI-agnostic fields + opencode-compatible fields). Sub-agents can
extend their capabilities through **skills** stored in `.agents/skills/`.

| Agent | SUBAGENT.md | Responsibility |
|--------|-------------|----------------|
| `architect-qa` | `.agents/subagents/architect-qa/SUBAGENT.md` | Default. Routes work, writes the spec, runs the closing review. Never implements. |
| `implementer` | `.agents/subagents/implementer/SUBAGENT.md` | Default. Executes `tasks.md` on the active feature. One per language with `--implementer`. |
| `harness`, `spec-author`, `reviewer` | `.agents/subagents/<name>/SUBAGENT.md` | Optional (`init --apply --add`): split routing, spec writing, or review out of `architect-qa`. |
| `agent-template` | `.agents/subagents/agent-template/SUBAGENT.md` | **Example template** — copy to create new sub-agents. |

*To add a new sub-agent, copy `.agents/subagents/agent-template/`, rename the folder and edit the SUBAGENT.md.*

## Routing

See `ROUTING.md` for the full decision tree.
See `workflows.md` for predefined workflows.
See `CONVENTION.md` for the mandatory usage convention.
