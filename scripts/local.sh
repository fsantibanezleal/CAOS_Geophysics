#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
COMMAND="${1:-check}"
case "$COMMAND" in
  dev) (cd frontend && npm run dev) ;;
  build) (cd frontend && npm ci && npm run build) ;;
  check)
    PY=".venv-pipeline/bin/python"; [ -x "$PY" ] || PY=".venv-pipeline/Scripts/python.exe"
    [ -x "$PY" ] || { echo "Run scripts/setup.sh --gpu to create .venv-pipeline" >&2; exit 2; }
    "$PY" tests/run_validation.py
    "$PY" scripts/check_artifacts.py
    "$PY" scripts/check_phase_assets.py
    "$PY" scripts/check_sdd_convergence.py
    "$PY" scripts/check_template_residue.py
    (cd frontend && npm test && npm run build) ;;
  stop) echo 'Use Ctrl+C in the terminal that launched this app. Other Node processes are not touched.' ;;
  *) echo "usage: ./scripts/local.sh {dev|build|check|stop}"; exit 2 ;;
esac
