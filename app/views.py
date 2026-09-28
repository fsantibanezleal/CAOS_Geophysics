"""Explicit owner-only wire views; ORM storage keys never cross this boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.models import RawAsset, SourceRecord


class UploadLocationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["upload"] = "upload"
    filename: str


class SourceRecordView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["geophysics.source-record-view/v1"] = "geophysics.source-record-view/v1"
    source_id: str
    version: int
    provider: str
    location: UploadLocationView
    doi: str | None
    citation: str | None
    retrieved_at: datetime
    rights_statement: str
    rights_decision: Literal["mirror", "provider-link-only", "derivative-only", "forbidden"]
    private_storage_permission: Literal["attested"] | None
    declared_format: str
    expected_bytes: int | None
    sha256: str
    attribution: str


class RawAssetView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["geophysics.raw-asset-view/v1"] = "geophysics.raw-asset-view/v1"
    asset_id: str
    owner_id: str
    project_id: str
    source_id: str
    source: SourceRecordView
    original_filename: str
    mime_type: str
    detected_format: str
    byte_count: int
    sha256: str
    physical_metadata: dict[str, Any]
    validation_status: Literal["raw_metadata_checked"]
    created_at: datetime
    receipt: str
    download_url: str


class RawAssetListView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assets: list[RawAssetView]


def stored_utc(value: datetime) -> datetime:
    """SQLite drops timezone offsets; persisted API timestamps are UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def source_view(source: SourceRecord) -> SourceRecordView:
    if source.exact_url is not None:
        raise RuntimeError("reviewed URL source projection is not implemented")
    return SourceRecordView(
        source_id=source.id,
        version=source.version,
        provider=source.provider,
        location=UploadLocationView(filename=source.original_filename),
        doi=source.doi,
        citation=source.citation,
        retrieved_at=stored_utc(source.retrieved_at),
        rights_statement=source.rights_statement,
        rights_decision=source.rights_decision,
        private_storage_permission=source.private_storage_permission,
        declared_format=source.declared_format,
        expected_bytes=source.expected_bytes,
        sha256=source.sha256,
        attribution=source.attribution,
    )


def asset_view(asset: RawAsset, source: SourceRecord) -> RawAssetView:
    if source.id != asset.source_id or source.project_id != asset.project_id or source.owner_id != asset.owner_id:
        raise RuntimeError("raw asset and source ownership disagree")
    receipt = f"/api/projects/{asset.project_id}/assets/{asset.id}"
    return RawAssetView(
        asset_id=asset.id,
        owner_id=str(asset.owner_id),
        project_id=asset.project_id,
        source_id=source.id,
        source=source_view(source),
        original_filename=asset.filename,
        mime_type=asset.client_mime,
        detected_format=asset.detected_format,
        byte_count=asset.byte_count,
        sha256=asset.sha256,
        physical_metadata=asset.physical_metadata,
        validation_status=asset.validation_status,
        created_at=stored_utc(asset.created_at),
        receipt=receipt,
        download_url=f"{receipt}/download",
    )
