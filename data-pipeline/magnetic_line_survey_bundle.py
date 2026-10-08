"""Fixed native preparation: indexed closed bytes and ALL original geometry.

No measurement decoding, fit, outer evaluation, field grant or automatic purge.
Only the fixed worker dispatches the public entry after actual Job containment.
"""
from __future__ import annotations

from hashlib import sha256
import os
import re
import sqlite3
import struct

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
from magnetic_line_survey_local_worker import decode_documents
from magnetic_line_survey_representation import Reader
from magnetic_line_survey_result import _refs

MAX_AUX = 4294967296
INDEX_LIMIT = 2147483648


def _check(condition, code='custody_mismatch'):
    if not condition:
        raise core.SurveyError(code, 'ingest')


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink)


def _key(info):
    # Windows CPython exposes different ctime semantics across stat/fstat.
    value = _stamp(info)
    return value[:4]+value[5:]


def _entry(value, limit):
    core._closed(value, 'path bytes sha256', 'ingest')
    _check(type(value['bytes']) is int and 0 < value['bytes'] <= limit, 'resource_refused')
    base._type(value['sha256'], 'Hash', 'identity', 0)
    return core._plain_path(io.external_path(value['path'], directory=False))


def _verified_document(entry):
    path = _entry(entry, 2097152)
    before = path.stat()
    payload = base.read_bounded(path, 2097152)
    _check(len(payload) == entry['bytes'] and sha256(payload).hexdigest() == entry['sha256'])
    _check(_stamp(before) == _stamp(path.stat()))
    return payload


def _geometry_preflight(entry):
    """Full raw stream, no numerical measurement-token decoder."""
    path = _entry(entry, MAX_AUX)
    count, total, digest = 0, 0, sha256()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        path_before = path.stat()
        _check(_key(before) == _key(path_before) and before.st_nlink == 1)
        header = True
        while True:
            raw = stream.readline(min(4097, entry['bytes']-total+1))
            if not raw:
                break
            total += len(raw); digest.update(raw)
            _check(total <= entry['bytes'] and len(raw) <= 4096, 'resource_refused')
            text = raw.decode('utf-8-sig' if header else 'utf-8')
            text = text[:-2] if text.endswith('\r\n') else text[:-1] if text.endswith('\n') else text
            _check('\r' not in text and '\n' not in text, 'invalid_contract')
            if header:
                _check(text == ','.join(base.CSV_COLUMNS), 'invalid_contract')
                header = False
                continue
            core._geometry_record(text.split(','), base)
            count += 1
            _check(count <= 8000000, 'resource_refused')
        _check(_stamp(before) == _stamp(os.fstat(stream.fileno())) and
               _stamp(path_before) == _stamp(path.stat()))
    _check(count > 0 and total == entry['bytes'] and digest.hexdigest() == entry['sha256'])
    return count


def preparation_capacity(rows, auxiliary_bytes):
    """Conservative geometry SQLite/chunk/journal allowance, not fit admission."""
    _check(type(rows) is int and 0 < rows <= 8000000, 'resource_refused')
    _check(type(auxiliary_bytes) is int and 0 < auxiliary_bytes <= MAX_AUX, 'resource_refused')
    # At most 4096 raw bytes/row; 64 KiB/row allows separately indexed geometry,
    # overflow pages, journal/temp and generated typed records, plus fixed roots.
    geometry = 65536*rows+67108864
    scratch = auxiliary_bytes+2*INDEX_LIMIT+geometry+67108864
    _check(scratch <= core.SCRATCH_LIMIT, 'resource_refused')
    return dict(schema='m03-owner-preparation-capacity/1', original_rows=rows,
        auxiliary_bytes=auxiliary_bytes, index_and_journal_bytes=2*INDEX_LIMIT,
        geometry_workspace_bytes=geometry, scratch_bound_bytes=scratch,
        logical_member_limit=192, physical_member_limit=1000000,
        value_access='not_opened', full_job_admission='not_established')


def _exact(stream, size):
    payload = stream.read(size)
    _check(len(payload) == size, 'invalid_contract')
    return payload


