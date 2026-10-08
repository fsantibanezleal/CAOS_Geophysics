"""Real durable failure cuts; no fabricated successful numerical generation."""
import asyncio
from pathlib import Path
import sqlite3
import threading

import pytest
from sqlalchemy import select

from app.errors import ApiError
from app.magnetic_custody import install_replay, install_dataset
from app.magnetic_custody_owner import attempt_charge
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.models import ProcessingJob
from tests.api.test_magnetic_charged_custody import case
from tests.api.magnetic_owner_transport import bind_sessions


@pytest.mark.parametrize("cut", ["before_export", "partial_export", "unknown_partial"])
def test_committed_charge_precedes_first_export_and_unknown_bytes_remain(tmp_path, monkeypatch, cut):
    async def gate():
        engine, sessions, settings, user, dataset, _ = await case(tmp_path)
        sessions.configure(info={})
        binding = bind_sessions(sessions, tmp_path)
        scratch = tmp_path / ".magnetic-custody"
        observed = []

        # Pure protocol phase controls. They deliberately fail BEFORE constructing
        # a view/job/success; these dictionaries are not scientific fixture data.
        monkeypatch.setattr("app.magnetic_custody._dataset", lambda *_: (
            dict(survey_source_id="authored_failure_control", request_sha256="d"*64,
                 geometry_plan=dict(identity=dict(configuration_sha256="e"*64))), {}))
        def fail_export(generation, request, stage, receipt):
            with sqlite3.connect(settings.database_path) as connection:
                state, reservation = connection.execute(
                    "SELECT state,reservation_bytes FROM magnetic_survey_dataset_attempts").fetchone()
                assert state == "reserved" and reservation == 512*1024**2
            assert binding.physical.worker.task is not None
            if cut != "before_export":
                (stage / "source.zip").write_bytes(b"actual partial export")
            if cut == "unknown_partial":
                (stage / "unknown-preserved").mkdir()
                (stage / "unknown-preserved" / "do-not-adopt").write_bytes(b"retain")
            observed.append(stage)
            raise RuntimeError("actual injected export failure")
        monkeypatch.setattr("app.magnetic_custody._prepare_replay", fail_export)
        try:
            async with sessions() as session:
                with pytest.raises(RuntimeError, match="actual injected"):
                    await install_replay(session, settings, user, dataset.id, Path("not-read-by-control"),
                                         project_id=dataset.project_id, temp_root=scratch)
                assert not session.in_transaction()
            async with sessions() as session:
                row = (await session.execute(select(SurveyDatasetAttempt))).scalar_one()
                assert row.state == "failed" and row.retained_bytes == row.reservation_bytes
                assert await attempt_charge(session, user.id) == 512*1024**2
                assert (await session.execute(select(ProcessingJob))).scalars().all() == []
                before = {p.relative_to(scratch).as_posix(): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
                with pytest.raises(ApiError, match="owner reconciliation"):
                    await install_replay(session, settings, user, dataset.id, Path("not-read-by-control"),
                                         project_id=dataset.project_id, temp_root=scratch)
                assert before == {p.relative_to(scratch).as_posix(): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
                assert len(observed) == 1
            assert binding.physical.worker.task is None and not binding.physical.leases.tasks
        finally:
            await engine.dispose()
    asyncio.run(gate())


@pytest.mark.parametrize("stop", ["cancel", "timeout"])
def test_wrapper_holds_worker_and_parent_lease_through_actual_thread_drain(tmp_path, monkeypatch, stop):
    async def gate():
        engine, sessions, settings, user, dataset, _ = await case(tmp_path)
        sessions.configure(info={})
        binding = bind_sessions(sessions, tmp_path)
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        monkeypatch.setattr("app.magnetic_custody._dataset", lambda *_: (
            dict(survey_source_id="failure_only", request_sha256="d"*64,
                 geometry_plan=dict(identity=dict(configuration_sha256="e"*64))), {}))
        def held_export(*_):
            started.set()
            assert release.wait(10)
            finished.set()
            raise RuntimeError("held export failed; no result constructed")
        monkeypatch.setattr("app.magnetic_custody._prepare_replay", held_export)
        if stop == "timeout":
            import app.magnetic_custody_owner as protocol
            real_work = protocol.bounded_work
            async def short_phase(function, *args, timeout):
                return await real_work(function, *args, timeout=0.02 if function is held_export else timeout)
            monkeypatch.setattr(protocol, "bounded_work", short_phase)

        async def run():
            async with sessions() as session:
                await install_replay(session, settings, user, dataset.id, Path("unused"),
                    project_id=dataset.project_id, temp_root=tmp_path / ".magnetic-custody")
        pending = asyncio.create_task(run())
        try:
            async with asyncio.timeout(10):
                while not started.is_set():
                    assert not pending.done()
                    await asyncio.sleep(0.001)
                if stop == "cancel":
                    pending.cancel()
                await asyncio.sleep(0.04)
                pending.cancel()  # repeated request cancellation during drain
                await asyncio.sleep(0.01)
                assert not pending.done() and not finished.is_set()
                assert binding.physical.worker.task is not None
                assert len(binding.physical.leases.tasks) == 2  # parent + fresh owned child
                release.set()
                with pytest.raises(asyncio.CancelledError):
                    await pending
                assert finished.is_set()
            assert binding.physical.worker.task is None and not binding.physical.leases.tasks
            async with sessions() as session:
                row = (await session.execute(select(SurveyDatasetAttempt))).scalar_one()
                assert row.state == "failed" and row.retained_bytes == 512*1024**2
                assert row.lifetime["work_completed"] is True and row.lifetime["native_admission"] is False
                assert (await session.execute(select(ProcessingJob))).scalars().all() == []
        finally:
            release.set()
            try:
                await pending
            except BaseException:
                pass
            await engine.dispose()
    asyncio.run(gate())


def test_dataset_target_failure_retains_precopy_intent_and_charge(tmp_path, monkeypatch):
    async def gate():
        engine, sessions, settings, user, dataset, _ = await case(tmp_path)
        sessions.configure(info={})
        binding = bind_sessions(sessions, tmp_path)
        from uuid import uuid4
        proposed = str(uuid4())
        # Failure-only phase DTO: it MUST NOT reach successful publication.
        monkeypatch.setattr("app.magnetic_custody._parse_owned_original", lambda *_:
            dict(dataset_id=proposed, parser_version="authored-failure-cut", dimensions=dict(row=288)))
        real_write = binding.physical.leases.files.write_new
        def fail_after_target(key, body, *, cap):
            with sqlite3.connect(settings.database_path) as connection:
                state, reservation, manifest = connection.execute(
                    "SELECT state,reservation_bytes,inventory FROM magnetic_survey_dataset_attempts").fetchone()
                import json
                assert state == "publication_uncertain" and reservation == 32*1024**2
                assert json.loads(manifest)[0]["id"] == proposed
            real_write(key, body, cap=cap)
            raise RuntimeError("actual target exists before failure")
        monkeypatch.setattr(binding.physical.leases.files, "write_new", fail_after_target)
        try:
            async with sessions() as session:
                with pytest.raises(RuntimeError, match="actual target exists"):
                    await install_dataset(session, settings, user, dataset.raw_asset_id, b"failure_only", project_id=dataset.project_id)
                from app.models import ObservationDataset
                assert await session.get(ObservationDataset, proposed) is None
                row = (await session.execute(select(SurveyDatasetAttempt))).scalar_one()
                assert row.state == "publication_uncertain" and row.dataset_id is None
                assert await attempt_charge(session, user.id) == 32*1024**2
                target = tmp_path / f"derived/{user.id}/{dataset.project_id}/datasets/{proposed}.json"
                original = target.read_bytes()
                with pytest.raises(ApiError, match="owner reconciliation"):
                    await install_dataset(session, settings, user, dataset.raw_asset_id, b"failure_only", project_id=dataset.project_id)
                assert target.read_bytes() == original
        finally:
            await engine.dispose()
    asyncio.run(gate())


def test_fresh_worker_does_not_rollback_callers_unrelated_transaction(tmp_path, monkeypatch):
    async def gate():
        engine, sessions, settings, user, dataset, _ = await case(tmp_path)
        sessions.configure(info={})
        bind_sessions(sessions, tmp_path)
        monkeypatch.setattr("app.magnetic_custody._dataset", lambda *_: (_ for _ in ()).throw(RuntimeError("before write")))
        try:
            async with sessions() as session:
                selected = await session.get(ProcessingJob, "00000000-0000-0000-0000-000000000000")
                assert selected is None and session.in_transaction()
                with pytest.raises(RuntimeError, match="before write"):
                    await install_replay(session, settings, user, dataset.id, Path("unused"),
                        project_id=dataset.project_id, temp_root=tmp_path / ".magnetic-custody")
                assert session.in_transaction()  # caller snapshot untouched
                assert (await session.execute(select(SurveyDatasetAttempt))).scalars().all() == []
        finally:
            await engine.dispose()
    asyncio.run(gate())
