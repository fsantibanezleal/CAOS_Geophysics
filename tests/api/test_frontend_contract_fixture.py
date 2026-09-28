"""Keep the frontend's checked-in owner-view fixture valid against the real API projection."""

import json
from pathlib import Path

from app.views import RawAssetView


def test_frontend_owner_view_fixture_matches_api_schema():
    fixture_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "test" / "fixtures" / "api-owner-raw-v1.json"
    value = json.loads(fixture_path.read_text(encoding="utf-8"))
    view = RawAssetView.model_validate(value)
    assert view.model_dump(mode="json") == value
    assert "storage_key" not in json.dumps(value)
    assert view.validation_status == "raw_metadata_checked"
    assert view.source.citation is None
