# Tasks — target-clis

> Discrete steps in order. The implementer marks `[x]` upon completing each one. Each task references the R<n> it covers.

## Implementation

- [x] **T1** — In `.agents/bootstrap.sh`, add `detect --clis`: print the evidence JSON (generated paths that exist per known CLI, `state`, best-effort `host_hints`), observing only and never mutating. _(R2)_
- [x] **T2** — In `.agents/bootstrap.sh`, rewrite `render_all`: with declared `target_clis` render only that list (unknown names skip with a fallback pointer); interactively without it, observe evidence, propose a list, prompt for confirmation or edits, persist the confirmed list with `save_manifest`, then render it; non-interactively without it, render opencode only and print the explicit-choice hint. Document `target_clis` in the help header. _(R1, R3, R4, R5, R6)_
- [x] **T3** — Add `./.agents/bootstrap.sh clean [cli...] [--all]`: deletes the generated adapter paths of known CLIs not in the effective list, refuses with usage when the list is ambiguous, prints every removed path, and never touches `.agents/`, `hooks/`, `steering/`, `progress/`, or `specs/`. _(R7, R8)_
- [x] **T4** — In `check.sh`, add a warning (not a failure) for each generated adapter path whose CLI is not in `target_clis`, suggesting `./.agents/bootstrap.sh clean`. Register `test_target_clis` in the CLI Adapter Tests loop. _(R9)_
- [x] **T5** — Update `.agents/commands/init.md`: new step that runs `detect --clis`, shows the evidence to the human, asks which CLIs the project uses, and writes the confirmed list to `target_clis` before rendering. Update `.agents/BOOTSTRAP.md`: the fallback agent observes evidence first, proposes and confirms `target_clis` (including unknown names like `cursor`) with the human, and generates files only for the CLI in use. _(R10, R11)_
- [x] **T6** — Update `README.md` quickstart: observe + prompt + render the CLI in use; `--all --yes` no longer the default suggestion. _(R12)_

## Tests

- [x] **T7** — Create `tests/test_target_clis.sh`: `detect --clis` prints valid JSON with per-CLI state and does not mutate the manifest; fixture manifest with `target_clis: ["cursor"]` renders no known-CLI adapters and exits 0 with a fallback pointer; absent field renders opencode only in a non-interactive run. _(R2, R5, R6, R4)_
- [x] **T8** — Extend `tests/test_target_clis.sh`: `clean` without args and without list exits non-zero deleting nothing; `clean` with `target_clis` deletes stray adapter paths and never deletes `.agents/` or hooks; `clean --all` deletes every generated adapter path; `clean` prints removed paths. _(R7, R8)_
- [x] **T9** — Extend `tests/test_target_clis.sh`: create a stray `GEMINI.md` with `target_clis: ["opencode"]` and assert `check.sh` warns but exits 0; assert the shipping tree (no `target_clis`, no stray adapters) produces no such warning; assert `export` never copies generated adapters even when they exist in the source tree. _(R9, R13)_
- [x] **T10** — Assert `.agents/commands/init.md` contains the observe-and-ask step and `.agents/BOOTSTRAP.md` instructs the fallback agent to observe, propose, confirm, and declare `target_clis`. _(R10, R11)_

## Closure

- [x] **T11** — Document traceability `R<n> ↔ test` in `progress/impl_target-clis.md`
- [x] **T12** — Re-render adapters with `./.agents/bootstrap.sh --all` and run `./check.sh` until it exits 0
- [x] **T13** — Update `feature_list.json`: set `status` to `"done"`
- [x] **T14** — Log the summary in `progress/progress.md`

## R<n> ↔ Task map

| Requirement | Tasks |
|-------------|---------|
| R1 | T2, T7 |
| R2 | T1, T7 |
| R3 | T2 |
| R4 | T2, T7 |
| R5, R6 | T2, T7 |
| R7, R8 | T3, T8 |
| R9 | T4, T9 |
| R10 | T5, T10 |
| R11 | T5, T10 |
| R12 | T6 |
| R13 | T9 |
