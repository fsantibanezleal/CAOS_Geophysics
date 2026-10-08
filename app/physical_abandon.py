"""Abandon a verified prepared root, never adopt or delete its installed copy.

Caller holds independently acquired exclusive exclusion after fresh complete
classification. This transaction transfers literal debt and retires only an
empty pending family. It does not replace full inventory or native admission.
"""

from app.physical_contract import byte_sha, canonical, integer, require, uuid, validate_custody
from app.physical_debt import begin_ledger
from app.physical_forest import _row
from app.physical_persistence import M
from app.physical_roots import _verified


def abandon_root(connection, files, *, owner_id, project_id, intent_id,
                 abandon_batch_id, abandoned_us, failure_cut=None):
    for value in (owner_id,project_id,intent_id,abandon_batch_id):
        uuid(value)
    integer(abandoned_us)
    begin_ledger(connection)
    try:
        intent=_row(connection,'SELECT * FROM physical_publication_intents WHERE intent_id=? AND owner_id=? AND project_id=?',
                    (intent_id,owner_id,project_id))
        root=intent['root_dataset_id']
        require(intent['kind']=='root' and intent['phase']=='prepared' and intent['ordinal']==1
                and intent['stage_id']==intent['child_dataset_id']==root
                and intent['parser_version']=='gravity-stations-json/v1'
                and intent['permanent_reservation_bytes']==16*M
                and all(intent[k] is None for k in ('job_id','parent_dataset_id','parent_dataset_sha256','request_sha256')),
                'physical_abandon_root_intent')
        require(not connection.execute('SELECT 1 FROM observation_datasets WHERE root_dataset_id=? OR id=?',(root,root)).fetchone(),
                'physical_abandon_root_already_published')
        family=_row(connection,'SELECT * FROM physical_dataset_families WHERE root_dataset_id=?',(root,))
        require((family['owner_id'],family['project_id'],family['raw_asset_id'],family['parser_version'],
                 family['state'],family['next_ordinal'],family['published_count'],family['reserved_count']) ==
                (owner_id,project_id,intent['raw_asset_id'],'gravity-stations-json/v1','pending',2,0,1),
                'physical_abandon_root_family')
        require(connection.execute('SELECT count(*) FROM physical_publication_intents WHERE root_dataset_id=?',(root,)).fetchone()==(1,),
                'physical_abandon_root_other_intent')
        raw,stage,body,_=_verified(connection,files,owner_id,project_id,intent['raw_asset_id'],root)
        target=_row(connection,'SELECT * FROM physical_publication_targets WHERE intent_id=?',(intent_id,))
        require((target['kind'],target['artifact_id'],target['storage_key'],target['bytes'],target['sha256']) ==
                ('dataset',root,f'derived/{owner_id}/{project_id}/datasets/{root}.json',len(body),byte_sha(body)),
                'physical_abandon_root_target')
        installed=False
        try:
            actual=files.read(target['storage_key'],cap=16*M,expected_bytes=len(body),expected_sha256=byte_sha(body))
        except FileNotFoundError:
            # Only a proven precommit target may be absent. This is NOT a
            # cleanup removed-ordinal acknowledgement or generic charge relief.
            pass
        else:
            require(actual==body,'physical_abandon_root_installed_copy')
            installed=True
        if installed:
            slot=dict(ordinal=1,role='dataset_copy',location='pending_target',artifact_id=root,
                      leaf=target['storage_key'],max_bytes=16*M,actual_bytes=len(body),actual_sha256=byte_sha(body))
            inventory=dict(schema='geophysics.physical-custody/v1',batch_id=abandon_batch_id,owner_id=owner_id,
                project_id=project_id,origin_kind='publication_abandon',origin_id=intent_id,stage_id=None,
                deletion_receipt_id=None,raw_asset_id=raw['id'],raw_sha256=raw['sha256'],raw_bytes=raw['byte_count'],
                parser_version='gravity-stations-json/v1',method_id=None,capacity_bytes=16*M,
                initial_files=[slot],removed_ordinals=[])
            charge=validate_custody(inventory)['retained_bytes']
            encoded=canonical(inventory)
            header={k:v for k,v in inventory.items() if k not in ('schema','initial_files','removed_ordinals')}
            header.update(state='cleanup_pending',charged_bytes=charge,inventory_bytes=encoded,
                          inventory_sha256=byte_sha(encoded),created_us=abandoned_us,sealed_us=abandoned_us,removed_us=None)
            connection.execute(f"INSERT INTO physical_custody_batches({','.join(header)}) VALUES({','.join('?' for _ in header)})",
                               tuple(header.values()))
            entry=dict(slot,batch_id=abandon_batch_id,state='present')
            connection.execute(f"INSERT INTO physical_custody_files({','.join(entry)}) VALUES({','.join('?' for _ in entry)})",
                               tuple(entry.values()))
        connection.execute("UPDATE physical_custody_batches SET state='cleanup_pending' WHERE batch_id=?",(stage['batch_id'],))
        if failure_cut:
            failure_cut('debt')
        connection.execute('DELETE FROM physical_publication_targets WHERE intent_id=?',(intent_id,))
        connection.execute('DELETE FROM physical_publication_intents WHERE intent_id=?',(intent_id,))
        connection.execute('DELETE FROM physical_dataset_families WHERE root_dataset_id=?',(root,))
        if failure_cut:
            failure_cut('retired')
        require(not connection.execute('PRAGMA foreign_key_check').fetchall(),'physical_abandon_foreign_keys')
        connection.commit()
        return dict(installed_targets=int(installed),stage_debt_bytes=stage['charged_bytes'],
                    installed_debt_bytes=len(body) if installed else 0)
    except BaseException:
        connection.rollback()
        raise
