"""Bounded owned physical receipts/ancestry; no numerical solve or admission."""

import base64
import hashlib
import hmac
import re
import struct
from uuid import UUID

from app.physical_contract import canonical, decode_source, fields, instant, integer, require, uuid
from app.physical_forest import _row
from app.physical_persistence import M
from app.physical_read import _verified_body
from app.physical_roots import _ledger

DATASET_LIST = 'geophysics.physical-dataset-list/v2'
LINEAGE = 'geophysics.physical-lineage/v2'
RECEIPT_KEYS = ('dataset_id version root_dataset_id parent_dataset_id parent_dataset_sha256 '
    'kind modality payload_schema parser_version raw_asset_id raw_sha256 raw_bytes dataset_sha256 '
    'bytes row_count state production structural_verdict created_at')
NODE_KEYS = ('dataset_id version kind modality payload_schema bytes sha256 raw_asset_id raw_sha256 '
    'raw_bytes scientific_payload_sha256')
PRODUCTION_KEYS = ('child_dataset_id job_id input_dataset_id input_dataset_sha256 method_id '
    'request_sha256 result_sha256 result_bytes submitted_parameters_sha256 scientific_request_sha256 '
    'scientific_result_sha256 adapter_result_sha256 module_manifest_sha256 scientific_verdict')
_DOMAIN = b'geophysics.physical-dataset-cursor/v1\0'


def _secret(value):
    require(type(value) is bytes and 32 <= len(value) <= 8192, 'physical_catalog_secret')
    return hmac.digest(value, _DOMAIN, hashlib.sha256)


def _order_time(value):
    # Retain the literal SQLite ordering key. Native root publication stores
    # str(UTC datetime), while historical rows omit the UTC suffix; neither
    # representation is normalized before keyset comparison.
    require(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:\+00:00)?', value),
            'physical_catalog_order')
    instant(value, legacy=True)
    return value


def _cursor(secret, owner, project, cutoff, anchor, after):
    stamp = _order_time(after[0]).encode('ascii')
    integer(cutoff, 1)
    for value in (owner, project, anchor, after[1]):
        uuid(value)
    body = (b'PCD1' + UUID(owner).bytes + UUID(project).bytes + struct.pack('>Q', cutoff)
        + UUID(anchor).bytes + bytes([len(stamp)]) + stamp + UUID(after[1]).bytes)
    return base64.urlsafe_b64encode(body + hmac.digest(_secret(secret), body, hashlib.sha256)).decode().rstrip('=')


def _open_cursor(value, secret, owner, project):
    require(type(value) is str and 1 <= len(value) <= 256 and re.fullmatch(r'[A-Za-z0-9_-]+', value),
            'physical_catalog_cursor')
    try:
        packet = base64.b64decode(value + '='*((-len(value)) % 4), altchars=b'-_', validate=True)
    except ValueError as error:
        raise ValueError('physical_catalog_cursor') from error
    require(base64.urlsafe_b64encode(packet).decode().rstrip('=') == value and len(packet) >= 112,
            'physical_catalog_cursor')
    body, signature = packet[:-32], packet[-32:]
    require(hmac.compare_digest(signature, hmac.digest(_secret(secret), body, hashlib.sha256))
        and body[:4] == b'PCD1' and body[4:20] == UUID(owner).bytes and body[20:36] == UUID(project).bytes,
        'physical_catalog_cursor')
    stamp_size = body[60]
    require(stamp_size in range(19, 33) and len(body) == 61 + stamp_size + 16, 'physical_catalog_cursor')
    try:
        stamp = _order_time(body[61:61+stamp_size].decode('ascii'))
    except (UnicodeError, ValueError) as error:
        raise ValueError('physical_catalog_cursor') from error
    cutoff = struct.unpack('>Q', body[36:44])[0]
    integer(cutoff, 1)
    return cutoff, str(UUID(bytes=body[44:60])), (stamp, str(UUID(bytes=body[-16:])))


def _owned(connection, owner, project):
    uuid(owner)
    uuid(project)
    _row(connection, 'SELECT id FROM projects WHERE id=? AND owner_id=?', (project, owner))


