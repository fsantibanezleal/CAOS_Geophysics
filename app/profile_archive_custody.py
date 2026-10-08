"""Closed retained-profile custody; no archive/raw deletion or science replay.

Caller supplies independently approved installation bindings and holds writer
exclusion plus a consistent SQL snapshot. This reader does not fabricate either.
Deletion entries survive in the existing receipt, outside cascading job/project
relations. Unknown or absent retained files never release a byte of charge.
"""

from copy import deepcopy
import json
import math

from app.physical_contract import byte_sha, canonical, fields, integer, require, sha, uuid

M = 1048576
ARCHIVE_CAP = 256*M
STAGE_CAP = 64*M
MANIFEST_CAP = 262144
SCHEMA = 'geophysics.profile-retained-custody/v1'
METHODS = frozenset(('ert.topographic-profile/v1','traveltime.first-arrival-profile/v1'))
SOURCE_FILES = (
    'app/profile_linux_exec.py','scripts/profile_linux_supervisor.py','scripts/profile_linux_child.py',
    'scripts/process_profile_job.py','scripts/process_supplied_profile.py','data-pipeline/ert.py',
    'data-pipeline/traveltime.py','data-pipeline/profile_mesh.py','data-pipeline/supplied_profiles.py',
    'data-pipeline/sources.py','data/source-ledger.json',
)
IDENTITY = 'owner_id project_id dataset_id raw_asset_id source_id dataset_sha256 raw_sha256'
RELATION = 'id '+IDENTITY+' request_sha256 method_id state'
MANIFEST_V1 = 'schema job_id request_sha256 installation stage_identity members recovery uncommitted_duplicate'
MANIFEST_V2 = MANIFEST_V1+' ownership'
OWNERSHIP = IDENTITY+' job_id method_id terminal_state request_sha256'
INSTALLATION = 'configuration_sha256 python_sha256 environment_sha256 invocation_sha256 source_hashes'
RECOVERY = 'schema job_id receipt_sha256 intent_sha256 installation retained_stage_identity terminal known_root_copies_removed'
EXECUTION = ('schema job_id request_sha256 dataset_sha256 raw_sha256 environment_sha256 unit terminal stop_reason failure '
    'launch_attempted extinction guardian_status guardian_scope invocation_sha256 source_hashes configuration_sha256 '
    'python_sha256 mounted_input_identities retained_stage_identity wall_seconds resources retained originals_reverified '
    'held_inputs_state cpu_accounting_admitted host_admission')
RECORD = ('schema job_id '+IDENTITY+' method_id terminal_state request_sha256 installation_sha256 '
          'manifest manifest_bytes manifest_sha256 charged_bytes')
MEMBERS = {'linux-execution.json':65536,'result.json':8*M,'linux-stderr.txt':32*M}


def _json(body, cap):
    # Archive native metadata is not the immutable scientific JSON dialect:
    # actual inode identifiers may exceed the latter's JavaScript-safe bound.
    require(type(body) is bytes and 0<len(body)<=cap,'profile_archive_json_cap')
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'profile_archive_duplicate_key')
            result[key]=value
        return result
    def constant(_):
        raise ValueError('profile_archive_nonfinite')
    try:
        value=json.loads(body.decode('utf-8','strict'),object_pairs_hook=pairs,parse_constant=constant)
    except (UnicodeError,json.JSONDecodeError,RecursionError):
        raise ValueError('profile_archive_json') from None
    pending=[(value,0)]; count=0
    while pending:
        item,depth=pending.pop(); count+=1
        require(count<=20000 and depth<=16,'profile_archive_json_structure')
        if type(item) is dict:
            pending.extend((v,depth+1) for v in item.values())
            pending.extend((k,depth+1) for k in item)
        elif type(item) is list:
            pending.extend((v,depth+1) for v in item)
        elif type(item) is str:
            require(len(item.encode('utf-8'))<=8192 and '\0' not in item,'profile_archive_json_string')
        elif type(item) is int:
            require(abs(item)<=2**64-1,'profile_archive_native_integer')
        elif type(item) is float:
            require(math.isfinite(item),'profile_archive_nonfinite')
        else:
            require(item is None or type(item) is bool,'profile_archive_json_type')
    return value


