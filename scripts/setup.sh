#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY="${PYTHON:-python3.12}"
mkvenv() { [ -d "$1" ] || "$PY" -m venv "$1"; }
venvpy() { local p="$1/bin/python"; [ -x "$p" ] || p="$1/Scripts/python.exe"; echo "$p"; }
GPU=0
NOTEBOOKS=0
M08=0
API=0
ERT=0
for arg in "$@"; do
  case "$arg" in
    --gpu) GPU=1 ;;
    --notebooks) NOTEBOOKS=1 ;;
    --m08) M08=1 ;;
    --api) API=1 ;;
    --ert) ERT=1 ;;
    *) echo "setup: unknown option $arg (use --gpu, --api, --notebooks, --m08, or --ert)"; exit 2 ;;
  esac
done
if [ "$ERT" -eq 1 ]; then
  mkvenv .venv-ert
  VERT="$(venvpy .venv-ert)"
  "$VERT" -m pip install --upgrade pip -q
  "$VERT" -m pip install -r data-pipeline/requirements-ert.txt -q
  "$VERT" -m pip check
  echo "[setup] M07 solver ready. Run scripts/run_notebooks.py --only notebooks/en/05-ert/02-ert-inversion.ipynb."
  exit 0
fi
if [ "$NOTEBOOKS" -eq 1 ]; then
  mkvenv .venv-notebooks
  VN="$(venvpy .venv-notebooks)"
  "$VN" -m pip install --upgrade pip -q
  "$VN" -m pip install -r notebooks/requirements.txt -q
  echo "[setup] notebook environment ready. Run python scripts/run_notebooks.py --check --tmp <device-temp-root>."
  exit 0
fi
if [ "$API" -eq 1 ]; then
  mkvenv .venv-api
  VAPI="$(venvpy .venv-api)"
  "$VAPI" -m pip install --upgrade pip -q
  "$VAPI" -m pip install -r requirements-api.txt -r requirements-dev.txt -q
  "$VAPI" -m pip check
  echo "[setup] API environment ready. Run .venv-api/bin/python -m pytest tests/api -q."
  exit 0
fi
if [ "$M08" -eq 1 ]; then
  mkvenv .venv-m08
  VM08="$(venvpy .venv-m08)"
  "$VM08" -m pip install --upgrade pip -q
  "$VM08" -m pip install -r data-pipeline/requirements-m08.txt -q
  "$VM08" -m pip check
  echo "[setup] M08 environment ready. Set M08_TEST_SCIENCE_PYTHON to .venv-m08/bin/python for local validation."
  exit 0
fi
mkvenv .venv; mkvenv .venv-pipeline
VR="$(venvpy .venv)"; VP="$(venvpy .venv-pipeline)"
"$VR" -m pip install --upgrade pip -q; "$VP" -m pip install --upgrade pip -q
"$VR" -m pip install -r requirements.txt -q
"$VP" -m pip install -r requirements-precompute.txt -r requirements-dev.txt -q
if [ "$GPU" -eq 1 ]; then "$VP" -m pip install -r requirements-gpu.txt -q; else "$VP" -m pip install torch==2.14.0 deepwave==0.0.27; fi
echo "[setup] complete. Use an explicit ignored --output for precompute; assemble and validate EDI before release."
