#!/bin/bash
# tests/test_plugin_adapters.sh — FEAT-008 native-plugin-adapters (cursor, codex)
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

make_fixture() { # $1 = python dict fragment for the manifest
    local FIX
    FIX=$(mktemp -d)
    mkdir -p "$FIX/.agents/subagents"
    ln -s "$ROOT_DIR/.agents/adapters" "$FIX/.agents/adapters"
    python3 - "$FIX" "$1" <<'PY'
import json, sys
fix, extra = sys.argv[1], json.loads(sys.argv[2])
m = {
    "version": 1,
    "kind": "harness-sdd",
    "instructions": [],
    "skills": {"paths": []},
    "commands": [{"name": "spec", "description": "Create the spec", "body_file": ".agents/commands/spec.md"}],
    "subagents": [{
        "name": "implementer", "mode": "subagent", "description": "Executes tasks",
        "role_file": ".agents/subagents/implementer/SUBAGENT.md",
        "permission": {"edit": {"specs/**": "deny", "*": "ask"}},
    }],
}
m.update(extra)
with open(fix + "/.agents/agentic.json", "w") as f:
    json.dump(m, f, indent=2)
    f.write("\n")
PY
    echo "$FIX"
}

echo "--- R1/R2/R3/R12 cursor renders natively and deterministically ---"
FIX1=$(make_fixture '{"target_clis": ["cursor"]}')
out1=$(ROOT_DIR="$FIX1" "$BOOT" --all --yes 2>&1)
if [ -f "$FIX1/.cursor/rules/harness-sdd.mdc" ] \
    && grep -q "alwaysApply: true" "$FIX1/.cursor/rules/harness-sdd.mdc" \
    && grep -q ".agents/subagents/implementer/SUBAGENT.md" "$FIX1/.cursor/rules/harness-sdd.mdc" \
    && [ -f "$FIX1/.cursor/commands/harness-spec.md" ] \
    && grep -q ".agents/commands/spec.md" "$FIX1/.cursor/commands/harness-spec.md" \
    && [ ! -e "$FIX1/opencode.json" ] && [ ! -e "$FIX1/GEMINI.md" ] && [ ! -e "$FIX1/CLAUDE.md" ]; then
    pass "cursor: rule + namespaced command rendered, other CLIs untouched"
else
    fail "cursor render"; echo "$out1"
fi

H1=$(cksum "$FIX1/.cursor/rules/harness-sdd.mdc" "$FIX1/.cursor/commands/harness-spec.md")
ROOT_DIR="$FIX1" "$BOOT" cursor >/dev/null 2>&1
H2=$(cksum "$FIX1/.cursor/rules/harness-sdd.mdc" "$FIX1/.cursor/commands/harness-spec.md")
if [ "$H1" = "$H2" ]; then
    pass "cursor: consecutive renders are byte-identical"
else
    fail "cursor determinism"
fi

echo "--- R5/R6/R12 codex leans on native files ---"
FIX2=$(make_fixture '{"target_clis": ["codex"]}')
out2=$(ROOT_DIR="$FIX2" "$BOOT" --all --yes 2>&1)
if [ $? -eq 0 ] && [ ! -e "$FIX2/.codex" ] && [ ! -e "$FIX2/.cursor" ] && echo "$out2" | grep -q "AGENTS.md native entry"; then
    pass "codex: native integration, nothing generated, exit 0"
else
    fail "codex render"; echo "$out2"
fi

echo "--- R7 detect --clis knows cursor and codex ---"
out3=$(ROOT_DIR="$FIX1" "$BOOT" detect --clis)
if echo "$out3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'cursor' in d and 'codex' in d, list(d)
assert d['cursor']['state'] == 'present', d['cursor']
assert '.cursor/rules/harness-sdd.mdc' in d['cursor']['generated_paths'], d['cursor']
"; then
    pass "detect --clis lists cursor (present) and codex evidence"
else
    fail "detect --clis evidence"; echo "$out3"
fi

