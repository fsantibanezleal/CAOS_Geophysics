"""Separate private upload authority from public rights decisions.

Revision ID: 0002_private_storage_permission
Revises: 0001_api_foundation
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_private_storage_permission"
down_revision = "0001_api_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing rows were never explicitly attested; do not invent consent.
    op.add_column("source_records", sa.Column("private_storage_permission", sa.String(16), nullable=True))
    op.add_column("deletion_receipts", sa.Column("asset_manifest", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("deletion_receipts", "asset_manifest")
    op.drop_column("source_records", "private_storage_permission")
