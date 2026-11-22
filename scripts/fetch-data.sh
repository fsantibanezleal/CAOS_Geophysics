#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python "$ROOT/data-pipeline/acquire.py" --source-id simpeg-gravity
python "$ROOT/data-pipeline/acquire.py" --source-id simpeg-magnetics
echo '[fetch-data] Both reviewed assets are hash-verified under ignored data/downloads/.'
