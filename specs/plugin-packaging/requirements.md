# Requirements — plugin-packaging

> Feature FEAT-009 from `feature_list.json`. Makes the repository itself distributable as a plugin: a Claude Code marketplace (`/plugin marketplace add`) with the SDD commands and canonical agents, and an OpenCode TS plugin with real SDD enforcement. Verified against the official Claude plugin/marketplace references and the OpenCode plugins docs (2026-10-22).
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

Scope (from the user's phased decision in FEAT-008): distributable packaging, adapters already done. Claude Code distributes plugins through marketplaces: a repo with `.claude-plugin/marketplace.json`; each entry can serve as the plugin manifest when no `plugin.json` exists. OpenCode loads local TS plugins from `.opencode/plugins/` or npm packages. A plugin installs into projects that do NOT have this template, so its components must be self-contained: command bodies reference paths that exist in the user's repo or degrade explicitly, and agent stubs inline the full role content instead of pointing at `.agents/subagents/<name>/SUBAGENT.md`.

The shipping manifest is `FRESH` (no active subagents), so plugin components derive from `_template_subagents_examples[]` (the canonical four), not from the active set.

## Requirements

### R1 — The repo is a Claude marketplace
- **Pattern:** Event
- WHEN the claude-code adapter renders, it SHALL generate `.claude-plugin/marketplace.json` at the repository root with a valid top-level shape per the official marketplace reference (`name`, `owner` with non-empty `name`, `description`, and at least one entry in `plugins`), and it SHALL be committed, not gitignored.

### R2 — Entry-as-manifest
- **Pattern:** Ubiquitous
- The generated marketplace entry SHALL declare `name: "harness-sdd"`, `source: "."`, a `description`, a `commands` object map with one entry per manifest command (its `source` a `./`-prefixed path to `.agents/commands/<name>.md` and its `description` copied from the manifest), and an `agents` array of the four canonical agent stub paths — and the renderer SHALL NOT generate `.claude-plugin/plugin.json`.

### R3 — Self-contained plugin agents
- **Pattern:** Ubiquitous
- The renderer SHALL generate four committed stubs at `.agents/plugin/claude/agents/<name>.md` from the canonical scaffolds, each with valid agent frontmatter (`name`, `description`), the full content of the scaffold's `SUBAGENT.md` inlined in the body, and the scaffold's `SOUL.md` section appended — so the agent works in a repository without the template.

### R4 — Plugin outputs are deterministic and drift-checked
- **Pattern:** Event
- WHEN the claude-code adapter renders twice on an unchanged manifest, `marketplace.json` and the agent stubs SHALL be byte-identical, and `bootstrap.sh claude-code --check` SHALL report drift when they are out of sync with the manifest.

### R5 — OpenCode TS plugin is generated
- **Pattern:** Event
- WHEN the opencode adapter renders, it SHALL generate `.opencode/plugins/harness-sdd.ts` — a zero-dependency TypeScript module (no `@opencode-ai/plugin` import, so no `.opencode/package.json`) that exports a plugin subscribing to `tool.execute.before`.

### R6 — TS plugin enforces the SDD boundaries
- **Pattern:** Unwanted
- IF the edit targets a `specs/<name>/{requirements,design,tasks}.md` file whose matching feature in `feature_list.json` has `sdd: true` and `status: "in_progress"`, THEN the TS plugin SHALL throw an error stating the spec is approved and read-only; IF there is no such active feature, THEN it SHALL NOT block; and IF the edit targets a generated adapter file (`opencode.json`, `GEMINI.md`, `CLAUDE.md`, `.claude/`, `.gemini/`, `.cursor/`, `.opencode/`), THEN it SHALL throw an error pointing at `.agents/agentic.json` and the bootstrap.

### R7 — Discovery, hygiene and clean know the TS plugin
- **Pattern:** Ubiquitous
- The opencode owned paths in `detect --clis`, Adapter Hygiene, and `clean` SHALL include `.opencode` (so `clean` removes it for unlisted CLIs and hygiene warns about strays), and `.opencode` SHALL be gitignored.

### R8 — Export stays consumer-shaped
- **Pattern:** State
- WHILE `export` runs, it SHALL NOT copy `.claude-plugin/` or `.opencode/` into the destination, and SHALL copy the committed plugin agent stubs as part of `.agents/`.

### R9 — Claude validation passes
- **Pattern:** Optional
- WHERE the `claude` CLI is available, `claude plugin validate .` against this repository SHALL report no errors; WHERE it is not available, the test SHALL skip with exit 0.

### R10 — Hook gap documented, commands are the bridge
- **Pattern:** Ubiquitous
- The plugin packaging SHALL NOT declare hooks (no `hooks/hooks.json`, no entry hooks) — the SDD transitions have no Claude hook-event equivalent, the same verified finding as the Cursor adapter — and the gap SHALL be documented in `README.md` or the adapter README.

### R11 — Install path documented
- **Pattern:** Ubiquitous
- `README.md` SHALL document the Claude install path (`/plugin marketplace add <owner>/<repo>` then `/plugin install harness-sdd@harness-sdd-template`) and the OpenCode path (regenerate the adapter to place the TS plugin, or add an npm package to `opencode.json` `plugin`), and SHALL state the limitation that SDD commands expect the template files in the repo.

### R12 — Gate green
- **Pattern:** Ubiquitous
- `./check.sh` SHALL exit 0 with the new test suite registered.

## Traceability with Acceptance Criteria

| Acceptance Criterion | Covered by |
|----------------------|--------------|
| `/plugin marketplace add marcmassa/harness-sdd-template` works | R1, R2, R9 |
| The plugin gives the full SDD workflow without the template | R2, R3, R11 |
| Plugin content is single-source (manifest-driven, deterministic, drift-checked) | R4, R12 |
| OpenCode gets enforcement, not just instructions | R5, R6 |
| Cleanup, discovery and export models stay coherent | R7, R8 |
| No invented hook behavior | R10 |
| Documentation reflects the new distribution model | R11, R12 |
