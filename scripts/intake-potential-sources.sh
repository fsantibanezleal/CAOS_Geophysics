#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTAKE_PYTHON="${GEOPHYSICS_INTAKE_PYTHON:-$ROOT/.venv-intake/bin/python}"
ARCHIVE=''
OUTPUT=''
while (($#)); do
    case "$1" in
        --file|--output|--python)
            if (($# < 2)); then echo "Missing value for $1" >&2; exit 2; fi
            case "$1" in
                --file) ARCHIVE="$2" ;;
                --output) OUTPUT="$2" ;;
                --python) INTAKE_PYTHON="$2" ;;
            esac
            shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done
if [[ -z "$ARCHIVE" || -z "$OUTPUT" || ! -f "$INTAKE_PYTHON" ]]; then
    echo 'Use --file <pinned ZIP> --output <new data/raw JSON> and an isolated --python or GEOPHYSICS_INTAKE_PYTHON; see guide 11.' >&2
    exit 2
fi
"$INTAKE_PYTHON" -c 'import sys; raise SystemExit(0 if sys.prefix != sys.base_prefix else 2)'
cd "$ROOT"
"$INTAKE_PYTHON" "$ROOT/data-pipeline/potential_sources.py" --file "$ARCHIVE" --output "$OUTPUT"
echo '[potential-intake] Local inspection only; unresolved modelling gates remain open.'
