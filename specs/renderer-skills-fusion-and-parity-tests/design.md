# Diseño — renderer-skills-fusion-and-parity-tests

> Decisiones técnicas para **FEAT-002**. Refactor mínimo del CLI-agnostic layer de la plantilla: fusiona dos fuentes de skills_paths, sanea el template del sub-agent, y añade tests de paridad y determinismo. Cero breaking changes al schema del manifest.

## Resumen

El CLI-agnostic layer de la plantilla tiene 3 debilidades reales:

1. **`extra_skills` calculado y nunca inyectado** (`render.py:132-135` vs `:145,224`). El campo `add_skills` del `project_detect` no tiene efecto en el render. Bug real.
2. **`opencode.json.tmpl` vestigial**. `render_opencode` construye el dict programáticamente sin tocar el `.tmpl`.
3. **`agent-template` con placeholders sin test**. Corchetes literales `[Area 1]` que podrían filtrarse a nuevos sub-agents.

Este feature:
- Arregla el bug 1 con ≈5 líneas (helper `_merge_unique_ordered` + 1 línea de cambio en `build_context`).
- Marca el bug 2 como vestigio documentado (comentario en la primera línea del `.tmpl`).
- Sanea el bug 3 con sanitización + test (regex de placeholders huérfanos → `<!-- TODO: personalizar -->`).
- Añade 2 tests genéricos (paridad + determinismo, placeholders) que cierran el principio de determinismo del framework.

## Archivos afectados

| Archivo | Acción | Razón |
|---------|--------|-------|
| `.agents/adapters/_common/render.py` | modificar | Fusión `skills_paths` + `extra_skills` (R1, R2) |
| `.agents/adapters/_common/render.py` | modificar | Sanitización en `scaffold_subagent_role_file` (R9) |
| `.agents/adapters/opencode/opencode.json.tmpl` | modificar | Marcar primera línea como `VESTIGIAL: ...` (R6) |
| `CLAUDE.md` | modificar | Documentar `.claude/settings.json` como estático (R8) |
| `tests/test_cli_adapter_parity.sh` | crear | Test de paridad + determinismo (R4, R5, R10) |
| `tests/test_agent_template_placeholders.sh` | crear | Test de no-filtración de placeholders (R7, R11) |
| `check.sh` | modificar | Invocar los 2 tests nuevos (R12) |
| `feature_list.json` | modificar | FEAT-002 → `status: "done"` (R14) |
| `progress/progress.md` | modificar | Entrada fechada (R15) |
| `specs/renderer-skills-fusion-and-parity-tests/{requirements,design,tasks}.md` | crear | Spec (R16) |

## Algoritmo

### A. Fusión `skills_paths` + `extra_skills` (R1, R2)

**Cambio en `build_context` (líneas 132-151 de `render.py`):**

```python
# ANTES (línea 145):
"skills_paths": manifest.get("skills", {}).get("paths", []),

# DESPUÉS:
def _merge_unique_ordered(*lists: list[str]) -> list[str]:
    """Unión ordenada y deduplicada preservando la primera aparición."""
    seen: set[str] = set()
    out: list[str] = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return out

# En build_context, reemplazar línea 145:
base_paths = manifest.get("skills", {}).get("paths", [])
"skills_paths": _merge_unique_ordered(base_paths, extra_skills),
```

**Por qué preservamos orden base → extra**: el manifest es la fuente canónica; `extra_skills` son overrides del stack. Si el manifest dice `["a", "b"]` y el stack añade `["b", "c"]`, el resultado es `["a", "b", "c"]` (no `["a", "b", "c", "b"]` ni `["a", "c", "b"]`).

### B. Sanitización de `agent-template` (R9)

**Cambio en `scaffold_subagent_role_file` (líneas ≈406-440 de `render.py`):**

