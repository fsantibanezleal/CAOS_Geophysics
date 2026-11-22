"""Explicit waveform source dependencies and immutable result members."""

from alembic import op
import sqlalchemy as sa

revision = "0004_waveform_artifacts"
down_revision = "0003_processing_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "waveform_dataset_sources",
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("observation_datasets.id"), primary_key=True),
        sa.Column("role", sa.String(16), primary_key=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("raw_assets.id"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("source_records.id"), nullable=False),
        sa.Column("raw_sha256", sa.String(64), nullable=False),
        sa.Column("raw_bytes", sa.Integer(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
    )
    op.create_table(
        "waveform_result_artifacts",
        sa.Column("job_id", sa.String(36), sa.ForeignKey("processing_jobs.id"), primary_key=True),
        sa.Column("name", sa.String(80), primary_key=True),
        sa.Column("storage_key", sa.String(260), nullable=False, unique=True),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
    )


def downgrade():
    # Existing artifact bytes are intentionally not deleted by a schema migration.
    op.drop_table("waveform_result_artifacts")
    op.drop_table("waveform_dataset_sources")
