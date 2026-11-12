#!/bin/sh
set -eu
[ "$#" -ge 1 ] || { printf '%s\n' '{"status":"rejected","reason":"path_contract"}'; exit 3; }
python_path=$1
shift
case "$python_path" in /*) ;; *) printf '%s\n' '{"status":"rejected","reason":"path_contract"}'; exit 3 ;; esac
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$python_path" -B "$script_dir/process_waveform_m08.py" "$@" --python "$python_path"