def _installation(value):
    fields(value,INSTALLATION)
    for key in INSTALLATION.split()[:-1]:
        sha(value[key])
    require(type(value['source_hashes']) is dict and set(value['source_hashes'])==set(SOURCE_FILES),
            'profile_archive_sources')
    for value in value['source_hashes'].values():
        sha(value)


def _identity(value):
    fields(value,'device inode')
    integer(value['device'],0,2**64-1); integer(value['inode'],1,2**64-1)


def _relation(value):
    fields(value,RELATION)
    for key in ('id','owner_id','project_id','dataset_id','raw_asset_id','source_id'):
        uuid(value[key])
    for key in ('dataset_sha256','raw_sha256','request_sha256'):
        sha(value[key])
    require(value['method_id'] in METHODS and value['state'] in ('succeeded','failed','cancelled'),
            'profile_archive_terminal_relation')


def _manifest(value, relation, approved):
    require(type(value) is dict,'profile_archive_manifest')
    schema=value.get('schema')
    require(schema == 'geophysics.profile-retained-stage/v2',
            'profile_archive_schema')
    fields(value,MANIFEST_V2)
    _relation(relation); _installation(approved)
    require(value['job_id']==relation['id'] and value['request_sha256']==relation['request_sha256'],
            'profile_archive_relation')
    ownership=value['ownership']; fields(ownership,OWNERSHIP)
    require(all(ownership[key]==relation[key] for key in IDENTITY.split()) and
            ownership['job_id']==relation['id'] and ownership['request_sha256']==relation['request_sha256'] and
            ownership['method_id']==relation['method_id'] and ownership['terminal_state']==relation['state'],
            'profile_archive_relation')
    _installation(value['installation'])
    require(canonical(value['installation'])==canonical(approved),'profile_archive_authority')
    _identity(value['stage_identity'])
    members=value['members']
    require(type(members) is dict and 'linux-execution.json' in members and set(members)<=set(MEMBERS),
            'profile_archive_members')
    for name,member in members.items():
        fields(member,'bytes sha256'); integer(member['bytes'],0,MEMBERS[name]); sha(member['sha256'])
    require(sum(m['bytes'] for m in members.values())<=STAGE_CAP,'profile_archive_stage_cap')
    recovery=value['recovery']; fields(recovery,RECOVERY)
    require(recovery['schema']=='geophysics.profile-linux-recovery/v1' and recovery['job_id']==relation['id'] and
            recovery['receipt_sha256']==members['linux-execution.json']['sha256'] and
            recovery['installation']==approved and recovery['retained_stage_identity']==value['stage_identity'] and
            recovery['known_root_copies_removed'] is True,'profile_archive_recovery')
    sha(recovery['intent_sha256'])
    units={f'geophysics-profile-{relation["id"]}.service',f'geophysics-profile-guardian-{relation["id"]}.scope'}
    require(type(recovery['terminal']) is dict and set(recovery['terminal'])==units,'profile_archive_units')
    for unit,state in recovery['terminal'].items():
        require(type(state) is dict and set(state) in (
            {'MainPID','ActiveState','SubState','ControlGroup'},{'ActiveState','SubState','ControlGroup'}) and
            ('MainPID' in state or unit.endswith('.scope')) and state.get('MainPID','0')=='0' and
            state['ActiveState'] in ('inactive','failed') and state['SubState'] in ('dead','failed','exited') and
            state['ControlGroup'] in ('','/system.slice/'+unit),'profile_archive_not_quiescent')
    duplicate=value['uncommitted_duplicate']
    if duplicate is not None:
        fields(duplicate,'bytes sha256 name')
        integer(duplicate['bytes'],1,8*M); sha(duplicate['sha256'])
        require(duplicate['name']==relation['id']+'.json' and relation['state']!='succeeded',
                'profile_archive_duplicate_identity')
    body=canonical(value)
    require(0<len(body)<=MANIFEST_CAP,'profile_archive_manifest_cap')
    return body


