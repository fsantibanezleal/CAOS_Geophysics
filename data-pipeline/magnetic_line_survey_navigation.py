"""Stream verified navigation into a value-free original-row geometry edge."""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import itertools
import math

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
from magnetic_line_survey_geometry import geometry_index
from magnetic_lines import _utc_ns


def align_geometry(root, inspection, metadata, operation, auxiliary_root, output, *, temp_root):
    """Admit authored independent navigation only; field review is not invented.

    Geometry-only SQLite is rebuilt from original verified members. Navigation
    absolute UTC never becomes float64 or SQLite int64: use anchored relative
    nanoseconds and exact Fraction lag. No measurement channel is opened.
    """
    metadata = schema.validate('SurveyInput', metadata)
    operation = schema.validate('SurveyOperationRequest', operation)
    if operation['operation'] != 'lag':
        raise core.SurveyError('unsupported_operation', 'seal')
    parameters = operation['parameters']
    nav = parameters['navigation']
    identity = nav['identity']
    states = {state['operation']: state for state in metadata['channel_state']}
    expected_clock = base.digest(dict(measurement_basis='UTC', auxiliary_basis='UTC', offset_s=0.,
                                     definition='authored shared synthetic2001 clock'))
    if metadata['quantity']['kind'] != 'scalar_total_intensity' or \
       metadata['source_kind'] != 'original_synthetic_acquisition' or identity['source_verification'] != 'authored' or \
       nav['coordinates'] != metadata['coordinates'] or metadata['coordinates']['vertical_datum'] is None or \
       metadata['acquisition']['timestamp_basis'] != 'UTC' or \
       nav['clock']['synchronization_evidence_sha256'] != expected_clock or \
       any(name not in states or states[name]['status'] != 'not_applied' for name in ('lag', 'main_field')) or \
       len(states) != len(metadata['channel_state']) or metadata['reference'] is not None or \
       identity['rights']['decision'] != 'allowed' or identity['rights']['private_processing'] != 'allowed':
        raise core.SurveyError('metadata_ineligible', 'seal')
    if metadata['original'] != inspection['original'] or metadata['arrays'] != inspection['arrays'] or \
       [metadata['acquisition'][key] for key in ('line_dictionary', 'sensor_dictionary')] != inspection['dictionaries']:
        raise core.SurveyError('custody_mismatch', 'seal')
    refs = [nav[key] for key in ('row_ids', 'utc', 'line_index', 'xyz')]
    rows = refs[0]['shape'][0]
    if not 2 <= rows <= 16000000 or len({ref['array_id'] for ref in refs}) != 4 or \
       any(ref['ordered_ids_sha256'] != refs[0]['ordered_ids_sha256'] for ref in refs):
        raise core.SurveyError('invalid_contract', 'seal')
    for ref, role, shape in zip(refs, ('row_id', 'utc', 'line_index', 'navigation'),
                               ([rows], [rows], [rows], [rows, 3]), strict=True):
        if ref['role'] != role or ref['shape'] != shape or ref['mask_array_id'] is not None:
            raise core.SurveyError('invalid_contract', 'seal')
    output = io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch', 'seal')
    reader = io.Reader(auxiliary_root)
    identifiers = sha256()
    canonical = sha256(b'[')
    origin = None
    previous = {}
    tau = Fraction.from_float(parameters['tau_s']) * 1000000000
    gap = Fraction.from_float(parameters['max_bracket_gap_s']) * 1000000000
    with geometry_index(root, inspection, temp_root=temp_root) as (db, _, lines, _):
        db.execute('CREATE TABLE navigation (id TEXT UNIQUE,line INTEGER,t INTEGER,e REAL,n REAL,z REAL,PRIMARY KEY(line,t))')
        xyz = reader.cells(refs[3])
        triples = iter(lambda: tuple(itertools.islice(xyz, 3)), ())
        for position, (rid, utc, line, coordinates) in enumerate(zip(
                *(reader.cells(ref) for ref in refs[:3]), triples, strict=True)):
            if position >= rows or len(coordinates) != 3 or not 0 <= line < len(lines) or \
               db.execute('SELECT 1 FROM rows WHERE id=?', (rid,)).fetchone():
                raise core.SurveyError('invalid_contract', 'seal')
            absolute = _utc_ns(utc)
            if origin is None:
                origin = absolute
            relative = absolute - origin
            if not -(2**63) <= relative < 2**63 or (line in previous and relative <= previous[line]):
                raise core.SurveyError('invalid_contract', 'seal')
            previous[line] = relative
            identifiers.update(rid.encode('ascii').ljust(64, b'\0'))
            if position:
                canonical.update(b',')
            canonical.update(base.canonical_bytes(dict(utc=utc, line_id=lines[line]['line_id'],
                easting_m=coordinates[0], northing_m=coordinates[1], upward_m=coordinates[2])))
            db.execute('INSERT INTO navigation VALUES (?,?,?,?,?,?)', (rid, line, relative, *coordinates))
            if position % 4096 == 4095:
                db.commit()
        canonical.update(b']')
        reader.reject_unknown()
        if db.execute('SELECT count(*) FROM navigation').fetchone()[0] != rows or \
           identifiers.hexdigest() != refs[0]['ordered_ids_sha256'] or \
           canonical.hexdigest() != identity['canonical_records_sha256'] or \
           canonical.hexdigest() != identity['source_sha256'] or \
           identity['source_receipt_sha256'] != base.digest({k: v for k, v in identity.items() if k != 'source_receipt_sha256'}):
            raise core.SurveyError('custody_mismatch', 'seal')
        db.execute('CREATE TABLE aligned (pos INTEGER PRIMARY KEY,e REAL,n REAL,z REAL,mask INTEGER)')
        unsupported = 0
        coordinates_hash = sha256(b'{"datum":'+base.canonical_bytes(metadata['coordinates']['vertical_datum'])+b',"rows":[')
        for position, rid, line, utc, east, north, upward, mask in db.execute(
                'SELECT pos,id,line,utc,e,n,z,mask FROM rows ORDER BY pos'):
            aligned = None
            if not mask & 3:
                target = _utc_ns(utc) - origin + tau
                if not -(2**63) <= target < 2**63:
                    raise core.SurveyError('invalid_contract', 'seal')
                before = db.execute('SELECT t,e,n,z FROM navigation WHERE line=? AND t<=? ORDER BY t DESC LIMIT 1',
                                    (line, math.floor(target))).fetchone()
                after = db.execute('SELECT t,e,n,z FROM navigation WHERE line=? AND t>=? ORDER BY t LIMIT 1',
                                   (line, math.ceil(target))).fetchone()
                if before is not None and after is not None:
                    if before[0] == after[0]:
                        aligned = before[1:]
                    elif after[0] - before[0] <= gap:
                        weight = float((target - before[0]) / (after[0] - before[0]))
                        aligned = tuple(math.fsum(((1-weight)*left, weight*right))
                                        for left, right in zip(before[1:], after[1:], strict=True))
            flags = 0
            if aligned is None:
                aligned = (east, north, upward)
                flags = 1 << 5
                unsupported += 1
            if any(not math.isfinite(value) for value in aligned):
                raise core.SurveyError('metadata_ineligible', 'seal')
            db.execute('INSERT INTO aligned VALUES (?,?,?,?,?)', (position, *aligned, flags))
            if position:
                coordinates_hash.update(b',')
            coordinates_hash.update(base.canonical_bytes([rid, *aligned]))
        coordinates_hash.update(b']}')
        db.commit()
        output.mkdir()
        row_hash = next(ref['ordered_ids_sha256'] for ref in inspection['arrays'] if ref['role'] == 'row_id')
        coordinates = io.write_array(output, 'aligned-xyz', 'navigation', db.execute('SELECT e,n,z FROM aligned ORDER BY pos'),
                                     [inspection['rows'], 3], 'float64', 'm', row_hash)
        flags = io.write_array(output, 'aligned-flags', 'qc_mask', (v for v, in db.execute('SELECT mask FROM aligned ORDER BY pos')),
                              [inspection['rows']], 'uint32', 'identity', row_hash)
        result = dict(schema='m03-navigation-alignment/1', original=inspection['original'],
            original_geometry_sha256=inspection['geometry_sha256'], operation_sha256=base.digest(operation),
            datum=metadata['coordinates']['vertical_datum'],
            auxiliary=identity, coordinates=coordinates, mask=flags, coordinates_sha256=coordinates_hash.hexdigest(),
            unsupported_rows=unsupported, value_access='not_opened', field_acceptance='unresolved')
        core._write_member(output, 'navigation-alignment.json', base.canonical_bytes(result))
        return result


