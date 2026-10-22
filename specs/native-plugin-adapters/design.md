# Design — native-plugin-adapters

> Technical decisions for FEAT-008. Two new deterministic adapters (cursor, codex) reusing the existing manifest-to-adapter pipeline, plus per-path cleanup. No distributable packaging (scope confirmed with the human).

## Summary

Claude Code and OpenCode already integrate through generated files. Cursor and Codex fall back to LLM translation. This feature adds two deterministic adapters that follow the same pattern: a `render_<cli>()` function in `render.py`, `.tmpl` templates in `.agents/adapters/<cli>/`, a field-mapping README, and discovery/cleanup/drift/hygiene updates. Both adapters bridge SDD lifecycle hooks to `hooks/run-hooks.sh` from whatever native mechanism the CLI offers. `AGENTS.md` is never touched by the codex adapter.

Key constraint discovered in design: Cursor's `.cursor/commands/` and Codex's `.codex/prompts/` are shared, user-writable directories — unlike `.claude/` or `.gemini/`, which are fully generated. So the new adapters namespace their files with a `harness-` prefix and `clean` works at per-path granularity there instead of deleting whole directories.

## Affected Files

| File | Action | Reason |
|---------|--------|-------|
| `.agents/adapters/cursor/README.md` | create | Field mapping + hook-bridge decisions (R11) |
| `.agents/adapters/cursor/cursor-rule.md.tmpl` | create | Template for `.cursor/rules/harness-sdd.mdc` (R2) |
| `.agents/adapters/cursor/cursor-commands/_template.md.tmpl` | create | Per-command template (R3) |
| `.agents/adapters/codex/README.md` | create | Field mapping + AGENTS.md-native contract (R11) |
| `.agents/adapters/codex/codex-prompts/_template.md.tmpl` | create | Per-command prompt template (R6) |
| `.agents/adapters/_common/render.py` | modify | `render_cursor`, `render_codex`, RENDERERS entries (R1, R12) |
| `.agents/bootstrap.sh` | modify | `clean` per-path granularity; `check_drift` guards (R8, R9) |
| `check.sh` | modify | Hygiene owned set; register test (R10) |
| `.agents/BOOTSTRAP.md` | modify | Adapter output examples gain cursor/codex (R14) |
| `AGENTS.md`, `README.md` | modify | Adapter lists (R14) |
| `tests/test_plugin_adapters.sh` | create | R1–R13 coverage |
| `check.sh` (test loop) | modify | Register `test_plugin_adapters` |

## Signatures and Structures

Renderer registration:

```python
RENDERERS = {
    "opencode": render_opencode,
    "gemini-cli": render_gemini,
    "claude-code": render_claude,
    "cursor": render_cursor,
    "codex": render_codex,
}
```

`render_cursor(root, manifest, ctx, check)`:

```
.cursor/rules/harness-sdd.mdc        ← cursor-rule.md.tmpl, single-output substitution
.cursor/commands/harness-<name>.md   ← cursor-commands/_template.md.tmpl, one per ctx["commands"]
.cursor/hooks.json                   ← ONLY if a verified Cursor hook event maps to an SDD event (R4)
```

The `.mdc` frontmatter is project-rule format:

```mdc
---
description: Harness SDD workflow — spec-driven, traceable, human-approved
alwaysApply: true
---
```

Body: hard rules (one in_progress feature, spec-before-code, check.sh gateway, no spec edits after approval) plus the role table pointing at `.agents/subagents/<name>/SUBAGENT.md`. The per-command template body: `Read <body_file> and execute the workflow described there.` — same stub contract as the other adapters.

`render_codex(root, manifest, ctx, check)`:

```
.codex/prompts/harness-<name>.md     ← codex-prompts/_template.md.tmpl, one per ctx["commands"], ONLY if project-level prompts are verified
```

`AGENTS.md` is the Codex native entry (read automatically). Skills in `.agents/skills/*/SKILL.md` use the cross-CLI SKILL.md convention. The codex adapter never writes `AGENTS.md`, never deletes under `.codex/` it did not generate, and records in its README whether prompts were emitted or the integration is AGENTS.md-only.

