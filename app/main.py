"""Uvicorn entry point. Configuration must be provided by the process environment."""

from app.config import Settings
from app.server import create_app


app = create_app(Settings.from_env())
