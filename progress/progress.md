# Progress Log

Append-only chronological log of project progress.

## Entry Format

```
{YYYY-MM-DD} | {type} | {brief title} | {affected files} | {next step}
```

Types: `feat`, `fix`, `refactor`, `chore`, `test`, `docs`, `hardening`, `migration`

---

## 2026-06-10 | hardening | FEAT-002 renderer-skills-fusion-and-parity-tests | `.agents/adapters/_common/render.py` `.agents/BOOTSTRAP.md` `CLAUDE.md` `tests/test_cli_adapter_parity.sh` `tests/test_agent_template_placeholders.sh` `check.sh` | none

**Resumen**: Refactor mínimo del CLI-agnostic layer. Fusiona las dos fuentes
de `skills_paths` (manifest base + `extra_skills` calculado por stack detect),
elimina el `opencode.json.tmpl` vestigial, sanea el `agent-template` con
sanitización + test, y cierra el principio de determinismo del framework con
dos tests genéricos (paridad y placeholders). Cero breaking changes al schema
de `agentic.json`.

**Bugs arreglados**:
- **R1 (extra_skills)**: `extra_skills` calculado en `build_context` ahora se
  fusiona con `manifest.skills.paths[]` mediante `_merge_unique_ordered`,
  preservando orden y eliminando duplicados. Antes el `add_skills` del
  `project_detect` no tenía efecto en el render.
- **R2 (vestigio)**: `opencode.json.tmpl` (≈50 líneas no leídas) eliminado;
  la fuente de verdad es `render_opencode()` en `render.py`. Documentado en
  `.agents/BOOTSTRAP.md`.
- **R3 (placeholders)**: `agent-template/SUBAGENT.md` ahora se sanea antes
  del scaffold mediante `_sanitize_template_body`, que reemplaza corchetes
  huérfanos del estilo `[Area 1]` por `<!-- TODO: ... -->`. Test de no-filtración
  añadido.

**Tests añadidos**:
- `tests/test_cli_adapter_parity.sh` (ejecutable, genérico): 5 aserciones que
  verifican SHA256 determinista, render de los 3 CLIs, skills_paths base,
  skills de add_skills[] cuando hay stack detectado, y unit test del helper
  `_merge_unique_ordered`.
- `tests/test_agent_template_placeholders.sh` (ejecutable, genérico): detecta
  placeholders huérfanos en `agent-template/SUBAGENT.md` fuera de bloques de
  código. Skip con exit 0 si el template no existe.

**Cobertura R↔T↔test**: 17/17 R<n>s cubiertos (ver `specs/renderer-skills-fusion-and-parity-tests/tasks.md`).

**Validación**: `./check.sh` exit 0, ambos tests pasan. FEAT-002 → `done`.

---

*[Entries are added at the top of the file, in reverse chronological order]*
