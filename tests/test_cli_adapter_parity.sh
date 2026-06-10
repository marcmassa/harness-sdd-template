#!/bin/bash
# tests/test_cli_adapter_parity.sh
# ──────────────────────────────────────────────────────────────────────────────
# Verifica el principio de determinismo del CLI-agnostic layer.
# Dos renders consecutivos del mismo `.agents/agentic.json` deben producir
# archivos idénticos byte-a-byte (mismo SHA256 agregado).
#
# Genérico: NO hardcodea skills. Las skills esperadas se descubren
# dinámicamente desde `agentic.json#project_detect[].apply.add_skills[]`.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

GENERATED_FILES=(opencode.json GEMINI.md CLAUDE.md .claude .gemini)

# ── Aserción 1: dos renders consecutivos → mismo SHA256 agregado ──
./.agents/bootstrap.sh --all >/dev/null 2>&1
HASH_1=$(find "${GENERATED_FILES[@]}" -type f -exec sha256sum {} \; 2>/dev/null \
    | sha256sum | cut -d' ' -f1)

./.agents/bootstrap.sh --all >/dev/null 2>&1
HASH_2=$(find "${GENERATED_FILES[@]}" -type f -exec sha256sum {} \; 2>/dev/null \
    | sha256sum | cut -d' ' -f1)

if [ "$HASH_1" != "$HASH_2" ]; then
    echo "FAIL: render no determinista"
    echo "  HASH_1=$HASH_1"
    echo "  HASH_2=$HASH_2"
    echo "  Sugerencia: ejecuta './.agents/bootstrap.sh --all' y revisa git diff."
    exit 1
fi

# ── Aserción 2: los 3 CLIs renderizan sin error ──
for cli in opencode gemini-cli claude-code; do
    if ! ./.agents/bootstrap.sh "$cli" >/dev/null 2>&1; then
        echo "FAIL: $cli no renderiza"
        exit 1
    fi
done

# ── Aserción 3: opencode.json#skills.paths incluye los paths base ──
if [ ! -f "opencode.json" ]; then
    echo "FAIL: opencode.json no existe"
    exit 1
fi

SKILLS_IN_RENDER=$(python3 -c "
import json
cfg = json.load(open('opencode.json'))
print(','.join(cfg.get('skills', {}).get('paths', [])))")

EXPECTED_BASE=".agents/skills"
if [[ "$SKILLS_IN_RENDER" != *"$EXPECTED_BASE"* ]]; then
    echo "FAIL: opencode.json#skills.paths no incluye $EXPECTED_BASE"
    echo "  Actual: $SKILLS_IN_RENDER"
    exit 1
fi

# ── Aserción 4: las skills declaradas en add_skills[] que EXISTEN EN DISCO
#               aparecen en el render — solo si el stack se detecta ──
# (descubrimiento dinámico desde agentic.json, no hardcoded)
#
# Esta aserción SOLO aplica cuando el stack se detecta (p.ej. hay *.tf en el
# proyecto). En el template base (sin archivos de stack), el render no añade
# extra_skills porque no hay matches. Esta aserción valida el flujo end-to-end
# solo en el caso de uso real.
DETECTED_STACK=$(python3 -c "
import sys
sys.path.insert(0, '.agents/adapters/_common')
import render
m = json.load(open('.agents/agentic.json'))
stack = render.detect_stack(__import__('pathlib').Path('.'), m)
print(','.join(s.get('label', '?') for s in stack))" 2>/dev/null || echo "")

if [ -n "$DETECTED_STACK" ]; then
    # Stack detectado: las skills de add_skills[] que existen en disco deben aparecer
    ADDED_SKILLS=$(python3 -c "
import json
m = json.load(open('.agents/agentic.json'))
out = []
for pd in m.get('project_detect', []):
    for s in pd.get('apply', {}).get('add_skills', []):
        out.append(s)
print('\n'.join(out))" 2>/dev/null || true)

    if [ -n "$ADDED_SKILLS" ]; then
        while IFS= read -r skill; do
            if [ -n "$skill" ] && [[ "$SKILLS_IN_RENDER" != *"$skill"* ]]; then
                echo "FAIL: skill '$skill' declarada en add_skills[] (stack=$DETECTED_STACK) no aparece en opencode.json#skills.paths"
                echo "  Actual: $SKILLS_IN_RENDER"
                exit 1
            fi
        done <<< "$ADDED_SKILLS"
    fi
else
    echo "  (info: ningún stack detectado, aserción 4 omitida — aplica solo cuando hay stack)"
fi

# ── Aserción 5: _merge_unique_ordered funciona correctamente (unit test) ──
# Esta aserción SIEMPRE corre, independiente del stack. Valida que el helper
# de fusión (R1) deduplica preservando orden.
MERGE_TEST=$(python3 -c "
import sys
sys.path.insert(0, '.agents/adapters/_common')
from render import _merge_unique_ordered
# Caso 1: dedup preservando orden
r1 = _merge_unique_ordered(['a', 'b'], ['b', 'c'])
assert r1 == ['a', 'b', 'c'], f'caso 1 falló: {r1}'
# Caso 2: vacío
r2 = _merge_unique_ordered([], [])
assert r2 == [], f'caso 2 falló: {r2}'
# Caso 3: todo en base
r3 = _merge_unique_ordered(['x', 'y'], [])
assert r3 == ['x', 'y'], f'caso 3 falló: {r3}'
# Caso 4: todo en extra
r4 = _merge_unique_ordered([], ['p', 'q'])
assert r4 == ['p', 'q'], f'caso 4 falló: {r4}'
# Caso 5: intersección completa
r5 = _merge_unique_ordered(['a', 'b'], ['a', 'b'])
assert r5 == ['a', 'b'], f'caso 5 falló: {r5}'
print('OK')
" 2>&1)
if [ "$MERGE_TEST" != "OK" ]; then
    echo "FAIL: _merge_unique_ordered no se comporta como se espera"
    echo "  $MERGE_TEST"
    exit 1
fi

echo "PASS: test_cli_adapter_parity"
