#!/usr/bin/env bash
# Server-only operational runner, not a workstation convenience script.
set -Eeuo pipefail
if [[ $# != 1 || ! "$1" =~ ^[a-z0-9][a-z0-9-]{7,63}$ ]]; then
  echo 'Usage: server_mt_admission.sh <immutable-run-id>' >&2
  exit 2
fi
if [[ "$(id -u)" != 0 ]]; then
  echo 'Root operator installs sandbox; scientific work runs as DynamicUser.' >&2
  exit 2
fi
RUN_ID="$1"
REPO="/opt/fasl-admission/geophysics/$RUN_ID"
STATE="geophysics-admission-$RUN_ID"
[[ -d "$REPO/app" && ! -L "$REPO" && -f "$REPO/.venv/bin/python" ]]
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
  --setenv=GEOPHYSICS_RUN_HOST_ADMISSION=1 --setenv=GEOPHYSICS_RUN_LOCAL_MT_BENCHMARK=1 \
  "$REPO/.venv/bin/python" -m pytest -s -q -x -o addopts= -p no:cacheprovider \
  --basetemp="/var/lib/$STATE/measurements" \
  tests/api/test_host_admission.py tests/api/test_online_mt_benchmark.py \
  tests/api/test_online_mt.py::test_preflight_cancel_timeout_and_memory \
  tests/api/test_job_limits.py
