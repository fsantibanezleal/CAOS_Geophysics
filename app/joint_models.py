"""Every native input is an explicit immutable dataset dependency."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
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
