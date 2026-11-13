#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY=".venv-pipeline/bin/python"; [ -x "$PY" ] || PY=".venv-pipeline/Scripts/python.exe"
"$PY" data-pipeline/rebuild.py "$@"
