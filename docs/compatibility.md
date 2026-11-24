# Adapter compatibility

> Generated from `.agents/schemas/capabilities.json` by
> `./.agents/bootstrap.sh capabilities --write`. Edit the JSON, not this file.

What each CLI adapter delivers, and how strongly. The matrix separates what a
CLI is configured to do from what an agent is only asked to do.

## Enforcement levels

- **native-config**: Written into the CLI's own configuration. The CLI is expected to apply it; this framework's tests check that it is rendered, not that the CLI enforces it.
- **instruction-only**: Text the model is asked to follow. Nothing stops an agent that ignores it.
- **not-rendered**: The manifest value does not reach this CLI's files at all.
- **manual-setup**: Works after a one-time step the adapter does not perform.
- **none**: The CLI has no equivalent and the adapter generates nothing.

## Matrix

| | `opencode` | `claude-code` | `gemini-cli` | `cursor` | `codex` |
|---|---|---|---|---|---|
| Instructions | native-config | native-config | native-config | native-config | native-config |
| Roles | native-config | native-config | instruction-only | instruction-only | instruction-only |
| Commands | native-config | native-config | native-config | native-config | none |
| Edit permissions | native-config | instruction-only | instruction-only | not-rendered | none |
| Lifecycle hooks | instruction-only | instruction-only | instruction-only | instruction-only | instruction-only |
| Skills | native-config | manual-setup | instruction-only | instruction-only | native-config |

## `opencode`

Generates: `opencode.json`.

| Element | Level | How |
|---|---|---|
| Instructions | native-config | `instructions[]` copied to `opencode.json`; the CLI loads those files. |
| Roles | native-config | One `agent.<name>` entry per sub-agent, with a prompt that points at its `SUBAGENT.md`. |
| Commands | native-config | One `command.<name>` entry per command, pointing at its body in `.agents/commands/`. |
| Edit permissions | native-config | `permission.edit` is copied per agent into `opencode.json`. |
| Lifecycle hooks | instruction-only | Command bodies call `workflow-transition` and `workflow-run-hook`; no native hook is registered. |
| Skills | native-config | `skills.paths` copied; the CLI discovers `SKILL.md` files there. |

Not supported: Per-agent permissions other than `edit`; Stack-aware permission overrides for roles other than `implementer`.

Evidence: `tests/test_capability_matrix.py::AdapterClaimTests::test_opencode_writes_permissions_into_native_config`, `tests/test_cli_adapter_parity.sh`.

## `claude-code`

Generates: `CLAUDE.md`, `.claude/agents/<name>.md`, `.claude/commands/<name>.md`, `.claude/settings.json`.

| Element | Level | How |
|---|---|---|
| Instructions | native-config | `CLAUDE.md` is loaded by the CLI; it points at `AGENTS.md`. |
| Roles | native-config | One `.claude/agents/<name>.md` per sub-agent, with the role card embedded. |
| Commands | native-config | One `.claude/commands/<name>.md` per command, with the workflow embedded. |
| Edit permissions | instruction-only | The permission map is printed in each agent file. `.claude/settings.json` only pre-allows reading framework files; its `deny` list is empty. |
| Lifecycle hooks | instruction-only | Command bodies call `workflow-transition` and `workflow-run-hook`; no native hook is registered. |
| Skills | manual-setup | The CLI discovers skills under `.claude/skills/`; link `.agents/skills` there once. |

Not supported: Blocking edits to `specs/**` or generated adapters; Per-sub-agent file permissions.

Evidence: `tests/test_capability_matrix.py::AdapterClaimTests::test_claude_code_permissions_are_instruction_only`, `tests/test_cli_adapter_parity.sh`.

## `gemini-cli`

Generates: `GEMINI.md`, `.gemini/commands/<name>.toml`.

