"""Positive current0005 compact deletion projection, no deletion or replay.

The frozen historical decoder is unchanged. Existing profile/M08 roles are
explicitly validated before the inherited physical graph validator is invoked
on its positively registered subset. Complete receipt projection is checked
separately; unknown entries never disappear into a legacy fallback.
"""

from app.physical_contract import (
    CORRECTION, TRANSFORM, M, METHODS as OLD_METHODS,
    byte_sha, canonical, descriptor, digest, fields, integer,
    require, sha, uuid, instant, validate_deleted_inventory,
)
from app.physical_persistence import DATASET_REGISTRY
from app.physical_successor import METHODS, predecessor_payload
from app.physical_current_custody import parse_current_custody, validate_current_custody
from app.profile_archive_custody import ARCHIVE_SCHEMAS, archive_limits, validate_saved_entry, validate_original_receipt_entry, _json


SCHEMA = 'geophysics.physical-deleted-inventory/v1'
JOINT_SCHEMA = 'geophysics.physical-deleted-inventory/v2'
BASE = 'raw_assets datasets edges productions jobs custody source_policy_sha256'
EXTRA = 'waveform_sources waveform_artifacts profile_archives'
JOINT_EXTRA = 'joint_raw_assets joint_sources joint_result_indexes joint_result_members'
DEFINITIONS = {
    'raw_assets': ('asset_id', 'asset_id source_id sha256 bytes'),
    'datasets': ('dataset_id', 'dataset_id raw_asset_id root_dataset_id parent_dataset_id version parser_version kind modality payload_schema sha256 bytes'),
    'edges': ('child_dataset_id', 'parent_dataset_id child_dataset_id role parent_dataset_sha256'),
    'productions': ('child_dataset_id', 'child_dataset_id job_id input_dataset_id input_dataset_sha256 method_id request_sha256 result_sha256 result_bytes submitted_parameters_sha256 scientific_request_sha256 scientific_result_sha256 adapter_result_sha256 module_manifest_sha256 scientific_verdict'),
    'jobs': ('job_id', 'job_id dataset_id dataset_sha256 method_id state request_sha256 result_sha256 result_bytes physical_fingerprint physical_control_sha256 scientific_verdict'),
    'custody': ('batch_id', 'batch_id origin_kind origin_id initial_inventory_sha256'),
}


def joint_projection(raw_assets, datasets, jobs, source_rows, artifact_rows):
    """Make the closed M11 projection from rows already checked by the reader.

    This function does not admit data. Callers first run the complete
    same-transaction classifier, which validates the index bytes, each member,
    the dataset JSON, all source links, and the complete storage census.
    """
    from app.physical_joint_native_contract import METHOD_ID, PARSER, bounded_json, member_metadata

    joint_raw = []
    for row in raw_assets:
        if row['detected_format'] != 'joint_native':
            continue
        metadata = bounded_json(row['physical_metadata'].encode('utf-8', 'strict'))
        fields(metadata, 'schema role name descriptor scientific_values_decoded scientific_accepted')
        require(metadata['schema'] == 'joint-native-member-1'
                and metadata['name'] == row['filename']
                and metadata['scientific_values_decoded'] is False
                and metadata['scientific_accepted'] is False, 'current_deletion_joint_raw_metadata')
        member_metadata(canonical(dict(role=metadata['role'], name=metadata['name'],
            descriptor=metadata['descriptor'], source=dict(expected_bytes=row['byte_count'],
                                                            expected_sha256=row['sha256']))))
        joint_raw.append(dict(asset_id=row['id'], source_id=row['source_id'], filename=row['filename'],
            role=metadata['role'], descriptor=metadata['descriptor'], sha256=row['sha256'], bytes=row['byte_count']))
    dataset_ids = {r['id'] for r in datasets if r['parser_version'] == PARSER}
    joint_jobs = {r['id']: r for r in jobs if r['method_id'] == METHOD_ID}
    joint_sources = [dict(dataset_id=r['dataset_id'], role=r['role'], name=r['name'], asset_id=r['asset_id'],
        source_id=r['source_id'], source_version=r['source_version'], raw_sha256=r['raw_sha256'],
        raw_bytes=r['raw_bytes']) for r in source_rows if r['dataset_id'] in dataset_ids]
    joint_sources.sort(key=lambda r: (r['dataset_id'], r['role'], r['name']))

    members_by_job = {}
    joint_members = []
    for row in artifact_rows:
        if row['job_id'] not in joint_jobs:
            continue
        item = dict(job_id=row['job_id'], owner_id=row['owner_id'], project_id=row['project_id'],
            dataset_id=row['dataset_id'], dataset_sha256=row['dataset_sha256'], method_id=row['method_id'],
            request_sha256=row['request_sha256'], name=row['name'], storage_key=row['storage_key'],
            sha256=row['sha256'], bytes=row['byte_count'])
        joint_members.append(item)
        members_by_job.setdefault(row['job_id'], []).append(dict(name=row['name'], sha256=row['sha256'],
                                                                  bytes=row['byte_count']))
    joint_members.sort(key=lambda r: (r['job_id'], r['name']))
    indexes = []
    for job_id, job in sorted(joint_jobs.items()):
        present = (job['result_key'] is not None, job['result_sha256'] is not None, job['result_bytes'] is not None)
        require(len(set(present)) == 1, 'current_deletion_joint_index_tuple')
        job_members = sorted(members_by_job.get(job_id, []), key=lambda r: r['name'])
        if not present[0]:
            require(not job_members and job['state'] != 'succeeded', 'current_deletion_joint_missing_index')
            continue
        require(job['state'] in ('succeeded', 'failed', 'cancelled') and job['result_key'] ==
                f"derived/{job['owner_id']}/{job['project_id']}/results/{job_id}.json",
                'current_deletion_joint_index_identity')
        indexes.append(dict(job_id=job_id, state=job['state'], dataset_id=job['dataset_id'],
            dataset_sha256=job['dataset_sha256'], method_id=job['method_id'], request_sha256=job['request_sha256'],
            sha256=job['result_sha256'], bytes=job['result_bytes'], member_manifest=job_members))
    return dict(joint_raw_assets=sorted(joint_raw, key=lambda r: r['asset_id']), joint_sources=joint_sources,
        joint_result_indexes=indexes, joint_result_members=joint_members)


