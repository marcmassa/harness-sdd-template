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
	terraform fmt -check -recursive 2>/dev/null && pass "terraform fmt" || warn "terraform fmt encontró diferencias (corrige con 'terraform fmt')"
	terraform validate 2>/dev/null && pass "terraform validate" || warn "terraform validate tiene advertencias"
fi

if command -v tflint &>/dev/null; then
	section "Terraform — TFLint"
	tflint --recursive 2>&1 | tail -5 && pass "tflint" || warn "tflint encontró issues"
fi

if [ -d "charts" ] && command -v helm &>/dev/null; then
	section "Helm — Lint"
	for chart in charts/*/; do
		helm lint "$chart" 2>/dev/null && pass "helm lint $chart" || warn "helm lint $chart"
	done
fi

# ── Python checks (si aplica) ─────────────────────
if ! $TS_ONLY && ! $GO_ONLY && (ls *.py 2>/dev/null || ls **/*.py 2>/dev/null); then
	section "Python — Syntax check"
	python3 -m py_compile -x .venv -x __pycache__ . 2>/dev/null && pass "py_compile" || warn "py_compile encontró errores"

	section "Python — Tests"
	if command -v pytest &>/dev/null && [ -d "tests" ]; then
		python3 -m pytest tests/ -v --tb=short -x 2>&1 | tail -10
		if [ $? -eq 0 ]; then
			pass "pytest: todos pasan"
		else
			fail "pytest: hay tests rotos"
		fi
	elif [ -d "tests" ]; then
		warn "tests/ existe pero pytest no está disponible"
	fi
fi

# ── Go checks (si aplica) ─────────────────────────
if ! $PY_ONLY && ! $TS_ONLY && (ls *.go 2>/dev/null || ls **/*.go 2>/dev/null); then
	section "Go — Build & Vet"
	if command -v go &>/dev/null; then
		go build ./... 2>/dev/null && pass "go build" || fail "go build"
		go vet ./... 2>/dev/null && pass "go vet" || fail "go vet"
		go test ./... -race -count=1 2>&1 | tail -5 && pass "go test -race" || fail "go test -race"
	fi
fi

# ── TypeScript checks (si aplica) ─────────────────
if ! $PY_ONLY && ! $GO_ONLY && [ -f "package.json" ]; then
	section "TypeScript — Build"
	npm run build 2>&1 | tail -3 && pass "npm run build" || fail "npm run build"

	if [ -f "vitest.config.js" ] || [ -f "vitest.config.ts" ]; then
		section "TypeScript — Tests"
		npm test -- --run 2>&1 | tail -10 && pass "npm test" || warn "npm test: algunos tests fallaron"
	fi
fi

# ── Feature list validation ───────────────────────
section "Feature List Validation"
if [ -f "feature_list.json" ]; then
	if python3 -c "import json; json.load(open('feature_list.json'))" 2>/dev/null; then
		pass "feature_list.json es JSON válido"
	else
		fail "feature_list.json no es JSON válido"
	fi

	python3 /dev/stdin <<'PYEOF' 2>/dev/null || true
import json, os, sys
with open('feature_list.json') as f:
    data = json.load(f)

valid_status = {"pending", "spec_ready", "in_progress", "done", "blocked"}
errors = []

for feat in data['features']:
    if feat['status'] not in valid_status:
        errors.append(f"{feat['id']}: estado inválido '{feat['status']}'")

in_progress = [f for f in data['features'] if f['status'] == 'in_progress']
if len(in_progress) > 1:
    names = ', '.join(f['id'] for f in in_progress)
    errors.append(f"Múltiples features 'in_progress': {names}")

requires_spec = {"spec_ready", "in_progress", "done"}
for feat in data['features']:
    if feat.get('sdd') and feat['status'] in requires_spec:
        spec_dir = os.path.join('specs', feat['name'])
        for fname in ('requirements.md', 'design.md', 'tasks.md'):
            if not os.path.isfile(os.path.join(spec_dir, fname)):
                errors.append(f"{feat['id']}: sdd=true, status={feat['status']}, falta {spec_dir}/{fname}")

if errors:
    for e in errors:
        print(f"[WARN]  {e}")
    sys.exit(1)
else:
    print(f"[OK]    feature_list.json válido ({len(data['features'])} features)")
    in_prog = [f for f in data['features'] if f['status'] == 'in_progress']
    if in_prog:
        print(f"        1 feature en progreso: {in_prog[0]['id']} — {in_prog[0]['name']}")
    else:
        print("        Ningún feature en progreso")
PYEOF

	if [ $? -eq 0 ]; then
		pass "Validación feature_list completada"
	else
		fail "Errores en feature_list.json"
	fi
else
	warn "feature_list.json no encontrado — se salta"
fi

# ── Progress files check ──────────────────────────
section "Progress Files"
for f in progress/current.md progress/progress.md progress/backlog.md progress/decisions.md progress/handoff.md; do
	if [ -f "$f" ]; then
		pass "Existe $f"
	else
		warn "Falta $f"
	fi
done

# ── SDD Infrastructure check ──────────────────────
section "SDD Infrastructure"
for f in specs/README.md specs/templates/requirements.md specs/templates/design.md specs/templates/tasks.md; do
	if [ -f "$f" ]; then
		pass "Existe $f"
	else
		warn "Falta $f"
	fi
done

# ── Summary ─────────────────────────────────────────
section "Resultado"
if [ "$EXIT_CODE" -eq 0 ]; then
	echo "  ✅ Todos los checks pasaron — entorno listo"
else
	echo "  ❌ Algunos checks fallaron — resuelve antes de continuar"
fi
echo ""
exit "$EXIT_CODE"