def _envelope(connection, files, row, approved):
    body = _verified_body(connection, files, owner_id=row['owner_id'], project_id=row['project_id'],
                          dataset_id=row['id'], approved_manifests=approved)
    envelope = decode_source([body], max_bytes=64*M, depth=32, nodes=2250000)
    require((envelope['dataset_id'], envelope['version'], envelope['kind'], envelope['modality'],
        envelope['payload_schema'], envelope['root_dataset_id'], envelope['parent_dataset_id']) ==
        tuple(row[k] for k in ('id', 'version', 'kind', 'modality', 'payload_schema', 'root_dataset_id', 'parent_dataset_id')),
        'physical_catalog_dataset_binding')
    return envelope


def _receipt(row, envelope):
    result = {key: envelope[key] for key in RECEIPT_KEYS.split()
              if key not in ('dataset_sha256', 'bytes', 'row_count', 'state', 'created_at')}
    result.update(dataset_sha256=row['sha256'], bytes=row['byte_count'], row_count=row['row_count'],
        state=envelope['payload']['state'] if envelope['kind'] == 'root' else
        envelope['payload']['correction_result']['dataset']['state'] if envelope['payload_schema'] == 'gravity-station-adapter-result-1'
        else None, created_at=instant(row['created_at'], legacy=True).isoformat().replace('+00:00', 'Z'))
    fields(result, RECEIPT_KEYS)
    integer(result['row_count'], 1, 400)
    require(len(canonical(result)) <= 4096, 'physical_catalog_receipt_limit')
    return result


def _bounded(value):
    body = canonical(value)
    decode_source([body], max_bytes=256*1024, depth=16, nodes=20000)
    return value


def catalog_response(value):
    """Bounded metadata only, separate from exact original dataset byte reads."""
    from fastapi.responses import Response
    require(type(value) is dict and value.get('schema') in (DATASET_LIST, LINEAGE), 'physical_catalog_response')
    if value['schema'] == DATASET_LIST:
        fields(value, 'schema project_id items next_cursor')
        require(type(value['items']) is list and len(value['items']) <= 32, 'physical_catalog_response')
    else:
        fields(value, 'schema project_id root_dataset_id selected_dataset_id nodes edges productions')
        require(type(value['nodes']) is list and 1 <= len(value['nodes']) <= 5
            and type(value['edges']) is list and type(value['productions']) is list
            and len(value['edges']) == len(value['productions']) == len(value['nodes'])-1, 'physical_catalog_response')
    _bounded(value)
    return Response(canonical(value), media_type='application/json', headers={'Cache-Control':'no-store'})


def list_datasets_transaction(connection, files, *, owner_id, project_id, approved_manifests,
                              secret, limit=32, cursor=None):
    """One fixed birth cutoff and bounded keyset page, never a partial graph."""
    integer(limit, 1, 32)
    _secret(secret)
    with _ledger(connection, caller_owned=True):
        _owned(connection, owner_id, project_id)
        where = "owner_id=? AND project_id=? AND parser_version='gravity-stations-json/v1'"
        parameters = (owner_id, project_id)
        if cursor is None:
            anchor_row = connection.execute('SELECT rowid,id FROM observation_datasets WHERE '+where+' ORDER BY rowid DESC LIMIT 1', parameters).fetchone()
            if anchor_row is None:
                return _bounded(dict(schema=DATASET_LIST, project_id=project_id, items=[], next_cursor=None))
            cutoff, anchor = anchor_row
            after = None
        else:
            cutoff, anchor, after = _open_cursor(cursor, secret, owner_id, project_id)
            require(connection.execute('SELECT rowid FROM observation_datasets WHERE '+where+' AND id=?', parameters+(anchor,)).fetchone() == (cutoff,),
                    'physical_catalog_cursor_stale')
        integer(cutoff, 1)
        sql = 'SELECT * FROM observation_datasets WHERE '+where+' AND rowid<=?'
        parameters += (cutoff,)
        if after is not None:
            sql += ' AND (created_at>? OR (created_at=? AND id>?))'
            parameters += (after[0], after[0], after[1])
        query = connection.execute(sql+' ORDER BY created_at,id LIMIT ?', parameters+(limit+1,))
        names = [column[0] for column in query.description]
        rows = [dict(zip(names, values)) for values in query.fetchall()]
        items = [_receipt(row, _envelope(connection, files, row, approved_manifests)) for row in rows[:limit]]
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit-1]
            next_cursor = _cursor(secret, owner_id, project_id, cutoff, anchor, (last['created_at'], last['id']))
        return _bounded(dict(schema=DATASET_LIST, project_id=project_id, items=items, next_cursor=next_cursor))


