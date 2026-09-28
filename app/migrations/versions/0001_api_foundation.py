"""Initial private project and library-auth metadata.

Revision ID: 0001_api_foundation
Revises:
"""

from alembic import op
import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import TIMESTAMPAware


revision = "0001_api_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_id = sa.CHAR(36)
    op.create_table(
        "user",
        sa.Column("id", user_id, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_table(
        "access_tokens",
        sa.Column("token", sa.String(43), primary_key=True),
        sa.Column("user_id", user_id, sa.ForeignKey("user.id", ondelete="cascade"), nullable=False),
        sa.Column("created_at", TIMESTAMPAware(timezone=True), nullable=False),
    )
    op.create_index("ix_access_tokens_created_at", "access_tokens", ["created_at"])
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", user_id, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_table(
        "source_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("owner_id", user_id, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(200), nullable=False),
        sa.Column("exact_url", sa.Text(), nullable=True),
        sa.Column("doi", sa.String(200), nullable=True),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rights_statement", sa.Text(), nullable=False),
        sa.Column("rights_decision", sa.String(32), nullable=False),
        sa.Column("declared_format", sa.String(32), nullable=False),
        sa.Column("expected_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.UniqueConstraint("project_id", "original_filename", "version"),
    )
    op.create_index("ix_source_records_project_id", "source_records", ["project_id"])
    op.create_index("ix_source_records_owner_id", "source_records", ["owner_id"])
    op.create_table(
        "raw_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("owner_id", user_id, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("source_records.id"), nullable=False, unique=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("client_mime", sa.String(100), nullable=False),
        sa.Column("detected_format", sa.String(32), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(150), nullable=False, unique=True),
        sa.Column("physical_metadata", sa.JSON(), nullable=False),
        sa.Column("validation_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raw_assets_project_id", "raw_assets", ["project_id"])
    op.create_index("ix_raw_assets_owner_id", "raw_assets", ["owner_id"])
    op.create_table(
        "account_usage",
        sa.Column("user_id", user_id, sa.ForeignKey("user.id"), primary_key=True),
        sa.Column("raw_bytes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "rate_windows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("client_key", sa.String(128), nullable=False),
        sa.Column("window_start", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("scope", "client_key", "window_start"),
    )
    op.create_table(
        "deletion_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False, unique=True),
        sa.Column("owner_id", user_id, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset_hashes", sa.JSON(), nullable=False),
        sa.Column("backup_purge_status", sa.String(40), nullable=False),
    )
    op.create_index("ix_deletion_receipts_owner_id", "deletion_receipts", ["owner_id"])


def downgrade() -> None:
    for table in (
        "deletion_receipts", "rate_windows", "account_usage", "raw_assets",
        "source_records", "projects", "access_tokens", "user",
    ):
        op.drop_table(table)
