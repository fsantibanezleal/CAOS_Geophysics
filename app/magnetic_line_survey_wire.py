"""Strict M03 owner DTOs and read-only source custody, without a mounted lifecycle.

Paths returned here are internal verified storage locations, never client fields.
Binding proves byte identity and scope at read time, not magnetic eligibility,
independent provider review, job admission or a durable execution snapshot.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, WorkerSettings
from app.database import checked_storage_path
from app.errors import ApiError
from app.models import User
from app.processing import _owned_dataset
from app.processing_contract import checked_derived_path, dataset_key
from app.projects import _owned_asset, _owned_project


WIRE_MAX_BYTES = 16384


def _uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if type(value) is not str:
        raise ValueError("A canonical UUID is required")
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError("A canonical UUID is required")
    return parsed


def _hash(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("A lowercase SHA-256 is required")
    return value


WireUUID = Annotated[UUID, BeforeValidator(_uuid)]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$"), BeforeValidator(_hash)]


class SurveyStart(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal["m03-owner-start/1"] = Field(alias="schema")
    dataset_id: WireUUID
    original_asset_id: WireUUID
    metadata_asset_id: WireUUID
    request_asset_id: WireUUID
    auxiliary_asset_ids: list[WireUUID] = Field(min_length=0, max_length=16)
    dataset_sha256: Hash
    original_sha256: Hash
    metadata_sha256: Hash
    request_sha256: Hash
    auxiliary_sha256: list[Hash] = Field(min_length=0, max_length=16)

    @model_validator(mode="after")
    def distinct_references(self) -> SurveyStart:
        if len(self.auxiliary_asset_ids) != len(self.auxiliary_sha256):
            raise ValueError("Auxiliary UUID and hash lengths must match")
        identities = [self.dataset_id, self.original_asset_id, self.metadata_asset_id,
                      self.request_asset_id, *self.auxiliary_asset_ids]
        if len(set(identities)) != len(identities):
            raise ValueError("UUID references must be unique")
        return self


class SurveyExport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal["m03-owner-export/1"] = Field(alias="schema")
    scope: Literal["private", "public"]


DTO = TypeVar("DTO", SurveyStart, SurveyExport)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("Nonfinite JSON")


def _parse(raw: bytes, model: type[DTO]) -> DTO:
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= WIRE_MAX_BYTES:
            raise ValueError("Invalid body size")
        payload = json.loads(raw.decode("utf-8", errors="strict"),
                             object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        return model.model_validate(payload)
    except (ValueError, RecursionError) as exc:
        fields = ["body"]
        if isinstance(exc, ValidationError):
            known = {field.alias or name for name, field in model.model_fields.items()}
            fields = sorted({str(error["loc"][0]) if error["loc"] and error["loc"][0] in known
                             else "body" for error in exc.errors()})
        raise ApiError(422, "request_invalid", "Survey request fields are invalid", fields) from exc


def parse_survey_start(raw: bytes) -> SurveyStart:
    """Call only after host authentication, CSRF/origin and owned-project checks."""
    return _parse(raw, SurveyStart)


def parse_survey_export(raw: bytes) -> SurveyExport:
    """Parse the closed export preference; it does not confer export rights."""
    return _parse(raw, SurveyExport)


@dataclass(frozen=True)
class BoundSurveyFile:
    id: UUID
    sha256: str
    byte_count: int
    path: Path


@dataclass(frozen=True)
class BoundSurveyAsset(BoundSurveyFile):
    source_id: UUID
    rights_decision: str
    private_storage_permission: str | None


@dataclass(frozen=True)
class OwnedSurveySources:
    owner_id: UUID
    project_id: UUID
    dataset: BoundSurveyFile
    original: BoundSurveyAsset
    metadata: BoundSurveyAsset
    request: BoundSurveyAsset
    auxiliaries: tuple[BoundSurveyAsset, ...]


def _integrity(code: str) -> ApiError:
    return ApiError(409, code, "Stored survey input differs from its custody receipt")


def _stamp(info: os.stat_result) -> tuple[int, ...]:
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError("Unsafe storage entry")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def _verify_bytes(root: Path, path: Path, expected_sha: str, expected_bytes: int, code: str) -> None:
    """Stream exact receipt bytes; reject aliases, changes during read and excess data."""
    try:
        _hash(expected_sha)
        if type(expected_bytes) is not int or expected_bytes <= 0:
            raise ValueError("Invalid receipt size")
        if not path.is_relative_to(root):
            raise ValueError("Invalid storage boundary")
        for item in (path, *path.parents):
            if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
                raise ValueError("Unsafe storage path")
            if item == root:
                break
        before = _stamp(path.lstat())
        if before[2] != expected_bytes:
            raise ValueError("Receipt size mismatch")
        digest = hashlib.sha256()
        count = 0
        with path.open("rb") as stream:
            opened = _stamp(os.fstat(stream.fileno()))
            # CPython 3.12 Windows lstat/fstat expose different ctime semantics.
            # Compare identity/size/mtime across APIs, ctime within each API.
            if opened[:4] + opened[5:] != before[:4] + before[5:]:
                raise ValueError("Storage changed before read")
            while chunk := stream.read(min(1024 * 1024, expected_bytes - count + 1)):
                count += len(chunk)
                if count > expected_bytes:
                    raise ValueError("Storage grew during read")
                digest.update(chunk)
            if _stamp(os.fstat(stream.fileno())) != opened:
                raise ValueError("Storage changed during read")
        if _stamp(path.lstat()) != before or count != expected_bytes or digest.hexdigest() != expected_sha:
            raise ValueError("Receipt hash mismatch")
    except (OSError, ValueError) as exc:
        raise _integrity(code) from exc


async def bind_owned_survey_sources(
    session: AsyncSession, settings: Settings | WorkerSettings, project_id: UUID,
    user: User, request: SurveyStart,
) -> OwnedSurveySources:
    """Resolve every DB scope before reading; verify receipts and exact originals.

    The caller owns transaction/snapshot lifetime and must rebind at claim and
    publication. No DB writes, JSON/scientific decoding, allocation or dispatch.
    """
    project_key = str(project_id)
    await _owned_project(session, project_key, user)
    # Frozen DTO attributes still contain JSON lists; never trust mutated lists
    # or model_construct objects at the internal worker boundary.
    request = SurveyStart.model_validate(request.model_dump(by_alias=True))
    dataset = await _owned_dataset(session, project_key, str(request.dataset_id), user)
    references = [(request.original_asset_id, request.original_sha256),
                  (request.metadata_asset_id, request.metadata_sha256),
                  (request.request_asset_id, request.request_sha256),
                  *zip(request.auxiliary_asset_ids, request.auxiliary_sha256, strict=True)]
    rows = []
    for asset_id, expected_sha in references:
        asset, source = await _owned_asset(session, project_key, str(asset_id), user)
        # The shared helper checks SourceRecord.owner_id but not project_id.
        if source.project_id != project_key:
            raise ApiError(404, "not_found", "Raw asset not found")
        rows.append((asset, source, expected_sha))
    if (dataset.raw_asset_id != str(request.original_asset_id)
            or dataset.raw_sha256 != request.original_sha256 or dataset.sha256 != request.dataset_sha256):
        raise _integrity("derived_integrity_failed")
    expected_key = dataset_key(str(user.id), project_key, dataset.id)
    if dataset.storage_key != expected_key:
        raise _integrity("derived_integrity_failed")
    for asset, source, expected_sha in rows:
        if (asset.sha256 != expected_sha or source.sha256 != expected_sha
                or source.expected_bytes != asset.byte_count
                or asset.storage_key != f"projects/{user.id}/{project_key}/{asset.id}"):
            raise _integrity("raw_integrity_failed")
    try:
        dataset_path = checked_derived_path(settings, expected_key)
        paths = [checked_storage_path(settings, asset.storage_key) for asset, _, _ in rows]
    except (RuntimeError, OSError, ValueError) as exc:
        raise _integrity("survey_storage_invalid") from exc
    await asyncio.to_thread(_verify_bytes, settings.data_dir, dataset_path,
                            dataset.sha256, dataset.byte_count, "derived_integrity_failed")
    bound = []
    for (asset, source, expected_sha), path in zip(rows, paths, strict=True):
        await asyncio.to_thread(_verify_bytes, settings.data_dir, path,
                                expected_sha, asset.byte_count, "raw_integrity_failed")
        bound.append(BoundSurveyAsset(UUID(asset.id), expected_sha, asset.byte_count, path,
                                      UUID(source.id), source.rights_decision, source.private_storage_permission))
    return OwnedSurveySources(user.id, project_id,
                              BoundSurveyFile(request.dataset_id, dataset.sha256, dataset.byte_count, dataset_path),
                              bound[0], bound[1], bound[2], tuple(bound[3:]))
