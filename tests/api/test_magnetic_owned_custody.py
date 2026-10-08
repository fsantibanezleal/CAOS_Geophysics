"""Real SQLite custody on an actual externally retained local generation.

Set GEOPHYSICS_MAGNETIC_TEST_GENERATION and ORIGINAL. Absence is an error, not
fixture skip or permission to manufacture a successful scientific generation.
"""

import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import Settings
from app.errors import ApiError
from app.magnetic_contract import parse_magnetic_dataset, MODALITY, science, magnetic_dataset_receipt, method_mapping
from app.magnetic_custody import install_replay, read_replay, exact_zip_inventory, install_dataset, read_dataset, read_method
from app.models import Base, User, Project, SourceRecord, RawAsset, ObservationDataset, AccountUsage, ProcessingJob
from app.magnetic_line_survey_models import SurveyDatasetAttempt  # register existing schema before test create_all
from app.processing_contract import canonical_bytes, dataset_key


@pytest.fixture(scope="module")
def actual_generation():
    science()
    from magnetic_result_bundle import read_bundle
    generation = Path(os.environ["GEOPHYSICS_MAGNETIC_TEST_GENERATION"])
    original = Path(os.environ["GEOPHYSICS_MAGNETIC_TEST_ORIGINAL"]).read_bytes()
    columns = json.loads(Path(os.environ["GEOPHYSICS_MAGNETIC_TEST_COLUMNS"]).read_bytes())
    imported = read_bundle(generation)
    assert hashlib.sha256(original).hexdigest() == imported["request"]["source"]["original_sha256"]
    assert imported["result"]["status"] == "complete" and not any(imported["result"]["claims"].values())
    return generation, original, imported, columns


async def seeded(tmp_path, actual):
    generation, original, imported, columns = actual
    doc = imported["request"]
    owner, project_id, asset_id, source_id, dataset_id = [str(uuid4()) for _ in range(5)]
    settings = Settings(data_dir=tmp_path, auth_secret="x"*40, public_origin="http://testserver", cookie_secure=False)
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    from tests.api.magnetic_owner_transport import bind_sessions
    bind_sessions(sessions, tmp_path)
    user = User(id=UUID(owner), email=f"{owner}@example.org", hashed_password="unusable", is_active=True, is_verified=True)
    source = SourceRecord(id=source_id, owner_id=user.id, project_id=project_id, original_filename="authored.csv",
        version=1, provider="Actual authored local control", rights_statement="Owner private control",
        rights_decision="mirror", private_storage_permission="attested", declared_format="magnetic_csv",
        sha256=hashlib.sha256(original).hexdigest(), expected_bytes=len(original), attribution="Authored, not field")
    physical = dict(coordinate_reference="local", local_crs=doc["frame"]["crs"], axis_order="xy", horizontal_unit="m",
        vertical_unit="m", vertical_positive="up", vertical_datum=doc["frame"]["vertical_datum"], measurement_unit="nT",
        component_frame="ENU" if doc["processing"]["quantity"] == "secondary_enu_nT" else "total field", geometry=columns)
    asset = RawAsset(id=asset_id, owner_id=user.id, project_id=project_id, source_id=source_id, filename="authored.csv",
        client_mime="text/csv", detected_format="magnetic_csv", byte_count=len(original), sha256=source.sha256,
        storage_key=f"projects/{owner}/{project_id}/{asset_id}", physical_metadata=physical)
    payload = parse_magnetic_dataset(canonical_bytes(doc), original, dataset_id=dataset_id,
                                    owner_id=owner, project_id=project_id, asset=asset, source=source)
    body = canonical_bytes(payload)
    dataset = ObservationDataset(id=dataset_id, owner_id=user.id, project_id=project_id, raw_asset_id=asset_id,
        version=1, parser_version=payload["parser_version"], modality=MODALITY, row_count=payload["dimensions"]["row"],
        raw_sha256=asset.sha256, sha256=hashlib.sha256(body).hexdigest(), byte_count=len(body),
        storage_key=dataset_key(owner, project_id, dataset_id))
    for key, data in ((asset.storage_key, original), (dataset.storage_key, body)):
        path = tmp_path / key
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_bytes(data)
    scratch = tmp_path / ".magnetic-custody"
    scratch.mkdir(mode=0o700)
    async with sessions() as session:
        session.add_all([user, Project(id=project_id, owner_id=user.id, name="Actual control"),
            source, asset, dataset, AccountUsage(user_id=user.id, raw_bytes=len(original))])
        await session.commit()
    return engine, sessions, settings, user, dataset, asset, scratch


