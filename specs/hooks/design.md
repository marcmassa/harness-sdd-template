# Diseño — hooks

> Decisiones técnicas para **FEAT-004**. Añade un sistema de hooks CLI-agnóstico al workflow SDD. Scripts shell ejecutables en `hooks/`, declarados en `agentic.json`, invocados por los comandos slash y `hooks/run-hooks.sh`. Sin breaking changes.

## Resumen

El sistema de hooks se compone de 4 piezas:

1. **Manifest**: `agentic.json#hooks[]` — array de definiciones de hook (`event`, `script`, `description`, `on_failure`).
2. **Scripts**: `hooks/*.sh` — scripts shell ejecutables. Reciben contexto vía variables de entorno.
3. **Runner**: `hooks/run-hooks.sh` — ejecuta todos los hooks para un evento dado. Los comandos slash lo invocan.
4. **Validación**: `check.sh` + `tests/test_hooks.sh` — verifican integridad y comportamiento.

## Archivos afectados

| Archivo | Acción | Razón |
|---------|--------|-------|
| `.agents/agentic.json` | modificar | Añadir `hooks: []` y `_template_hooks_examples: [...]` (R1, R10, R16) |
| `hooks/run-hooks.sh` | crear | Script runner que ejecuta hooks por evento (R3, R4) |
| `hooks/on-spec-created_validate.sh` | crear | Scaffold: valida estructura de spec (R7) |
| `hooks/on-feature-done_notify.sh` | crear | Scaffold: notificación de feature completado (R8) |
| `hooks/on-check-pass_ci.sh` | crear | Scaffold: registro de CI (R9) |
| `.agents/commands/spec.md` | modificar | Invocar hooks `on_spec_created` (R6) |
| `.agents/commands/approve.md` | modificar | Invocar hooks `on_spec_approved` (R6) |
| `.agents/commands/implement.md` | modificar | Invocar hooks `on_implementation_start` + `on_implementation_complete` (R6) |
| `.agents/commands/done.md` | modificar | Invocar hooks `on_review_start` + `on_review_complete` + `on_feature_done` (R6) |
| `.agents/commands/check.md` | modificar | Invocar hooks `on_check_pass` (R6) |
| `.agents/bootstrap.sh` | modificar | Comandos `add-hook` y `remove-hook` (R11) |
| `check.sh` | modificar | Sección «Hooks Validation» (R12) |
| `tests/test_hooks.sh` | crear | Test de integridad y comportamiento de hooks (R13) |
| `feature_list.json` | modificar | FEAT-004 → `status: "done"` |
| `progress/progress.md` | modificar | Entrada fechada |
| `specs/hooks/{requirements,design,tasks}.md` | crear | Spec (este archivo) |

## Algoritmo

### A. Schema de `hooks[]` en `agentic.json` (R1, R10, R16)

```jsonc
{
  "hooks": [],                    // Activos (vacío por defecto)
  "_template_hooks_examples": [   // Scaffolds (3 ejemplos)
    {
      "_lifecycle": "scaffold",
      "_intent": "Valida la estructura de spec tras crearla. Promover con add-hook.",
      "event": "on_spec_created",
      "script": "hooks/on-spec-created_validate.sh",
      "description": "Verifica que specs/<feature>/ contiene 3 .md con requisitos EARS",
      "on_failure": "warn"
    },
    {
      "_lifecycle": "scaffold",
      "_intent": "Notifica feature completado. Personalizar para Slack/Jira/etc.",
      "event": "on_feature_done",
      "script": "hooks/on-feature-done_notify.sh",
      "description": "Imprime resumen del feature completado para integraciones externas",
      "on_failure": "ignore"
    },
    {
      "_lifecycle": "scaffold",
      "_intent": "Registra timestamp de check.sh exitoso. Placeholder para CI/CD.",
      "event": "on_check_pass",
      "script": "hooks/on-check-pass_ci.sh",
      "description": "Registra timestamp del último check.sh exitoso",
      "on_failure": "ignore"
    }
  ]
}
```

**Campos de cada entrada en `hooks[]`:**
- `event` (string, requerido) — nombre del evento del ciclo de vida (R2)
- `script` (string, requerido) — ruta al script shell ejecutable
- `description` (string, requerido) — qué hace el hook
- `on_failure` (string, opcional, default `"warn"`) — `"warn"` | `"error"` | `"ignore"`

### B. Eventos del ciclo de vida y su mapping a comandos (R2, R6)

