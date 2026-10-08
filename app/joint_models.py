"""Every native input is an explicit immutable dataset dependency."""
from __future__ import annotations

from uuid import UUID

from fastapi_users_db_sqlalchemy import GUID
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class JointDatasetSource(Base):
    __tablename__ = 'joint_dataset_sources'

    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey('observation_datasets.id', ondelete='CASCADE'), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey('raw_assets.id'), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey('source_records.id'), nullable=False)
    raw_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)


class JointResultArtifact(Base):
    """Retained originals, bound to the complete immutable producing job identity.

    No cascading deletion: a terminal row is not evidence that its bytes have
    been removed, nor permission to release their charge.
    """
    __tablename__ = 'joint_result_artifacts'
    __table_args__ = (
        ForeignKeyConstraint(
            ['job_id','owner_id','project_id','dataset_id','dataset_sha256','method_id','request_sha256'],
            ['processing_jobs.id','processing_jobs.owner_id','processing_jobs.project_id',
             'processing_jobs.dataset_id','processing_jobs.dataset_sha256',
             'processing_jobs.method_id','processing_jobs.request_sha256'],
            name='fk_joint_artifact_job', ondelete='RESTRICT', onupdate='RESTRICT'),
        CheckConstraint("method_id='joint.gravity-magnetic-native/v1'", name='ck_joint_artifact_method'),
        CheckConstraint("typeof(byte_count)='integer' AND byte_count BETWEEN 1 AND 268435456", name='ck_joint_artifact_bytes'),
        CheckConstraint("typeof(sha256)='text' AND length(sha256)=64 AND sha256 NOT GLOB '*[^0-9a-f]*'", name='ck_joint_artifact_sha'),
        CheckConstraint("typeof(name)='text' AND length(name) BETWEEN 1 AND 180 AND name NOT GLOB '*[^a-zA-Z0-9_./-]*' "
                        "AND substr(name,1,1)<>'/' AND substr(name,-1)<>'/' AND instr(name,'..')=0 "
                        "AND instr(name,'//')=0 AND instr('/'||name||'/','/./')=0", name='ck_joint_artifact_name'),
        CheckConstraint("storage_key='derived/'||owner_id||'/'||project_id||'/joint/'||job_id||'/'||name",
                        name='ck_joint_artifact_key'),
    )

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(180), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dataset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    method_id: Mapped[str] = mapped_column(String(80), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
