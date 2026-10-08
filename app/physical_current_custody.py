"""Positive current deletion custody dispatch; historical v1 stays frozen.

V2 adds only named M08 extra-result members in the original derived trash
directory. It grants no deletion, cleanup, scientific or filesystem authority.
The full retired projection must separately bind each job/member/size/hash.
"""

from app.physical_contract import (
    CUSTODY_HEADER, M, canonical, custody_file, custody_header, decode_source,
    digest, fields, integer, require, sha, text, uuid, validate_custody,
)


SCHEMA = 'geophysics.physical-custody/v2'


def validate_current_custody(value):
    require(type(value) is dict, 'current_custody_object')
    if value.get('schema') == 'geophysics.physical-custody/v1':
        return validate_custody(value)
    fields(value, CUSTODY_HEADER + ' initial_files removed_ordinals')
    require(value['schema'] == SCHEMA and value['origin_kind'] == 'project_deletion',
            'current_custody_dispatch')
    header = {key:value[key] for key in CUSTODY_HEADER.split()}
    # Reuse the closed unchanged original header predicates, not a fallback for
    # new fields/origins. Only v2 project-deletion slots receive the new grammar.
    inherited = dict(header, schema='geophysics.physical-custody/v1')
    custody_header(inherited)
    entries = value['initial_files']
    require(type(entries) is list and len(entries) <= 4096, 'current_custody_count')
    ordinals, slots = [], set()
    from app.waveform_contract import MEMBER, SCRATCH
    for item in entries:
        fields(item, 'ordinal role location artifact_id leaf max_bytes actual_bytes actual_sha256')
        text(item['leaf'], 180)
        if item['leaf'].startswith('waveforms/'):
            pieces = item['leaf'].split('/')
            require(len(pieces) == 3 and pieces[0] == 'waveforms'
                    and uuid(pieces[1]) == uuid(item['artifact_id'])
                    and MEMBER.fullmatch(pieces[2]) is not None
                    and (item['role'], item['location']) == ('result_copy', 'deleting_derived'),
                    'current_custody_waveform_member')
            integer(item['ordinal'], 1, 4096)
            integer(item['max_bytes'], 1, SCRATCH)
            integer(item['actual_bytes'], 0, item['max_bytes'])
            sha(item['actual_sha256'])
            require(len(canonical(item)) <= 1024, 'current_custody_file_cap')
        else:
            custody_file(item, inherited)
        ordinals.append(item['ordinal'])
        slot = item['location'], item['leaf']
        require(slot not in slots, 'current_custody_duplicate_slot')
        slots.add(slot)
    require(ordinals == sorted(set(ordinals)), 'current_custody_ordinals')
    removed = value['removed_ordinals']
    require(type(removed) is list and all(type(n) is int for n in removed)
            and removed == sorted(set(removed)) and set(removed) <= set(ordinals), 'current_custody_removed_subset')
    require(value['capacity_bytes'] == max(1, sum(e['actual_bytes'] for e in entries)), 'current_custody_capacity')
    require(len(canonical(value)) <= 4*M, 'current_custody_inventory_cap')
    return dict(retained_bytes=sum(e['actual_bytes'] for e in entries if e['ordinal'] not in removed),
                initial_inventory_sha256=digest(dict(value,removed_ordinals=[])), current_inventory_sha256=digest(value))


def parse_current_custody(chunks):
    value = decode_source(chunks, max_bytes=4*M, depth=8, nodes=100000)
    validate_current_custody(value)
    return value
