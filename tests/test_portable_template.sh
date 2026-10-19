#!/bin/bash
# tests/test_portable_template.sh — FEAT-006 portable template
set -uo pipefail

if [ -n "${PORTABLE_TEST_RUNNING:-}" ]; then
    exit 0
fi
export PORTABLE_TEST_RUNNING=1

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PASS=0
FAIL=0
pass() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

echo "--- R1/R2 shipping manifest is FRESH ---"
python3 - << 'PY'
import json, sys
m = json.load(open(".agents/agentic.json"))
errors = []
if m.get("subagents") != []:
    errors.append("subagents not empty")
if m.get("steering") != []:
    errors.append("steering not empty")
if m.get("hooks") != []:
    errors.append("hooks not empty")
if "default_agent" in m:
    errors.append("default_agent present")
for key in ("_template_subagents_examples", "_template_steering_examples", "_template_hooks_examples", "_template_lifecycle"):
    if not m.get(key):
        errors.append(f"missing {key}")
if any(s.get("name") == "templates" for s in m.get("subagents", [])):
    errors.append("templates is active")
if errors:
    print("FAIL: " + "; ".join(errors))
    sys.exit(1)
print("ok")
PY
if [ $? -eq 0 ]; then pass "shipping manifest is FRESH"; else fail "shipping manifest is not FRESH"; fi

echo "--- R3 templates soul remains ---"
if grep -q "^## Identity$" .agents/subagents/templates/SOUL.md && [ -s .agents/subagents/templates/SOUL.md ]; then
    pass "templates SOUL.md kept"
else
    fail "templates SOUL.md missing or empty"
fi

echo "--- R16/R17 detect lists CLIs and labels stack ---"
detect_out=$(./.agents/bootstrap.sh detect)
printf '%s\n' "$detect_out" | grep -q "  - opencode" && printf '%s\n' "$detect_out" | grep -q "  - gemini-cli" && printf '%s\n' "$detect_out" | grep -q "  - claude-code"
if [ $? -eq 0 ]; then pass "detect lists three CLIs"; else fail "detect missing a CLI"; echo "$detect_out"; fi
if printf '%s\n' "$detect_out" | grep -q "^Project stack:"; then
    pass "project stack is labeled"
else
    fail "project stack label missing"
fi
if printf '%s\n' "$detect_out" | awk 'BEGIN{p=0} /^Available adapters:/{p=1; next} /^Project stack:/{p=0} p && /^\[\]$/{found=1} END{exit found?0:1}'; then
    fail "bare [] printed as the adapter list"
else
    pass "adapter list is not a bare []"
fi

echo "--- R23/R24 SECURITY.md ---"
if grep -q "Harness SDD Template" SECURITY.md && ! grep -q "5.1.x" SECURITY.md && ! grep -q "4.0.x" SECURITY.md; then
    pass "SECURITY.md names the project and drops boilerplate versions"
else
    fail "SECURITY.md is not the portable policy"
fi

echo "--- R9 hook examples ---"
hooks_ok=1
for f in hooks/on-spec-created_validate.sh hooks/on-feature-done_notify.sh hooks/on-check-pass_ci.sh; do
    if [ ! -s "$f" ] || [ ! -x "$f" ]; then
        hooks_ok=0
        echo "  bad hook example: $f"
    fi
done
python3 -c "import json; m=json.load(open('.agents/agentic.json')); assert m.get('hooks')==[]"
if [ $? -eq 0 ] && [ "$hooks_ok" -eq 1 ]; then pass "hook examples are real and inactive"; else fail "hook examples"; fi

echo "--- R4/R5/R29 renderer default_agent and GEMINI ---"
python3 - "$ROOT_DIR" << 'PY'
import json, sys, tempfile, os, subprocess
from pathlib import Path
root = Path(sys.argv[1])
renderer = root / ".agents/adapters/_common/render.py"
sys.path.insert(0, str(root / ".agents/adapters/_common"))
import render

