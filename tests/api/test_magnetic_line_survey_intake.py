"""Actual owned stream/SQLite/debt/cookie routes, NOT full processing admission."""
import asyncio
from copy import deepcopy
import hashlib
import json
import struct
from uuid import UUID

import pytest
from sqlalchemy import select

from app.errors import ApiError
from app.magnetic_line_survey_intake import parse_asset_header, inspect_bundle, account_intake_usage
from app.magnetic_line_survey_intake_api import install_magnetic_line_survey_intake_routes
from app.magnetic_line_survey_models import SurveyIntake, PARENT_KEYS
from app.models import AccountUsage, RawAsset, Base
from app.processing_storage import account_derived_usage


def header(body=b'original field bytes', role='original_csv'):
    mime = 'application/octet-stream' if role == 'typed_auxiliary_bundle' else 'application/json' if role.endswith('_json') else 'text/csv'
    return dict(schema='m03-owner-asset/1', role=role, filename='owned-original.csv', mime=mime,
        source=dict(provider='Actual user-scoped declaration', doi=None, citation=None,
            rights_statement='I am permitted to privately store these exact original bytes.',
            rights_decision='mirror', private_storage_permission=True, attribution='Test owner',
            expected_bytes=len(body), expected_sha256=hashlib.sha256(body).hexdigest()))


def test_strict_all_header_keys_rights_and_noncoercion():
    original = header()
    assert parse_asset_header(json.dumps(original)).model_dump(mode='json', by_alias=True) == original
    for key in original:
        wrong = deepcopy(original); del wrong[key]
        with pytest.raises(ApiError): parse_asset_header(json.dumps(wrong))
    for key in original['source']:
        wrong = deepcopy(original); del wrong['source'][key]
        with pytest.raises(ApiError): parse_asset_header(json.dumps(wrong))
    for key, value in [('expected_bytes', True), ('expected_bytes', '20'), ('expected_sha256', 'A'*64),
                       ('private_storage_permission', 'true'), ('private_storage_permission', 1)]:
        wrong = deepcopy(original); wrong['source'][key] = value
        with pytest.raises(ApiError): parse_asset_header(json.dumps(wrong))
    for key, value in [('filename', '../private.csv'), ('filename', 'C:raw'), ('mime', 'application/json'),
                       ('path', 'E:/secret'), ('worker_module', 'evil')]:
        wrong = deepcopy(original); wrong[key] = value
        with pytest.raises(ApiError): parse_asset_header(json.dumps(wrong))
    raw = json.dumps(original)
    with pytest.raises(ApiError): parse_asset_header(raw[:-1]+',"role":"original_csv"}')


def bundle(entries):
    body = b'M03AUX1\n'+struct.pack('<I', len(entries))
    for name, payload in entries:
        encoded = name.encode('ascii')
        body += struct.pack('<H', len(encoded))+encoded+struct.pack('<Q', len(payload))+hashlib.sha256(payload).digest()+payload
    return body


def test_streamed_bundle_count_order_sha_trailing_and_no_extension_grant(tmp_path):
    valid = bundle([('array-values.json', b'{}'), ('value-00000000.bin', b'12345678')])
    path = tmp_path/'upload.part'; path.write_bytes(valid)
    result = inspect_bundle(path, len(valid))
    assert result['members'] == 2 and result['semantic_closure'] == 'not_verified'
    for bad in (valid+b'x', valid[:-1], valid[:-1]+b'X', bundle([('same', b'x'), ('same', b'y')]),
                bundle([('z', b'x'), ('a', b'y')]), bundle([('../evil', b'x')]), b'M03AUX1\n'+struct.pack('<I', 1000000)):
        path.write_bytes(bad)
        with pytest.raises(ApiError): inspect_bundle(path, len(bad))


def install(harness, *, ledger=None):
    async def tables():
        async with harness.app.state.sessions() as session:
            connection = await session.connection()
            for name, table, _ in PARENT_KEYS:
                index=next(item for item in Base.metadata.tables[table].indexes if item.name==name)
                await connection.run_sync(lambda conn, index=index: index.create(conn,checkfirst=True))
            await connection.run_sync(lambda conn: SurveyIntake.__table__.create(conn))
            await session.commit()
    asyncio.run(tables())
    def routes(items):
        for item in items:
            if hasattr(item, 'original_router'):
                yield from routes(item.original_router.routes)
            else:
                yield item
    route = next(r for r in routes(harness.app.routes)
        if getattr(r, 'path', None) == '/api/projects/{project_id}/assets' and 'POST' in r.methods)
    deps = {dep.name: dep.call for dep in route.dependant.dependencies}
    async def actual_ledger(session, owner_id):
        usage = await session.get(AccountUsage, owner_id)
        return (usage.raw_bytes if usage else 0)+await account_derived_usage(session, owner_id)
    install_magnetic_line_survey_intake_routes(harness.app, harness.settings, deps['user'], deps['session'],
        account_ledger=actual_ledger if ledger is None else ledger)


def upload(harness, project, body, meta):
    return harness.request('POST', f'/api/projects/{project}/magnetic-line-surveys/assets', content=body,
        headers={'Content-Type':meta['mime'], 'X-Asset-Metadata':json.dumps(meta)})


