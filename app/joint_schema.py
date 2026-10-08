"""Additive schema body for the parent migration after actual M08 revision.

The parent Alembic revision owns version advancement. This leaf never upgrades
an older schema, changes the canonical head or silently creates missing tables.
"""
from sqlalchemy import inspect, text

from app.joint_models import JointDatasetSource

PREDECESSOR = '0004_waveform_artifacts'


def upgrade(operations):
    connection = operations.get_bind()
    if connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() != PREDECESSOR:
        raise RuntimeError('joint schema requires the committed M08 predecessor')
    inspector = inspect(connection)
    expected = {
        'waveform_dataset_sources':({'dataset_id','role','asset_id','source_id','raw_sha256','raw_bytes','source_version'},
            {('dataset_id','observation_datasets','id'),('asset_id','raw_assets','id'),('source_id','source_records','id')}),
        'waveform_result_artifacts':({'job_id','name','storage_key','byte_count','sha256'},
            {('job_id','processing_jobs','id')}),
    }
    for table,(columns,foreign) in expected.items():
        if table not in inspector.get_table_names() or {c['name'] for c in inspector.get_columns(table)} != columns:
            raise RuntimeError('joint schema requires actual M08 predecessor tables')
        actual = {(f['constrained_columns'][0],f['referred_table'],f['referred_columns'][0])
                  for f in inspector.get_foreign_keys(table) if len(f['constrained_columns'])==len(f['referred_columns'])==1}
        if actual != foreign: raise RuntimeError('joint schema requires actual M08 predecessor foreign keys')
    JointDatasetSource.__table__.create(connection, checkfirst=False)
