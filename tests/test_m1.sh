#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m unittest discover -s "$ROOT_DIR/tests" -p 'test_m1_*.py' -v
