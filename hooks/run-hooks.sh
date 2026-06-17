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

# Read hooks from manifest
MANIFEST="$ROOT_DIR/.agents/agentic.json"
if [ ! -f "$MANIFEST" ]; then
    echo "No manifest found at $MANIFEST — skipping hooks"
    exit 0
fi

HOOKS=$(python3 -c "
import json, sys
try:
    m = json.load(open('$MANIFEST'))
    hooks = [h for h in m.get('hooks', []) if h.get('event') == '$EVENT']
    for h in hooks:
        script = h['script']
        on_failure = h.get('on_failure', 'warn')
        desc = h.get('description', '')
        print(f'{script}|{on_failure}|{desc}')
except Exception as e:
    print(f'ERROR:{e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || true)

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
        if [ ! -f "$ROOT_DIR/$script" ]; then
            echo "  SKIP: $script not found"
        else
            echo "  SKIP: $script not executable (run: chmod +x $script)"
        fi
        continue
    fi
    if bash "$ROOT_DIR/$script"; then
        echo "  PASSED"
    else
        rc=$?
        case "$on_failure" in
            error)
                echo "  FAILED (on_failure=error, aborting)"
                exit $rc
                ;;
            ignore)
                echo "  FAILED (on_failure=ignore, continuing)"
                ;;
            *)
                echo "  FAILED (on_failure=warn, continuing)"
                OVERALL_EXIT=1
                ;;
        esac
    fi
done <<< "$HOOKS"

exit $OVERALL_EXIT
