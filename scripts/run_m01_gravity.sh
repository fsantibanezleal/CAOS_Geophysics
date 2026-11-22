#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_PATH="$REPO_ROOT/.venv-m01/bin/python"
if [[ ! -x "$PYTHON_PATH" ]]; then
    PYTHON_PATH="$REPO_ROOT/.venv-m01/Scripts/python.exe"
fi
if [[ ! -x "$PYTHON_PATH" ]]; then
    printf '%s\n' 'Create .venv-m01 and install data-pipeline/requirements-m01.txt first.' >&2
    exit 2
fi
exec "$PYTHON_PATH" "$REPO_ROOT/data-pipeline/gravity_processing.py" "$@"
