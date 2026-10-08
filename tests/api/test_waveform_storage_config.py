"""External storage and immutable implementation admission controls."""
from pathlib import Path

import pytest

from app.config import Settings, WorkerSettings, external_storage_path
from app.waveform_contract import implementation_sha256


def test_storage_has_no_implicit_repository_default(monkeypatch):
    monkeypatch.delenv("GEOPHYSICS_DATA_DIR", raising=False)
    for settings in (Settings, WorkerSettings):
        with pytest.raises(ValueError, match="explicitly select external"):
            settings.from_env()


def test_repository_and_relative_storage_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="absolute"):
        external_storage_path(Path("data/raw/api"), "data")
    with pytest.raises(ValueError, match="outside repository"):
        WorkerSettings(data_dir=Path(__file__).resolve().parents[2] / "data/raw/api")
    settings = WorkerSettings(data_dir=tmp_path / "private")
    assert settings.database_path == tmp_path / "private/api.sqlite3"


def test_implementation_hash_is_content_based_and_changes_on_source_change(monkeypatch):
    before = implementation_sha256()
    original = Path.read_bytes
    def changed(path):
        raw = original(path)
        return raw + b"\n# changed\n" if path.name == "waveform_processing.py" and path.parent.name == "data-pipeline" else raw
    monkeypatch.setattr(Path, "read_bytes", changed)
    assert implementation_sha256() != before
