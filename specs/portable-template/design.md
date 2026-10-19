# Design — Portable template

> Technical decisions for FEAT-006. The feature changes the shipping shape of the manifest and the copy path. It does not change the SDD state machine.

## Summary

The template currently ships in `PARTIAL`: `subagents[]` contains `templates` while scaffolds remain, so `./check.sh` fails on its own product. `steering[]` and `hooks[]` are copies of the scaffolds, two hook scripts are empty, and `auto_scaffold_content` in `.agents/bootstrap.sh` re-registers those scaffolds whenever the active arrays are empty. A `cp -r` of this repository also copies framework history (`FEAT-002` through `FEAT-005`, `AUTHORITY`, internal specs).

The shipping manifest becomes `FRESH`: active arrays empty, scaffolds retained, no `default_agent`. Render stops mutating the manifest. `./.agents/bootstrap.sh export <dest>` is the supported way to install the template into another project. `FRESH` stays informational in `check.sh`. `PARTIAL` stays a failure. No repository-name special case.

## Affected Files

| File | Action | Reason |
|---------|--------|-------|
| `.agents/agentic.json` | modify | Empty active arrays, drop `default_agent`, English scaffold descriptions |
| `.agents/bootstrap.sh` | modify | Stop manifest mutation in `auto_scaffold_content`; list programmatic adapters; add `export` |
| `.agents/adapters/_common/render.py` | modify | Omit dangling `default_agent`; scaffold `SOUL.md`; `export` helper; `--list-renderers` |
| `check.sh` | modify | File-gated terraform, declaration-gated subagent warnings, active hook/steering failures |
| `hooks/on-spec-created_validate.sh` | modify | Restore a non-empty executable English example |
| `hooks/on-feature-done_notify.sh` | modify | Restore a non-empty executable English example |
| `hooks/on-check-pass_ci.sh` | modify | English example body; keep it out of `hooks[]` |
| `steering/global-conventions.md` | modify | English placeholder body |
| `steering/implementer-patterns.md` | modify | English placeholder body |
| `.agents/adapters/gemini-cli/GEMINI.md.tmpl` | modify | Do not hardcode harness as the default |
| `SECURITY.md` | modify | Replace GitHub boilerplate |
| `README.md` | modify | Document `export` as the install step |
| `tests/test_portable_template.sh` | create | R1–R29 coverage that the existing tests do not own |
| `tests/test_soul_md.sh` | modify | T9 must render a fixture; shipping manifest no longer includes `templates` |
| `tests/test_steering.sh` | modify | Keep injection coverage when `steering[]` is empty (R30) |

## Signatures and Structures

```
./.agents/bootstrap.sh export <dest>
  exit 0 and write <dest> only when <dest> does not exist or is empty
  exit 1 and write nothing otherwise

./.agents/bootstrap.sh detect
  prints "Available adapters:" then one "  - <name>" line per discovered CLI
  prints "Project stack:" then a JSON array (possibly [])

render.py --list-renderers
  prints one RENDERERS key per line: opencode, gemini-cli, claude-code

render.py --export <dest> --root <root>
  implements the copy; bootstrap.sh is the CLI wrapper
```

Shipping manifest shape:

```
subagents: []
steering: []
hooks: []
# default_agent key absent
_template_subagents_examples: present (canonical + illustrative scaffolds)
_template_steering_examples: present
_template_hooks_examples: present
_template_lifecycle: present
```

`render_opencode` includes `default_agent` only when `build_context` returns a non-empty string that names an active subagent. The implicit fallback `"harness"` in `build_context` is removed.

`add-agent` already calls `scaffold_subagent_role_file`. That function, or a sibling called from the same promotion path, creates `SOUL.md` beside `SUBAGENT.md` when missing:

```
function scaffold_subagent_soul_file(root, sa) -> bool
  target = root / ".agents/subagents" / sa.name / "SOUL.md"
  if target exists: return false
  copy agent-template/SOUL.md
  replace the frontmatter line "agent: agent-template" with "agent: <name>"
```

Export allowlist (copy these; do not start from a full tree and delete):

```
AGENTS.md DESIGN.md README.md LICENSE SECURITY.md check.sh .gitignore
docs/sdd.md
.agents/            except .agents/subagents/templates/ and any __pycache__
specs/README.md
specs/templates/
examples/
hooks/run-hooks.sh
hooks/on-spec-created_validate.sh
hooks/on-feature-done_notify.sh
hooks/on-check-pass_ci.sh
steering/*.md
```

