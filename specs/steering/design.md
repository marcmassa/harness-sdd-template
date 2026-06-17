# Diseño — steering

> Decisiones técnicas para **FEAT-003**. Formaliza el concepto de steering files como ciudadanos de primera clase en `agentic.json`. Extiende el renderer, añade scaffolding, comandos bootstrap, y validación. Cero breaking changes.

## Resumen

El steering (archivos que dirigen el comportamiento de los agentes) ya existe de forma implícita en el template: `agentic.json#instructions[]` es una lista plana que el renderer vuelca a `opencode.json#instructions[]`. Este feature lo formaliza:

1. **Campo `steering[]` en `agentic.json`** — cada entrada declara un steering file con nombre, ruta, descripción, y scope (global o por agente).
2. **Directorio `steering/`** — los archivos `.md` viven aquí, con frontmatter YAML.
3. **Renderer extendido** — `build_context` incluye los steering files en `ctx["steering_files"]`. `render_opencode` los añade a `instructions[]` (global) y a `agent.<name>.instructions` (per-agent). Gemini y Claude los añaden al `instructions[]` global.
4. **Scaffolding** — dos ejemplos (`global-conventions.md`, `implementer-patterns.md`) en `steering/` + campo `_template_steering_examples[]` en el manifest.
5. **Comandos bootstrap** — `add-steering` y `remove-steering`.
6. **Validación** — `check.sh` verifica existencia de archivos y YAML frontmatter. Test en `tests/test_steering.sh`.

## Archivos afectados

| Archivo | Acción | Razón |
|---------|--------|-------|
| `.agents/agentic.json` | modificar | Añadir `steering: []` y `_template_steering_examples: [...]` (R1, R7, R13) |
| `.agents/adapters/_common/render.py` | modificar | `build_context` incluye steering; `render_opencode` los mapea a instructions (R3, R4, R11) |
| `.agents/bootstrap.sh` | modificar | Comandos `add-steering` y `remove-steering` (R8, R9) |
| `steering/global-conventions.md` | crear | Scaffold de ejemplo global (R5) |
| `steering/implementer-patterns.md` | crear | Scaffold de ejemplo por agente (R6) |
| `specs/templates/steering.md` | crear | Plantilla base para steering files (R14) |
| `AGENTS.md` | modificar | Añadir `steering/` al Repository Map (R12) |
| `check.sh` | modificar | Sección «Steering Validation» (R10) |
| `tests/test_steering.sh` | crear | Test de integridad del steering (R15) |
| `feature_list.json` | modificar | FEAT-003 → `status: "done"` |
| `progress/progress.md` | modificar | Entrada fechada |
| `specs/steering/{requirements,design,tasks}.md` | crear | Spec (este archivo) |

## Algoritmo

### A. Schema de `steering[]` en `agentic.json` (R1, R7, R13)

```jsonc
{
  // ... campos existentes ...
  "steering": [
    {
      "name": "global-conventions",
      "file": "steering/global-conventions.md",
      "description": "Convenciones globales del proyecto que aplican a todos los agentes",
      "applies_to": ["*"]
    },
    {
      "name": "implementer-patterns",
      "file": "steering/implementer-patterns.md",
      "description": "Patrones de código y convenciones para el implementer",
      "applies_to": ["implementer"]
    }
  ],
  "_template_steering_examples": [
    {
      "_lifecycle": "scaffold",
      "_intent": "Ejemplo de steering global. Copia, personaliza, y añade a steering[].",
      "name": "global-conventions",
      "file": "steering/global-conventions.md",
      "description": "Convenciones globales del proyecto que aplican a todos los agentes",
      "applies_to": ["*"]
    },
    {
      "_lifecycle": "scaffold",
      "_intent": "Ejemplo de steering por agente. Copia, personaliza, y añade a steering[].",
      "name": "implementer-patterns",
      "file": "steering/implementer-patterns.md",
      "description": "Patrones de código y convenciones para el implementer",
      "applies_to": ["implementer"]
    }
  ]
}
```

