"""Actual original-route upload and zero-science strict physical metadata."""

import json

import pytest

from app.errors import ApiError
from app.physical_upload import parse_physical_upload_header, validate_physical_upload
from app.physical_contract import canonical
from app.projects import _parse_upload_header
from tests.api.test_physical_wire import survey as survey
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor


def metadata():
    return dict(filename='original.json', mime='application/json', format='gravity_stations_json',
        source=dict(provider='Authored independent control', rights_statement='Permission to store privately only',
                    rights_decision='mirror', private_storage_permission='attested', attribution='Control author'),
        physical=dict(schema_version='gravity-stations-1'))


def test_physical_mode_is_explicit_without_fabricated_epoch_frame_or_csv_metadata(tmp_path, survey):
    value = metadata()
    parsed = parse_physical_upload_header(json.dumps(value))
    assert parsed.physical.model_dump() == {'schema_version': 'gravity-stations-1'}
    assert parsed.model_dump(exclude_none=True)['physical'] == value['physical']
    raw = b' \n' + canonical(survey) + b'\n'
    path = tmp_path / 'original.json'
    path.write_bytes(raw)
    validate_physical_upload(path, parsed)
    assert path.read_bytes() == raw
    with pytest.raises(ApiError) as refused:
        _parse_upload_header(json.dumps(value))
    assert refused.value.code == 'physical_admission_closed' and refused.value.status == 409


@pytest.mark.parametrize('damage', ['duplicate', 'escape-duplicate', 'fraction-count', 'bool-count',
    'nan', 'epoch', 'unknown-schema', 'unknown-key', 'basename', 'wrong-mime'])
def test_physical_metadata_rejects_before_coercion_without_scientific_import(damage):
    value = metadata()
    if damage == 'fraction-count': value['source']['expected_bytes'] = 1.0
    elif damage == 'bool-count': value['source']['expected_bytes'] = True
    elif damage == 'nan': value['source']['expected_bytes'] = float('nan')
    elif damage == 'epoch': value['physical']['epoch_utc'] = 'invented'
    elif damage == 'unknown-schema': value['physical']['schema_version'] = 'gravity-stations-2'
    elif damage == 'unknown-key': value['other'] = True
    elif damage == 'basename': value['filename'] = '../original.json'
    elif damage == 'wrong-mime': value['mime'] = 'text/csv'
    raw = json.dumps(value)
    if damage == 'duplicate': raw = raw.replace('"format":', '"format":"gravity_stations_json","format":', 1)
    if damage == 'escape-duplicate': raw = raw.replace('"format":', '"f\\u006frmat":"gravity_stations_json","format":', 1)
    with pytest.raises(ValueError):
        parse_physical_upload_header(raw)


def test_raw_original_structural_parser_refuses_csv_and_keeps_source(tmp_path):
    original = b'station,x,y,z,g\nS1,0,0,1,9.8\n'
    path = tmp_path / 'original.json'
    path.write_bytes(original)
    with pytest.raises(ApiError) as refused:
        validate_physical_upload(path, parse_physical_upload_header(json.dumps(metadata())))
    assert refused.value.code == 'physical_contract_invalid' and refused.value.status == 422
    assert path.read_bytes() == original


def test_original_asset_route_stores_exact_json_with_real_local_owner_and_custody_accounting(root_case, survey, monkeypatch):
    from contextlib import closing
    import sqlite3
    from fastapi.testclient import TestClient
    from fastapi_users.password import PasswordHelper
    from app.server import create_app
    from tests.api.test_physical_assembly import bound_fixture
    from tests.api.test_physical_deleted_inventory import case
    from app.physical_contract import byte_sha

    case(root_case)
    settings, physical = bound_fixture(root_case, monkeypatch)
    password = 'original private test password'
    owner = root_case[2]['owner_id']
    with closing(sqlite3.connect(settings.database_path)) as connection:
        connection.execute('UPDATE user SET hashed_password=? WHERE id=?', (PasswordHelper().hash(password), owner))
        connection.commit()
    original = b' \n' + canonical(survey) + b'\n'
    meta = metadata()
    meta['source'].update(expected_bytes=len(original), expected_sha256=byte_sha(original))
    with TestClient(create_app(settings, physical=physical)) as client:
        token = client.get('/api/auth/csrf').json()['csrf_token']
        headers = {'Origin': 'http://testserver', 'X-CSRF-Token': token}
        login = client.post('/api/auth/cookie/login', data={'username': owner+'@example.org', 'password': password}, headers=headers)
        assert login.status_code == 204, login.text
        created = client.post('/api/projects', json={'name': 'Physical original only'}, headers=headers)
        assert created.status_code == 201, created.text
        project = created.json()['id']
        uploaded = client.post(f'/api/projects/{project}/assets', content=original,
            headers={**headers, 'Content-Type': 'application/json', 'X-Asset-Metadata': json.dumps(meta)})
        assert uploaded.status_code == 201, uploaded.text
        receipt = uploaded.json()
        assert receipt['detected_format'] == 'gravity_stations_json'
        assert receipt['sha256'] == byte_sha(original) and receipt['byte_count'] == len(original)
        assert receipt['physical_metadata'] == {'schema_version': 'gravity-stations-1'}
        assert client.get(receipt['download_url']).content == original
        with closing(sqlite3.connect(settings.database_path)) as connection:
            assert connection.execute('SELECT raw_bytes FROM account_usage WHERE user_id=?', (owner,)).fetchone()[0] == len(original) + len(root_case[4])
            assert connection.execute('SELECT count(*) FROM observation_datasets').fetchone() == (1,)
    assert (settings.data_dir / f"projects/{owner}/{project}/{receipt['asset_id']}").read_bytes() == original
