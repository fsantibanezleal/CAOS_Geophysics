#!/bin/sh
# Explicit pre-existing pinned interpreter; no installation or environment fallback.
set -eu
if [ "$#" -lt 2 ] || [ "$1" != "--python" ]; then
    printf '%s\n' 'Supply --python EXISTING_PINNED_INTERPRETER followed by run/validate/replay and CLI flags.' >&2
    exit 2
fi
pipeline_python=$2
shift 2
if [ ! -f "$pipeline_python" ]; then
    printf '%s\n' 'An existing pinned Python interpreter is required.' >&2
    exit 2
fi
pipeline_directory=$(CDPATH= cd -- "$(dirname -- "$0")/../data-pipeline" && pwd)
exec "$pipeline_python" "$pipeline_directory/magnetic_lines.py" "$@"
