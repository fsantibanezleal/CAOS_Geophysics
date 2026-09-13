#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
PY="${PYTHON:-python3.12}"
mkvenv() { [ -d "$1" ] || "$PY" -m venv "$1"; }
venvpy() { local p="$1/bin/python"; [ -x "$p" ] || p="$1/Scripts/python.exe"; echo "$p"; }
GPU="${1:-}"
mkvenv .venv; mkvenv .venv-pipeline
VR="$(venvpy .venv)"; VP="$(venvpy .venv-pipeline)"
"$VR" -m pip install --upgrade pip -q; "$VP" -m pip install --upgrade pip -q
"$VR" -m pip install -r requirements.txt -q
"$VP" -m pip install -r requirements-precompute.txt -r requirements-dev.txt -q
"$VP" -m pip install -e . -q
if [ "$GPU" = "--gpu" ]; then "$VP" -m pip install -r requirements-gpu.txt -q; fi
echo "[setup] complete. Run ./scripts/precompute.sh, then cd frontend && npm install && npm run build"
