"""Unknown incomplete custody cannot bypass the original deletion seam."""

import asyncio
from types import SimpleNamespace

import pytest

from app.errors import ApiError
from app.profile_archive_delete import ProfileArchiveDeletion, prepare_archive_deletion


@pytest.mark.parametrize('installed',[False,True])
@pytest.mark.parametrize('kind',['empty-directory','partial-archive','file'])
def test_unregistered_incomplete_namespace_refuses_before_participant_or_moves(tmp_path,monkeypatch,installed,kind):
    root=tmp_path/'.profile-incomplete'
    if kind=='file': root.write_bytes(b'unknown namespace preserved')
    else:
        root.mkdir()
        if kind=='partial-archive': (root/'unknown.intent.json').write_bytes(b'unadmitted partial evidence')
    before={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    participant=object.__new__(ProfileArchiveDeletion) if installed else None
    async def forbidden(*_,**__):
        pytest.fail('Unknown custody reached participant or deletion preparation')
    monkeypatch.setattr(ProfileArchiveDeletion,'prepare',forbidden)
    app=SimpleNamespace(state=SimpleNamespace(profile_archive_deletion=participant))
    with pytest.raises(ApiError) as error:
        asyncio.run(prepare_archive_deletion(app,SimpleNamespace(data_dir=tmp_path),None,'owner','project',[]))
    assert error.value.status==409 and error.value.code=='profile_archive_custody_unresolved'
    assert before=={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert root.exists() and not (tmp_path/'.deleting').exists()


def test_legacy_no_incomplete_namespace_remains_empty_without_adoption(tmp_path):
    app=SimpleNamespace(state=SimpleNamespace())
    assert asyncio.run(prepare_archive_deletion(app,SimpleNamespace(data_dir=tmp_path),None,'owner','project',[]))==[]
    assert list(tmp_path.iterdir())==[]


def test_original_http_delete_preserves_incomplete_custody_and_plural_ownership(make_harness):
    import sqlite3
    from tests.api.conftest import GRAVITY_CSV
    from tests.api.test_local_auth import login,provision
    harness=make_harness(auth_mode='local')
    owner=provision(harness,'first@example.org')['account_id']
    provision(harness,'second@example.org')
    assert login(harness,'first@example.org').status_code==204
    project=harness.project()
    asset=harness.upload(project['id']).json()
    raw=harness.settings.data_dir/f"projects/{owner}/{project['id']}/{asset['asset_id']}"
    stage=harness.settings.data_dir/'.profile-incomplete'
    stage.mkdir()
    diagnostic=stage/'unknown.intent.json'
    diagnostic.write_bytes(b'authentic partial evidence must remain')
    assert login(harness,'second@example.org').status_code==204
    foreign=harness.request('DELETE',f"/api/projects/{project['id']}")
    assert foreign.status_code==404
    assert login(harness,'first@example.org').status_code==204
    own=harness.request('DELETE',f"/api/projects/{project['id']}")
    assert own.status_code==409 and own.json()['code']=='profile_archive_custody_unresolved'
    assert raw.read_bytes()==GRAVITY_CSV
    assert diagnostic.read_bytes()==b'authentic partial evidence must remain'
    assert not (harness.settings.data_dir/'.deleting').exists() and not harness.messages
    with sqlite3.connect(harness.settings.database_path) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone()==('0004_waveform_artifacts',)
        assert connection.execute('SELECT count(*) FROM projects').fetchone()==(1,)
        assert connection.execute('SELECT count(*) FROM raw_assets').fetchone()==(1,)
        assert connection.execute('SELECT count(*) FROM deletion_receipts').fetchone()==(0,)
        assert connection.execute('SELECT raw_bytes FROM account_usage WHERE user_id=?',(owner,)).fetchone()==(len(GRAVITY_CSV),)
