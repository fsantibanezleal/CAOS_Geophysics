"""Uvicorn entry point. Configuration must be provided by the process environment."""

from app.config import Settings
from app.server import create_app
from app.operator_runtime import configured_physical_assembly


settings = Settings.from_env()
physical = configured_physical_assembly(settings)
app = create_app(settings, physical=physical)
