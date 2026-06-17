# Requisitos — hooks

> Feature **FEAT-004** de `feature_list.json`. Añade un sistema de hooks (puntos de extensión del ciclo de vida) al workflow SDD. Permite ejecutar scripts automáticamente en momentos clave del ciclo de vida: creación de spec, aprobación, implementación, revisión, y cierre. Inspirado en los plugin events de OpenCode y los custom commands de Claude Code/Gemini CLI, pero CLI-agnóstico.

## Patrones EARS

| Patrón | Sintaxis |
|--------|----------|
| Ubicuo | `DEBE ...` |
| Evento | `CUANDO <evento> DEBE ...` |
| Estado | `MIENTRAS <estado> DEBE ...` |
| Opcional | `DONDE <opción> DEBE ...` |
| No deseado | `SI <condición> ENTONCES DEBE ...` |

## Contexto y motivación

El Harness SDD template define un workflow rígido (`pending → spec_ready → in_progress → done`) con comandos slash (`/spec`, `/approve`, `/implement`, `/done`, `/check`) que el agente ejecuta. Actualmente no hay forma de inyectar lógica personalizada en estos puntos sin modificar los archivos de comando (`.agents/commands/*.md`).

En el ecosistema de CLIs:

| CLI | Mecanismo de hooks | Formato |
|-----|-------------------|---------|
| OpenCode | Plugin events (`tool.execute.before`, `session.*`, `file.*`) | TypeScript en `.opencode/plugins/` |
| Claude Code | Custom slash commands como pseudo-hooks | `.claude/commands/*.md` |
| Gemini CLI | TOML commands como pseudo-hooks | `.gemini/commands/*.toml` |

Ninguno de estos es **CLI-agnóstico**. El Harness SDD necesita un sistema de hooks propio que:
1. Sea independiente del CLI (scripts shell ejecutables por cualquier runtime).
2. Se integre con el workflow SDD existente (los comandos slash invocan hooks en los puntos correctos).
3. Sea declarativo (definido en `agentic.json`, como todo lo demás).
4. Tenga scaffolding y validación.

Casos de uso reales:
- `on_spec_created`: validar que la spec cumple convenciones internas (lint de EARS, formato).
- `on_spec_approved`: enviar notificación a Slack/Teams, crear tarjeta en Jira.
- `on_implementation_start`: hacer checkout de rama feature, pre-cargar dependencias.
- `on_review_complete`: ejecutar tests de integración adicionales, scan de seguridad.
- `on_feature_done`: generar changelog, taggear release, cerrar issues.

## Decisiones de arquitectura validadas

| Decisión | Opción elegida | Razón |
|----------|----------------|-------|
| Formato de hooks | **A — scripts shell (`.sh`) en `hooks/`** | Portable, sin dependencias de runtime, ejecutable en cualquier CI. Consistente con `check.sh`, `bootstrap.sh`. |
| Puntos del ciclo de vida | **A — 8 eventos del workflow SDD** | Cubren el ciclo completo sin ser exhaustivos. Fáciles de extender. |
| Declaración en `agentic.json` | **A — array `hooks[]` con `event`, `script`, `on_failure`** | Consistente con `steering[]`, `subagents[]`. Simple. |
| Fallo de hook | **A — configurable: `warn` (default), `error`, `ignore`** | No queremos que un hook de notificación bloquee el deploy. Pero un hook de seguridad sí debe bloquear. |
| Ejecución | **A — script `hooks/run-hooks.sh` que ejecuta todos los hooks para un evento dado** | Centraliza la lógica. Los comandos slash invocan `hooks/run-hooks.sh <event>`. |
| Integración con comandos slash | **A — cada comando `.md` incluye una línea de invocación de hooks** | Mínima intrusión. El comando sigue siendo legible para humanos. |
| Scaffolding | **A — `_template_hooks_examples[]` con 3 ejemplos** | Un hook de validación, uno de notificación, uno de CI. |
| Variables de entorno | **A — `HOOK_EVENT`, `FEATURE_ID`, `FEATURE_NAME`, `AGENT_NAME`, `ROOT_DIR`** | Suficientes para que cualquier hook acceda al contexto relevante. |

## Requisitos

### R1 — Campo `hooks` en `agentic.json`
- **Patrón:** Ubicuo
- El manifest `.agents/agentic.json` DEBE aceptar un campo `hooks` de tipo array. Cada elemento DEBE tener los campos `event` (string, nombre del evento del ciclo de vida), `script` (string, ruta al script shell), `description` (string), y opcionalmente `on_failure` (enum: `"warn"`, `"error"`, `"ignore"`, default `"warn"`).

### R2 — Eventos del ciclo de vida SDD
- **Patrón:** Ubicuo
- Los siguientes eventos DEBEN ser reconocidos por el sistema de hooks: `on_spec_created`, `on_spec_approved`, `on_implementation_start`, `on_implementation_complete`, `on_review_start`, `on_review_complete`, `on_feature_done`, `on_check_pass`. Eventos adicionales definidos por el usuario DEBEN ser aceptados sin error (extensibilidad).

### R3 — Directorio `hooks/` y script runner
- **Patrón:** Ubicuo
- El proyecto DEBE incluir un directorio `hooks/` en la raíz. DEBE existir un script `hooks/run-hooks.sh` que acepte un argumento `<event>` y ejecute todos los hooks registrados para ese evento en `agentic.json#hooks[]`. Los hooks DEBEN ejecutarse en el orden de declaración.

### R4 — Ejecución de hooks con variables de entorno
- **Patrón:** Evento
- CUANDO `hooks/run-hooks.sh <event>` se ejecute, el script DEBE establecer las variables de entorno `HOOK_EVENT`, `ROOT_DIR` antes de ejecutar cada hook. Opcionalmente, DEBE aceptar flags `--feature-id`, `--feature-name`, `--agent-name` para pasar contexto adicional como `FEATURE_ID`, `FEATURE_NAME`, `AGENT_NAME`.

