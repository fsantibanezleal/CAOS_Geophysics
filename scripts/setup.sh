#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY="${PYTHON:-python3.12}"
mkvenv() { [ -d "$1" ] || "$PY" -m venv "$1"; }
venvpy() { local p="$1/bin/python"; [ -x "$p" ] || p="$1/Scripts/python.exe"; echo "$p"; }
GPU=0
NOTEBOOKS=0
for arg in "$@"; do
  case "$arg" in
    --gpu) GPU=1 ;;
    --notebooks) NOTEBOOKS=1 ;;
    *) echo "setup: unknown option $arg (use --gpu or --notebooks)"; exit 2 ;;
  esac
done
if [ "$NOTEBOOKS" -eq 1 ]; then
  mkvenv .venv-notebooks
  VN="$(venvpy .venv-notebooks)"
  "$VN" -m pip install --upgrade pip -q
  "$VN" -m pip install -r notebooks/requirements.txt -q
  echo "[setup] notebook environment ready. Run python scripts/run_notebooks.py --check --tmp <device-temp-root>."
  exit 0
fi
mkvenv .venv; mkvenv .venv-pipeline
VR="$(venvpy .venv)"; VP="$(venvpy .venv-pipeline)"
"$VR" -m pip install --upgrade pip -q; "$VP" -m pip install --upgrade pip -q
"$VR" -m pip install -r requirements.txt -q
"$VP" -m pip install -r requirements-precompute.txt -r requirements-dev.txt -q
if [ "$GPU" -eq 1 ]; then "$VP" -m pip install -r requirements-gpu.txt -q; else "$VP" -m pip install torch==2.14.0 deepwave==0.0.27; fi
echo "[setup] complete. Use an explicit ignored --output for precompute; assemble and validate EDI before release."
