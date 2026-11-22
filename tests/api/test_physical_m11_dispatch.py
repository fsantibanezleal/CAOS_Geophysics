"""M11 dispatch is limited to exact 0006 under the existing worker guards."""
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.physical_assembly import dispatch_candidate_m11
from app.database import make_engine
from tests.api.test_physical_assembly import bound_fixture
from tests.api.test_physical_deleted_inventory import case
from tests.api.test_physical_roots import root_case as root_case
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey

pytest_plugins = ("tests.api.test_m11_candidate_runtime_success",)


def test_default_schema_skips_m11_dispatch(root_case, monkeypatch):
    case(root_case)
    settings, physical = bound_fixture(root_case, monkeypatch)
    calls = []

    async def unexpected(*args, **kwargs):
        calls.append("m11")
        raise AssertionError("M11 dispatch must not run on 0005")

    monkeypatch.setattr("app.joint_job_worker.run_once", unexpected)

    async def run():
        engine = make_engine(settings)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with physical.leases.acquire():
                async with physical.worker.acquire_processing():
                    result = await dispatch_candidate_m11(settings, sessions, physical)
                    assert result == (False, None)
        finally:
            await engine.dispose()

    asyncio.run(run())
    assert calls == []
    assert not physical.leases.held and not physical.worker.held


def test_legacy_worker_claim_does_not_consume_candidate_m11(m11_candidate):
    from app.physical_joint_native_contract import METHOD_ID
    from app.worker import _claim
    from tests.api.test_m11_candidate_job_routes import _upload_dataset

    fixture_root, row, client, headers, project, _, _ = m11_candidate
    dataset = _upload_dataset(fixture_root, row, client, headers, project)
    app = client.app
    physical = app.state.physical_assembly

    queued = client.post(f"/api/projects/{project}/joint-jobs",
                         json={"dataset_id": dataset["dataset_id"]}, headers=headers)
    assert queued.status_code == 202, queued.text

    async def run():
        sessions = app.state.sessions
        async with physical.leases.acquire():
            async with physical.worker.acquire_processing():
                assert await _claim(sessions, "legacy-test-worker",
                                    exclude_method_id=METHOD_ID) is None

    client.portal.call(run)
    status = client.get(f"/api/projects/{project}/joint-jobs/{queued.json()['job_id']}")
    assert status.status_code == 200 and status.json()["state"] == "queued"

