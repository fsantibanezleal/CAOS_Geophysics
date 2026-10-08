"""Same-transaction hooks for the one original project DELETE.

No route, connection, commit, rename, purge or scientific computation here.
Preparation is committed by the caller before its first original rename.
The caller holds both original-worker and all-writer exclusion throughout.
"""

from app.physical_contract import M, byte_sha, canonical, digest, integer, require, sha, uuid
from app.physical_current_custody import validate_current_custody
from app.physical_deleted_inventory import project_inventory, save_current_tombstone
from app.physical_forest import SUCCESSOR_DDL
from app.physical_successor import REVISION, ddl_sha256


def _transaction(connection):
    require(connection.in_transaction and connection.execute('PRAGMA foreign_keys').fetchone()==(1,)
            and connection.execute('SELECT version_num FROM alembic_version').fetchall()==[(REVISION,)]
            and ddl_sha256(connection)==SUCCESSOR_DDL,'project_delete_native_transaction')


def original_slots(inventory):
    """Exact original files, not retained stages or profile archives."""
    from app.waveform_contract import SCRATCH
    records=([(r['asset_id'],'raw_delete','deleting_raw',r['asset_id'],1024*M,r['bytes'],r['sha256'])
              for r in inventory['raw_assets']] +
        [(r['dataset_id'],'dataset_copy','deleting_derived',f"datasets/{r['dataset_id']}.json",64*M,r['bytes'],r['sha256'])
         for r in inventory['datasets']] +
        [(r['job_id'],'result_copy','deleting_derived',f"results/{r['job_id']}.json",64*M,r['result_bytes'],r['result_sha256'])
         for r in inventory['jobs'] if r['state']=='succeeded'] +
        [(r['job_id'],'result_copy','deleting_derived',f"waveforms/{r['job_id']}/{r['name']}",SCRATCH,r['bytes'],r['sha256'])
         for r in inventory['waveform_artifacts']])
    require(len(records)<=4096,'project_delete_file_cap')
    return [dict(ordinal=i,artifact_id=identifier,role=role,location=location,leaf=leaf,
                 max_bytes=cap,actual_bytes=count,actual_sha256=hash_value)
            for i,(identifier,role,location,leaf,cap,count,hash_value) in enumerate(records,1)]


def prepare_project_deletion(connection, *, files, owner_id, project_id, batch_id, receipt_id,
                             created_us, expected_source_policy_sha256, approved_manifests,
                             approved_installations, native_metadata, profile_records):
    """Durable exact declaration, zero duplicate file charge before row removal.

    The complete source-positive classifier must pass first. No selected-family
    success can bypass an unrelated corrupt project, unknown file or active job.
    Returns the original receipt projection and immutable custody declaration.
    """
    from app.physical_classifier import classify_snapshot
    _transaction(connection)
    for identifier in (owner_id,project_id,batch_id,receipt_id): uuid(identifier)
    integer(created_us); sha(expected_source_policy_sha256)
    classified=classify_snapshot(connection,files,approved_manifests=approved_manifests,
        approved_installations=approved_installations,native_metadata=native_metadata,
        expected_source_policy_sha256=expected_source_policy_sha256)
    require(classified.classification=='coherent_committed','project_delete_unresolved_snapshot:'+classified.reason)
    inventory=project_inventory(connection,owner_id=owner_id,project_id=project_id,
        source_policy_sha256=expected_source_policy_sha256,profile_records=profile_records)
    slots=original_slots(inventory)
    custody=dict(schema='geophysics.physical-custody/v2',batch_id=batch_id,owner_id=owner_id,project_id=project_id,
        origin_kind='project_deletion',origin_id=project_id,stage_id=None,deletion_receipt_id=receipt_id,
        raw_asset_id=None,raw_sha256=None,raw_bytes=None,parser_version=None,method_id=None,
        capacity_bytes=max(1,sum(s['actual_bytes'] for s in slots)),initial_files=slots,removed_ordinals=[])
    measured=validate_current_custody(custody)
    header={k:v for k,v in custody.items() if k not in ('schema','initial_files','removed_ordinals')}
    header.update(state='sealed',charged_bytes=0,inventory_bytes=canonical(custody),inventory_sha256=digest(custody),
                  created_us=created_us,sealed_us=created_us,removed_us=None)
    connection.execute(f"INSERT INTO physical_custody_batches({','.join(header)}) VALUES({','.join('?' for _ in header)})",
                       tuple(header.values()))
    for slot in slots:
        row=dict(slot,batch_id=batch_id,state='present')
        connection.execute(f"INSERT INTO physical_custody_files({','.join(row)}) VALUES({','.join('?' for _ in row)})",tuple(row.values()))
    inventory['custody'].append(dict(batch_id=batch_id,origin_kind='project_deletion',origin_id=project_id,
                                    initial_inventory_sha256=measured['initial_inventory_sha256']))
    inventory['custody'].sort(key=lambda r:r['batch_id'])
    # Full immutable returned projection is carried only by the trusted caller;
    # recovery derives current identities from original rows, never adopts this
    # return object or a guessed HTTP payload as authority.
    return dict(inventory=inventory,custody=custody)


