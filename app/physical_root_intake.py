"""Preallocation custody and exact root sealing in the original WAL transaction.

No namespace allocation, commit, rollback of the caller, or scientific solver.
The route must commit reservation before allocating either immutable stage copy.
"""

from app.physical_contract import byte_sha, canonical, integer, require, uuid, validate_custody
from app.physical_forest import _row
from app.physical_persistence import M
from app.physical_roots import _ledger, _original
from app.physical_wire import SOURCE_KEYS, make_root_envelope


def _copies(connection, files, owner, project, raw_id, root):
    raw, source, original, payload = _original(connection, files, owner, project, raw_id)
    body = make_root_envelope(payload, dataset_id=root, owner_id=owner, project_id=project,
        raw_asset_id=raw_id, raw_sha256=raw['sha256'], raw_bytes=raw['byte_count'],
        source={key: source[key] for key in SOURCE_KEYS.split()})
    require(len(body) <= 16*M, 'physical_root_envelope_limit')
    return raw, original, body


def _slots(root):
    return [dict(ordinal=i, role=role, location='stage', artifact_id=artifact,
        leaf=leaf, max_bytes=16*M, actual_bytes=None, actual_sha256=None)
        for i, (role, artifact, leaf) in enumerate((
            ('input_spool', None, 'input.json'), ('dataset_copy', root, 'dataset.json')), 1)]


def reserve_root_transaction(connection, files, *, owner_id, project_id, raw_asset_id,
                             root_dataset_id, batch_id, created_us, quota_bytes=1024*M,
                             profile_records=None, approved_installations=None):
    for value in (owner_id, project_id, raw_asset_id, root_dataset_id, batch_id):
        uuid(value)
    integer(created_us)
    integer(quota_bytes, 1, 1024*M)
    with _ledger(connection, caller_owned=True):
        raw, original, body = _copies(connection, files, owner_id, project_id, raw_asset_id, root_dataset_id)
        require(not connection.execute("SELECT 1 FROM physical_dataset_families WHERE raw_asset_id=? AND parser_version='gravity-stations-json/v1'", (raw_asset_id,)).fetchone()
            and not connection.execute("SELECT 1 FROM physical_custody_batches WHERE raw_asset_id=? AND origin_kind='root_stage' AND state<>'removed'", (raw_asset_id,)).fetchone(),
            'physical_root_already_reserved')
        from app.physical_accounting import account_private_charge
        # The stage is charged at its exact 32-MiB capacity. Also admit the
        # future independent 16-MiB target here; preparation rechecks it under
        # BEGIN IMMEDIATE before allocating any installed copy.
        require(account_private_charge(connection, owner_id, profile_records=profile_records,
                approved_installations=approved_installations)['total'] + 48*M <= quota_bytes,
                'physical_account_quota')
        header = dict(batch_id=batch_id, owner_id=owner_id, project_id=project_id,
            origin_kind='root_stage', origin_id=root_dataset_id, stage_id=root_dataset_id,
            deletion_receipt_id=None, raw_asset_id=raw_asset_id, raw_sha256=raw['sha256'],
            raw_bytes=raw['byte_count'], parser_version='gravity-stations-json/v1', method_id=None,
            capacity_bytes=32*M, state='reserved', charged_bytes=32*M, inventory_bytes=None,
            inventory_sha256=None, created_us=created_us, sealed_us=None, removed_us=None)
        names = tuple(header)
        connection.execute(f"INSERT INTO physical_custody_batches({','.join(names)}) VALUES({','.join('?' for _ in names)})", tuple(header.values()))
        for slot in _slots(root_dataset_id):
            row = dict(slot, batch_id=batch_id, state='reserved')
            connection.execute(f"INSERT INTO physical_custody_files({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))
        return dict(original=original, body=body,
                    dataset_key=f'derived/{owner_id}/{project_id}/datasets/{root_dataset_id}.json')


def seal_root_transaction(connection, files, *, owner_id, project_id, root_dataset_id,
                          batch_id, sealed_us):
    for value in (owner_id, project_id, root_dataset_id, batch_id):
        uuid(value)
    integer(sealed_us)
    with _ledger(connection, caller_owned=True):
        batch = _row(connection, 'SELECT * FROM physical_custody_batches WHERE batch_id=? AND owner_id=? AND project_id=?', (batch_id, owner_id, project_id))
        require(batch['state'] == 'reserved' and batch['origin_kind'] == 'root_stage'
            and batch['stage_id'] == batch['origin_id'] == root_dataset_id
            and batch['method_id'] is None and batch['deletion_receipt_id'] is None
            and batch['capacity_bytes'] == batch['charged_bytes'] == 32*M
            and batch['inventory_bytes'] is None and batch['inventory_sha256'] is None
            and batch['sealed_us'] is None and batch['removed_us'] is None
            and sealed_us >= batch['created_us'], 'physical_root_reserved_binding')
        raw, original, body = _copies(connection, files, owner_id, project_id, batch['raw_asset_id'], root_dataset_id)
        require((raw['sha256'], raw['byte_count'], 'gravity-stations-json/v1') ==
            (batch['raw_sha256'], batch['raw_bytes'], batch['parser_version']), 'physical_root_reserved_original')
        slots = _slots(root_dataset_id)
        cursor = connection.execute('SELECT * FROM physical_custody_files WHERE batch_id=? ORDER BY ordinal', (batch_id,))
        names = [column[0] for column in cursor.description]
        actual = [dict(zip(names, row)) for row in cursor]
        require(actual == [dict(slot, batch_id=batch_id, state='reserved') for slot in slots], 'physical_root_reserved_slots')
        files.verify_directory(f'.job-staging/{root_dataset_id}', expected_files=['input.json', 'dataset.json'])
        for slot, expected in zip(slots, (original, body)):
            require(files.read(f".job-staging/{root_dataset_id}/{slot['leaf']}", cap=16*M,
                expected_bytes=len(expected), expected_sha256=byte_sha(expected)) == expected, 'physical_root_stage_changed')
            slot.update(actual_bytes=len(expected), actual_sha256=byte_sha(expected))
        inventory = {key: batch[key] for key in ('batch_id owner_id project_id origin_kind origin_id stage_id deletion_receipt_id raw_asset_id raw_sha256 raw_bytes parser_version method_id capacity_bytes').split()}
        inventory.update(schema='geophysics.physical-custody/v1', initial_files=slots, removed_ordinals=[])
        charge = validate_custody(inventory)['retained_bytes']
        encoded = canonical(inventory)
        for slot in slots:
            connection.execute("UPDATE physical_custody_files SET actual_bytes=?,actual_sha256=?,state='present' WHERE batch_id=? AND ordinal=?", (slot['actual_bytes'], slot['actual_sha256'], batch_id, slot['ordinal']))
        connection.execute("UPDATE physical_custody_batches SET state='sealed',charged_bytes=?,inventory_bytes=?,inventory_sha256=?,sealed_us=? WHERE batch_id=?", (charge, encoded, byte_sha(encoded), sealed_us, batch_id))