class _Known:
    """Reader ledger stored on disk, without million-member Python materialization."""
    def __init__(self, db): self.db = db

    def get(self, name):
        row = self.db.execute('SELECT size,sha,recognized FROM members WHERE name=?', (name,)).fetchone()
        return dict(name=name, bytes=row[0], sha256=row[1]) if row and row[2] else None

    def __setitem__(self, name, value):
        row = self.db.execute('SELECT size,sha FROM members WHERE name=?', (name,)).fetchone()
        _check(row == (value['bytes'], value['sha256']))
        self.db.execute('UPDATE members SET recognized=1 WHERE name=?', (name,))


class _IndexedReader(Reader):
    def __init__(self, root, db):
        super().__init__(root)
        self.db, self.known = db, _Known(db)

    def _case_identity(self, identity):
        row = self.db.execute('SELECT name FROM members WHERE folded=?', (identity['name'].casefold(),)).fetchone()
        _check(row == (identity['name'],))

    def reject_unknown(self, extra=()):
        _check(not extra and self.db.execute('SELECT 1 FROM members WHERE recognized=0 LIMIT 1').fetchone() is None)
        count = 0
        for path in self.root.iterdir():
            core._plain_path(path)
            _check(self.db.execute('SELECT 1 FROM members WHERE name=? AND recognized=1', (path.name,)).fetchone() is not None)
            count += 1
        _check(count == self.db.execute('SELECT COUNT(*) FROM members').fetchone()[0])


def _index_bundle(db, entry, number):
    path = _entry(entry, MAX_AUX)
    digest, previous, total = sha256(), '', 12
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        path_before = path.stat()
        _check(_key(before) == _key(path_before) and before.st_nlink == 1)
        def read(size):
            payload = _exact(stream, size); digest.update(payload); return payload
        _check(read(8) == b'M03AUX1\n', 'invalid_contract')
        count = struct.unpack('<I', read(4))[0]
        _check(1 <= count <= 1000000 and 12+44*count <= entry['bytes'], 'resource_refused')
        prior_count = db.execute('SELECT COUNT(*) FROM members').fetchone()[0]
        _check(prior_count+count <= 1000000, 'resource_refused')
        for _ in range(count):
            length = struct.unpack('<H', read(2))[0]
            _check(1 <= length <= 64, 'invalid_contract')
            name = read(length).decode('ascii')
            size = struct.unpack('<Q', read(8))[0]
            expected = read(32).hex()
            total += 42+length+size
            _check(re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', name) is not None and name not in ('.', '..') and
                   name > previous and 0 < size <= 8388608 and total <= entry['bytes'], 'invalid_contract')
            offset, remaining, payload_digest = stream.tell(), size, sha256()
            while remaining:
                payload = read(min(remaining, 1048576))
                remaining -= len(payload); payload_digest.update(payload)
            _check(payload_digest.hexdigest() == expected)
            try:
                db.execute('INSERT INTO members VALUES (?,?,?,?,?,?,?,0)',
                    (name, name.casefold(), number, offset, size, expected, _stamp(before)[2]))
            except sqlite3.IntegrityError:
                raise core.SurveyError('custody_mismatch', 'ingest') from None
            previous = name
        _check(total == entry['bytes'] and not stream.read(1) and digest.hexdigest() == entry['sha256'])
        _check(_stamp(before) == _stamp(os.fstat(stream.fileno())) and _stamp(path_before) == _stamp(path.stat()))
    return _stamp(path_before)


