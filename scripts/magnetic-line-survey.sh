#!/bin/sh
set -eu
: "${GEOPHYSICS_PYTHON:?Provide the existing Python executable explicitly}"
: "${GEOPHYSICS_EXISTING_PACKAGE_ROOT:?Provide the reviewed installed environment}"
survey_script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$GEOPHYSICS_PYTHON" -B -S "$survey_script_dir/../data-pipeline/magnetic_line_survey_cli.py" "$@"
