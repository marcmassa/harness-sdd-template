# Tareas — steering

> Pasos discretos en orden para FEAT-003. Cada tarea referencia los `R<n>` que cubre. El implementador marca `[x]` al completar.

## BLOQUE 1 — Schema y scaffolding (R1, R2, R5, R6, R7, R13, R14)

- [x] **T1** — Añadir `steering: []` y `_template_steering_examples: [...]` (con 2 entradas scaffold) a `.agents/agentic.json`. El campo `steering` empieza vacío. Los scaffolds incluyen `global-conventions` e `implementer-patterns` con `_lifecycle: "scaffold"`. _(R1, R7, R13)_

- [x] **T2** — Crear `steering/global-conventions.md` con YAML frontmatter (`name`, `description`, `applies_to: ["*"]`) y secciones placeholder (`<!-- TODO: ... -->`). _(R2, R5)_

- [x] **T3** — Crear `steering/implementer-patterns.md` con YAML frontmatter (`name`, `description`, `applies_to: ["implementer"]`) y secciones placeholder. _(R2, R6)_

- [x] **T4** — Crear `specs/templates/steering.md` con la plantilla base (estructura YAML frontmatter + secciones sugeridas: Contexto, Reglas, Anti-patrones, Referencias). _(R14)_

## BLOQUE 2 — Extensión del renderer (R3, R4, R11)

- [x] **T5** — En `.agents/adapters/_common/render.py`, modificar `build_context` para leer `manifest.get("steering", [])`, clasificar entradas en `steering_global` (applies_to contiene `"*"`) y `steering_per_agent` (applies_to lista nombres de agentes), y añadir ambos al dict de retorno. _(R3, R4)_

- [x] **T6** — En `render_opencode`, tras construir `cfg["instructions"]`, concatenar `ctx["steering_global"]`. Para cada agente en `ctx["steering_per_agent"]`, añadir `instructions` al objeto `cfg["agent"][<name>]` con los steering files correspondientes. _(R11)_

- [x] **T7** — En `build_context`, añadir `steering_all` (unión de global + per-agent) para que los adapters de gemini y claude (que solo tienen `instructions` global) incluyan todos los steering files. Verificar que `render_gemini` y `render_claude` usan `steering_all` en lugar de `steering_global`. _(R3)_

## BLOQUE 3 — Comandos bootstrap (R8, R9)

- [x] **T8** — Añadir `add_steering_run()` a `.agents/bootstrap.sh` que acepte `<name>`, `--description`, `--applies-to` (coma-separado, default `*`). Crea `steering/` si no existe, copia el template de `specs/templates/steering.md` con frontmatter personalizado, y añade entrada a `agentic.json#steering[]`. Usar `python3` para manipular el JSON del manifest. _(R8)_

- [x] **T9** — Añadir `remove_steering_run()` a `.agents/bootstrap.sh` que acepte `<name>`. Elimina la entrada de `agentic.json#steering[]` con ese nombre usando `python3`. No elimina el archivo en disco. _(R9)_

## BLOQUE 4 — Validación y tests (R10, R12, R15)

- [x] **T10** — En `check.sh`, añadir sección «Steering Validation» que ejecute un script Python inline para: (a) verificar que los archivos en `steering[].file` existen; (b) verificar YAML frontmatter válido en cada uno; (c) advertir sobre archivos en `steering/` no declarados. Usar ⚠️ para warnings (el steering es opcional). _(R10)_

- [x] **T11** — Crear `tests/test_steering.sh` ejecutable con 3 aserciones: (a) steering files globales aparecen en `opencode.json#instructions[]`; (b) todos los steering files declarados existen en disco; (c) cada steering file tiene YAML frontmatter con `name` y `description`. _(R15)_

- [x] **T12** — En `AGENTS.md` §2 (Repository Map), añadir entrada: `steering/` → «Archivos que dirigen el comportamiento de los agentes (global y por rol). Declarados en `agentic.json#steering[]`.» _(R12)_

## BLOQUE 5 — Integración y cierre (R16)

- [x] **T13** — Ejecutar `./.agents/bootstrap.sh opencode` para regenerar `opencode.json` con los steering files. Verificar que `instructions` incluye los paths de steering. _(R11)_

- [x] **T14** — Ejecutar `./check.sh` y verificar que pasa con exit 0, incluyendo la nueva sección de Steering Validation y el test `test_steering.sh`. _(R16)_

- [x] **T15** — Actualizar `feature_list.json`: cambiar FEAT-003 `status` a `"done"`. _(Cierre)_

- [x] **T16** — Añadir entrada fechada en `progress/progress.md` con: campo `steering` en manifest, directorio `steering/` con ejemplos, renderer extendido, comandos bootstrap, validación en check.sh, test. _(Cierre)_

## BLOQUE 6 — Commit y publicación

- [x] **T17** — `git add -A && git commit -m "feat(steering): formal steering files system — agentic.json schema, renderer extension, scaffolding, validation"` _(Cierre)_

- [x] **T18** — `git push origin master` para publicar. _(Cierre)_

## Resumen de cobertura R↔T↔test

| R<n> | Tareas | Test que lo verifica |
|------|--------|------------------------|
| R1 | T1 | JSON schema validation (steering[] existe en agentic.json) |
| R2 | T2, T3 | test_steering.sh (YAML frontmatter válido) |
| R3 | T5, T7 | test_steering.sh (steering files en instructions) |
| R4 | T5, T6 | test_steering.sh (per-agent instructions en opencode.json) |
| R5 | T2 | ls steering/global-conventions.md |
| R6 | T3 | ls steering/implementer-patterns.md |
| R7 | T1 | grep _template_steering_examples en agentic.json |
| R8 | T8 | bootstrap.sh add-steering (manual test) |
| R9 | T9 | bootstrap.sh remove-steering (manual test) |
| R10 | T10 | check.sh — Steering Validation section |
| R11 | T6, T13 | test_steering.sh (opencode.json#agent.<name>.instructions) |
| R12 | T12 | grep steering en AGENTS.md |
| R13 | T1 | manifest sin steering[] → render sin errores |
| R14 | T4 | ls specs/templates/steering.md |
| R15 | T11 | tests/test_steering.sh existe y pasa |
| R16 | T14 | check.sh exit 0 |

**Cobertura**: 16/16 R<n>s cubiertos.

## Cierre

- [x] **TC1** — Schema, scaffolding, templates (T1-T4) _(R1, R2, R5, R6, R7, R13, R14)_
- [x] **TC2** — Renderer extendido (T5-T7) _(R3, R4, R11)_
- [x] **TC3** — Comandos bootstrap (T8-T9) _(R8, R9)_
- [x] **TC4** — Validación, tests, documentación (T10-T12) _(R10, R12, R15)_
- [x] **TC5** — Integración, cierre, commit (T13-T18) _(R16)_
