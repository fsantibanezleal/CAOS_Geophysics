"""Additive owner records: allocated 0007 after the reviewed M11 0006 capsule."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, utcnow


class SurveyAdmission(Base):
    __tablename__ = 'magnetic_survey_admissions'
    __table_args__ = (CheckConstraint('reservation_bytes > 0'),)

    job_id: Mapped[str] = mapped_column(String(36), ForeignKey('processing_jobs.id'), primary_key=True)
    start_json: Mapped[dict] = mapped_column(JSON)
    source_receipts: Mapped[dict] = mapped_column(JSON)
    authority_sha256: Mapped[str] = mapped_column(String(64))
    reservation_bytes: Mapped[int] = mapped_column(Integer)


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
    __table_args__ = (UniqueConstraint('attempt_id','relative_name'), CheckConstraint('byte_count > 0'),
        CheckConstraint("kind IN ('result','manifest','chunk','page','receipt')"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey('magnetic_survey_attempts.id'), index=True)
    relative_name: Mapped[str] = mapped_column(String(240))
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))


class SurveyExportRecord(Base):
    __tablename__ = 'magnetic_survey_exports'
    __table_args__ = (CheckConstraint("scope IN ('private','public')"), CheckConstraint('byte_count > 0'))

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(36), ForeignKey('magnetic_survey_attempts.id'), index=True)
    scope: Mapped[str] = mapped_column(String(8))
    manifest_member_id: Mapped[str] = mapped_column(String(36), ForeignKey('magnetic_survey_members.id'))
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
