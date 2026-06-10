# Tareas — renderer-skills-fusion-and-parity-tests

> Pasos discretos en orden para FEAT-002. Cada tarea referencia los `R<n>` que cubre. El implementador marca `[x]` al completar.

## BLOQUE 1 — Refactor del renderer (R1, R2, R9, R17)

- [ ] **T1** — En `.agents/adapters/_common/render.py`, añadir el helper `_merge_unique_ordered(*lists: list[str]) -> list[str]` que implementa la unión ordenada y deduplicada preservando primera aparición. Ubicación sugerida: justo antes de `build_context`. _(R1, R2)_

- [ ] **T2** — En la misma función, modificar la construcción del dict de retorno en `build_context` (línea 145) para que `skills_paths` se compute como `_merge_unique_ordered(base_paths, extra_skills)`, donde `base_paths = manifest.get("skills", {}).get("paths", [])`. NO modificar otros campos del dict. _(R1, R2, R3, R17)_

- [ ] **T3** — En `.agents/adapters/_common/render.py`, añadir la constante `_PLACEHOLDER_RE = re.compile(r"^(\s*)\[([A-Za-z][A-Za-z0-9 _-]{0,30})\]\s*$")` y la función `_sanitize_template_body(body: str) -> str`. La función reemplaza líneas que coinciden con la regex (fuera de bloques de código ```...```) por `<!-- TODO: personalizar esta sección -->`. Verificar que `import re` está presente. _(R9)_

- [ ] **T4** — En `scaffold_subagent_role_file` (líneas ≈406-440), aplicar `_sanitize_template_body(body)` al cuerpo leído de `agent-template/SUBAGENT.md` **antes** de las sustituciones de `name` y `description`. Verificar que el fallback a `_default_subagent_body` sigue intacto. _(R9)_

## BLOQUE 2 — Marcar .tmpl vestigial (R6)

- [ ] **T5** — Sustituir la primera línea de `.agents/adapters/opencode/opencode.json.tmpl` por un comentario `VESTIGIAL: este archivo NO es procesado por render_opencode (que construye el dict programáticamente en .agents/adapters/_common/render.py). Se conserva como referencia para una futura migración a template puro. No editar — la fuente de verdad es render.py.`. NO eliminar el resto del archivo. _(R6)_

- [ ] **T6** — Verificar que `.agents/BOOTSTRAP.md` línea 25 sigue reflejando la realidad (opencode es renderizado programáticamente, sin `.tmpl` procesado). Si está desactualizado, actualizarlo. _(R6)_

## BLOQUE 3 — Documentar settings.json estático (R8)

- [ ] **T7** — En `CLAUDE.md`, añadir una mención explícita en la sección de Permissions (o donde se documente la configuración de Claude) declarando: "`.claude/settings.json` contiene permisos de **bootstrap** (estables, no cambian con el stack detectado en `agentic.json#project_detect[]`). Los overrides stack-aware se aplican a `.claude/agents/<name>.md` por sub-agente." _(R8)_

## BLOQUE 4 — Tests genéricos de paridad y determinismo (R4, R5, R7, R10, R11)

- [ ] **T8** — Crear `tests/` directorio y dentro el archivo `tests/test_cli_adapter_parity.sh` ejecutable (`chmod +x`). Incluir las 4 aserciones: (a) dos renders consecutivos → mismo SHA256 agregado; (b) los 3 CLIs renderizan sin error; (c) `opencode.json#skills.paths` incluye los paths base del manifest; (d) las skills declaradas en `add_skills[]` aparecen en el render (descubrimiento dinámico desde `agentic.json`). NO hardcodear nombres de skills. _(R4, R5, R10)_

- [ ] **T9** — Crear `tests/test_agent_template_placeholders.sh` ejecutable. Lee `.agents/subagents/agent-template/SUBAGENT.md`, busca líneas que coincidan con `^\s*\[[A-Za-z][A-Za-z0-9 _-]{0,30}\]\s*$` (excluyendo líneas dentro de bloques ```...```), y falla con el número de línea y el placeholder si encuentra alguna. Si el archivo no existe, el test hace SKIP con exit 0. _(R7, R11)_

- [ ] **T10** — En `check.sh`, añadir invocación de `test_cli_adapter_parity.sh` y `test_agent_template_placeholders.sh` antes del resumen final, con mensaje `✅`/`❌` y propagación del código de salida. _(R12)_

## BLOQUE 5 — Validación end-to-end (R12, R13, R14, R15, R16)

- [ ] **T11** — Ejecutar `./check.sh` y verificar que pasa con exit 0, incluyendo los 2 nuevos tests. Si algún test falla, arreglar el código (NO relajar el test). _(R13)_

- [ ] **T12** — Verificar que `find specs/renderer-skills-fusion-and-parity-tests -type f` solo contiene los 3 archivos `.md` (convenio specs-only-md, también aplicable a este spec). _(R16)_

- [ ] **T13** — Actualizar `feature_list.json`: cambiar FEAT-002 `status` a `"done"`. _(R14)_

- [ ] **T14** — Añadir entrada fechada en `progress/progress.md` con: skills_paths+extra_skills fusionados, `opencode.json.tmpl` marcado como vestigio, agent-template saneado, 2 tests nuevos, check.sh verde. _(R15)_

## BLOQUE 6 — Commit y publicación

- [ ] **T15** — `git add -A && git commit -m "feat(renderer): fusion skills_paths+extra_skills, parity tests, vestigial docs"` con mensaje descriptivo. _(Cierre)_

- [ ] **T16** — `git push origin master` para publicar. _(Cierre)_

## Resumen de cobertura R↔T↔test

| R<n> | Tareas | Test que lo verifica |
|------|--------|------------------------|
| R1 | T1, T2 | test_cli_adapter_parity.sh (skills en opencode.json) |
| R2 | T1, T2 | test_cli_adapter_parity.sh (dedup) |
| R3 | T2 | test_cli_adapter_parity.sh (opencode render usa skills_paths fusionado) |
| R4 | T8, T10 | test_cli_adapter_parity.sh (SHA256 doble) |
| R5 | T8 | test_cli_adapter_parity.sh |
| R6 | T5, T6 | grep `VESTIGIAL` en opencode.json.tmpl |
| R7 | T9, T10 | test_agent_template_placeholders.sh |
| R8 | T7 | grep en CLAUDE.md |
| R9 | T3, T4 | test_agent_template_placeholders.sh (scaffold no filtra) |
| R10 | T8 | test_cli_adapter_parity.sh (existe y es ejecutable) |
| R11 | T9 | test_agent_template_placeholders.sh (existe y es ejecutable) |
| R12 | T10 | ./check.sh invoca los tests |
| R13 | T11 | ./check.sh exit 0 |
| R14 | T13 | grep FEAT-002 en feature_list.json |
| R15 | T14 | grep entrada fechada en progress/progress.md |
| R16 | T12 | find specs/renderer-skills-fusion-and-parity-tests/ |
| R17 | T2 | agentic.json sin cambios de schema |

**Cobertura**: 17/17 R<n>s cubiertos.

## Cierre

- [ ] **TC1** — Refactor del renderer (T1-T4) _(R1, R2, R3, R9, R17)_
- [ ] **TC2** — Marcar .tmpl y documentar settings (T5-T7) _(R6, R8)_
- [ ] **TC3** — Tests nuevos + integración en check.sh (T8-T10) _(R4, R5, R7, R10, R11, R12)_
- [ ] **TC4** — Validación, documentación, cierre (T11-T14) _(R13, R14, R15, R16)_
- [ ] **TC5** — Commit y push (T15-T16) _(Cierre)_
