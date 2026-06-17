#!/bin/bash
# bootstrap.sh — Generate the native config adapter for your CLI from .agents/agentic.json
#
# Workflow:
#   ./.agents/bootstrap.sh <cli>                 # Render the native config for <cli>
#   ./.agents/bootstrap.sh --all                 # Render for every adapter that exists
#   ./.agents/bootstrap.sh --check               # Re-render to a temp file and diff; exit 1 if drift
#   ./.agents/bootstrap.sh detect                # Detect available CLIs and project stack
#
# Scaffold lifecycle (project shaping):
#   ./.agents/bootstrap.sh init                  # Show /init workflow + current scaffold-lifecycle state
#   ./.agents/bootstrap.sh init --validate       # Objective completion gate (exits 0 if /init is complete)
#   ./.agents/bootstrap.sh profile               # Report: active set + matching template examples
#   ./.agents/bootstrap.sh add-agent <name>      # Promote a template example to the active manifest
#   ./.agents/bootstrap.sh add-agent --all-matched  # Promote all examples that match this project
#   ./.agents/bootstrap.sh remove-examples       # Drop template scaffolds from the manifest (final stage)
#   ./.agents/bootstrap.sh add-steering <name>    # Add a steering file and register in agentic.json
#   ./.agents/bootstrap.sh remove-steering <name> # Remove a steering entry from agentic.json
#   ./.agents/bootstrap.sh --list-steering        # List current steering files
#   ./.agents/bootstrap.sh add-hook                # Add a lifecycle hook (--event, --script, --on-failure)
#   ./.agents/bootstrap.sh remove-hook             # Remove a hook entry from agentic.json
#   ./.agents/bootstrap.sh --list-hooks            # List registered hooks
#
# Housekeeping:
#   ./.agents/bootstrap.sh --list-adapters       # List adapters in .agents/adapters/
#   ./.agents/bootstrap.sh --list-orphans        # List canonical subagents on disk but missing from agentic.json
#   ./.agents/bootstrap.sh --list-examples       # List template example sub-agents
#   ./.agents/bootstrap.sh prune                 # Delete orphaned canonical subagent directories
#   ./.agents/bootstrap.sh --help                # Show this help

set -uo pipefail

if [ -n "${ROOT_DIR:-}" ]; then
    ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
else
    ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi
RENDERER="$ROOT_DIR/.agents/adapters/_common/render.py"
ADAPTERS_DIR="$ROOT_DIR/.agents/adapters"

print_help() {
    sed -n '2,20p' "$0" | sed 's/^# \?//'
}