def test_real_generation_owned_roundtrip(tmp_path, actual_generation):
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        try:
            async with sessions() as session:
                job = await install_replay(session, settings, user, dataset.id, actual_generation[0], project_id=dataset.project_id, temp_root=scratch)
                assert job.state == "succeeded" and job.result_key.endswith(".zip")
                view = await read_replay(session, settings, user, job.id, project_id=dataset.project_id, temp_root=scratch)
                assert len(view["rows"]) == dataset.row_count
                assert view["binding"]["generation_sha256"] == actual_generation[2]["generation_sha256"]
                assert view["binding"]["source_id"] == actual_generation[2]["request"]["source"]["id"]
                assert not any(view["claims"].values()) and view["lane"] == "local_replay"
                raw = await read_replay(session, settings, user, job.id, project_id=dataset.project_id, temp_root=scratch, export=True)
                assert hashlib.sha256(raw).hexdigest() == job.result_sha256 and len(raw) == job.result_bytes
                assert exact_zip_inventory(settings, job)["byte_count"] == len(raw)
                assert list(scratch.iterdir()) == []
                assert (tmp_path / asset.storage_key).read_bytes() == actual_generation[1]
                from app.processing import _job_view
                assert magnetic_dataset_receipt(dataset)["parser_version"] == dataset.parser_version
                (tmp_path / "browser-control.json").write_bytes(canonical_bytes(dict(
                    provenance="Actual retained original6 null7cell local generation; no nonzero/field/native-host acceptance",
                    job=_job_view(job), receipt=magnetic_dataset_receipt(dataset), view=view,
                    zip_path=str(tmp_path / job.result_key))))
                payload = json.loads((tmp_path / dataset.storage_key).read_bytes())
                (tmp_path / "browser-input-control.json").write_bytes(canonical_bytes(dict(
                    receipt=magnetic_dataset_receipt(dataset), payload=payload, mapping=method_mapping(payload,dataset))))
            # Reopen a distinct connection: this is a durable SQL/file receipt,
            # not an in-memory SimpleNamespace pretending to be an API job.
            async with sessions() as session:
                row = (await session.execute(select(ProcessingJob))).scalar_one()
                assert row.id == job.id and row.result_sha256 == job.result_sha256
                assert (await read_replay(session, settings, user, row.id, project_id=dataset.project_id, temp_root=scratch))["selected"] == view["selected"]
        finally:
            await engine.dispose()
    asyncio.run(gate())


@pytest.mark.parametrize("attack", ["quota", "other_owner", "request", "source_permission", "original"])
def test_custody_refusals(tmp_path, actual_generation, attack):
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        try:
            if attack == "quota": settings = replace(settings, max_upload_bytes=1, account_quota_bytes=1)
            if attack == "other_owner": user = User(id=uuid4(), email="foreign@example.org", hashed_password="unusable")
            if attack == "original": (tmp_path / asset.storage_key).write_bytes(b"changed")
            async with sessions() as session:
                if attack == "source_permission":
                    source = await session.get(SourceRecord, asset.source_id)
                    source.private_storage_permission = "unknown"
                    await session.commit()
                if attack == "request":
                    body = (tmp_path / dataset.storage_key).read_bytes() + b" "
                    (tmp_path / dataset.storage_key).write_bytes(body)
                with pytest.raises(ApiError):
                    await install_replay(session, settings, user, dataset.id, actual_generation[0], project_id=dataset.project_id, temp_root=scratch)
                assert (await session.execute(select(ProcessingJob))).scalars().all() == []
                assert list(scratch.iterdir()) == []
                assert not list((tmp_path / "derived").rglob("*.zip"))
        finally:
            await engine.dispose()
    asyncio.run(gate())


