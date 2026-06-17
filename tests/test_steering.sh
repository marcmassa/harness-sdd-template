#!/bin/bash
# Test: integridad del sistema de steering (FEAT-003)
# Verifica que los steering files declarados en agentic.json:
#   (a) aparecen en opencode.json#instructions[]
#   (b) existen en disco
#   (c) tienen YAML frontmatter válido con name y description
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PASS=0
FAIL=0

# 1. Verificar que los steering files globales aparecen en opencode.json#instructions[]
#    y los per-agent en opencode.json#agent.<name>.instructions[]
echo "--- Test 1: steering files in correct opencode.json locations ---"
STEERING_GLOBAL=$(python3 -c "
import json
m = json.load(open('.agents/agentic.json'))
for s in m.get('steering', []):
    applies = s.get('applies_to', ['*'])
    if '*' in applies:
        print(s['file'])
")
STEERING_PER_AGENT=$(python3 -c "
import json
m = json.load(open('.agents/agentic.json'))
for s in m.get('steering', []):
    applies = s.get('applies_to', ['*'])
    if '*' not in applies:
        for agent in applies:
            print(f'{s[\"file\"]} -> agent.{agent}')
")
if [ -z "$STEERING_GLOBAL" ] && [ -z "$STEERING_PER_AGENT" ]; then
    echo "SKIP: no steering files declared in agentic.json"
    PASS=$((PASS + 1))
else
    all_ok=1
    # Check global steering
    if [ -n "$STEERING_GLOBAL" ]; then
        while IFS= read -r f; do
            [ -z "$f" ] && continue
            if python3 -c "
import json
cfg = json.load(open('opencode.json'))
assert '$f' in cfg.get('instructions', [])
" 2>/dev/null; then
                echo "  OK: '$f' found in opencode.json#instructions[] (global)"
            else
                echo "  MISSING: '$f' not in opencode.json#instructions[]"
                all_ok=0
            fi
        done <<< "$STEERING_GLOBAL"
    fi
    # Check per-agent steering
    if [ -n "$STEERING_PER_AGENT" ]; then
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            f=$(echo "$line" | awk '{print $1}')
            agent_name=$(echo "$line" | awk '{print $3}')
            if python3 -c "
import json
cfg = json.load(open('opencode.json'))
agent = cfg.get('agent', {}).get('$agent_name', {})
agent_instructions = agent.get('instructions', [])
assert '$f' in agent_instructions, f\"{agent_instructions} does not contain '$f'\"
" 2>/dev/null; then
                echo "  OK: '$f' found in opencode.json#agent.$agent_name.instructions[] (per-agent)"
            else
                echo "  WARN: '$f' NOT in opencode.json#agent.$agent_name.instructions[] (agent '$agent_name' may not be active)"
            fi
        done <<< "$STEERING_PER_AGENT"
    fi
    if [ "$all_ok" -eq 1 ]; then
        echo "PASS: all global steering files in opencode.json#instructions[]"
        PASS=$((PASS + 1))
    else
        echo "FAIL: some global steering files missing from instructions"
        FAIL=$((FAIL + 1))
    fi
fi

# 2. Verificar que todos los steering files declarados existen en disco
echo ""
echo "--- Test 2: steering files exist on disk ---"
all_exist=1
python3 -c "
import json, os, sys
m = json.load(open('.agents/agentic.json'))
for s in m.get('steering', []):
    fpath = s['file']
    if not os.path.isfile(fpath):
        print(f'MISSING: {fpath}')
        sys.exit(1)
    print(f'OK: {fpath}')
sys.exit(0)
" && rc=0 || rc=1
if [ "$rc" -eq 0 ]; then
    echo "PASS: all steering files exist on disk"
    PASS=$((PASS + 1))
else
    echo "FAIL: some steering files missing"
    FAIL=$((FAIL + 1))
fi

# 3. Verificar YAML frontmatter en cada steering file
echo ""
echo "--- Test 3: YAML frontmatter validation ---"
all_valid=1
for f in steering/*.md; do
    [ -f "$f" ] || continue
    content=$(cat "$f")
    if ! echo "$content" | head -1 | grep -q '^---$'; then
        echo "  MISSING: $f does not start with YAML frontmatter (---)"
        all_valid=0
        continue
    fi
    if ! echo "$content" | grep -q '^name:'; then
        echo "  MISSING: $f frontmatter missing 'name'"
        all_valid=0
        continue
    fi
    if ! echo "$content" | grep -q '^description:'; then
        echo "  MISSING: $f frontmatter missing 'description'"
        all_valid=0
        continue
    fi
    echo "  OK: $f has valid YAML frontmatter"
done
if [ "$all_valid" -eq 1 ]; then
    echo "PASS: all steering files have valid YAML frontmatter"
    PASS=$((PASS + 1))
else
    echo "FAIL: some steering files have invalid/missing frontmatter"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
echo "PASS: test_steering"