list_adapters() {
    echo "Available adapters in $ADAPTERS_DIR:"
    for dir in "$ADAPTERS_DIR"/*/; do
        [ -d "$dir" ] || continue
        name=$(basename "$dir")
        [ "$name" = "_common" ] && continue
        [ "$name" = "_generic" ] && continue
        if ls "$dir"/*.tmpl &>/dev/null; then
            echo "  - $name"
        fi
    done
}

list_examples() {
    python3 "$RENDERER" --list-examples --root "$ROOT_DIR"
}

remove_examples_run() {
    local yes_flag=""
    while [ "${1:-}" != "" ]; do
        case "$1" in
            --yes|-y) yes_flag="1" ;;
            *)
                echo "ERROR: unknown remove-examples option: $1" >&2
                return 1
                ;;
        esac
        shift
    done

    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local n
    n=$(python3 "$RENDERER" --list-examples --root "$ROOT_DIR" 2>/dev/null | wc -l | tr -d ' ')
    if [ "${n:-0}" -eq 0 ]; then
        echo "No template scaffolds to remove — the manifest is already clean."
        return 0
    fi

    echo "This will drop the template scaffolds from .agents/agentic.json:"
    echo "  - _template_subagents_examples[] ($n entries)"
    echo "  - _template_lifecycle"
    echo ""
    echo "The leading-underscore convention guarantees they were never rendered."
    echo "Sub-agents already promoted to subagents[] (via 'add-agent') are NOT affected."
    echo ""

    local confirm="n"
    if [ -n "$yes_flag" ]; then
        confirm="y"
    elif [ -t 0 ]; then
        printf "Remove the template scaffolds? [y/N]: "
        read -r confirm
    fi
    case "$confirm" in
        y|Y|yes|YES)
            echo ""
            python3 "$RENDERER" --remove-examples --root "$ROOT_DIR"
            echo ""
            echo "Re-rendering adapters for all CLIs..."
            ROOT_DIR="$ROOT_DIR" "$ROOT_DIR/.agents/bootstrap.sh" --all >/dev/null
            echo ""
            echo "Done. The manifest now contains only the project's sub-agents."
            ;;
        *)
            echo "Aborted. No changes made."
            ;;
    esac
}

prune_orphans() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi
    python3 "$RENDERER" --prune --root "$ROOT_DIR"
}

list_steering() {
    python3 -c "
import json
m = json.load(open('$ROOT_DIR/.agents/agentic.json'))
for s in m.get('steering', []):
    print(f'{s[\"name\"]}  file={s[\"file\"]}  applies_to={s.get(\"applies_to\",[\"*\"])}  {s.get(\"description\",\"\")}')
if not m.get('steering'):
    print('(no steering files active)')
"
}

add_steering_run() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local name=""
    local description=""
    local applies_to="*"

    while [ "${1:-}" != "" ]; do
        case "$1" in
            --description) description="$2"; shift 2 ;;
            --applies-to)  applies_to="$2"; shift 2 ;;
            --yes|-y) ;;
            -*)
                echo "ERROR: unknown add-steering option: $1" >&2
                echo "Usage: ./.agents/bootstrap.sh add-steering <name> --description '...' [--applies-to 'agent1,agent2']" >&2
                return 1
                ;;
            *)
                if [ -z "$name" ]; then
                    name="$1"
                else
                    echo "ERROR: unexpected positional argument: $1" >&2
                    return 1
                fi
                ;;
        esac
        shift
    done

    if [ -z "$name" ]; then
        echo "Usage: ./.agents/bootstrap.sh add-steering <name> --description '...' [--applies-to 'agent1,agent2']" >&2
        echo ""
        echo "Current steering files:"
        list_steering | sed 's/^/  /'
        return 1
    fi

    local file="steering/${name}.md"

    # Create steering/ directory if missing
    mkdir -p "$ROOT_DIR/steering"

    # Create steering file from template if it doesn't exist
    if [ ! -f "$ROOT_DIR/$file" ]; then
        local template="$ROOT_DIR/specs/templates/steering.md"
        if [ -f "$template" ]; then
            cp "$template" "$ROOT_DIR/$file"
        else
            # Minimal fallback template
            cat > "$ROOT_DIR/$file" <<EOF
---
name: ${name}
description: "${description}"
applies_to:
  - ${applies_to//,/", "}
---

# ${name}

## Contexto

<!-- TODO: describir el contexto -->

## Reglas

1. <!-- TODO: regla 1 -->

## Anti-patrones

- <!-- TODO: anti-patrón 1 -->
EOF
        fi
        echo "Created $file"
    else
        echo "Steering file already exists: $file (reusing)"
    fi

    # Add entry to agentic.json
    python3 -c "
import json, sys
manifest_path = '$ROOT_DIR/.agents/agentic.json'
with open(manifest_path) as f:
    m = json.load(f)
name = '$name'
# Remove if already exists (update)
m['steering'] = [h for h in m.get('steering', []) if h.get('name') != name]
# Parse applies_to list
applies_raw = '$applies_to'
applies_list = [a.strip() for a in applies_raw.split(',') if a.strip()]
m['steering'].append({
    'name': name,
    'file': '$file',
    'description': '$description',
    'applies_to': applies_list,
})
with open(manifest_path, 'w') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
print(f'Added steering entry: {name}')
"

    echo ""
    echo "Re-rendering adapters for all CLIs..."
    ROOT_DIR="$ROOT_DIR" "$ROOT_DIR/.agents/bootstrap.sh" --all >/dev/null
    echo "Done."
}

remove_steering_run() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local name="${1:-}"
    if [ -z "$name" ]; then
        echo "Usage: ./.agents/bootstrap.sh remove-steering <name>" >&2
        echo ""
        echo "Current steering files:"
        list_steering | sed 's/^/  /'
        return 1
    fi

    python3 -c "
import json, sys
manifest_path = '$ROOT_DIR/.agents/agentic.json'
with open(manifest_path) as f:
    m = json.load(f)
name = '$name'
before = len(m.get('steering', []))
m['steering'] = [h for h in m.get('steering', []) if h.get('name') != name]
after = len(m['steering'])
with open(manifest_path, 'w') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
if before == after:
    print(f'Steering entry \"{name}\" not found in agentic.json (no change)')
else:
    print(f'Removed steering entry: {name} (file on disk NOT deleted)')
"

    echo ""
    echo "Re-rendering adapters for all CLIs..."
    ROOT_DIR="$ROOT_DIR" "$ROOT_DIR/.agents/bootstrap.sh" --all >/dev/null
    echo "Done."
}

list_hooks() {
    python3 -c "
import json
m = json.load(open('$ROOT_DIR/.agents/agentic.json'))
for h in m.get('hooks', []):
    print(f'{h[\"event\"]:<28} script={h[\"script\"]}  on_failure={h.get(\"on_failure\",\"warn\")}  {h.get(\"description\",\"\")}')
if not m.get('hooks'):
    print('(no hooks registered)')
"
}

add_hook_run() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local event=""
    local script=""
    local description=""
    local on_failure="warn"

    while [ "${1:-}" != "" ]; do
        case "$1" in
            --event)        event="$2"; shift 2 ;;
            --script)       script="$2"; shift 2 ;;
            --description)  description="$2"; shift 2 ;;
            --on-failure)   on_failure="$2"; shift 2 ;;
            --yes|-y) ;;
            -*)
                echo "ERROR: unknown add-hook option: $1" >&2
                echo "Usage: ./.agents/bootstrap.sh add-hook --event <event> --script <path> [--description '...'] [--on-failure warn|error|ignore]" >&2
                return 1
                ;;
            *)
                echo "ERROR: unexpected positional argument: $1" >&2
                return 1
                ;;
        esac
        shift
    done

    if [ -z "$event" ] || [ -z "$script" ]; then
        echo "Usage: ./.agents/bootstrap.sh add-hook --event <event> --script <path> [--description '...'] [--on-failure warn|error|ignore]" >&2
        echo ""
        echo "Known events: on_spec_created, on_spec_approved, on_implementation_start, on_implementation_complete, on_review_start, on_review_complete, on_feature_done, on_check_pass"
        echo ""
        echo "Current hooks:"
        list_hooks | sed 's/^/  /'
        return 1
    fi

    if [ -z "$description" ]; then
        description="Hook for event: $event"
    fi

    # Create script if it doesn't exist
    if [ ! -f "$ROOT_DIR/$script" ]; then
        mkdir -p "$(dirname "$ROOT_DIR/$script")"
        cat > "$ROOT_DIR/$script" <<EOF
#!/bin/bash
# Hook: $event — $description
echo "Hook $event triggered"
echo "Feature: \${FEATURE_ID:-\?} — \${FEATURE_NAME:-\?}"
# TODO: customize this hook
EOF
        chmod +x "$ROOT_DIR/$script"
        echo "Created $script (+x)"
    else
        echo "Script already exists: $script (reusing)"
    fi

    # Add entry to agentic.json
    python3 -c "
import json
manifest_path = '$ROOT_DIR/.agents/agentic.json'
with open(manifest_path) as f:
    m = json.load(f)
# Remove existing entry for same event+script (update)
m['hooks'] = [h for h in m.get('hooks', []) if not (h.get('event') == '$event' and h.get('script') == '$script')]
m['hooks'].append({
    'event': '$event',
    'script': '$script',
    'description': '$description',
    'on_failure': '$on_failure',
})
with open(manifest_path, 'w') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
print(f'Added hook: {event} -> {script}')
"

    echo ""
    echo "Re-rendering adapters for all CLIs..."
    ROOT_DIR="$ROOT_DIR" "$ROOT_DIR/.agents/bootstrap.sh" --all >/dev/null
    echo "Done."
}

remove_hook_run() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local event=""
    local script=""

    while [ "${1:-}" != "" ]; do
        case "$1" in
            --event)   event="$2"; shift 2 ;;
            --script)  script="$2"; shift 2 ;;
            --yes|-y)  ;;
            -*)
                echo "ERROR: unknown remove-hook option: $1" >&2
                echo "Usage: ./.agents/bootstrap.sh remove-hook --event <event> --script <path>" >&2
                return 1
                ;;
            *)
                echo "ERROR: unexpected positional argument: $1" >&2
                return 1
                ;;
        esac
        shift
    done

    if [ -z "$event" ] || [ -z "$script" ]; then
        echo "Usage: ./.agents/bootstrap.sh remove-hook --event <event> --script <path>" >&2
        echo ""
        echo "Current hooks:"
        list_hooks | sed 's/^/  /'
        return 1
    fi

    python3 -c "
import json
manifest_path = '$ROOT_DIR/.agents/agentic.json'
with open(manifest_path) as f:
    m = json.load(f)
before = len(m.get('hooks', []))
m['hooks'] = [h for h in m.get('hooks', []) if not (h.get('event') == '$event' and h.get('script') == '$script')]
after = len(m['hooks'])
with open(manifest_path, 'w') as f:
    json.dump(m, f, indent=2, ensure_ascii=False)
    f.write('\n')
if before == after:
    print(f'Hook ({event}=\"$event\", script=\"$script\") not found in agentic.json (no change)')
else:
    print(f'Removed hook: {event}=$event script=$script (file on disk NOT deleted)')
"

    echo ""
    echo "Re-rendering adapters for all CLIs..."
    ROOT_DIR="$ROOT_DIR" "$ROOT_DIR/.agents/bootstrap.sh" --all >/dev/null
    echo "Done."
}

list_orphans() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi
    python3 "$RENDERER" --list-orphans --root "$ROOT_DIR"
}

init_show() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local manifest="$ROOT_DIR/.agents/agentic.json"
    if [ ! -f "$manifest" ]; then
        echo "ERROR: manifest not found at $manifest" >&2
        return 1
    fi

    local validate="0"
    while [ "${1:-}" != "" ]; do
        case "$1" in
            --validate) validate="1" ;;
            --yes|-y) ;;
            *)
                echo "ERROR: unknown init option: $1" >&2
                return 1
                ;;
        esac
        shift
    done

    if [ "$validate" = "1" ]; then
        local report
        report=$(python3 "$RENDERER" --validate-init --root "$ROOT_DIR" 2>&1)
        local rc=$?
        echo "=== /init — VALIDATION (objective completion gate) ==="
        echo ""
        echo "$report" | python3 -c "
import json, sys
try:
    data = sys.stdin.read()
    start = data.find('{')
    r = json.loads(data[start:])
    print(f'  State:     {r[\"state\"]}')
    print(f'  Active:    {r.get(\"active_count\", 0)} sub-agent(s)')
    print(f'  Scaffolds: {r.get(\"scaffold_count\", 0)} remaining')
    print(f'  Summary:   {r[\"summary\"]}')
    print()
    if r.get('errors'):
        print(f'  ERRORS ({len(r[\"errors\"])}):')
        for e in r['errors']:
            print(f'    - {e}')
    if r.get('warnings'):
        print(f'  WARNINGS ({len(r[\"warnings\"])}):')
        for w in r['warnings']:
            print(f'    - {w}')
    print()
    if r['ok']:
        print('  RESULT: /init is COMPLETE.')
    else:
        print('  RESULT: /init is NOT complete. Fix the errors above and re-run.')
except Exception as ex:
    print(f'  ERROR parsing validation report: {ex}', file=sys.stderr)
    print(data, file=sys.stderr)
    sys.exit(1)
"
        return $rc
    fi

    local n_active
    n_active=$(python3 -c "import json; m=json.load(open('$manifest')); print(len(m.get('subagents', [])))")
    local n_scaffolds
    n_scaffolds=$(python3 -c "import json; m=json.load(open('$manifest')); print(len(m.get('_template_subagents_examples', [])))")
    local n_steering_scaffolds
    n_steering_scaffolds=$(python3 -c "import json; m=json.load(open('$manifest')); print(len(m.get('_template_steering_examples', [])))")
    local n_hooks_scaffolds
    n_hooks_scaffolds=$(python3 -c "import json; m=json.load(open('$manifest')); print(len(m.get('_template_hooks_examples', [])))")
    local total_scaffolds=$((n_scaffolds + n_steering_scaffolds + n_hooks_scaffolds))

    local validate="0"
    while [ "${1:-}" != "" ]; do
        case "$1" in
            --validate) validate="1" ;;
            --yes|-y) ;;
            *)
                echo "ERROR: unknown init option: $1" >&2
                return 1
                ;;
        esac
        shift
    done

    if [ "$validate" = "1" ]; then
        echo "=== /init — VALIDATION (objective completion gate) ==="
        echo ""
        local report
        report=$(python3 "$RENDERER" --validate-init --root "$ROOT_DIR" 2>&1)
        local rc=$?
        echo "$report" | python3 -c "
import json, sys
try:
    data = sys.stdin.read()
    start = data.find('{')
    r = json.loads(data[start:])
    print(f'  State:     {r[\"state\"]}')
    print(f'  Active:    {r.get(\"active_count\", 0)} sub-agent(s)')
    print(f'  Scaffolds: {r.get(\"scaffold_count\", 0)} remaining')
    print(f'  Summary:   {r[\"summary\"]}')
    print()
    if r.get('errors'):
        print(f'  ERRORS ({len(r[\"errors\"])}):')
        for e in r['errors']:
            print(f'    - {e}')
    if r.get('warnings'):
        print(f'  WARNINGS ({len(r[\"warnings\"])}):')
        for w in r['warnings']:
            print(f'    - {w}')
    if r['ok']:
        print()
        print('  RESULT: /init is COMPLETE.')
    else:
        print()
        print('  RESULT: /init is NOT complete. Fix the errors above and re-run.')
except Exception as ex:
    print(f'  ERROR parsing validation report: {ex}', file=sys.stderr)
    print(data, file=sys.stderr)
    sys.exit(1)
"
        return $rc
    fi

    echo "=== /init — scaffold lifecycle status ==="
    echo ""
    if [ "${n_active:-0}" -eq 0 ] && [ "${total_scaffolds:-0}" -gt 0 ]; then
        echo "  State:  FRESH INSTALL — subagents[] is empty, $total_scaffolds scaffold(s) in _template_* arrays"
        echo "          (${n_scaffolds:-0} sub-agent(s), ${n_steering_scaffolds:-0} steering, ${n_hooks_scaffolds:-0} hook(s))."
        echo "          The agent should run /init to shape the manifest to this project."
        echo "          Suggested next command: tell the agent \"run /init\"."
    elif [ "${n_active:-0}" -gt 0 ] && [ "${total_scaffolds:-0}" -gt 0 ]; then
        echo "  State:  PARTIAL — subagents[] has $n_active entries (project-specific), $total_scaffolds scaffold(s) remain"
        echo "          (${n_scaffolds:-0} sub-agent(s), ${n_steering_scaffolds:-0} steering, ${n_hooks_scaffolds:-0} hook(s))."
        echo "          The agent should finish /init by running 'remove-examples' once the project's"
        echo "          sub-agents, steering files, and hooks are in place."
    elif [ "${n_active:-0}" -gt 0 ] && [ "${total_scaffolds:-0}" -eq 0 ]; then
        echo "  State:  INITIALIZED — subagents[] has $n_active project-specific entry(ies), no scaffolds remain."
        echo "          The project is shaped. /init is not needed again."
    else
        echo "  State:  EMPTY — subagents[] and all _template_* arrays are empty."
        echo "          Run ./check.sh to diagnose."
    fi
    echo ""
    echo "  Active sub-agents (subagents[]):"
    if [ "${n_active:-0}" -gt 0 ]; then
        python3 -c "
import json
m = json.load(open('$manifest'))
for a in m.get('subagents', []):
    desc = a.get('description', '')[:60]
    print(f'    - {a[\"name\"]:<24} {desc}')
"
    else
        echo "    (none)"
    fi
    echo ""
    echo "  Scaffold examples (_template_subagents_examples[]):"
    if [ "${n_scaffolds:-0}" -gt 0 ]; then
        python3 -c "
import json
m = json.load(open('$manifest'))
for a in m.get('_template_subagents_examples', []):
    cat = a.get('category', '?')
    intent = a.get('_intent', '').split('.')[0][:60]
    print(f'    - {a[\"name\"]:<24} [{cat}]  {intent}')
"
    else
        echo "    (none)"
    fi
    echo ""
    echo "  Steering scaffolds (_template_steering_examples[]):"
    if [ "${n_steering_scaffolds:-0}" -gt 0 ]; then
        python3 -c "
import json
m = json.load(open('$manifest'))
for a in m.get('_template_steering_examples', []):
    applies = a.get('applies_to', ['*'])
    intent = a.get('_intent', '').split('.')[0][:60]
    print(f'    - {a[\"name\"]:<24} applies_to={applies}  {intent}')
"
    else
        echo "    (none)"
    fi
    echo ""
    echo "  Hook scaffolds (_template_hooks_examples[]):"
    if [ "${n_hooks_scaffolds:-0}" -gt 0 ]; then
        python3 -c "
import json
m = json.load(open('$manifest'))
for a in m.get('_template_hooks_examples', []):
    failure = a.get('on_failure', 'warn')
    intent = a.get('_intent', '').split('.')[0][:60]
    print(f'    - {a[\"event\"]:<28} on_failure={failure}  {intent}')
"
    else
        echo "    (none)"
    fi
    echo ""
    echo "  Agent workflow (./.agents/commands/init.md):"
    echo "    1. Read the project (README, feature_list.json, layout)."
    echo "    2. Decide which sub-agents the project needs (always the 4 canonicals,"
    echo "       plus any stack-specific illustratives: python, terraform, frontend, data)."
    echo "    3. For each: either ./bootstrap.sh add-agent <name> --yes   (borrow as-is)"
    echo "                or copy the entry to subagents[] and customize (recommended)."
    echo "    4. Decide which steering files and hooks the project needs."
    echo "       Use ./bootstrap.sh add-steering <name> and add-hook --event <event> --script <path>."
    echo "    5. ./bootstrap.sh remove-examples --yes   (drop the scaffolds)."
    echo "    6. ./bootstrap.sh init --validate         (objective completion gate, must exit 0)."
    echo "    7. ./check.sh                              (must be green)."
    echo ""
    echo "  Tell the agent: \"run /init\"  (or invoke the init slash command directly)."
    echo "  Completion gate: ./bootstrap.sh init --validate   (MUST exit 0 before init is declared done)"
    echo ""
    echo "  Reference: AGENTS.md §0.5 — Project Profiling (3-stage lifecycle)."
}

profile_run() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local report
    report=$(python3 "$RENDERER" --profile --root "$ROOT_DIR" 2>&1)
    if [ $? -ne 0 ]; then
        echo "$report"
        return 1
    fi

    echo "Project profile (scaffold lifecycle):"
    echo ""
    echo "$report" | python3 -c "
import json, sys
data = sys.stdin.read()
start = data.find('{')
r = json.loads(data[start:])
print(f'  Detected stack: {\", \".join(r[\"detected_stack\"]) or \"(none)\"}')
print('')
print('  STAGE 3 — Final (project-only) state of subagents[]:')
if r['active']:
    for a in r['active']:
        marker = '+' if a['action'] == 'scaffold' else '·'
        print(f'    {marker} {a[\"name\"]:<22} {a[\"reason\"]}')
else:
    print('    (none yet — go to STAGE 2 to populate)')
print('')
print('  STAGE 1 — Scaffolds still in _template_subagents_examples[]:')
n_match = len(r['examples_matching'])
n_idle  = len(r['examples_idle'])
if n_match or n_idle:
    for e in r['examples_matching']:
        print(f'    ~ {e[\"name\"]:<22} {e[\"reason\"]}  -> add-agent {e[\"name\"]}')
    for e in r['examples_idle']:
        if e.get('source') == '_template_subagents_examples':
            print(f'    . {e[\"name\"]:<22} (not relevant for this project)')
    print('')
    print(f'    Total scaffolds: {n_match + n_idle}  (use \"remove-examples\" to drop them all)')
else:
    print('    (none — scaffolds already removed; project-only state)')
print('')
print('  Workflow:')
print('    STAGE 1. Scaffold   — read this profile to see the patterns.')
print('    STAGE 2. Implement  — copy a scaffold into subagents[] and customize it.')
print('                       (or: ./bootstrap.sh add-agent <name>   to borrow as-is)')
print('    STAGE 3. Remove     — ./bootstrap.sh remove-examples     to drop the scaffolds.')

# Also show steering and hooks information
print()
n_steer = len(json.loads('''$(python3 -c "import json; m=json.load(open('$manifest')); print(json.dumps(m.get('_template_steering_examples', [])))")'''))
n_hooks = len(json.loads('''$(python3 -c "import json; m=json.load(open('$manifest')); print(json.dumps(m.get('_template_hooks_examples', [])))")'''))
n_active_steer = len(json.loads('''$(python3 -c "import json; m=json.load(open('$manifest')); print(json.dumps(m.get('steering', [])))")'''))
n_active_hooks = len(json.loads('''$(python3 -c "import json; m=json.load(open('$manifest')); print(json.dumps(m.get('hooks', [])))")'''))
print(f'  Steering: {n_active_steer} active, {n_steer} scaffold(s)')
print(f'  Hooks:    {n_active_hooks} active, {n_hooks} scaffold(s)')
print(f'  Use add-steering / add-hook to promote scaffolds.')
"
}

add_agent_run() {
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi

    local yes_flag=""
    local name=""
    local mode=""
    while [ "${1:-}" != "" ]; do
        case "$1" in
            --yes|-y) yes_flag="1" ;;
            --all-matched|--matched) mode="all-matched" ;;
            -*)
                echo "ERROR: unknown add-agent option: $1" >&2
                return 1
                ;;
            *)
                if [ -z "$name" ]; then
                    name="$1"
                else
                    echo "ERROR: unexpected positional argument: $1" >&2
                    return 1
                fi
                ;;
        esac
        shift
    done

    if [ "$mode" = "all-matched" ]; then
        local matched
        matched=$(python3 "$RENDERER" --profile --root "$ROOT_DIR" 2>&1 | python3 -c "
import json, sys
data = sys.stdin.read()
start = data.find('{')
r = json.loads(data[start:])
print('\n'.join(e['name'] for e in r['examples_matching']))
")
        if [ -z "$matched" ]; then
            echo "No template examples match this project. Nothing to add."
            return 0
        fi
        echo "Promoting all template examples that match this project:"
        echo "$matched" | sed 's/^/  - /'
        echo ""
        local confirm="n"
        if [ -n "$yes_flag" ]; then
            confirm="y"
        elif [ -t 0 ]; then
            printf "Proceed? [y/N]: "
            read -r confirm
        fi
        case "$confirm" in
            y|Y|yes|YES)
                local any_added=0
                while IFS= read -r n; do
                    [ -z "$n" ] && continue
                    echo ""
                    python3 "$RENDERER" --add-agent "$n" --root "$ROOT_DIR"
                    any_added=1
                done <<< "$matched"
                if [ "$any_added" -eq 1 ]; then
                    echo ""
                    echo "Re-rendering adapters for all CLIs..."
                    ROOT_DIR="$ROOT_DIR" "$ROOT_DIR/.agents/bootstrap.sh" --all >/dev/null
                fi
                ;;
            *)
                echo "Aborted. No changes made."
                return 0
                ;;
        esac
        return 0
    fi

    if [ -z "$name" ]; then
        echo "Usage: ./.agents/bootstrap.sh add-agent <name> [--yes] | --all-matched [--yes]" >&2
        echo ""
        echo "Available template examples:"
        list_examples | sed 's/^/  - /'
        return 1
    fi

    local confirm="n"
    if [ -n "$yes_flag" ]; then
        confirm="y"
    elif [ -t 0 ]; then
        printf "Promote '%s' from _template_subagents_examples to subagents[]? [y/N]: " "$name"
        read -r confirm
    fi
    case "$confirm" in
        y|Y|yes|YES)
            python3 "$RENDERER" --add-agent "$name" --root "$ROOT_DIR"
            echo ""
            echo "Re-rendering adapters for all CLIs..."
            ROOT_DIR="$ROOT_DIR" "$ROOT_DIR/.agents/bootstrap.sh" --all >/dev/null
            ;;
        *)
            echo "Aborted. No changes made."
            ;;
    esac
}

detect() {
    echo "Detecting CLIs and project stack..."
    echo ""
    echo "Available adapters:"
    list_adapters
    echo ""
    if [ -x "$RENDERER" ] || [ -f "$RENDERER" ]; then
        python3 "$RENDERER" --detect-stack --root "$ROOT_DIR"
    else
        echo "(project stack detection unavailable: $RENDERER not found)"
    fi
}

render_one() {
    local cli="$1"
    if [ ! -d "$ADAPTERS_DIR/$cli" ]; then
        echo "ERROR: No adapter for CLI '$cli' under $ADAPTERS_DIR/$cli/" >&2
        echo "       Available adapters:" >&2
        for d in "$ADAPTERS_DIR"/*/; do
            [ -d "$d" ] || continue
            n=$(basename "$d")
            [ "$n" = "_common" ] || [ "$n" = "_generic" ] && continue
            echo "         - $n" >&2
        done
        echo "       For unknown CLIs, read $ROOT_DIR/.agents/BOOTSTRAP.md" >&2
        return 1
    fi
    if [ ! -f "$RENDERER" ]; then
        echo "ERROR: Renderer not found at $RENDERER" >&2
        return 1
    fi
    python3 "$RENDERER" --cli "$cli" --root "$ROOT_DIR"
}

