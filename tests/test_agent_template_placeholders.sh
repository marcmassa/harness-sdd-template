#!/bin/bash
# tests/test_agent_template_placeholders.sh
# ──────────────────────────────────────────────────────────────────────────────
# Verifica que `.agents/subagents/agent-template/SUBAGENT.md` no contiene
# placeholders huérfanos del estilo [Area 1], [Step 1], [Guideline 3], etc.
# que NO estén dentro de bloques de código (entre ```...```).
#
# Si el template no existe, el test hace SKIP con exit 0 (es opcional).
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE="$ROOT_DIR/.agents/subagents/agent-template/SUBAGENT.md"

if [ ! -f "$TEMPLATE" ]; then
    echo "SKIP: $TEMPLATE no existe (template opcional)"
    exit 0
fi

# Regex: línea que empieza con 0+ espacios, sigue con '[' + letra + (letras/dígitos/espacios/_/- máx 30) + ']'
PLACEHOLDER_RE='^[[:space:]]*\[[A-Za-z][A-Za-z0-9 _-]{0,30}\][[:space:]]*$'

FAIL=0
LINE_NO=0
IN_CODE=0

while IFS= read -r line; do
    LINE_NO=$((LINE_NO + 1))
    # Detectar toggles de bloque de código ``` (sin importar el lenguaje)
    if [[ "$line" =~ ^[[:space:]]*\`\`\` ]]; then
        IN_CODE=$((1 - IN_CODE))
        continue
    fi
    # Saltar líneas dentro de bloques de código (ejemplos)
    if [ "$IN_CODE" -eq 1 ]; then
        continue
    fi
    # Detectar placeholder huérfano
    if [[ "$line" =~ $PLACEHOLDER_RE ]]; then
        echo "FAIL: $TEMPLATE:$LINE_NO placeholder huérfano:"
        echo "  $line"
        FAIL=1
    fi
done < "$TEMPLATE"

if [ "$FAIL" -eq 1 ]; then
    echo ""
    echo "Acción: o bien reemplaza los placeholders por contenido real, o bien"
    echo "deja que `_sanitize_template_body()` los reemplace por"
    echo "<!-- TODO: personalizar esta sección --> al scaffold."
    exit 1
fi

echo "PASS: test_agent_template_placeholders"