def _ordered(values, key, keys, *, cap=4096):
    require(type(values) is list and len(values) <= cap, 'current_deletion_list')
    identities = []
    for row in values:
        fields(row, keys)
        identities.append(row[key])
        for name, value in row.items():
            if value is not None and name.endswith('_id') and name != 'method_id':
                uuid(value)
            elif value is not None and name.endswith('sha256'):
                sha(value)
    require(identities == sorted(set(identities)), 'current_deletion_duplicate_or_order')


def validate_current_inventory(value, receipt, *, expected_source_policy_sha256, approved_installations):
    require(type(value) is dict, 'current_deletion_inventory_object')
    version = value.get('schema')
    fields(value, 'schema ' + BASE + ' ' + EXTRA + ((' ' + JOINT_EXTRA) if version == JOINT_SCHEMA else ''))
    require(version in (SCHEMA, JOINT_SCHEMA) and sha(expected_source_policy_sha256) == value['source_policy_sha256'],
            'current_deletion_source_binding')
    definitions = dict(DEFINITIONS)
    if version == JOINT_SCHEMA:
        definitions['raw_assets'] = ('asset_id', 'asset_id source_id sha256 bytes detected_format filename')
    for name, (key, keys) in definitions.items():
        _ordered(value[name], key, keys)
    counted = set(DEFINITIONS) | (set(JOINT_EXTRA.split()) if version == JOINT_SCHEMA else set())
    require(sum(len(value[k]) for k in counted) <= 20000 and len(canonical(value)) <= 4*M,
            'current_deletion_inventory_cap')
    raw = {r['asset_id']: r for r in value['raw_assets']}
    datasets = {r['dataset_id']: r for r in value['datasets']}
    jobs = {r['job_id']: r for r in value['jobs']}
    joint_job_ids = set()
    if version == JOINT_SCHEMA:
        from app.physical_joint_native_contract import METHOD_ID as JOINT_METHOD, PARSER as JOINT_PARSER, MAX_BYTES, MAX_JSON, member_metadata
        from app.physical_joint_custody import NAME
        expected_joint_raw = {r['asset_id'] for r in value['raw_assets'] if r['detected_format'] == 'joint_native'}
        joint_raw_ids, joint_raw_sources = set(), set()
        require(type(value['joint_raw_assets']) is list and len(value['joint_raw_assets']) <= 8192,
                'current_deletion_joint_raw_cap')
        raw_declarations = []
        for entry in value['joint_raw_assets']:
            fields(entry, 'asset_id source_id filename role descriptor sha256 bytes')
            uuid(entry['asset_id']); uuid(entry['source_id']); sha(entry['sha256'])
            require(type(entry['filename']) is str and entry['filename'].endswith(('.json','.npy')),
                    'current_deletion_joint_raw_name')
            integer(entry['bytes'], 1, MAX_JSON if entry['filename'].endswith('.json') else MAX_BYTES)
            asset = raw.get(entry['asset_id'])
            require(asset is not None and asset['detected_format'] == 'joint_native'
                    and (asset['source_id'], asset['filename'], asset['sha256'], asset['bytes']) ==
                    (entry['source_id'], entry['filename'], entry['sha256'], entry['bytes']),
                    'current_deletion_joint_raw_binding')
            member_metadata(canonical(dict(role=entry['role'], name=entry['filename'], descriptor=entry['descriptor'],
                source=dict(expected_bytes=entry['bytes'], expected_sha256=entry['sha256']))))
            require(entry['asset_id'] not in joint_raw_ids and entry['source_id'] not in joint_raw_sources,
                    'current_deletion_joint_raw_duplicate')
            joint_raw_ids.add(entry['asset_id']); joint_raw_sources.add(entry['source_id'])
            raw_declarations.append(dict(asset_id=entry['asset_id'], source_id=entry['source_id'],
                                         filename=entry['filename'], role=entry['role'], descriptor=entry['descriptor'],
                                         sha256=entry['sha256'], bytes=entry['bytes']))
        require(joint_raw_ids == expected_joint_raw, 'current_deletion_joint_raw_complete')
        require(type(value['joint_sources']) is list and len(value['joint_sources']) <= 8192,
                'current_deletion_joint_source_cap')
        source_ids = set()
        source_projection = []
        joint_raw_by_id = {r['asset_id']:r for r in value['joint_raw_assets']}
        for entry in value['joint_sources']:
            fields(entry, 'dataset_id role name asset_id source_id source_version raw_sha256 raw_bytes')
            for key in ('dataset_id', 'asset_id', 'source_id'): uuid(entry[key])
            sha(entry['raw_sha256']); integer(entry['raw_bytes'], 1, MAX_BYTES); integer(entry['source_version'], 1)
            dataset, asset = datasets.get(entry['dataset_id']), raw.get(entry['asset_id'])
            require(dataset is not None and dataset['parser_version'] == JOINT_PARSER and asset is not None
                    and asset['detected_format'] == 'joint_native'
                    and (asset['source_id'], asset['sha256'], asset['bytes']) ==
                    (entry['source_id'], entry['raw_sha256'], entry['raw_bytes']),
                    'current_deletion_joint_source_binding')
            raw_declaration = joint_raw_by_id.get(entry['asset_id'])
            require(raw_declaration is not None and (raw_declaration['source_id'],raw_declaration['filename'],
                    raw_declaration['role'],raw_declaration['sha256'],raw_declaration['bytes']) ==
                    (entry['source_id'],entry['name'],entry['role'],entry['raw_sha256'],entry['raw_bytes']),
                    'current_deletion_joint_source_raw_projection')
            key = (entry['dataset_id'], entry['role'], entry['name'])
            require(key not in source_ids, 'current_deletion_joint_source_duplicate')
            source_ids.add(key); source_projection.append(entry)
        require(source_projection == sorted(source_projection, key=lambda r:(r['dataset_id'],r['role'],r['name'])),
                'current_deletion_joint_source_order')
        require({r['dataset_id'] for r in source_projection} ==
                {r['dataset_id'] for r in datasets.values() if r['parser_version'] == JOINT_PARSER},
                'current_deletion_joint_source_complete')
        joint_job_ids = {r['job_id'] for r in value['jobs'] if r['method_id'] == JOINT_METHOD}
        require(type(value['joint_result_indexes']) is list and len(value['joint_result_indexes']) <= 4096,
                'current_deletion_joint_index_cap')
        index_ids, index_projection = set(), []
        for entry in value['joint_result_indexes']:
            fields(entry, 'job_id state dataset_id dataset_sha256 method_id request_sha256 sha256 bytes member_manifest')
            for key in ('job_id','dataset_id'): uuid(entry[key])
            for key in ('dataset_sha256','request_sha256','sha256'): sha(entry[key])
            integer(entry['bytes'], 1, MAX_JSON)
            job = jobs.get(entry['job_id'])
            require(job is not None and job['method_id'] == JOINT_METHOD and entry['state'] in ('succeeded','failed','cancelled')
                    and (job['state'],job['dataset_id'],job['dataset_sha256'],job['method_id'],job['request_sha256'],job['result_sha256'],job['result_bytes']) ==
                    (entry['state'],entry['dataset_id'],entry['dataset_sha256'],entry['method_id'],entry['request_sha256'],entry['sha256'],entry['bytes']),
                    'current_deletion_joint_index_binding')
            require(type(entry['member_manifest']) is list and 0 < len(entry['member_manifest']) <= 1100,
                    'current_deletion_joint_index_members')
            previous = []
            for member in entry['member_manifest']:
                fields(member, 'name sha256 bytes'); sha(member['sha256']); integer(member['bytes'],1,MAX_BYTES)
                require(type(member['name']) is str and NAME.fullmatch(member['name']) is not None,
                        'current_deletion_joint_index_member_name')
                previous.append(member['name'])
            require(previous == sorted(set(previous)), 'current_deletion_joint_index_member_order')
            require(entry['job_id'] not in index_ids, 'current_deletion_joint_index_duplicate')
            index_ids.add(entry['job_id']); index_projection.append(entry)
        expected_index_ids = {j['job_id'] for j in value['jobs'] if j['method_id'] == JOINT_METHOD
                              and j['result_sha256'] is not None}
        require(index_ids == expected_index_ids, 'current_deletion_joint_index_complete')
        require(type(value['joint_result_members']) is list and len(value['joint_result_members']) <= 4096,
                'current_deletion_joint_member_cap')
        member_rows, by_job = [], {}
        for entry in value['joint_result_members']:
            fields(entry, 'job_id owner_id project_id dataset_id dataset_sha256 method_id request_sha256 name storage_key sha256 bytes')
            for key in ('job_id','owner_id','project_id','dataset_id'): uuid(entry[key])
            for key in ('dataset_sha256','request_sha256','sha256'): sha(entry[key])
            integer(entry['bytes'],1,MAX_BYTES)
            require(type(entry['name']) is str and NAME.fullmatch(entry['name']) is not None,
                    'current_deletion_joint_member_name')
            job = jobs.get(entry['job_id'])
            require(job is not None and job['method_id'] == JOINT_METHOD
                    and entry['storage_key'] == f"derived/{entry['owner_id']}/{entry['project_id']}/joint/{entry['job_id']}/{entry['name']}"
                    and (entry['owner_id'],entry['project_id'],entry['dataset_id'],entry['dataset_sha256'],entry['method_id'],entry['request_sha256']) ==
                    (receipt['owner_id'],receipt['project_id'],job['dataset_id'],job['dataset_sha256'],JOINT_METHOD,job['request_sha256']),
                    'current_deletion_joint_member_binding')
            by_job.setdefault(entry['job_id'],[]).append(dict(name=entry['name'],sha256=entry['sha256'],bytes=entry['bytes']))
            member_rows.append(entry)
        require(member_rows == sorted(member_rows,key=lambda r:(r['job_id'],r['name']))
                and len({(r['job_id'],r['name']) for r in member_rows}) == len(member_rows),
                'current_deletion_joint_member_order')
        for entry in value['joint_result_indexes']:
            require(entry['member_manifest'] == sorted(by_job.get(entry['job_id'],[]),key=lambda r:r['name']),
                    'current_deletion_joint_index_member_projection')
            require(sum(member['bytes'] for member in entry['member_manifest']) <= MAX_BYTES,
                    'current_deletion_joint_member_total')
        require(set(by_job) == index_ids, 'current_deletion_joint_orphan_member')
    old_datasets, new_datasets = [], []
    from app.physical_joint_native_contract import METHOD_ID as JOINT_METHOD, MODALITY as JOINT_MODALITY, PARSER as JOINT_PARSER
    for row in datasets.values():
        require(row['raw_asset_id'] in raw, 'current_deletion_raw')
        integer(row['bytes'], 1, 64*M if row['payload_schema'] == 'gravity-transform-result-1' else 16*M)
        integer(row['version'], 1)
        discriminator = tuple(row[k] for k in ('kind', 'parser_version', 'modality', 'payload_schema'))
        if discriminator in DATASET_REGISTRY:
            old_datasets.append(row)
        elif version == JOINT_SCHEMA and row['parser_version'] == JOINT_PARSER:
            require((row['kind'],row['version'],row['root_dataset_id'],row['parent_dataset_id'],row['modality'],row['payload_schema']) ==
                    ('root',1,row['dataset_id'],None,JOINT_MODALITY,'geophysics.joint-native-dataset/v1'),
                    'current_deletion_joint_dataset_tuple')
            new_datasets.append(row)
        else:
            require(row['kind'] == 'root' and row['version'] == 1 and row['root_dataset_id'] == row['dataset_id']
                    and row['parent_dataset_id'] is None
                    and predecessor_payload(row['parser_version'], row['modality']) == row['payload_schema'],
                    'current_deletion_dataset_registry')
            new_datasets.append(row)
    old_jobs = []
    for row in jobs.values():
        require(row['method_id'] in METHODS | {CORRECTION, TRANSFORM, *({JOINT_METHOD} if version == JOINT_SCHEMA else set())}
                and row['state'] in ('succeeded', 'failed', 'cancelled'), 'current_deletion_terminal_job')
        dataset = datasets.get(row['dataset_id'])
        require(dataset is not None and dataset['sha256'] == row['dataset_sha256'], 'current_deletion_job_input')
        success, physical = row['state'] == 'succeeded', row['method_id'] in (CORRECTION, TRANSFORM)
        joint = version == JOINT_SCHEMA and row['method_id'] == JOINT_METHOD
        has_result = row['result_sha256'] is not None and row['result_bytes'] is not None
        require((row['result_sha256'] is not None) == (row['result_bytes'] is not None)
                and (has_result == success if not joint else (not success or has_result))
                and (row['physical_fingerprint'] is not None) == physical
                and (row['physical_control_sha256'] is not None) == physical
                and row['scientific_verdict'] in (('passed', 'non_pass') if physical and success else (None,)),
                'current_deletion_job_result')
        if success:
            integer(row['result_bytes'], 1, 256*1024 if joint else 64*M)
        elif joint and has_result:
            integer(row['result_bytes'],1,256*1024)
        if row['method_id'] in OLD_METHODS:
            old_jobs.append(row)
        elif joint:
            require(dataset['parser_version']==JOINT_PARSER and dataset['modality']==JOINT_MODALITY,
                    'current_deletion_joint_job_registry')
        else:
            modality = {'ert.topographic-profile/v1':'ert_profile', 'traveltime.first-arrival-profile/v1':'traveltime_profile',
                        'seismic.waveform-qc-classical/v1':'waveform_counts_response'}[row['method_id']]
            require(dataset['modality'] == modality and dataset in new_datasets, 'current_deletion_job_registry')

    # Inherited complete physical graph predicates, no weakened old parser.
    inherited = {k:value[k] for k in BASE.split()}
    if version == JOINT_SCHEMA:
        inherited['raw_assets'] = [{k:r[k] for k in ('asset_id','source_id','sha256','bytes')} for r in value['raw_assets']]
    inherited['datasets'], inherited['jobs'] = old_datasets, old_jobs
    inherited_receipt = dict(asset_manifest=[dict(asset_id=r['asset_id'],sha256=r['sha256'],byte_count=r['bytes']) for r in raw.values()],
        derived_manifest=[dict(kind='dataset',id=r['dataset_id'],sha256=r['sha256'],byte_count=r['bytes']) for r in old_datasets] +
        [dict(kind='result',id=r['job_id'],sha256=r['result_sha256'],byte_count=r['result_bytes']) for r in old_jobs if r['state']=='succeeded'])
    validate_deleted_inventory(inherited, inherited_receipt)

    from app.waveform_contract import MEMBER, SCRATCH
    require(type(value['waveform_sources']) is list and len(value['waveform_sources']) <= 8192,
            'current_deletion_waveform_sources')
    pairs = {}
    source_order = []
    for row in value['waveform_sources']:
        fields(row, 'dataset_id role asset_id source_id raw_sha256 raw_bytes source_version')
        for key in ('dataset_id', 'asset_id', 'source_id'): uuid(row[key])
        sha(row['raw_sha256']); integer(row['raw_bytes'],1,16*M); integer(row['source_version'],1)
        require(row['role'] in ('miniseed','stationxml') and row['dataset_id'] in datasets
                and datasets[row['dataset_id']]['modality']=='waveform_counts_response', 'current_deletion_waveform_sources')
        asset = raw.get(row['asset_id'])
        require(asset is not None and (asset['source_id'], asset['sha256'], asset['bytes']) ==
                (row['source_id'], row['raw_sha256'], row['raw_bytes']), 'current_deletion_waveform_source_binding')
        require(row['raw_bytes'] <= (16*M if row['role']=='miniseed' else 2*M), 'current_deletion_waveform_source_cap')
        source_order.append((row['dataset_id'],row['role']))
        pairs.setdefault(row['dataset_id'],set()).add(row['role'])
        if row['role']=='miniseed':
            require(datasets[row['dataset_id']]['raw_asset_id']==row['asset_id'], 'current_deletion_waveform_primary')
    require(source_order==sorted(set(source_order)) and set(pairs)=={r['dataset_id'] for r in new_datasets
            if r['modality']=='waveform_counts_response'} and all(roles=={'miniseed','stationxml'} for roles in pairs.values()),
            'current_deletion_waveform_pair_completeness')
    require(type(value['waveform_artifacts']) is list and len(value['waveform_artifacts'])<=4096,
            'current_deletion_waveform_artifacts')
    artifact_order = []
    artifact_projection = []
    for row in value['waveform_artifacts']:
        fields(row, 'job_id name sha256 bytes')
        uuid(row['job_id']); sha(row['sha256']); integer(row['bytes'],1,SCRATCH)
        require(type(row['name']) is str and MEMBER.fullmatch(row['name']) is not None
                and row['job_id'] in jobs and jobs[row['job_id']]['method_id']=='seismic.waveform-qc-classical/v1'
                and jobs[row['job_id']]['state']=='succeeded', 'current_deletion_waveform_artifact_binding')
        artifact_order.append((row['job_id'],row['name']))
        artifact_projection.append(dict(kind='waveform_artifact',id=row['job_id'],name=row['name'],
            relative_path=f"waveforms/{row['job_id']}/{row['name']}",sha256=row['sha256'],byte_count=row['bytes']))
    require(artifact_order==sorted(set(artifact_order)), 'current_deletion_waveform_artifact_duplicates')

    require(type(value['profile_archives']) is list and len(value['profile_archives'])<=128, 'current_deletion_archive_cap')
    archive_limits(value['profile_archives'])
    identifiers = []
    for entry in value['profile_archives']:
        relation = validate_saved_entry(entry,owner_id=receipt['owner_id'],project_id=receipt['project_id'],
                                        approved_installations=approved_installations)
        identifiers.append(relation['id'])
        job, dataset, asset = jobs.get(relation['id']), datasets.get(relation['dataset_id']), raw.get(relation['raw_asset_id'])
        require(job is not None and dataset is not None and asset is not None and
            (job['method_id'],job['state'],job['request_sha256'],job['dataset_id'],job['dataset_sha256']) ==
            tuple(relation[k] for k in ('method_id','state','request_sha256','dataset_id','dataset_sha256')) and
            dataset['raw_asset_id']==asset['asset_id'] and (asset['source_id'],asset['sha256'])==
            (relation['source_id'],relation['raw_sha256']), 'current_deletion_archive_join')
    require(identifiers==sorted(set(identifiers)), 'current_deletion_archive_duplicate')

    projected_raw = [dict(asset_id=r['asset_id'],sha256=r['sha256'],byte_count=r['bytes']) for r in raw.values()]
    joint_index_jobs = {r['job_id'] for r in value.get('joint_result_indexes', [])}
    projected = ([dict(kind='dataset',id=r['dataset_id'],sha256=r['sha256'],byte_count=r['bytes']) for r in datasets.values()] +
        [dict(kind='result',id=r['job_id'],sha256=r['result_sha256'],byte_count=r['result_bytes'])
         for r in jobs.values() if r['state']=='succeeded' and r['job_id'] not in joint_index_jobs] +
        [dict(kind='result',id=r['job_id'],sha256=r['sha256'],byte_count=r['bytes'])
         for r in value.get('joint_result_indexes', [])] +
        artifact_projection + [dict(kind='joint_artifact',id=r['job_id'],name=r['name'],
            relative_path=f"joint/{r['job_id']}/{r['name']}",sha256=r['sha256'],byte_count=r['bytes'])
            for r in value.get('joint_result_members', [])] + value['profile_archives'])
    require(type(receipt['asset_manifest']) is list and type(receipt['derived_manifest']) is list,
            'current_deletion_receipt_type')
    for row in receipt['asset_manifest']:
        fields(row,'asset_id sha256 byte_count'); uuid(row['asset_id']); sha(row['sha256']); integer(row['byte_count'],1,1024*M)
    for row in receipt['derived_manifest']:
        require(type(row) is dict,'current_deletion_receipt_type')
        if row.get('schema') not in ARCHIVE_SCHEMAS: validate_original_receipt_entry(row)
    require(sorted(canonical(r) for r in projected_raw)==sorted(canonical(r) for r in receipt['asset_manifest'])
            and sorted(canonical(r) for r in projected)==sorted(canonical(r) for r in receipt['derived_manifest']),
            'current_deletion_complete_projection')


