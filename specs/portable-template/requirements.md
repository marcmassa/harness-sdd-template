# Requirements — Portable template

> Feature FEAT-006 from `feature_list.json`. Makes the Harness SDD template a portable artifact: a fresh checkout is `FRESH` and `./check.sh` exits 0, and `export` produces a consumer tree that does not carry this repository's history.
>
> Each requirement is written in strict EARS and is verifiable by at least one specific test.

## EARS Patterns

| Pattern | Syntax | When to use |
|--------|----------|---------------|
| **Ubiquitous** | `SHALL ...` | Always true, permanent condition |
| **Event** | `WHEN <event> SHALL ...` | Triggered by a specific event |
| **State** | `WHILE <state> SHALL ...` | While a condition remains true |
| **Optional** | `WHERE <option> SHALL ...` | Behavior varies based on configuration |
| **Unwanted** | `IF <condition> THEN SHALL ...` | Response to failures or edge cases |

## Requirements

### R1 — Shipping manifest is FRESH
- **Pattern:** Ubiquitous
- The shipping `.agents/agentic.json` SHALL have empty `subagents`, `steering`, and `hooks` arrays, retain `_template_subagents_examples`, `_template_steering_examples`, `_template_hooks_examples`, and `_template_lifecycle`, and omit `default_agent`.

### R2 — Maintainer agent is not active
- **Pattern:** Ubiquitous
- The name `templates` SHALL NOT appear in `subagents[]`.

### R3 — Maintainer soul stays in the framework repo
- **Pattern:** Ubiquitous
- The framework repository SHALL keep `.agents/subagents/templates/SOUL.md` with a non-empty `## Identity` section.

### R4 — No dangling default agent
- **Pattern:** Unwanted
- IF `default_agent` is absent or names an agent that is not in `subagents[]`, THEN `render_opencode` SHALL omit the `default_agent` key from `opencode.json`.

### R5 — Explicit default agent is preserved
- **Pattern:** State
- WHILE `default_agent` names an agent present in `subagents[]`, the renderer SHALL copy that value into `opencode.json` unchanged.

### R6 — Render does not activate scaffolds
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh` renders a CLI, it SHALL NOT append entries to `steering[]` or `hooks[]`.

### R7 — Consecutive renders are stable
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh --all` runs twice on an unchanged shipping manifest, the second run SHALL produce the same aggregate SHA256 of generated adapter files as the first and SHALL NOT modify `.agents/agentic.json`.

### R8 — Missing example files may be created, not registered
- **Pattern:** Optional
- WHERE a path named by `_template_steering_examples[]` or `_template_hooks_examples[]` does not exist, render MAY create that file and SHALL NOT add a matching entry to `steering[]` or `hooks[]`.

### R9 — Scaffold hook scripts are real examples
- **Pattern:** Ubiquitous
- `hooks/on-spec-created_validate.sh`, `hooks/on-feature-done_notify.sh`, and `hooks/on-check-pass_ci.sh` SHALL be non-empty, executable, and absent from `hooks[]`.

### R10 — Active hook integrity
- **Pattern:** Unwanted
- IF an entry in `hooks[]` points to a script that is missing, zero bytes, or not executable, THEN `./check.sh` SHALL exit non-zero.

### R11 — Scaffold hooks are not active hooks
- **Pattern:** State
- WHILE a hook script is referenced only from `_template_hooks_examples[]`, `./check.sh` SHALL NOT fail because that script is inactive.

### R12 — Active steering TODO gate
- **Pattern:** Unwanted
- IF a file listed in `steering[]` contains the substring `<!-- TODO`, THEN `./check.sh` SHALL exit non-zero.

### R13 — Scaffold steering is not gated
- **Pattern:** State
- WHILE a steering file is referenced only from `_template_steering_examples[]`, `./check.sh` SHALL NOT exit non-zero because that file contains `<!-- TODO` or is undeclared in `steering[]`.

### R14 — Stack checks follow files, not binaries
- **Pattern:** State
- WHILE no `*.tf` file exists under the project root outside `.git`, `./check.sh` SHALL NOT invoke `terraform` or `tflint`.

### R15 — Subagent warnings follow declarations
- **Pattern:** Ubiquitous
- `./check.sh` SHALL warn about a missing `SUBAGENT.md` only for a name declared in `subagents[]` or `_template_subagents_examples[]`.

