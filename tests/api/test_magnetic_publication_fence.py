"""Independent SQLite mutation during real retained-generation publication."""
import asyncio
import hashlib
import json
import sqlite3

import pytest
from sqlalchemy import select

from app.errors import ApiError
from app.magnetic_custody import install_dataset, install_replay
from app.magnetic_custody_owner import attempt_charge
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from app.models import ObservationDataset, ProcessingJob
from app.processing_contract import canonical_bytes
from tests.api.test_magnetic_owned_custody import actual_generation as retained_generation, seeded


@pytest.fixture(scope="module")
def actual_generation():
    return retained_generation.__wrapped__()


@pytest.mark.parametrize("operation", ["dataset", "import"])
@pytest.mark.parametrize("mutation", ["rights", "physical"])
def test_final_fence_reads_actual_sql_after_copy(tmp_path, actual_generation, monkeypatch, operation, mutation):
    async def gate():
        engine, sessions, settings, user, dataset, asset, scratch = await seeded(tmp_path, actual_generation)
        owner = sessions.kw["info"]["magnetic_custody_owner"]
        files = owner.physical.leases.files
        real_write = files.write_new
        targets = []
        def mutate_after_copy(key, raw, *, cap):
            real_write(key, raw, cap=cap)
            targets.append((key, raw))
            with sqlite3.connect(settings.database_path) as independent:
                # This commit occurs AFTER the first fence's transaction and
                # target fsync, BEFORE the final fence's BEGIN IMMEDIATE.
                if mutation == "rights":
                    independent.execute("UPDATE source_records SET rights_decision='link' WHERE id=?", (asset.source_id,))
                else:
                    independent.execute("UPDATE raw_assets SET physical_metadata=? WHERE id=?",
                        (json.dumps({**asset.physical_metadata, "measurement_unit":"T"}), asset.id))
                independent.commit()
        monkeypatch.setattr(files, "write_new", mutate_after_copy)
        original_raw = (tmp_path / asset.storage_key).read_bytes()
        original_dataset = (tmp_path / dataset.storage_key).read_bytes()
        try:
            async with sessions() as session:
                with pytest.raises(ApiError):
                    if operation == "import":
                        await install_replay(session, settings, user, dataset.id, actual_generation[0],
                            project_id=dataset.project_id, temp_root=scratch)
                    else:
                        request = json.loads(canonical_bytes(actual_generation[2]["request"]))
                        request["inducing_field"]["D_deg"] = -72.0
                        await install_dataset(session, settings, user, asset.id, canonical_bytes(request), project_id=dataset.project_id)
            assert len(targets) == 1
            key, raw = targets[0]
            assert (tmp_path / key).read_bytes() == raw
            async with sessions() as session:
                row = (await session.execute(select(SurveyDatasetAttempt))).scalar_one()
                assert row.state == "publication_uncertain"
                assert row.retained_bytes == row.reservation_bytes == (512 if operation == "import" else 32)*1024**2
                assert await attempt_charge(session, user.id) == row.reservation_bytes
                assert row.inventory[0]["sha256"] == hashlib.sha256(raw).hexdigest()
                assert (await session.execute(select(ProcessingJob))).scalars().all() == []
                assert (await session.execute(select(ObservationDataset.id))).scalars().all() == [dataset.id]
            assert (tmp_path / asset.storage_key).read_bytes() == original_raw
            assert (tmp_path / dataset.storage_key).read_bytes() == original_dataset
        finally:
            await engine.dispose()
    asyncio.run(gate())