@pytest.mark.parametrize("attack", ["zip", "zip_missing", "receipt", "source", "physical", "original", "dataset", "foreign", "cancel", "preflight"])
def test_read_export_drift_refused(tmp_path, actual_generation, attack):
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        try:
            async with sessions() as session:
                job = await install_replay(session, settings, user, dataset.id, actual_generation[0], project_id=dataset.project_id, temp_root=scratch)
                session.add(job)  # fresh worker returns a detached durable row
                if attack == "zip": (tmp_path / job.result_key).write_bytes(b"changed")
                if attack == "zip_missing": (tmp_path / job.result_key).unlink()
                if attack == "receipt": job.result_sha256 = "0"*64
                if attack == "source":
                    source = await session.get(SourceRecord, asset.source_id)
                    source.rights_decision = "forbidden"
                if attack == "original": (tmp_path / asset.storage_key).write_bytes(b"changed")
                if attack == "physical":
                    row = await session.get(RawAsset, asset.id)
                    row.physical_metadata = {**row.physical_metadata, "measurement_unit": "T"}
                if attack == "dataset": (tmp_path / dataset.storage_key).write_bytes(b"{}")
                if attack == "foreign": user = User(id=uuid4(), email="foreign@example.org", hashed_password="unusable")
                if attack == "cancel": job.cancel_requested = True
                if attack == "preflight": job.preflight = {**job.preflight, "unknown": True}
                await session.commit()
                for export in (False, True):
                    with pytest.raises(ApiError): await read_replay(session, settings, user, job.id, project_id=dataset.project_id, temp_root=scratch, export=export)
                assert list(scratch.iterdir()) == []
        finally:
            await engine.dispose()
    asyncio.run(gate())


def test_changed_physical_request_versions_dataset_without_overwrite(tmp_path, actual_generation):
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        try:
            raw = canonical_bytes(actual_generation[2]["request"])
            previous = (tmp_path / dataset.storage_key).read_bytes()
            async with sessions() as session:
                same = await install_dataset(session, settings, user, asset.id, raw, project_id=dataset.project_id)
                assert same.id == dataset.id
            doc = json.loads(raw)
            doc["inducing_field"]["D_deg"] = -72.0
            async with sessions() as session:
                changed = await install_dataset(session, settings, user, asset.id, canonical_bytes(doc), project_id=dataset.project_id)
                assert changed.id != dataset.id and changed.parser_version != dataset.parser_version
                assert len(changed.parser_version) <= 80
                assert (tmp_path / dataset.storage_key).read_bytes() == previous
                assert (tmp_path / asset.storage_key).read_bytes() == actual_generation[1]
                assert (await session.execute(select(ProcessingJob))).scalars().all() == []
                changed_id = changed.id
                await session.rollback()
                with pytest.raises(ApiError, match="custody"):
                    await install_replay(session, settings, user, changed_id, actual_generation[0], project_id=dataset.project_id, temp_root=scratch)
        finally:
            await engine.dispose()
    asyncio.run(gate())


@pytest.mark.parametrize("failure", ["flush", "commit", "existing_path"])
def test_exclusive_publication_and_uncertain_commit_preserve_custody(tmp_path, actual_generation, monkeypatch, failure):
    import app.magnetic_custody as custody
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        prior = (tmp_path / dataset.storage_key).read_bytes()
        known_job = str(uuid4())
        unknown = tmp_path / custody.zip_result_key(str(user.id), dataset.project_id, known_job)
        try:
            async with sessions() as session:
                if failure == "existing_path":
                    unknown.parent.mkdir(parents=True, exist_ok=True)
                    unknown.write_bytes(b"unknown existing custody: never adopted or removed")
                    monkeypatch.setattr(custody, "uuid4", lambda: UUID(known_job))
                else:
                    original = getattr(sessions.class_, failure)
                    async def broken(worker, *args, **kwargs):
                        # Inject into the fresh worker's FINAL publication only,
                        # never the caller or pre-copy reservation transaction.
                        final = (any(isinstance(row, ProcessingJob) for row in worker.new) if failure == "flush" else
                            any(isinstance(row, SurveyDatasetAttempt) and row.state == "published"
                                for row in worker.identity_map.values()))
                        if final:
                            raise RuntimeError("injected storage transaction failure")
                        return await original(worker, *args, **kwargs)
                    monkeypatch.setattr(sessions.class_, failure, broken)
                with pytest.raises((OSError, RuntimeError)):
                    await install_replay(session, settings, user, dataset.id, actual_generation[0], project_id=dataset.project_id, temp_root=scratch)
                retained = list((tmp_path / "derived").rglob("*.zip"))
                if failure in ("flush", "commit"): assert len(retained) == 1 and retained[0].stat().st_size > 0
                if failure == "existing_path": assert retained == [unknown] and unknown.read_bytes().startswith(b"unknown existing")
            async with sessions() as session:
                assert (await session.execute(select(ProcessingJob))).scalars().all() == []
                debt = (await session.execute(select(SurveyDatasetAttempt))).scalar_one()
                assert debt.state == "publication_uncertain" and debt.retained_bytes == debt.reservation_bytes
                assert debt.inventory[0]["kind"] == "magnetic_result"
            assert (tmp_path / dataset.storage_key).read_bytes() == prior
            assert (tmp_path / asset.storage_key).read_bytes() == actual_generation[1]
            if failure != "existing_path":
                assert list(scratch.iterdir()) == []
        finally:
            await engine.dispose()
    asyncio.run(gate())