| Evento | Cuándo se dispara | Comando slash que lo invoca |
|--------|-------------------|---------------------------|
| `on_spec_created` | Después de crear `specs/<feature>/{requirements,design,tasks}.md` | `/spec` |
| `on_spec_approved` | Después de cambiar status a `in_progress` | `/approve` |
| `on_implementation_start` | Antes de empezar a ejecutar `tasks.md` | `/implement` |
| `on_implementation_complete` | Después de marcar todas las tareas `[x]` | `/implement` |
| `on_review_start` | Antes de ejecutar la revisión | `/done` |
| `on_review_complete` | Después de verificar trazabilidad R↔test | `/done` |
| `on_feature_done` | Después de cambiar status a `done` | `/done` |
| `on_check_pass` | Después de que `check.sh` pasa exitosamente | `/check` |

### C. Script runner `hooks/run-hooks.sh` (R3, R4, R5)

```bash
#!/bin/bash
# run-hooks.sh — Ejecuta todos los hooks registrados para un evento del ciclo de vida SDD.
#
# Uso: hooks/run-hooks.sh <event> [--feature-id <id>] [--feature-name <name>] [--agent-name <name>]
#
# Variables de entorno disponibles para los hooks:
#   HOOK_EVENT     — el evento que se está procesando
#   ROOT_DIR       — raíz del proyecto
#   FEATURE_ID     — (opcional) ID del feature en feature_list.json
#   FEATURE_NAME   — (opcional) nombre del feature
#   AGENT_NAME     — (opcional) nombre del agente que invoca el hook

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EVENT="${1:-}"
shift 2>/dev/null || true

export ROOT_DIR
export HOOK_EVENT="$EVENT"

while [ $# -gt 0 ]; do
    case "$1" in
        --feature-id)   export FEATURE_ID="$2"; shift 2 ;;
        --feature-name) export FEATURE_NAME="$2"; shift 2 ;;
        --agent-name)   export AGENT_NAME="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "$EVENT" ]; then
    echo "ERROR: event required. Usage: hooks/run-hooks.sh <event> [flags]" >&2
    exit 1
fi

# Leer hooks del manifest
HOOKS=$(python3 -c "
import json, sys
m = json.load(open('$ROOT_DIR/.agents/agentic.json'))
hooks = [h for h in m.get('hooks', []) if h.get('event') == '$EVENT']
for h in hooks:
    print(f'{h[\"script\"]}|{h.get(\"on_failure\", \"warn\")}|{h.get(\"description\", \"\")}')
")

if [ -z "$HOOKS" ]; then
    echo "No hooks registered for event: $EVENT"
    exit 0
fi

OVERALL_EXIT=0
echo "Running hooks for event: $EVENT"

while IFS='|' read -r script on_failure description; do
    [ -z "$script" ] && continue
    echo ""
    echo "── Hook: $script — $description"
    if [ ! -x "$ROOT_DIR/$script" ]; then
        echo "  SKIP: $script not found or not executable"
        continue
    fi
    if bash "$ROOT_DIR/$script"; then
        echo "  ✅ passed"
    else
        rc=$?
        case "$on_failure" in
            error)
                echo "  ❌ FAILED (on_failure=error, aborting)"
                exit $rc
                ;;
            ignore)
                echo "  ⚠️  FAILED (on_failure=ignore, continuing)"
                ;;
            *)
                echo "  ⚠️  FAILED (on_failure=warn, continuing)"
                OVERALL_EXIT=1
                ;;
        esac
    fi
done <<< "$HOOKS"

exit $OVERALL_EXIT
```

### D. Integración con comandos slash (R6)

**Ejemplo: `.agents/commands/spec.md`** — añadir al final:

```markdown
After creating the spec files and updating feature_list.json to spec_ready:
- Run `hooks/run-hooks.sh on_spec_created --feature-id "<feature_id>" --feature-name "<feature_name>"`.
- If hooks fail with on_failure=error, report the failure to the user.
```

**Ejemplo: `.agents/commands/approve.md`** — añadir después de cambiar status:

```markdown
After updating feature_list.json status to in_progress:
- Run `hooks/run-hooks.sh on_spec_approved --feature-id "<feature_id>" --feature-name "<feature_name>"`.
```

**Ejemplo: `.agents/commands/done.md`** — añadir en los puntos correspondientes:

```markdown
Before starting the review:
- Run `hooks/run-hooks.sh on_review_start --feature-id "<feature_id>" --feature-name "<feature_name>" --agent-name "reviewer"`.

After verifying traceability and before marking done:
- Run `hooks/run-hooks.sh on_review_complete --feature-id "<feature_id>" --feature-name "<feature_name>"`.

After marking feature as done:
- Run `hooks/run-hooks.sh on_feature_done --feature-id "<feature_id>" --feature-name "<feature_name>"`.
```

