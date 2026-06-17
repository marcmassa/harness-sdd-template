#!/bin/bash
set -uo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EVENT="${1:-}"; shift 2>/dev/null || true
export ROOT_DIR HOOK_EVENT="$EVENT"
while [ $# -gt 0 ]; do
    case "$1" in
        --feature-id) export FEATURE_ID="$2"; shift 2 ;;
        --feature-name) export FEATURE_NAME="$2"; shift 2 ;;
        --agent-name) export AGENT_NAME="$2"; shift 2 ;;
        *) shift ;;
    esac
done
[ -z "$EVENT" ] && { echo "ERROR: event required" >&2; exit 1; }
MANIFEST="$ROOT_DIR/.agents/agentic.json"
[ ! -f "$MANIFEST" ] && { echo "No manifest — skipping hooks"; exit 0; }
HOOKS=$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
for h in m.get('hooks',[]):
    if h.get('event')=='$EVENT': print(f'{h[\"script\"]}|{h.get(\"on_failure\",\"warn\")}|{h.get(\"description\",\"\")}')
" 2>/dev/null || true)
[ -z "$HOOKS" ] && { echo "No hooks for: $EVENT"; exit 0; }
echo "Running hooks for: $EVENT"; OVERALL_EXIT=0
while IFS='|' read -r script on_failure desc; do
    [ -z "$script" ] && continue
    echo "  -- $script — $desc"
    if [ ! -x "$ROOT_DIR/$script" ]; then echo "  SKIP: not executable"; continue; fi
    if bash "$ROOT_DIR/$script"; then echo "  PASSED"; else
        rc=$?; case "$on_failure" in
            error) echo "  FAILED (aborting)"; exit $rc ;;
            ignore) echo "  FAILED (ignored)" ;;
            *) echo "  FAILED (warn)"; OVERALL_EXIT=1 ;;
        esac
    fi
done <<<"$HOOKS"
exit $OVERALL_EXIT
