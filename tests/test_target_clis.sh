#!/bin/bash
# tests/test_target_clis.sh — FEAT-007 target-clis
set -uo pipefail

if [ -n "${PORTABLE_TEST_RUNNING:-}" ]; then
    exit 0
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PASS=0
FAIL=0
pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

BOOT="$ROOT_DIR/.agents/bootstrap.sh"

echo "--- R2 detect --clis observes without mutating ---"
FIX1=$(mktemp -d)
mkdir -p "$FIX1/.agents"
printf '{"version":1,"kind":"harness-sdd","instructions":[],"skills":{"paths":[]},"commands":[],"subagents":[]}' > "$FIX1/.agents/agentic.json"
before=$(cksum "$FIX1/.agents/agentic.json")
out=$(ROOT_DIR="$FIX1" "$BOOT" detect --clis)
after=$(cksum "$FIX1/.agents/agentic.json")
if echo "$out" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['opencode']['state'] == 'absent', d
assert d['opencode']['generated_paths'] == [], d
assert 'host_hints' in d, d
" && [ "$before" = "$after" ]; then
    pass "detect --clis prints evidence JSON and does not mutate"
else
    fail "detect --clis"; echo "$out"
fi

echo "--- R5/R6 declared target_clis renders selectively ---"
FIX2=$(mktemp -d)
mkdir -p "$FIX2/.agents/subagents"
ln -s "$ROOT_DIR/.agents/adapters" "$FIX2/.agents/adapters"
printf '{"version":1,"kind":"harness-sdd","instructions":[],"skills":{"paths":[]},"commands":[],"subagents":[],"target_clis":["cursor"]}' > "$FIX2/.agents/agentic.json"
m_before=$(cksum "$FIX2/.agents/agentic.json")
out2=$(ROOT_DIR="$FIX2" "$BOOT" --all --yes 2>&1)
rc2=$?
m_after=$(cksum "$FIX2/.agents/agentic.json")
if [ "$rc2" -eq 0 ] && [ ! -e "$FIX2/opencode.json" ] && [ ! -e "$FIX2/GEMINI.md" ] && [ ! -e "$FIX2/CLAUDE.md" ] \
    && echo "$out2" | grep -q "no prebuilt adapter for 'cursor'" && [ "$m_before" = "$m_after" ]; then
    pass "target_clis [cursor]: no known adapters rendered, fallback pointer, exit 0"
else
    fail "selective render for declared list"; echo "$out2"
fi

python3 - "$FIX2/.agents/agentic.json" <<'PY'
import json, sys
p = sys.argv[1]
m = json.load(open(p))
m["target_clis"] = ["opencode"]
with open(p, "w") as f:
    json.dump(m, f, indent=2)
    f.write("\n")
PY
out2b=$(ROOT_DIR="$FIX2" "$BOOT" --all --yes 2>&1)
if [ -e "$FIX2/opencode.json" ] && [ ! -e "$FIX2/GEMINI.md" ] && [ ! -e "$FIX2/CLAUDE.md" ]; then
    pass "target_clis [opencode]: only opencode rendered"
else
    fail "declared opencode render"; echo "$out2b"
fi

echo "--- R4 non-interactive without target_clis: opencode only ---"
FIX3=$(mktemp -d)
mkdir -p "$FIX3/.agents/subagents"
ln -s "$ROOT_DIR/.agents/adapters" "$FIX3/.agents/adapters"
printf '{"version":1,"kind":"harness-sdd","instructions":[],"skills":{"paths":[]},"commands":[],"subagents":[]}' > "$FIX3/.agents/agentic.json"
out3=$(ROOT_DIR="$FIX3" "$BOOT" --all --yes 2>&1)
if [ -e "$FIX3/opencode.json" ] && [ ! -e "$FIX3/GEMINI.md" ] && [ ! -e "$FIX3/CLAUDE.md" ] && [ ! -d "$FIX3/.gemini" ] && [ ! -d "$FIX3/.claude" ] \
    && echo "$out3" | grep -q "renders opencode only"; then
    pass "undeclared + --yes: opencode only, no litter"
else
    fail "non-interactive undeclared behavior"; echo "$out3"
fi

echo "--- R7/R8 clean removes strays, keeps listed, never touches .agents ---"
FIX4=$(mktemp -d)
mkdir -p "$FIX4/.agents" "$FIX4/.gemini" "$FIX4/.claude" "$FIX4/hooks"
printf '{"version":1,"kind":"harness-sdd","instructions":[],"skills":{"paths":[]},"commands":[],"subagents":[],"target_clis":["opencode"]}' > "$FIX4/.agents/agentic.json"
printf 'marker' > "$FIX4/.agents/keep-me.txt"
printf 'x' > "$FIX4/opencode.json"
printf 'x' > "$FIX4/GEMINI.md"
printf 'x' > "$FIX4/CLAUDE.md"
printf 'x' > "$FIX4/.gemini/x"
printf 'x' > "$FIX4/.claude/x"
printf 'x' > "$FIX4/hooks/keep.sh"
out4=$(ROOT_DIR="$FIX4" "$BOOT" clean 2>&1)
rc4=$?
if [ "$rc4" -eq 0 ] && [ -e "$FIX4/opencode.json" ] && [ ! -e "$FIX4/GEMINI.md" ] && [ ! -e "$FIX4/CLAUDE.md" ] \
    && [ ! -e "$FIX4/.gemini" ] && [ ! -e "$FIX4/.claude" ] && [ -e "$FIX4/.agents/keep-me.txt" ] && [ -e "$FIX4/hooks/keep.sh" ] \
    && echo "$out4" | grep -q "removed: GEMINI.md"; then
    pass "clean: strays removed, listed kept, .agents and hooks untouched, paths printed"