### E. Scaffolds de ejemplo (R7, R8, R9)

**`hooks/on-spec-created_validate.sh`:**

```bash
#!/bin/bash
# Hook: on_spec_created — valida estructura del spec recién creado
set -euo pipefail
SPEC_DIR="$ROOT_DIR/specs/${FEATURE_NAME:-}"
if [ ! -d "$SPEC_DIR" ]; then
    echo "WARN: spec directory $SPEC_DIR not found"
    exit 0
fi
COUNT=$(find "$SPEC_DIR" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')
if [ "$COUNT" -ne 3 ]; then
    echo "WARN: expected 3 .md files in $SPEC_DIR, found $COUNT"
fi
if ! grep -q '^### R[0-9]' "$SPEC_DIR/requirements.md" 2>/dev/null; then
    echo "WARN: no EARS requirements (### R<n>) found in $SPEC_DIR/requirements.md"
fi
echo "Spec structure validation complete"
```

**`hooks/on-feature-done_notify.sh`:**

```bash
#!/bin/bash
# Hook: on_feature_done — imprime resumen del feature completado
echo "Feature completed: ${FEATURE_ID:-?} — ${FEATURE_NAME:-?}"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Agent: ${AGENT_NAME:-unknown}"
echo ""
echo "TODO: integrate with Slack, Jira, or notification system"
```

**`hooks/on-check-pass_ci.sh`:**

```bash
#!/bin/bash
# Hook: on_check_pass — registra timestamp del último check.sh exitoso
mkdir -p "$ROOT_DIR/progress"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$ROOT_DIR/progress/last-check-pass.txt"
echo "CI timestamp recorded in progress/last-check-pass.txt"
```

### F. Comandos bootstrap (R11)

**`add-hook --event <event> --script <path> [--description <desc>] [--on-failure <warn|error|ignore>]`**:
1. Añade la entrada al array `hooks[]` de `agentic.json` vía `python3`.
2. Si `--script` no apunta a un archivo existente, pregunta si desea crear un template básico.
3. Guarda el manifest.

**`remove-hook <event> <script>`**:
1. Elimina la entrada con `event` y `script` coincidentes del array `hooks[]`.
2. Guarda el manifest.
3. NO elimina el archivo en disco.

### G. Validación en `check.sh` (R12)

```bash
section "Hooks Validation"
python3 /dev/stdin <<'PYEOF'
import json, os, sys
with open('.agents/agentic.json') as f:
    m = json.load(f)
hooks = m.get('hooks', [])
known_events = {
    "on_spec_created", "on_spec_approved",
    "on_implementation_start", "on_implementation_complete",
    "on_review_start", "on_review_complete",
    "on_feature_done", "on_check_pass"
}
errors = []
warnings = []

if not os.path.isfile('hooks/run-hooks.sh'):
    errors.append("hooks/run-hooks.sh not found")
elif not os.access('hooks/run-hooks.sh', os.X_OK):
    errors.append("hooks/run-hooks.sh is not executable")

for h in hooks:
    script = h.get('script', '')
    event = h.get('event', '?')
    if not os.path.isfile(script):
        errors.append(f"hook script '{script}' (event={event}) not found")
    elif not os.access(script, os.X_OK):
        warnings.append(f"hook script '{script}' is not executable")
    if event not in known_events:
        warnings.append(f"hook event '{event}' is not a standard SDD event (custom?)")

for e in errors:
    print(f"[ERROR] {e}")
for w in warnings:
    print(f"[WARN]  {w}")
if errors:
    sys.exit(1)
if not hooks:
    print("[OK]    No hooks registered (hooks system is idle)")
else:
    print(f"[OK]    {len(hooks)} hook(s) registered, run-hooks.sh present")
PYEOF
```

### H. Test `tests/test_hooks.sh` (R13)

