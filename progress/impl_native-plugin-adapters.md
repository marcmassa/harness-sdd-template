# Implementation report — native-plugin-adapters (FEAT-008)

## Traceability R<n> ↔ Test

| Requirement | Test | Type | File |
|-------------|------|------|------|
| R1 | cursor: rule + namespaced command rendered, other CLIs untouched | shell | tests/test_plugin_adapters.sh |
| R2 | cursor rule has alwaysApply + role pointers | shell | tests/test_plugin_adapters.sh |
| R3 | harness-spec.md command with body_file stub | shell | tests/test_plugin_adapters.sh |
| R4 | no hooks.json emitted (verified gap); bridge = command bodies | shell | tests/test_plugin_adapters.sh + .agents/adapters/cursor/README.md |
| R5 | codex: native integration, nothing generated | shell | tests/test_plugin_adapters.sh |
| R6 | no .codex/prompts emitted (deprecated, user-level); README documents AGENTS.md+skills | shell | tests/test_plugin_adapters.sh + .agents/adapters/codex/README.md |
| R7 | detect --clis lists cursor (present) and codex evidence | shell | tests/test_plugin_adapters.sh |
| R8 | clean removes only harness-prefixed outputs; user files preserved (clean and clean --all) | shell | tests/test_plugin_adapters.sh |
| R9 | drift check skips adapters whose outputs are absent | shell | tests/test_plugin_adapters.sh |
| R10 | hygiene warns for stray cursor outputs, exit 0 | shell | tests/test_plugin_adapters.sh |
| R11 | adapter READMEs copied by export, mapping documented | shell | tests/test_plugin_adapters.sh |
| R12 | cursor consecutive renders byte-identical; codex trivially stable | shell | tests/test_plugin_adapters.sh |
| R13 | export copies adapter sources, never rendered .cursor/.codex artifacts | shell | tests/test_plugin_adapters.sh |
| R14 | AGENTS.md/README/BOOTSTRAP.md include cursor and codex | shell | tests/test_plugin_adapters.sh |

## T1 evidence findings (verified 2026-10-22 against official docs)

- **Cursor hooks** (cursor.com/docs/hooks): `hooks.json` format confirmed (`{"version":1,"hooks":{"<event>":[{"command":"..."}]}}`), 18+ agent events — all tool/session-scoped (`sessionStart`, `preToolUse`, `beforeShellExecution`, `stop`, …). SDD transitions are command-driven: **no genuine 1:1 equivalent** → per R4, `hooks.json` is NOT emitted; the bridge is command bodies instructing `hooks/run-hooks.sh <event>`. Gap documented in the adapter README with a pointer for future mapping.
- **Codex prompts** (learn.chatgpt.com/docs/custom-prompts): custom prompts are **deprecated** in favor of skills, and were user-level only ("not shared through your repository"). → per R6, no prompt files emitted.
- **Codex skills** (learn.chatgpt.com/codex/build-skills): Codex scans `.agents/skills` natively at REPO scope (CWD → repo root) — exactly our canonical location, zero bridging needed. AGENTS.md is the native entry.

## Notes

- `check_drift` guards for cursor/codex must test harness-owned paths only (`.cursor/rules/harness-sdd.mdc`, `.cursor/commands/harness-*.md`, `.cursor/hooks.json`, `.codex/prompts/harness-*.md`) — not the shared `.cursor/commands` directory, which survives cleanup holding user files. Caught by the drift-skip test.
- `clean` now computes the owned-path set in python (including globs for namespaced files) and removes per path; `.gemini`/`.claude` keep whole-directory deletion because they are fully generated.
- `detect --clis` state for codex always reads `absent` (it never generates files); the codex integration is native — documented in the adapter README.
- README line 3 and the template-structure tree now name the five adapters; AGENTS.md §0 table gained cursor/codex rows; BOOTSTRAP.md step 9 examples gained them too.

## Validation

- `tests/test_plugin_adapters.sh`: 10/10 assertions.
- Adapters re-rendered for opencode, gemini-cli, claude-code.
- `./check.sh`: exit 0.