render_all() {
    local rc=0
    for dir in "$ADAPTERS_DIR"/*/; do
        [ -d "$dir" ] || continue
        name=$(basename "$dir")
        [ "$name" = "_common" ] || [ "$name" = "_generic" ] && continue
        if ls "$dir"/*.tmpl &>/dev/null; then
            echo "=== Rendering for $name ==="
            if ! render_one "$name"; then
                rc=1
            fi
            echo ""
        fi
    done
    return $rc
}

check_drift() {
    echo "Checking adapter consistency (re-render and diff)..."
    local rc=0
    for dir in "$ADAPTERS_DIR"/*/; do
        [ -d "$dir" ] || continue
        name=$(basename "$dir")
        [ "$name" = "_common" ] || [ "$name" = "_generic" ] && continue
        if ls "$dir"/*.tmpl &>/dev/null; then
            if ! python3 "$RENDERER" --cli "$name" --root "$ROOT_DIR" --check; then
                rc=1
            fi
        fi
    done
    return $rc
}

case "${1:-help}" in
    detect)            detect ;;
    --detect)          detect ;;
    --list-adapters)   list_adapters ;;
    --list-orphans)    list_orphans ;;
    --list-examples)   list_examples ;;
    init)              shift; init_show "$@"; exit $? ;;
    prune)             prune_orphans ;;
    profile)           shift; profile_run "$@" ;;
    add-agent)         shift; add_agent_run "$@" ;;
    remove-examples)   shift; remove_examples_run "$@" ;;
    add-steering)      shift; add_steering_run "$@" ;;
    remove-steering)   shift; remove_steering_run "$@" ;;
    --list-steering)   list_steering ;;
    add-hook)          shift; add_hook_run "$@" ;;
    remove-hook)       shift; remove_hook_run "$@" ;;
    --list-hooks)      list_hooks ;;
    --all)             render_all ;;
    --check)
        shift
        if [ $# -eq 0 ]; then
            check_drift
        else
            rc=0
            for cli in "$@"; do
                if ! python3 "$RENDERER" --cli "$cli" --root "$ROOT_DIR" --check; then
                    rc=1
                fi
            done
            exit $rc
        fi
        ;;
    --help|-h|help)    print_help ;;
    *)
        cli="$1"
        shift
        if [ "${1:-}" = "--check" ]; then
            python3 "$RENDERER" --cli "$cli" --root "$ROOT_DIR" --check
            exit $?
        else
            render_one "$cli"
        fi
        ;;
esac
