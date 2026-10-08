"""Closed M11 SQL/source/native custody reader for the physical union.

No importer, solver, file adoption, cleanup or publication occurs here. The
caller retains its consistent SQL snapshot and writer exclusion. Result
custody is not scientific acceptance, including when the job is succeeded.
"""

import hashlib
import re
from types import SimpleNamespace

from app import physical_joint_native_contract as native
from app.physical_joint_dataset_contract import validate_dataset
from app.physical_contract import byte_sha, canonical, fields, integer, require, sha, uuid

METHOD = native.METHOD_ID
INDEX_SCHEMA = 'geophysics.joint-result-custody/v1'
INDEX_CAP = native.MAX_JSON
NAME = re.compile(r'(?:workflow\.json|failure\.json|(?:calibration|frozen|models|result|instrument|aborted)/[a-z][a-z0-9_]{0,120}\.(?:json|npy))\Z')


def scan_stream(stream, *, byte_count, sha256, descriptor):
    """Bounded 64KiB hashing; native values are never decoded or accumulated."""
    integer(byte_count, 1, native.MAX_BYTES); sha(sha256)
    if descriptor is not None:
        require(descriptor['file_sha256'] == sha256, 'physical_joint_native_file_hash')
    head = stream.read(min(byte_count, native.MAX_HEADER + 10))
    offset = native.native_header(head, descriptor, byte_count) if descriptor is not None else 0
    whole, data = hashlib.sha256(), hashlib.sha256()
    whole.update(head); data.update(head[offset:]); count = len(head)
    while chunk := stream.read(min(65536, byte_count + 1 - count)):
        count += len(chunk)
        require(count <= byte_count, 'physical_joint_original_grew')
        whole.update(chunk); data.update(chunk)
    require(count == byte_count and whole.hexdigest() == sha256, 'physical_joint_original_hash')
    if descriptor is not None:
        require(data.hexdigest() == descriptor['data_sha256'], 'physical_joint_native_data_hash')
    return dict(bytes=count, sha256=whole.hexdigest())


def dataset_inventory(rows, files, dataset):
    """Close actual original dependencies, manifests, native headers and data."""
    body = files.read(dataset['storage_key'], cap=INDEX_CAP,
        expected_bytes=dataset['byte_count'], expected_sha256=dataset['sha256'])
    payload = native.bounded_json(body)
    validate_dataset(payload, SimpleNamespace(**dataset))
    owner, project = dataset['owner_id'], dataset['project_id']
    require(dataset['kind'] == 'root' and dataset['version'] == 1 and
            dataset['root_dataset_id'] == dataset['id'] and dataset['parent_dataset_id'] is None,
            'physical_joint_root_tuple')
    expected = {(role, name): binding for role, members in payload['members'].items()
                for name, binding in members.items()}
    dependencies = [r for r in rows.get('joint_dataset_sources', ()) if r['dataset_id'] == dataset['id']]
    require(len(dependencies) == len(expected) and
            {(r['role'], r['name']) for r in dependencies} == set(expected),
            'physical_joint_dependency_inventory')
    raw = {r['id']: r for r in rows['raw_assets']}
    sources = {r['id']: r for r in rows['source_records']}
    for row in dependencies:
        binding = expected[row['role'], row['name']]
        require(all(row[k] == binding[k] for k in ('asset_id','source_id','raw_sha256','raw_bytes','source_version')),
                'physical_joint_dependency_binding')
        asset, source = raw[row['asset_id']], sources[row['source_id']]
        actual = native.source_identity(SimpleNamespace(**asset), SimpleNamespace(**source),
            owner_id=owner, project_id=project)
        require({**actual, 'descriptor': binding['descriptor']} == binding and
                asset['detected_format'] == source['declared_format'] == 'joint_native' and
                asset['filename'] == row['name'] and asset['validation_status'] == 'raw_metadata_checked',
                'physical_joint_original_binding')
        key = f"projects/{owner}/{project}/{asset['id']}"
        require(asset['storage_key'] == key, 'physical_joint_original_key')
        meta = native.bounded_json(asset['physical_metadata'].encode())
        fields(meta, 'schema role name descriptor scientific_values_decoded scientific_accepted')
        require(meta == dict(schema='joint-native-member-1', role=row['role'], name=row['name'],
            descriptor=binding['descriptor'], scientific_values_decoded=False, scientific_accepted=False),
            'physical_joint_original_metadata')
        native.member_metadata(canonical(dict(role=row['role'], name=row['name'], descriptor=binding['descriptor'],
            source=dict(expected_bytes=asset['byte_count'], expected_sha256=asset['sha256']))))
        if row['name'].endswith('.json'):
            original = files.read(key, cap=INDEX_CAP, expected_bytes=asset['byte_count'], expected_sha256=asset['sha256'])
            if row['name'] in ('request.json','sealed.json'):
                require(native.bounded_json(original) == payload['manifests'][row['role']],
                        'physical_joint_manifest_changed')
        else:
            files.scan_joint_member(key, byte_count=asset['byte_count'], sha256=asset['sha256'],
                                    descriptor=binding['descriptor'])
    return payload


