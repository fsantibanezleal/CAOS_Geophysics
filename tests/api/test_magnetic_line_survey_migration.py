"""Real capsule DDL; explicitly NOT the combined 0004 -> 0007 one-head gate."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
import sqlalchemy as sa

from app.magnetic_line_survey_models import SurveyAdmission, SurveyAttempt, SurveyDatasetAttempt, SurveyExportRecord, SurveyMember, SurveyIntake
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
    owned=(SurveyAdmission,SurveyAttempt,SurveyMember,SurveyExportRecord,SurveyIntake,SurveyDatasetAttempt)
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


def test_sql_existing_foreign_owner_project_raw_and_export_attempt_refuse(tmp_path):
    """All parents exist: independence of valid IDs cannot grant composition."""
    from uuid import uuid4
    from app.models import User, Project, SourceRecord, RawAsset, ObservationDataset, ProcessingJob
    from sqlalchemy.orm import Session
    engine=sa.create_engine('sqlite:///'+(tmp_path/'composite.sqlite3').as_posix())
    with engine.begin() as connection:
        connection.execute(sa.text('PRAGMA foreign_keys=ON'))
        owned={model.__tablename__ for model in (SurveyAdmission,SurveyAttempt,SurveyMember,SurveyExportRecord,SurveyIntake,SurveyDatasetAttempt)}
        Base.metadata.create_all(connection,tables=[table for table in Base.metadata.sorted_tables if table.name not in owned])
        with Operations.context(MigrationContext.configure(connection)):capsule().upgrade()
    pairs=[]
    with Session(engine) as session:
        for index in range(2):
            owner=uuid4(); project,source,raw,dataset,job=[str(uuid4()) for _ in range(5)]
            session.add(User(id=owner,email=f'owner{index}@example.test',hashed_password='fixture',is_active=True,is_verified=True,is_superuser=False))
            session.flush()
            session.add(Project(id=project,owner_id=owner,name='owned'))
            session.flush()
            session.add(SourceRecord(id=source,project_id=project,owner_id=owner,original_filename='raw.csv',version=1,
                provider='Owner',rights_statement='Private test bytes',rights_decision='mirror',declared_format='csv',sha256='a'*64,attribution='Owner'))
            session.flush()
            session.add(RawAsset(id=raw,project_id=project,owner_id=owner,source_id=source,filename='raw.csv',client_mime='text/csv',
                detected_format='csv',byte_count=1,sha256='a'*64,storage_key=raw,physical_metadata={}))
            session.flush()
            session.add(ObservationDataset(id=dataset,project_id=project,owner_id=owner,raw_asset_id=raw,version=1,parser_version='fixture',
                modality='fixture',row_count=1,raw_sha256='a'*64,sha256='b'*64,byte_count=1,storage_key=dataset))
            session.flush()
            session.add(ProcessingJob(id=job,project_id=project,owner_id=owner,dataset_id=dataset,dataset_sha256='b'*64,
                method_id='fixture',state='queued',cancel_requested=False,request_json={},request_sha256='c'*64,preflight={}))
            session.commit();pairs.append((owner,project,raw,dataset,job))
        owner,project,raw,dataset,job=pairs[0]
        for field in ('owner','project','raw'):
            values=dict(owner=owner,project=project,raw=raw)
            values[field]=pairs[1][{'owner':0,'project':1,'raw':2}[field]]
            session.add(SurveyIntake(id=str(uuid4()),owner_id=values['owner'],project_id=values['project'],asset_id=values['raw'],
                role='original_csv',header_json={},state='failed',reservation_bytes=32,retained_bytes=7,inventory=[]))
            with pytest.raises(sa.exc.IntegrityError):session.commit()
            session.rollback()
        # NULL unpublished raw still requires matching project ownership.
        session.add(SurveyIntake(id=str(uuid4()),owner_id=pairs[1][0],project_id=project,
            role='original_csv',header_json={},state='reserved',reservation_bytes=32,retained_bytes=0,inventory=[]))
        with pytest.raises(sa.exc.IntegrityError):session.commit()
        session.rollback()
        attempts=[str(uuid4()),str(uuid4())]
        for ordinal,attempt in enumerate(attempts,1):
            session.add(SurveyAttempt(id=attempt,job_id=job,ordinal=ordinal,state='drained',worker_id='fixture',retained_bytes=7,inventory=[]))
        session.commit()
        member=str(uuid4())
        session.add(SurveyMember(id=member,attempt_id=attempts[0],relative_name='manifest.json',byte_count=7,sha256='a'*64,kind='manifest'))
        session.commit()
        session.add(SurveyExportRecord(id=str(uuid4()),attempt_id=attempts[1],scope='private',manifest_member_id=member,byte_count=7,sha256='a'*64))
        with pytest.raises(sa.exc.IntegrityError):session.commit()
        session.rollback()
        session.add(SurveyExportRecord(id=str(uuid4()),attempt_id=attempts[0],scope='private',manifest_member_id=member,byte_count=7,sha256='a'*64))
        session.commit()
        assert session.execute(sa.text('PRAGMA foreign_key_check')).all()==[]
    engine.dispose()
