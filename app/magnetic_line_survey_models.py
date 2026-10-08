"""Additive owner records: allocated 0007 after the reviewed M11 0006 capsule."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utcnow
from fastapi_users_db_sqlalchemy import GUID
from uuid import UUID


# Additive parent keys owned by this capsule; shared model source is unchanged.
PARENT_KEYS = (
    ('uq_m03_projects_owner_id', 'projects', ('owner_id', 'id')),
    ('uq_m03_raw_owner_project_id', 'raw_assets', ('owner_id', 'project_id', 'id')),
    ('uq_m03_dataset_owner_project_id', 'observation_datasets', ('owner_id', 'project_id', 'id')),
)
for _name, _table, _columns in PARENT_KEYS:
    Index(_name, *(Base.metadata.tables[_table].c[key] for key in _columns), unique=True)


class SurveyIntake(Base):
    """Committed quota/debt BEFORE any owned upload allocation."""
    __tablename__ = 'magnetic_survey_intakes'
    __table_args__ = (CheckConstraint('reservation_bytes > 0'), CheckConstraint('retained_bytes >= 0'),
        ForeignKeyConstraint(['owner_id', 'project_id'], ['projects.owner_id', 'projects.id']),
        ForeignKeyConstraint(['owner_id', 'project_id', 'asset_id'], ['raw_assets.owner_id', 'raw_assets.project_id', 'raw_assets.id']),
        CheckConstraint("state IN ('reserved','receiving','publication_uncertain','failed','published')"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey('user.id'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id'), index=True)
    role: Mapped[str] = mapped_column(String(32))
    header_json: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(24))
    reservation_bytes: Mapped[int] = mapped_column(Integer)
    retained_bytes: Mapped[int] = mapped_column(Integer, default=0)
    inventory: Mapped[list] = mapped_column(JSON, default=list)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('raw_assets.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SurveyAdmission(Base):
    __tablename__ = 'magnetic_survey_admissions'
    __table_args__ = (CheckConstraint('reservation_bytes > 0'),)

    job_id: Mapped[str] = mapped_column(String(36), ForeignKey('processing_jobs.id'), primary_key=True)
    start_json: Mapped[dict] = mapped_column(JSON)
    source_receipts: Mapped[dict] = mapped_column(JSON)
    authority_sha256: Mapped[str] = mapped_column(String(64))
    reservation_bytes: Mapped[int] = mapped_column(Integer)


class SurveyDatasetAttempt(Base):
    """Inspection debt before allocation; never a scientific success record."""
    __tablename__ = 'magnetic_survey_dataset_attempts'
    __table_args__ = (
        ForeignKeyConstraint(['owner_id', 'project_id'], ['projects.owner_id', 'projects.id']),
        ForeignKeyConstraint(['owner_id', 'project_id', 'dataset_id'],
            ['observation_datasets.owner_id', 'observation_datasets.project_id', 'observation_datasets.id']),
        CheckConstraint('reservation_bytes > 0'), CheckConstraint('retained_bytes >= 0'),
        CheckConstraint("state IN ('reserved','running','drained','publication_uncertain','failed','published')"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey('user.id'), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id'), index=True)
    input_json: Mapped[dict] = mapped_column(JSON)
    source_receipts: Mapped[dict] = mapped_column(JSON)
    authority_sha256: Mapped[str] = mapped_column(String(64))
    reservation_bytes: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24))
    retained_bytes: Mapped[int] = mapped_column(Integer, default=0)
    inventory: Mapped[list] = mapped_column(JSON, default=list)
    lifetime: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey('observation_datasets.id'), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SurveyAttempt(Base):
    __tablename__ = 'magnetic_survey_attempts'
    __table_args__ = (UniqueConstraint('job_id','ordinal'), CheckConstraint('ordinal > 0'),
        CheckConstraint('retained_bytes >= 0'), CheckConstraint("state IN ('claimed','running','drained','publication_uncertain','published')"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey('processing_jobs.id'), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24))
    worker_id: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lifetime: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retained_bytes: Mapped[int] = mapped_column(Integer, default=0)
    inventory: Mapped[list] = mapped_column(JSON, default=list)


class SurveyMember(Base):
    __tablename__ = 'magnetic_survey_members'
    __table_args__ = (UniqueConstraint('attempt_id','relative_name'), UniqueConstraint('attempt_id','id'), CheckConstraint('byte_count > 0'),
        CheckConstraint("kind IN ('result','manifest','chunk','page','receipt')"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey('magnetic_survey_attempts.id'), index=True)
    relative_name: Mapped[str] = mapped_column(String(240))
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))


class SurveyExportRecord(Base):
    __tablename__ = 'magnetic_survey_exports'
    __table_args__ = (CheckConstraint("scope IN ('private','public')"), CheckConstraint('byte_count > 0'),
        ForeignKeyConstraint(['attempt_id', 'manifest_member_id'], ['magnetic_survey_members.attempt_id', 'magnetic_survey_members.id']))

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey('magnetic_survey_attempts.id'), index=True)
    scope: Mapped[str] = mapped_column(String(8))
    manifest_member_id: Mapped[str] = mapped_column(String(36), ForeignKey('magnetic_survey_members.id'))
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