Export then overwrites `feature_list.json` and `progress/{current,progress,backlog,decisions,handoff}.md` with English templates. The consumer feature list has one pending `sdd: true` feature named `example-feature`. It does not copy `tests/`.

Hook example bodies, in English:

```
hooks/on-spec-created_validate.sh
  if FEATURE_NAME is set and specs/$FEATURE_NAME exists:
    warn if the directory does not contain exactly 3 *.md files
    warn if requirements.md has no "^### R[0-9]" heading
  exit 0

hooks/on-feature-done_notify.sh
  print FEATURE_ID, FEATURE_NAME, UTC timestamp, AGENT_NAME
  exit 0

hooks/on-check-pass_ci.sh
  write the UTC timestamp to progress/last-check-pass.txt
  exit 0
```

These scripts stay out of `hooks[]`. `add-hook` remains the way to register them.

`check.sh` hook validation treats missing, zero-byte, or non-executable active scripts as errors. Non-executable is no longer a warning. Steering validation treats `<!-- TODO` in an active file as an error. Undeclared files under `steering/` stay warnings.

Terraform and tflint run only when `find` reports a `*.tf` file outside `.git`. The subagent loop warns about a missing `SUBAGENT.md` only for declared names.

`list_adapters` lists a directory when its basename is printed by `--list-renderers` or the directory contains `*.tmpl`. `_common` and `_generic` stay hidden.

## Algorithm / Flow

```
1. Shape agentic.json to FRESH and translate the scaffold descriptions this feature touches.
2. Stop auto_scaffold_content from appending to steering[] or hooks[].
   File creation for a missing scaffold path remains allowed.
3. Teach the renderer to omit a dangling default_agent and to scaffold SOUL.md.
4. Tighten check.sh (R10, R12, R14, R15) without changing the FRESH init branch.
5. Restore the three hook scripts and the English steering placeholders.
6. Add export. Point README quickstart at it. Replace SECURITY.md.
7. Add tests/test_portable_template.sh and adjust test_soul_md.sh and test_steering.sh.
8. Re-render adapters. ./check.sh must exit 0 on this repository.
9. Export to a temp dir, run ./check.sh there, then add-agent + remove-examples and run ./check.sh again.
```

## Error Handling

| Condition | Response |
|-----------|-----------|
| `export` destination exists and is non-empty | exit 1, destination unchanged |
| `export` destination parent is not writable | exit 1, no partial tree left behind (remove the dest created by this run) |
| Active hook script missing, empty, or not executable | `check.sh` exit 1 |
| Active steering file contains `<!-- TODO` | `check.sh` exit 1 |
| `add-agent` name is not a scaffold | existing error, unchanged |
| `default_agent` names an unknown agent | omit the key; do not invent `harness` |

## Discarded Alternative

**Special-case this repository in `check.sh`.** Treat `PARTIAL` as success when the directory name is `harness-sdd-template`, or add `distribution: template` and skip the init gate. Discarded because the next `bootstrap.sh` render would still re-register scaffolds through `auto_scaffold_content`, adopters who copy the flag inherit a half-initialized manifest, and the gate would depend on a name instead of the manifest shape.

A second discarded option is to delete the scaffolds so this repository becomes `INITIALIZED`. That makes `./check.sh` green by destroying the patterns `export` and `/init` exist to ship.

## Risks and Edge Cases

- `test_soul_md.sh` T9 reads `.claude/agents/templates.md`. After `templates` leaves `subagents[]`, that stub is not regenerated. The test must render a temporary manifest that includes `templates`, then assert `## Agent Soul`. The source file check for R3 stays in `tests/test_portable_template.sh`.
- `test_steering.sh` skips injection checks when `steering[]` is empty. R30 requires a fixture so that skip is not the only coverage.
- `bootstrap.sh --all` is consultative. The parity test already runs it non-interactively. R7 must run in the same non-interactive way and must assert `agentic.json` is byte-stable, not only the adapters.
- `add-agent implementer --yes` copies the scaffold permission and `role_file`. Soul scaffolding must not overwrite an existing `SOUL.md`.
- Export copies `.agents/agentic.json` after it is FRESH. It must not copy a rendered `opencode.json` even if one exists in the working tree.
- Historical Spanish specs and `progress/progress.md` stay in this repository. They are not part of the portable surface and are not copied.
- `check.sh` in an exported tree warns about missing `tests/test_*.sh`. Those warnings already do not change the exit code. R26 asserts the exit code only.
