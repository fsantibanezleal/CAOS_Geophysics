#!/usr/bin/env bash
set -euo pipefail
TASK_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_PYTHON="$TASK_REPO/.venv/bin/python"
if [[ ! -x "$TASK_PYTHON" ]]; then
  echo 'Create the pinned repository runtime .venv first.' >&2
  exit 2
fi
exec "$TASK_PYTHON" "$TASK_REPO/scripts/provision_account.py" "$@"
