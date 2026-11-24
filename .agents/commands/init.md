# /init

Shape the Harness SDD manifest for this project. Run once, right after
installing the template, when `./.agents/bootstrap.sh brief` shows
`init: FRESH`. One command does the work; the human confirms one plan (**ASK**).

## Steps

1. Learn the project, in one call:

   ```bash
   ./.agents/bootstrap.sh detect --clis; ./.agents/bootstrap.sh profile; ls
   ```

   Read the project's `README.md` only if the stack is still unclear. Do not
   guess the stack: if the language or framework is unclear, ask.

2. **ASK**: show the command you intend to run and wait for confirmation.

   - `--clis`: the CLIs the project uses (propose the ones reported `present`;
     default `opencode`). Never render a CLI the human did not confirm; it is
     written to `target_clis`. A CLI without an adapter: `.agents/BOOTSTRAP.md`.
   - `--implementer <language>=<glob>[,<glob>]`: one per language, never per
     file or feature. It becomes `<language>-implementer` with edit access to
     those globs. Omit it for a single generic `implementer`.
   - `--add <scaffold>`: an optional role (`cloud-architect`,
     `frontend-specialist`, `data-engineer`) only if the project has that
     work. Prefer fewer agents; adding one later is easy.

3. Apply it (add `--dry-run` first to preview the plan):

   ```bash
   ./.agents/bootstrap.sh init --apply --clis claude-code \
       --implementer 'python=**/*.py,tests/**'
   ```

   It builds `subagents[]` from the scaffolds (orchestrator, spec author,
   implementers, reviewer), writes each role card and `SOUL.md`, drops the
   sub-agent scaffolds, renders the adapters, and runs the completion gate.
   It only runs on a fresh manifest and changes nothing if the plan is invalid.

4. Run `./check.sh --quiet`. `/init` is done only when step 3 printed
   `init: COMPLETE` and this passes. Never report success otherwise.

5. If step 3 listed "placeholders to replace", fill those files with real
   content now (role card: mission, tasks, rules; `SOUL.md`: Identity,
   Decision Principles, Boundaries, Tone & Style), then run
   `./.agents/bootstrap.sh --all --yes`.

6. Report in a few lines: the CLIs, the sub-agents, and both results. Next
   step for the human: `/spec` on a pending feature.

## Optional tailoring

The generated roles work as they are. If the human wants them specific to the
project, edit a `description` in `.agents/agentic.json` (160 characters at
most), a role card, or a `SOUL.md`, then run `./.agents/bootstrap.sh --all --yes`.
Do this only when asked: it is the expensive part of setup.

## Manual path

For a layout `init --apply` cannot express, edit `subagents[]` by hand. Each
entry needs `name`, `mode` (`primary` for the orchestrator, else `subagent`),
`description`, `role_file` (`.agents/subagents/<name>/SUBAGENT.md`), and
`permission` (always with `"specs/**": "deny"` unless the role writes specs;
when unsure use `"ask"`). Never copy the scaffold-only fields `_lifecycle`,
`_intent`, `category`. Then run
`./.agents/bootstrap.sh remove-examples --yes` and
`./.agents/bootstrap.sh init --validate` until it exits 0.

Later additions use `add-agent`, `add-steering`, `add-hook`; see
`docs/framework-workflow.md` ("Template Installation Lifecycle").
