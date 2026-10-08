"""Actual parsed producer/read envelope controls, not numerical qualification."""
import asyncio
import hashlib

import pytest
from sqlalchemy import select

from app.errors import ApiError
from app.magnetic_contract import MAX_DATASET, MAX_REQUEST, parse_magnetic_dataset
from app.magnetic_custody import install_dataset, _dataset
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.models import ObservationDataset
from app.processing_contract import canonical_bytes
from tests.api.test_magnetic_owned_custody import seeded
from tests.api.test_magnetic_owned_survey import control


def test_real_parsed_8MiB_request_refuses_unreadable_body_before_reservation(tmp_path):
    async def gate():
        doc, original, refs = control()
        raw = canonical_bytes(doc)
        # Actual valid whitespace in the supplied full request. Escaping newlines
        # in its dataset body increases bytes; no mocked parse or fake success.
        supplied = b'\n'*(MAX_REQUEST-len(raw))+raw
        payload = parse_magnetic_dataset(supplied, original, **refs)
        assert len(supplied) == MAX_REQUEST == MAX_DATASET == 8388608
        assert len(canonical_bytes(payload)) > MAX_DATASET
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path,
            (None, original, {'request': doc}, refs['asset'].physical_metadata['geometry']))
        before = (tmp_path/dataset.storage_key).read_bytes()
        try:
            async with sessions() as session:
                with pytest.raises(ApiError) as refusal:
                    await install_dataset(session, settings, user, asset.id, supplied,
                                          project_id=dataset.project_id)
                assert refusal.value.status == 413
                assert refusal.value.code == 'magnetic_dataset_capacity_refused'
            async with sessions() as independent:
                assert (await independent.execute(select(SurveyDatasetAttempt))).scalars().all() == []
                assert len((await independent.execute(select(ObservationDataset))).scalars().all()) == 1
            assert list(scratch.iterdir()) == []
            assert (tmp_path/asset.storage_key).read_bytes() == original
            assert (tmp_path/dataset.storage_key).read_bytes() == before
        finally:
            await engine.dispose()
    asyncio.run(gate())


def test_owned_read_refuses_oversized_retained_body_before_json_decode(tmp_path, monkeypatch):
    async def gate():
        doc, original, refs = control()
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path,
            (None, original, {'request': doc}, refs['asset'].physical_metadata['geometry']))
        try:
            path = tmp_path/dataset.storage_key
            raw = b' '*(MAX_DATASET+1)
            path.write_bytes(raw)
            dataset.byte_count, dataset.sha256 = len(raw), hashlib.sha256(raw).hexdigest()
            def no_parse(*_):
                pytest.fail('Oversized body must refuse before decoding')
            import app.magnetic_custody as custody
            monkeypatch.setattr(custody.json, 'loads', no_parse)
            with pytest.raises(ApiError):
                _dataset(settings, dataset, asset, refs['source'])
            assert path.read_bytes() == raw
            assert (tmp_path/asset.storage_key).read_bytes() == original
            assert list(scratch.iterdir()) == []
        finally:
            await engine.dispose()
    asyncio.run(gate())