def _native_control(row):
    return {k:descriptor(v) if type(v) is bytes else v for k,v in row.items()}


def project_inventory(connection, *, owner_id, project_id, source_policy_sha256, profile_records):
    """Snapshot projection only; caller first performs the full fresh classifier.

    This neither mutates SQL nor moves/removes files. No real-world numerical
    recomputation is claimed after deletion; saved native descriptors survive.
    """
    uuid(owner_id); uuid(project_id); sha(source_policy_sha256)
    from app.physical_schema import schema_tables
    require(connection.in_transaction, 'current_deletion_snapshot')
    _, registered_tables = schema_tables(connection)
    require(connection.execute('SELECT owner_id FROM projects WHERE id=?',(project_id,)).fetchone()==(owner_id,),
            'current_deletion_owner')
    def rows(table, where='owner_id=? AND project_id=?', values=(owner_id,project_id)):
        cursor=connection.execute(f'SELECT * FROM {table} WHERE '+where,values)
        headers=[c[0] for c in cursor.description]
        result=[dict(zip(headers,row)) for row in cursor.fetchmany(20001)]
        require(len(result)<=20000,'current_deletion_row_cap')
        return result
    raw=rows('raw_assets'); datasets=rows('observation_datasets'); jobs=rows('processing_jobs')
    from app.physical_joint_native_contract import METHOD_ID as JOINT_METHOD, PARSER as JOINT_PARSER
    joint_raw = [r for r in raw if r['detected_format'] == 'joint_native']
    joint_datasets = [r for r in datasets if r['parser_version'] == JOINT_PARSER]
    joint_jobs = [r for r in jobs if r['method_id'] == JOINT_METHOD]
    joint_children = joint_artifacts = False
    if 'joint_dataset_sources' in registered_tables:
        joint_children = connection.execute('''SELECT 1 FROM joint_dataset_sources s
            JOIN observation_datasets d ON d.id=s.dataset_id
            WHERE d.owner_id=? AND d.project_id=? LIMIT 1''',(owner_id,project_id)).fetchone() is not None
    if 'joint_result_artifacts' in registered_tables:
        joint_artifacts = connection.execute('''SELECT 1 FROM joint_result_artifacts a
            JOIN processing_jobs j ON j.id=a.job_id
            WHERE j.owner_id=? AND j.project_id=? LIMIT 1''',(owner_id,project_id)).fetchone() is not None
    from app.physical_schema import JOINT_TABLES
    require(not (joint_raw or joint_datasets or joint_jobs or joint_children or joint_artifacts)
            or JOINT_TABLES <= registered_tables, 'current_deletion_joint_schema_incomplete')
    joint_source_rows = rows('joint_dataset_sources',
        'dataset_id IN (SELECT id FROM observation_datasets WHERE owner_id=? AND project_id=?)') if JOINT_TABLES <= registered_tables else []
    joint_member_rows = rows('joint_result_artifacts',
        'job_id IN (SELECT id FROM processing_jobs WHERE owner_id=? AND project_id=?)') if JOINT_TABLES <= registered_tables else []
    joint = joint_projection(raw,datasets,jobs,joint_source_rows,joint_member_rows)
    has_joint = bool(joint_raw or joint_datasets or joint_jobs or joint_children or joint_artifacts)
    require(not any(j['state'] in ('queued','running') for j in jobs)
            and not rows('physical_publication_intents'),'current_deletion_active_operation')
    controls={r['job_id']:r for r in rows('physical_job_controls')}
    productions=rows('physical_dataset_productions')
    verdicts={r['job_id']:r['scientific_verdict'] for r in productions}
    joint_fields=joint if has_joint else {}
    value=dict(schema=JOINT_SCHEMA if has_joint else SCHEMA,source_policy_sha256=source_policy_sha256,
        raw_assets=[dict(asset_id=r['id'],source_id=r['source_id'],sha256=r['sha256'],bytes=r['byte_count'],
                         **({'detected_format':r['detected_format'],'filename':r['filename']} if has_joint else {})) for r in raw],
        datasets=[dict(dataset_id=r['id'],**{k:r[k] for k in ('raw_asset_id','root_dataset_id','parent_dataset_id','version','parser_version','kind','modality','payload_schema','sha256')},bytes=r['byte_count']) for r in datasets],
        edges=[{k:r[k] for k in DEFINITIONS['edges'][1].split()} for r in rows('physical_dataset_edges')],
        productions=[dict(child_dataset_id=r['child_dataset_id'],job_id=r['job_id'],input_dataset_id=r['parent_dataset_id'],input_dataset_sha256=r['parent_dataset_sha256'],
            **{k:r[k] for k in DEFINITIONS['productions'][1].split() if k not in ('child_dataset_id','job_id','input_dataset_id','input_dataset_sha256')}) for r in productions],
        jobs=[dict(job_id=r['id'],**{k:r[k] for k in ('dataset_id','dataset_sha256','method_id','state','request_sha256','result_sha256','result_bytes','physical_fingerprint')},
            physical_control_sha256=digest(_native_control(controls[r['id']])) if r['id'] in controls else None,scientific_verdict=verdicts.get(r['id'])) for r in jobs],
        custody=[],waveform_sources=[],waveform_artifacts=[],profile_archives=[],**joint_fields)
    for batch in rows('physical_custody_batches'):
        preparing=batch['origin_kind']=='project_deletion' and batch['state']=='sealed' and batch['charged_bytes']==0
        require((batch['state'] in ('cleanup_pending','removed') or preparing) and type(batch['inventory_bytes']) is bytes
                and byte_sha(batch['inventory_bytes'])==batch['inventory_sha256'],'current_deletion_custody_unresolved')
        inv=parse_current_custody([batch['inventory_bytes']]); measured=validate_current_custody(inv)
        require(preparing or measured['retained_bytes']==batch['charged_bytes'],'current_deletion_custody_charge')
        value['custody'].append(dict(batch_id=batch['batch_id'],origin_kind=batch['origin_kind'],origin_id=batch['origin_id'],
                                    initial_inventory_sha256=measured['initial_inventory_sha256']))
    for row in rows('waveform_dataset_sources','dataset_id IN (SELECT id FROM observation_datasets WHERE owner_id=? AND project_id=?)'):
        value['waveform_sources'].append(row)
    for row in rows('waveform_result_artifacts','job_id IN (SELECT id FROM processing_jobs WHERE owner_id=? AND project_id=?)'):
        value['waveform_artifacts'].append(dict(job_id=row['job_id'],name=row['name'],sha256=row['sha256'],bytes=row['byte_count']))
    require(type(profile_records) is list,'current_deletion_profile_records')
    value['profile_archives']=[r for r in profile_records if (r['owner_id'],r['project_id'])==(owner_id,project_id)]
    for name,(key,_) in DEFINITIONS.items(): value[name].sort(key=lambda r:r[key])
    value['waveform_sources'].sort(key=lambda r:(r['dataset_id'],r['role']))
    value['waveform_artifacts'].sort(key=lambda r:(r['job_id'],r['name']))
    value['profile_archives'].sort(key=lambda r:r['job_id'])
    require(len(canonical(value))<=4*M,'current_deletion_inventory_cap')
    return value


