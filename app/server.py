"""FastAPI assembly for account and private raw-source lifecycles."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth import MailSender, install_auth
from app.config import Settings
from app.database import make_engine, reconcile_private_files, require_migration_head
from app.errors import ApiError, api_error_handler
from app.projects import install_project_routes
from app.processing import install_processing_routes
from app.security import install_security


def create_app(settings: Settings, mail_sender: MailSender | None = None, *, physical=None) -> FastAPI:
    if physical is not None:
        from app.physical_assembly import PhysicalAssembly
        from app.physical_contract import require
        require(isinstance(physical, PhysicalAssembly), 'physical_operator_assembly_required')
    engine = make_engine(settings)
    if physical is not None:
        physical.bind_engine(settings, engine)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            if physical is None:
                await require_migration_head(engine)
                await reconcile_private_files(settings, application.state.sessions)
            else:
                await physical.startup(settings, application.state.sessions)
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Geophysics private-state API", lifespan=lifespan)
    app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
    app.add_exception_handler(ApiError, api_error_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        if not request.url.path.startswith("/api/projects"):
            return await request_validation_exception_handler(request, error)
        fields = [".".join(str(part) for part in item["loc"]) for item in error.errors()]
        return JSONResponse(
            {"code": "request_invalid", "message": "Request fields are invalid", "fields": fields}, status_code=422,
        )

    current_user, get_session = install_auth(app, settings, mail_sender)
    install_security(app, settings)
    install_project_routes(app, settings, current_user, get_session)
    install_processing_routes(app, settings, current_user, get_session)
    if physical is not None:
        # Last-added ASGI middleware is outermost: before CSRF/rate/auth writes,
        # in their same task, covering the final streamed response as well.
        physical.install(app, settings)
    return app
