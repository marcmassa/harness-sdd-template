# Progress Log

Append-only chronological log of project progress.

## Entry Format

```
{YYYY-MM-DD} | {type} | {brief title} | {affected files} | {next step}
```

Types: `feat`, `fix`, `refactor`, `chore`, `test`, `docs`, `hardening`, `migration`

---

## 2026-06-17 | feat | FEAT-004 hooks — sistema de hooks del ciclo de vida SDD | `.agents/agentic.json` `hooks/` `.agents/bootstrap.sh` `.agents/commands/{spec,approve,implement,done,check}.md` `tests/test_hooks.sh` `check.sh` | none

**Resumen**: Añade un sistema de hooks CLI-agnóstico con 8 puntos del ciclo de vida
SDD (`on_spec_created`, `on_spec_approved`, `on_implementation_start`/`complete`,
`on_review_start`/`complete`, `on_feature_done`, `on_check_pass`). Los hooks son
scripts shell en `hooks/` con política de fallo configurable (`warn`/`error`/`ignore`).
Incluye runner `hooks/run-hooks.sh`, 3 scaffolds de ejemplo, integración con los 5
comandos slash, comandos bootstrap `add-hook`/`remove-hook`, y validación en
`check.sh` + test automatizado.

**Componentes implementados**:
- **Schema**: `hooks: [...]` y `_template_hooks_examples: [...]` en `agentic.json`.
  Cada entrada tiene `event`, `script`, `description`, `on_failure`.
- **Runner**: `hooks/run-hooks.sh` — ejecuta hooks secuencialmente por evento,
  pasa contexto vía variables de entorno (`HOOK_EVENT`, `ROOT_DIR`, `FEATURE_ID`,
  `FEATURE_NAME`, `AGENT_NAME`), aplica política `on_failure` (warn/error/ignore).
- **Scaffolds**: 3 hooks de ejemplo — `on-spec-created_validate.sh` (valida estructura
  de spec), `on-feature-done_notify.sh` (resumen de feature), `on-check-pass_ci.sh`
  (timestamp CI).
- **Comandos slash**: hooks integrados en `/spec` (on_spec_created), `/approve`
  (on_spec_approved), `/implement` (on_implementation_start/complete), `/done`
  (on_review_start/complete + on_feature_done), `/check` (on_check_pass).
- **Bootstrap**: comandos `add-hook` (--event, --script, --description, --on-failure),
  `remove-hook`, `--list-hooks`.
- **Validación**: sección «Hooks Validation» en `check.sh` (verifica runner, scripts,
  eventos no estándar). Test `test_hooks.sh` con 4 aserciones.

**Cobertura R↔T↔test**: 16/16 R<n>s cubiertos (ver `specs/hooks/tasks.md`).

**Validación**: `./check.sh` — Hooks Validation ✅, test_hooks ✅, 3 hooks activos,
runner funcional. Init validation en PARTIAL (scaffolds pendientes de
`remove-examples`, fuera del scope de este feature).

---

**Resumen**: Formaliza el concepto de «steering files» (archivos que dirigen el
comportamiento del agente) como ciudadanos de primera clase en `agentic.json`.
Añade campo `steering[]` con `applies_to` (global `["*"]` o per-agent), directorio
`steering/` con YAML frontmatter, scaffolding con `_template_steering_examples[]`,
comandos bootstrap `add-steering`/`remove-steering`, extensión del renderer para
mapear steering files al `instructions[]` de cada CLI, y validación en `check.sh`
+ test automatizado. Cero breaking changes.

**Componentes implementados**:
- **Schema**: `steering: []` y `_template_steering_examples: [...]` en `agentic.json`.
  Cada entrada tiene `name`, `file`, `description`, `applies_to`.
- **Directorio**: `steering/` con 2 ejemplos (`global-conventions.md`,
  `implementer-patterns.md`) con YAML frontmatter y placeholders `<!-- TODO -->`.
- **Renderer**: `build_context` clasifica en `steering_global` y `steering_per_agent`.
  `render_opencode` añade steering global a `instructions[]` y per-agent a
  `agent.<name>.instructions[]`. `steering_all` disponible para Gemini y Claude.
- **Templates Gemini/Claude**: sección «Steering Files» con LOOP sobre `steering`.
- **Bootstrap**: comandos `add-steering` (crea archivo + registra en manifest),
  `remove-steering` (elimina del manifest, preserva archivo en disco),
  `--list-steering`.
- **Validación**: sección «Steering Validation» en `check.sh` (verifica existencia
  de archivos, YAML frontmatter, archivos no declarados).
- **Test**: `tests/test_steering.sh` con 3 aserciones (global en instructions,
  existencia en disco, YAML frontmatter válido).

**Cobertura R↔T↔test**: 16/16 R<n>s cubiertos (ver `specs/steering/tasks.md`).

**Validación**: `./check.sh` — Steering Validation ✅, test_steering ✅,
adapter consistency ✅. Init validation en PARTIAL (scaffolds pendientes de
`remove-examples`, fuera del scope de este feature).

---

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