```python
import re

_PLACEHOLDER_RE = re.compile(r"^(\s*)\[([A-Za-z][A-Za-z0-9 _-]{0,30})\]\s*$")

def _sanitize_template_body(body: str) -> str:
    """Elimina líneas que son placeholders huérfanos del estilo '[Area 1]'.

    Un placeholder huérfano es una línea que:
      - Empieza con 0+ espacios
      - Sigue con '[' + (letra) + (letras/dígitos/espacios/guiones bajos/guiones, máx 30) + ']'
      - Termina con 0+ espacios
      - NO está dentro de un bloque de código ```...```

    Heurística: si la línea coincide con `^\\s*\\[[A-Za-z][A-Za-z0-9 _-]{0,30}\\]\\s*$`,
    se reemplaza por un comentario HTML indicando que se sustituye en producción.
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
```

**Aplicación en `scaffold_subagent_role_file`**: leer el body de `agent-template/SUBAGENT.md`, pasar por `_sanitize_template_body(body)`, luego aplicar las sustituciones `{{ name }}` y `{{ description }}`.

**Por qué sanitizar en lugar de eliminar el template**: el template sigue siendo valioso como referencia humana (un dev lo lee y entiende la estructura). Lo que NO queremos es que sus placeholders se filtren a un sub-agent de producción. La sanitización reemplaza `[Area 1]` por `<!-- TODO: personalizar esta sección -->`.

### C. Marcar `opencode.json.tmpl` como vestigio (R6)

**Opción recomendada: DOCUMENTAR (no eliminar)**. Razón: coherencia con `GEMINI.md.tmpl` y `CLAUDE.md.tmpl` que sí se procesan. Si algún día queremos migrar opencode de "dict programático" a "template puro", el archivo está listo. Solo se sustituye la primera línea por un comentario:

```python
# Primera línea del archivo opencode.json.tmpl (sustituyendo la línea 1):
# VESTIGIAL: este archivo NO es procesado por render_opencode (que construye
# el dict programáticamente en .agents/adapters/_common/render.py). Se conserva
# como referencia para una futura migración a template puro. No editar — la
# fuente de verdad es render.py.
```

### D. Test de paridad y determinismo (R4, R5, R10)

**`tests/test_cli_adapter_parity.sh`** (≈60 líneas):

```bash
#!/bin/bash
# Test: dos renders consecutivos del mismo agentic.json producen el mismo
# SHA256 agregado. Verifica el principio de determinismo del framework.
# Genérico: NO hardcodea skills, las descubre dinámicamente.

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Snapshot antes
./.agents/bootstrap.sh --all >/dev/null 2>&1
HASH_1=$(find opencode.json GEMINI.md CLAUDE.md .claude .gemini -type f \
    -exec sha256sum {} \; 2>/dev/null | sha256sum | cut -d' ' -f1)

# Snapshot después (mismo input)
./.agents/bootstrap.sh --all >/dev/null 2>&1
HASH_2=$(find opencode.json GEMINI.md CLAUDE.md .claude .gemini -type f \
    -exec sha256sum {} \; 2>/dev/null | sha256sum | cut -d' ' -f1)

if [ "$HASH_1" != "$HASH_2" ]; then
    echo "FAIL: render no determinista (HASH_1=$HASH_1, HASH_2=$HASH_2)"
    exit 1
fi

# Verificar que los 3 CLIs renderizan
for cli in opencode gemini-cli claude-code; do
    ./.agents/bootstrap.sh "$cli" >/dev/null 2>&1 \
        || { echo "FAIL: $cli no renderiza"; exit 1; }
done

# Verificar que opencode.json#skills.paths incluye los paths del manifest
SKILLS_IN_RENDER=$(python3 -c "
import json
cfg = json.load(open('opencode.json'))
print(','.join(cfg.get('skills', {}).get('paths', [])))")
EXPECTED_BASE=".agents/skills"
if [[ "$SKILLS_IN_RENDER" != *"$EXPECTED_BASE"* ]]; then
    echo "FAIL: opencode.json no incluye $EXPECTED_BASE (actual: $SKILLS_IN_RENDER)"
    exit 1
fi

# Verificar que las skills declaradas en add_skills[] están en el render
# (descubrimiento dinámico, sin hardcodear nombres)
ADDED_SKILLS=$(python3 -c "
import json
m = json.load(open('.agents/agentic.json'))
out = []
for pd in m.get('project_detect', []):
    for s in pd.get('apply', {}).get('add_skills', []):
        out.append(s)
print('\n'.join(out))")
if [ -n "$ADDED_SKILLS" ]; then
    while IFS= read -r skill; do
        if [ -n "$skill" ] && [[ "$SKILLS_IN_RENDER" != *"$skill"* ]]; then
            echo "FAIL: skill '$skill' declarada en add_skills[] no aparece en opencode.json#skills.paths"
            exit 1
        fi
    done <<< "$ADDED_SKILLS"
fi

echo "PASS: test_cli_adapter_parity"
```

