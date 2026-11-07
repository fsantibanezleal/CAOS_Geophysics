"""Deletion path admission precedes moves and SQL retirement, no native claim."""
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from app.errors import ApiError
from app.projects import _require_supported_deletion_paths
from tests.api.test_local_auth import login, provision


@pytest.mark.parametrize('length,accepted', [(259, True), (260, False), (261, False)])
def test_every_deletion_member_obeys_windows_utf16_bound(length, accepted):
    member = 'waveforms/job/c00-characteristic.bin'
    suffix_length = len(str(Path('d') / member)) - 1
    derived = Path('x' * (length - suffix_length))
    manifest = [dict(kind='waveform_artifact', relative_path=member)]
    if accepted:
        _require_supported_deletion_paths(Path('raw'), derived, [], manifest, platform='nt')
    else:
        with pytest.raises(ApiError) as error:
            _require_supported_deletion_paths(Path('raw'), derived, [], manifest, platform='nt')
        assert error.value.status == 503
        assert error.value.code == 'deletion_storage_unavailable'


def test_raw_targets_are_checked_and_posix_has_no_windows_limit():
    asset = SimpleNamespace(id='x' * 260)
    with pytest.raises(ApiError):
        _require_supported_deletion_paths(Path('raw'), Path('derived'), [asset], [], platform='nt')
    _require_supported_deletion_paths(Path('raw'), Path('derived'), [asset], [], platform='posix')


def test_count_is_utf16_units_not_unicode_characters():
    derived = Path(chr(0x10000) * 130)
    assert len(str(derived)) < 260
    with pytest.raises(ApiError):
        _require_supported_deletion_paths(Path('raw'), derived, [], [], platform='nt')


def test_original_http_refusal_preserves_plural_ownership_rows_and_files(make_harness, monkeypatch):
    harness = make_harness(auth_mode='local')
    provision(harness, 'first@example.org')
    provision(harness, 'second@example.org')
    assert login(harness, 'first@example.org').status_code == 204
    project = harness.project()
    asset = harness.upload(project['id']).json()
    originals = {p: p.read_bytes() for p in harness.settings.data_dir.rglob('*')
                 if p.is_file() and 'projects' in p.parts}

    def unavailable(*args, **kwargs):
        raise ApiError(503, 'deletion_storage_unavailable', 'Unsupported destination')

    monkeypatch.setattr('app.projects._require_supported_deletion_paths', unavailable)
    assert login(harness, 'second@example.org').status_code == 204
    assert harness.request('DELETE', f"/api/projects/{project['id']}").status_code == 404
    assert login(harness, 'first@example.org').status_code == 204
    response = harness.request('DELETE', f"/api/projects/{project['id']}")
    assert response.status_code == 503
    assert response.json()['code'] == 'deletion_storage_unavailable'
    assert originals and all(p.read_bytes() == body for p, body in originals.items())
    assert not (harness.settings.data_dir / '.deleting').exists()
    with sqlite3.connect(harness.settings.database_path) as db:
        assert db.execute('SELECT count(*) FROM projects').fetchone() == (1,)
        assert db.execute('SELECT id FROM raw_assets').fetchone() == (asset['asset_id'],)
        assert db.execute('SELECT count(*) FROM deletion_receipts').fetchone() == (0,)
    assert not harness.messages
