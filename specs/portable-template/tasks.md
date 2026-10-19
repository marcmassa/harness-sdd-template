# Tasks — Portable template

> Discrete steps in order. The implementer marks `[x]` upon completing each one. Each task references the R<n> it covers.

## Implementation

- [x] **T1** — In `.agents/agentic.json`, set `subagents`, `steering`, and `hooks` to `[]`, remove `default_agent`, keep every `_template_*` field, and rewrite `_template_steering_examples[].description` and `_template_hooks_examples[].description` in English. Do not add `templates` to either active or scaffold arrays. _(R1, R2, R24)_
- [x] **T2** — In `.agents/bootstrap.sh` `auto_scaffold_content`, stop appending to `steering[]` and `hooks[]`. Creating a missing scaffold file remains allowed. The created steering placeholder must be the English line `<!-- TODO: customize this steering file for the project -->`. _(R6, R8, R24)_
- [x] **T3** — In `render.py` `build_context` and `render_opencode`, omit `default_agent` unless it names an entry in `subagents[]`. Remove the `"harness"` fallback. _(R4, R5)_
- [x] **T4** — Add `scaffold_subagent_soul_file` and call it from the `add-agent` promotion path. Copy `agent-template/SOUL.md` only when the target is missing, and set `agent:` to the new name. _(R28)_
- [x] **T5** — Add `render.py --list-renderers` and teach `list_adapters` to union those names with directories that contain `*.tmpl`. `detect` must label the stack line `Project stack:`. _(R16, R17)_
- [x] **T6** — Add `render.py --export` and `./.agents/bootstrap.sh export <dest>` using the allowlist and reset rules in `design.md`. Refuse a non-empty destination before writing. _(R18, R19, R20, R21, R22)_
- [x] **T7** — In `check.sh`, run terraform/tflint only when a `*.tf` file exists outside `.git`; warn on a missing `SUBAGENT.md` only for declared names; fail active hooks that are missing, empty, or not executable; fail active steering files that contain `<!-- TODO`. Leave the `FRESH` init branch informational. _(R10, R11, R12, R13, R14, R15)_
- [x] **T8** — Restore the three hook scripts as non-empty executable English examples, using the bodies in `design.md`. Leave them out of `hooks[]`. Rewrite `steering/*.md` placeholder bodies in English. _(R9, R24)_
- [x] **T9** — Replace `SECURITY.md` with a short English policy that names Harness SDD Template and does not mention `5.1.x` or `4.0.x`. In `GEMINI.md.tmpl`, replace the hardcoded harness-default sentence with a statement that no default agent is active until `/init` sets `default_agent`. Update the README quickstart to use `export` instead of `cp -r`. _(R23, R24, R29)_

## Tests

- [x] **T10** — Create `tests/test_portable_template.sh` covering the shipping manifest shape, `detect` output, export refusal, export payload boundaries, exported `feature_list.json`, English `SECURITY.md`, and `./check.sh` exit 0 in an exported tree. _(R1, R2, R3, R16, R17, R18, R19, R20, R21, R22, R23, R26)_
- [x] **T11** — Extend `tests/test_portable_template.sh` with a temp manifest whose `hooks[]` points at an empty script and whose `steering[]` points at a file containing `<!-- TODO`, and assert `check.sh` exits non-zero for each. Assert a scaffold-only TODO file does not fail the shipping tree. _(R10, R12, R13)_
- [x] **T12** — Extend `tests/test_portable_template.sh` so two non-interactive `./.agents/bootstrap.sh --all` runs leave `.agents/agentic.json` byte-identical, and so `add-agent implementer --yes` in an exported tree creates `SOUL.md` with `agent: implementer`. Then run `remove-examples --yes`, assert `INITIALIZED`, and assert `./check.sh` exits 0. _(R6, R7, R27, R28)_
- [x] **T13** — Update `tests/test_soul_md.sh` T9 to render a fixture manifest that includes `templates`, instead of requiring `.claude/agents/templates.md` from the shipping manifest. Update `tests/test_steering.sh` so a fixture with global steering still asserts the path appears in `opencode.json` `instructions`. _(R3, R30)_
- [x] **T14** — Add a fixture assertion that `opencode.json` omits `default_agent` when the key is absent, and includes it when it names an active subagent. Assert rendered `GEMINI.md` does not contain `The harness role is the default` for the shipping manifest. _(R4, R5, R29)_

## Closure

- [x] **T15** — Document traceability `R<n> ↔ test` in `progress/impl_portable-template.md`
- [x] **T16** — Re-render adapters with `./.agents/bootstrap.sh --all` and run `./check.sh` until it exits 0 _(R25)_
- [ ] **T17** — Update `feature_list.json`: set `status` to `"done"`
- [ ] **T18** — Log the summary in `progress/progress.md`

## R<n> ↔ Task map

| Requirement | Tasks |
|-------------|---------|
| R1, R2 | T1, T10 |
| R3 | T10, T13 |
| R4, R5 | T3, T14 |
| R6, R7, R8 | T2, T12 |
| R9 | T8 |
| R10, R11 | T7, T11 |
| R12, R13 | T7, T11 |
| R14, R15 | T7 |
| R16, R17 | T5, T10 |
| R18–R22 | T6, T10 |
| R23, R24 | T1, T8, T9, T10 |
| R25 | T16 |
| R26 | T10 |
| R27, R28 | T4, T12 |
| R29 | T9, T14 |
| R30 | T13 |
