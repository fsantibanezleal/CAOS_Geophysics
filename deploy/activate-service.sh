#!/usr/bin/env bash
# Qualified single-site cutover. Not a builder, trainer or final acceptance claim.
set -Eeuo pipefail
umask 077
if [[ $# != 2 || ! "$1" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$ ]]; then
  echo 'Usage: activate-service.sh <release-id> <absolute reviewed host-admission receipt>' >&2
  exit 2
fi
[[ $(id -u) == 0 ]]
release_id="$1"
admission="$2"
root=/var/www/geophysics.ml.fasl-work.com
release="$root/releases/$release_id"
site=/etc/nginx/sites-available/geophysics.ml.fasl-work.com
state="/var/lib/geophysics-deploy/$release_id"
python="$release/.venv/bin/python"
[[ "$admission" == /* && -f "$admission" && ! -L "$admission" ]]
[[ -d "$release" && ! -L "$release" && -x "$python" ]]
[[ $(realpath -e "$release") == "$release" ]]
[[ -d /var/lib/geophysics && ! -L /var/lib/geophysics ]]
[[ $(stat -c '%U:%a' /var/lib/geophysics) == geophysics:700 ]]
getent passwd geophysics >/dev/null
[[ -f /etc/geophysics/api.env && -f /etc/geophysics/worker.env ]]
for env_file in /etc/geophysics/api.env /etc/geophysics/worker.env; do
  [[ ! -L "$env_file" && $(stat -c '%U:%a' "$env_file") == root:600 ]]
done
[[ ! -L /etc/geophysics && ! -L /var/lib/geophysics-deploy ]]
[[ -f /etc/letsencrypt/live/geophysics.ml.fasl-work.com/fullchain.pem ]]
[[ -f /etc/letsencrypt/live/geophysics.ml.fasl-work.com/privkey.pem ]]
[[ -f "$site" && ! -L "$site" ]]
[[ -L "$root/current" ]]
previous=$(realpath -e "$root/current")
[[ "$previous" == "$root/releases/"* && "$previous" != "$release" ]]
[[ $(dirname "$previous") == "$root/releases" ]]
[[ ! -L "$previous" && -d "$previous" ]]
exec 9>/run/lock/geophysics-deploy.lock
flock -n 9
cd "$release/source"
# Verify exact bytes and all non-deployment scientific/UI receipts BEFORE stopping writes.
"$python" -B - "$release" "$admission" <<'PY'
import hashlib, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd() / 'scripts'))
from prepare_service_release import verify_bundle, require_pre_cutover, strict_json
from check_sdd_convergence import validate
from verify_single_vps_release import validate_capacity
bundle = pathlib.Path(sys.argv[1])
manifest = verify_bundle(bundle)
ledger = strict_json((pathlib.Path.cwd() / 'docs/design/convergence.json').read_bytes())
validate(pathlib.Path.cwd(), ledger)
require_pre_cutover(ledger)
with pathlib.Path(sys.argv[2]).open('rb') as handle:
    admission = strict_json(handle.read(4 * 1024 * 1024 + 1))
if admission.get('schema') != 'geophysics.service-host-admission/v1':
    raise ValueError('wrong actual-host admission schema')
if admission.get('source_revision') != manifest['source_revision']:
    raise ValueError('host admission source revision changed')
digest = hashlib.sha256((bundle / 'release.json').read_bytes()).hexdigest()
if admission.get('bundle_sha256') != digest:
    raise ValueError('host admission bundle identity changed')
required = {'nominal', 'upper', 'malformed', 'cancel', 'crash', 'ownership', 'public_read'}
checks = admission.get('checks', [])
if len(checks) != len(required) or {c.get('name') for c in checks} != required:
    raise ValueError('actual-host admission coverage incomplete')
for check in checks:
    if check.get('verdict') != 'pass':
        raise ValueError('actual-host admission failed')
    path = pathlib.Path(check['evidence_path'])
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('host evidence path invalid')
    sha = hashlib.sha256()
    with path.open('rb') as handle:
        while block := handle.read(65536):
            sha.update(block)
    if sha.hexdigest() != check['evidence_sha256']:
        raise ValueError('host evidence hash changed')
validate_capacity(admission['capacity'])
# The service environment has deliberately simple literal entries, never shell code.
import re
for name in ('api', 'worker'):
    file = pathlib.Path('/etc/geophysics') / (name + '.env')
    with file.open('rb') as handle:
        raw = handle.read(8193)
    if len(raw) > 8192:
        raise ValueError('service environment exceeds bound')
    values = {}
    for line in raw.decode('ascii').splitlines():
        if not line or line.startswith('#'):
            continue
        if not re.fullmatch(r'GEOPHYSICS_[A-Z_]+=[A-Za-z0-9_./:-]+', line):
            raise ValueError('service environment must use simple literal values')
        key, value = line.split('=', 1)
        if key in values:
            raise ValueError('duplicate service environment key')
        values[key] = value
    common = {'GEOPHYSICS_DATA_DIR', 'GEOPHYSICS_DB_PATH', 'GEOPHYSICS_MT_ONLINE_ENABLED'}
    if name == 'worker' and not set(values) <= common:
        raise ValueError('worker environment is not storage-only')
    if values.get('GEOPHYSICS_DATA_DIR') != '/var/lib/geophysics':
        raise ValueError('private state path differs from service sandbox')
    if values.get('GEOPHYSICS_DB_PATH', '/var/lib/geophysics/api.sqlite3') != '/var/lib/geophysics/api.sqlite3':
        raise ValueError('private database path differs from reviewed schema')
    if name == 'api' and (values.get('GEOPHYSICS_PUBLIC_ORIGIN') != 'https://geophysics.ml.fasl-work.com'
                          or values.get('GEOPHYSICS_AUTH_MODE') != 'local'):
        raise ValueError('API origin/local account profile differs')
PY
"$python" -B -m pip check
# Existing database must match the reviewed compatible schema. No automatic downgrade/replacement.
"$python" -B - <<'PY'
import pathlib, sqlite3
path = pathlib.Path('/var/lib/geophysics/api.sqlite3')
if path.is_symlink() or not path.is_file():
    raise ValueError('provision the exact migration and internal accounts before activation')
with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as connection:
    head = connection.execute('SELECT version_num FROM alembic_version').fetchall()
if head != [('0003_processing_jobs',)]:
    raise ValueError('database schema incompatible; explicit migration review required')
PY
[[ ! -e "$state" && ! -L "$state" ]]
install -d -m 0700 /var/lib/geophysics-deploy
mkdir -m 0700 "$state"
cp -- "$site" "$state/previous.nginx"
printf '%s\n' "$previous" > "$state/previous-release"
for unit in geophysics-api.socket geophysics-api.service geophysics-worker.service; do
  if [[ -e "/etc/systemd/system/$unit" ]]; then
    [[ -f "/etc/systemd/system/$unit" && ! -L "/etc/systemd/system/$unit" ]]
    cp -- "/etc/systemd/system/$unit" "$state/$unit"
  fi
done
api_active=false
worker_active=false
socket_active=false
worker_stopped=false
systemctl is-active --quiet geophysics-api.service && api_active=true
systemctl is-active --quiet geophysics-worker.service && worker_active=true
systemctl is-active --quiet geophysics-api.socket && socket_active=true
stop_if_present() {
  if [[ $(systemctl show --property=LoadState --value "$1") != not-found ]]; then
    systemctl stop "$1"
  fi
}
rollback() {
  trap - ERR INT TERM
  set +e
  echo 'Activation failed; restoring previous release and retaining evidence.' >&2
  stop_if_present geophysics-api.service
  stop_if_present geophysics-api.socket
  [[ "$worker_stopped" == false ]] || stop_if_present geophysics-worker.service
  ln -s -- "$previous" "$root/rollback-$release_id"
  mv -T -- "$root/rollback-$release_id" "$root/current"
  install -m 0644 "$state/previous.nginx" "$site"
  for unit in geophysics-api.socket geophysics-api.service geophysics-worker.service; do
    if [[ -f "$state/$unit" ]]; then
      install -m 0644 "$state/$unit" "/etc/systemd/system/$unit"
    else
      unlink -- "/etc/systemd/system/$unit"
    fi
  done
  systemctl daemon-reload
  [[ "$socket_active" == false ]] || systemctl start geophysics-api.socket
  [[ "$api_active" == false ]] || systemctl start geophysics-api.service
  if [[ "$worker_active" == true && "$worker_stopped" == true ]]; then
    systemctl start geophysics-worker.service
  fi
  nginx -t && systemctl reload nginx
  echo 'Rollback attempted; verify actual service/site state. No acceptance claimed.' >&2
  exit 1
}
trap rollback ERR
trap 'rollback' INT TERM
stop_if_present geophysics-api.service
stop_if_present geophysics-api.socket
# Freeze new writes, then refuse a busy queue without killing a running calculation.
"$python" -B - <<'PY'
import sqlite3
with sqlite3.connect('file:/var/lib/geophysics/api.sqlite3?mode=ro', uri=True) as connection:
    count = connection.execute("SELECT COUNT(*) FROM processing_jobs WHERE state IN ('queued','running')").fetchone()[0]
if count:
    raise ValueError('processing queue is busy; old worker continues, cutover refused')
PY
worker_stopped=true
stop_if_present geophysics-worker.service
ln -s -- "$release" "$root/activate-$release_id"
mv -T -- "$root/activate-$release_id" "$root/current"
for unit in geophysics-api.socket geophysics-api.service geophysics-worker.service; do
  install -m 0644 "$release/source/deploy/service/$unit" "/etc/systemd/system/$unit"
done
install -m 0644 "$release/source/deploy/service/geophysics.nginx" "$site"
systemd-analyze verify /etc/systemd/system/geophysics-api.socket /etc/systemd/system/geophysics-api.service /etc/systemd/system/geophysics-worker.service
nginx -t
systemctl daemon-reload
systemctl start geophysics-api.socket geophysics-api.service
"$python" -B scripts/verify_local_service.py --socket /run/geophysics-api/api.sock
systemctl start geophysics-worker.service
systemctl is-active --quiet geophysics-worker.service
systemctl reload nginx
trap - ERR INT TERM
printf 'Qualified activation=%s; final HTTPS/browser/rollback acceptance still required.\n' "$release_id"
