"""Value-free disk-indexed whole-line partitions and global source blocks.

No inline row ceiling is changed. No measurements, fitted coefficients or
validation scores enter this planner. The fresh producer index is never loaded
from user-supplied SQLite. A complete GeometrySeal additionally needs the
navigation/crossover/support stages of the owner workflow.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import math
from pathlib import Path
import sqlite3

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
from magnetic_line_validation import segment_rectangle


@contextmanager
def geometry_index(root, inspection, *, temp_root, alignment=None):
    """Independently verify all original geometry then rebuild bounded index."""
    root = io.external_path(root)
    core.verify_geometry_inspection(root, inspection)
    reader = io.Reader(root)
    lines = list(reader.table(inspection['dictionaries'][0]))
    sensors = list(reader.table(inspection['dictionaries'][1]))
    refs = {ref['role']: ref for ref in inspection['arrays']}
    with io.scratch_directory(temp_root) as temporary:
        db = sqlite3.connect(Path(temporary)/'geometry.sqlite3')
        try:
            db.execute('PRAGMA cache_size=-8192')
            # Even spill files of DISTINCT/ORDER BY use the explicitly external
            # producer directory, not ordinary OS temp or unbounded RAM.
            db.execute('PRAGMA temp_store=FILE')
            db.execute("PRAGMA temp_store_directory='"+temporary.replace("'", "''")+"'")
            db.execute('PRAGMA max_page_count=8388608')
            db.execute('CREATE TABLE rows (pos INTEGER PRIMARY KEY, id TEXT UNIQUE, line INTEGER, sensor INTEGER, '
                       'ordinal INTEGER, utc TEXT, e REAL, n REAL, z REAL, mask INTEGER, block_e INTEGER, block_n INTEGER)')
            db.execute('CREATE INDEX group_order ON rows(line,sensor,ordinal)')
            db.execute('CREATE INDEX xy_order ON rows(e,n,pos)')
            iterators = {role: reader.cells(refs[role]) for role in
                         ('row_id', 'line_index', 'sensor_index', 'ordinal', 'utc', 'easting', 'northing', 'upward', 'missing_mask')}
            for pos, values in enumerate(zip(*iterators.values(), strict=True)):
                row = dict(zip(iterators, values))
                db.execute('INSERT INTO rows VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL)',
                    (pos, row['row_id'], row['line_index'], row['sensor_index'], row['ordinal'], row['utc'],
                     row['easting'], row['northing'], row['upward'], row['missing_mask']))
                if pos % 4096 == 4095:
                    db.commit()
            db.commit()
            if db.execute('SELECT count(*) FROM rows').fetchone()[0] != inspection['rows']:
                raise core.SurveyError('custody_mismatch', 'seal')
            if alignment is not None:
                from magnetic_line_survey_navigation import apply_alignment_view
                apply_alignment_view(db, inspection, alignment)
            yield db, reader, lines, sensors
        except core.SurveyError:
            raise
        except (sqlite3.Error, ValueError, OverflowError):
            raise core.SurveyError('invalid_contract', 'seal') from None
        finally:
            db.close()


def _ids(reader, ref):
    values = list(reader.cells(ref))
    if len(values) != len(set(values)) or values != sorted(values) or any(not base.ID_PATTERN.fullmatch(v) for v in values):
        raise core.SurveyError('invalid_contract', 'seal')
    return set(values)


def _rectangle(block, buffer=0.):
    return (block['e_min_m']-buffer, block['e_max_m']+buffer,
            block['n_min_m']-buffer, block['n_max_m']+buffer)


def _contains(point, rectangle):
    return rectangle[0] <= point[0] <= rectangle[1] and rectangle[2] <= point[1] <= rectangle[3]


def _ordered_hash(db, condition, parameters):
    identity = sha256()
    for (rid,) in db.execute('SELECT id FROM rows '+condition+' ORDER BY pos', parameters):
        identity.update(rid.encode('ascii').ljust(64, b'\0'))
    return identity.hexdigest()


def _indexes(db, output, identifier, fold, disposition):
    query = 'SELECT pos FROM part WHERE fold=? AND disposition=? ORDER BY pos'
    params = (fold, disposition)
    count = db.execute('SELECT count(*) FROM part WHERE fold=? AND disposition=?', params).fetchone()[0]
    digest = sha256()
    for (rid,) in db.execute('SELECT r.id FROM rows r JOIN part p ON r.pos=p.pos '
                             'WHERE p.fold=? AND p.disposition=? ORDER BY r.pos', params):
        digest.update(rid.encode('ascii').ljust(64, b'\0'))
    return io.write_array(output, identifier, 'partition_index', (p for p, in db.execute(query, params)),
                          [count], 'uint64', 'identity', digest.hexdigest())


def _source_blocks(db, output, fold, configuration, depth):
    rows = db.execute('SELECT count(*), min(r.z) FROM rows r JOIN part p ON r.pos=p.pos '
                      'WHERE p.fold=? AND p.disposition=1', (fold,)).fetchone()
    if rows[0] < 2:
        raise core.SurveyError('metadata_ineligible', 'seal')
    db.execute('CREATE TABLE IF NOT EXISTS sources (fold INTEGER, source INTEGER, block_e INTEGER, '
               'block_n INTEGER, e REAL, n REAL, z REAL, PRIMARY KEY(fold,source))')
    db.execute('CREATE INDEX IF NOT EXISTS block_row_order ON rows(block_e,block_n,id)')
    query = ('SELECT DISTINCT r.block_e,r.block_n FROM rows r JOIN part p ON r.pos=p.pos '
             'WHERE p.fold=? AND p.disposition=1 ORDER BY r.block_e,r.block_n')
    blocks = list(db.execute(query+' LIMIT ?', (fold, configuration['max_sources']+1)))
    if not 1 <= len(blocks) <= configuration['max_sources']:
        raise core.SurveyError('resource_refused', 'seal')
    height = rows[1]-depth
    if not math.isfinite(height) or height == rows[1]:
        raise core.SurveyError('metadata_ineligible', 'seal')
    db.execute('CREATE TABLE IF NOT EXISTS members (fold INTEGER,pos INTEGER,source INTEGER, PRIMARY KEY(fold,pos))')
    for index, (east, north) in enumerate(blocks):
        condition = ' FROM rows r JOIN part p ON r.pos=p.pos WHERE p.fold=? AND p.disposition=1 AND r.block_e=? AND r.block_n=?'
        args = (fold, east, north)
        count = db.execute('SELECT count(*)'+condition, args).fetchone()[0]
        e = math.fsum(v for v, in db.execute('SELECT r.e'+condition+' ORDER BY r.id', args))/count
        n = math.fsum(v for v, in db.execute('SELECT r.n'+condition+' ORDER BY r.id', args))/count
        if not math.isfinite(e) or not math.isfinite(n):
            raise core.SurveyError('metadata_ineligible', 'seal')
        db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)', (fold, index, east, north, e, n, height))
        db.execute('INSERT INTO members SELECT ?,r.pos,?'+condition, (fold, index, *args))
    db.commit()
    identity = sha256()
    for row in db.execute('SELECT source,block_e,block_n,e,n,z FROM sources WHERE fold=? ORDER BY source', (fold,)):
        identity.update(base.canonical_bytes(list(row)))
    positions = io.write_array(output, f'f{fold}-sources', 'source_position',
        db.execute('SELECT e,n,z FROM sources WHERE fold=? ORDER BY source', (fold,)),
        [len(blocks), 3], 'float64', 'm', identity.hexdigest())
    ids_hash = _ordered_hash(db, 'WHERE pos IN (SELECT pos FROM members WHERE fold=?)', (fold,))
    members = io.write_array(output, f'f{fold}-members', 'source_block_member',
        db.execute('SELECT pos,source FROM members WHERE fold=? ORDER BY pos', (fold,)),
        [rows[0], 2], 'uint64', 'identity', ids_hash)
    table = io.write_table(output, f'f{fold}-blocks', 'source_block',
        (dict(row_index=p, block_e=e, block_n=n, source_index=s) for p,e,n,s in db.execute(
            'SELECT r.pos,r.block_e,r.block_n,m.source FROM rows r JOIN members m ON r.pos=m.pos '
            'WHERE m.fold=? ORDER BY r.pos', (fold,))))
    return positions, members, table


def plan_partitions(geometry_root, inspection, request, request_root, output, *, temp_root, alignment=None):
    """All whole-line folds, conservative tie exclusions and training sources.

    Returns a closed *internal planning* receipt, not the complete GeometrySeal:
    crossover/support/navigation still have independent stages. No values are
    opened; every selected row remains represented or explicitly excluded.
    """
    request = schema.validate('SurveyRequest', request)
    output = io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch', 'seal')
    output.mkdir()
    request_reader = io.Reader(request_root)
    split = request['split']
    outer = _ids(request_reader, split['outer_line_ids'])
    anchors = set() if split['anchor_line_ids'] is None else _ids(request_reader, split['anchor_line_ids'])
    heldout = list(request_reader.table(split['heldout_blocks']))
    folds = [(None, outer, heldout)]
    for fold in split['inner_folds']:
        folds.append((fold['fold_id'], _ids(request_reader, fold['validation_line_ids']),
                      list(request_reader.table(fold['validation_blocks']))))
    used = outer | anchors
    for _, ids, _ in folds[1:]:
        if not ids or ids & used:
            raise core.SurveyError('invalid_contract', 'seal')
        used |= ids
    if not outer or outer & anchors:
        raise core.SurveyError('invalid_contract', 'seal')
    if split['geometry_manifest_sha256'] != inspection['geometry_sha256']:
        raise core.SurveyError('custody_mismatch', 'seal')
    with geometry_index(geometry_root, inspection, temp_root=temp_root, alignment=alignment) as (db, _, lines, sensors):
        sensor_ids = [row['sensor_id'] for row in sensors]
        if request['sensor_id'] not in sensor_ids:
            raise core.SurveyError('metadata_ineligible', 'seal')
        selected = sensor_ids.index(request['sensor_id'])
        flights = {lines[i]['line_id'] for i, in db.execute('SELECT DISTINCT line FROM rows WHERE sensor=?', (selected,))
                   if lines[i]['kind'] != 'tie'}
        if used != flights:
            raise core.SurveyError('invalid_contract', 'seal')
        configuration = request['equivalent_sources']['source_geometry']
        for pos,e,n,mask in db.execute('SELECT pos,e,n,mask FROM rows WHERE sensor=? ORDER BY pos', (selected,)):
            if mask & 2:
                raise core.SurveyError('metadata_ineligible', 'seal')
            block = (math.floor((e-configuration['origin_e_m'])/configuration['block_e_m']),
                     math.floor((n-configuration['origin_n_m'])/configuration['block_n_m']))
            if any(not -2147483648 <= b <= 2147483647 for b in block):
                raise core.SurveyError('resource_refused', 'seal')
            db.execute('UPDATE rows SET block_e=?,block_n=? WHERE pos=?', (*block, pos))
        db.execute('CREATE TABLE part (fold INTEGER,pos INTEGER,disposition INTEGER,PRIMARY KEY(fold,pos))')
        db.execute('CREATE INDEX disposition_order ON part(fold,disposition,pos)')
        results = []
        for index, (fold_id, ids, blocks) in enumerate(folds):
            rectangles = [_rectangle(b) for b in blocks]
            buffered = [_rectangle(b, split['buffer_m']) for b in heldout+blocks]
            db.execute('CREATE TABLE excluded (pos INTEGER PRIMARY KEY)')
            previous = None
            for pos,line,sensor,e,n in db.execute('SELECT pos,line,sensor,e,n FROM rows WHERE sensor=? ORDER BY line,sensor,ordinal', (selected,)):
                if lines[line]['kind'] != 'tie':
                    continue
                point = (e,n)
                if any(_contains(point, rectangle) for rectangle in buffered):
                    db.execute('INSERT OR IGNORE INTO excluded VALUES (?)', (pos,))
                if previous is not None and previous[1:3] == (line,sensor) and any(
                    segment_rectangle(previous[3], point, rectangle) for rectangle in buffered):
                    db.executemany('INSERT OR IGNORE INTO excluded VALUES (?)', [(previous[0],), (pos,)])
                previous = (pos,line,sensor,point)
            for pos,line,e,n in db.execute('SELECT pos,line,e,n FROM rows WHERE sensor=? ORDER BY pos', (selected,)):
                line_id = lines[line]['line_id']
                excluded = db.execute('SELECT 1 FROM excluded WHERE pos=?', (pos,)).fetchone() is not None
                disposition = 2 if line_id in ids else 3 if excluded or line_id in outer else 1
                if disposition == 2 and not any(_contains((e,n), rectangle) for rectangle in rectangles):
                    raise core.SurveyError('metadata_ineligible', 'seal')
                db.execute('INSERT INTO part VALUES (?,?,?)', (index,pos,disposition))
            db.execute('DROP TABLE excluded')
            count, groups = db.execute('SELECT count(*),count(DISTINCT r.line) FROM rows r JOIN part p ON r.pos=p.pos '
                                      'WHERE p.fold=? AND p.disposition=1', (index,)).fetchone()
            if count < 2 or groups < 4 or not db.execute('SELECT 1 FROM part WHERE fold=? AND disposition=2 LIMIT 1', (index,)).fetchone():
                raise core.SurveyError('metadata_ineligible', 'seal')
            refs = [_indexes(db, output, f'f{index}-{role}', index, number)
                    for role, number in (('train',1), ('validation',2), ('excluded',3))]
            sources, members, source_table = _source_blocks(db, output, index, configuration,
                                            request['equivalent_sources']['depth_candidates_m'][0])
            results.append(dict(fold_id=fold_id, training=refs[0], validation=refs[1], exclusions=refs[2],
                                sources=sources, source_members=members, source_blocks=source_table))
        grid = request['grid']
        cells = grid['nx']*grid['ny']*(2 if grid['continuation_delta_m'] is not None else 1)
        boundary = grid['boundary_policy']
        fft = (grid['nx']+2*boundary['pad_e_cells'])*(grid['ny']+2*boundary['pad_n_cells'])
        capacity = core.plan_capacity(inspection['rows'], max(f['sources']['shape'][0] for f in results),
                    raw_bytes=inspection['original']['csv_bytes'], exported_cells=cells, fft_cells=fft)
        result = dict(schema='m03-partition-source-plan/1', geometry_sha256=inspection['geometry_sha256'],
            request_sha256=base.digest(request), original=inspection['original'], rows=inspection['rows'],
            partitions=results, capacity=capacity, value_access='not_opened',
            complete_geometry_seal=False, remaining_geometry_stages=['navigation', 'crossovers', 'support'])
        if alignment is not None:
            result['navigation_sha256'] = base.digest(alignment[1])
        core._write_member(output, 'partition-plan.json', base.canonical_bytes(result))
        return result
