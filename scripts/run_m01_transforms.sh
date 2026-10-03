#!/usr/bin/env bash
set -Eeuo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_PATH="$REPO_ROOT/.venv-m01/bin/python"
SCRIPT_PATH="$REPO_ROOT/data-pipeline/gravity_transforms.py"
ARGS=("$@")
if [[ ! -x "$PYTHON_PATH" ]]; then
    PYTHON_PATH="$REPO_ROOT/.venv-m01/Scripts/python.exe"
    # WSL does not translate argv paths when calling a Windows Python binary.
    # Translate only the script and the two explicit path-valued CLI options.
    CONVERTER=""
    if command -v wslpath >/dev/null 2>&1; then CONVERTER=wslpath;
    elif command -v cygpath >/dev/null 2>&1; then CONVERTER=cygpath; fi
    if [[ -n "$CONVERTER" ]]; then
        SCRIPT_PATH="$("$CONVERTER" -w "$SCRIPT_PATH")"
        for ((i=0; i<${#ARGS[@]}; i++)); do
            if [[ "${ARGS[i]}" == --input || "${ARGS[i]}" == --output-dir ]]; then
                if ((i+1<${#ARGS[@]})); then
                    ARGS[i+1]="$("$CONVERTER" -w "$(realpath -m -- "${ARGS[i+1]}")")"
                    i=$((i+1))
                fi
            fi
        done
    fi
fi
if [[ ! -x "$PYTHON_PATH" ]]; then
    printf '%s\n' 'Create the owned .venv-m01 using requirements-m01-transforms.txt first.' >&2
    exit 2
fi
exec "$PYTHON_PATH" "$SCRIPT_PATH" "${ARGS[@]}"
