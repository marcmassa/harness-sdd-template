"""Sub-agent scaffolding, orphan pruning, project profiling, and the scaffold lifecycle.

Part of the renderer; the entry point and CLI are in render.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
import shutil

from render_core import (
    CANONICAL_SUBAGENTS,
    _sanitize_template_body,
    detect_stack,
    matches_condition,
    save_manifest,
)


def list_orphans(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Canonical subagent directories on disk that are not referenced anywhere
    in `agentic.json` (neither in `subagents[]` nor in
    `_template_subagents_examples[]`).

    A canonical directory is "expected" if it appears in either list:
      - `subagents[]`                      — the agent is active.
      - `_template_subagents_examples[]`   — the agent is a template scaffold.
    Returns the list of orphan names (not paths).
    """
    subagents_dir = root / ".agents" / "subagents"
    if not subagents_dir.exists():
        return []
    active = {sa["name"] for sa in manifest.get("subagents", [])}
    scaffolds = {sa["name"] for sa in manifest.get("_template_subagents_examples", [])}
    expected = active | scaffolds
    orphans: list[str] = []
    for sub_dir in sorted(subagents_dir.iterdir()):
        if not sub_dir.is_dir():
            continue
        name = sub_dir.name
        if name == "agent-template":
            continue
        if name in CANONICAL_SUBAGENTS and name not in expected:
            orphans.append(name)
    return orphans


