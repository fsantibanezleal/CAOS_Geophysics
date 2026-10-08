"""Real capsule DDL; explicitly NOT the combined 0004 -> 0007 one-head gate."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa

from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt, SurveyExportRecord, SurveyMember
from app.models import Base


def capsule():
    path=Path(__file__).resolve().parents[2]/'app/magnetic_line_survey_migrations/0007_magnetic_line_artifacts.py'
    spec=spec_from_file_location('m03_allocated_revision',path)
    module=module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_allocated_predecessor_is_literal_not_a_competing_head():
    version=capsule()
    assert version.revision=='0007_magnetic_line_artifacts'
    assert version.down_revision=='0006_joint_artifacts'
    assert version.branch_labels is None and version.depends_on is None


def test_real_ddl_roundtrip_constraints_and_refused_custody_loss(tmp_path):
    version=capsule()
    engine=sa.create_engine('sqlite:///'+(tmp_path/'owned-migration.sqlite3').as_posix())
    owned=(SurveyAdmission,SurveyAttempt,SurveyMember,SurveyExportRecord)
    names={model.__tablename__ for model in owned}
    with engine.begin() as connection:
        connection.execute(sa.text('PRAGMA foreign_keys=ON'))
        # Concrete older base tables, not fake 0004/5/6 revision placeholders.
        Base.metadata.create_all(connection,tables=[table for table in Base.metadata.sorted_tables if table.name not in names])
        baseline=set(sa.inspect(connection).get_table_names())
        with Operations.context(MigrationContext.configure(connection)):
            version.upgrade()
            assert set(sa.inspect(connection).get_table_names())==baseline|names
            inspector=sa.inspect(connection)
            for model in owned:
                columns={row['name']:row for row in inspector.get_columns(model.__tablename__)}
                assert set(columns)==set(model.__table__.columns.keys())
                for column in model.__table__.columns:
                    assert columns[column.name]['nullable']==column.nullable
                actual_fk={(tuple(row['constrained_columns']),row['referred_table'],tuple(row['referred_columns'])) for row in inspector.get_foreign_keys(model.__tablename__)}
                expected_fk={(tuple(fk.parent.name for fk in constraint.elements),constraint.referred_table.name,
                    tuple(fk.column.name for fk in constraint.elements)) for constraint in model.__table__.foreign_key_constraints}
                assert actual_fk==expected_fk
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(sa.text("INSERT INTO magnetic_survey_admissions VALUES ('missing','{}','{}',:sha,1)"),{'sha':'a'*64})
            # Actual retained evidence even without a published Result blocks
            # the whole downgrade, before any table is dropped.
            connection.execute(sa.text('PRAGMA defer_foreign_keys=ON'))
            connection.execute(sa.text("INSERT INTO magnetic_survey_admissions VALUES ('retained','{}','{}',:sha,34359738368)"),{'sha':'b'*64})
            with pytest.raises(RuntimeError,match='m03_custody_retained'):
                version.downgrade()
            assert set(sa.inspect(connection).get_table_names())==baseline|names
            assert connection.execute(sa.text('SELECT reservation_bytes FROM magnetic_survey_admissions')).scalar_one()==34359738368
            connection.execute(sa.text("DELETE FROM magnetic_survey_admissions WHERE job_id='retained'"))
            version.downgrade()
            assert set(sa.inspect(connection).get_table_names())==baseline
            version.upgrade()
            assert set(sa.inspect(connection).get_table_names())==baseline|names
    engine.dispose()
