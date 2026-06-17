#!/bin/bash
# Test: sistema de hooks — runner, ejemplo hooks, y política on_failure=error (FEAT-004)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PASS=0
FAIL=0

# 1. Ejecutar hooks para un evento sin hooks registrados → exit 0
echo "--- Test 1: run-hooks.sh with empty event ---"
EVENT="__test_no_such_event__"
if hooks/run-hooks.sh "$EVENT" 2>/dev/null; then
    echo "PASS: exit 0 for event with no hooks registered"
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

# 4. Verificar política on_failure=error (usa temp manifest)
echo ""
echo "--- Test 4: on_failure=error stops execution ---"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Crear manifest temporal con un hook que falla
mkdir -p "$TMPDIR/.agents"
cp .agents/agentic.json "$TMPDIR/.agents/agentic.json"
cat > "$TMPDIR/error_hook.sh" <<'SHEOF'
#!/bin/bash
echo "This hook should fail"
exit 42
SHEOF
chmod +x "$TMPDIR/error_hook.sh"

python3 -c "
import json
with open('$TMPDIR/.agents/agentic.json') as f:
    m = json.load(f)
m['hooks'] = [{
    'event': '__test_error_event__',
    'script': '$TMPDIR/error_hook.sh',
    'description': 'Test error hook',
    'on_failure': 'error',
}]
with open('$TMPDIR/.agents/agentic.json', 'w') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
"

# Ejecutar run-hooks.sh con el manifest temporal
(
    export ROOT_DIR="$TMPDIR"
    export HOOK_EVENT="__test_error_event__"
    cd "$TMPDIR"
    if "$ROOT_DIR/hooks/run-hooks.sh" __test_error_event__ 2>/dev/null; then
        echo "__TEST_FAIL__"
    else
        rc=$?
        echo "__TEST_PASS__ exit_code=$rc"
    fi
) > "$TMPDIR/output.txt" 2>/dev/null || true

if grep -q "__TEST_PASS__" "$TMPDIR/output.txt"; then
    echo "PASS: hook with on_failure=error stopped execution"
    PASS=$((PASS + 1))
else
    echo "FAIL: expected non-zero exit for on_failure=error"
    echo "  Output: $(cat "$TMPDIR/output.txt")"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
echo "PASS: test_hooks"
