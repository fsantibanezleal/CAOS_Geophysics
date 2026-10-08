"""Allocated joint successor body, not automatic runtime schema admission."""
from __future__ import annotations

import hashlib
import json

from sqlalchemy.schema import CreateTable

from app.joint_models import JointDatasetSource, JointResultArtifact

PREDECESSOR = '0005_physical_forest'
REVISION = '0006_joint_artifacts'
PREDECESSOR_DDL = 'b35d30cbbc77e7c26ad4d4c0efa7d2365cdd582e7e22979ca1ae0461ef1dacb4'
ROOT = "(kind='root' AND parser_version='m11-native-members/v1' AND modality='joint_gravity_magnetic_native' AND payload_schema='geophysics.joint-native-dataset/v1')"
BOUNDARY = ') IS TRUE),\nCONSTRAINT fk_dataset_family'
TABLES = (JointDatasetSource.__table__, JointResultArtifact.__table__)


def ddl_rows(connection):
    return [tuple(r) for r in connection.exec_driver_sql(
        'SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name').fetchall()]


def ddl_digest(rows):
    return hashlib.sha256(json.dumps(rows,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def _environment(operations, head):
    context = operations.get_context()
    db = operations.get_bind()
    if (db.dialect.name != 'sqlite' or not context.impl.transactional_ddl
            or not db.in_transaction() or db.exec_driver_sql('PRAGMA foreign_keys').scalar() != 0
            or db.exec_driver_sql('PRAGMA journal_mode').scalar() not in ('delete','memory')):
        raise ValueError('joint_requires_explicit_transactional_rollback_registry')
    if db.exec_driver_sql('SELECT version_num FROM alembic_version').scalars().all() != [head]:
        raise ValueError('joint_requires_exact_allocated_head')
    if db.exec_driver_sql('PRAGMA integrity_check').scalar() != 'ok' or db.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
        raise ValueError('joint_inconsistent_predecessor')
    tables = db.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars().all()
    if sum(db.exec_driver_sql(f'SELECT count(*) FROM "{t}"').scalar() for t in tables)>100000:
        raise ValueError('joint_migration_row_limit')
    if db.exec_driver_sql("SELECT id FROM processing_jobs WHERE state IN ('queued','running') LIMIT 1").first():
        raise ValueError('joint_active_job_refusal')
    return db


def _cut(operations, name):
    callback = operations.get_context().config.attributes.get('m11_successor_failure_cut')
    if callback is not None: callback(name)  # Explicit isolated test control only.


def _dataset_sql(db):
    return db.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='observation_datasets'").scalar_one()


def _extend(sql):
    if sql.count(BOUNDARY)!=1 or ROOT in sql:
        raise ValueError('joint_exact_root_dictionary_required')
    return sql.replace(BOUNDARY,' OR '+ROOT+BOUNDARY,1)


def _restore(sql):
    marker = ' OR '+ROOT+BOUNDARY
    if sql.count(marker)!=1: raise ValueError('joint_exact_root_dictionary_required')
    return sql.replace(marker,BOUNDARY,1)


def _rebuild(operations, db, sql):
    prefix = 'CREATE TABLE "observation_datasets"'
    if not sql.startswith(prefix): raise ValueError('joint_exact_dataset_ddl_required')
    indexes = db.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='observation_datasets' AND sql IS NOT NULL ORDER BY name").scalars().all()
    db.exec_driver_sql(sql.replace(prefix,'CREATE TABLE _joint_candidate_datasets',1))
    db.exec_driver_sql('INSERT INTO _joint_candidate_datasets SELECT * FROM observation_datasets')
    _cut(operations,'dataset_copy')
    db.exec_driver_sql('DROP TABLE observation_datasets')
    db.exec_driver_sql('ALTER TABLE _joint_candidate_datasets RENAME TO observation_datasets')
    for index in indexes: db.exec_driver_sql(index)
    _cut(operations,'dataset_rename')


def upgrade(operations):
    db = _environment(operations,PREDECESSOR)
    if ddl_digest(ddl_rows(db)) != PREDECESSOR_DDL:
        raise ValueError('joint_unknown_predecessor_ddl')
    _rebuild(operations,db,_extend(_dataset_sql(db)))
    for table in TABLES:
        table.create(db,checkfirst=False)
        _cut(operations,table.name)
    if db.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
        raise ValueError('joint_foreign_key_check_failed')
    _cut(operations,'checked')


def downgrade(operations):
    db = _environment(operations,REVISION)
    # Verify the exact added ORM DDL and inverse predecessor projection before
    # touching any row. An unknown new constraint/index/trigger is not adopted.
    rows = ddl_rows(db)
    if {(kind,name) for kind,name,target,_ in rows if target in {t.name for t in TABLES}} != {('table',t.name) for t in TABLES}:
        raise ValueError('joint_unknown_successor_ddl')
    for table in TABLES:
        actual = db.exec_driver_sql('SELECT sql FROM sqlite_master WHERE type=\'table\' AND name=?',(table.name,)).scalar_one()
        expected = str(CreateTable(table).compile(dialect=db.dialect)).strip()
        if actual.strip()!=expected: raise ValueError('joint_unknown_successor_ddl')
    restored = _restore(_dataset_sql(db))
    projection = [(kind,name,target,restored if name=='observation_datasets' else sql)
                  for kind,name,target,sql in rows if target not in {t.name for t in TABLES}]
    if ddl_digest(projection)!=PREDECESSOR_DDL: raise ValueError('joint_unknown_successor_ddl')
    if (any(db.exec_driver_sql(f'SELECT 1 FROM {t.name} LIMIT 1').first() for t in TABLES)
            or db.exec_driver_sql("SELECT 1 FROM observation_datasets WHERE parser_version='m11-native-members/v1' OR modality='joint_gravity_magnetic_native' LIMIT 1").first()
            or db.exec_driver_sql("SELECT 1 FROM physical_dataset_families WHERE parser_version='m11-native-members/v1' LIMIT 1").first()
            or db.exec_driver_sql("SELECT 1 FROM processing_jobs WHERE method_id='joint.gravity-magnetic-native/v1' LIMIT 1").first()):
        raise ValueError('joint_downgrade_retained_custody_refused')
    for table in reversed(TABLES):
        table.drop(db,checkfirst=False)
        _cut(operations,'drop_'+table.name)
    _rebuild(operations,db,restored)
    if ddl_digest(ddl_rows(db))!=PREDECESSOR_DDL or db.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
        raise ValueError('joint_downgrade_predecessor_binding_failed')
    _cut(operations,'checked')
