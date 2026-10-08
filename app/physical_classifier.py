"""Read-only whole-successor outcome and closed namespace classification.

The caller owns the consistent transaction and exclusion. This module grants
no native lease, runtime admission, repair, scientific solve or file adoption.
Every disconnected family and deleted partition is audited before dispositions.
Only source-bound current0005 deletion extensions are positively dispatched.
"""

from dataclasses import dataclass
import math
import sqlite3
import time
from types import MappingProxyType, SimpleNamespace

from app.physical_accounting import account_private_charge
from app.physical_contract import (
    CORRECTION, TRANSFORM, M, byte_sha, canonical, custody_file, custody_header,
    decode_source, digest, fields, integer, require, sha,
)
from app.errors import ApiError
from app.physical_debt import ERRORS
from app.physical_current_custody import parse_current_custody, validate_current_custody
from app.physical_forest import SUCCESSOR_DDL, _row, _targets
from app.physical_persistence import TABLES
from app.physical_publication import audit_correction_ancestry, audit_transform_producer, decode
from app.physical_producer import REQUEST_KEYS
from app.physical_roots import _verified
from app.physical_successor import FORMATS, METHODS, REVISION, ddl_sha256, predecessor_payload
from app.profile_archive_custody import METHODS as PROFILE_METHODS, retained_inventory, _json


@dataclass(frozen=True)
class Classification:
    classification: str
    reason: str
    operations: object
    account_charges: object
    inventory_sha256: str | None = None
    runtime: bool = False


