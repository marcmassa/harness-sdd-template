# Requirements — native-plugin-adapters

> Feature FEAT-008 from `feature_list.json`. Gives the four CLIs the user asked for (Claude Code, Codex, Cursor, OpenCode) deterministic in-repo integration: new adapters for Cursor and Codex, hook bridging to `hooks/run-hooks.sh`, and per-path cleanup that never deletes user files.
>
> Each requirement is written in strict EARS and is verifiable by at least one specific test.

## EARS Patterns

| Pattern | Syntax | When to use |
|--------|----------|---------------|
| **Ubiquitous** | `SHALL ...` | Always true, permanent condition |
| **Event** | `WHEN <event> SHALL ...` | Triggered by a specific event |
| **State** | `WHILE <state> SHALL ...` | While a condition remains true |
| **Optional** | `WHERE <option> SHALL ...` | Behavior varies based on configuration |
| **Unwanted** | `IF <condition> THEN SHALL ...` | Response to failures or edge cases |

## Context

Scope confirmed with the human (2026-10-22): in-repo adapters, no distributable packaging; SDD lifecycle hooks bridge to `hooks/run-hooks.sh` from whatever native mechanism each CLI has. Claude Code and OpenCode already have adapters (`CLAUDE.md`+`.claude/`, `opencode.json`). Cursor and Codex have none — they fall back to LLM translation today.

Native plugin models as of 2026-10: Claude Code ships `.claude-plugin/plugin.json` packages; OpenCode loads TS plugins and reads `opencode.json`; Cursor consumes repo files (`.cursor/rules/*.mdc`, `.cursor/commands/*.md`, `.cursor/hooks.json`); Codex reads `AGENTS.md` natively plus skills in SKILL.md format.

## Requirements

### R1 — Cursor adapter is deterministic
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh cursor` runs, it SHALL render the Cursor integration natively and deterministically, without LLM translation.

### R2 — Cursor rule
- **Pattern:** Ubiquitous
- The cursor adapter SHALL emit `.cursor/rules/harness-sdd.mdc` with valid `.mdc` frontmatter (`description`, `alwaysApply: true`) whose body carries the SDD hard rules and points each role at `.agents/subagents/<name>/SUBAGENT.md`.

### R3 — Cursor commands are namespaced
- **Pattern:** Ubiquitous
- The cursor adapter SHALL emit one `.cursor/commands/harness-<name>.md` per manifest command, whose body instructs the agent to read the command's `body_file`, and SHALL use the `harness-` prefix so it never overwrites user commands.

### R4 — Cursor hooks bridge is evidence-gated
- **Pattern:** Unwanted
- IF the official Cursor hook system (verified against the Cursor docs at implementation time) has an event with a clear SDD equivalent, THEN the adapter SHALL emit `.cursor/hooks.json` whose command invokes `hooks/run-hooks.sh <sdd_event>`, and IF no event has an SDD equivalent, THEN the adapter SHALL NOT emit `hooks.json` and SHALL document the gap in the adapter README.

### R5 — Codex adapter leans on native files
- **Pattern:** Ubiquitous
- The codex adapter SHALL treat `AGENTS.md` as the native entry point — SHALL NOT render, overwrite, or delete it — and SHALL NOT delete anything under `.codex/` it did not generate.

### R6 — Codex prompts are evidence-gated
- **Pattern:** Unwanted
- IF Codex supports project-level custom prompts (verified against the Codex docs at implementation time), THEN the codex adapter SHALL emit `.codex/prompts/harness-<name>.md` per manifest command, and IF it does not, THEN the adapter SHALL NOT emit prompt files and SHALL document the AGENTS.md-plus-skills integration in the adapter README.

### R7 — Adapter discovery covers the four CLIs
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh detect --clis` runs, its evidence SHALL include cursor (`.cursor/rules/harness-sdd.mdc`, `.cursor/commands/harness-*`, `.cursor/hooks.json`) and codex (`.codex/prompts/harness-*`) alongside opencode, gemini-cli, and claude-code.

### R8 — `clean` is per-path and user-safe
- **Pattern:** Unwanted
- IF `./.agents/bootstrap.sh clean` runs, THEN it SHALL delete only the adapter's known generated paths (for cursor and codex, only `harness-`-prefixed or adapter-named files), and SHALL NOT delete user-owned files under `.cursor/` or `.codex/`.

### R9 — Drift checks follow rendered outputs
- **Pattern:** State
- WHILE a cursor or codex adapter has no rendered outputs in the tree, `check_drift` SHALL skip its consistency check.

### R10 — Hygiene knows the new owned paths
- **Pattern:** Ubiquitous
- The check.sh Adapter Hygiene `owned` set SHALL include the cursor and codex generated paths.

### R11 — Adapter READMEs document the mapping
- **Pattern:** Ubiquitous
- `.agents/adapters/cursor/README.md` and `.agents/adapters/codex/README.md` SHALL document the manifest-to-native field mapping following the existing adapter README convention, including hook-bridge decisions and gaps.

### R12 — New adapters are deterministic
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh cursor` and `codex` run twice on an unchanged manifest, their outputs SHALL be byte-identical.

### R13 — Export stays clean for the new adapters
- **Pattern:** State
- WHILE `export` runs, it SHALL NOT copy rendered cursor or codex artifacts into the destination.

### R14 — Documentation reflects four CLIs
- **Pattern:** Ubiquitous
- `AGENTS.md` and `README.md` SHALL list cursor and codex among the supported adapters.

## Traceability with Acceptance Criteria

| Acceptance Criterion | Covered by |
|----------------------|--------------|
| Cursor users stop relying on LLM translation | R1, R2, R3, R4 |
| Codex users get integration without losing native behavior | R5, R6 |
| The observe-first flow knows all four CLIs | R7, R10, R14 |
| Cleanup never destroys user files | R8 |
| Drift model extends to the new adapters | R9 |
| The framework's determinism principle holds for new adapters | R12 |
| Export and docs stay consistent | R13, R14 |
