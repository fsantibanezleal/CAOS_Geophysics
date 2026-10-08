"""Correction ancestry and same-terminal-commit publication, no numerical solve.

Native exclusion/full namespace classification precede this transaction. The
isolated ledger is not production WAL admission; unknown bytes stay preserved.
Runtime registration and aggregate telemetry come from the trusted supervisor.
"""

from app.physical_contract import (
    CORRECTION, M, byte_sha, canonical, decode_source, digest, fields, instant, require, uuid,
)
from app.physical_debt import begin_ledger, sealed_stage
from app.physical_forest import _row, _parent_chain, _targets
from app.physical_producer import verify_correction_producer
from app.physical_wire import SOURCE_KEYS, parse_root, root_envelope, scientific_digest


def decode(body, cap):
    return decode_source([body],max_bytes=cap,depth=32,nodes=2250000)


def _dataset_body(files, row):
    key=f"derived/{row['owner_id']}/{row['project_id']}/datasets/{row['id']}.json"
    require(row['storage_key']==key,'physical_publication_dataset_key')
    return files.read(key,cap=16*M,expected_bytes=row['byte_count'],expected_sha256=row['sha256'])


def _snapshot(child, child_body, job, production, manifest):
    receipt=child['payload']['receipt']
    return dict(schema='geophysics.physical-parent-production/v1',
                **{k:child[k] for k in ('owner_id','project_id','root_dataset_id','raw_asset_id','raw_sha256','raw_bytes')},
                output_dataset_id=child['dataset_id'],output_dataset_version=child['version'],
                output_dataset_sha256=byte_sha(child_body),output_dataset_bytes=len(child_body),
                job_id=job['id'],method_id=job['method_id'],state=job['state'],scientific_verdict=production['scientific_verdict'],
                input_dataset_id=job['dataset_id'],input_dataset_sha256=job['dataset_sha256'],
                **{k:production[k] for k in ('request_sha256','submitted_parameters_sha256','scientific_request_sha256',
                    'result_sha256','result_bytes','module_manifest_sha256','adapter_result_sha256','adapter_receipt_sha256',
                    'core_result_sha256','submitted_config_sha256','normalized_config_sha256')},
                module_manifest=manifest,adapter_receipt=receipt)


