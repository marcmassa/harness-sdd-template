"""Manifest loading, stack detection, template rendering, and file writing shared by every adapter.

Part of the renderer; the entry point and CLI are in render.py.
"""
from __future__ import annotations

from glob import glob
from pathlib import Path
from typing import Any
import json
import re


SIMPLE_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}")
LOOP_RE = re.compile(
    r"\{\{\s*LOOP:([A-Za-z_][A-Za-z0-9_]*)\s*\}\}(.*?)\{\{\s*ENDLOOP\s*\}\}",
    re.DOTALL,
)

CANONICAL_SUBAGENTS: set[str] = {
    "harness",
    "spec-author",
    "implementer",
    "reviewer",
}


def _active_default_agent(manifest: dict[str, Any]) -> str:
    """Return default_agent only when it names an active subagent."""
    requested = manifest.get("default_agent")
    if not requested:
        return ""
    active = {sa.get("name") for sa in manifest.get("subagents", [])}
    if requested not in active:
        return ""
    return str(requested)


def load_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / ".agents" / "agentic.json"
    with manifest_path.open() as f:
        return json.load(f)


def save_manifest(root: Path, manifest: dict[str, Any]) -> None:
    manifest_path = root / ".agents" / "agentic.json"
    with manifest_path.open("w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")


def matches_condition(root: Path, cond: dict[str, Any] | None) -> bool:
    """Evaluate a `when` or `applies_when` block.

    Supported keys (all must match, combined with AND):
      - file_exists: [path, ...]    — at least one path must exist
      - file_glob:   [pattern, ...] — at least one glob must yield results
    An empty/None condition is treated as a match.
    """
    if not cond:
        return True
    for key, patterns in cond.items():
        if not patterns:
            continue
        if key == "file_exists":
            if not any((root / p).exists() for p in patterns):
                return False
        elif key == "file_glob":
            if not any(glob(str(root / p), recursive=True) for p in patterns):
                return False
        else:
            return False
    return True


