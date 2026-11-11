# Tasks — plugin-packaging

> Discrete steps in order. The implementer marks `[x]` upon completing each one. Each task references the R<n> it covers.

## Implementation

- [ ] **T1** — Create `.agents/adapters/claude-code/claude-plugin-agents/_template.md.tmpl` (self-contained agent stub: frontmatter `name`/`description`, inlined role content with leading frontmatter stripped, soul section) and add the `_plugin_agent_item` enrichment reading the canonical scaffolds. _(R3)_
- [ ] **T2** — Extend `render.py` `render_claude` with `render_claude_plugin`: generate the four committed stubs at `.agents/plugin/claude/agents/<name>.md` from `category == "canonical"` scaffolds, and generate `.claude-plugin/marketplace.json` (entry-as-manifest: `name: "harness-sdd"`, `source: "."`, description, commands map from manifest commands with `./`-prefixed sources, agents array; omit `agents` when empty; no `plugin.json`, no hooks). _(R1, R2, R3, R4, R5-...)_
- [ ] **T3** — Extend `render.py` `render_opencode` to write `.opencode/plugins/harness-sdd.ts` (zero-dep TS module, `tool.execute.before`, specs read-only guard for the active `sdd` `in_progress` feature, generated-adapters guard). _(R5, R6)_
- [ ] **T4** — Update `.gitignore` (add `/.opencode/`; add comments marking `.claude-plugin/` and `.agents/plugin/` as committed distribution payload) and update `.agents/bootstrap.sh` (`clean` owned set) plus `check.sh` (`detect --clis` mapping in bootstrap, Adapter Hygiene owned set) so `.opencode` is owned by opencode. _(R7)_
- [ ] **T5** — Update `README.md` (new "Install as a plugin" section: Claude two-command path, OpenCode regenerate-or-npm path, hook-gap note, self-containment limitation) and `.agents/BOOTSTRAP.md` step 9 output examples. _(R10, R11)_

## Tests

- [ ] **T6** — Create `tests/test_plugin_packaging.sh`: re-render and assert `marketplace.json` is valid JSON with required top-level fields and one entry (`name`, `source`, `description`, 7 commands with `./.agents/commands/` sources matching manifest descriptions, 4 agents); assert the 4 stubs exist with frontmatter `name`/`description`, inlined role content (no second frontmatter block at body start), and autogen header. _(R1, R2, R3)_
- [ ] **T7** — Extend `tests/test_plugin_packaging.sh`: assert determinism (two renders byte-identical for marketplace + stubs) and drift detection (`bootstrap.sh claude-code --check` fails after tampering with `marketplace.json`, passes after re-render); assert `.opencode/plugins/harness-sdd.ts` exists, contains `tool.execute.before`, both guard messages, and no `@opencode-ai/plugin` import or `.opencode/package.json`. _(R4, R5, R6)_
- [ ] **T8** — Extend `tests/test_plugin_packaging.sh`: fixture with `target_clis: ["opencode"]` and a stray `.claude-plugin/` … no — assert hygiene/clean contract: fixture with `.opencode/` present and target_clis `["cursor"]` → `clean` removes `.opencode`; `detect --clis` reports `.opencode/plugins` in opencode paths; export to a temp tree copies no `.claude-plugin/`/`.opencode/` but does copy `.agents/plugin/`; optional `claude plugin validate .` (skip exit 0 when CLI absent, no errors when present). _(R7, R8, R9)_

## Closure

- [ ] **T9** — Document traceability `R<n> ↔ test` in `progress/impl_plugin-packaging.md`
- [ ] **T10** — Re-render adapters and run `./check.sh` until it exits 0
- [ ] **T11** — Update `feature_list.json`: set `status` to `"done"`
- [ ] **T12** — Log the summary in `progress/progress.md`

## R<n> ↔ Task map

| Requirement | Tasks |
|-------------|---------|
| R1 | T2, T6 |
| R2 | T2, T6 |
| R3 | T1, T2, T6 |
| R4 | T2, T7 |
| R5 | T3, T7 |
| R6 | T3, T7 |
| R7 | T4, T8 |
| R8 | T8 |
| R9 | T8 |
| R10 | T5 |
| R11 | T5 |
| R12 | T10 |
