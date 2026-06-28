# Tasks — SOUL.md: capa de identidad y principios de decisión por subagente

> Pasos discretos en orden. El implementer marca `[x]` al completar cada uno.
> Cada tarea referencia el R<n> que cubre.

## Implementation

- [x] **T1** — Crear `.agents/subagents/agent-template/SOUL.md` con la estructura canónica de cuatro secciones y placeholders descriptivos _(R1, R5)_

- [x] **T2** — Crear `.agents/subagents/templates/SOUL.md` con contenido real que refleje la identidad, principios de decisión, límites y estilo del subagente `templates` _(R1, R2, R8)_

- [x] **T3** — Añadir campo `soul` en la entrada del subagente `templates` dentro de `.agents/agentic.json`, apuntando a `.agents/subagents/templates/SOUL.md` _(R3, R10)_

- [x] **T4** — Modificar `render.py` para leer SOUL.md de cada subagente (campo `soul` o convención de path) e inyectar su contenido en el stub generado bajo la sección `## Agent Soul` _(R4)_

- [x] **T5** — Añadir validación en `check.sh`: iterar subagentes declarados en `agentic.json` y verificar existencia de su SOUL.md; terminar con error y nombre del afectado si falta alguno _(R6)_

- [x] **T6** — Actualizar `.agents/commands/init.md` para instruir explícitamente al agente implementador a poblar SOUL.md de cada subagente antes de declarar el init completado _(R7)_

- [x] **T7** — Poblar `DESIGN.md` con contenido meta: explicar su naturaleza de plantilla, el propósito de cada sección, y usar el propio Harness SDD como ejemplo de adaptación _(R9)_

- [x] **T8** — Regenerar `.claude/agents/templates.md` y `GEMINI.md` ejecutando `./.agents/bootstrap.sh claude-code` y `./.agents/bootstrap.sh gemini-cli` _(R4)_

## Tests

- [x] **T9** — Test en `tests/test_soul_md.sh` que verifica que el stub generado por bootstrap para el subagente `templates` contiene la sección `## Agent Soul` con contenido no vacío _(R4)_

- [x] **T10** — Test que simula un subagente declarado en `agentic.json` sin SOUL.md en disco y verifica que la validación termina con código de error != 0 _(R6)_

- [x] **T11** — Test que verifica que `.agents/subagents/agent-template/SOUL.md` contiene las cuatro secciones canónicas _(R1, R5)_

- [x] **T12** — Verificación de retrocompatibilidad: `load_soul_content` sin campo `soul` retorna string vacío sin error _(R10)_

## Closure

- [x] **T13** — Documentar trazabilidad `R<n> ↔ test` en `progress/impl_soul-md-subagent-identity.md`
- [x] **T14** — Ejecutar `./check.sh` y verificar que todos los tests pasan (fallo Init Validation es preexistente)
- [x] **T15** — Actualizar `feature_list.json`: establecer `status` a `"done"`
- [x] **T16** — Registrar resumen en `progress/progress.md`