def _prepare(plan, workspace):
    """Internal finite data operation; production entry below always requires Job."""
    core._closed(plan, 'schema original metadata request bundles', 'ingest')
    _check(plan['schema'] == 'm03-owner-preparation-plan/1', 'invalid_contract')
    _check(type(plan['bundles']) is list and 1 <= len(plan['bundles']) <= 16, 'invalid_contract')
    metadata, request = decode_documents(_verified_document(plan['metadata']), _verified_document(plan['request']))
    _check(metadata['original']['csv_sha256'] == plan['original']['sha256'] and
           metadata['original']['csv_bytes'] == plan['original']['bytes'])
    _check(request['dataset_version_sha256'] == base.dataset_identity(
        metadata['original']['csv_sha256'], base.digest(metadata)))
    _check(metadata['rights']['decision'] == metadata['rights']['private_processing'] == 'allowed', 'metadata_ineligible')
    refs = _refs(dict(metadata=metadata, request=request))
    _check(1 <= len(refs) <= 192, 'resource_refused')
    auxiliary_bytes = 0
    for entry in plan['bundles']:
        _entry(entry, MAX_AUX); auxiliary_bytes += entry['bytes']
    rows = _geometry_preflight(plan['original'])
    capacity = preparation_capacity(rows, auxiliary_bytes)
    workspace = io.external_path(workspace)
    core._write_member(workspace, 'preparation-capacity.json', base.canonical_bytes(capacity))
    index = workspace/'bundle-index.sqlite3'
    _check(not index.exists(), 'invalid_contract')
    db = sqlite3.connect(index)
    try:
        db.execute('PRAGMA page_size=4096')
        db.execute('PRAGMA cache_size=-8192')
        db.execute('PRAGMA temp_store=FILE')
        db.execute("PRAGMA temp_store_directory='"+str(workspace).replace("'", "''")+"'")
        db.execute('PRAGMA max_page_count=524288')
        db.execute('CREATE TABLE members(name TEXT PRIMARY KEY,folded TEXT UNIQUE,bundle INTEGER,offset INTEGER,size INTEGER,sha TEXT,bundle_size INTEGER,recognized INTEGER)')
        stamps = [_index_bundle(db, entry, number) for number, entry in enumerate(plan['bundles'])]
        db.commit()  # Complete envelope checks before the FIRST extracted file.
        root = workspace/'auxiliary'
        root.mkdir()  # No adoption/overwrite, even after a retained failure.
        for number, entry in enumerate(plan['bundles']):
            path = _entry(entry, MAX_AUX)
            with path.open('rb') as stream:
                opened = os.fstat(stream.fileno())
                _check(_key(opened) == _key(path.stat()) and _stamp(path.stat()) == stamps[number])
                for name, offset, size, expected in db.execute('SELECT name,offset,size,sha FROM members WHERE bundle=? ORDER BY name', (number,)):
                    stream.seek(offset); remaining, digest = size, sha256()
                    with (root/name).open('xb') as target:
                        while remaining:
                            payload = _exact(stream, min(remaining, 1048576))
                            remaining -= len(payload); digest.update(payload); target.write(payload)
                        target.flush(); os.fsync(target.fileno())
                    _check(digest.hexdigest() == expected)
                _check(_stamp(opened) == _stamp(os.fstat(stream.fileno())) and _stamp(path.stat()) == stamps[number])
        reader = _IndexedReader(root, db)
        for ref in refs:
            # No float/UTC/ID array decoding here, especially magnetic/sigma.
            for _ in reader.chunks(ref): pass
        reader.reject_unknown(); db.commit()
        lines = list(reader.table(metadata['acquisition']['line_dictionary']))
        sensors = list(reader.table(metadata['acquisition']['sensor_dictionary']))
        inspection = core.inspect_geometry(plan['original']['path'], workspace/'geometry',
            metadata['original'], metadata['rights'], lines, sensors)
        _check(inspection['rows'] == rows and inspection['arrays'] == metadata['arrays'] and
            inspection['dictionaries'] == [metadata['acquisition']['line_dictionary'], metadata['acquisition']['sensor_dictionary']])
        from magnetic_line_survey_runtime import owned_bytes
        _check(owned_bytes(workspace) <= capacity['scratch_bound_bytes'], 'resource_refused')
        receipt = dict(schema='m03-owner-preparation-receipt/1', original=metadata['original'],
            metadata_sha256=plan['metadata']['sha256'], request_sha256=plan['request']['sha256'],
            bundle_sha256=[entry['sha256'] for entry in plan['bundles']], rows=rows,
            geometry=inspection, geometry_sha256=base.digest(inspection), logical_members=len(refs),
            physical_members=db.execute('SELECT COUNT(*) FROM members').fetchone()[0],
            capacity=capacity, semantic_closure='schema_recognized_encoded_bytes', value_access='not_opened',
            field_eligibility='not_established', scientific_result='not_established')
        core._write_member(workspace, 'preparation.json', base.canonical_bytes(receipt))
        _check(owned_bytes(workspace) <= capacity['scratch_bound_bytes'], 'resource_refused')
        return receipt
    except sqlite3.Error:
        raise core.SurveyError('io_failed', 'ingest') from None
    finally:
        db.close()


def run_preparation_plan(plan, workspace, job_handle):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    _prepare(plan, workspace)
    return 0
