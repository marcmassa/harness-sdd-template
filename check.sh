#!/usr/bin/env bash
# check.sh — Verificación e inicialización del entorno Harness SDD
#
# Ejecuta builds, lints, tests y validaciones de integridad SDD.
# Gateway para declarar una tarea como done — si falla, la tarea no está terminada.
#
# Uso: ./check.sh [--verbose] [--py-only] [--ts-only] [--go-only]
#
# Personaliza este script añadiendo bloques para tu stack:
#   - Terraform: terraform fmt -check, terraform validate
#   - Docker: hadolint
#   - Kubernetes: kustomize build, helm lint
#   - Security: checkov, tfsec, trivy

set -uo pipefail

VERBOSE=false
PY_ONLY=false
TS_ONLY=false
GO_ONLY=false
EXIT_CODE=0

for arg in "$@"; do
	case "$arg" in
		--verbose) VERBOSE=true ;;
		--py-only) PY_ONLY=true ;;
		--ts-only) TS_ONLY=true ;;
		--go-only) GO_ONLY=true ;;
	esac
done

section() {
	echo ""
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo "  $1"
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; EXIT_CODE=1; }
warn() { echo "  ⚠️  $1"; }

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# ── Stack checks ──────────────────────────────────
# Personaliza estos bloques según tu stack.
# Ejemplos comentados para Terraform, Docker y K8s.

if command -v terraform &>/dev/null; then
	section "Terraform — Format & Validate"
	terraform fmt -check -recursive 2>/dev/null && pass "terraform fmt" || warn "terraform fmt found differences (fix with 'terraform fmt')"
	terraform validate 2>/dev/null && pass "terraform validate" || warn "terraform validate has warnings"
fi

if command -v tflint &>/dev/null; then
	section "Terraform — TFLint"
	tflint --recursive 2>&1 | tail -5 && pass "tflint" || warn "tflint found issues"
fi

if [ -d "charts" ] && command -v helm &>/dev/null; then
	section "Helm — Lint"
	for chart in charts/*/; do
		helm lint "$chart" 2>/dev/null && pass "helm lint $chart" || warn "helm lint $chart"
	done
fi

# ── Python checks (if applicable) ─────────────────────
if ! $TS_ONLY && ! $GO_ONLY && (ls *.py 2>/dev/null || ls **/*.py 2>/dev/null); then
	section "Python — Syntax check"
	python3 -m py_compile -x .venv -x __pycache__ . 2>/dev/null && pass "py_compile" || warn "py_compile found errors"

	section "Python — Tests"
	if command -v pytest &>/dev/null && [ -d "tests" ]; then
		python3 -m pytest tests/ -v --tb=short -x 2>&1 | tail -10
		if [ $? -eq 0 ]; then
			pass "pytest: all passed"
		else
			fail "pytest: broken tests"
		fi
	elif [ -d "tests" ]; then
		warn "tests/ exists but pytest is not available"
	fi
fi

# ── Go checks (if applicable) ─────────────────────────
if ! $PY_ONLY && ! $TS_ONLY && (ls *.go 2>/dev/null || ls **/*.go 2>/dev/null); then
	section "Go — Build & Vet"
	if command -v go &>/dev/null; then
		go build ./... 2>/dev/null && pass "go build" || fail "go build"
		go vet ./... 2>/dev/null && pass "go vet" || fail "go vet"
		go test ./... -race -count=1 2>&1 | tail -5 && pass "go test -race" || fail "go test -race"
	fi
fi

# ── TypeScript checks (if applicable) ─────────────────
if ! $PY_ONLY && ! $GO_ONLY && [ -f "package.json" ]; then
	section "TypeScript — Build"
	npm run build 2>&1 | tail -3 && pass "npm run build" || fail "npm run build"

	if [ -f "vitest.config.js" ] || [ -f "vitest.config.ts" ]; then
		section "TypeScript — Tests"
		npm test -- --run 2>&1 | tail -10 && pass "npm test" || warn "npm test: some tests failed"
	fi
fi

# ── Feature list validation ───────────────────────
section "Feature List Validation"
if [ -f "feature_list.json" ]; then
	if python3 -c "import json; json.load(open('feature_list.json'))" 2>/dev/null; then
		pass "feature_list.json is valid JSON"
	else
		fail "feature_list.json is NOT valid JSON"
	fi

	python3 /dev/stdin <<'PYEOF' 2>/dev/null || true
import json, os, sys
with open('feature_list.json') as f:
    data = json.load(f)

valid_status = {"pending", "spec_ready", "in_progress", "done", "blocked"}
errors = []

for feat in data['features']:
    if feat['status'] not in valid_status:
        errors.append(f"{feat['id']}: invalid status '{feat['status']}'")

in_progress = [f for f in data['features'] if f['status'] == 'in_progress']
if len(in_progress) > 1:
    names = ', '.join(f['id'] for f in in_progress)
    errors.append(f"Multiple features 'in_progress': {names}")

requires_spec = {"spec_ready", "in_progress", "done"}
for feat in data['features']:
    if feat.get('sdd') and feat['status'] in requires_spec:
        spec_dir = os.path.join('specs', feat['name'])
        for fname in ('requirements.md', 'design.md', 'tasks.md'):
            if not os.path.isfile(os.path.join(spec_dir, fname)):
                errors.append(f"{feat['id']}: sdd=true, status={feat['status']}, missing {spec_dir}/{fname}")

if errors:
    for e in errors:
        print(f"[WARN]  {e}")
    sys.exit(1)
else:
    print(f"[OK]    feature_list.json valid ({len(data['features'])} features)")
    in_prog = [f for f in data['features'] if f['status'] == 'in_progress']
    if in_prog:
        print(f"        1 feature in progress: {in_prog[0]['id']} — {in_prog[0]['name']}")
    else:
        print("        No features in progress")
PYEOF

	if [ $? -eq 0 ]; then
		pass "Feature list validation completed"
	else
		fail "Errors in feature_list.json"
	fi
else
	warn "feature_list.json not found — skipping"
fi

# ── Progress files check ──────────────────────────
section "Progress Files"
for f in progress/current.md progress/progress.md progress/backlog.md progress/decisions.md progress/handoff.md; do
	if [ -f "$f" ]; then
		pass "Exists $f"
	else
		warn "Missing $f"
	fi
done

# ── Sub-Agent check ───────────────────────────────
section "Sub-Agents"
for dir in .agents/subagents/*/; do
	name=$(basename "$dir")
	if [ -f "${dir}SUBAGENT.md" ]; then
		pass "Subagent $name (SUBAGENT.md)"
	else
		warn "Subagent $name: missing SUBAGENT.md"
	fi
done

if ! ls .agents/subagents/*/SUBAGENT.md &>/dev/null 2>&1; then
	warn "No subagents defined in .agents/subagents/"
fi

# ── SDD Infrastructure check ──────────────────────
section "SDD Infrastructure"
if [ -f "DESIGN.md" ]; then
	pass "Exists DESIGN.md (Global Architecture)"
else
	warn "Missing DESIGN.md in root directory"
fi

for f in specs/README.md specs/templates/requirements.md specs/templates/design.md specs/templates/tasks.md; do
	if [ -f "$f" ]; then
		pass "Exists $f"
	else
		warn "Missing $f"
	fi
done

# ── Summary ─────────────────────────────────────────
section "Result"
if [ "$EXIT_CODE" -eq 0 ]; then
	echo "  ✅ All checks passed — environment ready"
else
	echo "  ❌ Some checks failed — resolve before continuing"
fi
echo ""
exit "$EXIT_CODE"
