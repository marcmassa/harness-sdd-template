# Tareas — hooks

> Pasos discretos en orden para FEAT-004. Cada tarea referencia los `R<n>` que cubre. El implementador marca `[x]` al completar.

## BLOQUE 1 — Schema, scaffolding, y runner (R1, R2, R3, R4, R5, R7, R8, R9, R10, R16)

- [x] **T1** — Añadir `hooks: []` y `_template_hooks_examples: [...]` (con 3 entradas scaffold) a `.agents/agentic.json`. El campo `hooks` empieza vacío. Los scaffolds incluyen `on-spec-created_validate`, `on-feature-done_notify`, y `on-check-pass_ci`. _(R1, R10, R16)_

- [x] **T2** — Crear `hooks/run-hooks.sh` ejecutable (`chmod +x`). Implementar: leer `agentic.json#hooks[]`, filtrar por `event == $1`, ejecutar scripts secuencialmente con variables de entorno (`HOOK_EVENT`, `ROOT_DIR`, `FEATURE_ID`, `FEATURE_NAME`, `AGENT_NAME`), aplicar política `on_failure` (warn/error/ignore). Aceptar flags `--feature-id`, `--feature-name`, `--agent-name`. _(R2, R3, R4, R5)_

- [x] **T3** — Crear `hooks/on-spec-created_validate.sh` ejecutable. Verificar: directorio `specs/<FEATURE_NAME>/` existe, contiene 3 `.md`, `requirements.md` tiene al menos un `### R<n>`. _(R7)_

- [x] **T4** — Crear `hooks/on-feature-done_notify.sh` ejecutable. Imprimir resumen con FEATURE_ID, FEATURE_NAME, timestamp UTC, AGENT_NAME. Placeholder para integraciones. _(R8)_

- [x] **T5** — Crear `hooks/on-check-pass_ci.sh` ejecutable. Escribir timestamp UTC en `progress/last-check-pass.txt`. _(R9)_

## BLOQUE 2 — Integración con comandos slash (R6)

- [x] **T6** — Modificar `.agents/commands/spec.md`: añadir al final instrucción para ejecutar `hooks/run-hooks.sh on_spec_created --feature-id "..." --feature-name "..."`. _(R6)_

- [x] **T7** — Modificar `.agents/commands/approve.md`: añadir después de cambiar status instrucción para ejecutar `hooks/run-hooks.sh on_spec_approved --feature-id "..." --feature-name "..."`. _(R6)_

- [x] **T8** — Modificar `.agents/commands/implement.md`: añadir al inicio `hooks/run-hooks.sh on_implementation_start` y al final `hooks/run-hooks.sh on_implementation_complete`. _(R6)_

- [x] **T9** — Modificar `.agents/commands/done.md`: añadir `on_review_start` (antes de revisar), `on_review_complete` (después de verificar trazabilidad), `on_feature_done` (después de marcar done). _(R6)_

- [x] **T10** — Modificar `.agents/commands/check.md`: añadir al final (tras check.sh exitoso) `hooks/run-hooks.sh on_check_pass`. _(R6)_

## BLOQUE 3 — Comandos bootstrap (R11)

- [x] **T11** — Añadir `add_hook_run()` a `.agents/bootstrap.sh`: acepta `--event`, `--script`, `--description`, `--on-failure` (default `warn`). Añade entrada a `agentic.json#hooks[]` vía `python3`. Si el script no existe, pregunta si crear template. _(R11)_

- [x] **T12** — Añadir `remove_hook_run()` a `.agents/bootstrap.sh`: acepta `<event>` y `<script>`. Elimina entrada coincidente de `agentic.json#hooks[]`. No elimina archivo en disco. _(R11)_

## BLOQUE 4 — Validación, tests, y documentación (R12, R13, R14)

- [x] **T13** — En `check.sh`, añadir sección «Hooks Validation» que: (a) verifica `hooks/run-hooks.sh` existe y es ejecutable; (b) verifica cada `hooks[].script` existe; (c) advierte sobre eventos no estándar. Usar ❌ para errores de existencia, ⚠️ para warnings. _(R12)_

- [x] **T14** — Crear `tests/test_hooks.sh` ejecutable con tests: (a) `run-hooks.sh` con evento sin hooks → exit 0; (b) `run-hooks.sh` existe y es ejecutable; (c) los 3 hooks de ejemplo existen. _(R13)_

- [x] **T15** — Si `_template_lifecycle` aún existe en `agentic.json`, actualizarlo para mencionar `_template_hooks_examples[]`. Si ya fue eliminado, marcar R14 como N/A. _(R14)_

## BLOQUE 5 — Integración y cierre (R15)

- [x] **T16** — Ejecutar `./check.sh` y verificar que pasa con exit 0, incluyendo la sección «Hooks Validation» y `tests/test_hooks.sh`. _(R15)_

- [x] **T17** — Actualizar `feature_list.json`: cambiar FEAT-004 `status` a `"done"`. _(Cierre)_

- [x] **T18** — Añadir entrada fechada en `progress/progress.md` con: sistema de hooks (runner, scaffolds, integración con comandos), comandos bootstrap, validación, tests. _(Cierre)_

## BLOQUE 6 — Commit y publicación

- [x] **T19** — `git add -A && git commit -m "feat(hooks): SDD lifecycle hooks system — runner, scaffolding, slash-command integration, validation"` _(Cierre)_

- [x] **T20** — `git push origin master` para publicar. _(Cierre)_

## Resumen de cobertura R↔T↔test

| R<n> | Tareas | Test que lo verifica |
|------|--------|------------------------|
| R1 | T1 | JSON schema (hooks[] en agentic.json) |
| R2 | T2 | test_hooks.sh (eventos reconocidos) |
| R3 | T2 | test_hooks.sh (run-hooks.sh existe y ejecuta) |
| R4 | T2 | test_hooks.sh (variables de entorno seteadas) |
| R5 | T2 | test_hooks.sh (políticas on_failure) |
| R6 | T6-T10 | integración manual (comandos invocan hooks) |
| R7 | T3 | test_hooks.sh (example hook exists) |
| R8 | T4 | test_hooks.sh (example hook exists) |
| R9 | T5 | test_hooks.sh (example hook exists) |
| R10 | T1 | grep _template_hooks_examples en agentic.json |
| R11 | T11-T12 | bootstrap.sh add-hook/remove-hook (manual) |
| R12 | T13 | check.sh — Hooks Validation section |
| R13 | T14 | tests/test_hooks.sh existe y pasa |
| R14 | T15 | grep hooks en _template_lifecycle (si existe) |
| R15 | T16 | check.sh exit 0 |
| R16 | T1 | manifest sin hooks[] → render sin error |

**Cobertura**: 16/16 R<n>s cubiertos.

## Cierre

- [x] **TC1** — Schema, runner, scaffolds (T1-T5) _(R1, R2, R3, R4, R5, R7, R8, R9, R10, R16)_
- [x] **TC2** — Integración con comandos slash (T6-T10) _(R6)_
- [x] **TC3** — Comandos bootstrap (T11-T12) _(R11)_
- [x] **TC4** — Validación, tests, docs (T13-T15) _(R12, R13, R14)_
- [x] **TC5** — Integración, cierre, commit (T16-T20) _(R15)_