echo "--- R8/R9 clean is per-path and user-safe ---"
FIX3=$(make_fixture '{"target_clis": ["cursor"]}')
ROOT_DIR="$FIX3" "$BOOT" cursor >/dev/null 2>&1
mkdir -p "$FIX3/.cursor/commands" "$FIX3/.codex/prompts"
printf 'user rule' > "$FIX3/.cursor/commands/custom.md"
printf 'user prompt' > "$FIX3/.codex/prompts/mine.md"
python3 - "$FIX3" <<'PY'
import json, sys
p = sys.argv[1] + "/.agents/agentic.json"
m = json.load(open(p))
m["target_clis"] = ["opencode"]
with open(p, "w") as f:
    json.dump(m, f, indent=2)
    f.write("\n")
PY
out4=$(ROOT_DIR="$FIX3" "$BOOT" clean 2>&1)
if [ ! -e "$FIX3/.cursor/rules/harness-sdd.mdc" ] && [ ! -e "$FIX3/.cursor/commands/harness-spec.md" ] \
    && [ -e "$FIX3/.cursor/commands/custom.md" ] && [ -e "$FIX3/.codex/prompts/mine.md" ] \
    && echo "$out4" | grep -q "removed: .cursor/rules/harness-sdd.mdc"; then
    pass "clean: harness outputs removed, user files preserved"
else
    fail "clean user-safety"; echo "$out4"
fi

ROOT_DIR="$FIX3" "$BOOT" clean --all >/dev/null 2>&1
if [ -e "$FIX3/.cursor/commands/custom.md" ] && [ -e "$FIX3/.codex/prompts/mine.md" ]; then
    pass "clean --all still preserves user files"
else
    fail "clean --all user-safety"
fi

ROOT_DIR="$FIX3" "$BOOT" --check >/dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "drift check skips adapters whose outputs are absent"
else
    fail "drift skip"
fi

echo "--- R10 hygiene warns for stray cursor outputs; R11/R13 export payload ---"
FIX4=$(mktemp -d)
if ROOT_DIR="$ROOT_DIR" "$BOOT" export "$FIX4" >/dev/null; then
    if [ ! -d "$FIX4/.cursor" ] && [ ! -d "$FIX4/.codex" ] \
        && [ -f "$FIX4/.agents/adapters/cursor/README.md" ] && [ -f "$FIX4/.agents/adapters/codex/README.md" ]; then
        pass "export: adapter sources copied, rendered artifacts not"
    else
        fail "export adapter hygiene"
    fi
    ROOT_DIR="$FIX4" "$BOOT" cursor >/dev/null 2>&1
    ROOT_DIR="$FIX4" "$BOOT" opencode >/dev/null 2>&1
    python3 - "$FIX4" <<'PY'
import json, sys
p = sys.argv[1] + "/.agents/agentic.json"
m = json.load(open(p))
m["target_clis"] = ["opencode"]
with open(p, "w") as f:
    json.dump(m, f, indent=2)
    f.write("\n")
PY
    export PORTABLE_TEST_RUNNING=1
    out5=$(cd "$FIX4" && ./check.sh 2>&1)
    rc5=$?
    if [ "$rc5" -eq 0 ] && echo "$out5" | grep -q ".cursor/rules/harness-sdd.mdc.*not in target_clis"; then
        pass "hygiene: stray cursor outputs warn, check.sh exits 0"
    else
        fail "hygiene stray warning"; echo "$out5" | tail -20
    fi
else
    fail "export fixture"
fi
unset PORTABLE_TEST_RUNNING

echo "--- R14 docs list the four CLIs ---"
docs_ok=1
grep -q "cursor" AGENTS.md && grep -q "codex" AGENTS.md || docs_ok=0
grep -q "cursor" README.md && grep -q "codex" README.md || docs_ok=0
grep -q "cursor" .agents/BOOTSTRAP.md || docs_ok=0
if [ "$docs_ok" -eq 1 ]; then
    pass "AGENTS.md, README.md and BOOTSTRAP.md include cursor and codex"
else
    fail "docs missing cursor/codex"
fi

rm -rf "$FIX1" "$FIX2" "$FIX3" "$FIX4"
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