Owned paths (used by `detect --clis`, `clean`, and hygiene):

```
opencode     → opencode.json
gemini-cli   → GEMINI.md, .gemini
claude-code  → CLAUDE.md, .claude
cursor       → .cursor/rules/harness-sdd.mdc, .cursor/commands/harness-*.md, .cursor/hooks.json (if emitted)
codex        → .codex/prompts/harness-*.md
```

`clean` upgrade — replaces the flat bash mapping with a computed path list:

```
effective list = args | target_clis | refuse (unchanged)
owned(cli) computed in python from the table above
  cursor: glob .cursor/commands/harness-*.md (never other files)
  codex:  glob .codex/prompts/harness-*.md
bash removes each printed path, echoes "removed: <path>", skips missing
```

`.gemini` and `.claude` keep whole-directory deletion: in an adopted tree they are fully generated. `.cursor/` and `.codex/` are never deleted wholesale.

`check_drift` guards gain:

```
cursor → [ -e .cursor/rules/harness-sdd.mdc ] || [ -d .cursor/commands ] || continue
codex  → [ -d .codex/prompts ] || continue
```

Hook bridge principle (all adapters): the SDD hook system fires on slash-command transitions. Where a CLI supports command bodies (Cursor, Claude, Gemini, OpenCode), the bridge is the body stub instructing `hooks/run-hooks.sh <event>`; `.cursor/hooks.json` is emitted only for tool-lifecycle events that have a genuine SDD equivalent, verified against the official docs during implementation. If the verified event list has no SDD-equivalent mapping (expected outcome: SDD transitions are command-driven, not tool-driven), the adapter omits `hooks.json` and documents the gap — the commands remain the bridge.

## Algorithm / Flow

```
1. Verify native facts in official docs: Cursor hook event list; Codex project-level prompts. Record findings in the adapter READMEs (R4, R6 evidence gate).
2. Write cursor adapter templates + render_cursor + register.
3. Write codex adapter templates + render_codex + register (respecting the verification outcome).
4. Upgrade clean to per-path owned-set; extend detect --clis, check_drift guards, hygiene owned set.
5. Docs: adapter READMEs, AGENTS.md adapter table, README, BOOTSTRAP.md output examples.
6. tests/test_plugin_adapters.sh; register in check.sh loop; re-render; ./check.sh green.
```

## Error Handling

| Condition | Response |
|-----------|-----------|
| Docs verification finds no Cursor SDD hook equivalent | omit hooks.json, document gap, exit 0 |
| Docs verification finds no Codex project prompts | omit prompts, document AGENTS.md integration, exit 0 |
| User file collides with a `harness-`-prefixed name | renderer overwrites only its own namespaced path; user files never match the prefix |
| `clean` path missing | skip silently (unchanged) |

## Discarded Alternative

**Emit whole `.cursor/` and `.codex/` directories and delete them in `clean`, like `.claude/`.** Discarded because both are shared user directories: Cursor projects routinely carry pre-existing project rules the team wrote; deleting `.cursor/` would destroy them. Namespaced files plus per-path cleanup is the only safe model — it is also why `harness-` prefixing is a requirement rather than a style choice.

A second discarded option: full distributable packaging (Claude `plugin.json` + npm opencode plugin). Confirmed out of scope with the human; becomes FEAT-009 if needed later. The adapters here produce the same artifacts a future package would bundle, so nothing is thrown away.

## Risks and Edge Cases

- Cursor `.mdc` frontmatter and Codex prompt support change fast; the evidence gate (R4, R6) forces re-verification against official docs at implementation time instead of trusting this design's 2026-10 snapshot.
- `harness-` prefix could collide with a user file literally named `harness-init.md`. Accepted risk: negligible, documented in adapter README.
- `detect --clis` `host_hints` does not change; cursor evidence is file-based.
- Export copies `.agents/adapters/` (source templates) but never rendered outputs — already true for opencode/gemini/claude; R13 asserts it for the new pair.
- Parity test's `GENERATED_FILES` array stays as-is; new-adapter determinism is covered by the new test instead of widening the legacy array.
