#!/usr/bin/env bash
# Server-only runner for the authenticated uploaded M02 ordinary-L2 child path.
set -Eeuo pipefail
if [[ $# != 1 || ! "$1" =~ ^[a-z0-9][a-z0-9-]{7,63}$ ]]; then
  echo 'Usage: server_gravity_l2_admission.sh <immutable-run-id>' >&2
  exit 2
fi
if [[ "$(id -u)" != 0 ]]; then
  echo 'Root operator installs sandbox; scientific work runs as DynamicUser.' >&2
  exit 2
fi
RUN_ID="$1"
REPO="/opt/fasl-admission/geophysics/$RUN_ID"
STATE="geophysics-admission-$RUN_ID"
API_PYTHON="$REPO/.venv/bin/python"
GRAVITY_PYTHON="$REPO/.venv-gravity/bin/python"
[[ -d "$REPO/app" && ! -L "$REPO" && -f "$API_PYTHON" && -f "$GRAVITY_PYTHON" ]]
[[ -f "$REPO/admission-source-revision.txt" ]]
systemd-run --unit="$STATE" --wait --pipe \
  --property=DynamicUser=yes --property="StateDirectory=$STATE" \
  --property=StateDirectoryMode=0700 --property="WorkingDirectory=$REPO" \
  --property=ProtectSystem=strict --property=ProtectHome=yes \
  --property=PrivateTmp=yes --property=PrivateDevices=yes --property=PrivateNetwork=yes \
  --property=NoNewPrivileges=yes --property=RestrictSUIDSGID=yes \
  --property=ProtectKernelTunables=yes --property=ProtectKernelModules=yes \
  --property=ProtectControlGroups=yes --property=RestrictRealtime=yes \
  --property=CapabilityBoundingSet= --property=TasksMax=96 \
  --property=MemoryHigh=1536M --property=MemoryMax=2G --property=MemorySwapMax=0 \
  --property=CPUQuota=200% --property=RuntimeMaxSec=1800 --property=UMask=0077 \
  --setenv=PYTHONDONTWRITEBYTECODE=1 --setenv=PYTHONIOENCODING=utf-8 \
  --setenv=OMP_NUM_THREADS=1 --setenv=OPENBLAS_NUM_THREADS=1 \
  --setenv=MKL_NUM_THREADS=1 --setenv=NUMEXPR_NUM_THREADS=1 \
  --setenv=GEOPHYSICS_TEST_GRAVITY_PYTHON="$GRAVITY_PYTHON" \
  "$API_PYTHON" -m pytest -s -q -x -o addopts= -p no:cacheprovider \
  --basetemp="/var/lib/$STATE/measurements" \
  tests/api/test_gravity_l2_upload.py::test_uploaded_user_survey_runs_isolated_inverse_and_parameter_changes_predictions