def retire_project_forest_relations(connection, *, owner_id, project_id):
    """Before original job DELETE, remove only exact owned RESTRICT children."""
    _transaction(connection); uuid(owner_id); uuid(project_id)
    require(connection.execute('SELECT owner_id FROM projects WHERE id=?',(project_id,)).fetchone()==(owner_id,),
            'project_delete_owner')
    require(not connection.execute('SELECT 1 FROM physical_publication_intents WHERE owner_id=? AND project_id=?',
                                  (owner_id,project_id)).fetchone(),'project_delete_active_intent')
    for table in ('physical_dataset_productions','physical_dataset_edges','physical_job_controls'):
        connection.execute(f'DELETE FROM {table} WHERE owner_id=? AND project_id=?',(owner_id,project_id))


def retire_project_forest_families(connection, *, owner_id, project_id):
    """After original dataset DELETE and before original raw DELETE."""
    _transaction(connection); uuid(owner_id); uuid(project_id)
    require(not connection.execute('SELECT 1 FROM observation_datasets WHERE owner_id=? AND project_id=?',
                                  (owner_id,project_id)).fetchone(),'project_delete_dataset_still_live')
    connection.execute('DELETE FROM physical_dataset_families WHERE owner_id=? AND project_id=?',(owner_id,project_id))


def transfer_project_deletion(connection, *, inventory, custody, expected_source_policy_sha256, approved_installations):
    """Receipt/native JSON/extension/debt transfer in the original final commit."""
    _transaction(connection)
    measured=validate_current_custody(custody)
    require(custody['origin_kind']=='project_deletion' and not custody['removed_ordinals'],'project_delete_custody')
    cursor=connection.execute('SELECT * FROM physical_custody_batches WHERE batch_id=?',(custody['batch_id'],))
    native=cursor.fetchone()
    require(native is not None,'project_delete_preparation_missing')
    row=dict(zip((c[0] for c in cursor.description),native))
    require(row['state']=='sealed' and row['charged_bytes']==0 and row['inventory_bytes']==canonical(custody)
            and row['inventory_sha256']==byte_sha(canonical(custody)),'project_delete_preparation_changed')
    body=save_current_tombstone(connection,receipt_id=custody['deletion_receipt_id'],inventory=inventory,
        expected_source_policy_sha256=expected_source_policy_sha256,approved_installations=approved_installations)
    # Empty project is an empty recognized preparation, never a zero-byte file.
    empty=not custody['initial_files']
    connection.execute('UPDATE physical_custody_batches SET state=?,charged_bytes=?,removed_us=? WHERE batch_id=?',
        ('removed' if empty else 'cleanup_pending',measured['retained_bytes'],row['sealed_us'] if empty else None,custody['batch_id']))
    return body


def cleanup_project_deletion_file(connection,files,*,owner_id,batch_id,ordinal,removed_us):
    """Closed original-transaction cleanup operation; no callback/SQL from DTO."""
    _transaction(connection)
    require(connection.execute('SELECT origin_kind FROM physical_custody_batches WHERE batch_id=? AND owner_id=?',
        (batch_id,owner_id)).fetchone()==('project_deletion',),'project_delete_cleanup_origin')
    from app.physical_debt import cleanup_custody_file
    return cleanup_custody_file(connection,files,owner_id=owner_id,batch_id=batch_id,ordinal=ordinal,
                               removed_us=removed_us,_caller_transaction=True)
