"""Owner-scoped, deliberately CLOSED M03 full-survey integration port.

Mounting this router does not activate computation. It has no worker, filesystem,
scientific-engine or request-body dependency. Opening the lane requires replacing
this closed port with the reviewed owner lifecycle, not toggling configuration.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ApiError
from app.models import User
from app.projects import _owned_project


class MagneticSurveyCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema: Literal["m03-owner-capability/1"] = "m03-owner-capability/1"
    method: Literal["magnetic_line_survey"] = "magnetic_line_survey"
    online: Literal["closed"] = "closed"
    field_acceptance: Literal["unresolved"] = "unresolved"
    original_s1_predictive: Literal["fail"] = "fail"
    opened_refinement_predictive: Literal["fail"] = "fail"
    full_field_execution: Literal["not_verified"] = "not_verified"
    owner_lifecycle: Literal["not_integrated"] = "not_integrated"
    host_admission: Literal["not_established"] = "not_established"
    result_schema: Literal["magnetic-line-survey-result/1"] = "magnetic-line-survey-result/1"


def install_magnetic_survey_port(app: FastAPI, current_user, get_session) -> None:
    """Reuse the host's actual auth, DB ownership and security middleware."""
    router = APIRouter(prefix="/api/projects/{project_id}/magnetic-line-surveys")

    @router.get("/capability", response_model=MagneticSurveyCapability)
    async def capability(project_id: str, user: User = Depends(current_user),
                         session: AsyncSession = Depends(get_session)):
        await _owned_project(session, project_id, user)
        return MagneticSurveyCapability()

    @router.post("/jobs", status_code=409, responses={
        409: {"description": "Full-survey method is closed; no job is created"},
    })
    async def closed_job(project_id: str, user: User = Depends(current_user),
                         session: AsyncSession = Depends(get_session)):
        await _owned_project(session, project_id, user)
        raise ApiError(409, "method_closed", "Full-survey magnetic processing is not activated")

    app.include_router(router)