def prune_orphans(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Remove canonical subagent directories that are not in `agentic.json`.
    Project-specific subagents are never auto-pruned.
    Returns the list of pruned names for logging."""
    pruned: list[str] = []
    for name in list_orphans(root, manifest):
        target = root / ".agents" / "subagents" / name
        if target.exists():
            shutil.rmtree(target)
            pruned.append(name)
    return pruned


def should_subagent_apply(root: Path, sa: dict[str, Any]) -> bool:
    """Decide whether a subagent entry should be active for this project.

    Resolution order:
      1. If `applies_when` matches → active.
      2. Else if `default: true` → active.
      3. Else → not active.
    """
    applies_when = sa.get("applies_when")
    if applies_when is not None and matches_condition(root, applies_when):
        return True
    return bool(sa.get("default", False))


def auto_scaffold_all(root: Path, manifest: dict[str, Any]) -> list[str]:
    """For every active subagent in the manifest, create SUBAGENT.md if missing.
    Returns the list of role files that were created."""
    created: list[str] = []
    for sa in manifest.get("subagents", []):
        if not should_subagent_apply(root, sa):
            continue
        if scaffold_subagent_role_file(root, sa):
            created.append(sa["role_file"])
    return created


def scaffold_subagent_role_file(root: Path, sa: dict[str, Any]) -> bool:
    """Create `.agents/subagents/<name>/SUBAGENT.md` from `agent-template/` if missing.
    Returns True if a file was created."""
    role_file = root / sa["role_file"]
    if role_file.exists():
        return False
    template_dir = root / ".agents" / "subagents" / "agent-template"
    if template_dir.exists():
        source = template_dir / "SUBAGENT.md"
        if source.exists():
            target_dir = role_file.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            body = source.read_text()
            body = _sanitize_template_body(body)
            body = re.sub(
                r"^name:\s+agent-template\s*$",
                f"name: {sa['name']}",
                body,
                count=1,
                flags=re.MULTILINE,
            )
            sa_desc = sa.get("description", "")
            if sa_desc:
                body = re.sub(
                    r'^description:\s*".*"\s*$',
                    f'description: "{sa_desc}"',
                    body,
                    count=1,
                    flags=re.MULTILINE,
                )
            role_file.write_text(body)
            return True
    target_dir = role_file.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    role_file.write_text(_default_subagent_body(sa))
    return True


def scaffold_subagent_soul_file(root: Path, sa: dict[str, Any]) -> bool:
    """Create `.agents/subagents/<name>/SOUL.md` from agent-template if missing."""
    name = sa["name"]
    target = root / ".agents" / "subagents" / name / "SOUL.md"
    if target.exists():
        return False
    source = root / ".agents" / "subagents" / "agent-template" / "SOUL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        body = source.read_text()
        body = re.sub(
            r"^agent:\s+agent-template\s*$",
            f"agent: {name}",
            body,
            count=1,
            flags=re.MULTILINE,
        )
        target.write_text(body)
    else:
        target.write_text(f"---\nagent: {name}\nversion: 1.0\n---\n\n## Identity\n\n{name}\n")
    return True


def _default_subagent_body(sa: dict[str, Any]) -> str:
    name = sa["name"]
    description = sa.get("description", name)
    mode = sa.get("mode", "subagent")
    perm_yaml = ""
    if "permission" in sa:
        perm_yaml = "\npermission:\n  edit: " + json.dumps(sa["permission"].get("edit", {})) + "\n"
    return (
        f"---\n"
        f"name: {name}\n"
        f"type: subagent\n"
        f"user-invocable: true\n"
        f"description: \"{description}\"\n"
        f"mode: {mode}\n"
        f"model-agnostic: true\n"
        f"{perm_yaml}"
        f"---\n\n"
        f"# {name} — Harness SDD sub-agent\n\n"
        f"> AUTOGENERATED from .agents/agentic.json. Edit `.agents/agentic.json` to change\n"
        f"> the metadata. Edit this file to customize the role's behavior.\n\n"
        f"## Mission\n\n"
        f"Describe the mission of `{name}`. What problem does it solve in this project?\n\n"
        f"## Main tasks\n\n"
        f"- [Customize this list with the concrete responsibilities of {name}]\n\n"
        f"## Available tools\n\n"
        f"- `AGENTS.md` — navigation map.\n"
        f"- `.agents/agentic.json` — canonical manifest.\n"
        f"- `./check.sh` — verification gateway.\n\n"
        f"## Style rules\n\n"
        f"- **Harness Compliance**: This agent operates under the **Harness SDD** framework.\n"
        f"- **Modular Skills**: Check `.agents/skills/` for specialized knowledge.\n\n"
        f"## Guidelines\n\n"
        f"- **Harness First**: Every action must be traceable and validated via `./check.sh`.\n"
        f"- **Skills Oriented**: Prefer skill instructions over reinvention.\n\n"
        f"## Integration with other sub-agents\n\n"
        f"- `architect-qa` writes the spec and runs the closing review.\n"
        f"- Implementer roles write the code; they never edit the approved spec.\n\n"
        f"## Workflow\n\n"
        f"1. Read this file in full to internalize the role.\n"
        f"2. Apply the role's behavior strictly.\n"
        f"3. Document any non-trivial decisions in `progress/decisions.md`.\n"
    )


def profile_project(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Analyze the project and report on the current subagent set.

    Returns a dict with:
      - detected_stack: list[str]
      - active:   list of {name, reason, action, role_exists}  (from subagents[])
      - examples_matching: list of {name, reason, role_file}   (from
                            _template_subagents_examples[] that match the project)
      - examples_idle:     list of {name, reason, role_file}   (examples that don't match)

    The `profile` subcommand is purely informational: the default install is
    already clean (illustrative agents live in `_template_subagents_examples[]`
    and are not in `subagents[]`). To opt-in to an example, use `add-agent`.
    """
    detected = [r.get("label", "?") for r in detect_stack(root, manifest)]
    active: list[dict[str, Any]] = []
    examples_matching: list[dict[str, Any]] = []
    examples_idle: list[dict[str, Any]] = []

    for sa in manifest.get("subagents", []):
        name = sa["name"]
        role_path = root / sa.get("role_file", f".agents/subagents/{name}/SUBAGENT.md")
        role_exists = role_path.exists()
        applies = should_subagent_apply(root, sa)
        applies_when = sa.get("applies_when")
        is_default = bool(sa.get("default", False))

        if applies:
            reason = (
                f"matches applies_when ({list(applies_when.keys())})"
                if applies_when is not None
                else "default: true"
            )
            action = "scaffold" if not role_exists else "keep"
            active.append({"name": name, "reason": reason, "action": action, "role_exists": role_exists})
        else:
            examples_idle.append(
                {
                    "name": name,
                    "reason": (
                        f"in subagents[] but applies_when "
                        f"({list(applies_when.keys()) if applies_when else []}) "
                        f"does not match and default: {is_default}"
                    ),
                    "role_file": sa.get("role_file"),
                    "source": "subagents",
                }
            )

    for ex in manifest.get("_template_subagents_examples", []):
        name = ex["name"]
        role_path = root / ex.get("role_file", f".agents/subagents/{name}/SUBAGENT.md")
        applies_when = ex.get("applies_when")
        if applies_when and matches_condition(root, applies_when):
            examples_matching.append(
                {
                    "name": name,
                    "reason": f"matches applies_when ({list(applies_when.keys())})",
                    "role_file": ex.get("role_file"),
                    "source": "_template_subagents_examples",
                }
            )
        else:
            examples_idle.append(
                {
                    "name": name,
                    "reason": "template example; not in active manifest",
                    "role_file": ex.get("role_file"),
                    "source": "_template_subagents_examples",
                }
            )

    return {
        "detected_stack": detected,
        "active": active,
        "examples_matching": examples_matching,
        "examples_idle": examples_idle,
    }


def apply_profile(root: Path, manifest: dict[str, Any], report: dict[str, Any]) -> list[str]:
    """Apply the auto-scaffold part of the profile.

    In the clean-install model, `subagents[]` only contains canonical agents
    that should always be active. The `apply` step:
      - Scaffolds any missing `SUBAGENT.md` for active sub-agents.
      - Does NOT remove anything from `subagents[]` (illustrative agents live
        in `_template_subagents_examples[]` and are not in the active set).
      - Does NOT auto-promote examples (use `add-agent` for that).

    Returns a list of human-readable actions taken (for logging).
    """
    actions: list[str] = []
    for entry in report.get("active", []):
        if entry["action"] == "scaffold":
            sa = next((s for s in manifest["subagents"] if s["name"] == entry["name"]), None)
            if sa and scaffold_subagent_role_file(root, sa):
                actions.append(f"scaffolded {sa['role_file']}")
    return actions


def add_agent_from_example(root: Path, manifest: dict[str, Any], name: str) -> list[str]:
    """Promote an entry from `_template_subagents_examples[]` to `subagents[]`.

    The promoted agent gets `default: true` so it stays active regardless of
    `applies_when`. (Use the bootstrap.sh wrapper to confirm with the user.)
    Returns a list of actions taken.
    """
    examples = manifest.get("_template_subagents_examples", [])
    ex = next((e for e in examples if e.get("name") == name), None)
    if ex is None:
        return [f"ERROR: '{name}' not found in _template_subagents_examples[]"]

    if any(s.get("name") == name for s in manifest.get("subagents", [])):
        return [f"'{name}' is already in subagents[] (no change)"]

    new_sa = dict(ex)
    new_sa["default"] = True
    new_sa.pop("applies_when", None)
    for field in ("_lifecycle", "_intent", "category"):
        new_sa.pop(field, None)
    manifest.setdefault("subagents", []).append(new_sa)
    manifest["_template_subagents_examples"] = [e for e in examples if e.get("name") != name]

    actions: list[str] = []
    if scaffold_subagent_role_file(root, new_sa):
        actions.append(f"scaffolded {new_sa['role_file']}")
    if scaffold_subagent_soul_file(root, new_sa):
        actions.append(f"scaffolded .agents/subagents/{name}/SOUL.md")
    save_manifest(root, manifest)
    actions.insert(0, "saved .agents/agentic.json")
    actions.insert(0, f"promoted '{name}' from _template_subagents_examples to subagents[]")
    return actions


def remove_all_examples(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Drop the `_template_subagents_examples[]` (and `_template_lifecycle`) from the manifest.

    This is the third stage of the scaffold lifecycle (see `_template_lifecycle`
    in agentic.json). Call this after the project's sub-agents are in place.
    Returns a list of actions taken.
    """
    actions: list[str] = []
    n = len(manifest.get("_template_subagents_examples", []))
    if "_template_subagents_examples" in manifest:
        manifest.pop("_template_subagents_examples")
        actions.append(f"removed _template_subagents_examples[] ({n} scaffold entries)")
    if "_template_lifecycle" in manifest:
        manifest.pop("_template_lifecycle")
        actions.append("removed _template_lifecycle")
    if not actions:
        return ["nothing to remove — the manifest is already clean of template scaffolds"]
    save_manifest(root, manifest)
    actions.insert(0, "saved .agents/agentic.json")
    return actions