def _record(manifest,relation,approved):
    body=_manifest(manifest,relation,approved)
    return dict(schema=SCHEMA,job_id=relation['id'],**{key:relation[key] for key in IDENTITY.split()},
        method_id=relation['method_id'],terminal_state=relation['state'],request_sha256=relation['request_sha256'],
        installation_sha256=byte_sha(canonical(approved)),manifest=deepcopy(manifest),manifest_bytes=len(body),
        manifest_sha256=byte_sha(body),charged_bytes=2*len(body)+sum(m['bytes'] for m in manifest['members'].values()))


def validate_saved_entry(value, *, owner_id, project_id, approved_installations):
    fields(value,RECORD)
    require(value['schema']==SCHEMA and value['owner_id']==owner_id and value['project_id']==project_id,
            'profile_archive_saved_owner')
    relation=dict(id=value['job_id'],state=value['terminal_state'],method_id=value['method_id'],
                  request_sha256=value['request_sha256'],**{key:value[key] for key in IDENTITY.split()})
    require(value['job_id'] in approved_installations,'profile_archive_unapproved_installation')
    expected=_record(value['manifest'],relation,approved_installations[value['job_id']])
    require(canonical(value)==canonical(expected),'profile_archive_saved_binding')
    return relation


def retained_inventory(files, relations, receipts, *, approved_installations):
    """Complete closed archive-only census, separate from the global forest census.

    The fixed namespace is read only. Nonarchived jobs are not required to have
    archives. A lone intent is an interrupted recovery, never delete authority.
    Approval is independently supplied, never taken from an uploaded manifest.
    """
    require(type(relations) is list and type(receipts) is list and len(relations)+len(receipts)<=100000,
            'profile_archive_relation_cap')
    require(type(approved_installations) is dict,'profile_archive_registry')
    live={}; saved={}
    for relation in relations:
        # Nonterminal relations remain declared so an actual archive for one
        # fails on terminal eligibility, rather than being silently omitted.
        fields(relation,RELATION); uuid(relation['id'])
        require(relation['id'] not in live,'profile_archive_duplicate_job')
        live[relation['id']]=relation
    for receipt in receipts:
        for key in ('id','owner_id','project_id'): uuid(receipt[key])
        entries=receipt['derived_manifest'] or []
        require(type(entries) is list and len(entries)<=4096,'profile_archive_receipt_cap')
        for entry in entries:
            require(type(entry) is dict,'profile_archive_receipt_entry')
            if entry.get('schema')==SCHEMA:
                relation=validate_saved_entry(entry,owner_id=receipt['owner_id'],project_id=receipt['project_id'],
                    approved_installations=approved_installations)
                identifier=relation['id']
                require(identifier not in saved and identifier not in live,'profile_archive_duplicate_custody')
                saved[identifier]=(relation,entry)
            else:
                # Only the unchanged original derived receipt tuple is skipped;
                # this bridge cannot silently skip a future custody extension.
                require(set(entry)=={'kind','id','sha256','byte_count'} and entry['kind'] in ('dataset','result'),
                        'profile_archive_unknown_receipt_entry')
    try:
        names=set(files.names('.profile-retained',limit=127))
    except FileNotFoundError:
        require(not saved,'profile_archive_missing_custody')
        return []
    allowed={name for identifier in (*live,*saved) for name in (identifier,identifier+'.intent.json')}
    require(names<=allowed,'profile_archive_unknown_name')
    records=[]
    present={name.removesuffix('.intent.json') for name in names}
    require(set(saved)<=present,'profile_archive_missing_custody')
    for identifier in sorted(present):
        require({identifier,identifier+'.intent.json'}<=names,'profile_archive_interrupted_pair')
        require(identifier in approved_installations,'profile_archive_unapproved_installation')
        relation=live[identifier] if identifier in live else saved[identifier][0]
        intent=files.read(f'.profile-retained/{identifier}.intent.json',cap=MANIFEST_CAP,expected_bytes=None,expected_sha256=None)
        manifest=_json(intent,MANIFEST_CAP)
        record=_record(manifest,relation,approved_installations[identifier])
        require(intent==canonical(manifest),'profile_archive_canonical_intent')
        if identifier in saved:
            require(canonical(record)==canonical(saved[identifier][1]),'profile_archive_changed_deleted_custody')
        prefix=f'.profile-retained/{identifier}'
        require(set(files.names(prefix,limit=4))==set(manifest['members'])|{'manifest.json'},'profile_archive_unknown_member')
        require(files.directory_identity(prefix)==manifest['stage_identity'],'profile_archive_replaced_stage')
        files.read(prefix+'/manifest.json',cap=MANIFEST_CAP,expected_bytes=len(intent),expected_sha256=byte_sha(intent))
        for name,member in manifest['members'].items():
            body=files.read(prefix+'/'+name,cap=MEMBERS[name],expected_bytes=member['bytes'],expected_sha256=member['sha256'])
            if name=='linux-execution.json':
                execution=_json(body,65536); fields(execution,EXECUTION)
                require(body==canonical(execution) and execution['schema']=='geophysics.profile-linux-execution/v1' and
                        execution['job_id']==identifier and execution['request_sha256']==relation['request_sha256'] and
                        execution['dataset_sha256']==relation['dataset_sha256'] and execution['raw_sha256']==relation['raw_sha256'] and
                        execution['retained_stage_identity']==manifest['stage_identity'] and
                        all(execution[key]==approved_installations[identifier][key] for key in INSTALLATION.split()),
                        'profile_archive_execution_identity')
                retained=execution['retained']
                require(type(retained) is dict and set(retained)<= {'result.json','stderr.txt'},'profile_archive_retained')
                for producer,leaf in (('result.json','result.json'),('stderr.txt','linux-stderr.txt')):
                    require((producer in retained)==(leaf in manifest['members']),'profile_archive_retained')
                    if producer in retained:
                        require(retained[producer]==manifest['members'][leaf],'profile_archive_retained')
        records.append(record)
        require(sum(x['charged_bytes'] for x in records)<=ARCHIVE_CAP,'profile_archive_global_cap')
    return records


