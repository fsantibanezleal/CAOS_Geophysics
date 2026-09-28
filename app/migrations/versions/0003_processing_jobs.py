"""Immutable processed datasets and bounded processing jobs.

Revision ID: 0003_processing_jobs
Revises: 0002_private_storage_permission
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_processing_jobs"
down_revision = "0002_private_storage_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_id = sa.CHAR(36)
    op.create_table(
        "observation_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("owner_id", user_id, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("raw_asset_id", sa.String(36), sa.ForeignKey("raw_assets.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parser_version", sa.String(80), nullable=False),
        sa.Column("modality", sa.String(40), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("raw_sha256", sa.String(64), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(180), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("raw_asset_id", "parser_version"),
    )
    for column in ("project_id", "owner_id", "raw_asset_id"):
        op.create_index(f"ix_observation_datasets_{column}", "observation_datasets", [column])
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("owner_id", user_id, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("observation_datasets.id"), nullable=False),
        sa.Column("dataset_sha256", sa.String(64), nullable=False),
        sa.Column("method_id", sa.String(80), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("preflight", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("result_key", sa.String(180), nullable=True),
        sa.Column("result_sha256", sa.String(64), nullable=True),
        sa.Column("result_bytes", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("wall_ms", sa.Integer(), nullable=True),
        sa.Column("peak_rss_bytes", sa.Integer(), nullable=True),
        sa.Column("scratch_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ("project_id", "owner_id", "dataset_id", "state"):
        op.create_index(f"ix_processing_jobs_{column}", "processing_jobs", [column])
    op.add_column("deletion_receipts", sa.Column("derived_manifest", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("deletion_receipts", "derived_manifest")
    op.drop_table("processing_jobs")
    op.drop_table("observation_datasets")
