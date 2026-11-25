#!/usr/bin/env python3
"""render.py — Deterministic adapter renderer for Harness SDD.

Reads `.agents/agentic.json` (the canonical manifest), applies project-stack
detection via `project-detect.py`, and renders the native config files for the
requested CLI under `.agents/adapters/<cli>/`.

Usage:
    python3 render.py --cli <cli> --root <project_root> [--check]
    python3 render.py --profile --root <project_root> [--apply]
    python3 render.py --prune --root <project_root>
    python3 render.py --list-orphans --root <project_root>
    python3 render.py --detect-stack --root <project_root>
    python3 render.py --validate-init --root <project_root>
    python3 render.py --add-agent <name> --root <project_root>
    python3 render.py --remove-examples --root <project_root>

In `--check` mode, the renderer re-renders to a temp file and diffs against the
existing on-disk artifact. Exits 0 if identical, 1 if drift (or if the on-disk
file is missing).

In `--profile` mode, the renderer analyzes the project and prints recommended
add/keep/remove actions for each subagent. With `--apply`, it updates
`agentic.json` accordingly and scaffolds any missing `SUBAGENT.md` files.

Each adapter under `.agents/adapters/<cli>/` may contain:
  - `*.tmpl`           — single-output templates (substitution + LOOP blocks)
  - `_template.<ext>.tmpl` — per-item templates; the renderer produces one
                              output file per item in the relevant array
                              (e.g. one per subagent, one per command).

Template syntax (for MD/TOML/JSONC):
  - `{{ SIMPLE_VAR }}` — recursive substitution from the merged context dict.
  - `{{ LOOP:key }} ... {{ ENDLOOP }}` — iterate over the array at context[key],
    exposing each element as `{{ item.<field> }}`.

For native JSON output (opencode, claude settings), the renderer builds the
dict programmatically instead of templating, to guarantee valid JSON.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

# The implementation lives in the sibling render_*.py modules. Every name is
# re-exported here, so `import render` and `python3 render.py` keep working.
from render_adapters import (  # noqa: F401
    RENDERERS,
    render_claude,
    render_codex,
    render_cursor,
    render_gemini,
    render_opencode,
)
from render_core import (  # noqa: F401
    CANONICAL_SUBAGENTS,
    LOOP_RE,
    SIMPLE_VAR_RE,
    _PLACEHOLDER_RE,
    _active_default_agent,
    _merge_unique_ordered,
    _sanitize_template_body,
    build_context,
    detect_stack,
    load_manifest,
    load_soul_content,
    matches_condition,
    merge_permissions,
    render_template_str,
    save_manifest,
    write_file,
)
from render_export import (  # noqa: F401
    _ignore_agents,
    _write_consumer_state,
    export_template,
)
from render_init import (  # noqa: F401
    REQUIRED_SUBAGENT_FIELDS,
    SCAFFOLD_ONLY_FIELDS,
    validate_init,
)
from render_init_apply import InitError, apply_init, plan_lines  # noqa: F401
from render_scaffold import (  # noqa: F401
    _default_subagent_body,
    add_agent_from_example,
    apply_profile,
    auto_scaffold_all,
    list_orphans,
    profile_project,
    prune_orphans,
    remove_all_examples,
    scaffold_subagent_role_file,
    scaffold_subagent_soul_file,
    should_subagent_apply,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", help="CLI to render (e.g. opencode, gemini-cli, claude-code, cursor, codex)")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--check", action="store_true", help="Diff mode, no writes")
    parser.add_argument("--detect-stack", action="store_true", help="Print detected stack labels as JSON")
    parser.add_argument("--prune", action="store_true", help="Prune orphaned canonical subagent directories and exit")
    parser.add_argument("--list-orphans", action="store_true", help="Print names of orphaned canonical subagents and exit")
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Analyze the project and print recommended subagent actions (JSON). Use with --apply to update agentic.json and scaffold role files.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the profile recommendations (only valid with --profile).",
    )
    parser.add_argument(
        "--add-agent",
        metavar="NAME",
        help="Promote an entry from _template_subagents_examples[] to subagents[]. "
             "Scaffolds the SUBAGENT.md if missing and updates agentic.json.",
    )
    parser.add_argument(
        "--list-examples",
        action="store_true",
        help="List names of agents in _template_subagents_examples[] and exit.",
    )
    parser.add_argument(
        "--remove-examples",
        action="store_true",
        help="Drop the _template_subagents_examples[] and _template_lifecycle fields from agentic.json. "
             "Use this after the project's sub-agents are in place (see _template_lifecycle).",
    )
    parser.add_argument(
        "--validate-init",
        action="store_true",
        help="Validate the post-init manifest state. Exits 0 if subagents[] is shaped correctly, "
             "1 otherwise. Used by the /init completion gate (see .agents/commands/init.md).",
    )
    parser.add_argument(
        "--list-renderers",
        action="store_true",
        help="Print programmatic renderer names, one per line.",
    )
    parser.add_argument(
        "--export",
        metavar="DEST",
        help="Copy the portable template payload into DEST. Refuses a non-empty destination.",
    )
    parser.add_argument("--init-plan", action="store_true",
                        help="Print a proposed init --apply command for this project; writes nothing.")
    parser.add_argument("--init-apply", action="store_true",
                        help="Build subagents[] from the scaffolds in one step (see init --apply).")
    parser.add_argument("--clis", default="", help="Comma-separated CLIs for --init-apply.")
    parser.add_argument("--implementer", action="append", default=[],
                        help="<language>=<glob>[,<glob>...]; repeatable. Default: one generic implementer.")
    parser.add_argument("--add-example", action="append", default=[],
                        help="Optional scaffold to activate with --init-apply; repeatable.")
    parser.add_argument("--dry-run", action="store_true", help="With --init-apply: print the plan only.")
    args = parser.parse_args()

    if args.list_renderers:
        for name in RENDERERS:
            print(name)
        return 0

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root {root} does not exist", file=sys.stderr)
        return 1

    if args.export is not None:
        return export_template(root, Path(args.export))

    manifest = load_manifest(root)
    stack = detect_stack(root, manifest)

    if args.detect_stack:
        print(json.dumps([r.get("label", "?") for r in stack], indent=2))
        return 0

    if args.list_orphans:
        for name in list_orphans(root, manifest):
            print(name)
        return 0

    if args.prune:
        pruned = prune_orphans(root, manifest)
        if pruned:
            print(f"Pruned orphaned canonical subagents: {', '.join(pruned)}")
            print("  (These were removed from .agents/agentic.json and no longer active.)")
        else:
            print("No orphaned canonical subagents to prune.")
        return 0

    if args.profile:
        report = profile_project(root, manifest)
        if args.apply:
            actions = apply_profile(root, manifest, report)
            print(json.dumps({"report": report, "actions": actions}, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if args.list_examples:
        for ex in manifest.get("_template_subagents_examples", []):
            print(ex.get("name", "?"))
        return 0

    if args.add_agent:
        actions = add_agent_from_example(root, manifest, args.add_agent)
        for a in actions:
            print(a)
        if actions and actions[0].startswith("ERROR"):
            return 1
        return 0

    if args.remove_examples:
        actions = remove_all_examples(root, manifest)
        for a in actions:
            print(a)
        return 0

    if args.init_plan:
        print("\n".join(plan_lines(root, manifest)))
        return 0

    if args.init_apply:
        try:
            lines = apply_init(root, manifest, [c for c in args.clis.split(",") if c],
                               list(RENDERERS), args.implementer, args.add_example, args.dry_run)
        except InitError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print("\n".join(lines))
        return 0

    if args.validate_init:
        report = validate_init(root, manifest)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["ok"] else 1

    if not args.cli:
        print("ERROR: --cli is required (or pass --detect-stack / --prune / --list-orphans)", file=sys.stderr)
        return 1

    if args.cli not in RENDERERS:
        print(f"ERROR: no prebuilt renderer for CLI '{args.cli}'", file=sys.stderr)
        print(f"       Available: {', '.join(RENDERERS.keys())}", file=sys.stderr)
        print(f"       For unknown CLIs, read {root}/.agents/BOOTSTRAP.md", file=sys.stderr)
        return 1

    ctx = build_context(root, manifest, stack)
    if stack:
        print(f"Detected stack: {', '.join(r.get('label','?') for r in stack)}")
    if not args.check:
        scaffolded = auto_scaffold_all(root, manifest)
        if scaffolded:
            print(f"Auto-scaffolded missing role files: {', '.join(scaffolded)}")
        print(f"Rendering adapter for: {args.cli}")
    ok = RENDERERS[args.cli](root, manifest, ctx, args.check)
    if not ok:
        if args.check:
            print("DRIFT detected — run ./.agents/bootstrap.sh <cli> to regenerate")
        return 1
    if not args.check:
        pruned = prune_orphans(root, manifest)
        if pruned:
            print(f"Pruned orphaned canonical subagents: {', '.join(pruned)}")
            print("  (These were removed from .agents/agentic.json and no longer active.)")
        print(f"Done. Restart your CLI to activate Harness SDD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