### E. Test de placeholders (R7, R11)

**`tests/test_agent_template_placeholders.sh`** (≈30 líneas):

```bash
#!/bin/bash
# Test: .agents/subagents/agent-template/SUBAGENT.md NO contiene placeholders
# literales del estilo [Area 1] fuera de bloques de código.

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$ROOT_DIR/.agents/subagents/agent-template/SUBAGENT.md"

if [ ! -f "$TEMPLATE" ]; then
    echo "SKIP: $TEMPLATE no existe (template opcional)"
    exit 0
fi

FAIL=0
LINE_NO=0
IN_CODE=0
PLACEHOLDER_RE='^\s*\[[A-Za-z][A-Za-z0-9 _-]{0,30}\]\s*$'

while IFS= read -r line; do
    LINE_NO=$((LINE_NO + 1))
    if [[ "$line" =~ ^\s*``` ]]; then
        IN_CODE=$((1 - IN_CODE))
        continue
    fi
    if [ "$IN_CODE" -eq 1 ]; then
        continue
    fi
    if [[ "$line" =~ $PLACEHOLDER_RE ]]; then
        echo "FAIL: $TEMPLATE:$LINE_NO placeholder huérfano: $line"
        FAIL=1
    fi
done < "$TEMPLATE"

if [ "$FAIL" -eq 1 ]; then
    echo "FAIL: agent-template contiene placeholders. Ejecuta _sanitize_template_body o edita el template."
    exit 1
fi

echo "PASS: test_agent_template_placeholders"
```

### F. Integración en `check.sh` (R12)

Añadir al final de `check.sh`, antes del resumen final:

```bash
# Tests de paridad y determinismo del CLI-agnostic layer (FEAT-002)
for t in test_cli_adapter_parity test_agent_template_placeholders; do
    if [ -f "$ROOT_DIR/tests/${t}.sh" ]; then
        if bash "$ROOT_DIR/tests/${t}.sh" >/dev/null 2>&1; then
            echo "  ✅ ${t}"
        else
            echo "  ❌ ${t} falló"
            exit 1
        fi
    fi
