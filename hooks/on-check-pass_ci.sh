#!/bin/bash
# Hook: on_check_pass — record the timestamp of the last successful check.sh
mkdir -p "${ROOT_DIR:-.}/progress"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "${ROOT_DIR:-.}/progress/last-check-pass.txt"
echo "CI timestamp recorded in progress/last-check-pass.txt"
exit 0
