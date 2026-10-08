"""Durable original-line survey custody. MAIN combines actual predecessors.

Revision ID: 0007_magnetic_line_artifacts
Revises: 0006_joint_artifacts

Isolated capsule, not searched by the older checkout's shared Alembic runner.
No predecessor alias, schema relabel, scientific pass or dispatcher activation.
"""
from alembic import op
import sqlalchemy as sa


revision = '0007_magnetic_line_artifacts'
down_revision = '0006_joint_artifacts'
branch_labels = None
depends_on = None


TABLES = ('magnetic_survey_intakes','magnetic_survey_exports','magnetic_survey_members',
          'magnetic_survey_attempts','magnetic_survey_admissions')


def upgrade() -> None:
    op.create_table('magnetic_survey_intakes',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('owner_id',sa.CHAR(36),sa.ForeignKey('user.id'),nullable=False),
        sa.Column('project_id',sa.String(36),sa.ForeignKey('projects.id'),nullable=False),
        sa.Column('role',sa.String(32),nullable=False),
        sa.Column('header_json',sa.JSON(),nullable=False),
        sa.Column('state',sa.String(24),nullable=False),
        sa.Column('reservation_bytes',sa.Integer(),nullable=False),
        sa.Column('retained_bytes',sa.Integer(),nullable=False),
        sa.Column('inventory',sa.JSON(),nullable=False),
        sa.Column('error_code',sa.String(80),nullable=True),
        sa.Column('asset_id',sa.String(36),sa.ForeignKey('raw_assets.id'),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint('reservation_bytes > 0'),sa.CheckConstraint('retained_bytes >= 0'),
        sa.CheckConstraint("state IN ('reserved','receiving','publication_uncertain','failed','published')"))
    op.create_index('ix_magnetic_survey_intakes_owner_id','magnetic_survey_intakes',['owner_id'])
    op.create_index('ix_magnetic_survey_intakes_project_id','magnetic_survey_intakes',['project_id'])
    op.create_table('magnetic_survey_admissions',
        sa.Column('job_id',sa.String(36),sa.ForeignKey('processing_jobs.id'),primary_key=True),
        sa.Column('start_json',sa.JSON(),nullable=False),
        sa.Column('source_receipts',sa.JSON(),nullable=False),
        sa.Column('authority_sha256',sa.String(64),nullable=False),
        sa.Column('reservation_bytes',sa.Integer(),nullable=False),
        sa.CheckConstraint('reservation_bytes > 0'))
    op.create_table('magnetic_survey_attempts',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('job_id',sa.String(36),sa.ForeignKey('processing_jobs.id'),nullable=False),
        sa.Column('ordinal',sa.Integer(),nullable=False),
        sa.Column('state',sa.String(24),nullable=False),
        sa.Column('worker_id',sa.String(100),nullable=False),
        sa.Column('started_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('finished_at',sa.DateTime(timezone=True),nullable=True),
        sa.Column('lifetime',sa.JSON(),nullable=True),
        sa.Column('retained_bytes',sa.Integer(),nullable=False),
        sa.Column('inventory',sa.JSON(),nullable=False),
        sa.UniqueConstraint('job_id','ordinal'),sa.CheckConstraint('ordinal > 0'),
        sa.CheckConstraint('retained_bytes >= 0'),
        sa.CheckConstraint("state IN ('claimed','running','drained','publication_uncertain','published')"))
    op.create_index('ix_magnetic_survey_attempts_job_id','magnetic_survey_attempts',['job_id'])
    op.create_table('magnetic_survey_members',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('attempt_id',sa.String(36),sa.ForeignKey('magnetic_survey_attempts.id'),nullable=False),
        sa.Column('relative_name',sa.String(240),nullable=False),
        sa.Column('byte_count',sa.Integer(),nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('kind',sa.String(16),nullable=False),
        sa.UniqueConstraint('attempt_id','relative_name'),sa.CheckConstraint('byte_count > 0'),
        sa.CheckConstraint("kind IN ('result','manifest','chunk','page','receipt')"))
    op.create_index('ix_magnetic_survey_members_attempt_id','magnetic_survey_members',['attempt_id'])
    op.create_table('magnetic_survey_exports',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('attempt_id',sa.String(36),sa.ForeignKey('magnetic_survey_attempts.id'),nullable=False),
        sa.Column('scope',sa.String(8),nullable=False),
        sa.Column('manifest_member_id',sa.String(36),sa.ForeignKey('magnetic_survey_members.id'),nullable=False),
        sa.Column('byte_count',sa.Integer(),nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("scope IN ('private','public')"),sa.CheckConstraint('byte_count > 0'))
    op.create_index('ix_magnetic_survey_exports_attempt_id','magnetic_survey_exports',['attempt_id'])


def downgrade() -> None:
    # Check every custody table BEFORE changing any table. No cascading data
    # loss; filesystem debt cannot be inferred absent from an empty Result.
    connection=op.get_bind()
    for table in TABLES:
        if connection.execute(sa.text(f'SELECT 1 FROM {table} LIMIT 1')).first() is not None:
            raise RuntimeError('m03_custody_retained: downgrade requires reviewed empty custody')
    for table in TABLES:
        op.drop_table(table)
