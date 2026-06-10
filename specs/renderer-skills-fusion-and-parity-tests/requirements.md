# Requisitos — renderer-skills-fusion-and-parity-tests

> Feature **FEAT-002** de `feature_list.json`. Endurece el CLI-agnostic layer de la plantilla: fusiona las dos fuentes de skills_paths, sanea el sistema de templates del sub-agent, y añade tests de paridad y determinismo. Sin breaking changes al schema del manifest.

## Patrones EARS

| Patrón | Sintaxis |
|--------|----------|
| Ubicuo | `DEBE ...` |
| Evento | `CUANDO <evento> DEBE ...` |
| Estado | `MIENTRAS <estado> DEBE ...` |
| Opcional | `DONDE <opción> DEBE ...` |
| No deseado | `SI <condición> ENTONCES DEBE ...` |

## Contexto y motivación

El CLI-agnostic layer de la plantilla (`.agents/adapters/_common/render.py`) tiene 3 debilidades identificadas durante el uso real por proyectos downstream:

1. **Bug 1 — `extra_skills` calculado y nunca inyectado en el render final**: la función `build_context` calcula `extra_skills` desde `project_detect[].apply.add_skills[]` (líneas 132-135 de `render.py`). Sin embargo, `render_opencode` (línea 224) usa `ctx["skills_paths"]`, que se asigna en la línea 145 desde `manifest.skills.paths[]` **sin** incluir `extra_skills`. Resultado: declarar skills en el `add_skills` del `project_detect` no tiene efecto en el `opencode.json` generado. Es un bug real.

2. **Bug 2 — `opencode.json.tmpl` vestigial**: el archivo `opencode.json.tmpl` (≈50 líneas) existe en `.agents/adapters/opencode/` pero `render_opencode` construye el dict programáticamente sin leerlo. Es código muerto que confunde sobre cuál es la fuente de verdad del render.

3. **Bug 3 — `agent-template` con placeholders sin test de no-filtración**: `agent-template/SUBAGENT.md` contiene corchetes literales del estilo `[Area 1]`, `[Step 1 of typical workflow]`. El código lo exceptúa de "orphans" en `render.py` (lo trata como referencia humana), pero no existe un test que valide que se mantiene como referencia limpia. Si alguien lo modifica añadiendo o quitando secciones, el cambio pasa desapercibido y los placeholders podrían filtrarse a nuevos sub-agents.

Además, no existen tests que verifiquen el principio de determinismo del framework: dado un manifest fijo, el render debe ser idéntico byte-a-byte entre ejecuciones. Esto es importante porque la plantilla promete "regenerar adapters de forma determinista" pero no hay prueba automatizada de ello.

## Decisiones de arquitectura validadas

| Decisión | Opción elegida | Razón |
|----------|----------------|-------|
| Fusión `skills_paths` + `extra_skills` | **A — unión deduplicada en `build_context`** | Mínimo, determinista, sin nueva API. ≈5 líneas + 1 test. |
| `opencode.json.tmpl` | **A — marcar como vestigio documentado** | YAGNI eliminar. Mantener coherencia con `GEMINI.md.tmpl` y `CLAUDE.md.tmpl` que sí se usan. Marcar claramente que la fuente de verdad es `render.py`. |
| `agent-template` | **C — mantener como referencia humana, saneado** | Test verifica no-filtración de placeholders `[...]`. El código usa `_default_subagent_body` cuando `agent-template/` falla la lectura. La sanitización reemplaza placeholders huérfanos por comentarios HTML `<!-- TODO: ... -->`. |

## Requisitos

### R1 — Fusión de skills_paths y extra_skills en build_context
- **Patrón:** Ubicuo
- La función `build_context` en `.agents/adapters/_common/render.py` DEBE devolver `skills_paths` como la **unión ordenada y deduplicada** de `manifest.skills.paths[]` seguido de `extra_skills[]`, donde los duplicados se eliminan preservando la primera aparición.

### R2 — Deduplicación con preservación de orden
- **Patrón:** Ubicuo
- CUANDO `manifest.skills.paths[]` y `extra_skills[]` contengan elementos idénticos, el resultado DEBE contener cada elemento único exactamente una vez, en el orden de primera aparición (primero manifest, después extra_skills).

### R3 — Cobertura de la fusión en render_opencode
- **Patrón:** Ubicuo
- `render_opencode` DEBE usar `ctx["skills_paths"]` (que ahora incluye `extra_skills`) al construir el campo `skills.paths` de `opencode.json`. NO DEBE filtrar ni recortar la lista fusionada.

### R4 — Determinismo del render
- **Patrón:** Evento
- CUANDO se ejecute `./.agents/bootstrap.sh --all` dos veces consecutivas SIN modificar `.agents/agentic.json`, los archivos generados (`opencode.json`, `GEMINI.md`, `CLAUDE.md`, `.claude/agents/*.md`, `.claude/commands/*.md`, `.claude/settings.json`, `.gemini/commands/*.toml`) DEBEN ser **idénticos byte-a-byte** entre ambas ejecuciones. NO DEBEN contener timestamps, paths absolutos del host, ni orden de claves no determinista.

### R5 — Test de paridad de los 3 CLIs
- **Patrón:** Evento
- CUANDO se ejecute el nuevo test de paridad (`tests/test_cli_adapter_parity.sh`), los 3 renders resultantes DEBEN ser estables. Es decir, una segunda ejecución del mismo render DEBE producir el mismo SHA256 sobre el contenido de los archivos generados.