def result_inventory(rows, files, job):
    """One exact terminal index and every copy, even failed/cancelled output."""
    request = native.bounded_json(job['request_json'].encode())
    require(byte_sha(canonical(request)) == job['request_sha256'], 'physical_joint_request_changed')
    for key in ('id','owner_id','project_id','dataset_id'): uuid(job[key])
    sha(job['dataset_sha256']); sha(job['request_sha256'])
    require(job['method_id'] == METHOD, 'physical_joint_method')
    members = [r for r in rows.get('joint_result_artifacts', ()) if r['job_id'] == job['id']]
    if job['result_key'] is None:
        require(not members and job['result_bytes'] is None and job['result_sha256'] is None,
                'physical_joint_missing_index')
        require(job['state'] != 'succeeded', 'physical_joint_success_without_custody')
        return None, ()
    require(job['state'] in ('succeeded','failed','cancelled'), 'physical_joint_nonterminal_index')
    key = f"derived/{job['owner_id']}/{job['project_id']}/results/{job['id']}.json"
    require(job['result_key'] == key, 'physical_joint_index_key')
    raw = files.read(key, cap=INDEX_CAP, expected_bytes=job['result_bytes'], expected_sha256=job['result_sha256'])
    payload = native.bounded_json(raw)
    binding = {k: job[k] for k in ('owner_id','project_id','dataset_id','dataset_sha256','method_id','request_sha256')}
    binding['job_id'] = job['id']
    fields(payload, 'schema state members native_bytes scientific_acceptance authenticity_verified public_activation '+ ' '.join(binding))
    require(payload['schema'] == INDEX_SCHEMA and payload['state'] == job['state'] and
            all(payload[k] == v for k,v in binding.items()) and
            all(payload[k] is False for k in ('scientific_acceptance','authenticity_verified','public_activation')),
            'physical_joint_index_binding')
    require(type(payload['members']) is dict and 0 < len(payload['members']) <= 1100 and
            len(members) == len(payload['members']) and
            {r['name'] for r in members} == set(payload['members']), 'physical_joint_result_inventory')
    total, declarations = 0, []
    for row in members:
        name = row['name']
        require(type(name) is str and NAME.fullmatch(name) is not None, 'physical_joint_member_name')
        count = integer(row['byte_count'], 1, native.MAX_BYTES); sha(row['sha256'])
        total += count; require(total <= native.MAX_BYTES, 'physical_joint_whole_cap')
        require(all(row[k] == v for k,v in binding.items()) and
                payload['members'][name] == dict(byte_count=count, sha256=row['sha256']),
                'physical_joint_member_binding')
        key = f"derived/{job['owner_id']}/{job['project_id']}/joint/{job['id']}/{name}"
        require(row['storage_key'] == key, 'physical_joint_member_key')
        declarations.append((key, dict(cap=native.MAX_BYTES, bytes=count, sha256=row['sha256'])))
    require(type(payload['native_bytes']) is int and payload['native_bytes'] == total,
            'physical_joint_native_total')
    return payload, tuple(declarations)


def accounting(connection, owner_id):
    """Additive M11 charge; base already counts successful result indexes."""
    uuid(owner_id)
    require(connection.in_transaction, 'physical_joint_account_snapshot')
    cursor = connection.execute('SELECT byte_count FROM joint_result_artifacts WHERE owner_id=?', (owner_id,))
    members = sum(integer(r[0], 1, native.MAX_BYTES) for r in cursor)
    indices = active = 0
    for state, count in connection.execute('SELECT state,result_bytes FROM processing_jobs WHERE owner_id=? AND method_id=?', (owner_id, METHOD)):
        require(state in ('queued','running','succeeded','failed','cancelled'), 'physical_joint_job_state')
        if state in ('queued','running'):
            require(count is None, 'physical_joint_active_index')
            active += native.MAX_BYTES
        elif state != 'succeeded' and count is not None:
            indices += integer(count, 1, INDEX_CAP)
    return dict(joint_members=members, joint_terminal_indices=indices, joint_active=active)


def audit_snapshot(rows, files):
    """Return exact declarations only after all joint SQL and source joins.

    The enclosing classifier still must close its complete namespace census.
    This reader never grants a deletion or successful scientific disposition.
    """
    datasets = {r['id']: r for r in rows['observation_datasets'] if r['parser_version'] == native.PARSER}
    jobs = {r['id']: r for r in rows['processing_jobs'] if r['method_id'] == METHOD}
    require(all(r['dataset_id'] in datasets for r in rows.get('joint_dataset_sources', ())),
            'physical_joint_orphan_source')
    require(all(r['job_id'] in jobs for r in rows.get('joint_result_artifacts', ())),
            'physical_joint_orphan_result')
    expected, indices = {}, set()
    for dataset in datasets.values():
        key = f"derived/{dataset['owner_id']}/{dataset['project_id']}/datasets/{dataset['id']}.json"
        require(dataset['storage_key'] == key and dataset['payload_schema'] == 'geophysics.joint-native-dataset/v1',
                'physical_joint_dataset_key')
        dataset_inventory(rows, files, dataset)
        expected[key] = dict(cap=INDEX_CAP, bytes=dataset['byte_count'], sha256=dataset['sha256'])
    for job in jobs.values():
        dataset = datasets.get(job['dataset_id'])
        require(dataset is not None and (job['owner_id'],job['project_id'],job['dataset_sha256']) ==
                (dataset['owner_id'],dataset['project_id'],dataset['sha256']), 'physical_joint_job_input')
        payload, members = result_inventory(rows, files, job)
        if payload is not None:
            indices.add(job['id'])
            expected[job['result_key']] = dict(cap=INDEX_CAP, bytes=job['result_bytes'], sha256=job['result_sha256'])
            for key, record in members:
                require(key not in expected, 'physical_joint_duplicate_file')
                expected[key] = record
    return dict(dataset_ids=frozenset(datasets), job_ids=frozenset(jobs), index_ids=frozenset(indices), files=expected)
