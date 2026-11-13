"""Distinct source-owned incomplete custody, never successful execution evidence.

The recovery owner's validators remain canonical. This consumer adds independent
installation/SQL/receipt and actual private-file closure under caller exclusion.
Nothing is deleted, adopted or upgraded, and no process is launched here.
"""
from copy import deepcopy

from app.errors import ApiError
from app.physical_contract import byte_sha, canonical, fields, require, uuid
from app.profile_archive_custody import (
    ARCHIVE_CAP, IDENTITY, MANIFEST_CAP, RECORD, RELATION, _installation, _json, _relation,
)

SCHEMA = 'geophysics.profile-incomplete-custody/v1'
NAMESPACE = '.profile-incomplete'


def _record(manifest, relation, approved):
    from app.profile_incomplete_recovery import validate_manifest, incomplete_descriptor
    _relation(relation); _installation(approved)
    require(relation['state'] in ('failed', 'cancelled'), 'profile_incomplete_terminal')
    expected = dict(job_id=relation['id'], terminal_state=relation['state'], method_id=relation['method_id'],
                    request_sha256=relation['request_sha256'], **{k:relation[k] for k in IDENTITY.split()})
    try:
        validate_manifest(manifest, expected)
        record = incomplete_descriptor(manifest)
    except (ApiError, ValueError, KeyError, TypeError):
        raise ValueError('profile_incomplete_manifest') from None
    require(canonical(manifest['installation']) == canonical(approved), 'profile_incomplete_authority')
    fields(record, RECORD)
    require(record['schema'] == SCHEMA, 'profile_incomplete_descriptor_registry')
    return deepcopy(record)


def validate_saved_entry(value, *, owner_id, project_id, approved_installations):
    fields(value, RECORD)
    require(value['schema'] == SCHEMA and (value['owner_id'], value['project_id']) == (owner_id, project_id),
            'profile_incomplete_saved_owner')
    relation = dict(id=value['job_id'], state=value['terminal_state'], method_id=value['method_id'],
                    request_sha256=value['request_sha256'], **{k:value[k] for k in IDENTITY.split()})
    require(value['job_id'] in approved_installations, 'profile_incomplete_unapproved_installation')
    expected = _record(value['manifest'], relation, approved_installations[value['job_id']])
    require(canonical(value) == canonical(expected), 'profile_incomplete_saved_binding')
    return relation


def incomplete_inventory(files, relations, receipts, *, approved_installations):
    """Independent complete census; absence cannot release a saved receipt charge."""
    require(type(relations) is list and type(receipts) is list and len(relations)+len(receipts) <= 100000,
            'profile_incomplete_relation_cap')
    require(type(approved_installations) is dict, 'profile_incomplete_registry')
    live, saved = {}, {}
    for relation in relations:
        fields(relation, RELATION); uuid(relation['id'])
        require(relation['id'] not in live, 'profile_incomplete_duplicate_job')
        live[relation['id']] = relation
    for receipt in receipts:
        for key in ('id', 'owner_id', 'project_id'): uuid(receipt[key])
        entries = receipt['derived_manifest'] or []
        require(type(entries) is list and len(entries) <= 4096, 'profile_incomplete_receipt_cap')
        for entry in entries:
            require(type(entry) is dict, 'profile_incomplete_receipt_entry')
            # Other registered receipts are independently checked by the
            # successful/complete dispatcher. Never treat them as this schema.
            if entry.get('schema') != SCHEMA: continue
            relation = validate_saved_entry(entry, owner_id=receipt['owner_id'], project_id=receipt['project_id'],
                                            approved_installations=approved_installations)
            identifier = relation['id']
            require(identifier not in saved and identifier not in live, 'profile_incomplete_duplicate_custody')
            saved[identifier] = (relation, entry)
    try:
        names = set(files.names(NAMESPACE, limit=256))
    except FileNotFoundError:
        require(not saved, 'profile_incomplete_missing_custody')
        return []
    files.private_directory_identity(NAMESPACE)
    allowed = {n for j in (*live, *saved) for n in (j, j+'.intent.json')}
    require(names <= allowed, 'profile_incomplete_unknown_name')
    present = {n.removesuffix('.intent.json') for n in names}
    require(set(saved) <= present and len(present) <= 128, 'profile_incomplete_missing_custody')
    records = []
    for identifier in sorted(present):
        require({identifier, identifier+'.intent.json'} <= names, 'profile_incomplete_interrupted_pair')
        require(identifier in approved_installations, 'profile_incomplete_unapproved_installation')
        relation = live[identifier] if identifier in live else saved[identifier][0]
        intent, _ = files.private_member(f'{NAMESPACE}/{identifier}.intent.json', cap=MANIFEST_CAP)
        manifest = _json(intent, MANIFEST_CAP)
        record = _record(manifest, relation, approved_installations[identifier])
        require(intent == canonical(manifest), 'profile_incomplete_canonical_intent')
        if identifier in saved:
            require(canonical(record) == canonical(saved[identifier][1]), 'profile_incomplete_changed_deleted_custody')
        prefix = f'{NAMESPACE}/{identifier}'
        require(files.private_directory_identity(prefix) == manifest['stage_identity'], 'profile_incomplete_replaced_stage')
        require(set(files.names(prefix, limit=4)) == set(manifest['members']) | {'manifest.json'},
                'profile_incomplete_unknown_member')
        body, _ = files.private_member(prefix+'/manifest.json', cap=MANIFEST_CAP,
                                      expected_bytes=len(intent), expected_sha256=byte_sha(intent))
        require(body == intent, 'profile_incomplete_manifest_pair')
        from app.profile_incomplete_recovery import MEMBER_CAPS
        for name, member in manifest['members'].items():
            _, measured = files.private_member(prefix+'/'+name, cap=MEMBER_CAPS[name],
                                               expected_bytes=member['bytes'], expected_sha256=member['sha256'])
            require(measured == member, 'profile_incomplete_member_identity')
        records.append(record)
        require(sum(x['charged_bytes'] for x in records) <= ARCHIVE_CAP, 'profile_incomplete_global_cap')
    return records