def audit_correction_ancestry(connection, files, parent, *, approved_manifests):
    """Audit every producing edge to an exact retained original root.

    No fresh/global inventory or writer-exclusion receipt is manufactured by
    this local audit. Transforms cannot become correction/transform parents.
    """
    require(type(approved_manifests) is dict,'physical_publication_registration')
    owner,project=parent['owner_id'],parent['project_id']
    _parent_chain(connection,parent,owner,project)
    chain,current=[],parent
    while current['kind']!='root':
        chain.append(current)
        current=_row(connection,'SELECT * FROM observation_datasets WHERE id=?',(current['parent_dataset_id'],))
    require(current['parser_version']=='gravity-stations-json/v1' and current['payload_schema']=='gravity-stations-1'
            and current['modality']=='gravity_physical_station','physical_publication_root_tuple')
    raw=_row(connection,'SELECT * FROM raw_assets WHERE id=? AND owner_id=? AND project_id=?',
             (current['raw_asset_id'],owner,project))
    source=_row(connection,'SELECT * FROM source_records WHERE id=? AND owner_id=? AND project_id=?',
                (raw['source_id'],owner,project))
    require(_row(connection,'SELECT owner_id FROM projects WHERE id=?',(project,))['owner_id']==owner,
            'physical_publication_owner')
    require(raw['detected_format']==source['declared_format']=='gravity_stations_json'
            and raw['validation_status']=='raw_metadata_checked' and source['private_storage_permission']=='attested'
            and source['rights_decision']=='mirror' and source['sha256']==raw['sha256']
            and source['expected_bytes'] in (None,raw['byte_count']),'physical_publication_source')
    require(raw['storage_key']==f"projects/{owner}/{project}/{raw['id']}",'physical_publication_raw_key')
    original=files.read(raw['storage_key'],cap=16*M,expected_bytes=raw['byte_count'],expected_sha256=raw['sha256'])
    scientific=parse_root([original])
    body=_dataset_body(files,current)
    root=root_envelope([body])
    require(canonical(root)==body and
            (root['dataset_id'],root['owner_id'],root['project_id'],root['raw_asset_id'],root['raw_sha256'],root['raw_bytes'])==
            (current['id'],owner,project,raw['id'],raw['sha256'],raw['byte_count']) and
            canonical(root['payload'],scientific=True)==canonical(scientific,scientific=True) and
            canonical(root['source'])==canonical({k:source[k] for k in SOURCE_KEYS.split()}) and
            current['raw_sha256']==raw['sha256'] and current['row_count']==len(scientific['stations']),
            'physical_publication_original_root')
    require(not connection.execute('SELECT 1 FROM physical_dataset_edges WHERE child_dataset_id=?',(current['id'],)).fetchone()
            and not connection.execute('SELECT 1 FROM physical_dataset_productions WHERE child_dataset_id=?',(current['id'],)).fetchone(),
            'physical_publication_root_has_producer')
    previous=None
    for row in reversed(chain):
        child_body=_dataset_body(files,row)
        child=decode(child_body,16*M)
        require((child['dataset_id'],child['version'],child['owner_id'],child['project_id'],child['raw_asset_id'],
                 child['raw_sha256'],child['root_dataset_id'],child['parent_dataset_id'],child['payload_schema'],child['modality'])==
                tuple(row[k] for k in ('id','version','owner_id','project_id','raw_asset_id','raw_sha256','root_dataset_id',
                                      'parent_dataset_id','payload_schema','modality')), 'physical_publication_parent_envelope')
        production=_row(connection,'SELECT * FROM physical_dataset_productions WHERE child_dataset_id=?',(row['id'],))
        job=_row(connection,'SELECT * FROM processing_jobs WHERE id=?',(production['job_id'],))
        control=_row(connection,'SELECT * FROM physical_job_controls WHERE job_id=?',(job['id'],))
        require(control['permanent_reservation_bytes']==0,'physical_publication_parent_reservation')
        manifest=decode(control['module_manifest_bytes'],65536)
        approved=approved_manifests.get(digest(manifest))
        result=files.read(job['result_key'],cap=64*M,expected_bytes=job['result_bytes'],expected_sha256=job['result_sha256'])
        snapshot=_snapshot(child,child_body,job,production,manifest)
        verify_correction_producer(snapshot,input_bytes=body,child_bytes=child_body,request_bytes=control['request_bytes'],
                                   result_bytes=result,approved_manifest=approved,job=job,production=production)
        request=decode(control['request_bytes'],34*M)
        require(canonical(request['parent_production'])==canonical(previous) and
                control['module_manifest_sha256']==snapshot['module_manifest_sha256'] and
                control['submitted_parameters_sha256']==snapshot['submitted_parameters_sha256'] and
                control['scientific_request_sha256']==snapshot['scientific_request_sha256'] and
                (control['parent_production_bytes'] is None if previous is None else
                 control['parent_production_bytes']==canonical(previous)), 'physical_publication_parent_snapshot')
        require(canonical(decode(job['request_json'].encode('utf-8'),35*M))==canonical(request) and
                request['admission_receipt_sha256']==control['admission_receipt_sha256'] and
                all(control[k]==request[k] for k in ('owner_id','project_id','dataset_id','dataset_sha256','root_dataset_id',
                    'raw_asset_id','raw_sha256','raw_bytes','method_id')) and
                control['request_sha256']==digest(request), 'physical_publication_parent_control')
        require(row['row_count']==len(child['payload']['correction_result']['dataset']['stations']),
                'physical_publication_parent_rows')
        previous,body=snapshot,child_body
    return body,previous