```bash
#!/bin/bash
# Test: sistema de hooks — runner, fallos, y políticas de on_failure
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PASS=0
FAIL=0

# 1. Ejecutar hooks para un evento sin hooks registrados → exit 0
echo "--- Test 1: no hooks registered for event ---"
if hooks/run-hooks.sh on_spec_created; then
    echo "PASS: exit 0 for event with no hooks"
    PASS=$((PASS + 1))
else
    echo "FAIL: expected exit 0 for event with no hooks"
    FAIL=$((FAIL + 1))
fi

# 2. Verificar que run-hooks.sh existe y es ejecutable
echo ""
echo "--- Test 2: run-hooks.sh exists and is executable ---"
if [ -x "hooks/run-hooks.sh" ]; then
    echo "PASS: hooks/run-hooks.sh is executable"
    PASS=$((PASS + 1))
else
    echo "FAIL: hooks/run-hooks.sh missing or not executable"
    FAIL=$((FAIL + 1))
fi

# 3. Verificar que los hooks de ejemplo existen
echo ""
echo "--- Test 3: example hooks exist ---"
EXAMPLES=(
    "hooks/on-spec-created_validate.sh"
    "hooks/on-feature-done_notify.sh"
    "hooks/on-check-pass_ci.sh"
)
all_ok=1
for f in "${EXAMPLES[@]}"; do
    if [ -f "$f" ]; then
        echo "  OK: $f exists"
    else
        echo "  MISSING: $f"
        all_ok=0
    fi
done
if [ "$all_ok" -eq 1 ]; then
    echo "PASS: all example hooks exist"
    PASS=$((PASS + 1))
else
    echo "FAIL: some example hooks missing"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
echo "PASS: test_hooks"
```

## Manejo de Errores

| Condición | Respuesta |
|-----------|-----------|
| `hooks` está vacío o ausente | `run-hooks.sh` imprime "No hooks registered" y sale con 0. Sin efecto en el workflow. |
| Un hook script no existe o no es ejecutable | `run-hooks.sh` hace SKIP con mensaje. `check.sh` reporta error. |
| Un hook falla con `on_failure: "ignore"` | Continúa con el siguiente hook. El workflow no se interrumpe. |
| Un hook falla con `on_failure: "warn"` | Muestra warning, continúa. `run-hooks.sh` sale con 1 al final si algún hook falló. |
| Un hook falla con `on_failure: "error"` | `run-hooks.sh` sale inmediatamente con el exit code del hook. El comando slash debe detectarlo y reportar. |
| `run-hooks.sh` recibe un evento desconocido | Busca hooks registrados para ese evento en `agentic.json`. Si no hay, exit 0. |
| El manifest no es JSON válido | `run-hooks.sh` falla al parsear con python3. El error se muestra en stderr. |

## Alternativas Descartadas

### A1 — Hooks como plugins TypeScript (como OpenCode)
**Por qué se descarta**: no es CLI-agnóstico. Los hooks shell funcionan en cualquier entorno (macOS, Linux, CI). Un proyecto puede envolver un script shell que invoque TypeScript si lo desea.

### A2 — Hooks inline en el manifest (cuerpo del script en `agentic.json`)
**Por qué se descarta**: mezcla código con configuración. Los scripts en archivos separados son más fáciles de editar, testear, y versionar.

### B1 — Solo 4 eventos (spec_created, approved, done, check_pass)
**Por qué se descarta**: los 8 eventos cubren granularidad útil (pre/post implementación, pre/post revisión). Si un proyecto no los usa, simplemente no registra hooks para esos eventos.

### C1 — Ejecutar hooks en paralelo
**Por qué se descarta**: los hooks pueden tener dependencias (primero validar, luego notificar). El orden secuencial (por orden de declaración) es predecible y fácil de razonar.

### D1 — Hooks como feature independiente del manifest
**Por qué se descarta**: rompe el principio de «single source of truth». Todo lo que el framework gestiona vive en `agentic.json`.

## Diagrama de impacto

```
ANTES:
  /spec    → crea spec → actualiza feature_list.json → fin
  /approve → cambia status → fin
  /done    → revisa → cambia status → fin

DESPUÉS:
  /spec    → crea spec → actualiza feature_list.json
           → hooks/run-hooks.sh on_spec_created → (validación, lint, etc.) → fin
  /approve → cambia status
           → hooks/run-hooks.sh on_spec_approved → (notificación, CI trigger) → fin
  /done    → hooks/run-hooks.sh on_review_start
           → revisa trazabilidad
           → hooks/run-hooks.sh on_review_complete
           → cambia status a done
           → hooks/run-hooks.sh on_feature_done → (changelog, release) → fin
```

## Compatibilidad hacia atrás

- **Manifests sin `hooks`**: el campo es opcional. `run-hooks.sh` recibe evento, busca en manifest (vacío), imprime "No hooks registered", sale 0. Sin efecto.
- **Comandos slash**: si `hooks/run-hooks.sh` no existe, los comandos slash simplemente ignoran ese paso (el script no se ejecuta). Esto permite que proyectos sin el sistema de hooks sigan funcionando.
- **Sub-agents existentes**: no cambian. Los hooks son adicionales, no reemplazan nada.