def observe_receipt(connection, receipt_id):
    """Observe the real native JSON TEXT after original ORM serialization."""
    uuid(receipt_id)
    require(connection.in_transaction,'current_deletion_snapshot')
    cursor=connection.execute('SELECT * FROM deletion_receipts WHERE id=?',(receipt_id,))
    native=cursor.fetchone()
    require(native is not None and cursor.fetchone() is None,'current_deletion_receipt_identity')
    row=dict(zip((c[0] for c in cursor.description),native))
    value=dict(schema='geophysics.deletion-receipt-native/v1',
        **{k:row[k] for k in ('id','owner_id','project_id','deleted_at','backup_purge_status')})
    for key in ('asset_hashes','asset_manifest','derived_manifest'):
        require(type(row[key]) is str,'current_deletion_native_json')
        body=row[key].encode('utf-8','strict')
        require(len(body)<=4*M,'current_deletion_native_json_cap')
        value[key]=dict(utf8=row[key],bytes=len(body),sha256=byte_sha(body))
    return value


def receipt_values(value):
    fields(value,'schema id owner_id project_id deleted_at backup_purge_status asset_hashes asset_manifest derived_manifest')
    require(value['schema']=='geophysics.deletion-receipt-native/v1'
            and value['backup_purge_status']=='not_attempted',
            'current_deletion_native_receipt')
    for key in ('id','owner_id','project_id'): uuid(value[key])
    instant(value['deleted_at'],legacy=True)
    receipt={k:value[k] for k in ('id','owner_id','project_id','deleted_at','backup_purge_status')}
    for key in ('asset_hashes','asset_manifest','derived_manifest'):
        record=value[key]; fields(record,'utf8 bytes sha256')
        require(type(record['utf8']) is str,'current_deletion_native_json')
        body=record['utf8'].encode('utf-8','strict')
        integer(record['bytes'],1,4*M); sha(record['sha256'])
        require(len(body)==record['bytes'] and byte_sha(body)==record['sha256'],'current_deletion_native_json_identity')
        receipt[key]=_json(body,4*M)
        require(type(receipt[key]) is list and len(receipt[key])<=4096,'current_deletion_native_json_shape')
    for h in receipt['asset_hashes']: sha(h)
    require(receipt['asset_hashes']==[r['sha256'] for r in receipt['asset_manifest']],
            'current_deletion_original_hash_order')
    return receipt