def _snapshot(connection):
    """Preserve native SQL representations; no JSON reserialization backfill."""
    require(isinstance(connection, sqlite3.Connection) and connection.in_transaction,
            'physical_classifier_transaction')
    require(connection.execute('SELECT version_num FROM alembic_version').fetchall() == [(REVISION,)]
            and ddl_sha256(connection) == SUCCESSOR_DDL, 'physical_classifier_schema')
    deadline = time.monotonic() + 60
    connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
    try:
        require(connection.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
                and not connection.execute('PRAGMA foreign_key_check').fetchall(), 'physical_classifier_sql_integrity')
        from app.models import Base
        names = sorted(set(Base.metadata.tables) | set(TABLES) | {'alembic_version'})
        require({r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                == set(names), 'physical_classifier_tables')
        rows, descriptors = {}, {}
        count = byte_count = 0
        for name in names:
            require(time.monotonic() <= deadline, 'physical_classifier_deadline')
            columns = connection.execute(f'PRAGMA table_info("{name}")').fetchall()
            keys = [row[1] for row in sorted(columns, key=lambda r: r[5]) if row[5]]
            require(bool(keys), 'physical_classifier_primary_key')
            cursor = connection.execute(f'SELECT * FROM "{name}" ORDER BY ' + ','.join('"' + k + '"' for k in keys))
            headers = [c[0] for c in cursor.description]
            rows[name], descriptors[name] = [], []
            for values in cursor:
                count += 1
                require(count <= 100000 and time.monotonic() <= deadline, 'physical_classifier_row_cap')
                row, encoded = dict(zip(headers, values)), {}
                for key, value in row.items():
                    if value is None or type(value) is int:
                        encoded[key] = dict(type='null' if value is None else 'integer', value=value)
                    elif type(value) is float:
                        require(math.isfinite(value), 'physical_classifier_sql_finite')
                        encoded[key] = dict(type='real', value=value)
                    else:
                        require(type(value) in (str, bytes), 'physical_classifier_sql_type')
                        body = value.encode('utf-8', 'strict') if type(value) is str else value
                        byte_count += len(body)
                        require(len(body) <= 35*M and byte_count <= 512*M, 'physical_classifier_sql_byte_cap')
                        encoded[key] = dict(type='text' if type(value) is str else 'blob',
                                            bytes=len(body), sha256=byte_sha(body))
                rows[name].append(row)
                descriptors[name].append(encoded)
        return rows, descriptors
    finally:
        connection.set_progress_handler(None, 0)


def _custody_key(header, slot):
    if slot['location'] == 'stage':
        return f".job-staging/{header['stage_id']}/{slot['leaf']}"
    if slot['location'] == 'pending_target':
        return slot['leaf']
    if slot['location'] == 'deleting_raw':
        return f".deleting/{header['owner_id']}--{header['project_id']}/{slot['leaf']}"
    require(slot['location'] == 'deleting_derived', 'physical_classifier_custody_location')
    # The one original project DELETE moves this directory under .deleting.
    # A similarly named alternate namespace is not custody/adoption authority.
    return f".deleting/{header['owner_id']}--{header['project_id']}--derived/{slot['leaf']}"


class _PreparedOriginals:
    """Read-only exact relocation map, never arbitrary missing-file fallback.

    The closed final census independently requires XOR existence for every pair.
    A changed original, link, duplicate or unregistered path never falls through.
    """
    def __init__(self, original, pairs):
        self.original,self.pairs=original,pairs

    def __getattr__(self,name):
        return getattr(self.original,name)

    def read(self,key,**arguments):
        try:
            return self.original.read(key,**arguments)
        except FileNotFoundError:
            require(key in self.pairs,'physical_classifier_unregistered_missing_original')
            return self.original.read(self.pairs[key],**arguments)


class _Audit:
    def __init__(self, connection, files, rows, manifests, installations, metadata, source_policy):
        self.connection, self.files, self.rows = connection, files, rows
        self.manifests, self.installations = manifests, installations
        self.expected, self.absent, self.empty, self.operations = {}, set(), set(), {}
        require(type(manifests) is dict and type(installations) is dict and type(metadata) is dict,
                'physical_classifier_registration')
        # Exact operator-declared native files only; never wildcard DB suffixes.
        require(set(metadata) <= {'geophysics.sqlite3', 'geophysics.sqlite3-wal', 'geophysics.sqlite3-shm',
                                  '.physical-writers.lock', '.processing-worker.lock'},
                'physical_classifier_native_metadata')
        for key, record in metadata.items():
            fields(record, 'cap bytes sha256 required')
            self.declare(key, **record)
        self.projects = {row['id']: row for row in rows['projects']}
        self.raw = {row['id']: row for row in rows['raw_assets']}
        self.datasets = {row['id']: row for row in rows['observation_datasets']}
        self.jobs = {row['id']: row for row in rows['processing_jobs']}
        self.batches = {row['batch_id']: row for row in rows['physical_custody_batches']}
        self.controls = {row['job_id']: row for row in rows['physical_job_controls']}
        self.source_policy = source_policy
        self.deleted = {}
        self.relocations = {}
        self.predeletion = set()

    def deleted_projects(self):
        from app.physical_deleted_inventory import observe_receipt, validate_current_tombstone
        users = {r['id'] for r in self.rows['user']}
        retired_ids = {name: set() for name in ('raw_assets', 'datasets', 'jobs', 'sources')}
        for extension in self.rows['physical_deletion_extensions']:
            body = extension['tombstone_bytes']
            require(type(body) is bytes and byte_sha(body) == extension['tombstone_sha256']
                    and extension['schema_tag'] == 'geophysics.physical-deletion/v2',
                    'physical_classifier_deletion_hash')
            # Closed current dispatch uses the unchanged strict native lexer;
            # the historical schema validator deliberately refuses this origin.
            value = decode_source([body], max_bytes=16*M, depth=16, nodes=200000)
            require(canonical(value) == body, 'physical_classifier_deletion_encoding')
            receipt = validate_current_tombstone(value, expected_source_policy_sha256=self.source_policy,
                                                 approved_installations=self.installations)
            require((extension['receipt_id'], extension['owner_id'], extension['project_id']) ==
                    tuple(receipt[k] for k in ('id', 'owner_id', 'project_id'))
                    and observe_receipt(self.connection, receipt['id']) == value['legacy_receipt'],
                    'physical_classifier_native_receipt_binding')
            project = receipt['project_id']
            require(project not in self.projects and project not in self.deleted and receipt['owner_id'] in users,
                    'physical_classifier_deleted_project')
            owned = ('source_records', 'raw_assets', 'observation_datasets', 'processing_jobs',
                     'physical_dataset_families', 'physical_dataset_edges', 'physical_dataset_productions',
                     'physical_job_controls', 'physical_publication_intents')
            require(not any(r['project_id'] == project for table in owned for r in self.rows[table]),
                    'physical_classifier_deleted_live_rows')
            inventory = value['physical_inventory']
            mappings = {name: {r[key]: r for r in inventory[name]} for name, key in (
                ('raw_assets', 'asset_id'), ('datasets', 'dataset_id'), ('jobs', 'job_id'), ('custody', 'batch_id'))}
            actual = {r['batch_id']: r for r in self.batches.values() if r['project_id'] == project}
            require(set(actual) == set(mappings['custody']), 'physical_classifier_deleted_complete_custody')
            live_ids = dict(raw_assets=set(self.raw), datasets=set(self.datasets), jobs=set(self.jobs),
                            sources={r['id'] for r in self.rows['source_records']})
            closed_ids = dict(raw_assets=set(mappings['raw_assets']), datasets=set(mappings['datasets']),
                              jobs=set(mappings['jobs']), sources={r['source_id'] for r in mappings['raw_assets'].values()})
            for name, ids in closed_ids.items():
                require(not ids & (live_ids[name] | retired_ids[name]), 'physical_classifier_deleted_identity_overlap')
                retired_ids[name].update(ids)
            for identifier, record in actual.items():
                require((record['owner_id'], record['origin_kind'], record['origin_id']) ==
                        (receipt['owner_id'], mappings['custody'][identifier]['origin_kind'],
                         mappings['custody'][identifier]['origin_id']), 'physical_classifier_deleted_custody_binding')
            self.deleted[project] = dict(receipt=receipt, inventory=inventory, **mappings)
            # The original route leaves these known empty ancestors after its
            # directory rename. No deleted project subtree/file is admitted.
            for lane in ('projects','derived'):
                self.empty.update((lane,f"{lane}/{receipt['owner_id']}"))
            self.operations[receipt['id']] = 'retain_deleted_projection'

    def prepared_deletions(self):
        from app.physical_project_deletion import original_slots
        for batch in self.batches.values():
            if batch['origin_kind']!='project_deletion' or batch['project_id'] in self.deleted:
                continue
            self.ownership(batch)
            require(batch['origin_id']==batch['project_id'] and batch['state']=='sealed'
                    and batch['charged_bytes']==0 and batch['removed_us'] is None,
                    'physical_classifier_predeletion_state')
            require(not any(r['project_id']==batch['project_id'] for r in self.rows['deletion_receipts'])
                    and not any(r['project_id']==batch['project_id'] for r in self.rows['physical_publication_intents'])
                    and not any(r['project_id']==batch['project_id'] and r['state'] in ('queued','running')
                                for r in self.jobs.values()),'physical_classifier_predeletion_operation')
            body=batch['inventory_bytes']
            require(type(body) is bytes and byte_sha(body)==batch['inventory_sha256'],
                    'physical_classifier_predeletion_hash')
            inventory=parse_current_custody([body]); validate_current_custody(inventory)
            require(canonical(inventory)==body and not inventory['removed_ordinals'] and
                    all(batch[k]==v for k,v in inventory.items() if k not in ('schema','initial_files','removed_ordinals')),
                    'physical_classifier_predeletion_header')
            owner,project=batch['owner_id'],batch['project_id']
            self.empty.add('.deleting')
            projected=dict(raw_assets=[dict(asset_id=r['id'],bytes=r['byte_count'],sha256=r['sha256'])
                for r in sorted(self.raw.values(),key=lambda r:r['id']) if r['project_id']==project],
                datasets=[dict(dataset_id=r['id'],bytes=r['byte_count'],sha256=r['sha256'])
                for r in sorted(self.datasets.values(),key=lambda r:r['id']) if r['project_id']==project],
                jobs=[dict(job_id=r['id'],state=r['state'],result_bytes=r['result_bytes'],result_sha256=r['result_sha256'])
                for r in sorted(self.jobs.values(),key=lambda r:r['id']) if r['project_id']==project],
                waveform_artifacts=[dict(job_id=r['job_id'],name=r['name'],bytes=r['byte_count'],sha256=r['sha256'])
                for r in sorted(self.rows['waveform_result_artifacts'],key=lambda r:(r['job_id'],r['name']))
                if self.jobs[r['job_id']]['project_id']==project])
            require(inventory['initial_files']==original_slots(projected),'physical_classifier_predeletion_complete_files')
            sqlslots=sorted([r for r in self.rows['physical_custody_files'] if r['batch_id']==batch['batch_id']],key=lambda r:r['ordinal'])
            require(all(r['state']=='present' for r in sqlslots) and
                    [{k:v for k,v in r.items() if k not in ('state','batch_id')} for r in sqlslots]==inventory['initial_files'],
                    'physical_classifier_predeletion_slots')
            for slot in inventory['initial_files']:
                lane='projects' if slot['location']=='deleting_raw' else 'derived'
                key=f"{lane}/{owner}/{project}/{slot['leaf']}"
                require(key not in self.relocations,'physical_classifier_predeletion_overlap')
                self.relocations[key]=_custody_key(inventory,slot)
                for name in (key,self.relocations[key]):
                    parts=name.split('/')
                    self.empty.update('/'.join(parts[:n]) for n in range(1,len(parts)))
            self.predeletion.add(batch['batch_id'])
            self.operations[batch['batch_id']]='abandon_only'
        if self.relocations:
            self.files=_PreparedOriginals(self.files,self.relocations)

    def retired_custody(self, batch, inventory, charge):
        deleted = self.deleted[batch['project_id']]
        saved = deleted['custody'][batch['batch_id']]
        require(charge['initial_inventory_sha256'] == saved['initial_inventory_sha256']
                and batch['state'] in ('cleanup_pending', 'removed'), 'physical_classifier_deleted_custody_inventory')
        if batch['origin_kind'] == 'project_deletion':
            require(batch['origin_id'] == batch['project_id'] and batch['deletion_receipt_id'] == deleted['receipt']['id'],
                    'physical_classifier_deletion_receipt_custody')
            # Every originally moved copy is retained in the complete initial
            # inventory, including ordinals already durably acknowledged removed.
            # A repeated waveform job owns several differently named copies.
            # Include the exact leaf in projection, never SHA deduplication.
            projection = [(s['role'], s['artifact_id'], s['leaf'], s['actual_bytes'], s['actual_sha256'])
                          for s in inventory['initial_files']]
            expected = ([('raw_delete', r['asset_id'], r['asset_id'], r['bytes'], r['sha256']) for r in deleted['raw_assets'].values()] +
                [('dataset_copy', r['dataset_id'], f"datasets/{r['dataset_id']}.json", r['bytes'], r['sha256']) for r in deleted['datasets'].values()] +
                [('result_copy', r['job_id'], f"results/{r['job_id']}.json", r['result_bytes'], r['result_sha256']) for r in deleted['jobs'].values()
                 if r['state'] == 'succeeded'] +
                [('result_copy', r['job_id'], f"waveforms/{r['job_id']}/{r['name']}", r['bytes'], r['sha256'])
                 for r in deleted['inventory']['waveform_artifacts']])
            require(sorted(projection) == sorted(expected),
                    'physical_classifier_deletion_complete_files')
        else:
            raw = deleted['raw_assets'].get(batch['raw_asset_id'])
            require(raw is not None and (raw['sha256'], raw['bytes']) == (batch['raw_sha256'], batch['raw_bytes']),
                    'physical_classifier_deleted_custody_raw')
            if batch['origin_kind'] == 'root_stage':
                dataset = deleted['datasets'].get(batch['origin_id'])
                require(dataset is not None and dataset['kind'] == 'root' and dataset['raw_asset_id'] == batch['raw_asset_id']
                        and dataset['parser_version'] == batch['parser_version'], 'physical_classifier_deleted_root_stage')
            elif batch['origin_kind'] == 'job_stage':
                job = deleted['jobs'].get(batch['origin_id'])
                require(job is not None and job['method_id'] == batch['method_id']
                        and deleted['datasets'][job['dataset_id']]['raw_asset_id'] == batch['raw_asset_id'],
                        'physical_classifier_deleted_job_stage')

    def declare(self, key, *, cap, bytes, sha256, required=True):
        integer(cap, 1, 1024*M)
        require(type(required) is bool, 'physical_classifier_file_rule')
        if bytes is not None:
            integer(bytes, 0, cap)
        if sha256 is not None:
            sha(sha256)
        if key in self.relocations:
            # Both exact locations are optional individually, never both absent
            # or both present. No same-hash dedup or alternate directory exists.
            moved=self.relocations[key]
            value=dict(cap=cap,bytes=bytes,sha256=sha256,required=False)
            for destination in (key,moved):
                require(destination not in self.absent,'physical_classifier_removed_file')
                require(destination not in self.expected or self.expected[destination]==value,
                        'physical_classifier_file_overlap')
                self.expected[destination]=value
            return
        value = dict(cap=cap, bytes=bytes, sha256=sha256, required=required)
        require(key not in self.absent, 'physical_classifier_removed_file')
        if key in self.expected:
            require(self.expected[key] == value, 'physical_classifier_file_overlap')
        self.expected[key] = value

    def ownership(self, row):
        project = self.projects.get(row['project_id'])
        require(project is not None and project['owner_id'] == row['owner_id'], 'physical_classifier_owner')

    def originals(self):
        sources = {row['id']: row for row in self.rows['source_records']}
        for row in sources.values():
            self.ownership(row)
            require(row['declared_format'] in FORMATS | {'gravity_stations_json'}
                    and row['private_storage_permission'] == 'attested'
                    and row['rights_decision'] in ('mirror', 'provider-link-only', 'derivative-only'),
                    'physical_classifier_source')
        for row in self.raw.values():
            self.ownership(row)
            source = sources[row['source_id']]
            require((row['owner_id'], row['project_id'], row['sha256'], row['detected_format']) ==
                    tuple(source[k] for k in ('owner_id', 'project_id', 'sha256', 'declared_format'))
                    and source['expected_bytes'] in (None, row['byte_count'])
                    and row['validation_status'] == 'raw_metadata_checked', 'physical_classifier_original')
            require(row['storage_key'] == f"projects/{row['owner_id']}/{row['project_id']}/{row['id']}",
                    'physical_classifier_original_key')
            self.declare(row['storage_key'], cap=16*M if row['detected_format'] == 'gravity_stations_json' else 1024*M,
                         bytes=row['byte_count'], sha256=row['sha256'])

    def custody(self):
        by_batch = {key: [] for key in self.batches}
        for slot in self.rows['physical_custody_files']:
            by_batch[slot['batch_id']].append(slot)
        for batch in self.batches.values():
            if batch['batch_id'] in self.predeletion:
                # Full header/slot/native/body/charge/row projection was checked
                # before every scientific file read; final census closes XOR.
                continue
            header = {key: batch[key] for key in ('batch_id owner_id project_id origin_kind origin_id stage_id '
                'deletion_receipt_id raw_asset_id raw_sha256 raw_bytes parser_version method_id capacity_bytes').split()}
            header['schema'] = 'geophysics.physical-custody/v1'
            if type(batch['inventory_bytes']) is bytes:
                header['schema'] = parse_current_custody([batch['inventory_bytes']])['schema']
            # Header v2 is narrowly inherited project-deletion grammar only.
            if header['schema'] != 'geophysics.physical-custody/v1':
                require(header['schema'] == 'geophysics.physical-custody/v2' and
                        header['origin_kind'] == 'project_deletion', 'physical_classifier_custody_dispatch')
                custody_header(dict(header, schema='geophysics.physical-custody/v1'))
            else:
                custody_header(header)
            slots = sorted(by_batch[batch['batch_id']], key=lambda row: row['ordinal'])
            require(batch['state'] != 'quarantined', 'physical_classifier_quarantined')
            retired = batch['project_id'] in self.deleted
            if not retired and batch['origin_kind'] != 'project_deletion':
                self.ownership(batch)
                raw = self.raw.get(batch['raw_asset_id'])
                require(raw is not None and (raw['owner_id'], raw['project_id'], raw['sha256'], raw['byte_count']) ==
                        tuple(batch[k] for k in ('owner_id', 'project_id', 'raw_sha256', 'raw_bytes')),
                        'physical_classifier_custody_raw')
            elif not retired:
                require(False, 'physical_classifier_deletion_extension_required')
            if batch['state'] in ('reserved', 'active'):
                require(batch['inventory_bytes'] is None and batch['inventory_sha256'] is None
                        and batch['sealed_us'] is None and batch['removed_us'] is None
                        and batch['charged_bytes'] == batch['capacity_bytes'] and 1 <= len(slots) <= 64,
                        'physical_classifier_reservation')
                require(batch['origin_kind'] in ('root_stage', 'job_stage'), 'physical_classifier_reservation_origin')
                for slot in slots:
                    require(slot['state'] == 'reserved', 'physical_classifier_unsealed_slot')
                    entry = {k: v for k, v in slot.items() if k not in ('state', 'batch_id')}
                    custody_file(entry, header, measured=False)
                    self.declare(_custody_key(header, entry), cap=entry['max_bytes'], bytes=None,
                                 sha256=None, required=False)
                self.operations[batch['batch_id']] = 'retain_reservation'
            else:
                body = batch['inventory_bytes']
                require(type(body) is bytes and byte_sha(body) == batch['inventory_sha256'],
                        'physical_classifier_custody_hash')
                inventory = parse_current_custody([body])
                charge = validate_current_custody(inventory)
                require(all(inventory[k] == v for k, v in header.items())
                        and charge['retained_bytes'] == batch['charged_bytes'], 'physical_classifier_custody_charge')
                if retired:
                    self.retired_custody(batch, inventory, charge)
                entries, removed = [], []
                for slot in slots:
                    require(slot['state'] in ('present', 'removed'), 'physical_classifier_measured_slot')
                    if slot['state'] == 'removed':
                        removed.append(slot['ordinal'])
                    entries.append({k: v for k, v in slot.items() if k not in ('state', 'batch_id')})
                require(entries == inventory['initial_files'] and removed == inventory['removed_ordinals'],
                        'physical_classifier_custody_slots')
                require((batch['state'] == 'removed') == (batch['charged_bytes'] == 0 and len(removed) == len(entries))
                        and (batch['removed_us'] is not None) == (batch['state'] == 'removed'),
                        'physical_classifier_custody_removal')
                for slot in entries:
                    key = _custody_key(header, slot)
                    if slot['location'] in ('deleting_raw', 'deleting_derived'):
                        # Exact historically declared parents may be empty
                        # after acknowledged cleanup; no wildcard trash adoption.
                        parts = key.split('/')
                        self.empty.update('/'.join(parts[:n]) for n in range(1, len(parts)))
                    if slot['ordinal'] in removed:
                        require(key not in self.expected, 'physical_classifier_removed_overlap')
                        self.absent.add(key)
                    else:
                        self.declare(key, cap=slot['max_bytes'], bytes=slot['actual_bytes'],
                                     sha256=slot['actual_sha256'])
                self.operations[batch['batch_id']] = 'retain_debt' if batch['state'] != 'removed' else 'retain_removal_record'
            if batch['stage_id'] is not None:
                self.empty.add(f".job-staging/{batch['stage_id']}")

    def forest(self):
        physical = {key: row for key, row in self.datasets.items() if row['parser_version'] == 'gravity-stations-json/v1'}
        children = {key for key, row in physical.items() if row['kind'] == 'derived'}
        require(children == {r['child_dataset_id'] for r in self.rows['physical_dataset_edges']} ==
                {r['child_dataset_id'] for r in self.rows['physical_dataset_productions']},
                'physical_classifier_complete_productions')
        intents = self.rows['physical_publication_intents']
        for family in self.rows['physical_dataset_families']:
            self.ownership(family)
            members = [r for r in self.datasets.values() if r['root_dataset_id'] == family['root_dataset_id']]
            prepared = [r for r in intents if r['root_dataset_id'] == family['root_dataset_id']]
            versions = [r['version'] for r in members] + [r['ordinal'] for r in prepared]
            require(family['published_count'] == len(members) and family['reserved_count'] == len(prepared)
                    and len(versions) == len(set(versions)) and all(v < family['next_ordinal'] for v in versions)
                    and all((r['owner_id'], r['project_id'], r['raw_asset_id'], r['parser_version']) ==
                            tuple(family[k] for k in ('owner_id', 'project_id', 'raw_asset_id', 'parser_version')) for r in members),
                    'physical_classifier_family_allocator')
            require((family['state'] == 'pending') == (not members) and
                    (not members or any(r['id'] == family['root_dataset_id'] and r['kind'] == 'root' for r in members)),
                    'physical_classifier_family_root')
        for row in physical.values():
            self.ownership(row)
            cap = 64*M if row['payload_schema'] == 'gravity-transform-result-1' else 16*M
            self.declare(row['storage_key'], cap=cap, bytes=row['byte_count'], sha256=row['sha256'])
            if row['payload_schema'] == 'gravity-transform-result-1':
                audit_transform_producer(self.connection, self.files, row, approved_manifests=self.manifests)
            else:
                audit_correction_ancestry(self.connection, self.files, row, approved_manifests=self.manifests)
            if row['kind'] == 'root':
                history = [b for b in self.batches.values() if b['origin_kind'] == 'root_stage' and b['origin_id'] == row['id']]
                require(len(history) == 1 and history[0]['state'] in ('cleanup_pending', 'removed'),
                        'physical_classifier_root_custody_history')
            self.operations[row['id']] = 'retain_committed'
        for row in self.datasets.values():
            if row['id'] in physical:
                continue
            self.ownership(row)
            require(row['kind'] == 'root' and row['version'] == 1 and row['root_dataset_id'] == row['id']
                    and row['parent_dataset_id'] is None and predecessor_payload(row['parser_version'], row['modality']) == row['payload_schema'],
                    'physical_classifier_legacy_tuple')
            raw = self.raw[row['raw_asset_id']]
            require((raw['owner_id'], raw['project_id'], raw['sha256']) ==
                    (row['owner_id'], row['project_id'], row['raw_sha256']), 'physical_classifier_legacy_raw')
            key = f"derived/{row['owner_id']}/{row['project_id']}/datasets/{row['id']}.json"
            require(row['storage_key'] == key, 'physical_classifier_legacy_key')
            self.declare(key, cap=16*M, bytes=row['byte_count'], sha256=row['sha256'])
            from app.processing_contract import validate_dataset_identity
            value = decode(self.files.read(key, cap=16*M, expected_bytes=row['byte_count'], expected_sha256=row['sha256']), 16*M)
            validate_dataset_identity(value, SimpleNamespace(**row))
            self.operations[row['id']] = 'retain_committed'

    def job_controls(self):
        physical_jobs = {key: r for key, r in self.jobs.items() if r['method_id'] in (CORRECTION, TRANSFORM)}
        require(set(physical_jobs) == set(self.controls), 'physical_classifier_complete_controls')
        productions = {r['job_id']: r for r in self.rows['physical_dataset_productions']}
        for job in self.jobs.values():
            self.ownership(job)
            dataset = self.datasets.get(job['dataset_id'])
            require(dataset is not None and (dataset['owner_id'], dataset['project_id'], dataset['sha256']) ==
                    (job['owner_id'], job['project_id'], job['dataset_sha256']), 'physical_classifier_job_input')
            request = decode(job['request_json'].encode(), 35*M)
            require(type(request) is dict and job['state'] in ('queued', 'running', 'succeeded', 'failed', 'cancelled'),
                    'physical_classifier_job_state')
            terminal = job['state'] in ('succeeded', 'failed', 'cancelled')
            require((job['finished_at'] is not None) == terminal, 'physical_classifier_job_terminal')
            if job['id'] in physical_jobs:
                control = self.controls[job['id']]
                decoded = decode(control['request_bytes'], 34*M)
                fields(decoded, REQUEST_KEYS)
                require(canonical(decoded) == control['request_bytes'] and canonical(request) == canonical(decoded)
                        and decoded['schema'] == 'geophysics.physical-request/v2'
                        and digest(decoded) == control['request_sha256'] == job['request_sha256']
                        and all(decoded[k] == control[k] for k in ('owner_id', 'project_id', 'dataset_id', 'dataset_sha256',
                            'root_dataset_id', 'raw_asset_id', 'raw_sha256', 'raw_bytes', 'method_id'))
                        and control['stage_id'] == job['id'] == decoded['job_id'], 'physical_classifier_control')
                manifest = decode(control['module_manifest_bytes'], 65536)
                require(digest(manifest) == control['module_manifest_sha256'] == decoded['module_manifest_sha256']
                        and canonical(manifest) == canonical(decoded['module_manifest'])
                        and self.manifests.get(digest(manifest)) is not None
                        and canonical(self.manifests[digest(manifest)]) == canonical(manifest)
                        and digest(decoded['parameters']) == decoded['submitted_parameters_sha256'] == control['submitted_parameters_sha256']
                        and digest(decoded['scientific_request'], scientific=True) == decoded['scientific_request_sha256']
                        and decoded['scientific_request_sha256'] == control['scientific_request_sha256']
                        and decoded['admission_receipt_sha256'] == control['admission_receipt_sha256'],
                        'physical_classifier_control_source')
                parent = self.datasets[job['dataset_id']]
                input_body, prior = audit_correction_ancestry(self.connection, self.files, parent, approved_manifests=self.manifests)
                envelope = decode(input_body, 16*M)
                science = decoded['scientific_request']
                if job['method_id'] == CORRECTION:
                    fields(science, 'schema_version method dataset config input_dataset_sha256 submitted_config_sha256')
                    selected = envelope['payload'] if envelope['kind'] == 'root' else envelope['payload']['correction_result']['dataset']
                    require(science['schema_version'] == 'gravity-station-adapter-request-1' and science['method'] == CORRECTION
                            and science['input_dataset_sha256'] == digest(selected, scientific=True)
                            and science['submitted_config_sha256'] == digest(science['config'], scientific=True)
                            and canonical(science['dataset'], scientific=True) == canonical(selected, scientific=True)
                            and canonical(science['config'], scientific=True) == canonical(decoded['parameters'], scientific=True),
                            'physical_classifier_scientific_input')
                else:
                    fields(science, 'schema_version correction_result geometry config')
                    fields(decoded['parameters'], 'geometry config')
                    require(science['schema_version'] == 'gravity-transform-request-1' and envelope['kind'] == 'derived'
                            and envelope['payload_schema'] == 'gravity-station-adapter-result-1'
                            and canonical(science['correction_result'], scientific=True) == canonical(envelope['payload']['correction_result'], scientific=True)
                            and all(canonical(science[k], scientific=True) == canonical(decoded['parameters'][k], scientific=True)
                                    for k in ('geometry', 'config')), 'physical_classifier_scientific_input')
                require(canonical(decoded['parent_production']) == canonical(prior) and
                        (control['parent_production_bytes'] is None if prior is None else control['parent_production_bytes'] == canonical(prior)),
                        'physical_classifier_control_parent')
                raw = self.raw[control['raw_asset_id']]
                require((raw['owner_id'], raw['project_id'], raw['sha256'], raw['byte_count']) ==
                        tuple(control[k] for k in ('owner_id', 'project_id', 'raw_sha256', 'raw_bytes')),
                        'physical_classifier_control_raw')
                batches = [b for b in self.batches.values() if b['stage_id'] == job['id'] and b['origin_kind'] == 'job_stage']
                require(len(batches) == 1 and tuple(batches[0][k] for k in ('owner_id', 'project_id', 'raw_asset_id', 'raw_sha256', 'raw_bytes', 'method_id')) ==
                        tuple(control[k] for k in ('owner_id', 'project_id', 'raw_asset_id', 'raw_sha256', 'raw_bytes', 'method_id')),
                        'physical_classifier_control_custody')
                require(control['permanent_reservation_bytes'] == (0 if terminal else 80*M if job['method_id'] == CORRECTION else 128*M),
                        'physical_classifier_control_reservation')
                require((job['id'] in productions) == (job['state'] == 'succeeded')
                        and (not terminal or batches[0]['state'] in ('cleanup_pending', 'removed')),
                        'physical_classifier_job_production')
                if job['state'] in ('failed', 'cancelled'):
                    require(job['error_code'] in ERRORS and job['error_message'] == ERRORS[job['error_code']]
                            and (job['state'] == 'cancelled') == (job['error_code'] == 'physical_cancelled'),
                            'physical_classifier_terminal_error')
            else:
                require(job['method_id'] in METHODS, 'physical_classifier_method')
            if job['state'] == 'succeeded':
                key = f"derived/{job['owner_id']}/{job['project_id']}/results/{job['id']}.json"
                require(job['result_key'] == key and job['error_code'] is None and job['error_message'] is None,
                        'physical_classifier_result_key')
                self.declare(key, cap=64*M, bytes=job['result_bytes'], sha256=job['result_sha256'])
                if job['id'] not in physical_jobs:
                    from app.processing_contract import validate_result_identity
                    value = decode(self.files.read(key, cap=64*M, expected_bytes=job['result_bytes'], expected_sha256=job['result_sha256']), 64*M)
                    validate_result_identity(value, SimpleNamespace(**dict(job, request_json=request)))
            else:
                require(all(job[k] is None for k in ('result_key', 'result_bytes', 'result_sha256')),
                        'physical_classifier_nonsuccess_result')
            self.operations[job['id']] = 'retain_success' if job['state'] == 'succeeded' else 'retain_nonsuccess' if terminal else 'retain_reservation'

    def preparations(self):
        for intent in self.rows['physical_publication_intents']:
            self.ownership(intent)
            require(intent['child_dataset_id'] not in self.datasets, 'physical_classifier_visible_prepared_child')
            targets = [r for r in self.rows['physical_publication_targets'] if r['intent_id'] == intent['intent_id']]
            declared = [{k: r[k] for k in ('kind', 'artifact_id', 'storage_key', 'bytes', 'sha256')} for r in targets]
            if intent['kind'] == 'root':
                raw, batch, body, _ = _verified(self.connection, self.files, intent['owner_id'], intent['project_id'],
                                              intent['raw_asset_id'], intent['root_dataset_id'])
                require(intent['child_dataset_id'] == intent['stage_id'] == intent['root_dataset_id']
                        and intent['permanent_reservation_bytes'] == 16*M and len(declared) == 1
                        and declared[0] == dict(kind='dataset', artifact_id=intent['root_dataset_id'],
                            storage_key=f"derived/{intent['owner_id']}/{intent['project_id']}/datasets/{intent['root_dataset_id']}.json",
                            bytes=len(body), sha256=byte_sha(body)) and batch['raw_asset_id'] == raw['id'],
                        'physical_classifier_root_preparation')
            else:
                job = self.jobs[intent['job_id']]
                control = self.controls[job['id']]
                require(job['state'] == 'running' and intent['stage_id'] == job['id']
                        and tuple(intent[k] for k in ('owner_id', 'project_id', 'raw_asset_id', 'root_dataset_id', 'parent_dataset_id',
                            'parent_dataset_sha256', 'request_sha256')) == tuple(control[k] for k in ('owner_id', 'project_id',
                            'raw_asset_id', 'root_dataset_id', 'dataset_id', 'dataset_sha256', 'request_sha256')),
                        'physical_classifier_job_preparation')
                _targets(self.connection, control, declared, intent['child_dataset_id'], job['id'], intent['owner_id'], intent['project_id'])
            for target in declared:
                cap = 64*M if target['kind'] == 'result' or (intent['kind'] == 'job' and self.controls[intent['job_id']]['method_id'] == TRANSFORM) else 16*M
                self.declare(target['storage_key'], cap=cap, bytes=target['bytes'], sha256=target['sha256'], required=False)
            self.operations[intent['intent_id']] = 'abandon_only'

    def extra_members(self):
        from app.waveform_contract import MEMBER, SCRATCH, artifact_key, source_identity
        for row in self.rows['waveform_dataset_sources']:
            dataset = self.datasets[row['dataset_id']]
            require(dataset['modality'] == 'waveform_counts_response', 'physical_classifier_waveform_source')
            raw = self.raw[row['asset_id']]
            source = _row(self.connection, 'SELECT * FROM source_records WHERE id=?', (raw['source_id'],))
            require((raw['owner_id'], raw['project_id']) == (dataset['owner_id'], dataset['project_id']),
                    'physical_classifier_waveform_owner')
            value = decode(self.files.read(dataset['storage_key'], cap=16*M, expected_bytes=dataset['byte_count'],
                                          expected_sha256=dataset['sha256']), 16*M)
            identity = source_identity(SimpleNamespace(**raw), SimpleNamespace(**source))
            require(canonical(value['sources'][row['role']]) == canonical(identity) and all(
                row[k] == identity[k] for k in ('source_id', 'raw_sha256', 'raw_bytes', 'source_version')),
                'physical_classifier_waveform_binding')
        for row in self.rows['waveform_result_artifacts']:
            job = self.jobs[row['job_id']]
            require(job['method_id'] == 'seismic.waveform-qc-classical/v1' and job['state'] == 'succeeded'
                    and MEMBER.fullmatch(row['name']) is not None, 'physical_classifier_waveform_artifact')
            key = artifact_key(job['owner_id'], job['project_id'], job['id'], row['name'])
            require(row['storage_key'] == key, 'physical_classifier_waveform_artifact_key')
            self.declare(key, cap=SCRATCH, bytes=row['byte_count'], sha256=row['sha256'])

    def profile_archives(self):
        relations = []
        for job in self.jobs.values():
            if job['method_id'] not in PROFILE_METHODS:
                continue
            dataset = self.datasets[job['dataset_id']]
            raw = self.raw[dataset['raw_asset_id']]
            source = _row(self.connection, 'SELECT * FROM source_records WHERE id=?', (raw['source_id'],))
            request = decode(job['request_json'].encode(), 35*M)
            require(request['raw_asset_id'] == raw['id'] and request['raw_sha256'] == raw['sha256'],
                    'physical_classifier_profile_relation')
            if job['state'] in ('succeeded', 'failed', 'cancelled'):
                from app.profile_linux_recovery import retained_ownership
                retained_ownership(SimpleNamespace(**dict(job, request_json=request)), SimpleNamespace(**dataset),
                                   SimpleNamespace(**raw), SimpleNamespace(**source))
            relations.append(dict(id=job['id'], owner_id=job['owner_id'], project_id=job['project_id'], dataset_id=dataset['id'],
                dataset_sha256=dataset['sha256'], raw_asset_id=raw['id'], source_id=raw['source_id'], raw_sha256=raw['sha256'],
                request_sha256=job['request_sha256'], method_id=job['method_id'], state=job['state']))
        receipts = [dict(row, derived_manifest=_json(row['derived_manifest'].encode(), 4*M)
                    if row['derived_manifest'] is not None else []) for row in self.rows['deletion_receipts']]
        records = retained_inventory(self.files, relations, receipts, approved_installations=self.installations)
        if records:
            self.empty.add('.profile-retained')
        for record in records:
            job = record['job_id']
            prefix = '.profile-retained/' + job
            self.empty.add(prefix)
            self.declare(prefix + '/manifest.json', cap=262144, bytes=record['manifest_bytes'], sha256=record['manifest_sha256'])
            self.declare('.profile-retained/' + job + '.intent.json', cap=262144,
                         bytes=record['manifest_bytes'], sha256=record['manifest_sha256'])
            for name, member in record['manifest']['members'].items():
                self.declare(prefix + '/' + name, cap=64*M, bytes=member['bytes'], sha256=member['sha256'])
        return records


def classify_snapshot(connection, files, *, approved_manifests, approved_installations, native_metadata,
                      expected_source_policy_sha256=None):
    """One disposition set only after complete SQL, body and namespace barriers.

    Pure/portable callers get runtime=False; runtime assembly must additionally
    prove the actual retained leases, source policy and fixed SQL/file roots.
    No missing pathname grants removal or debt release. No transaction changes.
    """
    try:
        rows, descriptors = _snapshot(connection)
        audit = _Audit(connection, files, rows, approved_manifests, approved_installations, native_metadata,
                       expected_source_policy_sha256)
        audit.deleted_projects()
        audit.prepared_deletions()
        audit.originals()
        audit.custody()
        audit.forest()
        audit.job_controls()
        audit.preparations()
        audit.extra_members()
        records = audit.profile_archives()
        measured = files.census(audit.expected, empty_directories=audit.empty)
        require(all((original in measured)!=(moved in measured) for original,moved in audit.relocations.items()),
                'physical_classifier_predeletion_partition')
        require(not audit.absent & set(measured), 'physical_classifier_removed_reappeared')
        charges = {row['id']: MappingProxyType(dict(account_private_charge(connection, row['id'],
            profile_records=records, approved_installations=approved_installations))) for row in rows['user']}
        require(all(c['total'] <= 1024*M for c in charges.values()), 'physical_classifier_account_quota')
        fingerprint = digest(dict(schema='geophysics.physical-classification/v1', revision=REVISION,
                                  rows=descriptors, files=measured, profile_records=records))
        prepared = bool(rows['physical_publication_intents']) or any(r['state'] in ('reserved', 'active', 'sealed')
            for r in rows['physical_custody_batches']) or any(r['state'] in ('queued', 'running') for r in rows['processing_jobs'])
        return Classification('prepared_uncommitted' if prepared else 'coherent_committed', 'complete_snapshot',
                              MappingProxyType(audit.operations), MappingProxyType(charges), fingerprint)
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, UnicodeError, ApiError) as error:
        # No partial classifications, hashes or selected-family "green" escape.
        reason = error.code if isinstance(error, ApiError) else str(error)
        return Classification('inconsistent', reason[:160], MappingProxyType({}), MappingProxyType({}))
