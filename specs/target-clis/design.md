# Design — target-clis

> Technical decisions for FEAT-007. The feature makes "which CLI does this project use" an observed, prompt-confirmed, persisted decision — then renders and prunes accordingly. It does not change any renderer's output.

## Summary

`bootstrap.sh --all --yes` renders every prebuilt adapter even when the project uses one CLI, and there is no agent-facing path to observe and confirm that choice. This feature adds: an evidence observation helper (`detect --clis`), a prompt-first selection flow in `--all`, the persisted `target_clis` field in `.agents/agentic.json`, a `clean` command that deletes generated files of unlisted CLIs, a `check.sh` warning for strays, and documentation updates in `/init`, `BOOTSTRAP.md`, and `README.md`.

The declared list is the single place where the confirmed choice lives. The agent observes evidence, the human confirms via prompt, the manifest stores it. Unknown names (like `cursor`) are allowed: they carry intent for the LLM fallback even though no deterministic renderer exists.

## Affected Files

| File | Action | Reason |
|---------|--------|-------|
| `.agents/bootstrap.sh` | modify | `detect --clis`; prompt-first `render_all`; new `clean` subcommand; help text |
| `check.sh` | modify | Warning section for stray generated adapters; register test |
| `.agents/commands/init.md` | modify | New step: observe evidence, ask which CLIs, write `target_clis` |
| `.agents/BOOTSTRAP.md` | modify | Fallback agent observes first, proposes, confirms, declares |
| `README.md` | modify | Quickstart: observe → prompt → render one CLI; drop `--all --yes` as default |
| `tests/test_target_clis.sh` | create | R1–R13 coverage |

## Signatures and Structures

Manifest field:

```jsonc
{
  "target_clis": ["cursor"]   // optional; absent = prompt-first flow
}
```

Valid names: any string. Known prebuilt adapters are `opencode`, `gemini-cli`, `claude-code`. Unknown names render nothing deterministic and are consumed by the LLM fallback.

Generated files owned by each known adapter:

```
opencode     → opencode.json
gemini-cli   → GEMINI.md, .gemini/
claude-code  → CLAUDE.md, .claude/
```

Evidence observation — `./.agents/bootstrap.sh detect --clis` prints one JSON object:

```json
{
  "opencode":    { "generated_paths": ["opencode.json"], "state": "present" },
  "gemini-cli":  { "generated_paths": ["GEMINI.md", ".gemini/"], "state": "present" },
  "claude-code": { "generated_paths": [], "state": "absent" },
  "host_hints":  { "CLAUDECODE": "unset", "CURSOR_TRACE_ID": "unset" }
}
```

`state` is `present` when any of the CLI's generated paths exists on disk. `host_hints` is best-effort: it reports well-known host-CLI environment variables (`CLAUDECODE`, `CURSOR_TRACE_ID`) as `set`/`unset`, with file evidence taking precedence. The helper exits 0 always; it observes, never mutates.

`render_all` selection:

```
declared = manifest.target_clis (may be absent)
if declared:
  for name in declared:
    if name in RENDERERS or adapter dir has *.tmpl: render_one(name)
    else: print "  (no prebuilt adapter for '<name>' — the LLM fallback in .agents/BOOTSTRAP.md handles it)"
elif interactive (stdin is a TTY):
  evidence = detect --clis output
  proposed = known CLIs whose generated paths exist, or ["opencode"] if none
  print the proposal with one line of rationale per entry
  ask "Use this target_clis? [y/n/edit list]"; honor edits, persist to manifest, render confirmed list
else:
  render opencode only; print the explicit-choice hint
```

The prompt uses the existing interactive pattern (`printf` + `read -r`) already used by `add-agent`. The persisted write reuses `save_manifest` so formatting stays consistent.

`clean` deletes exactly the generated paths of known CLIs that are not in the effective list. The effective list is `target_clis` when declared, otherwise positional arguments, otherwise nothing (refuse). `clean --all` deletes every generated adapter path regardless of the list. It never touches `.agents/`, `hooks/`, `steering/`, `progress/`, `specs/`, `tests/`, or any path outside the table above. It prints each removed path and skips missing ones silently.

```bash
./.agents/bootstrap.sh clean          # effective list from target_clis; error if undeclared
./.agents/bootstrap.sh clean opencode # prunes every known adapter except opencode
./.agents/bootstrap.sh clean --all    # deletes every generated adapter path
```

`check.sh` warning (informational, does not set EXIT_CODE):

```
for each known adapter path that exists and whose CLI is not in target_clis:
  warn "<path> belongs to a CLI not in target_clis — run ./.agents/bootstrap.sh clean"
```

## Algorithm / Flow

```
1. bootstrap.sh: add detect --clis, prompt-first render_all, clean subcommand.
2. check.sh: stray-adapter warning + register tests/test_target_clis.sh.
3. Docs: init.md step, BOOTSTRAP.md observe-first contract, README quickstart.
4. Shipping manifest stays without target_clis (absent = prompt-first, no litter).
5. Re-render adapters; ./check.sh must stay green.
```

## Error Handling

| Condition | Response |
|-----------|-----------|
| `clean` without list and without args | exit 1, usage printed, nothing deleted |
| `clean` path already missing | skip silently, still exit 0 |
| Prompt answered `n` | abort render, exit 0, nothing changed |
| `target_clis` contains an unknown CLI | render skips it, exit 0, fallback pointer printed |
| Non-interactive run without list | opencode only, exit 0, hint printed |

## Discarded Alternative

**Delete stray adapters automatically on every render.** Discarded because implicit deletion in a render command is surprising: a developer with two CLIs (e.g. opencode at work, Cursor on a laptop) would lose one adapter every time the other CLI runs. Deletion must be an explicit command (`clean`) with visible output.

A second discarded option: hardcode the answer (always render only opencode, ignore prompts). Discarded because it discards real multi-CLI teams and contradicts the prompt-first requirement — the human confirms, the manifest persists.

A third discarded option: a separate `.harnessrc` file for the choice. Discarded because the manifest is already the single source of truth every tool reads; a second config file creates a sync problem.

## Risks and Edge Cases

- `clean` deletes gitignored files, so git status will not show it. The command prints what it deleted to stay auditable.
- `.claude/` contains only generated artifacts (`.agents/` is the source of truth), so deleting it is safe; the same holds for `.gemini/`.
- Host hints are best-effort: absence of a hint never changes behavior; file evidence wins.
- A user who declares `target_clis: ["opencode"]` while running claude-code daily must render explicitly with `bootstrap.sh claude-code`; `--all` will no longer do it. Documented in README.
- `/init` writing `target_clis` mutates the manifest before scaffolds are dropped. Fine: it is a project field, not a scaffold field.
- The check.sh warning must not fire in the shipping template where no generated adapters exist.