def render_default(default_agent, active):
    dest = Path(tempfile.mkdtemp())
    (dest / ".agents").mkdir()
    subagents = []
    if active:
        subagents.append({
            "name": active,
            "mode": "subagent",
            "description": "fixture",
            "role_file": ".agents/subagents/x/SUBAGENT.md",
            "permission": {"edit": {"*": "ask"}},
        })
    manifest = {
        "version": 1,
        "kind": "harness-sdd",
        "instructions": [],
        "skills": {"paths": []},
        "commands": [],
        "subagents": subagents,
    }
    if default_agent is not None:
        manifest["default_agent"] = default_agent
    (dest / ".agents" / "agentic.json").write_text(json.dumps(manifest))
    subprocess.check_call([sys.executable, str(renderer), "--cli", "opencode", "--root", str(dest)], stdout=subprocess.DEVNULL)
    cfg = json.loads((dest / "opencode.json").read_text())
    return cfg

omitted = render_default(None, None)
assert "default_agent" not in omitted, omitted
dangling = render_default("harness", None)
assert "default_agent" not in dangling, dangling
kept = render_default("implementer", "implementer")
assert kept.get("default_agent") == "implementer", kept
print("ok")
PY
if [ $? -eq 0 ]; then pass "default_agent omitted unless active"; else fail "default_agent contract"; fi

if ./.agents/bootstrap.sh gemini-cli >/dev/null && ! grep -q "The harness role is the default" GEMINI.md; then
    pass "GEMINI.md does not hardcode the harness default"
else
    fail "GEMINI.md still hardcodes the harness default"
fi

echo "--- R18 export refuses a non-empty destination ---"
refuse_dest=$(mktemp -d)
echo keep > "$refuse_dest/keep.txt"
before=$(cat "$refuse_dest/keep.txt")
if ./.agents/bootstrap.sh export "$refuse_dest" >/dev/null; then
    fail "export accepted a non-empty destination"
else
    if [ "$(cat "$refuse_dest/keep.txt")" = "$before" ]; then
        pass "export refused a non-empty destination"
    else
        fail "export wrote into a refused destination"
    fi
fi
rm -rf "$refuse_dest"

echo "--- R19-R22/R26 export payload and green check ---"
export_dest=$(mktemp -d)
rmdir "$export_dest"
if ./.agents/bootstrap.sh export "$export_dest"; then
    missing=0
    for f in AGENTS.md DESIGN.md README.md LICENSE SECURITY.md check.sh docs/sdd.md .gitignore .agents/agentic.json specs/README.md hooks/run-hooks.sh steering; do
        if [ ! -e "$export_dest/$f" ]; then
            echo "  missing $f"
            missing=1
        fi
    done
    if [ -d "$export_dest/specs/templates" ] && [ -d "$export_dest/examples" ]; then
        :
    else
        missing=1
    fi
    if [ "$missing" -eq 0 ]; then pass "export payload present"; else fail "export payload incomplete"; fi
    if [ -e "$export_dest/.git" ] || [ -e "$export_dest/.env" ] || [ -e "$export_dest/AUTHORITY" ] || [ -d "$export_dest/tests" ] || [ -e "$export_dest/opencode.json" ] || [ -e "$export_dest/GEMINI.md" ] || [ -d "$export_dest/.claude" ] || [ -d "$export_dest/.agents/subagents/templates" ] || [ -d "$export_dest/specs/portable-template" ]; then
        fail "export copied framework history"
    else
        pass "export omitted framework history"
    fi
    python3 - "$export_dest/feature_list.json" << 'PY'
import json, sys
m = json.load(open(sys.argv[1]))
ids = [f["id"] for f in m["features"]]
assert len(m["features"]) == 1, ids
assert m["features"][0]["status"] == "pending"
assert m["features"][0]["sdd"] is True
for banned in ("FEAT-002", "FEAT-003", "FEAT-004", "FEAT-005", "FEAT-006"):
    assert banned not in ids
print("ok")
PY
    if [ $? -eq 0 ]; then pass "exported feature list is a single pending example"; else fail "exported feature list"; fi
    if grep -q "^# Current Session State" "$export_dest/progress/current.md" && ! grep -q "FEAT-006" "$export_dest/progress/current.md"; then
        pass "exported progress is a template"
    else
        fail "exported progress is not a template"
    fi
    if (cd "$export_dest" && ./check.sh >/tmp/portable-export-check.txt); then
        pass "exported tree check.sh exits 0"
    else
        fail "exported tree check.sh failed"
        tail -30 /tmp/portable-export-check.txt
    fi