### R16 — Adapter discovery includes programmatic CLIs
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh detect` runs in this repository, its adapter list SHALL include `opencode`, `gemini-cli`, and `claude-code`.

### R17 — Stack detection is labeled
- **Pattern:** Event
- WHEN `./.agents/bootstrap.sh detect` prints the project stack, it SHALL prefix that result with the label `Project stack:` and SHALL NOT print a bare `[]` as the adapter list.

### R18 — Export refuses a non-empty destination
- **Pattern:** Unwanted
- IF `./.agents/bootstrap.sh export <dest>` is given a destination that exists and contains any entry, THEN the command SHALL exit non-zero and SHALL NOT write into that destination.

### R19 — Export copies the portable payload
- **Pattern:** Event
- WHEN `export` succeeds, the destination SHALL contain `AGENTS.md`, `DESIGN.md`, `README.md`, `LICENSE`, `SECURITY.md`, `check.sh`, `docs/sdd.md`, `.gitignore`, `.agents/agentic.json`, `specs/README.md`, `specs/templates/`, `examples/`, `hooks/run-hooks.sh`, the three scaffold hook scripts, and `steering/`.

### R20 — Export omits framework history
- **Pattern:** Event
- WHEN `export` succeeds, the destination SHALL NOT contain `.git`, `.env`, `AUTHORITY`, `tests/`, `opencode.json`, `GEMINI.md`, `CLAUDE.md`, `.claude/`, `.gemini/`, `.agents/subagents/templates/`, or any directory under `specs/` other than `templates`.

### R21 — Export resets consumer state
- **Pattern:** Event
- WHEN `export` succeeds, the destination `feature_list.json` SHALL contain exactly one feature, with `"status": "pending"` and `"sdd": true`, and SHALL NOT contain the ids `FEAT-002`, `FEAT-003`, `FEAT-004`, `FEAT-005`, or `FEAT-006`.

### R22 — Export progress files are templates
- **Pattern:** Event
- WHEN `export` succeeds, `progress/current.md` in the destination SHALL contain the heading `# Current Session State` and SHALL NOT contain `FEAT-006`.

### R23 — Security policy is about this project
- **Pattern:** Ubiquitous
- `SECURITY.md` SHALL name Harness SDD Template and SHALL NOT contain `5.1.x` or `4.0.x`.

### R24 — Portable surface is English
- **Pattern:** Ubiquitous
- `SECURITY.md`, the three scaffold hook scripts, the bodies of files under `steering/`, the `description` fields of `_template_steering_examples[]` and `_template_hooks_examples[]`, and the `feature_list.json` written by `export` SHALL be English.

### R25 — Fresh framework checkout is green
- **Pattern:** State
- WHILE the shipping manifest is `FRESH` and no `*.tf` file exists, `./check.sh` in this repository SHALL exit 0.

### R26 — Exported tree is green before init
- **Pattern:** Event
- WHEN `export` succeeds, `./check.sh` run in the destination SHALL exit 0 without `/init`.

### R27 — Adopted tree can reach INITIALIZED
- **Pattern:** Event
- WHEN an exported tree runs `./.agents/bootstrap.sh add-agent implementer --yes` and then `./.agents/bootstrap.sh remove-examples --yes`, `init --validate` SHALL report state `INITIALIZED` and `./check.sh` SHALL exit 0.

### R28 — add-agent scaffolds SOUL.md
- **Pattern:** Event
- WHEN `add-agent` promotes a scaffold whose `SOUL.md` is missing, it SHALL create `.agents/subagents/<name>/SOUL.md` from `.agents/subagents/agent-template/SOUL.md` and set the frontmatter `agent:` value to `<name>`.

### R29 — Gemini does not invent a default
- **Pattern:** State
- WHILE `default_agent` is omitted, rendered `GEMINI.md` SHALL NOT contain the sentence `The harness role is the default`.

### R30 — Steering injection remains tested
- **Pattern:** Event
- WHEN a fixture manifest has a global steering file, the opencode renderer SHALL place that file path in `opencode.json` `instructions`.

## Traceability with Acceptance Criteria

| Acceptance Criterion | Covered by |
|----------------------|--------------|
| Shipping checkout is FRESH and `./check.sh` exits 0 | R1, R2, R14, R15, R25 |
| Render does not re-activate scaffolds | R6, R7, R8 |
| Active hooks and steering fail closed; scaffolds do not | R9, R10, R11, R12, R13 |
| `detect` lists opencode | R16, R17 |
| `export` is the supported copy path | R18, R19, R20, R21, R22, R23, R24, R26 |
| `/init` still reaches a green INITIALIZED tree | R27, R28 |
| Existing renderer contracts survive an empty active set | R3, R4, R5, R29, R30 |
