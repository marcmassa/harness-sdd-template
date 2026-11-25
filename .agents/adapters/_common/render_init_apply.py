"""Deterministic /init: build the project's sub-agents from the scaffolds in one step.

The agent passes only the decisions (CLIs, implementers, extra roles); this
module writes the manifest entries, role cards, and SOUL files. The wrapper in
.agents/lib/bootstrap-lifecycle.sh then drops the scaffolds, renders, and
validates. Part of the renderer; the entry point and CLI are in render.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import datetime
import os
import re

from render_core import detect_stack, matches_condition, save_manifest
from render_init import SCAFFOLD_ONLY_FIELDS
from render_scaffold import scaffold_subagent_role_file, scaffold_subagent_soul_file

CANONICAL_ORDER = ("harness", "spec-author", "implementer", "reviewer")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
DEFAULT_PERMISSION = {"edit": {"specs/**": "deny", "*": "ask"}}

# The shipped progress/current.md points at /init; once init is done it must not.
CURRENT_AFTER_INIT = (
    ("None. Run /init before starting a feature.", "None. Run /spec on a pending feature."),
    ("- [ ] Shape the manifest with /init", "- [x] Manifest shaped with init --apply"),
    ("Run /init.", "Run /spec."),
)

# What tells us a CLI is in use: its generated entry file, or the host's environment.
CLI_SIGNS = {
    "opencode": ("opencode.json", "OPENCODE"),
    "gemini-cli": ("GEMINI.md", "GEMINI_CLI"),
    "claude-code": (".claude/settings.json", "CLAUDECODE"),
    "cursor": (".cursor/rules/harness-sdd.mdc", "CURSOR_TRACE_ID"),
}
STACK_GLOBS = {"python": "**/*.py", "typescript": "**/*.ts,**/*.tsx", "go": "**/*.go",
               "terraform": "**/*.tf"}


class InitError(Exception):
    """The plan cannot be applied; the message says what to change."""


def _subagent_dir(name: str) -> str:
    return f".agents/subagents/{name}"


def _from_scaffold(scaffold: dict[str, Any]) -> dict[str, Any]:
    entry = {k: v for k, v in scaffold.items() if k not in SCAFFOLD_ONLY_FIELDS}
    entry.pop("applies_when", None)
    entry["default"] = True
    edit = dict((entry.get("permission") or {}).get("edit") or DEFAULT_PERMISSION["edit"])
    # Every role states its rule for the approved spec, ahead of any wildcard.
    entry["permission"] = {"edit": edit if "specs/**" in edit else {"specs/**": "deny", **edit}}
    entry["soul"] = f"{_subagent_dir(entry['name'])}/SOUL.md"
    return entry


def parse_implementer(spec: str) -> tuple[str, list[str]]:
    """`python=**/*.py,tests/**` -> ("python-implementer", ["**/*.py", "tests/**"])."""
    label, sep, globs_text = spec.partition("=")
    globs = [g.strip() for g in globs_text.split(",") if g.strip()]
    label = label.strip()
    if not sep or not globs or not NAME_RE.match(label):
        raise InitError(
            f"--implementer '{spec}' is not <language>=<glob>[,<glob>...] "
            "(for example python=**/*.py)"
        )
    name = label if label.endswith("implementer") else f"{label}-implementer"
    return name, globs


def _language_implementer(root: Path, base: dict[str, Any], name: str, globs: list[str]) -> dict[str, Any]:
    label = name[: -len("-implementer")] if name.endswith("-implementer") else name
    edit: dict[str, str] = {"specs/**": "deny", "feature_list.json": "ask"}
    for glob in globs:
        edit[glob] = "allow"
    edit["*"] = "ask"
    description = (
        f"Implements approved tasks in {label} code ({', '.join(globs)}), with a test "
        "for every requirement. Never edits the spec."
    )
    entry = {**base, "name": name, "description": description,
             "role_file": f"{_subagent_dir(name)}/SUBAGENT.md",
             "soul": f"{_subagent_dir(name)}/SOUL.md",
             "applies_when": {"file_glob": globs}, "permission": {"edit": edit}}
    for filename, key in (("SUBAGENT.md", "name"), ("SOUL.md", "agent")):
        source = root / _subagent_dir("implementer") / filename
        target = root / _subagent_dir(name) / filename
        if target.exists() or not source.is_file():
            continue
        text = re.sub(rf"^{key}:\s+implementer\s*$", f"{key}: {name}", source.read_text(encoding="utf-8"),
                      count=1, flags=re.MULTILINE)
        if filename == "SUBAGENT.md":
            text = re.sub(r'^description:\s*".*"\s*$', lambda _m: f'description: "{description}"',
                          text, count=1, flags=re.MULTILINE)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return entry


def plan_lines(root: Path, manifest: dict[str, Any]) -> list[str]:
    """A short, ready-to-confirm proposal for `init --apply`; reads only, writes nothing."""
    clis = [name for name, (path, env) in CLI_SIGNS.items()
            if (root / path).exists() or os.environ.get(env)]
    stack = [m.get("label", "?") for m in detect_stack(root, manifest)]
    optional = [s["name"] for s in manifest.get("_template_subagents_examples", []) or []
                if s.get("name") not in CANONICAL_ORDER and s.get("applies_when")
                and matches_condition(root, s["applies_when"])]
    command = "./.agents/bootstrap.sh init --apply --clis " + (",".join(clis) or "<cli>")
    command += "".join(f" --implementer '{label}={STACK_GLOBS[label]}'" for label in stack
                       if label in STACK_GLOBS)
    command += "".join(f" --add {name}" for name in optional)
    return [
        f"init plan | stack: {', '.join(stack) or 'not detected (ask)'} | CLIs seen: "
        f"{', '.join(clis) or 'none (ask)'} | optional roles matching: {', '.join(optional) or 'none'}",
        f"proposed: {command}",
        "Confirm with the human before running; adjust --clis, --implementer, --add to what they say.",
    ]


def apply_init(root: Path, manifest: dict[str, Any], clis: list[str], known_clis: list[str],
               implementers: list[str], extras: list[str], dry_run: bool = False) -> list[str]:
    """Shape a FRESH manifest. Returns the lines to print; raises InitError on a bad plan."""
    scaffolds = {s.get("name"): s for s in manifest.get("_template_subagents_examples", []) or []}
    if manifest.get("subagents"):
        raise InitError("subagents[] is not empty: init --apply only runs on a FRESH manifest. "
                        "Edit .agents/agentic.json and re-render instead.")
    if not clis:
        raise InitError(f"--clis is required (one or more of: {', '.join(known_clis)})")
    unknown = [c for c in clis if c not in known_clis]
    if unknown:
        raise InitError(f"unknown CLI(s): {', '.join(unknown)}. Known: {', '.join(known_clis)}. "
                        "For another CLI see .agents/BOOTSTRAP.md.")
    missing = [n for n in CANONICAL_ORDER if n not in scaffolds]
    if missing:
        raise InitError(f"canonical scaffold(s) missing from the manifest: {', '.join(missing)}")
    parsed = [parse_implementer(spec) for spec in implementers]
    bad_extras = [n for n in extras if n not in scaffolds or n in CANONICAL_ORDER]
    if bad_extras:
        available = [n for n in scaffolds if n not in CANONICAL_ORDER]
        raise InitError(f"--add: not an optional scaffold: {', '.join(bad_extras)}. "
                        f"Available: {', '.join(available) or 'none'}")
    names: list[str] = []
    for name in CANONICAL_ORDER:
        names += [n for n, _ in parsed] if name == "implementer" and parsed else [name]
    names += extras
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise InitError(f"duplicate sub-agent name(s): {', '.join(duplicates)}")

    plan = f"sub-agents: {', '.join(names)} | CLIs: {', '.join(clis)}"
    if dry_run:
        return [f"init --apply (dry run, nothing written): {plan}"]

    entries: list[dict[str, Any]] = []
    for name in CANONICAL_ORDER:
        base = _from_scaffold(scaffolds[name])
        if name == "implementer" and parsed:
            entries += [_language_implementer(root, base, n, globs) for n, globs in parsed]
        else:
            entries.append(base)
    entries += [_from_scaffold(scaffolds[name]) for name in extras]

    customize: list[str] = []
    for entry in entries:
        made_role = scaffold_subagent_role_file(root, entry)
        made_soul = scaffold_subagent_soul_file(root, entry)
        customize += [path for made, path in ((made_role, entry["role_file"]), (made_soul, entry["soul"])) if made]

    current = root / "progress" / "current.md"
    if current.is_file():
        text = current.read_text(encoding="utf-8")
        updated = text
        for old, new in CURRENT_AFTER_INIT:
            updated = updated.replace(old, new)
        updated = updated.replace("{YYYY-MM-DD}", datetime.date.today().isoformat(), 1)
        if updated != text:
            current.write_text(updated, encoding="utf-8")

    manifest["subagents"] = entries
    manifest["target_clis"] = clis
    save_manifest(root, manifest)
    lines = [f"init --apply: {plan}"]
    if customize:
        lines.append("placeholders to replace (generated from agent-template): " + ", ".join(customize))
    return lines
