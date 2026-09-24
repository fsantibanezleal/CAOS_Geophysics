#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
COMMAND="${1:-check}"
case "$COMMAND" in
  dev) (cd frontend && npm run dev) ;;
  build) (cd frontend && npm install && npm run build) ;;
  check) PY=".venv-pipeline/bin/python"; [ -x "$PY" ] || PY=".venv-pipeline/Scripts/python.exe"; "$PY" -m pytest; python scripts/check_artifacts.py; python scripts/check_template_residue.py ;;
  stop) echo 'Use Ctrl+C in the terminal that launched this app. Other Node processes are not touched.' ;;
  *) echo "usage: ./scripts/local.sh {dev|build|check|stop}"; exit 2 ;;
esac