| Element | Level | How |
|---|---|---|
| Instructions | native-config | `GEMINI.md` is loaded by the CLI. |
| Roles | instruction-only | Roles are sections of `GEMINI.md`; the CLI has no separate sub-agent concept. |
| Commands | native-config | One `.gemini/commands/<name>.toml` per command. |
| Edit permissions | instruction-only | Printed in `GEMINI.md` as a soft permission contract. |
| Lifecycle hooks | instruction-only | Command bodies call `workflow-transition` and `workflow-run-hook`. |
| Skills | instruction-only | `GEMINI.md` tells the model to read `SKILL.md` files under `.agents/skills/`. |

Not supported: Hard file permissions; Role isolation within a session.

Evidence: `tests/test_capability_matrix.py::AdapterClaimTests::test_gemini_declares_its_permissions_soft`, `tests/test_cli_adapter_parity.sh`.

## `cursor`

Generates: `.cursor/rules/harness-sdd.mdc`, `.cursor/commands/harness-<name>.md`.

| Element | Level | How |
|---|---|---|
| Instructions | native-config | An always-applied project rule; the CLI also reads `AGENTS.md`. |
| Roles | instruction-only | Role pointers in the rule body. |
| Commands | native-config | One `.cursor/commands/harness-<name>.md` per command; the prefix keeps user commands untouched. |
| Edit permissions | not-rendered | The manifest's permission map does not appear in the rule; only the general rule not to edit approved specs does. |
| Lifecycle hooks | instruction-only | No `.cursor/hooks.json`: no Cursor event corresponds to an SDD transition. Command bodies call the workflow commands. |
| Skills | instruction-only | The rule tells the model to read skills under `.agents/skills/`. |

Not supported: File permissions; Native lifecycle hooks for SDD transitions.

Evidence: `tests/test_capability_matrix.py::AdapterClaimTests::test_cursor_does_not_render_the_permission_map`, `tests/test_plugin_adapters.sh`.

## `codex`

Generates: nothing.

| Element | Level | How |
|---|---|---|
| Instructions | native-config | The CLI reads `AGENTS.md`, which is versioned source and never generated. |
| Roles | instruction-only | Described in `AGENTS.md` and the role cards. |
| Commands | none | No project-level slash commands; a workflow is run by asking the agent to follow `.agents/commands/<name>.md`. |
| Edit permissions | none | The CLI has no project file-permission concept. |
| Lifecycle hooks | instruction-only | Workflow bodies call the workflow commands. |
| Skills | native-config | The CLI scans `.agents/skills` from the working directory up to the repository root. |

Not supported: Slash commands; File permissions; Any generated file.

Evidence: `tests/test_capability_matrix.py::AdapterClaimTests::test_codex_generates_nothing`, `tests/test_plugin_adapters.sh`.

## Controls that do not depend on the CLI

These hold for any agent, because a tool applies them rather than the model.

| Control | Enforced by | Evidence |
|---|---|---|
| `./check.sh` gateway | Whoever runs it, and CI on every push and pull request | `tests/test_m1_quality.py` |
| Validated status transitions (`workflow-transition`) | The command itself; a hand edit of `feature_list.json` bypasses it | `tests/test_workflow_state.py` |
| Approved spec bound by digest | `./check.sh` while the feature is in progress, and the `done` transition | `tests/test_workflow_commands.py` |
| Staged-file size limit | Git pre-commit hook once `core.hooksPath` is set, and CI on changed files | `tests/test_token_limit.py` |
| Trusted repository review | `trusted-review.yml` as a required check on the protected default branch | `tests/test_trusted_verify.py` |

## Validation with the CLIs themselves

The generated files are not validated with the vendors' own CLIs. The suites check that each adapter renders the declared files deterministically; whether a given version of a CLI loads and applies them is not exercised, and a skipped native check is recorded as skipped, never as passed.

## Native plugin packaging

Optional and not shipped. Distributing the framework as a Claude Code marketplace plugin and an OpenCode plugin, which would add real blocking of edits to approved specs and generated adapters in OpenCode, is specified in FEAT-009 (`specs/plugin-packaging/`) and awaits human approval.