def detect_stack(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the project_detect rules against the project root."""
    return [r for r in manifest.get("project_detect", []) if matches_condition(root, r.get("when"))]


def merge_permissions(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two permission dicts. Override values win on conflict."""
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_permissions(out[k], v)
        else:
            out[k] = v
    return out


def _merge_unique_ordered(*lists: list[str]) -> list[str]:
    """Unión ordenada y deduplicada preservando la primera aparición.

    Usado para fusionar `manifest.skills.paths[]` con `extra_skills[]`
    (calculado desde `project_detect[].apply.add_skills[]`). El primer argumento
    tiene precedencia: si un path aparece en `manifest.skills.paths[]` y en
    `extra_skills[]`, se conserva la posición del primero.
    """
    seen: set[str] = set()
    out: list[str] = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return out


_PLACEHOLDER_RE = re.compile(r"^(\s*)\[([A-Za-z][A-Za-z0-9 _-]{0,30})\]\s*$")


def _sanitize_template_body(body: str) -> str:
    """Elimina líneas que son placeholders huérfanos del estilo '[Area 1]'.

    Un placeholder huérfano es una línea que:
      - Empieza con 0+ espacios
      - Sigue con '[' + (letra inicial) + (letras/dígitos/espacios/guiones_bajos/guiones, máx 30) + ']'
      - Termina con 0+ espacios
      - NO está dentro de un bloque de código ```...```

    Heurística: si la línea coincide con `^\\s*\\[[A-Za-z][A-Za-z0-9 _-]{0,30}\\]\\s*$`,
    se reemplaza por un comentario HTML indicando que se sustituye en producción.
    Conserva la indentación original.

    Por qué existe: el archivo `.agents/subagents/agent-template/SUBAGENT.md`
    contiene corchetes literales como `[Area 1]`, `[Step 1]` pensados como
    referencia humana. Si ese cuerpo se usa para scaffold de un sub-agent de
    producción, los placeholders se filtrarían. Esta función los reemplaza
    por `<!-- TODO: personalizar esta sección -->`.
    """
    sanitized: list[str] = []
    in_code_block = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            sanitized.append(line)
            continue
        if in_code_block:
            sanitized.append(line)
            continue
        m = _PLACEHOLDER_RE.match(line)
        if m:
            indent = m.group(1)
            sanitized.append(f"{indent}<!-- TODO: personalizar esta sección -->")
        else:
            sanitized.append(line)
    return "\n".join(sanitized) + "\n"


def load_soul_content(root: Path, sa: dict[str, Any]) -> str:
    """Load SOUL.md content for a subagent. Returns empty string if not found."""
    soul_path_str = sa.get("soul", f".agents/subagents/{sa['name']}/SOUL.md")
    soul_path = root / soul_path_str
    if soul_path.exists():
        return soul_path.read_text()
    return ""


def _strip_frontmatter(text: str) -> str:
    """Drop a leading `---` YAML block; the adapter writes its own."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def _inline_file(root: Path, relative: str, pointer: str) -> str:
    """Content of a canonical file for embedding in an adapter, or `pointer`.

    Embedding saves the agent one read (a full model turn) every time a
    command or role is invoked. The pointer is the fallback when the file is
    missing, so a render never fails on it.
    """
    path = root / relative if relative else None
    if path is None or not path.is_file():
        return pointer
    body = _strip_frontmatter(path.read_text(encoding="utf-8")).strip()
    return body or pointer


def build_context(
    root: Path, manifest: dict[str, Any], stack_matches: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build the substitution context from the manifest + stack detection."""
    implementer = next(
        (sa for sa in manifest["subagents"] if sa["name"] == "implementer"),
        None,
    )
    implementer_perm = implementer.get("permission", {}) if implementer else {}
    extra_skills: list[str] = []
    for m in stack_matches:
        for s in m.get("apply", {}).get("add_skills", []):
            extra_skills.append(s)
        overrides = m.get("apply", {}).get("implementer_permission_overrides", {})
        if overrides:
            implementer_perm = merge_permissions(implementer_perm, overrides)

    base_paths = manifest.get("skills", {}).get("paths", [])

    steering_global: list[str] = []
    steering_per_agent: dict[str, list[str]] = {}
    for s in manifest.get("steering", []):
        applies = s.get("applies_to", ["*"])
        file_path = s["file"]
        if "*" in applies:
            steering_global.append(file_path)
        else:
            for agent_name in applies:
                steering_per_agent.setdefault(agent_name, []).append(file_path)

    steering_all: list[str] = list(steering_global)
    for files in steering_per_agent.values():
        for f in files:
            if f not in steering_all:
                steering_all.append(f)

    enriched_subagents: list[dict[str, Any]] = []
    for sa in manifest.get("subagents", []):
        soul_content = load_soul_content(root, sa)
        soul_section = (
            f"\n## Agent Soul\n\n{soul_content}" if soul_content else ""
        )
        role_file = sa.get("role_file", "")
        role_inline = _inline_file(
            root, role_file,
            f"**Full role:** read `{role_file}` in full and follow it strictly.",
        )
        enriched_subagents.append({
            **sa, "soul_content": soul_content, "soul_section": soul_section,
            "role_inline": role_inline,
        })

    enriched_commands: list[dict[str, Any]] = []
    for cmd in manifest.get("commands", []):
        body_file = cmd.get("body_file", "")
        pointer = f"Read `{body_file}` and execute the workflow described there."
        inline = _inline_file(root, body_file, pointer)
        # A TOML literal string cannot contain its own delimiter.
        inline_toml = pointer if "'''" in inline else inline
        enriched_commands.append({**cmd, "inline": inline, "inline_toml": inline_toml})

    return {
        "manifest": manifest,
        "root": str(root),
        "default_agent": _active_default_agent(manifest),
        "instructions": manifest.get("instructions", []),
        "skills_paths": _merge_unique_ordered(base_paths, extra_skills),
        "subagents": enriched_subagents,
        "commands": enriched_commands,
        "implementer_permission": implementer_perm,
        "stack_labels": [m.get("label", "?") for m in stack_matches],
        "extra_skills": extra_skills,
        "steering_global": steering_global,
        "steering_per_agent": steering_per_agent,
        "steering_all": steering_all,
        "steering": manifest.get("steering", []),
    }


def render_template_str(template: str, ctx: dict[str, Any]) -> str:
    """Render `{{ VAR }}` and `{{ LOOP:key }}...{{ ENDLOOP }}` blocks."""

    def expand_loops(s: str, scope: dict[str, Any]) -> str:
        def replace(m: re.Match[str]) -> str:
            key = m.group(1)
            body = m.group(2)
            items = scope.get(key)
            if not isinstance(items, list):
                return ""
            rendered = []
            for item in items:
                inner_scope = {**scope, "item": item}
                rendered.append(expand_vars(body, inner_scope))
            return "".join(rendered)

        return LOOP_RE.sub(replace, s)

    def expand_vars(s: str, scope: dict[str, Any]) -> str:
        s = expand_loops(s, scope)

        def lookup(path: str, scope: dict[str, Any]) -> Any:
            cur: Any = scope
            for part in path.split("."):
                if isinstance(cur, dict):
                    cur = cur.get(part)
                else:
                    return None
            return cur

        def replace(m: re.Match[str]) -> str:
            path = m.group(1)
            val = lookup(path, scope)
            if val is None:
                return ""
            if isinstance(val, (dict, list)):
                return json.dumps(val, indent=2, ensure_ascii=False)
            return str(val)

        return SIMPLE_VAR_RE.sub(replace, s)

    return expand_vars(template, ctx)


def write_file(path: Path, content: str, check: bool, original: str | None) -> bool:
    """Write file. In check mode, diff against original and return True if equal/missing-ok."""
    if check:
        if not path.exists():
            print(f"  MISSING: {path}")
            return False
        existing = path.read_text()
        if existing != content:
            print(f"  DRIFT: {path}")
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  WROTE: {path}")
    return True
