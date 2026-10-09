#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
python_bin="${M12_PYTHON:-$root/.venv-pipeline/bin/python}"
if [[ ! -x "$python_bin" ]]; then
  python_bin="$root/.venv-m12/bin/python"
fi
if [[ ! -x "$python_bin" ]]; then
  echo "Create an ignored local Python environment with NumPy, SciPy and PyTorch, or set M12_PYTHON." >&2
  exit 2
fi
device="${1:-cpu}"
shift || true
if [[ "$device" != cpu && "$device" != cuda ]]; then
  echo "Device must be cpu or cuda" >&2
  exit 2
fi
"$python_bin" scripts/run_m12_velocity.py --device "$device" "$@"
