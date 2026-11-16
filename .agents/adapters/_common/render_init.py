"""Objective completion gate for /init.

Part of the renderer; the entry point and CLI are in render.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any



# Fields that belong to scaffolds (_template_subagents_examples[]) and MUST NOT
# appear in active sub-agents (subagents[]). If any of these leak into a
# subagents[] entry, the init validation gate rejects the manifest.
SCAFFOLD_ONLY_FIELDS = ("_lifecycle", "_intent", "category")

# Fields REQUIRED in every active sub-agent. The init gate rejects entries
# missing any of these.
REQUIRED_SUBAGENT_FIELDS = ("name", "mode", "description", "role_file", "permission")


def validate_init(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Objective completion gate for the /init workflow.

    Returns a dict with:
        state: one of "FRESH" | "PARTIAL" | "INITIALIZED" | "EMPTY" | "BROKEN"
        ok: True iff state == "INITIALIZED" and there are no schema errors
        errors: list of human-readable error strings (empty if ok)
        warnings: list of human-readable warning strings (empty if perfect)
        summary: one-line human summary

    Exit code from main(): 0 if ok, 1 otherwise.
    """
    subagents: list[dict[str, Any]] = manifest.get("subagents", []) or []
    scaffolds: list[dict[str, Any]] = manifest.get("_template_subagents_examples", []) or []
    has_lifecycle = "_template_lifecycle" in manifest
    n_active = len(subagents)
    n_scaffolds = len(scaffolds)

    if n_active == 0 and n_scaffolds > 0:
        state = "FRESH"
    elif n_active > 0 and n_scaffolds > 0:
        state = "PARTIAL"
    elif n_active > 0 and n_scaffolds == 0:
        state = "INITIALIZED"
    else:
        state = "EMPTY"

    errors: list[str] = []
    warnings: list[str] = []

    if state == "EMPTY":
        errors.append(
            "Both subagents[] and _template_subagents_examples[] are empty. "
            "The install is in a broken state — restore at least one of them."
        )

    if state == "FRESH":
        errors.append(
            "Init has not started: subagents[] is empty. "
            "Run /init to shape the manifest to this project."
        )
        return {
            "state": state,
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "summary": f"State: {state} — init needed",
        }

    if state == "PARTIAL":
        errors.append(
            f"Init is in progress: subagents[] has {n_active} entries "
            f"but {n_scaffolds} scaffolds remain. "
            f"Run `./.agents/bootstrap.sh remove-examples --yes` to drop the scaffolds."
        )
        if has_lifecycle:
            errors.append(
                "_template_lifecycle is still in the manifest. "
                "It will be removed by `remove-examples`."
            )

    if state in ("PARTIAL", "INITIALIZED"):
        if has_lifecycle and state == "INITIALIZED":
            errors.append(
                "_template_lifecycle is still in the manifest but no scaffolds remain. "
                "Run `./.agents/bootstrap.sh remove-examples --yes` to clean up."
            )

        for i, sa in enumerate(subagents):
            name = sa.get("name", f"<index {i}>")
            for field in REQUIRED_SUBAGENT_FIELDS:
                if field not in sa or not sa[field]:
                    errors.append(
                        f"subagents[{i}] ({name}): missing required field '{field}'"
                    )
            for field in SCAFFOLD_ONLY_FIELDS:
                if field in sa:
                    errors.append(
                        f"subagents[{i}] ({name}): has scaffold-only field '{field}' — "
                        f"this field belongs to _template_subagents_examples[] only. Remove it."
                    )
            mode = sa.get("mode")
            if mode is not None and mode not in ("primary", "subagent"):
                errors.append(
                    f"subagents[{i}] ({name}): mode='{mode}' is invalid (must be 'primary' or 'subagent')"
                )
            role_file = sa.get("role_file", "")
            if role_file and not (root / role_file).is_file():
                errors.append(
                    f"subagents[{i}] ({name}): role_file '{role_file}' does not exist on disk"
                )
            perm = sa.get("permission", {})
            if isinstance(perm, dict) and "edit" not in perm:
                errors.append(
                    f"subagents[{i}] ({name}): permission is missing the 'edit' mapping"
                )
            elif isinstance(perm, dict) and isinstance(perm.get("edit"), dict):
                if "specs/**" not in perm["edit"] and "specs" not in str(perm["edit"]):
                    warnings.append(
                        f"subagents[{i}] ({name}): permission has no 'specs/**' rule — "
                        f"sub-agents should NOT edit the approved spec."
                    )

    ok = state == "INITIALIZED" and not errors
    if ok:
        summary = (
            f"State: INITIALIZED — {n_active} project-specific sub-agent(s), "
            f"no scaffolds, no scaffold-only field leaks. /init is complete."
        )
    else:
        summary = f"State: {state} — {len(errors)} error(s), {len(warnings)} warning(s). /init is NOT complete."

    return {
        "state": state,
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
        "active_count": n_active,
        "scaffold_count": n_scaffolds,
    }
