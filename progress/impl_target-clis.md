# Implementation report — target-clis (FEAT-007)

## Traceability R<n> ↔ Test

| Requirement | Test | Type | File |
|-------------|------|------|------|
| R1 | shipping manifest has no target_clis; fixture renders honor it | shell | tests/test_target_clis.sh |
| R2 | detect --clis prints evidence JSON and does not mutate | shell | tests/test_target_clis.sh |
| R3 | prompt text "Use this target_clis? [y/n/edit]" present; proposal from evidence | shell | tests/test_target_clis.sh + .agents/bootstrap.sh |
| R4 | undeclared + --yes: opencode only, no litter | shell | tests/test_target_clis.sh |
| R5 | target_clis [cursor] / [opencode] selective render | shell | tests/test_target_clis.sh |
| R6 | unknown name: fallback pointer, exit 0, manifest untouched | shell | tests/test_target_clis.sh |
| R7 | clean: strays removed, listed kept, .agents/hooks untouched | shell | tests/test_target_clis.sh |
| R8 | clean without list and without args refuses (exit 1, usage) | shell | tests/test_target_clis.sh |
| R9 | stray adapter warns, check.sh exits 0; shipping tree silent | shell | tests/test_target_clis.sh |
| R10 | init.md observe-and-ask step (detect --clis + target_clis) | shell | tests/test_target_clis.sh |
| R11 | BOOTSTRAP.md Observe first + export copies no adapters | shell | tests/test_target_clis.sh |
| R12 | README quickstart observe+prompt; --all --yes absent | shell | tests/test_target_clis.sh |
| R13 | export never copies generated adapters | shell | tests/test_target_clis.sh |

## Notes

- `check_drift` now skips consistency checks for adapters whose generated outputs are absent in the tree (opencode.json / GEMINI.md+.gemini / CLAUDE.md+.claude). Without this, an adopted tree that renders only its declared CLI would fail the FEAT-006 R27 gate because gemini/claude drift was checked against files that legitimately do not exist.
- The stray-adapter warning only fires when `target_clis` is declared: without a declared expectation there is no "stray" to define, and the shipping template keeps regenerated adapters locally without warning.
- Real strays come from previous renders (in-sync files), which is why the test renders gemini-cli first and then narrows `target_clis`.
- `--all` behavior changed: interactive + undeclared → evidence proposal + `[y/n/edit]` prompt + persist; non-interactive + undeclared → opencode only + explicit-choice hint. The parity test (two non-interactive `--all` runs) still passes with an untouched manifest.
- Manifest description documents `target_clis`; the field itself stays absent from the shipping manifest (FRESH).

## Validation

- `tests/test_target_clis.sh`: 11/11 assertions.
- Adapters re-rendered for opencode, gemini-cli, claude-code after the manifest description change.
- `./check.sh`: exit 0.
