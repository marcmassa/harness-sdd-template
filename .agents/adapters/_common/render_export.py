"""Export of the portable template into a new project directory.

Part of the renderer; the entry point and CLI are in render.py.
"""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys


def _ignore_agents(dirpath: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__"}
    if Path(dirpath).name == "subagents":
        ignored.add("templates")
    return ignored


def _write_consumer_state(dest: Path) -> None:
    feature_list = {
        "project": "Harness SDD",
        "description": "Project using the Harness SDD template",
        "rules": {
            "maxConcurrent": 1,
            "requireSpec": True,
            "requireTests": True,
            "requireCheck": True,
            "validStatus": ["pending", "spec_ready", "in_progress", "done", "blocked"],
        },
        "features": [
            {
                "id": "FEAT-001",
                "name": "example-feature",
                "title": "Example feature",
                "description": "Replace this example with the first feature for this project.",
                "type": "feat",
                "status": "pending",
                "sdd": True,
                "priority": "P0",
                "agent": "implementer",
                "sprint": "S1",
            }
        ],
    }
    (dest / "feature_list.json").write_text(
        json.dumps(feature_list, indent=2, ensure_ascii=False) + "\n"
    )
    progress = dest / "progress"
    progress.mkdir(exist_ok=True)
    files = {
        "current.md": (
            "# Current Session State — {YYYY-MM-DD}\n\n"
            "## Active Task\n\n"
            "None. Run /init before starting a feature.\n\n"
            "## Progress\n\n"
            "- [ ] Shape the manifest with /init\n\n"
            "## Pending\n\n"
            "- First project feature\n\n"
            "## Blockers\n\n"
            "- None\n\n"
            "## Next Step\n\n"
            "Run /init.\n"
        ),
        "progress.md": (
            "# Progress Log\n\n"
            "Append-only chronological log of project progress.\n\n"
            "## Entry Format\n\n"
            "```\n"
            "{YYYY-MM-DD} | {type} | {brief title} | {affected files} | {next step}\n"
            "```\n"
        ),
        "backlog.md": (
            "# Backlog\n\n"
            "Prioritized list of pending features for the project.\n\n"
            "## P0 — Critical (current sprint)\n\n"
            "- [ ] First project feature\n"
        ),
        "decisions.md": (
            "# Decisions\n\n"
            "Append-only log of architectural decisions.\n"
        ),
        "handoff.md": (
            "# Handoff\n\n"
            "Notes for the next session. Empty until the first handoff.\n"
        ),
    }
    for name, body in files.items():
        (progress / name).write_text(body)


def export_template(root: Path, dest: Path) -> int:
    """Copy the portable template payload into dest. Refuse a non-empty dest."""
    dest = dest.expanduser()
    if not dest.is_absolute():
        dest = (Path.cwd() / dest).resolve()
    else:
        dest = dest.resolve()
    if dest == root or root in dest.parents:
        print("ERROR: destination must not be inside the source repository", file=sys.stderr)
        return 1
    if dest.exists() and any(dest.iterdir()):
        print(f"ERROR: destination {dest} exists and is not empty", file=sys.stderr)
        return 1
    if not dest.parent.exists():
        print(f"ERROR: destination parent {dest.parent} does not exist", file=sys.stderr)
        return 1

    root_files = (
        "AGENTS.md",
        "DESIGN.md",
        "README.md",
        "LICENSE",
        "SECURITY.md",
        "check.sh",
        ".gitignore",
        "docs/sdd.md",
    )
    hook_files = (
        "hooks/run-hooks.sh",
        "hooks/on-spec-created_validate.sh",
        "hooks/on-feature-done_notify.sh",
        "hooks/on-check-pass_ci.sh",
    )
    created = not dest.exists()
    try:
        dest.mkdir(exist_ok=True)
        for rel in root_files:
            src = root / rel
            if not src.is_file():
                raise FileNotFoundError(rel)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        shutil.copytree(root / ".agents", dest / ".agents", ignore=_ignore_agents, dirs_exist_ok=True)
        (dest / "specs").mkdir(exist_ok=True)
        shutil.copy2(root / "specs" / "README.md", dest / "specs" / "README.md")
        shutil.copytree(
            root / "specs" / "templates",
            dest / "specs" / "templates",
            dirs_exist_ok=True,
        )
        if (root / "examples").is_dir():
            shutil.copytree(root / "examples", dest / "examples", dirs_exist_ok=True)
        for rel in hook_files:
            src = root / rel
            if not src.is_file():
                raise FileNotFoundError(rel)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        steering_dest = dest / "steering"
        steering_dest.mkdir(exist_ok=True)
        for src in sorted((root / "steering").glob("*.md")):
            shutil.copy2(src, steering_dest / src.name)
        _write_consumer_state(dest)
    except Exception as exc:
        print(f"ERROR: export failed: {exc}", file=sys.stderr)
        if created and dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        return 1
    print(f"Exported portable template to {dest}")
    return 0