def test_public_input_and_method_readers(tmp_path, actual_generation):
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        try:
            async with sessions() as session:
                payload = await read_dataset(session, settings, user, dataset.id, project_id=dataset.project_id)
                assert json.loads(payload["request_utf8"]) == actual_generation[2]["request"]
                mapping = await read_method(session, settings, user, dataset.id, project_id=dataset.project_id)
                assert mapping["online_admitted"] is False and mapping["dataset_sha256"] == dataset.sha256
                source = await session.get(SourceRecord, asset.source_id)
                source.private_storage_permission = "unknown"
                await session.commit()
                for reader in (read_dataset, read_method):
                    with pytest.raises(ApiError):
                        await reader(session, settings, user, dataset.id, project_id=dataset.project_id)
                assert list(scratch.iterdir()) == []
        finally:
            await engine.dispose()
    asyncio.run(gate())


def test_selected_project_precedes_file_io(tmp_path, actual_generation, monkeypatch):
    import app.magnetic_custody as custody
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        other = str(uuid4())
        try:
            async with sessions() as session:
                session.add(Project(id=other, owner_id=user.id, name="Other owned project"))
                await session.commit()
                job = await install_replay(session, settings, user, dataset.id, actual_generation[0], project_id=dataset.project_id, temp_root=scratch)
            def no_io(*args, **kwargs):
                raise AssertionError("Selected project must be checked before file I/O")
            monkeypatch.setattr(custody, "_read", no_io)
            async with sessions() as session:
                with pytest.raises(ApiError) as error:
                    await install_dataset(session, settings, user, asset.id, canonical_bytes(actual_generation[2]["request"]), project_id=other)
                assert error.value.status == 404
            async with sessions() as session:
                with pytest.raises(ApiError) as error:
                    await install_replay(session, settings, user, dataset.id, tmp_path/"does-not-exist", project_id=other, temp_root=scratch)
                assert error.value.status == 404
            for reader in (read_dataset, read_method):
                async with sessions() as session:
                    with pytest.raises(ApiError) as error:
                        await reader(session, settings, user, dataset.id, project_id=other)
                    assert error.value.status == 404
            for export in (False, True):
                async with sessions() as session:
                    with pytest.raises(ApiError) as error:
                        await read_replay(session, settings, user, job.id, project_id=other, temp_root=scratch, export=export)
                    assert error.value.status == 404
            assert list(scratch.iterdir()) == []
        finally:
            await engine.dispose()
    asyncio.run(gate())