def validate_current_tombstone(value, *, expected_source_policy_sha256, approved_installations):
    fields(value,'schema id project_id owner_id deleted_at origin_revision legacy_receipt physical_inventory')
    from app.physical_schema import DDL
    require(value['schema']=='geophysics.physical-deletion/v2' and value['origin_revision'] in DDL,
            'current_deletion_revision_dispatch')
    receipt=receipt_values(value['legacy_receipt'])
    require(all(value[k]==receipt[k] for k in ('id','owner_id','project_id','deleted_at')),
            'current_deletion_tombstone_identity')
    validate_current_inventory(value['physical_inventory'],receipt,
        expected_source_policy_sha256=expected_source_policy_sha256,approved_installations=approved_installations)
    require(len(canonical(value))<=16*M,'current_deletion_tombstone_cap')
    return receipt


def save_current_tombstone(connection, *, receipt_id, inventory, expected_source_policy_sha256, approved_installations):
    """Co-commit extension with existing receipt/row deletion, never delete.

    Caller keeps the original DELETE transaction. No second receipt, commit,
    overwrite, backup or archive mutation is performed here.
    """
    native=observe_receipt(connection,receipt_id)
    require(connection.execute('SELECT 1 FROM projects WHERE id=?',(native['project_id'],)).fetchone() is None,
            'current_deletion_project_still_live')
    from app.physical_schema import schema_tables
    revision, _ = schema_tables(connection)
    value=dict(schema='geophysics.physical-deletion/v2',origin_revision=revision,legacy_receipt=native,
               physical_inventory=inventory,**{k:native[k] for k in ('id','owner_id','project_id','deleted_at')})
    validate_current_tombstone(value,expected_source_policy_sha256=expected_source_policy_sha256,
                               approved_installations=approved_installations)
    body=canonical(value)
    connection.execute('''INSERT INTO physical_deletion_extensions
        (receipt_id,owner_id,project_id,schema_tag,tombstone_bytes,tombstone_sha256) VALUES(?,?,?,?,?,?)''',
        (receipt_id,native['owner_id'],native['project_id'],value['schema'],body,byte_sha(body)))
    return body
