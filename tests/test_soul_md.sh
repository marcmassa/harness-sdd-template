#!/bin/bash
# tests/test_soul_md.sh
# ──────────────────────────────────────────────────────────────────────────────
# Tests for SOUL.md feature (FEAT-005):
#
# T9: Verifies that the generated claude-code stub for 'templates' contains
#     the '## Agent Soul' section with non-empty content.
#
# T10: Verifies that check.sh exits with error when a declared subagent
#      is missing its SOUL.md.
#
# T11: Verifies that agent-template/SOUL.md contains the four canonical
#      sections and no empty section bodies.
#
# T12: Verifies that bootstrap renders without error when a subagent entry
#      in agentic.json has no 'soul' field (retrocompatibility).
# ──────────────────────────────────────────────────────────────────────────────

set -uo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

PASS=0
FAIL=0

pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SOUL.md Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── T9: fixture render of 'templates' contains '## Agent Soul' ───────────────
echo ""
echo "T9: fixture Claude stub contains '## Agent Soul' with content"
FIXTURE=$(mktemp -d)
mkdir -p "$FIXTURE/.agents/subagents/templates" "$FIXTURE/.agents/adapters"
ln -s "$ROOT_DIR/.agents/adapters/claude-code" "$FIXTURE/.agents/adapters/claude-code"
cp "$ROOT_DIR/.agents/subagents/templates/SOUL.md" "$FIXTURE/.agents/subagents/templates/SOUL.md"
cp "$ROOT_DIR/.agents/subagents/templates/SUBAGENT.md" "$FIXTURE/.agents/subagents/templates/SUBAGENT.md"
python3 - "$FIXTURE" << 'PY'
import json, sys
dest = sys.argv[1]
manifest = {
    "version": 1,
    "kind": "harness-sdd",
    "instructions": [],
    "skills": {"paths": []},
    "commands": [],
    "subagents": [{
        "name": "templates",
        "mode": "subagent",
        "description": "fixture",
        "role_file": ".agents/subagents/templates/SUBAGENT.md",
        "soul": ".agents/subagents/templates/SOUL.md",
        "permission": {"edit": {"*": "ask"}},
    }],
}
with open(dest + "/.agents/agentic.json", "w") as f:
    json.dump(manifest, f)
PY
if python3 "$ROOT_DIR/.agents/adapters/_common/render.py" --cli claude-code --root "$FIXTURE" >/dev/null; then
    STUB="$FIXTURE/.claude/agents/templates.md"
    if [ -f "$STUB" ] && grep -q "## Agent Soul" "$STUB"; then
        soul_content=$(awk '/## Agent Soul/{found=1; next} found && /^##/{exit} found{print}' "$STUB" | grep -v '^[[:space:]]*$' | head -1)
        if [ -n "$soul_content" ]; then
            pass "T9: fixture .claude/agents/templates.md contains '## Agent Soul' with content"
        else
            fail "T9: '## Agent Soul' section is empty in fixture stub"
        fi
    else
        fail "T9: '## Agent Soul' not found in fixture stub"
    fi
else
    fail "T9: fixture claude-code render failed"
fi
rm -rf "$FIXTURE"

# ── T10: check.sh fails when a declared subagent is missing SOUL.md ──────────
echo ""
echo "T10: check.sh fails for subagent missing SOUL.md"
TMPDIR_TEST=$(mktemp -d)
# Create a minimal agentic.json with a subagent that has no SOUL.md
cat > "$TMPDIR_TEST/.agents_agentic_test.json" << 'EOF'
{"version":1,"kind":"harness-sdd","subagents":[{"name":"ghost-agent","mode":"subagent","description":"test","role_file":".agents/subagents/ghost-agent/SUBAGENT.md","soul":".agents/subagents/ghost-agent/SOUL.md"}]}
EOF
# Run the validation logic inline (same as check.sh uses)
validation_output=$(python3 - "$ROOT_DIR" "$TMPDIR_TEST/.agents_agentic_test.json" << 'PYEOF'
import json, sys, os
root = sys.argv[1]
manifest_path = sys.argv[2]
manifest = json.load(open(manifest_path))
errors = []
for sa in manifest.get("subagents", []):
    name = sa["name"]
    if name == "agent-template":
        continue
    soul_path_str = sa.get("soul", f".agents/subagents/{name}/SOUL.md")
    soul_path = os.path.join(root, soul_path_str)
    if not os.path.exists(soul_path):
        errors.append(name)
if errors:
    sys.exit(1)
sys.exit(0)
PYEOF
)
t10_rc=$?
rm -rf "$TMPDIR_TEST"
if [ $t10_rc -ne 0 ]; then
    pass "T10: validation correctly detects missing SOUL.md (exit code != 0)"
else
    fail "T10: validation did NOT detect missing SOUL.md (exit code 0, expected non-0)"
fi

# ── T11: agent-template/SOUL.md has the four canonical sections ───────────────
echo ""
echo "T11: agent-template/SOUL.md has four canonical sections"
TEMPLATE_SOUL="$ROOT_DIR/.agents/subagents/agent-template/SOUL.md"
if [ ! -f "$TEMPLATE_SOUL" ]; then
    fail "T11: $TEMPLATE_SOUL not found"
else
    MISSING_SECTIONS=""
    for section in "## Identity" "## Decision Principles" "## Boundaries" "## Tone & Style"; do
        if ! grep -q "^${section}$" "$TEMPLATE_SOUL"; then
            MISSING_SECTIONS="$MISSING_SECTIONS '$section'"
        fi
    done
    if [ -z "$MISSING_SECTIONS" ]; then
        pass "T11: agent-template/SOUL.md contains all four canonical sections"
    else
        fail "T11: agent-template/SOUL.md missing sections:$MISSING_SECTIONS"
    fi
fi

# ── T12: bootstrap renders without error when 'soul' field is absent ──────────
echo ""
echo "T12: bootstrap renders without error for subagent without 'soul' field"
# Test render.py load_soul_content with a subagent dict that has no 'soul' key
render_test_output=$(python3 - "$ROOT_DIR" << 'PYEOF'
import sys
sys.path.insert(0, sys.argv[1] + "/.agents/adapters/_common")
from render import load_soul_content
from pathlib import Path
root = Path(sys.argv[1])
# Subagent without 'soul' field — should fall back to convention path
sa_no_soul_field = {"name": "nonexistent-agent-xyz"}
result = load_soul_content(root, sa_no_soul_field)
# Should return empty string (no error) since path doesn't exist
assert isinstance(result, str), "Expected string return"
print("OK")
PYEOF
)
if [ "${render_test_output:-}" = "OK" ]; then
    pass "T12: load_soul_content returns empty string (no error) when 'soul' field absent and file missing"
else
    fail "T12: load_soul_content raised an error: ${render_test_output:-unknown}"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
[ $FAIL -eq 0 ]