else
    fail "export command failed"
fi

echo "--- R10/R12 active hook and steering fail closed ---"
if [ -d "$export_dest" ]; then
    python3 - "$export_dest" << 'PY'
import json, sys
from pathlib import Path
dest = Path(sys.argv[1])
manifest_path = dest / ".agents" / "agentic.json"
m = json.loads(manifest_path.read_text())
empty = dest / "hooks" / "empty-hook.sh"
empty.write_text("")
m["hooks"] = [{
    "event": "on_spec_created",
    "script": "hooks/empty-hook.sh",
    "description": "empty",
    "on_failure": "warn",
}]
manifest_path.write_text(json.dumps(m, indent=2) + "\n")
PY
    if (cd "$export_dest" && ./check.sh >/tmp/portable-empty-hook.txt); then
        fail "empty active hook did not fail check.sh"
    else
        pass "empty active hook fails check.sh"
    fi
    python3 - "$export_dest" << 'PY'
import json, sys
from pathlib import Path
dest = Path(sys.argv[1])
manifest_path = dest / ".agents" / "agentic.json"
m = json.loads(manifest_path.read_text())
m["hooks"] = []
todo = dest / "steering" / "todo.md"
todo.write_text("---\nname: todo\ndescription: \"todo\"\napplies_to:\n  - '*'\n---\n\n<!-- TODO: customize -->\n")
m["steering"] = [{
    "name": "todo",
    "file": "steering/todo.md",
    "description": "todo",
    "applies_to": ["*"],
}]
manifest_path.write_text(json.dumps(m, indent=2) + "\n")
PY
    if (cd "$export_dest" && ./check.sh >/tmp/portable-todo-steer.txt); then
        fail "active TODO steering did not fail check.sh"
    else
        pass "active TODO steering fails check.sh"
    fi
fi

echo "--- R13 scaffold TODO does not fail a FRESH tree ---"
fresh_dest=$(mktemp -d)
rmdir "$fresh_dest"
if ./.agents/bootstrap.sh export "$fresh_dest" && (cd "$fresh_dest" && ./check.sh >/tmp/portable-fresh-check.txt); then
    pass "scaffold TODO files do not fail a FRESH tree"
else
    fail "FRESH tree with scaffold TODO failed check.sh"
    tail -20 /tmp/portable-fresh-check.txt
fi

echo "--- R7 render does not rewrite the manifest ---"
before=$(cksum .agents/agentic.json)
./.agents/bootstrap.sh --all </dev/null >/dev/null
./.agents/bootstrap.sh --all </dev/null >/dev/null
after=$(cksum .agents/agentic.json)
if [ "$before" = "$after" ]; then
    pass "consecutive --all runs left agentic.json unchanged"
else
    fail "consecutive --all runs modified agentic.json"
fi

echo "--- R27/R28 adopted tree reaches INITIALIZED ---"
adopt_dest=$(mktemp -d)
rmdir "$adopt_dest"
if ./.agents/bootstrap.sh export "$adopt_dest"; then
    (cd "$adopt_dest" && ./.agents/bootstrap.sh add-agent implementer --yes >/tmp/portable-add-agent.txt)
    if grep -q "^agent: implementer$" "$adopt_dest/.agents/subagents/implementer/SOUL.md"; then
        pass "add-agent scaffolded SOUL.md"
    else
        fail "add-agent did not scaffold SOUL.md"
        cat /tmp/portable-add-agent.txt
    fi
    (cd "$adopt_dest" && ./.agents/bootstrap.sh remove-examples --yes >/dev/null)
    state=$(cd "$adopt_dest" && python3 ./.agents/adapters/_common/render.py --validate-init --root "$adopt_dest" | python3 -c "import json,sys; print(json.load(sys.stdin).get('state'))")
    if [ "$state" = "INITIALIZED" ] && (cd "$adopt_dest" && ./check.sh >/tmp/portable-init-check.txt); then
        pass "adopted tree is INITIALIZED and check.sh exits 0"
    else
        fail "adopted tree did not reach a green INITIALIZED state ($state)"
        tail -40 /tmp/portable-init-check.txt
    fi
else
    fail "export for adoption test failed"
fi

rm -rf "$export_dest" "$fresh_dest" "$adopt_dest"
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
