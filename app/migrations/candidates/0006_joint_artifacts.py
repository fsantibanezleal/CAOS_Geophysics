"""Allocated joint native roots/artifacts, explicit candidate registry only."""
from alembic import op

from app import joint_successor

revision = '0006_joint_artifacts'
down_revision = '0005_physical_forest'
branch_labels = None
depends_on = None


def upgrade():
    joint_successor.upgrade(op)


def downgrade():
    joint_successor.downgrade(op)
