"""Real owned HTTP/SQL root lifecycle; explicit portable file transport."""

from contextlib import closing
import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
import pytest

from app.server import create_app
from app.physical_contract import byte_sha, canonical
from tests.api.test_physical_assembly import bound_fixture
from tests.api.test_physical_deleted_inventory import case
from tests.api.test_physical_upload import metadata
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


@pytest.fixture
def http_root(root_case, survey, monkeypatch):
    case(root_case)
    settings, physical = bound_fixture(root_case, monkeypatch)
    files = physical.leases.files

    def directory(key, *, exist_ok=False):
        (files.root/key).mkdir(mode=0o700, exist_ok=exist_ok)

    def write(key, body, *, cap):
        assert type(body) is bytes and len(body) <= cap
        with (files.root/key).open('xb') as output:
            output.write(body)

    def install(source, target, **limits):
        write(target, files.read(source, **limits), cap=limits['cap'])

    monkeypatch.setattr(files, 'create_directory', directory, raising=False)
    monkeypatch.setattr(files, 'write_new', write, raising=False)
    monkeypatch.setattr(files, 'install', install, raising=False)
    owner = root_case[2]['owner_id']
    password = 'exact route private fixture password'
    foreign = str(uuid4())
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.execute('UPDATE user SET hashed_password=? WHERE id=?', (PasswordHelper().hash(password), owner))
        connection.execute('INSERT INTO user VALUES(?,?,?,1,0,1)', (foreign, foreign+'@example.org', PasswordHelper().hash(password)))
        connection.commit()
    original = b' \n' + canonical(survey) + b'\n'
    meta = metadata()
    meta['source'].update(expected_bytes=len(original), expected_sha256=byte_sha(original))
    with TestClient(create_app(settings, physical=physical)) as client:
        headers = {'Origin': 'http://testserver', 'X-CSRF-Token': client.get('/api/auth/csrf').json()['csrf_token']}
        login = client.post('/api/auth/cookie/login', data={'username': owner+'@example.org', 'password': password}, headers=headers)
        assert login.status_code == 204
        project = client.post('/api/projects', json={'name': 'Actual physical root'}, headers=headers).json()['id']
        response = client.post(f'/api/projects/{project}/assets', content=original,
            headers={**headers, 'Content-Type': 'application/json', 'X-Asset-Metadata': json.dumps(meta)})
        assert response.status_code == 201, response.text
        yield settings, physical, client, headers, project, response.json(), original, foreign, password


def test_original_dataset_route_root_publication_debt_duplicate_read_restart_and_foreign404(http_root):
    settings, physical, client, headers, project, asset, original, foreign, password = http_root
    owner = client.get('/api/auth/me').json()['id']
    base = f'/api/projects/{project}/datasets'
    created = client.post(base, json={'asset_id': asset['asset_id']}, headers=headers)
    assert created.status_code == 201, created.text
    dataset = created.json()
    assert dataset['modality'] == 'gravity_physical_station'
    assert dataset['qc_verdict'] == 'structural_only_not_scientifically_admitted'
    root = dataset['dataset_id']
    response = client.get(base+'/'+root)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['kind'] == 'root' and payload['parent_dataset_id'] is None
    assert payload['production'] is None and payload['structural_verdict'] == 'structural_only'
    assert payload['source']['rights_decision'] == 'mirror'
    assert client.get(asset['download_url']).content == original
    methods = client.get(base+'/'+root+'/methods')
    assert methods.status_code == 200 and methods.json()['methods'] == []
    assert all(item['lane'] == 'native_context_pending' for item in methods.json()['unavailable'])
    before = {p.relative_to(settings.data_dir).as_posix(): p.read_bytes() for p in settings.data_dir.rglob('*') if p.is_file()}
    duplicate = client.post(base, json={'asset_id': asset['asset_id']}, headers=headers)
    assert duplicate.status_code == 409 and duplicate.json()['code'] == 'dataset_exists'
    assert before == {p.relative_to(settings.data_dir).as_posix(): p.read_bytes() for p in settings.data_dir.rglob('*') if p.is_file()}
    with closing(sqlite3.connect(settings.database_path)) as connection:
        assert connection.execute('SELECT state,published_count,reserved_count FROM physical_dataset_families WHERE root_dataset_id=?', (root,)).fetchone() == ('published', 1, 0)
        state, charge = connection.execute('SELECT state,charged_bytes FROM physical_custody_batches WHERE stage_id=?', (root,)).fetchone()
        assert state == 'cleanup_pending'
        assert charge == len(original) + dataset_body_size(settings, owner, project, root)
        assert connection.execute('SELECT count(*) FROM physical_publication_intents').fetchone() == (0,)
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    client.post('/api/auth/cookie/logout', headers=headers)
    login = client.post('/api/auth/cookie/login', data={'username': foreign+'@example.org', 'password': password}, headers=headers)
    assert login.status_code == 204
    for path in (base, base+'/'+root, base+'/'+root+'/methods', asset['download_url']):
        assert client.get(path).status_code == 404
    assert client.post(base, json={'asset_id': asset['asset_id']}, headers=headers).status_code == 404
    # A second actual app lifespan sees the complete saved forest and debt,
    # not a manufactured token from the original startup observation.
    with TestClient(create_app(settings, physical=physical)) as restarted:
        fresh_headers = {'Origin': 'http://testserver',
            'X-CSRF-Token': restarted.get('/api/auth/csrf').json()['csrf_token']}
        login = restarted.post('/api/auth/cookie/login',
            data={'username': owner+'@example.org', 'password': password}, headers=fresh_headers)
        assert login.status_code == 204
        assert restarted.get(base+'/'+root).json() == payload
        assert restarted.get(asset['download_url']).content == original
    assert (settings.data_dir/f'.job-staging/{root}/input.json').read_bytes() == original


def dataset_body_size(settings, owner, project, root):
    return (settings.data_dir/f'derived/{owner}/{project}/datasets/{root}.json').stat().st_size


def test_failed_stage_write_keeps_committed_capacity_and_exact_original_then_startup_refuses(http_root, monkeypatch):
    settings, physical, client, headers, project, asset, original, _, _ = http_root
    writes = physical.leases.files.write_new
    def cut(key, body, *, cap):
        if key.endswith('/dataset.json'):
            raise OSError('injected stage output failure')
        writes(key, body, cap=cap)
    monkeypatch.setattr(physical.leases.files, 'write_new', cut)
    with pytest.raises(OSError, match='injected stage output failure'):
        client.post(f'/api/projects/{project}/datasets', json={'asset_id': asset['asset_id']}, headers=headers)
    from app.physical_persistence import M
    with closing(sqlite3.connect(settings.database_path)) as connection:
        root, state, charge = connection.execute('SELECT stage_id,state,charged_bytes FROM physical_custody_batches WHERE project_id=?', (project,)).fetchone()
        assert (state, charge) == ('reserved', 32*M)
        assert connection.execute('SELECT count(*) FROM observation_datasets WHERE project_id=?', (project,)).fetchone() == (0,)
    assert (settings.data_dir/f'.job-staging/{root}/input.json').read_bytes() == original
    assert client.get(asset['download_url']).content == original
    with pytest.raises(ValueError, match='physical_startup_recovery_required'):
        with TestClient(create_app(settings, physical=physical)):
            raise AssertionError('Unfinished reservation was silently adopted')