def test_actual_cookie_owner_stream_upload_uuid_source_and_precustody_reservation(make_harness, monkeypatch):
    harness = make_harness(); install(harness)
    account = harness.account(); project = harness.project()['id']
    import app.magnetic_line_survey_intake_api as routes
    original_reserve = routes.reserve_intake
    async def checked_reserve(*args):
        row = await original_reserve(*args)
        # A SECOND transaction observes the committed reservation before any
        # upload namespace/body allocation exists, not just an unflushed object.
        assert not (harness.settings.data_dir/'.m03-intake'/row.id).exists()
        async with harness.app.state.sessions() as another:
            stored = await another.get(SurveyIntake, row.id)
            assert stored.state == 'reserved' and stored.reservation_bytes > stored.header_json['source']['expected_bytes']
        return row
    monkeypatch.setattr(routes, 'reserve_intake', checked_reserve)
    body = b'all original bytes, not a parsed scientific field grant\n'
    response = upload(harness, project, body, header(body))
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt['provider_verification'] == 'not_verified' and receipt['field_eligibility'] == 'not_established'
    async def inspect():
        async with harness.app.state.sessions() as session:
            row = await session.get(SurveyIntake, receipt['asset_id'])
            assert row.state == 'published' and row.reservation_bytes > len(body)
            assert await account_intake_usage(session, UUID(account['id'])) == 0
            asset = await session.get(RawAsset, receipt['asset_id'])
            assert asset.detected_format == 'm03_original_csv'
            assert (harness.settings.data_dir/asset.storage_key).read_bytes() == body
            assert (await session.get(AccountUsage, UUID(account['id']))).raw_bytes == len(body)
    asyncio.run(inspect())
    sources = harness.request('GET', f'/api/projects/{project}/magnetic-line-surveys/sources')
    assert sources.status_code == 200 and sources.json()['entries'][0]['asset_id'] == receipt['asset_id']
    harness.client.cookies.clear()
    assert harness.request('GET', f'/api/projects/{project}/magnetic-line-surveys/sources').status_code == 401
    harness.csrf = ''
    harness.account('foreign-intake@example.org')
    assert upload(harness, project, body, header(body)).status_code == 404


def test_csrf_and_invalid_trusted_account_ledger_refuse_before_staging(make_harness):
    async def invalid_ledger(session, owner_id): return True
    harness = make_harness(); install(harness, ledger=invalid_ledger)
    harness.account(); project = harness.project()['id']; body = b'no allocation'
    meta = header(body)
    path = f'/api/projects/{project}/magnetic-line-surveys/assets'
    response = harness.client.post(path, content=body, headers={'Content-Type':'text/csv', 'X-Asset-Metadata':json.dumps(meta)})
    assert response.status_code == 403
    assert upload(harness, project, body, meta).status_code == 409
    assert not (harness.settings.data_dir/'.m03-intake').exists()


def test_failed_sha_retains_actual_partial_debt_and_quota_precedes_allocation(make_harness):
    harness = make_harness(account_quota_bytes=1024*1024, max_upload_bytes=512*1024); install(harness)
    account = harness.account(); project = harness.project()['id']
    body = b'actual wrong hash body'; meta = header(body); meta['source']['expected_sha256'] = '0'*64
    response = upload(harness, project, body, meta)
    assert response.status_code == 422, response.text
    async def inspect():
        async with harness.app.state.sessions() as session:
            row = (await session.execute(select(SurveyIntake))).scalar_one()
            assert row.state == 'failed' and row.retained_bytes == len(body) and row.asset_id is None
            assert await account_intake_usage(session, UUID(account['id'])) == row.reservation_bytes
            assert row.inventory[0]['sha256'] == hashlib.sha256(body).hexdigest()
    asyncio.run(inspect())
    large = b'x'*(512*1024)
    assert upload(harness, project, large, header(large)).status_code == 201
    before = sorted(p.as_posix() for p in harness.settings.data_dir.rglob('*'))
    assert upload(harness, project, large, header(large)).status_code == 507
    assert sorted(p.as_posix() for p in harness.settings.data_dir.rglob('*')) == before
    for rights in ('provider-link-only', 'derivative-only', 'forbidden'):
        meta = header(body); meta['source']['rights_decision'] = rights
        assert upload(harness, project, body, meta).status_code == 422


def test_corrupt_bundle_retained_without_asset_or_source_grant(make_harness):
    harness = make_harness(); install(harness); harness.account(); project = harness.project()['id']
    body = b'not a typed compressed/ZIP/pickle substitute'
    response = upload(harness, project, body, header(body, 'typed_auxiliary_bundle'))
    assert response.status_code == 409
    async def inspect():
        async with harness.app.state.sessions() as session:
            row = (await session.execute(select(SurveyIntake))).scalar_one()
            assert row.state == 'failed' and row.retained_bytes == len(body)
            assert (await session.execute(select(RawAsset))).scalars().all() == []
    asyncio.run(inspect())


def test_changed_moved_target_stays_uncertain_and_is_not_registered(make_harness, monkeypatch):
    import app.magnetic_line_survey_intake as intake
    harness = make_harness(); install(harness); account = harness.account(); project = harness.project()['id']
    original_rename = intake.os.rename
    def changed_after_move(source, target):
        original_rename(source, target)
        # Owned negative-control bytes in the isolated test root only.
        target.write_bytes(b'changed target, retained as adverse custody evidence')
    monkeypatch.setattr(intake.os, 'rename', changed_after_move)
    body = b'exact original target'
    assert upload(harness, project, body, header(body)).status_code == 409
    async def inspect():
        async with harness.app.state.sessions() as session:
            row = (await session.execute(select(SurveyIntake))).scalar_one()
            assert row.state == 'publication_uncertain' and row.asset_id is None
            assert row.retained_bytes == len(b'changed target, retained as adverse custody evidence')
            assert (await session.execute(select(RawAsset))).scalars().all() == []
            assert await account_intake_usage(session, UUID(account['id'])) >= row.retained_bytes
    asyncio.run(inspect())