def lineage_transaction(connection, files, *, owner_id, project_id, dataset_id, approved_manifests):
    """Exact complete selected ancestry, not a scientific refit or byte bundle."""
    uuid(dataset_id)
    with _ledger(connection, caller_owned=True):
        _owned(connection, owner_id, project_id)
        selected = _row(connection, 'SELECT * FROM observation_datasets WHERE id=? AND owner_id=? AND project_id=?',
                        (dataset_id, owner_id, project_id))
        _envelope(connection, files, selected, approved_manifests)
        rows, seen, current = [], set(), selected
        while True:
            require(current['id'] not in seen and len(rows) < 5, 'physical_catalog_lineage_depth')
            seen.add(current['id'])
            rows.append(current)
            if current['kind'] == 'root':
                break
            current = _row(connection, 'SELECT * FROM observation_datasets WHERE id=? AND owner_id=? AND project_id=?',
                (current['parent_dataset_id'], owner_id, project_id))
        nodes, edges, productions = [], [], []
        for row in reversed(rows):
            envelope = _envelope(connection, files, row, approved_manifests)
            node = {key: envelope[key] for key in NODE_KEYS.split() if key not in ('bytes', 'sha256')}
            node.update(bytes=row['byte_count'], sha256=row['sha256'])
            fields(node, NODE_KEYS)
            nodes.append(node)
            if row['kind'] == 'root':
                continue
            edge = _row(connection, 'SELECT * FROM physical_dataset_edges WHERE child_dataset_id=?', (row['id'],))
            edges.append({key: edge[key] for key in ('parent_dataset_id', 'child_dataset_id', 'role', 'parent_dataset_sha256')})
            production = _row(connection, 'SELECT * FROM physical_dataset_productions WHERE child_dataset_id=?', (row['id'],))
            projected = {key: production[{'input_dataset_id': 'parent_dataset_id', 'input_dataset_sha256': 'parent_dataset_sha256'}.get(key, key)]
                         for key in PRODUCTION_KEYS.split()}
            fields(projected, PRODUCTION_KEYS)
            productions.append(projected)
        return _bounded(dict(schema=LINEAGE, project_id=project_id, root_dataset_id=selected['root_dataset_id'],
            selected_dataset_id=dataset_id, nodes=nodes, edges=edges, productions=productions))


async def owned_catalog(session, physical, *, operation, owner_id, project_id, **arguments):
    from sqlalchemy import text
    from app.errors import ApiError
    from app.physical_assembly import PhysicalAssembly
    from app.physical_async_sql import run_native_transaction
    if not isinstance(physical, PhysicalAssembly) or session.info.get('physical_assembly') is not physical:
        raise ApiError(409, 'physical_admission_closed', 'Physical operator assembly is not installed')
    physical.leases.require_held()
    require(not session.new and not session.dirty and not session.deleted, 'physical_catalog_pending_writer')
    try:
        await session.rollback()
        await session.execute(text('BEGIN'))
        result = await run_native_transaction(session, operation, files=physical.leases.files,
            owner_id=owner_id, project_id=project_id,
            approved_manifests=physical.participant.arguments()['approved_manifests'], **arguments)
        physical.leases.require_held()
        return result
    except (ValueError, OSError) as error:
        if str(error) == 'physical_bundle_total_limit':
            raise ApiError(413, 'physical_limit_exceeded', 'Complete physical export exceeds its byte limit') from error
        code = 'physical_contract_invalid' if str(error).startswith('physical_catalog_cursor') else 'physical_integrity_failed'
        raise ApiError(409, code, 'Physical catalog or saved ancestry differs from its owned receipt') from error