def deletion_entries(records, *, owner_id, project_id):
    uuid(owner_id); uuid(project_id)
    return deepcopy([record for record in records if (record['owner_id'],record['project_id'])==(owner_id,project_id)])


def attach_deletion_entries(connection, *, receipt_id, owner_id, project_id, entries):
    """Attach inside the existing delete transaction; never delete rows or files.

    Entries must come from the fresh excluded inventory above in this transaction.
    This is not an HTTP-callable authority constructor or an independent delete.
    """
    require(connection.in_transaction,'profile_archive_delete_transaction')
    for value in (receipt_id,owner_id,project_id): uuid(value)
    require(type(entries) is list and len(entries)<=63,'profile_archive_delete_entries')
    for entry in entries:
        fields(entry,RECORD)
        require(entry['schema']==SCHEMA and (entry['owner_id'],entry['project_id'])==(owner_id,project_id),
                'profile_archive_delete_owner')
    row=connection.execute('SELECT derived_manifest FROM deletion_receipts WHERE id=? AND owner_id=? AND project_id=?',
                           (receipt_id,owner_id,project_id)).fetchone()
    require(row is not None,'profile_archive_delete_receipt')
    prior=[] if row[0] is None else _json(row[0].encode(),4*M)
    require(type(prior) is list and len(prior)+len(entries)<=4096,'profile_archive_delete_receipt_cap')
    require(not any(item.get('schema')==SCHEMA for item in prior),'profile_archive_immutable_receipt')
    body=canonical(prior+entries)
    require(len(body)<=4*M,'profile_archive_delete_receipt_cap')
    connection.execute('UPDATE deletion_receipts SET derived_manifest=? WHERE id=? AND owner_id=? AND project_id=?',
                       (body.decode(),receipt_id,owner_id,project_id))