def publish_correction(connection, files, *, owner_id, project_id, intent_id,
                       approved_manifests, metrics, finished_at, failure_cut=None):
    """Verify original/staged/installed copies, then co-commit all terminal rows.

    The caller's measured metrics are compared to the result, not inferred from
    JSON. A caller-supplied registered manifest is not an OS/runtime approval.
    After an uncertain commit: close the connection and classify fresh; NEVER
    repeat this operation to adopt a prepared outcome automatically.
    """
    for value in (owner_id,project_id,intent_id):
        uuid(value)
    instant(finished_at,legacy=True)
    fields(metrics,'wall_ms cpu_ms peak_rss_bytes scratch_bytes')
    begin_ledger(connection)
    try:
        intent=_row(connection,'SELECT * FROM physical_publication_intents WHERE intent_id=? AND owner_id=? AND project_id=?',
                    (intent_id,owner_id,project_id))
        require(intent['kind']=='job' and intent['phase']=='prepared','physical_publication_intent')
        job=_row(connection,'SELECT * FROM processing_jobs WHERE id=?',(intent['job_id'],))
        control=_row(connection,'SELECT * FROM physical_job_controls WHERE job_id=?',(job['id'],))
        require(job['state']=='running' and job['cancel_requested']==0 and job['method_id']==CORRECTION and
                job['physical_fingerprint'] is not None and job['result_key'] is job['result_sha256'] is job['result_bytes'] is None,
                'physical_publication_job_not_publishable')
        require((control['owner_id'],control['project_id'],control['dataset_id'],control['dataset_sha256'],control['request_sha256'],
                 control['stage_id'],control['root_dataset_id'],control['method_id'],control['permanent_reservation_bytes'])==
                (owner_id,project_id,job['dataset_id'],job['dataset_sha256'],job['request_sha256'],job['id'],intent['root_dataset_id'],CORRECTION,80*M)
                and (intent['parent_dataset_id'],intent['parent_dataset_sha256'],intent['request_sha256'],intent['stage_id'])==
                (job['dataset_id'],job['dataset_sha256'],job['request_sha256'],job['id']), 'physical_publication_control')
        parent=_row(connection,'SELECT * FROM observation_datasets WHERE id=?',(job['dataset_id'],))
        input_body,prior=audit_correction_ancestry(connection,files,parent,approved_manifests=approved_manifests)
        batch,inventory=sealed_stage(connection,control)
        roles={slot['role']:slot for slot in inventory['initial_files']}
        require(len(roles)==len(inventory['initial_files']) and
                {'input_spool','request_spool','dataset_copy','result_copy','scientific_output','completion'}<=set(roles),
                'physical_publication_stage_roles')
        stage=f".job-staging/{job['id']}"
        files.verify_directory(stage,expected_files=[slot['leaf'] for slot in inventory['initial_files']])
        bodies={}
        for role,slot in roles.items():
            bodies[role]=files.read(stage+'/'+slot['leaf'],cap=slot['max_bytes'],
                                    expected_bytes=slot['actual_bytes'],expected_sha256=slot['actual_sha256'])
        require(bodies['input_spool']==input_body and bodies['request_spool']==control['request_bytes'],
                'physical_publication_spool')
        request=decode(bodies['request_spool'],34*M)
        manifest=decode(control['module_manifest_bytes'],65536)
        require(canonical(request['parent_production'])==canonical(prior) and
                (control['parent_production_bytes'] is None if prior is None else control['parent_production_bytes']==canonical(prior))
                and request['admission_receipt_sha256']==control['admission_receipt_sha256']
                and digest(manifest)==control['module_manifest_sha256'],'physical_publication_saved_control')
        require(canonical(decode(job['request_json'].encode('utf-8'),35*M))==canonical(request) and
                all(control[k]==request[k] for k in ('owner_id','project_id','dataset_id','dataset_sha256','root_dataset_id',
                    'raw_asset_id','raw_sha256','raw_bytes','method_id')) and control['request_sha256']==digest(request),
                'physical_publication_request_control')
        targets=connection.execute('SELECT kind,artifact_id,storage_key,bytes,sha256 FROM physical_publication_targets WHERE intent_id=? ORDER BY kind',
                                   (intent_id,)).fetchall()
        targets=[dict(zip(('kind','artifact_id','storage_key','bytes','sha256'),row)) for row in targets]
        _targets(connection,control,targets,intent['child_dataset_id'],job['id'],owner_id,project_id)
        for target in targets:
            require(files.read(target['storage_key'],cap=16*M if target['kind']=='dataset' else 64*M,
                               expected_bytes=target['bytes'],expected_sha256=target['sha256'])==bodies[target['kind']+'_copy'],
                    'physical_publication_installed_copy')
        child=decode(bodies['dataset_copy'],16*M)
        require(child['dataset_id']==intent['child_dataset_id'] and child['version']==intent['ordinal'],
                'physical_publication_reserved_child')
        receipt=child['payload']['receipt']
        production=dict(child_dataset_id=child['dataset_id'],job_id=job['id'],owner_id=owner_id,project_id=project_id,
                        root_dataset_id=intent['root_dataset_id'],raw_asset_id=control['raw_asset_id'],
                        parent_dataset_id=job['dataset_id'],parent_dataset_sha256=job['dataset_sha256'],method_id=CORRECTION,
                        request_sha256=job['request_sha256'],submitted_parameters_sha256=control['submitted_parameters_sha256'],
                        scientific_request_sha256=control['scientific_request_sha256'],scientific_result_sha256=scientific_digest(child['payload']),
                        module_manifest_sha256=control['module_manifest_sha256'],result_sha256=byte_sha(bodies['result_copy']),
                        result_bytes=len(bodies['result_copy']),scientific_verdict='passed',adapter_result_sha256=scientific_digest(child['payload']),
                        adapter_receipt_sha256=scientific_digest(receipt),core_result_sha256=receipt['correction_result_sha256'],
                        submitted_config_sha256=receipt['submitted_config_sha256'],normalized_config_sha256=receipt['normalized_config_sha256'],
                        adapter_receipt_bytes=canonical(receipt))
        terminal=dict(job,state='succeeded',finished_at=finished_at,result_key=f"derived/{owner_id}/{project_id}/results/{job['id']}.json",
                      result_sha256=production['result_sha256'],result_bytes=production['result_bytes'],wall_ms=metrics['wall_ms'],
                      physical_cpu_ms=metrics['cpu_ms'],peak_rss_bytes=metrics['peak_rss_bytes'],scratch_bytes=metrics['scratch_bytes'],
                      error_code=None,error_message=None)
        snapshot=_snapshot(child,bodies['dataset_copy'],terminal,production,manifest)
        verify_correction_producer(snapshot,input_bytes=input_body,child_bytes=bodies['dataset_copy'],request_bytes=bodies['request_spool'],
                                   result_bytes=bodies['result_copy'],approved_manifest=approved_manifests.get(digest(manifest)),
                                   job=terminal,production=production)
        require(canonical(child['payload'],scientific=True)==bodies['scientific_output'],'physical_publication_scientific_bytes')
        complete=decode(bodies['completion'],4096)
        require(complete==dict(schema='geophysics.physical-child-completion/v1',job_id=job['id'],method_id=CORRECTION,
                              scientific_request_sha256=control['scientific_request_sha256'],scientific_result_sha256=scientific_digest(child['payload']),
                              output_bytes=len(bodies['scientific_output']),output_sha256=byte_sha(bodies['scientific_output']),scientific_verdict='passed'),
                'physical_publication_completion')
        family=_row(connection,'SELECT * FROM physical_dataset_families WHERE root_dataset_id=?',(intent['root_dataset_id'],))
        require(family['state']=='published' and family['reserved_count']>=1 and intent['ordinal']<family['next_ordinal'] and
                family['published_count']==connection.execute('SELECT count(*) FROM observation_datasets WHERE root_dataset_id=?',(intent['root_dataset_id'],)).fetchone()[0] and
                family['reserved_count']==connection.execute('SELECT count(*) FROM physical_publication_intents WHERE root_dataset_id=?',(intent['root_dataset_id'],)).fetchone()[0],
                'physical_publication_allocator')
        row=dict(id=child['dataset_id'],project_id=project_id,owner_id=owner_id,raw_asset_id=control['raw_asset_id'],version=intent['ordinal'],
                 parser_version='gravity-stations-json/v1',modality='gravity_physical_station',row_count=len(child['payload']['correction_result']['dataset']['stations']),
                 raw_sha256=control['raw_sha256'],sha256=byte_sha(bodies['dataset_copy']),byte_count=len(bodies['dataset_copy']),
                 storage_key=f"derived/{owner_id}/{project_id}/datasets/{child['dataset_id']}.json",created_at=finished_at,kind='derived',
                 root_dataset_id=intent['root_dataset_id'],parent_dataset_id=job['dataset_id'],payload_schema='gravity-station-adapter-result-1')
        connection.execute(f"INSERT INTO observation_datasets({','.join(row)}) VALUES ({','.join('?' for _ in row)})",tuple(row.values()))
        if failure_cut:
            failure_cut('child')
        edge={key:production[key] for key in ('child_dataset_id','parent_dataset_id','parent_dataset_sha256','owner_id','project_id','raw_asset_id','root_dataset_id')}
        edge.update(role='scientific_input',child_kind='derived')
        connection.execute(f"INSERT INTO physical_dataset_edges({','.join(edge)}) VALUES ({','.join('?' for _ in edge)})",tuple(edge.values()))
        connection.execute(f"INSERT INTO physical_dataset_productions({','.join(production)}) VALUES ({','.join('?' for _ in production)})",tuple(production.values()))
        if failure_cut:
            failure_cut('production')
        connection.execute('UPDATE processing_jobs SET state=?,finished_at=?,result_key=?,result_sha256=?,result_bytes=?,wall_ms=?,physical_cpu_ms=?,peak_rss_bytes=?,scratch_bytes=?,error_code=NULL,error_message=NULL WHERE id=?',
                           tuple(terminal[k] for k in ('state','finished_at','result_key','result_sha256','result_bytes','wall_ms','physical_cpu_ms','peak_rss_bytes','scratch_bytes','id')))
        connection.execute("UPDATE physical_job_controls SET permanent_reservation_bytes=0 WHERE job_id=?",(job['id'],))
        connection.execute("UPDATE physical_custody_batches SET state='cleanup_pending' WHERE batch_id=?",(batch['batch_id'],))
        if failure_cut:
            failure_cut('terminal')
        connection.execute('DELETE FROM physical_publication_targets WHERE intent_id=?',(intent_id,))
        connection.execute('DELETE FROM physical_publication_intents WHERE intent_id=?',(intent_id,))
        connection.execute('UPDATE physical_dataset_families SET published_count=published_count+1,reserved_count=reserved_count-1 WHERE root_dataset_id=?',(intent['root_dataset_id'],))
        if failure_cut:
            failure_cut('retired')
        require(not connection.execute('PRAGMA foreign_key_check').fetchall(),'physical_publication_foreign_keys')
        connection.commit()
        return snapshot
    except BaseException:
        connection.rollback()
        raise