def apply_alignment_view(db, inspection, alignment):
    """Verify a producer alignment closure before planning on its coordinates.

    Only fully supported geometry enters this current seal path. Unsupported
    alignment remains a retained explicit refusal, never silently filtered.
    Original inspection and arrays are not rewritten or relabelled.
    """
    if type(alignment) is not tuple or len(alignment) != 2:
        raise core.SurveyError('invalid_contract', 'seal')
    root, receipt = alignment
    root = io.external_path(root)
    stored = base.strict_json(base.read_bounded(core._plain_path(root/'navigation-alignment.json'), 2097152))
    core._closed(stored, 'schema original original_geometry_sha256 operation_sha256 datum auxiliary '
                        'coordinates mask coordinates_sha256 unsupported_rows value_access field_acceptance', 'seal')
    if stored != receipt or stored['schema'] != 'm03-navigation-alignment/1' or \
       stored['original'] != inspection['original'] or stored['original_geometry_sha256'] != inspection['geometry_sha256'] or \
       stored['value_access'] != 'not_opened' or stored['field_acceptance'] != 'unresolved':
        raise core.SurveyError('custody_mismatch', 'seal')
    base.validate_named('AuxIdentity', stored['auxiliary'])
    for key in ('operation_sha256', 'coordinates_sha256'):
        base._type(stored[key], 'Hash', 'alignment', 0)
    base._type(stored['datum'], 'Text', 'alignment', 0)
    if type(stored['unsupported_rows']) is not int or not 0 <= stored['unsupported_rows'] <= inspection['rows']:
        raise core.SurveyError('invalid_contract', 'seal')
    row_hash = next(ref['ordered_ids_sha256'] for ref in inspection['arrays'] if ref['role'] == 'row_id')
    for key, role, shape in (('coordinates', 'navigation', [inspection['rows'], 3]),
                             ('mask', 'qc_mask', [inspection['rows']])):
        ref = schema.validate('ArrayRef', stored[key])
        if ref['role'] != role or ref['shape'] != shape or ref['ordered_ids_sha256'] != row_hash or ref['mask_array_id'] is not None:
            raise core.SurveyError('custody_mismatch', 'seal')
    reader = io.Reader(root)
    cells = reader.cells(stored['coordinates'])
    triples = iter(lambda: tuple(itertools.islice(cells, 3)), ())
    identity = sha256(b'{"datum":'+base.canonical_bytes(stored['datum'])+b',"rows":[')
    count = unsupported = 0
    for (pos, rid), xyz, flags in zip(db.execute('SELECT pos,id FROM rows ORDER BY pos'), triples,
                                    reader.cells(stored['mask']), strict=True):
        if len(xyz) != 3 or flags not in (0, 1 << 5):
            raise core.SurveyError('invalid_contract', 'seal')
        unsupported += bool(flags)
        if pos:
            identity.update(b',')
        identity.update(base.canonical_bytes([rid, *xyz]))
        db.execute('UPDATE rows SET e=?,n=?,z=? WHERE pos=?', (*xyz, pos))
        count += 1
    identity.update(b']}')
    reader.reject_unknown(extra=('navigation-alignment.json',))
    if count != inspection['rows'] or identity.hexdigest() != stored['coordinates_sha256'] or unsupported != stored['unsupported_rows']:
        raise core.SurveyError('custody_mismatch', 'seal')
    if unsupported:
        raise core.SurveyError('metadata_ineligible', 'seal')
    db.commit()
