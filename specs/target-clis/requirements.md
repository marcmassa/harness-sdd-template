# Requirements — target-clis

> Feature FEAT-007 from `feature_list.json`. Makes the used CLI a prompt-first, observed decision: the adopting agent detects evidence of the CLI in use, asks the human, writes the answer to `target_clis` in the manifest, renders only that CLI, and can prune the generated files of the rest — so adopting with Cursor does not leave `CLAUDE.md`, `.claude/`, `GEMINI.md`, `.gemini/` litter behind.
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

The quickstart suggests `./.agents/bootstrap.sh --all --yes`, which renders adapters for opencode, gemini-cli, and claude-code regardless of what the project uses. A Cursor user ends up with three generated adapter sets in the working tree. There is no way to say "this project only uses X", and no agent-facing path to observe and confirm that choice before rendering.

The decision flow must be prompt-first: the agent observes, proposes, asks, and only then acts. The confirmed choice is persisted in the manifest, not only in the chat.

## Requirements

### R1 — `target_clis` field
- **Pattern:** Ubiquitous
- The manifest `.agents/agentic.json` SHALL accept an optional array field `target_clis` whose entries are CLI adapter names, and SHALL NOT require it.

### R2 — Evidence observation helper
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh detect --clis` runs, it SHALL print, per known CLI, the generated adapter paths that exist in the working tree, and SHALL mark each known CLI as `present` or `absent` so an agent can observe the approach in use.

### R3 — Prompt-first selection
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh --all` runs interactively without `target_clis`, it SHALL detect the evidence described in R2, propose a `target_clis` list to the human, ask for confirmation or edits, write the confirmed list to the manifest, and render only the confirmed adapters.

### R4 — Non-interactive default creates no litter
- **Pattern:** Unwanted
- IF `./.agents/bootstrap.sh --all --yes` runs without `target_clis`, THEN it SHALL render only opencode, SHALL NOT render adapters for any other CLI, and SHALL print how to make the choice explicit (`target_clis` or an interactive run).

### R5 — Declared list is selective
- **Pattern:** Event
- WHEN `target_clis` is non-empty, `./.agents/bootstrap.sh --all` SHALL render only the adapters named in `target_clis` and SHALL NOT render adapters for any other CLI, with or without `--yes`.

### R6 — Unknown CLI names do not fail the render
- **Pattern:** Unwanted
- IF `target_clis` names a CLI without a prebuilt adapter, THEN `./.agents/bootstrap.sh --all` SHALL skip that name with an informational message pointing at the LLM fallback and SHALL exit 0.

### R7 — `clean` command
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh clean` runs, it SHALL delete every generated adapter file of a known CLI that is not named in `target_clis` (when declared) and not named in the command arguments, and SHALL NOT delete anything under `.agents/`, `hooks/`, `steering/`, `progress/`, or `specs/`.

### R8 — `clean` refuses ambiguity
- **Pattern:** Unwanted
- IF `target_clis` is absent and `clean` is called without arguments and without `--all`, THEN the command SHALL exit non-zero and print usage instead of deleting anything.

### R9 — Drift warning for stray adapters
- **Pattern:** Unwanted
- IF a generated adapter file for a CLI that is not in `target_clis` exists in the working tree, THEN `./check.sh` SHALL warn and suggest `./.agents/bootstrap.sh clean`, and SHALL NOT fail because of it.

### R10 — `/init` observes and prompts
- **Pattern:** Event
- WHEN `/init` runs, its workflow SHALL instruct the agent to observe the CLI evidence (R2), ask the human which CLIs this project uses, and write the confirmed list to `target_clis` in `.agents/agentic.json` before rendering.

### R11 — Fallback observes first
- **Pattern:** Ubiquitous
- `.agents/BOOTSTRAP.md` SHALL instruct the translating agent to run the evidence observation (R2), propose and confirm `target_clis` — including an unknown CLI name such as `cursor` — with the human, and to generate files only for the CLI in use.

### R12 — Quickstart is prompt-first
- **Pattern:** Ubiquitous
- `README.md` SHALL present observation plus prompt as the standard render step and SHALL NOT present `--all --yes` as the default suggestion.

### R13 — Export stays clean
- **Pattern:** State
- WHILE `export` runs, it SHALL NOT copy generated adapters of any CLI into the destination, regardless of `target_clis`.

## Traceability with Acceptance Criteria

| Acceptance Criterion | Covered by |
|----------------------|--------------|
| The agent can observe which CLI is in use before acting | R2, R3, R10, R11 |
| The choice is confirmed by prompt, not assumed | R3, R10, R11 |
| The confirmed choice persists in the manifest | R1, R3, R10 |
| A Cursor-only project renders nothing else | R5, R6, R11 |
| Non-interactive runs never generate litter | R4 |
| Litter from other CLIs can be removed explicitly | R7, R8, R9 |
| Documentation no longer pushes `--all --yes` by default | R12 |
| Export never reintroduces the litter | R13 |
