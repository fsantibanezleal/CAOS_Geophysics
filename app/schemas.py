"""Request and response contracts for the private API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi_users import schemas as users_schemas
from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import UUID


class UserRead(users_schemas.BaseUser[UUID]):
    pass


class UserCreate(users_schemas.BaseUserCreate):
    pass


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must contain visible characters")
        return value.strip()


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must contain visible characters")
        return value.strip() if value is not None else None


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=200)
    doi: str | None = Field(default=None, max_length=200)
    citation: str | None = Field(default=None, max_length=2000)
    rights_statement: str = Field(min_length=10, max_length=4000)
    rights_decision: Literal["mirror", "provider-link-only", "derivative-only", "forbidden"]
    private_storage_permission: Literal["attested"]
    attribution: str = Field(min_length=1, max_length=2000)
    expected_bytes: int | None = Field(default=None, gt=0)
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")


class PhysicalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coordinate_reference: Literal["epsg", "local"]
    epsg: int | None = Field(default=None, ge=1000, le=999999)
    local_crs: str | None = Field(default=None, min_length=5, max_length=500)
    axis_order: Literal["xy", "yx", "lon_lat", "lat_lon"]
    horizontal_datum: str = Field(min_length=2, max_length=200)
    vertical_datum: str = Field(min_length=2, max_length=200)
    vertical_positive: Literal["up", "down"]
    horizontal_unit: Literal["m", "km", "degree"]
    vertical_unit: Literal["m", "ft"]
    measurement_unit: str = Field(min_length=1, max_length=40)
    epoch_utc: datetime
    component_frame: str = Field(min_length=2, max_length=80)
    geometry: dict = Field(min_length=1)

    @field_validator("epoch_utc")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("epoch_utc must include a timezone")
        return value

    @field_validator("horizontal_datum", "vertical_datum", "component_frame", "measurement_unit", "local_crs")
    @classmethod
    def nonblank_metadata(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("physical metadata must contain visible characters")
        return value.strip() if value is not None else None


class RawUploadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    mime: str = Field(min_length=1, max_length=100)
    format: Literal[
        "gravity_csv", "magnetic_csv", "traveltime_csv", "ert_csv", "geotiff",
        "edi", "miniseed", "stationxml", "segy", "mth5",
    ]
    source: SourceInput
    physical: PhysicalInput

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, value: str) -> str:
        if value in (".", "..") or "/" in value or "\\" in value or any(ord(c) < 32 for c in value):
            raise ValueError("filename must be a plain basename")
        return value