**Campos de cada entrada en `steering[]`:**
- `name` (string, requerido, único) — identificador
- `file` (string, requerido) — ruta relativa al steering file `.md`
- `description` (string, requerido) — qué contiene y para qué sirve
- `applies_to` (array de strings, opcional, default `["*"]`) — nombres de sub-agentes o `"*"` para global

### B. Estructura de un steering file (R2, R14)

```markdown
---
name: global-conventions
description: "Convenciones globales del proyecto que aplican a todos los agentes"
applies_to:
  - "*"
---

# Convenciones Globales

## Contexto

<!-- TODO: describir el contexto del proyecto -->

## Reglas

1. ...
2. ...

## Anti-patrones

- ...
- ...
```

El frontmatter YAML replica los metadatos del manifest. Esto permite que el archivo sea auto-contenido (un agente que lea el archivo directamente sabe para qué es y a quién aplica).

### C. Extensión del renderer (R3, R4, R11)

**En `build_context` — añadir al dict de retorno:**

```python
# En build_context (junto con los demás campos del contexto):
steering_global: list[str] = []
steering_per_agent: dict[str, list[str]] = {}
for s in manifest.get("steering", []):
    applies = s.get("applies_to", ["*"])
    if "*" in applies:
        steering_global.append(s["file"])
    else:
        for agent_name in applies:
            steering_per_agent.setdefault(agent_name, []).append(s["file"])

# En el dict de retorno:
"steering_global": steering_global,
"steering_per_agent": steering_per_agent,
```

**En `render_opencode` — añadir a instructions y agent instructions:**

```python
# Después de construir cfg["instructions"]:
# Añadir steering files globales
cfg["instructions"] = list(cfg["instructions"]) + ctx["steering_global"]

# Para cada agente con steering files específicos:
for agent_name, files in ctx["steering_per_agent"].items():
    if agent_name in cfg["agent"]:
        if "instructions" not in cfg["agent"][agent_name]:
            cfg["agent"][agent_name]["instructions"] = []
        cfg["agent"][agent_name]["instructions"].extend(files)
```

**En `build_context` para gemini y claude** — los steering files se añaden a `steering_all = steering_global + flatten(steering_per_agent.values())` y se inyectan en el contexto para que los templates `.tmpl` los incluyan en sus `instructions`.

### D. Scaffolding de steering files (R5, R6)

**`steering/global-conventions.md`:**

```markdown
---
name: global-conventions
description: "Convenciones globales del proyecto que aplican a todos los agentes"
applies_to:
  - "*"
---

# Convenciones Globales

## Contexto

<!-- TODO: describir el contexto del proyecto, su propósito, y su stack tecnológico -->

## Reglas Generales

1. <!-- TODO: regla 1 -->
2. <!-- TODO: regla 2 -->

## Convenciones de Nombrado

- <!-- TODO: convención 1 -->

## Anti-patrones

- <!-- TODO: anti-patrón 1 -->

## Referencias

- `DESIGN.md` — arquitectura global
- `AGENTS.md` — mapa de navegación
```

**`steering/implementer-patterns.md`:**

```markdown
---
name: implementer-patterns
description: "Patrones de código y convenciones para el implementer"
applies_to:
  - implementer
---

# Patrones del Implementer

## Contexto

<!-- TODO: describir las convenciones de código específicas del proyecto -->

## Estilo de Código

1. <!-- TODO: regla de estilo 1 -->

## Estructura de Archivos

- <!-- TODO: convención de estructura 1 -->

## Testing

1. <!-- TODO: convención de testing 1 -->

## Anti-patrones

- <!-- TODO: anti-patrón de implementación 1 -->
```

### E. Comandos bootstrap (R8, R9)

**`add-steering <name>`** en `bootstrap.sh`:
1. Pide `--description` y `--applies-to` (o interactivo si TTY).
2. Crea `steering/` si no existe.
3. Copia `specs/templates/steering.md` a `steering/<name>.md` con el frontmatter personalizado.
4. Añade entrada a `agentic.json#steering[]`.
5. Guarda el manifest.