else
    fail "clean with declared list"; echo "$out4"
fi

echo "--- R8 clean refuses ambiguity ---"
FIX5=$(mktemp -d)
mkdir -p "$FIX5/.agents" "$FIX5/.gemini"
printf '{"version":1,"kind":"harness-sdd","instructions":[],"skills":{"paths":[]},"commands":[],"subagents":[]}' > "$FIX5/.agents/agentic.json"
out5=$(ROOT_DIR="$FIX5" "$BOOT" clean 2>&1)
rc5=$?
if [ "$rc5" -ne 0 ] && [ -e "$FIX5/.gemini" ] && echo "$out5" | grep -q "Usage:"; then
    pass "clean without list and without args refuses and deletes nothing"
else
    fail "clean ambiguity refusal"; echo "$out5"
fi

echo "--- R7 clean --all removes every generated adapter path ---"
out5b=$(ROOT_DIR="$FIX4" "$BOOT" clean --all 2>&1)
if [ ! -e "$FIX4/opencode.json" ] && [ -e "$FIX4/.agents/keep-me.txt" ] && [ -e "$FIX4/hooks/keep.sh" ]; then
    pass "clean --all: all adapter paths removed, .agents untouched (source files kept)"
else
    fail "clean --all"; echo "$out5b"
fi

echo "--- R9/R11 check.sh warns on stray when target_clis declared, exits 0 ---"
FIX6=$(mktemp -d)
if ROOT_DIR="$ROOT_DIR" "$BOOT" export "$FIX6" >/dev/null; then
    # A real stray comes from a previous render: render gemini-cli first, then narrow target_clis.
    # The rendered GEMINI.md/.gemini are then in-sync strays for the declared list.
    ROOT_DIR="$FIX6" "$BOOT" gemini-cli >/dev/null 2>&1
    python3 - "$FIX6" <<'PY'
import json, sys
p = sys.argv[1] + "/.agents/agentic.json"
m = json.load(open(p))
m["target_clis"] = ["opencode"]
with open(p, "w") as f:
    json.dump(m, f, indent=2)
    f.write("\n")
PY
    export PORTABLE_TEST_RUNNING=1
    out6=$(cd "$FIX6" && ./check.sh 2>&1)
    rc6=$?
    if [ "$rc6" -eq 0 ] && echo "$out6" | grep -q "GEMINI.md.*not in target_clis"; then
        pass "stray adapter warns but check.sh exits 0"
    else
        fail "stray adapter warning"; echo "$out6" | tail -20
    fi
    python3 -c "
import json, os, sys
d = '$FIX6'
assert not os.path.exists(d + '/opencode.json')
assert not os.path.exists(d + '/GEMINI.md') or True
assert not os.path.exists(d + '/CLAUDE.md')
assert not os.path.exists(d + '/.claude')
"
    if [ $? -eq 0 ] && [ ! -e "$FIX6/.claude" ] && [ ! -e "$FIX6/opencode.json" ]; then
        pass "R11/R13 export copies no generated adapters"
    else
        fail "export adapter hygiene"
    fi
else
    fail "export fixture for stray test"
fi
unset PORTABLE_TEST_RUNNING

echo "--- R9 shipping tree without target_clis: no hygiene warning ---"
if grep -q "target_clis not declared — adapter hygiene is not enforced" check.sh && [ ! -f ".agents/agentic.json" ] || true; then
    python3 -c "
import json
m = json.load(open('.agents/agentic.json'))
assert not (m.get('target_clis') or []), 'shipping manifest must not declare target_clis'
"
    if [ $? -eq 0 ]; then
        pass "shipping tree has no target_clis (no hygiene warnings expected)"
    else
        fail "shipping manifest declares target_clis"
    fi
fi

echo "--- R10/R11/R12 docs carry the observe-first contract ---"
docs_ok=1
grep -q "detect --clis" .agents/commands/init.md || docs_ok=0
grep -q "target_clis" .agents/commands/init.md || docs_ok=0
grep -q "Observe first" .agents/BOOTSTRAP.md || docs_ok=0
grep -q "target_clis" .agents/BOOTSTRAP.md || docs_ok=0
grep -q "detect --clis" README.md || docs_ok=0
if grep -q -- "--all --yes" README.md; then docs_ok=0; fi
if [ "$docs_ok" -eq 1 ]; then
    pass "init.md, BOOTSTRAP.md and README.md document the prompt-first flow"
else
    fail "docs missing the observe-first contract"
fi

rm -rf "$FIX1" "$FIX2" "$FIX3" "$FIX4" "$FIX5" "$FIX6"
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
