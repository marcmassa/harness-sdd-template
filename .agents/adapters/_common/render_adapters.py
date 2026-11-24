"""One render function per CLI adapter, and the RENDERERS registry.

Part of the renderer; the entry point and CLI are in render.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from render_core import render_template_str, write_file


def render_opencode(
    root: Path,
    manifest: dict[str, Any],
    ctx: dict[str, Any],
    check: bool,
) -> bool:
    cfg: dict[str, Any] = {
        "$schema": "https://opencode.ai/config.json",
        "instructions": list(ctx["instructions"]) + ctx["steering_global"],
        "skills": {"paths": ctx["skills_paths"]},
        "agent": {},
        "command": {},
    }
    for sa in ctx["subagents"]:
        soul_section = sa.get("soul_section", "")
        prompt = (
            f"You are `{sa['name']}`. Your complete role is defined in "
            f"`{sa['role_file']}` — read that file FIRST and follow it strictly."
        )
        if soul_section:
            prompt += soul_section
        agent_def: dict[str, Any] = {
            "mode": sa.get("mode", "subagent"),
            "description": sa["description"],
            "prompt": prompt,
        }
        if sa["name"] in ctx["steering_per_agent"]:
            agent_def["instructions"] = ctx["steering_per_agent"][sa["name"]]
        if sa["name"] == "implementer" and ctx["implementer_permission"]:
            agent_def["permission"] = ctx["implementer_permission"]
        elif "permission" in sa:
            agent_def["permission"] = sa["permission"]
        cfg["agent"][sa["name"]] = agent_def
    for cmd in ctx["commands"]:
        cfg["command"][cmd["name"]] = {
            "description": cmd["description"],
            "template": cmd["inline"],
        }
    if ctx.get("default_agent"):
        cfg["default_agent"] = ctx["default_agent"]
    out = root / "opencode.json"
    body = json.dumps(cfg, indent=2, ensure_ascii=False)
    return write_file(out, body + "\n", check, body + "\n")


def render_gemini(
    root: Path,
    manifest: dict[str, Any],
    ctx: dict[str, Any],
    check: bool,
) -> bool:
    adapter_dir = root / ".agents" / "adapters" / "gemini-cli"
    ok = True

    gemini_tmpl_path = adapter_dir / "GEMINI.md.tmpl"
    gemini_out = root / "GEMINI.md"
    if gemini_tmpl_path.exists():
        body = render_template_str(gemini_tmpl_path.read_text(), ctx)
        ok &= write_file(gemini_out, body, check, None)
    else:
        print(f"  WARN: {gemini_tmpl_path} not found, skipping GEMINI.md")

    cmds_tmpl_dir = adapter_dir / "gemini-commands"
    if cmds_tmpl_dir.exists():
        tmpl_files = list(cmds_tmpl_dir.glob("_template.*.tmpl"))
        if not tmpl_files:
            print(f"  WARN: no _template.*.tmpl in {cmds_tmpl_dir}")
        for tf in tmpl_files:
            ext = tf.name.replace("_template.", "").replace(".tmpl", "")
            for cmd in ctx["commands"]:
                cmd_ctx = {**ctx, "item": cmd, "command": cmd}
                body = render_template_str(tf.read_text(), cmd_ctx)
                out = root / ".gemini" / "commands" / f"{cmd['name']}.{ext}"
                ok &= write_file(out, body, check, None)
    return ok


def render_claude(
    root: Path,
    manifest: dict[str, Any],
    ctx: dict[str, Any],
    check: bool,
) -> bool:
    adapter_dir = root / ".agents" / "adapters" / "claude-code"
    ok = True

    claude_md_tmpl = adapter_dir / "CLAUDE.md.tmpl"
    if claude_md_tmpl.exists():
        body = render_template_str(claude_md_tmpl.read_text(), ctx)
        ok &= write_file(root / "CLAUDE.md", body, check, None)

    agents_tmpl_dir = adapter_dir / "claude-agents"
    if agents_tmpl_dir.exists():
        tf = next(iter(agents_tmpl_dir.glob("_template.*.tmpl")), None)
        if tf:
            for sa in ctx["subagents"]:
                sa_ctx = {**ctx, "item": sa, "subagent": sa}
                if sa["name"] == "implementer" and ctx["implementer_permission"]:
                    sa_ctx = {**sa_ctx, "permission": ctx["implementer_permission"]}
                body = render_template_str(tf.read_text(), sa_ctx)
                out = root / ".claude" / "agents" / f"{sa['name']}.md"
                ok &= write_file(out, body, check, None)

    cmds_tmpl_dir = adapter_dir / "claude-commands"
    if cmds_tmpl_dir.exists():
        tf = next(iter(cmds_tmpl_dir.glob("_template.*.tmpl")), None)
        if tf:
            for cmd in ctx["commands"]:
                cmd_ctx = {**ctx, "item": cmd, "command": cmd}
                body = render_template_str(tf.read_text(), cmd_ctx)
                out = root / ".claude" / "commands" / f"{cmd['name']}.md"
                ok &= write_file(out, body, check, None)

    settings_tmpl = adapter_dir / "claude-settings.json.tmpl"
    if settings_tmpl.exists():
        body = render_template_str(settings_tmpl.read_text(), ctx)
        ok &= write_file(root / ".claude" / "settings.json", body, check, None)

    return ok


def render_cursor(
    root: Path,
    manifest: dict[str, Any],
    ctx: dict[str, Any],
    check: bool,
) -> bool:
    adapter_dir = root / ".agents" / "adapters" / "cursor"
    ok = True

    rule_tmpl = adapter_dir / "cursor-rule.md.tmpl"
    if rule_tmpl.exists():
        body = render_template_str(rule_tmpl.read_text(), ctx)
        ok &= write_file(root / ".cursor" / "rules" / "harness-sdd.mdc", body, check, None)
    else:
        print(f"  WARN: {rule_tmpl} not found, skipping cursor rule")

    cmds_tmpl_dir = adapter_dir / "cursor-commands"
    if cmds_tmpl_dir.exists():
        tf = next(iter(cmds_tmpl_dir.glob("_template.*.tmpl")), None)
        if tf:
            for cmd in ctx["commands"]:
                cmd_ctx = {**ctx, "item": cmd, "command": cmd}
                body = render_template_str(tf.read_text(), cmd_ctx)
                out = root / ".cursor" / "commands" / f"harness-{cmd['name']}.md"
                ok &= write_file(out, body, check, None)

    # R4 evidence gate (verified 2026-10-22 against cursor.com/docs/hooks):
    # no Cursor hook event has a genuine SDD-transition equivalent, so
    # hooks.json is deliberately NOT emitted. The command bodies bridge
    # hooks/run-hooks.sh instead. Gap documented in the adapter README.
    return ok


def render_codex(
    root: Path,
    manifest: dict[str, Any],
    ctx: dict[str, Any],
    check: bool,
) -> bool:
    # R5/R6 evidence gate (verified 2026-10-22 against learn.chatgpt.com/codex
    # docs): AGENTS.md is the native entry point and .agents/skills is read
    # natively at REPO scope. Custom prompts are deprecated and user-level
    # only ("not shared through your repository"), so nothing is rendered.
    # Contract documented in .agents/adapters/codex/README.md.
    print("  codex: AGENTS.md native entry + .agents/skills repo-scope skills — no generated files required")
    return True


RENDERERS = {
    "opencode": render_opencode,
    "gemini-cli": render_gemini,
    "claude-code": render_claude,
    "cursor": render_cursor,
    "codex": render_codex,
}
