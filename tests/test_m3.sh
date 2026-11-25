#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/tests"
# The modules are independent (each works in its own temporary directory), so
# they run side by side; a failing module's output is printed in full.
logs=$(mktemp -d)
trap 'rm -rf "$logs"' EXIT
modules="test_workflow_state test_workflow_recovery test_workflow_commands test_review_attestation test_evidence_gate test_workflow_safety test_workflow_classification test_trusted_verify test_github_api"
for module in $modules; do
    ( python3 -m unittest "$module" >"$logs/$module.log" 2>&1; echo $? >"$logs/$module.rc" ) &
done
wait
status=0
for module in $modules; do
    if [ "$(cat "$logs/$module.rc" 2>/dev/null)" = "0" ]; then
        echo "ok: $module ($(grep '^Ran ' "$logs/$module.log"))"
    else
        status=1
        echo "FAILED: $module"
        cat "$logs/$module.log"
    fi
done
exit "$status"
