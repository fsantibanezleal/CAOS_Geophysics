"""Actual private normal-server root intake; not a scientific execution gate.

Uses a copied, source-pinned original and existing copied fixture owner only.
No account creation, public flag, live bootstrap or parent qualification reuse.
"""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper

from app.config import Settings
from app.physical_assembly import PhysicalAssembly
from app.physical_bootstrap import initialize_private_locks
from app.physical_contract import byte_sha
from app.physical_leases import WriterLeases
from app.physical_participation import WorkerExclusion
from app.server import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--policy', required=True)
    args = parser.parse_args()
    private, database = args.root/'private', args.root/'fixture.sqlite'
    assert os.name == 'posix' and os.geteuid() == 61901 and args.root.is_absolute()
    os.umask(0o077)
    password = 'copied-fixture-root-qualification-password'
    with closing(sqlite3.connect(database)) as connection:
        actual = connection.execute('SELECT sqlite_version(),sqlite_source_id()').fetchone()
        assert actual == ('3.51.3', '2026-03-13 10:38:09 737ae4a34738ffa0c3ff7f9bb18df914dd1cad163f28fd6b6e114a344fe6d618')
        owner, email = connection.execute('SELECT id,email FROM user ORDER BY id LIMIT 1').fetchone()
        key, raw_sha, raw_bytes, provider, rights, attribution = connection.execute(
            "SELECT r.storage_key,r.sha256,r.byte_count,s.provider,s.rights_statement,s.attribution "
            "FROM raw_assets r JOIN source_records s ON s.id=r.source_id "
            "WHERE r.owner_id=? AND r.detected_format='gravity_stations_json' ORDER BY r.id LIMIT 1",
            (owner,)).fetchone()
        manifests = {h: json.loads(body) for h, body in connection.execute(
            'SELECT module_manifest_sha256,module_manifest_bytes FROM physical_job_controls')}
        connection.execute('UPDATE user SET hashed_password=? WHERE id=?',
            (PasswordHelper().hash(password), owner))
        connection.commit()
    original = (private/key).read_bytes()
    assert byte_sha(original) == raw_sha and len(original) == raw_bytes
    before = {p.relative_to(private).as_posix(): byte_sha(p.read_bytes())
        for p in private.rglob('*') if p.is_file()}
    initialized = initialize_private_locks(private)
    leases = WriterLeases(private, **initialized['.physical-writers.lock'])
    worker = WorkerExclusion(leases, **initialized['.processing-worker.lock'])
    metadata = {name: dict(cap=1, bytes=1, sha256=byte_sha(marker), required=True)
        for name, marker in (('.physical-writers.lock', b'\0'), ('.processing-worker.lock', b'0'))}
    physical = PhysicalAssembly(leases, worker, source_policy_sha256=args.policy,
        approved_manifests=manifests, approved_installations={}, native_metadata=metadata)
    settings = Settings(data_dir=private, db_path=database,
        auth_secret='actual-private-root-qualification-no-live-secret-123456',
        public_origin='http://testserver', cookie_secure=False, auth_mode='local')
    messages = []

    async def mail(*values):
        messages.append(values)

    def login(client):
        headers = {'Origin': 'http://testserver',
            'X-CSRF-Token': client.get('/api/auth/csrf').json()['csrf_token']}
        response = client.post('/api/auth/cookie/login',
            data={'username': email, 'password': password}, headers=headers)
        assert response.status_code == 204, response.text
        return headers

    try:
        with TestClient(create_app(settings, mail, physical=physical)) as client:
            headers = login(client)
            response = client.post('/api/projects', json={'name': 'Private actual root intake'}, headers=headers)
            assert response.status_code == 201, response.text
            project = response.json()['id']
            meta = dict(filename='original.json', mime='application/json', format='gravity_stations_json',
                source=dict(provider=provider, rights_statement=rights, rights_decision='mirror',
                    private_storage_permission='attested', attribution=attribution,
                    expected_bytes=raw_bytes, expected_sha256=raw_sha),
                physical=dict(schema_version='gravity-stations-1'))
            response = client.post(f'/api/projects/{project}/assets', content=original,
                headers={**headers, 'Content-Type': 'application/json', 'X-Asset-Metadata': json.dumps(meta)})
            assert response.status_code == 201, response.text
            asset = response.json()
            assert client.get(asset['download_url']).content == original
            base = f'/api/projects/{project}/datasets'
            response = client.post(base, json={'asset_id': asset['asset_id']}, headers=headers)
            assert response.status_code == 201, response.text
            dataset = response.json()['dataset_id']
            payload = client.get(base+'/'+dataset)
            assert payload.status_code == 200, payload.text
            assert payload.json()['structural_verdict'] == 'structural_only'
            assert client.post(base, json={'asset_id': asset['asset_id']}, headers=headers).status_code == 409
        with TestClient(create_app(settings, mail, physical=physical)) as client:
            login(client)
            assert client.get(base+'/'+dataset).json() == payload.json()
            assert client.get(asset['download_url']).content == original
        assert all(byte_sha((private/name).read_bytes()) == h for name, h in before.items())
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute('PRAGMA integrity_check').fetchone() == ('ok',)
            assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
            state, charge = connection.execute('SELECT state,charged_bytes FROM physical_custody_batches WHERE stage_id=?', (dataset,)).fetchone()
            assert state == 'cleanup_pending'
            dataset_body = private/f'derived/{owner}/{project}/datasets/{dataset}.json'
            assert charge == len(original) + dataset_body.stat().st_size
            assert connection.execute('SELECT count(*) FROM physical_publication_intents').fetchone() == (0,)
        for path in (private/f'.job-staging/{dataset}/input.json', private/f'.job-staging/{dataset}/dataset.json', dataset_body):
            assert path.stat().st_uid == 61901 and path.stat().st_mode & 0o777 == 0o600
        assert not messages
        print(json.dumps(dict(schema='geophysics.private-native-root-http/v1', uid=os.geteuid(),
            sqlite_version=actual[0], sqlite_source_id=actual[1], actual_normal_create_app=True,
            root_dataset_id=dataset, project_id=project, raw_sha256=raw_sha, raw_bytes=raw_bytes,
            retained_stage_charge=charge, actual_posix_exclusive_write_and_install=True,
            exact_originals_preserved=True, duplicate_refused=True, fresh_restart=True,
            mail_messages=0, scientific_execution=False, production_activated=False), sort_keys=True))
    finally:
        leases.close()


if __name__ == '__main__':
    main()