def test_existing_cookie_csrf_auth_assembly(tmp_path, actual_generation):
    """Actual auth + ABI fixture, NOT the mounted shared product union."""
    from fastapi import FastAPI, Depends
    from fastapi.responses import JSONResponse, Response
    from fastapi.testclient import TestClient
    from fastapi_users.password import PasswordHelper
    from pydantic import BaseModel, ConfigDict, Field
    from app.auth import install_auth
    from app.errors import api_error_handler
    from app.security import install_security
    from app.processing import _job_view, _owned_job

    password = "Actual-cookie-control-password-1"
    other_id = uuid4()
    other_project = str(uuid4())
    async def prepare():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        async with sessions() as session:
            owner = await session.get(User, user.id)
            owner.hashed_password = PasswordHelper().hash(password)
            session.add_all([User(id=other_id, email="other-cookie@example.org",
                hashed_password=PasswordHelper().hash(password), is_active=True, is_verified=True),
                Project(id=other_project, owner_id=user.id, name="Other owned route")])
            await session.commit()
            job = await install_replay(session, settings, user, dataset.id, actual_generation[0],
                                       project_id=dataset.project_id, temp_root=scratch)
        return engine, sessions, settings, user, dataset, asset, scratch, job
    engine, sessions, settings, user, dataset, asset, scratch, job = asyncio.run(prepare())
    app = FastAPI()
    app.state.sessions = sessions
    app.add_exception_handler(ApiError, api_error_handler)
    async def no_mail(*args):
        raise AssertionError("No registration, verification mail or SMTP prerequisite")
    current_user, get_session = install_auth(app, settings, no_mail)
    install_security(app, settings)

    class DatasetInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        asset_id: UUID
        magnetic_request_utf8: str = Field(min_length=1, max_length=8388608)

    @app.post("/api/projects/{project_id}/datasets", status_code=201)
    async def create(project_id: str, body: DatasetInput, owner=Depends(current_user)):
        async with sessions() as session:
            item = await install_dataset(session, settings, owner, str(body.asset_id),
                body.magnetic_request_utf8.encode("utf-8"), project_id=project_id)
            return magnetic_dataset_receipt(item)

    @app.get("/api/projects/{project_id}/datasets/{dataset_id}")
    async def input_read(project_id: str, dataset_id: str, owner=Depends(current_user), session=Depends(get_session)):
        return JSONResponse(await read_dataset(session, settings, owner, dataset_id, project_id=project_id),
                            headers={"Cache-Control":"no-store"})

    @app.get("/api/projects/{project_id}/datasets/{dataset_id}/methods")
    async def method_read(project_id: str, dataset_id: str, owner=Depends(current_user), session=Depends(get_session)):
        return await read_method(session, settings, owner, dataset_id, project_id=project_id)

    @app.get("/api/projects/{project_id}/jobs/{job_id}")
    async def job_read(project_id: str, job_id: str, owner=Depends(current_user), session=Depends(get_session)):
        return _job_view(await _owned_job(session, project_id, job_id, owner))

    @app.get("/api/projects/{project_id}/jobs/{job_id}/result")
    async def result_read(project_id: str, job_id: str, owner=Depends(current_user), session=Depends(get_session)):
        return await read_replay(session, settings, owner, job_id, project_id=project_id, temp_root=scratch)

    @app.get("/api/projects/{project_id}/jobs/{job_id}/export")
    async def export_read(project_id: str, job_id: str, owner=Depends(current_user), session=Depends(get_session)):
        return Response(await read_replay(session, settings, owner, job_id,
            project_id=project_id, temp_root=scratch, export=True), media_type="application/zip",
            headers={"Cache-Control":"no-store"})

    prefix = f"/api/projects/{dataset.project_id}"
    paths = [f"{prefix}/datasets/{dataset.id}", f"{prefix}/datasets/{dataset.id}/methods",
             f"{prefix}/jobs/{job.id}", f"{prefix}/jobs/{job.id}/result", f"{prefix}/jobs/{job.id}/export"]
    def login(client, email):
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        headers = {"Origin":settings.public_origin,"X-CSRF-Token":csrf}
        response = client.post("/api/auth/cookie/login",data={"username":email,"password":password},headers=headers)
        assert response.status_code == 204, response.text
        assert "geophysics_session" in client.cookies
        assert client.get("/api/auth/me").status_code == 200
        return headers
    try:
        with TestClient(app, base_url=settings.public_origin) as client:
            for path in paths:
                assert client.get(path).status_code == 401
            headers = login(client, user.email)
            body = dict(asset_id=asset.id, magnetic_request_utf8=canonical_bytes(actual_generation[2]["request"]).decode())
            assert client.post(prefix+"/datasets",json=body).status_code == 403
            response = client.post(prefix+"/datasets",json=body,headers=headers)
            assert response.status_code == 201, response.text
            assert response.json()["dataset_id"] == dataset.id
            assert client.get(paths[0]).json()["request_utf8"] == body["magnetic_request_utf8"]
            assert client.get(paths[1]).json()["online_admitted"] is False
            assert client.get(paths[2]).json()["result_sha256"] == job.result_sha256
            result = client.get(paths[3])
            assert result.status_code == 200 and not any(result.json()["claims"].values())
            exported = client.get(paths[4])
            assert exported.status_code == 200 and exported.headers["cache-control"] == "no-store"
            assert hashlib.sha256(exported.content).hexdigest() == job.result_sha256
            assert exported.content == (tmp_path/job.result_key).read_bytes()
            for path in paths:
                assert client.get(path.replace(dataset.project_id,other_project)).status_code == 404
            assert client.post(f"/api/projects/{other_project}/datasets",json=body,headers=headers).status_code == 404
            assert client.post("/api/auth/cookie/logout",headers=headers).status_code == 204
            headers = login(client,"other-cookie@example.org")
            for path in paths:
                assert client.get(path).status_code == 404
            assert client.post(prefix+"/datasets",json=body,headers=headers).status_code == 404
            assert (tmp_path/asset.storage_key).read_bytes() == actual_generation[1]
            assert list(scratch.iterdir()) == []
    finally:
        asyncio.run(engine.dispose())
