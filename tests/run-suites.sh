#!/usr/bin/env bash
# Runs the framework suites for check.sh, side by side. Register a new suite in SUITES.
#   HARNESS_CHECK_SERIAL=1 runs them one at a time (for debugging).
set -uo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SUITES="test_cli_adapter_parity test_agent_template_placeholders test_steering test_hooks test_soul_md test_portable_template test_target_clis test_plugin_adapters test_token_limit test_m1 test_team_policy test_m3 test_session_brief test_hook_runner test_inventory test_update test_capability_matrix test_docs_contract test_m5_e2e test_m4 test_release test_init_apply"
# These render adapters into the repository root, so they share one lane.
ROOT_SUITES=" test_cli_adapter_parity test_steering test_hooks test_portable_template test_target_clis test_plugin_adapters "

logs=$(mktemp -d)
trap 'rm -rf "$logs"' EXIT
run_suite() {
	bash "$ROOT_DIR/tests/$1.sh" >"$logs/$1.log" 2>&1
	echo $? >"$logs/$1.rc"
}
exists() { [ -f "$ROOT_DIR/tests/$1.sh" ]; }

if [ "${HARNESS_CHECK_SERIAL:-0}" = "1" ]; then
	for t in $SUITES; do
		exists "$t" && run_suite "$t"
	done
else
	(
		for t in $SUITES; do
			case "$ROOT_SUITES" in *" $t "*) exists "$t" && run_suite "$t" ;; esac
		done
	) &
	for t in $SUITES; do
		case "$ROOT_SUITES" in *" $t "*) continue ;; esac
		exists "$t" && run_suite "$t" &
	done
	wait
fi

status=0
for t in $SUITES; do
	if ! exists "$t"; then
		echo "  [FAIL] Missing required tests/${t}.sh"
		status=1
	elif [ "$(cat "$logs/$t.rc" 2>/dev/null)" = "0" ]; then
		echo "  [PASS] ${t}"
	else
		echo "  [FAIL] ${t} (bash tests/${t}.sh to reproduce); last lines:"
		tail -n 15 "$logs/$t.log" 2>/dev/null | sed 's/^/        /'
		status=1
	fi
done
# A suite on disk that nobody registered would silently never run.
for path in "$ROOT_DIR"/tests/test_*.sh; do
	name=$(basename "$path" .sh)
	case "$name" in *[!a-z0-9_]*) continue ;; esac
	case " $SUITES " in *" $name "*) ;; *) echo "  [FAIL] tests/${name}.sh is not registered in tests/run-suites.sh"; status=1 ;; esac
done
exit "$status"
