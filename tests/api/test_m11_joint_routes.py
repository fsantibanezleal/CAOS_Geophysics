"""M11 route seam, fail-closed schema admission, and adversarial source maps."""
from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.errors import ApiError
from app.joint_routes import _registered_0006, member_request
from tests.api.test_physical_successor import successor as successor


def _valid_map():
    return {"development": {"request.json": str(uuid4())},
            "sealed": {"sealed.json": str(uuid4())}}


@pytest.mark.parametrize("body", [
    b"", b"{}", b'{"development":{},"sealed":{}}',
    b'{"development":{"request.json":"not-a-uuid"},"sealed":{"sealed.json":"11111111-1111-4111-8111-111111111111"}}',
    b'{"development":{"../request.json":"11111111-1111-4111-8111-111111111111"},"sealed":{"sealed.json":"22222222-2222-4222-8222-222222222222"}}',
    b'{"development":{"request.json":"11111111-1111-4111-8111-111111111111"},"sealed":{"sealed.json":"11111111-1111-4111-8111-111111111111"}}',
    b'{"development":{"request.json":"11111111-1111-4111-8111-111111111111"},"development":{"mesh_hx.npy":"22222222-2222-4222-8222-222222222222"},"sealed":{"sealed.json":"33333333-3333-4333-8333-333333333333"}}',
    b'{"development":{"request.json":"11111111-1111-4111-8111-111111111111"},"sealed":{"sealed.json":"22222222-2222-4222-8222-222222222222"},"extra":{}}',
])
def test_member_map_rejects_malformed_duplicate_or_cross_role_inventory(body):
    with pytest.raises((ValueError, TypeError)):
        member_request(body)


def test_member_map_accepts_only_closed_role_asset_map():
    expected = _valid_map()
    assert member_request(json.dumps(expected, separators=(",", ":")).encode()) == expected
    with pytest.raises(ValueError, match="joint_dataset_request_cap"):
        member_request(b" " * 65537)


class _ScalarResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class _HeadOnlySession:
    def __init__(self, revision):
        self.revision = revision

    async def execute(self, _statement):
        return _ScalarResult([self.revision])


@pytest.mark.parametrize("revision", ["0004_waveform_artifacts", "0005_physical_forest", "0007_magnetic_line_artifacts"])
def test_noncanonical_or_unapproved_head_refuses_before_route_work(revision):
    import anyio

    async def check():
        with pytest.raises(ApiError) as error:
            await _registered_0006(_HeadOnlySession(revision))
        assert error.value.status == 409
        assert error.value.code == "joint_schema_unavailable"

    anyio.run(check)


def test_standard_app_does_not_mount_operator_only_m11_routes(make_harness):
    harness = make_harness()
    harness.account()
    project = harness.project()["id"]
    upload = harness.request("POST", f"/api/projects/{project}/joint-members", content=b"opaque")
    index = harness.request("POST", f"/api/projects/{project}/joint-datasets", json={})
    receipt = harness.request("GET", f"/api/projects/{project}/joint-datasets/{uuid4()}")
    assert (upload.status_code, index.status_code, receipt.status_code) == (404, 404, 404)


def test_real_0004_database_fails_schema_gate(make_harness):
    harness = make_harness()

    async def check():
        async with harness.app.state.sessions() as session:
            with pytest.raises(ApiError) as error:
                await _registered_0006(session)
            assert error.value.code == "joint_schema_unavailable"
            await session.rollback()

    harness.client.portal.call(check)


def test_real_0005_successor_database_fails_before_any_m11_write(successor):
    import asyncio
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    _config, database = successor

    async def check():
        engine = create_async_engine("sqlite+aiosqlite:///" + database.as_posix())
        try:
            async with async_sessionmaker(engine)() as session:
                with pytest.raises(ApiError) as error:
                    await _registered_0006(session)
                assert error.value.code == "joint_schema_unavailable"
                await session.rollback()
        finally:
            await engine.dispose()

    asyncio.run(check())
