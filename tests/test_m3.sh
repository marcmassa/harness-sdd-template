#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/tests"
python3 -m unittest test_workflow_state test_workflow_recovery test_workflow_commands test_review_attestation test_evidence_gate \
    test_workflow_safety test_workflow_classification test_trusted_verify test_github_api
