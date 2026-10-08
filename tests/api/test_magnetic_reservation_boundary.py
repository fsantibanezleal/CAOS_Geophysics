"""Prior-record refusal with actual SQLite, not native admission or fitting."""
import asyncio

import pytest
from sqlalchemy import select
from uuid import uuid4

from app.errors import ApiError
from app.magnetic_line_survey_models import SurveyDatasetAttempt
from tests.api.test_magnetic_charged_custody import case


@pytest.mark.parametrize("attack", ["array", "null", "number", "unknown", "forged_published"])
def test_prior_attempt_refuses_before_accounting_and_any_new_birth(tmp_path, attack):
    async def gate():
        engine, sessions, settings, user, dataset, owner = await case(tmp_path)
        try:
            async with sessions() as session, owner.lifetime(session, settings):
                row = await owner.reserve(session, settings, user, dataset, operation="import",
                                          sources=owner.test_sources, job_id=str(uuid4()))
                if attack == "forged_published":
                    row.state = "published"
                    row.lifetime = dict(schema="magnetic-owned-custody-drain-1",
                                        work_completed=1, scratch_removed=True, native_admission=False)
                else:
                    row.input_json = {"array": [], "null": None, "number": 7,
                                      "unknown": {"schema": "unknown-owner"}}[attack]
                await session.commit()
                identifier, retained_request = row.id, row.input_json
                accounting = []

                async def observe_accounting(*_):
                    accounting.append("called")
                    return 0

                owner.base_charge = owner.device_charge = observe_accounting
                with pytest.raises(ApiError) as error:
                    await owner.reserve(session, settings, user, dataset, operation="read",
                                        sources=owner.test_sources, job_id=str(uuid4()))
                assert error.value.status == 409
                assert error.value.code == "magnetic_custody_debt"
                assert accounting == []
                assert not session.in_transaction()
                assert not (tmp_path / ".magnetic-custody").exists()
            async with sessions() as independent:
                rows = (await independent.execute(select(SurveyDatasetAttempt))).scalars().all()
                assert len(rows) == 1 and rows[0].id == identifier
                assert rows[0].input_json == retained_request
                assert rows[0].reservation_bytes == 512*1024**2
        finally:
            await engine.dispose()
    asyncio.run(gate())
