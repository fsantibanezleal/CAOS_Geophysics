"""SQLite metadata schema. Raw bytes live outside the web root."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy import GUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "user"


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    __tablename__ = "access_tokens"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("user.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourceRecord(Base):
    __tablename__ = "source_records"
    __table_args__ = (UniqueConstraint("project_id", "original_filename", "version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("user.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(200))
    exact_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    rights_statement: Mapped[str] = mapped_column(Text)
    rights_decision: Mapped[str] = mapped_column(String(32))
    private_storage_permission: Mapped[str | None] = mapped_column(String(16), nullable=True)
    declared_format: Mapped[str] = mapped_column(String(32))
    expected_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    attribution: Mapped[str] = mapped_column(Text)


class RawAsset(Base):
    __tablename__ = "raw_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("user.id"), index=True)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("source_records.id"), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    client_mime: Mapped[str] = mapped_column(String(100))
    detected_format: Mapped[str] = mapped_column(String(32))
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(150), unique=True)
    physical_metadata: Mapped[dict] = mapped_column(JSON)
    validation_status: Mapped[str] = mapped_column(String(32), default="raw_metadata_checked")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ObservationDataset(Base):
    __tablename__ = "observation_datasets"
    __table_args__ = (UniqueConstraint("raw_asset_id", "parser_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("user.id"), index=True)
    raw_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("raw_assets.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    parser_version: Mapped[str] = mapped_column(String(80))
    modality: Mapped[str] = mapped_column(String(40))
    row_count: Mapped[int] = mapped_column(Integer)
    raw_sha256: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64))
    byte_count: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(180), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("user.id"), index=True)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("observation_datasets.id"), index=True)
    dataset_sha256: Mapped[str] = mapped_column(String(64))
    method_id: Mapped[str] = mapped_column(String(80))
    request_json: Mapped[dict] = mapped_column(JSON)
    request_sha256: Mapped[str] = mapped_column(String(64))
    preflight: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(20), index=True)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    result_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    wall_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_rss_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scratch_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountUsage(Base):
    __tablename__ = "account_usage"

    user_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("user.id"), primary_key=True)
    raw_bytes: Mapped[int] = mapped_column(Integer, default=0)


class WaveformDatasetSource(Base):
    """Exact original pair; application also checks owner/project joins."""
    __tablename__ = "waveform_dataset_sources"
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("observation_datasets.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("raw_assets.id"))
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("source_records.id"))
    raw_sha256: Mapped[str] = mapped_column(String(64))
    raw_bytes: Mapped[int] = mapped_column(Integer)
    source_version: Mapped[int] = mapped_column(Integer)


class WaveformResultArtifact(Base):
    """Every immutable scientific export member is charged and inventoried."""
    __tablename__ = "waveform_result_artifacts"
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("processing_jobs.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(260), unique=True)
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))


class RateWindow(Base):
    __tablename__ = "rate_windows"
    __table_args__ = (UniqueConstraint("scope", "client_key", "window_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(40))
    client_key: Mapped[str] = mapped_column(String(128))
    window_start: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer, default=0)


class DeletionReceipt(Base):
    __tablename__ = "deletion_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), unique=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("user.id"), index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    asset_hashes: Mapped[list[str]] = mapped_column(JSON)
    asset_manifest: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    derived_manifest: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    backup_purge_status: Mapped[str] = mapped_column(String(40))
