"""Isolated loopback browser QA against fixed installed nonroot waveform authority.

Never a deployment entry point or root/science double. All paths are explicit
operator configuration; the public application has no QA routes or credentials.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import base64
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(os.environ["GEOPHYSICS_QA_API_SOURCE"]).resolve(strict=True)
sys.path.insert(0,str(ROOT))

from alembic import command
from alembic.config import Config
from fastapi.responses import FileResponse
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
import uvicorn

from app.accounts import provision_account
from app.config import Settings,external_storage_path
from app.database import make_engine
from app.models import User
from app.server import create_app
from app.waveform_linux_worker import installed_snapshot
from app.waveform_contract import INPUT
from tests.api.test_waveform_native_workflow import actual_metadata
from tests.api.test_waveform_service import make_case

EMAIL = "waveform-installed-qa@example.org"
PASSWORD = "isolated loopback QA account not a production credential"

def settings():
    assert sys.platform == "linux" and os.getuid() == os.geteuid() != 0 and not os.getgroups()
    data = external_storage_path(Path(os.environ["GEOPHYSICS_QA_DATA"]),"QA data")
    result = Settings(data_dir=data,auth_mode="local",cookie_secure=False,
        public_origin=os.environ["GEOPHYSICS_QA_ORIGIN"],
        auth_secret="isolated-installed-waveform-qa-not-deployment-123456789")
    installation = installed_snapshot(result)
    assert installation["source_revision"] == os.environ["GEOPHYSICS_QA_REVISION"]
    assert Path(installation["source_root"]).parent/"api-source" == ROOT
    return result

def fixture():
    case = os.environ.get("GEOPHYSICS_QA_CASE","nominal1")
    if case == "nominal1":
        return make_case(case),case
    assert case in ("ridgecrest-original","ridgecrest-original-aligned")
    import importlib.util
    spec = importlib.util.spec_from_file_location("waveform_original_qa",ROOT/"tests/data/test_waveform_ridgecrest.py")
    field = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(field)
    selected = {name:field.bounded_original(name+".raw") for name in ("miniseed","stationxml")}
    request = field.original_request()
    if case.endswith("-aligned"):
        records = INPUT.scan_miniseed(selected["miniseed"],request)
        shift = (records[0]["start_us"]-INPUT.utc_us(request["conditioning_start_utc"])) % (1000000//records[0]["sample_rate_hz"])
        assert shift == 8300
        for name in ("conditioning_start_utc","conditioning_end_utc","analysis_start_utc","analysis_end_utc"):
            request[name] = INPUT.format_utc(INPUT.utc_us(request[name])+shift)
    return dict(mseed=selected["miniseed"],stationxml=selected["stationxml"],
        request=json.dumps(INPUT.validate_request(request)).encode()),case

def main():
    if os.environ.get("GEOPHYSICS_WAVEFORM_QA") != "isolated-loopback-only":
        raise RuntimeError("Explicit isolated installed QA opt-in required")
    configured = settings()
    if sys.argv[1:] == ["--worker"]:
        from app.worker import run_forever
        asyncio.run(run_forever(configured))
        return
    assert sys.argv[1:] == []
    dist = external_storage_path(Path(os.environ["GEOPHYSICS_QA_DIST"]),"QA build")
    assert (dist/"qa-waveform.html").is_file()
    existing = configured.database_path.exists()
    assert not existing or os.environ.get("GEOPHYSICS_QA_EXISTING_DATABASE") == "reviewed-existing-same-source"
    port = int(os.environ["GEOPHYSICS_QA_PORT"])
    assert 1024 <= port <= 65535
    assert configured.public_origin == f"http://127.0.0.1:{port}"
    os.environ["GEOPHYSICS_DB_PATH"] = str(configured.database_path)
    migration = Config(str(ROOT/"app/alembic.ini"))
    migration.set_main_option("script_location",str(ROOT/"app/migrations"))
    if not existing:
        command.upgrade(migration,"head")
    else:
        from app.database import require_migration_head
        async def schema():
            engine = make_engine(configured)
            try:
                await require_migration_head(engine)
            finally:
                await engine.dispose()
        asyncio.run(schema())
    async def account():
        engine = make_engine(configured)
        try:
            sessions = async_sessionmaker(engine,expire_on_commit=False)
            async with sessions() as session:
                user = (await session.execute(select(User).where(User.email == EMAIL))).scalar_one_or_none()
                if user is not None:
                    if not existing or not user.is_active or user.is_superuser:
                        raise RuntimeError("Existing QA account is not an active ordinary account")
                    # Never rotate a password or change existing account rows.
                    # The browser must authenticate normally with the QA password.
                    return
            await provision_account(sessions,EMAIL,PASSWORD)
        finally:
            await engine.dispose()
    asyncio.run(account())
    worker = None
    app = create_app(configured)
    original = app.router.lifespan_context
    def stop_worker():
        nonlocal worker
        if worker is not None and worker.poll() is None:
            # Signal only this ordinary QA worker, never root/scientific PIDs.
            # Its original caller pipe and independent guardian contain science.
            worker.terminate()
            worker.wait(timeout=30)
        worker = None
    @asynccontextmanager
    async def lifetime(application):
        async with original(application):
            try:
                yield
            finally:
                stop_worker()
    app.router.lifespan_context = lifetime

    @app.get("/__qa/local-account")
    async def local_account():
        return dict(email=EMAIL,password=PASSWORD)

    @app.get("/__qa/waveform")
    async def original_fixture():
        selected,case = fixture()
        request = json.loads(selected["request"])
        return dict(harness="actual-waveform-native-v1",case=case,request=request,
            inputs={role:dict(base64=base64.b64encode(selected[key]).decode("ascii"),
                metadata=actual_metadata(selected[key],role,selected,request))
                for role,key in (("stationxml","stationxml"),("miniseed","mseed"))})

    @app.post("/__qa/worker/start")
    async def start():
        nonlocal worker
        if worker is None:
            worker = subprocess.Popen([sys.executable,"-I","-B",str(Path(__file__).resolve()),"--worker"],
                cwd=configured.data_dir,env=os.environ.copy(),stdin=subprocess.DEVNULL)
        if worker.poll() is not None:
            raise HTTPException(500,"Actual installed QA worker exited")
        return dict(started=True)

    @app.post("/__qa/worker/stop")
    async def stop():
        stop_worker()
        return dict(stopped=True)

    @app.get("/{path:path}")
    async def static(path:str):
        candidate = (dist/path).resolve()
        if candidate.is_relative_to(dist) and candidate.is_file():
            return FileResponse(candidate)
        if path == "":
            return FileResponse(dist/"qa-waveform.html")
        raise HTTPException(404,"Not found")
    uvicorn.run(app,host="127.0.0.1",port=port,log_level="warning")

if __name__ == "__main__":
    main()