**`remove-steering <name>`** en `bootstrap.sh`:
1. Elimina la entrada de `agentic.json#steering[]` con ese `name`.
2. Guarda el manifest.
3. NO elimina el archivo en disco (el usuario decide).

### F. Validación en `check.sh` (R10)

```bash
section "Steering Validation"
if python3 -c "import json; m=json.load(open('.agents/agentic.json')); print(len(m.get('steering',[])))" 2>/dev/null; then
    python3 /dev/stdin <<'PYEOF'
import json, os, sys
with open('.agents/agentic.json') as f:
    m = json.load(f)
steering = m.get('steering', [])
errors = []
warnings = []
for s in steering:
    fpath = s.get('file', '')
    if not os.path.isfile(fpath):
        errors.append(f"steering '{s.get('name','?')}': file '{fpath}' not found")
    else:
        # Verificar YAML frontmatter
        with open(fpath) as sf:
            content = sf.read()
        if not content.startswith('---'):
            warnings.append(f"steering '{s.get('name','?')}': missing YAML frontmatter")
# Verificar archivos en steering/ no referenciados
if os.path.isdir('steering'):
    declared = {s['file'] for s in steering}
    for f in os.listdir('steering'):
        fpath = f"steering/{f}"
        if fpath not in declared and f.endswith('.md'):
            warnings.append(f"steering file '{fpath}' not declared in agentic.json#steering[]")
for e in errors:
    print(f"[ERROR] {e}")
for w in warnings:
    print(f"[WARN]  {w}")
if errors:
    sys.exit(1)
print(f"[OK]    {len(steering)} steering file(s) valid")
PYEOF
    # ... pass/fail ...
fi
```

### G. Test `tests/test_steering.sh` (R15)

```bash
#!/bin/bash
# Test: integridad del sistema de steering
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

FAIL=0

# 1. Verificar que opencode.json#instructions incluye steering files globales
STEERING_GLOBAL=$(python3 -c "
import json
m = json.load(open('.agents/agentic.json'))
for s in m.get('steering', []):
    if s.get('applies_to', ['*']) == ['*'] or '*' in s.get('applies_to', []):
        print(s['file'])")

if [ -n "$STEERING_GLOBAL" ]; then
    while IFS= read -r f; do
        if ! python3 -c "import json; cfg=json.load(open('opencode.json')); assert '$f' in cfg.get('instructions',[])" 2>/dev/null; then
            echo "FAIL: steering file '$f' not in opencode.json#instructions[]"
            FAIL=1
        fi
    done <<< "$STEERING_GLOBAL"
fi

# 2. Verificar que los steering files existen en disco
python3 -c "
import json, os
m = json.load(open('.agents/agentic.json'))
for s in m.get('steering', []):
    assert os.path.isfile(s['file']), f'{s[\"file\"]} not found'
print('All steering files exist on disk')
"

# 3. Verificar YAML frontmatter en cada steering file
python3 -c "
import os
for f in os.listdir('steering'):
    if f.endswith('.md'):
        with open(f'steering/{f}') as sf:
            content = sf.read()
        assert content.startswith('---'), f'steering/{f}: missing YAML frontmatter'
        # Verificar que tiene al menos name y description
        parts = content.split('---')
        assert len(parts) >= 3, f'steering/{f}: invalid YAML frontmatter'
        frontmatter = parts[1]
        assert 'name:' in frontmatter, f'steering/{f}: missing name in frontmatter'
        assert 'description:' in frontmatter, f'steering/{f}: missing description in frontmatter'
print('All steering files have valid YAML frontmatter')
"

if [ "$FAIL" -eq 1 ]; then
    exit 1
fi
echo "PASS: test_steering"
```

## Manejo de Errores

