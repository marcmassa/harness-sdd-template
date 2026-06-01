# /init

Set up the Harness SDD framework for this project. The agent does the work;
the human supervises.

This is the **meta-workflow**: a one-time command that runs at the start of a
project. It shapes the manifest to the project, builds the sub-agents the
project needs, and drops the template scaffolds. After `/init`, the project
follows the per-feature SDD workflow (`/spec` → `/approve` → `/implement` →
`/done`).

## When to run

Run `/init` exactly once per project, right after copying the template, when
`./.agents/bootstrap.sh profile` shows:

- `subagents[]` is empty.
- `_template_subagents_examples[]` has scaffolds (7 by default).

If you have already run `/init` once and want to **add** a new sub-agent
later (e.g. the project adopted Terraform), do not re-run `/init`. Instead,
manually add a new entry to `subagents[]` in `.agents/agentic.json`.

## Steps

### 1 — Read the project

Understand what this project is. Read the relevant context:

- `README.md` — what the project does
- `feature_list.json` — current feature backlog (may be empty)
- The repository layout — detect the stack (Python / TypeScript / Terraform / Go / mixed)
- Any existing sub-agents in `.agents/subagents/` (not on disk yet — they live
  in the manifest)

Run `./.agents/bootstrap.sh profile` to see:
- The detected stack.
- The current `subagents[]` (probably `[]` after a clean install).
- The scaffolds available in `_template_subagents_examples[]` (7 by default:
  4 canonicals + 3 illustrative). Each carries an `_intent` field explaining
  how to use it.

### 2 — Decide which sub-agents the project needs

Based on the project layout, decide:

| Always (any project doing SDD) | `harness`, `spec-author`, `implementer`, `reviewer` |
| Python project | `implementer` → `python-implementer` (file_glob: `**/*.py`) |
| TypeScript / Node project | `implementer` → `typescript-implementer` (file_glob: `**/*.ts`, `**/*.tsx`) |
| Terraform / CloudFormation project | `cloud-architect` → `terraform-architect` (or kept as-is) |
| React / frontend project | `frontend-specialist` (often kept as-is) |
| Data / SQL / pipeline project | `data-engineer` → `sql-engineer` (or kept as-is) |
| Multi-stack (e.g. Python backend + React frontend) | One implementer per stack + `frontend-specialist` |

Always keep the 4 canonicals (renamed or as-is). Add illustrative agents only
if the project actually has that kind of work.

### 3 — Build each sub-agent

For each sub-agent the project needs, you have two options.

**Option A — Borrow as-is (quick try):**

```bash
./.agents/bootstrap.sh add-agent <name> --yes
```

This copies a scaffold from `_template_subagents_examples[]` to `subagents[]`,
sets `default: true`, and strips `_lifecycle` / `_intent` /
`applies_when`. Good for evaluation; not for production projects.

**Option B — Customize (recommended for production):**

Edit `.agents/agentic.json` by hand:

1. Copy an entry from `_template_subagents_examples[]` to `subagents[]`
   (top level).
2. Customize the fields:
   - `name` — your project's name (e.g. `python-implementer`,
     `terraform-architect`).
   - `description` — what this agent does in YOUR project.
   - `permission` — what files it may edit.
   - `role_file` — path to its `SUBAGENT.md` (defaults to
     `.agents/subagents/<name>/SUBAGENT.md`).
   - `applies_when` — when the agent is active (`file_glob` /
     `file_exists`). Required for opt-in agents; omit for always-on.
   - `default` — `true` for always-on, `false` for opt-in.
3. Remove the `_lifecycle` and `_intent` fields from the copied entry.
4. If you do not have a `SUBAGENT.md` for this agent, the renderer will
   auto-scaffold it from `.agents/subagents/agent-template/` on the next
   render. Customize the auto-scaffolded file to match your project's
   conventions.

Example: turn the `implementer` scaffold into a `python-implementer`:

```json
{
  "name": "python-implementer",
  "mode": "subagent",
  "description": "Implements Python code in src/ and tests/. Reads pyproject.toml and existing modules before writing. Does not modify the approved spec.",
  "role_file": ".agents/subagents/python-implementer/SUBAGENT.md",
  "default": true,
  "applies_when": {
    "file_glob": ["**/*.py", "pyproject.toml", "requirements.txt", "src/**", "tests/**"]
  },
  "permission": {
    "edit": {
      "specs/**": "deny",
      "feature_list.json": "ask",
      "**/*.py": "allow",
      "tests/**/*.py": "allow",
      "*": "ask"
    }
  }
}
```

### 4 — Drop the scaffolds

Once the project's sub-agents are in `subagents[]`:

```bash
./.agents/bootstrap.sh remove-examples --yes
```

This deletes `_template_subagents_examples[]` and `_template_lifecycle` from
`.agents/agentic.json`. Sub-agents already in `subagents[]` are NOT affected.
The CLI adapters are re-rendered automatically.

If you are in a non-TTY context and want to skip the confirmation, pass
`--yes`. The default for piped input is **N** (safe), so abort the command
with `Ctrl+C` if you need to.

### 5 — Verify

```bash
./check.sh
```

All checks must pass. If any check fails:

- Read the error carefully.
- Common issues:
  - `Adapter consistency: drift detected` → re-run `./.agents/bootstrap.sh opencode`.
  - `Subagent consistency: orphaned` → a `SUBAGENT.md` exists on disk but
    the agent is not in the manifest. Either re-add it to `subagents[]` or
    delete the directory.
  - `Spec validator` → the placeholder spec in `specs/templates/` may have
    an issue; check `check.sh --spec-only` for details.
- Fix the issue and re-run `./check.sh` until it is green.

### 6 — Report

Tell the human what you did. Be specific:

```
=== /init — report ===

Scaffolds borrowed (as-is):
  - implementer     -> added to subagents[]

Scaffolds customized:
  - harness         -> harness-onesait (role: SDD orchestrator for Onesait)
  - spec-author     -> kept as canonical
  - reviewer        -> kept as canonical
  - implementer     -> python-implementer (file_glob: **/*.py)
  - cloud-architect -> terraform-architect (file_glob: **/*.tf)

Scaffolds dropped:
  - 7 entries removed from _template_subagents_examples[]
  - _template_lifecycle removed from manifest

Final subagents[]:
  - harness-onesait
  - spec-author
  - python-implementer
  - terraform-architect
  - reviewer

./check.sh: ✅ All checks passed

The project is now shaped. Next: run /spec on a pending feature.
```

## Rules

- **Never** copy a scaffold to `subagents[]` without considering customization.
  Scaffolds are starting points, not final implementations.
- **Never** leave `_template_subagents_examples[]` in the manifest at the end
  of init. The whole point is to shape the manifest to the project.
- **Always** run `./check.sh` at the end. Init is not done until the
  environment is green.
- **Ask the human** if you are unsure which sub-agents the project needs.
  Default to a smaller set over a larger set — it is easy to add an agent
  later, hard to remove one in use.
- **Do not** add an agent you cannot justify. If the project has no SQL
  files, do not add a `data-engineer`.

## Related

- `AGENTS.md §0.5` — Project Profiling (the 3-stage lifecycle).
- `AGENTS.md §1` — Mandatory pre-task checklist (includes `./check.sh`).
- `bootstrap.sh profile` — see the current state (active + scaffolds).
- `bootstrap.sh add-agent <name>` — borrow a scaffold as-is.
- `bootstrap.sh remove-examples` — drop the scaffolds.
- `.agents/agentic.json#_template_lifecycle` — the lifecycle intent
  documented in the manifest.