### R5 — Política de fallo configurable
- **Patrón:** Opcional
- DONDE un hook tenga `on_failure: "ignore"`, su fallo (exit code ≠ 0) NO DEBE detener la ejecución de hooks posteriores ni del workflow. DONDE tenga `on_failure: "warn"`, DEBE mostrar un warning pero continuar. DONDE tenga `on_failure: "error"`, DEBE detener la ejecución y el workflow DEBE fallar.

### R6 — Integración con comandos slash
- **Patrón:** Evento
- CUANDO se ejecute un comando slash que corresponde a un punto del ciclo de vida (e.g., `/spec` → `on_spec_created`), el cuerpo del comando (`.agents/commands/*.md`) DEBE incluir una instrucción para ejecutar `hooks/run-hooks.sh <event>` en el momento adecuado (después de completar la acción principal).

### R7 — Scaffold de ejemplo: `hooks/on-spec-created_validate.sh`
- **Patrón:** Ubicuo
- El template DEBE incluir un archivo `hooks/on-spec-created_validate.sh` ejecutable que verifique que el directorio `specs/<feature>/` contiene exactamente 3 archivos `.md` y que `requirements.md` tiene al menos un requisito EARS (línea que empieza con `### R`).

### R8 — Scaffold de ejemplo: `hooks/on-feature-done_notify.sh`
- **Patrón:** Ubicuo
- El template DEBE incluir un archivo `hooks/on-feature-done_notify.sh` ejecutable que imprima un resumen del feature completado (feature ID, nombre, timestamp) en stdout. DEBE servir como placeholder para integraciones reales (Slack, Jira, etc.).

### R9 — Scaffold de ejemplo: `hooks/on-check-pass_ci.sh`
- **Patrón:** Ubicuo
- El template DEBE incluir un archivo `hooks/on-check-pass_ci.sh` ejecutable que registre un timestamp de `check.sh` exitoso en `progress/last-check-pass.txt`. Placeholder para CI/CD integrations.

### R10 — Campo `_template_hooks_examples` en `agentic.json`
- **Patrón:** Ubicuo
- El manifest DEBE incluir un campo `_template_hooks_examples` con las referencias a los hooks de ejemplo (R7, R8, R9). Sigue el mismo convenio de underscore (scaffold, no se renderiza automáticamente).

### R11 — Comandos bootstrap `add-hook` y `remove-hook`
- **Patrón:** Evento
- CUANDO se ejecute `./.agents/bootstrap.sh add-hook --event <event> --script <path>`, el script DEBE añadir una entrada a `agentic.json#hooks[]`. CUANDO se ejecute `./.agents/bootstrap.sh remove-hook <event> <script>`, DEBE eliminar la entrada correspondiente. El archivo en disco NO DEBE eliminarse automáticamente.

### R12 — Validación en `check.sh`
- **Patrón:** Ubicuo
- `./check.sh` DEBE incluir una sección «Hooks Validation» que: (a) verifique que `hooks/run-hooks.sh` existe y es ejecutable; (b) verifique que todos los scripts referenciados en `agentic.json#hooks[].script` existen en disco; (c) verifique que cada hook tiene un `event` reconocido (de la lista R2) o emita un warning si es un evento personalizado. Errores de existencia DEBEN ser ❌ (fail).

### R13 — Test de hooks en `tests/`
- **Patrón:** Ubicuo
- DEBE existir un test `tests/test_hooks.sh` ejecutable que: (a) ejecute `hooks/run-hooks.sh on_spec_created` y verifique que los hooks para ese evento se ejecutan sin error; (b) verifique que un hook con `on_failure: "error"` que falla detiene la ejecución; (c) verifique que un hook con `on_failure: "ignore"` que falla no detiene la ejecución de hooks posteriores.

### R14 — Campo `_template_lifecycle` actualizado con hooks
- **Patrón:** Ubicuo
- El campo `_template_lifecycle` en `agentic.json` (si aún existe) DEBE mencionar que `_template_hooks_examples[]` sigue el mismo ciclo de 3 etapas que `_template_subagents_examples[]`. Si `_template_lifecycle` ya fue eliminado, este requisito es N/A.

### R15 — check.sh verde tras implementación
- **Patrón:** Evento
- CUANDO se complete la implementación, `./check.sh` DEBE pasar con exit 0, incluyendo la validación de hooks (R12, R13).

### R16 — Sin breaking changes
- **Patrón:** Ubicuo
- El campo `hooks` en `agentic.json` DEBE ser opcional. Manifests sin `hooks` DEBEN seguir siendo válidos. `hooks/run-hooks.sh` DEBE aceptar eventos sin hooks registrados (exit 0, sin error).

## Trazabilidad con Criterios de Aceptación

| Criterio | Cubierto por |
|----------|--------------|
| Campo `hooks` en el schema del manifest | R1 |
| Eventos del ciclo de vida reconocidos | R2 |
| Directorio `hooks/` y runner script | R3 |
| Ejecución con variables de entorno | R4 |
| Política de fallo configurable | R5 |
| Integración con comandos slash | R6 |
| Scaffolds de ejemplo (3 hooks) | R7, R8, R9 |
| Campo `_template_hooks_examples` | R10 |
| Comandos bootstrap (add/remove hook) | R11 |
| Validación en check.sh | R12 |
| Test automatizado | R13 |
| Documentación del lifecycle | R14 |
| Cierre limpio (check.sh verde) | R15 |
| Compatibilidad hacia atrás | R16 |