| Condición | Respuesta |
|-----------|-----------|
| `steering[]` está vacío o ausente en `agentic.json` | El renderer se comporta como antes (sin steering files en instructions). R13 lo garantiza. |
| Un `steering[].file` no existe en disco | `check.sh` reporta warning. El renderer no falla (omite ese archivo del array de instructions). |
| Un steering file no tiene YAML frontmatter | `check.sh` reporta warning. El renderer lo incluye igual (el contenido sigue siendo markdown válido). |
| `applies_to` referencia un agente que no existe | `check.sh` reporta warning. El renderer ignora ese mapeo (no hay agente al que asignarlo). |
| Dos steering entries tienen el mismo `name` | `check.sh` reporta error (nombres duplicados). Bootstrap `add-steering` rechaza nombres duplicados. |
| El directorio `steering/` tiene archivos `.md` no declarados | `check.sh` reporta warning. No afecta al render. |

## Alternativas Descartadas

### A1 — Poner steering files en `.agents/steering/`
**Por qué se descarta**: `.agents/` es maquinaria del framework (adapters, renderer, bootstrap). Los steering files son contenido del proyecto, igual que `specs/` y `progress/`. Ponerlos en `steering/` a nivel raíz los hace visibles y editables sin navegar la maquinaria interna.

### A2 — Usar `applies_when` en lugar de `applies_to`
**Por qué se descarta**: `applies_when` evalúa condiciones del sistema de archivos (globs, file_exists). Los steering files no necesitan activación condicional por stack — el usuario sabe a qué agente aplican. `applies_to` es más simple y directo.

### B1 — Mapear steering files a `agent.<name>.prompt` en lugar de `instructions`
**Por qué se descarta**: el `prompt` de cada agente ya es un stub que redirige a `SUBAGENT.md`. Añadir steering files al `prompt` mezclaría dos fuentes de verdad. Es más limpio usar `agent.<name>.instructions` (array separado) que opencode carga en paralelo al prompt.

### C1 — Eliminar steering files de `instructions[]` global y solo usar per-agent
**Por qué se descarta**: Gemini CLI y Claude Code no tienen `instructions` per-agent. Los steering files per-agent deben cargarse en el contexto global para esos CLIs. El approach híbrido (global + per-agent donde se soporte) maximiza compatibilidad.

### D1 — Auto-scaffoldear steering files desde `_template_steering_examples` como se hace con sub-agents
**Por qué se descarta**: los steering files son más simples que los sub-agents (un solo `.md`). El comando `add-steering` es suficiente. No necesitan el ciclo completo de 3 etapas.

## Diagrama de impacto

```
ANTES (agestic.json):
  instructions: ["AGENTS.md", ".agents/harness/CONVENTION.md"]
  → opencode.json#instructions: ["AGENTS.md", ".agents/harness/CONVENTION.md"]
  → todos los agentes comparten el mismo contexto de steering

DESPUÉS:
  instructions: ["AGENTS.md", ".agents/harness/CONVENTION.md"]
  steering: [
    {name: "global-conventions",  file: "steering/global-conventions.md",
     applies_to: ["*"]},
    {name: "implementer-patterns", file: "steering/implementer-patterns.md",
     applies_to: ["implementer"]},
  ]
  → opencode.json#instructions: [..., "steering/global-conventions.md"]
  → opencode.json#agent.implementer.instructions: ["steering/implementer-patterns.md"]
  → el implementer lee ambos (global + su steering específico)
```

## Compatibilidad hacia atrás

- **Manifests sin `steering`**: el campo es opcional. Si no existe, `build_context` devuelve `steering_global: []` y `steering_per_agent: {}`. El renderer no añade nada. Comportamiento idéntico al anterior.
- **Adapters regenerados**: `opencode.json#instructions[]` puede crecer (más archivos). Si algún consumer downstream parsea `instructions` asumiendo un número fijo de entradas, puede romper. **Mitigación**: `instructions` siempre ha sido un array de longitud variable. Consumers deben iterar, no indexar.
- **Sub-agents existentes**: no cambian. El steering es aditivo (más contexto, no menos).
