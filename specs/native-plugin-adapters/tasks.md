# Tasks — native-plugin-adapters

> Discrete steps in order. The implementer marks `[x]` upon completing each one. Each task references the R<n> it covers.

## Implementation

- [x] **T1** — Verify against official docs (cursor.com/docs, OpenAI Codex docs) the Cursor hook event list and whether Codex supports project-level prompts; record findings in the two adapter READMEs. _(R4, R6)_
- [x] **T2** — Create `.agents/adapters/cursor/`: README (field mapping + hook-bridge decisions), `cursor-rule.md.tmpl` (SDD hard rules + role pointers, `.mdc` frontmatter), `cursor-commands/_template.md.tmpl` (body stub pointing at `body_file`). _(R2, R3, R11)_
- [x] **T3** — Add `render_cursor` to `render.py` and register `"cursor"` in `RENDERERS`: single-output rule, one namespaced `harness-<name>.md` command per manifest command, `hooks.json` only per the T1 finding. _(R1, R2, R3, R4, R12)_
- [x] **T4** — Create `.agents/adapters/codex/`: README (AGENTS.md-native contract + verification finding), `codex-prompts/_template.md.tmpl`. Add `render_codex`, register `"codex"`, emit prompts only per the T1 finding; never render or delete `AGENTS.md`. _(R5, R6, R11, R12)_
- [x] **T5** — Upgrade `clean` in `.agents/bootstrap.sh` to the computed per-path owned set (cursor/codex limited to `harness-`-prefixed files), extend `check_drift` guards for cursor/codex, and extend `detect --clis` owned mapping. _(R7, R8, R9)_
- [x] **T6** — In `check.sh`, add cursor/codex paths to the Adapter Hygiene owned set and register `test_plugin_adapters` in the test loop. Update `AGENTS.md` adapter table, `README.md` adapter mentions, and `.agents/BOOTSTRAP.md` output examples. _(R7, R10, R14)_

## Tests

- [x] **T7** — Create `tests/test_plugin_adapters.sh`: fixture manifest with `target_clis: ["cursor"]` renders `.cursor/rules/harness-sdd.mdc` (valid frontmatter, role pointers) and namespaced commands, and no adapters for other CLIs; `target_clis: ["codex"]` renders `.codex/prompts/harness-*` or documents the AGENTS.md-only integration; two consecutive renders are byte-identical. _(R1, R2, R3, R5, R6, R12)_
- [x] **T8** — Extend `tests/test_plugin_adapters.sh`: `clean` with a user file `.cursor/commands/custom.md` and `.codex/prompts/mine.md` present deletes only harness-prefixed outputs and preserves user files; `clean --all` still leaves user files; drift check skips absent outputs; hygiene warns for stray cursor/codex outputs when declared. _(R8, R9, R10)_
- [x] **T9** — Extend `tests/test_plugin_adapters.sh`: `detect --clis` lists cursor and codex evidence; export to a temp tree copies no rendered cursor/codex artifacts; adapter READMEs exist and document the mapping. _(R7, R11, R13)_

## Closure

- [x] **T10** — Document traceability `R<n> ↔ test` in `progress/impl_native-plugin-adapters.md`
- [x] **T11** — Re-render adapters and run `./check.sh` until it exits 0
- [x] **T12** — Update `feature_list.json`: set `status` to `"done"`
- [x] **T13** — Log the summary in `progress/progress.md`

## R<n> ↔ Task map

| Requirement | Tasks |
|-------------|---------|
| R1 | T3, T7 |
| R2 | T2, T3, T7 |
| R3 | T2, T3, T7 |
| R4 | T1, T3, T7 |
| R5 | T4, T7 |
| R6 | T1, T4, T7 |
| R7 | T5, T6, T9 |
| R8 | T5, T8 |
| R9 | T5, T8 |
| R10 | T6, T8 |
| R11 | T2, T4, T9 |
| R12 | T3, T4, T7 |
| R13 | T9 |
| R14 | T6 |
