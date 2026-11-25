# /init

Shape the Harness SDD manifest for this project. Run once, right after
installing the template, when `./.agents/bootstrap.sh brief` shows
`init: FRESH`. One command does the work; the human confirms one plan (**ASK**).

## Steps

1. Get the proposal:

   ```bash
   ./.agents/bootstrap.sh init --plan
   ```

   It prints the detected stack, the CLIs seen, and a ready `init --apply`
   command. Do not guess: if the stack or the CLI is "ask", ask the human
   (`./.agents/bootstrap.sh detect --clis` shows the raw detection).

2. **ASK**: show the command you intend to run and wait for confirmation.

   - `--clis`: only CLIs the human confirmed; the list is written to
     `target_clis`. A CLI without an adapter: `.agents/BOOTSTRAP.md`.
   - `--implementer <language>=<glob>[,<glob>]`: one per language, never per
     file or feature. It becomes `<language>-implementer` with edit access to
     those globs. Omit it for a single generic `implementer`.
   - The default is two kinds of role: `architect-qa` (routes, writes the
     spec, runs the closing review, never codes) and the implementers.
   - `--add <scaffold>`: an optional role only if the project has that work:
     `frontend-specialist` (front-end developer and designer),
     `cloud-architect`, `data-engineer`, or `harness` / `spec-author` /
     `reviewer` to split those duties out of `architect-qa`. Prefer fewer
     roles; adding one later is easy.

3. Run the confirmed command (`--dry-run` previews it without writing):

   ```bash
   ./.agents/bootstrap.sh init --apply --clis <cli>[,<cli>] [--implementer '<language>=<glob>']...
   ```

   It builds `subagents[]` from the scaffolds (orchestrator, spec author,
   implementers, reviewer), writes each role card and `SOUL.md`, drops the
   sub-agent scaffolds, renders the adapters, and runs the completion gate.
   It only runs on a fresh manifest and changes nothing if the plan is invalid.

4. Run `./check.sh --quiet`. `/init` is done only when step 3 printed
   `init: COMPLETE` and this passes. Never report success otherwise.

5. Only if step 3 printed a "placeholders to replace" line (it prints none
   when nothing needs filling), fill those files with real
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