### R6 — opencode.json.tmpl marcado como vestigio
- **Patrón:** Ubicuo
- El archivo `.agents/adapters/opencode/opencode.json.tmpl` DEBE contener un comentario en la primera línea declarando `VESTIGIAL: la fuente de verdad es render_opencode en render.py; este archivo se conserva solo como referencia para una futura migración a template puro`. NO DEBE ser procesado por `render_opencode` (que es programático).

### R7 — Test de no-filtración de placeholders en agent-template
- **Patrón:** Evento
- CUANDO se ejecute el test de placeholders, el archivo `.agents/subagents/agent-template/SUBAGENT.md` NO DEBE contener placeholders literales del estilo `[Area 1]`, `[Step 1]`, `[Guideline 3]`, `[Rule 3]` que NO estén dentro de bloques de código de ejemplo (entre ``` ... ```). Si los contiene, el test DEBE fallar con un mensaje indicando el número de línea y el placeholder detectado.

### R8 — Documentación de `.claude/settings.json` como estático
- **Patrón:** Ubicuo
- El archivo `CLAUDE.md` DEBE contener una mención explícita de que `.claude/settings.json` declara permisos de **bootstrap** (estables, no cambian con el stack detectado) y que los overrides stack-aware se aplican a `.claude/agents/<name>.md` por sub-agente.

### R9 — Sanitización de agent-template al scaffold
- **Patrón:** Ubicuo
- La función `scaffold_subagent_role_file` en `.agents/adapters/_common/render.py` DEBE pasar el cuerpo leído de `agent-template/SUBAGENT.md` por una **función de sanitización** que elimina líneas que coinciden con el patrón `^\s*\[[A-Za-z][A-Za-z0-9 _-]{0,30}\]\s*$` (placeholders huérfanos, primer carácter letra, longitud máx 30) antes de las sustituciones de `name` y `description`. Las líneas dentro de bloques de código ```...``` NO DEBEN ser sanitizadas. Las líneas sanitizadas DEBEN reemplazarse por `<!-- TODO: personalizar esta sección -->`.

### R10 — El test `tests/test_cli_adapter_parity.sh` existe y es ejecutable
- **Patrón:** Ubicuo
- El archivo `tests/test_cli_adapter_parity.sh` DEBE existir, ser ejecutable, y DEBE incluir al menos las siguientes aserciones: (a) dos renders consecutivos producen el mismo SHA256 agregado; (b) los 3 CLIs (opencode, gemini-cli, claude-code) renderizan sin error; (c) el render de `opencode.json` incluye los paths de las skills declaradas en `agentic.json#project_detect[].apply.add_skills[]` (descubrimiento dinámico, no hardcoded).

### R11 — El test `tests/test_agent_template_placeholders.sh` existe y es ejecutable
- **Patrón:** Ubicuo
- El archivo `tests/test_agent_template_placeholders.sh` DEBE existir, ser ejecutable, y DEBE leer `.agents/subagents/agent-template/SUBAGENT.md`, buscar líneas que coincidan con `^\s*\[[A-Za-z][A-Za-z0-9 _-]{0,30}\]\s*$` (excluyendo líneas dentro de bloques ```...```), y fallar con el número de línea y el placeholder si encuentra alguno.

### R12 — check.sh invoca los nuevos tests
- **Patrón:** Ubicuo
- `./check.sh` DEBE invocar `tests/test_cli_adapter_parity.sh` y `tests/test_agent_template_placeholders.sh` antes del resumen final, mostrando ✅/❌ y propagando el código de salida.

### R13 — check.sh verde tras los cambios
- **Patrón:** Evento
- CUANDO se complete la implementación, `./check.sh` DEBE pasar con exit 0, incluyendo la ejecución de los 2 nuevos tests (R10, R11).

### R14 — feature_list actualizado
- **Patrón:** Ubicuo
- `feature_list.json` DEBE tener este feature con `status: "done"` tras la implementación exitosa y el commit.

### R15 — progress.md registra el cambio
- **Patrón:** Evento
- CUANDO se complete la implementación, `progress/progress.md` DEBE contener una entrada fechada con: skills_paths+extra_skills fusionados, `opencode.json.tmpl` marcado como vestigio, agent-template saneado, 2 tests nuevos, check.sh verde.

### R16 — Spec del feature cumple el convenio specs-only-md
- **Patrón:** Ubicuo
- El directorio `specs/renderer-skills-fusion-and-parity-tests/` DEBE contener únicamente `requirements.md`, `design.md` y `tasks.md`. NO DEBE contener archivos `.xml`, `.json`, `.sh` u otros artefactos de prueba. La validación del spec se hace con `find specs/renderer-skills-fusion-and-parity-tests -type f` que debe devolver exactamente 3 archivos.

### R17 — Sin breaking changes al manifest
- **Patrón:** Ubicuo
- El cambio en `build_context` NO DEBE añadir, renombrar ni eliminar campos del schema de `.agents/agentic.json`. Manifests válidos antes del feature DEBEN seguir siendo válidos después.

## Trazabilidad con Criterios de Aceptación

| Criterio | Cubierto por |
|----------|--------------|
| `extra_skills` se propaga al render | R1, R2, R3 |
| Render determinista (2 ejecuciones = mismo SHA256) | R4, R5, R10 |
| `opencode.json.tmpl` clarificado como vestigio | R6 |
| `agent-template` sin placeholders filtrables | R7, R9, R11 |
| `.claude/settings.json` documentado como estático | R8 |
| Tests ejecutables y validables | R10, R11, R12 |
| Cierre limpio (feature_list + progress + spec) | R14, R15, R16 |
| Compatibilidad con manifests previos | R17 |
| Cierre técnico (check.sh verde) | R13 |
