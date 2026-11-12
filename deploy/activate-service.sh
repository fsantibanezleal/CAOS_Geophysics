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
gravity_python="$release/.venv-gravity/bin/python"
[[ "$admission" == /* && -f "$admission" && ! -L "$admission" ]]
[[ -d "$release" && ! -L "$release" && -x "$python" && -x "$gravity_python" ]]
[[ $(realpath -e "$release") == "$release" ]]
[[ -d /var/lib/geophysics && ! -L /var/lib/geophysics ]]
[[ $(stat -c '%U:%a' /var/lib/geophysics) == geophysics:700 ]]
getent passwd geophysics >/dev/null
[[ -f /etc/geophysics/api.env && -f /etc/geophysics/worker.env ]]
for env_file in /etc/geophysics/api.env /etc/geophysics/worker.env; do
  [[ ! -L "$env_file" && $(stat -c '%U:%a' "$env_file") == root:600 ]]
done
candidate_env_dir="/etc/geophysics/releases/$release_id"
[[ -d "$candidate_env_dir" && ! -L "$candidate_env_dir" ]]
[[ $(stat -c '%U:%a' "$candidate_env_dir") == root:700 ]]
for env_file in "$candidate_env_dir/api.env" "$candidate_env_dir/worker.env"; do
  [[ -f "$env_file" && ! -L "$env_file" && $(stat -c '%U:%a' "$env_file") == root:600 ]]
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
"$python" -B - "$release" "$admission" "$previous" <<'PY'
import hashlib, json, os, pathlib, re, stat, sys
sys.path.insert(0, str(pathlib.Path.cwd() / 'scripts'))
from prepare_service_release import verify_bundle, require_pre_cutover, strict_json
from check_sdd_convergence import validate
from verify_single_vps_release import validate_capacity
bundle = pathlib.Path(sys.argv[1])
previous = pathlib.Path(sys.argv[3])
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
envs = {}
for name in ('api', 'worker'):
    file = pathlib.Path('/etc/geophysics/releases') / bundle.name / (name + '.env')
    with file.open('rb') as handle:
        raw = handle.read(8193)
    if len(raw) > 8192:
        raise ValueError('service environment exceeds bound')
    values = {}
    for line in raw.decode('ascii').splitlines():
        if not line or line.startswith('#'):
            continue
        if not re.fullmatch(r'GEOPHYSICS_[A-Z0-9_]+=[A-Za-z0-9_./:-]+', line):
            raise ValueError('service environment must use simple literal values')
        key, value = line.split('=', 1)
        if key in values:
            raise ValueError('duplicate service environment key')
        values[key] = value
    common = {'GEOPHYSICS_DATA_DIR', 'GEOPHYSICS_DB_PATH', 'GEOPHYSICS_MT_ONLINE_ENABLED',
              'GEOPHYSICS_GRAVITY_L2_ONLINE_ENABLED', 'GEOPHYSICS_GRAVITY_L2_PYTHON',
              'GEOPHYSICS_PHYSICAL_BINDING_PATH', 'GEOPHYSICS_PHYSICAL_BINDING_SHA256'}
    if name == 'worker' and not set(values) <= common:
        raise ValueError('worker environment is not storage-only')
    if name == 'api' and not set(values) <= (common | {'GEOPHYSICS_PUBLIC_ORIGIN',
            'GEOPHYSICS_AUTH_MODE', 'GEOPHYSICS_AUTH_SECRET'}):
        raise ValueError('API environment contains an unreviewed key')
    if values.get('GEOPHYSICS_DATA_DIR') != '/var/lib/geophysics':
        raise ValueError('private state path differs from service sandbox')
    if values.get('GEOPHYSICS_DB_PATH', '/var/lib/geophysics/api.sqlite3') != '/var/lib/geophysics/api.sqlite3':
        raise ValueError('private database path differs from reviewed schema')
    if name == 'api' and (values.get('GEOPHYSICS_PUBLIC_ORIGIN') != 'https://geophysics.ml.fasl-work.com'
                          or values.get('GEOPHYSICS_AUTH_MODE') != 'local'):
        raise ValueError('API origin/local account profile differs')
    envs[name] = values
    environment_hashes = globals().setdefault('environment_hashes', {})
    environment_hashes[name + '.env'] = hashlib.sha256(raw).hexdigest()
if admission.get('service_environment_hashes') != environment_hashes:
    raise ValueError('host admission does not bind candidate release environment hashes')
active_dir = pathlib.Path('/etc/geophysics/releases') / previous.name
active_info = active_dir.stat(follow_symlinks=False)
if (not stat.S_ISDIR(active_info.st_mode) or active_info.st_uid != 0
        or stat.S_IMODE(active_info.st_mode) != 0o700):
    raise ValueError('active release environment directory ownership or mode differs')
for name in ('api.env', 'worker.env'):
    if not active_dir.is_dir() or active_dir.is_symlink():
        raise ValueError('active release environment selection is missing')
    selected = active_dir / name
    global_file = pathlib.Path('/etc/geophysics') / name
    if hashlib.sha256(selected.read_bytes()).hexdigest() != hashlib.sha256(global_file.read_bytes()).hexdigest():
        raise ValueError('global environment is not the active release selection')
api_binding = tuple(envs['api'].get(k) for k in (
    'GEOPHYSICS_PHYSICAL_BINDING_PATH', 'GEOPHYSICS_PHYSICAL_BINDING_SHA256'))
worker_binding = tuple(envs['worker'].get(k) for k in (
    'GEOPHYSICS_PHYSICAL_BINDING_PATH', 'GEOPHYSICS_PHYSICAL_BINDING_SHA256'))
if api_binding != worker_binding or (bool(api_binding[0]) != bool(api_binding[1])):
    raise ValueError('physical binding must be identical and complete in API and worker envs')
if api_binding[0]:
    registry_path = pathlib.Path(api_binding[0])
    expected_path = pathlib.Path('/var/lib/geophysics/physical-operator-bindings') / (bundle.name + '.json')
    if registry_path != expected_path or not re.fullmatch(r'[0-9a-f]{64}', api_binding[1]):
        raise ValueError('physical binding path or digest is not canonical')
    root_info = pathlib.Path('/var/lib/geophysics').stat()
    import pwd, grp
    service_uid, service_gid = pwd.getpwnam('geophysics').pw_uid, grp.getgrnam('geophysics').gr_gid
    if (root_info.st_uid, root_info.st_gid, stat.S_IMODE(root_info.st_mode)) != (service_uid, service_gid, 0o700):
        raise ValueError('physical registry root owner or mode differs')
    binding_dir = registry_path.parent
    binding_dir_info = binding_dir.stat(follow_symlinks=False)
    if (binding_dir.is_symlink() or not stat.S_ISDIR(binding_dir_info.st_mode)
            or binding_dir_info.st_uid != service_uid or stat.S_IMODE(binding_dir_info.st_mode) != 0o700):
        raise ValueError('physical registry directory ownership or mode differs')
    if registry_path.is_symlink():
        raise ValueError('physical registry cannot be a symlink')
    registry_stat = registry_path.stat(follow_symlinks=False)
    if (not stat.S_ISREG(registry_stat.st_mode) or registry_stat.st_uid != service_uid
            or registry_stat.st_nlink != 1 or stat.S_IMODE(registry_stat.st_mode) != 0o600):
        raise ValueError('physical registry ownership or mode differs')
    registry_raw = registry_path.read_bytes()
    if hashlib.sha256(registry_raw).hexdigest() != api_binding[1]:
        raise ValueError('physical registry hash differs')
    sys.path.insert(0, str(pathlib.Path.cwd()))
    from app.operator_runtime import _check_registry, _strict_json
    registry = _strict_json(registry_raw, cap=4 * 1024 * 1024, code='operator_registry')
    _check_registry(registry, (bundle / 'release.json').read_bytes())
    if registry.get('release_manifest_sha256') != digest:
        raise ValueError('physical registry does not bind exact candidate release.json')
    for lock_name, marker in (('.physical-writers.lock', b'\0'), ('.processing-worker.lock', b'0')):
        lock_path = pathlib.Path('/var/lib/geophysics') / lock_name
        if lock_path.is_symlink():
            raise ValueError('physical lock cannot be a symlink')
        info = lock_path.stat(follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != service_uid or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != 0o600 or lock_path.read_bytes() != marker):
            raise ValueError('physical lock ownership, mode or marker differs')
        if hashlib.sha256(lock_path.read_bytes()).hexdigest() != hashlib.sha256(marker).hexdigest():
            raise ValueError('physical lock hash differs')
PY
"$python" -B -m pip check
# The only admitted existing schemas are the exact pre-waveform and candidate heads.
# The fixed DDL digests bind the additive upgrade; arbitrary same-version schemas refuse.
"$python" -B - <<'PY'
import hashlib, json, pathlib, sqlite3
path = pathlib.Path('/var/lib/geophysics/api.sqlite3')
if path.is_symlink() or not path.is_file():
    raise ValueError('provision the exact migration and internal accounts before activation')
known = {
    '0003_processing_jobs': '33a96998cd77c595a0d983461f84e1367a813e460b9c13222d07490fd9b86709',
    '0004_waveform_artifacts': 'f2a1a28305e8115d42549bc64508afe8de76f42b8b2e32b516ff753f6f45851f',
}
with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as connection:
    connection.execute('PRAGMA query_only=ON')
    head = connection.execute('SELECT version_num FROM alembic_version').fetchall()
    ddl = [tuple(row) for row in connection.execute(
        'SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name')]
    integrity = connection.execute('PRAGMA integrity_check').fetchall()
    foreign_keys = connection.execute('PRAGMA foreign_key_check').fetchall()
if len(head) != 1 or head[0][0] not in known:
    raise ValueError('database schema revision is not an admitted migration state')
schema = hashlib.sha256(json.dumps(ddl, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
if schema != known[head[0][0]] or integrity != [('ok',)] or foreign_keys:
    raise ValueError('database schema or integrity differs from the reviewed migration')
PY
database_head=$("$python" -B - <<'PY'
import sqlite3
with sqlite3.connect('file:/var/lib/geophysics/api.sqlite3?mode=ro', uri=True) as connection:
    print(connection.execute('SELECT version_num FROM alembic_version').fetchone()[0])
PY
)
if [[ "$database_head" == 0003_processing_jobs ]]; then
  for unit in geophysics-api.socket geophysics-api.service geophysics-worker.service; do
    if systemctl is-active --quiet "$unit"; then
      echo '0003-to-0004 migration requires all existing service writers to be inactive' >&2
      exit 1
    fi
  done
fi
[[ ! -e "$state" && ! -L "$state" ]]
install -d -m 0700 /var/lib/geophysics-deploy
mkdir -m 0700 "$state"
cp -- "$site" "$state/previous.nginx"
printf '%s\n' "$previous" > "$state/previous-release"
install -m 0600 /etc/geophysics/api.env "$state/previous.api.env"
install -m 0600 /etc/geophysics/worker.env "$state/previous.worker.env"
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
environment_switched=false
rollback_env_restored=true
rollback_schema_verified=true
systemctl is-active --quiet geophysics-api.service && api_active=true
systemctl is-active --quiet geophysics-worker.service && worker_active=true
systemctl is-active --quiet geophysics-api.socket && socket_active=true
stop_if_present() {
  if [[ $(systemctl show --property=LoadState --value "$1") != not-found ]]; then
    systemctl stop "$1"
  fi
}
recover_migration_observation() {
  [[ -f "$state/schema-migration-attempted.json" && ! -e "$state/schema-migration.json" \
      && ! -e "$state/schema-migration-recovery.json" ]] || return 0
  local verification observation
  if ! verification=$(runuser -u geophysics -- env \
      GEOPHYSICS_DATA_DIR=/var/lib/geophysics \
      GEOPHYSICS_DB_PATH=/var/lib/geophysics/api.sqlite3 \
      PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
      "$python" -I -B "$release/source/scripts/migrate_service_schema.py" --verify-only); then
    echo 'Migration completion receipt is absent and read-only recovery verification failed; inspect the retained attempt marker and database revision.' >&2
    return 1
  fi
  observation=$("$python" -B - "$verification" "$state/schema-migration-attempted.json" <<'PY'
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd() / 'scripts'))
from migrate_service_schema import recovery_observation
verified = json.loads(sys.argv[1])
attempt = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='ascii'))
print(json.dumps(recovery_observation(attempt, verified), sort_keys=True, separators=(',', ':')))
PY
  ) || return 1
  printf '%s\n' "$observation" > "$state/schema-migration-recovery.json.tmp" \
    && mv -T -- "$state/schema-migration-recovery.json.tmp" "$state/schema-migration-recovery.json" \
    || return 1
  echo 'The forward schema head was verified read-only and its recovery observation was retained.' >&2
}
rollback() {
  trap - ERR INT TERM
  set +e
  echo 'Activation failed; restoring previous release and retaining evidence.' >&2
  stop_if_present geophysics-api.service
  stop_if_present geophysics-api.socket
  [[ "$worker_stopped" == false ]] || stop_if_present geophysics-worker.service
  if ! recover_migration_observation; then rollback_schema_verified=false; fi
  if [[ "$environment_switched" == true ]]; then
    install -o root -g root -m 0600 "$state/previous.api.env" /etc/geophysics/api.env || rollback_env_restored=false
    install -o root -g root -m 0600 "$state/previous.worker.env" /etc/geophysics/worker.env || rollback_env_restored=false
  fi
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
  if [[ "$rollback_env_restored" == true && "$rollback_schema_verified" == true ]]; then
    [[ "$socket_active" == false ]] || systemctl start geophysics-api.socket
    [[ "$api_active" == false ]] || systemctl start geophysics-api.service
  else
    echo 'Prior environment or database schema could not be verified; prior services remain stopped.' >&2
  fi
  if [[ "$rollback_env_restored" == true && "$rollback_schema_verified" == true \
      && "$worker_active" == true && "$worker_stopped" == true ]]; then
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
# Keep the old release selected while the exact additive migration runs. The migration is
# forward-only; a failed activation retains its receipt and never deletes user data or downgrades.
printf '{"schema":"geophysics.service-schema-migration-attempt/v1","status":"attempted","preflight_revision":"%s","to":"0004_waveform_artifacts"}\n' \
  "$database_head" > "$state/schema-migration-attempted.json"
migration_receipt=$(runuser -u geophysics -- env \
  GEOPHYSICS_DATA_DIR=/var/lib/geophysics \
  GEOPHYSICS_DB_PATH=/var/lib/geophysics/api.sqlite3 \
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
  "$python" -I -B "$release/source/scripts/migrate_service_schema.py")
[[ ${#migration_receipt} -le 8192 ]]
"$python" -B - "$migration_receipt" <<'PY'
import json, sys
receipt = json.loads(sys.argv[1])
if (receipt.get('schema') != 'geophysics.service-schema-migration/v1'
        or receipt.get('to') != '0004_waveform_artifacts'
        or receipt.get('migration_sha256') != 'c08dde26f55aea87af39e9228013f23a6823de1cf54ba9163d164b0ebfb49bc0'):
    raise ValueError('candidate migration receipt is incomplete')
PY
printf '%s\n' "$migration_receipt" > "$state/schema-migration.json.tmp"
mv -T -- "$state/schema-migration.json.tmp" "$state/schema-migration.json"
environment_switched=true
install -o root -g root -m 0600 "$candidate_env_dir/api.env" /etc/geophysics/api.env
install -o root -g root -m 0600 "$candidate_env_dir/worker.env" /etc/geophysics/worker.env
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
