"""Explicit allocated-family registration, never schema discovery or a solve."""
from datetime import timezone

from sqlalchemy import text

from app import joint_contract as native
from app.joint_datasets import SCHEMA, validate_dataset
from app.joint_successor import REVISION, ROOT
from app.models import ObservationDataset, RawAsset, SourceRecord


async def register_root(session, dataset, payload, *, expected_head=REVISION):
    """Insert family/root in the caller's write transaction, without committing.

    The canonical mount selects this service explicitly. A reviewed successor
    may pass its exact installed head; no client parameter controls that choice.
    No file is copied/removed and no charge, acceptance or producer is inferred.
    """
    if not session.in_transaction(): raise ValueError('joint_root_write_transaction_required')
    if (await session.execute(text('PRAGMA foreign_keys'))).scalar_one()!=1:
        raise ValueError('joint_root_foreign_keys_required')
    if (await session.execute(text('SELECT version_num FROM alembic_version'))).scalars().all()!=[expected_head]:
        raise ValueError('joint_root_exact_allocated_head_required')
    sql = (await session.execute(text("SELECT sql FROM sqlite_master WHERE name='observation_datasets' AND type='table'"))).scalar_one()
    if sql.count(ROOT)!=1: raise ValueError('joint_root_exact_dictionary_required')
    validate_dataset(payload,dataset)
    raw = await session.get(RawAsset,dataset.raw_asset_id)
    source = None if raw is None else await session.get(SourceRecord,raw.source_id)
    if raw is None or source is None: raise ValueError('joint_root_primary_source_missing')
    binding = native.source_identity(raw,source,owner_id=dataset.owner_id,project_id=dataset.project_id)
    declared = payload['members']['development']['request.json']
    if any(binding[k]!=declared[k] for k in binding): raise ValueError('joint_root_primary_source_binding')
    if (dataset.version!=1 or dataset.raw_sha256!=raw.sha256 or payload['schema']!=SCHEMA
            or dataset.created_at.tzinfo is None): raise ValueError('joint_root_literal_identity')
    stamp=dataset.created_at.astimezone(timezone.utc)
    delta=stamp-stamp.replace(year=1970,month=1,day=1,hour=0,minute=0,second=0,microsecond=0)
    micros=delta.days*86400000000+delta.seconds*1000000+delta.microseconds
    if not 0<=micros<=9007199254740991: raise ValueError('joint_root_timestamp')
    await session.execute(text(
        'INSERT INTO physical_dataset_families (root_dataset_id,raw_asset_id,project_id,owner_id,parser_version,state,next_ordinal,published_count,reserved_count,created_us) '
        "VALUES (:id,:raw_asset_id,:project_id,:owner_id,:parser_version,'published',2,1,0,:micros)"),
        {'id':dataset.id,'raw_asset_id':dataset.raw_asset_id,'project_id':dataset.project_id,
         'owner_id':str(dataset.owner_id),'parser_version':native.PARSER,'micros':micros})
    values={key:getattr(dataset,key) for key in ('id','project_id','raw_asset_id','version','parser_version','modality','row_count','raw_sha256','sha256','byte_count','storage_key')}
    values.update(owner_id=str(dataset.owner_id),created_at=stamp.replace(tzinfo=None).isoformat(sep=' '),payload_schema=SCHEMA)
    await session.execute(text(
        'INSERT INTO observation_datasets (id,project_id,owner_id,raw_asset_id,version,parser_version,modality,row_count,raw_sha256,sha256,byte_count,storage_key,created_at,kind,root_dataset_id,parent_dataset_id,payload_schema) '
        "VALUES (:id,:project_id,:owner_id,:raw_asset_id,:version,:parser_version,:modality,:row_count,:raw_sha256,:sha256,:byte_count,:storage_key,:created_at,'root',:id,NULL,:payload_schema)"),values)
    return await session.get(ObservationDataset,dataset.id)
