"""Explicit current default0004 control; no alternative physical schema mount."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_default_is_recognized_waveform_predecessor_not_historical_alternative():
    from app.database import MIGRATION_HEAD
    from app.models import Base
    root = Path(__file__).resolve().parents[2]
    assert ScriptDirectory.from_config(Config(str(root / 'app/alembic.ini'))).get_heads() == ['0004_waveform_artifacts']
    assert MIGRATION_HEAD == '0004_waveform_artifacts'
    assert not any(name.startswith('physical_') for name in Base.metadata.tables)
    assert not (root / 'app/migrations/versions/0004_physical_persistence.py').exists()
    assert not (root / 'app/migrations/versions/0005_physical_forest.py').exists()