done
```

### G. Documentar `.claude/settings.json` como estático (R8)

Añadir a `CLAUDE.md` (en la sección de Permissions o donde se documente la configuración de Claude):

```markdown
> **Nota**: `.claude/settings.json` declara permisos de **bootstrap** (estables,
> no cambian con el stack detectado en `agentic.json#project_detect[]`). Los
> overrides stack-aware se aplican a `.claude/agents/<name>.md` por sub-agente.
```

## Manejo de Errores

| Condición | Respuesta |
|-----------|-----------|
| `extra_skills` contiene paths que no existen en disco | NO se eliminan — `skills_paths` solo lista, no valida existencia. La validación de existencia la hace cada CLI en su loader. |
| `_sanitize_template_body` elimina un placeholder que el dev quería mantener | El comentario HTML `<!-- TODO: ... -->` es visible y editable. El dev puede reescribir la línea. |
| Test de paridad falla por cambio intencional (nueva feature) | El test debe actualizarse: regenerar el snapshot, o ajustar la aserción. El test es un contrato, no una camisa de fuerza. |
| `bootstrap.sh --all` introduce un cambio no determinista (p.ej. timestamp en comentario) | Es un bug del renderer. El test lo detecta. Se arregla en el renderer. |
| `agent-template` se elimina por error | `scaffold_subagent_role_file` cae a `_default_subagent_body` (fallback ya implementado). |
| `agent-template/SUBAGENT.md` no existe | El test de placeholders hace SKIP con exit 0 (es opcional). |

## Alternativas Descartadas

### A1 — Inyectar `extra_skills` como variable separada del contexto
**Por qué se descarta**: las plantillas (`opencode.json.tmpl`, `GEMINI.md.tmpl`, etc.) ya consumen `ctx["skills_paths"]`. Si creamos `ctx["all_skills_paths"]`, hay que migrar todas las plantillas y mantener 2 variables sincronizadas. La fusión en `build_context` con dedup evita la duplicación y mantiene 1 sola variable. Más simple, menos superficie de bugs.

### A2 — Eliminar `extra_skills` del contexto y mover la lógica al template
**Por qué se descarta**: las plantillas no deberían saber de `project_detect`. La lógica de "qué skills añadir según stack" pertenece al renderer (Python), no a las plantillas (texto). Separación de concerns.

### C1 — Eliminar `agent-template` por completo
**Por qué se descarta**: el template es valioso como referencia humana (un dev nuevo lo lee para entender la estructura de un SUBAGENT.md). El código no lo necesita (usa `_default_subagent_body`), pero la documentación implícita sigue siendo útil. La sanitización (R9) cierra el riesgo de filtración sin perder el beneficio pedagógico.

### C2 — Reemplazar el template entero por un generador
**Por qué se descarta**: YAGNI. `_default_subagent_body` ya existe y es funcional. Añadir un generador sería duplicar trabajo.

### D1 — Test de paridad en Python con pytest
**Por qué se descarta**: el resto del framework (cuando exista) usará `tests/test_*.sh` por coherencia con la portabilidad. Python sería un outlier innecesario.

### D2 — Test que hardcodea nombres de skills
**Por qué se descarta**: el template es agnóstico de stack. Hardcodear `terraform-code-generator-templates` o cualquier skill específica acopla el test a un cliente. El test DEBE descubrir las skills dinámicamente desde `agentic.json#project_detect[]`.

## Diagrama de impacto

```
ANTES (render.py build_context):
  manifest.skills.paths:    ["a", "b"]
  extra_skills (calculado): ["b", "c"]    <- calculado pero ignorado
  ctx["skills_paths"]:      ["a", "b"]    <- usado por opencode.json

DESPUÉS:
  manifest.skills.paths:    ["a", "b"]
  extra_skills (calculado): ["b", "c"]
  ctx["skills_paths"]:      ["a", "b", "c"]   <- unión deduplicada

Cambio en 5 líneas de build_context + 1 helper.
Tests test_cli_adapter_parity.sh y test_agent_template_placeholders.sh
verifican que el cambio funciona y que el render es determinista byte-a-byte.
```

## Compatibilidad hacia atrás

- **Manifests previos**: siguen siendo válidos. R17 lo garantiza. No se añade, renombra ni elimina ningún campo.
- **Adapters regenerados**: el `opencode.json#skills.paths` puede crecer (de 1 a N elementos). Si algún consumer downstream parsea `skills.paths[0]` esperando un único path, rompe. **Mitigación**: opencode es el único adapter con `skills.paths` (gemini y claude lo manejan diferente), y el formato es `["dir1", "dir2", ...]` (lista). Consumers deben iterar, no indexar.
- **Plugins/customizaciones de proyectos downstream**: el cambio en `build_context` es aditivo (más paths, no menos). Proyectos que hardcodean `opencode.json#skills.paths[0]` se romperán — pero esto es un anti-patrón claro.
