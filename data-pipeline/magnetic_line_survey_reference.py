"""Verify full original-row authored reference arrays without native imports.

This is a physical correction stage, not an IGRF evaluator, field admission,
parameter-selection routine or completed SurveyResult. Original arrays are
streamed at their real length; no ordinary 400-row loader is used.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import math
import itertools

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io


def _json_list_hash(values):
    identity = sha256(b'[')
    for index, value in enumerate(values):
        if index:
            identity.update(b',')
        identity.update(base.canonical_bytes(value))
    identity.update(b']')
    return identity.hexdigest()


def validate_authored_reference(root, reference, metadata, seal, original_root, *, definition,capacity_proof=None):
    """Reconstruct an explicit constant definition, dates and metric geometry.

    Definition is a verified FileIdentity of original authored F/D/I JSON, not a
    guessed site field. The evaluator's source SHA binds its canonical content.
    This rejects field/IGRF before reading arrays. Returning a receipt does not
    authorize the full method or assert predictive validity.
    """
    import magnetic_line_survey_contract_v2 as v2
    import magnetic_line_survey_representation as representation
    contract=v2 if metadata.get('schema')=='magnetic-line-survey-input/2' else schema
    reference = contract.validate('SurveyReference', reference)
    metadata = contract.validate('SurveyInput', metadata)
    seal = contract.validate('GeometrySeal', seal)
    definition = schema.validate('FileIdentity', definition)
    evaluator = reference['evaluator']
    if metadata['source_kind'] != 'original_synthetic_acquisition' or reference['kind'] != 'authored_constant' or \
       evaluator['name'] != 'authored_constant' or metadata['coordinates']['vertical_datum'] is None or \
       metadata['rights']['decision'] != 'allowed' or metadata['rights']['private_processing'] != 'allowed' or \
       reference['input_height_definition'] != metadata['coordinates']['vertical_datum'] or \
       reference['input_height_unit'] != 'm' or reference['datum_transform_evidence_sha256'] is not None or \
       reference['original_basis'] != 'ENU' or evaluator['source_rights_evidence_sha256'] != base.digest(metadata['rights']):
        raise core.SurveyError('metadata_ineligible', 'correction')
    if metadata['original'] != seal['original'] or reference['coordinates_sha256'] != seal['coordinates_sha256'] or \
       evaluator['input_coordinates_sha256'] != seal['coordinates_sha256'] or \
       reference['receipt_sha256'] != base.digest({k: v for k, v in reference.items() if k != 'receipt_sha256'}):
        raise core.SurveyError('custody_mismatch', 'correction')
    reader = io.Reader(root)
    source_bytes = reader.member(definition, limit=2097152)
    constant = base.strict_json(source_bytes)
    core._closed(constant, 'F_nT D_deg I_deg', 'correction')
    for key, spec in (('F_nT', 'Pos'), ('D_deg', 'F64'), ('I_deg', 'F64')):
        base._type(constant[key], spec, 'reference', 0)
    if not -180 <= constant['D_deg'] <= 180 or not -90 <= constant['I_deg'] <= 90:
        raise core.SurveyError('metadata_ineligible', 'correction')
    if base.digest(constant) != evaluator['source_sha256']:
        raise core.SurveyError('custody_mismatch', 'correction')
    dec, inc = math.radians(constant['D_deg']), math.radians(constant['I_deg'])
    expected = tuple(constant['F_nT']*v for v in
                     (math.cos(inc)*math.sin(dec), math.cos(inc)*math.cos(dec), -math.sin(inc)))
    original_refs = metadata['arrays']
    row_ref = next(r for r in original_refs if r['role'] == 'row_id')
    utc_ref = next(r for r in original_refs if r['role'] == 'utc')
    missing_ref = next(r for r in original_refs if r['role'] == 'missing_mask')
    row_hash, rows = row_ref['ordered_ids_sha256'], seal['rows']
    original_reader = representation.Reader(original_root)
    stored = contract.validate('GeometrySeal', base.strict_json(base.read_bounded(
        core._plain_path(original_reader.root/'geometry-seal.json'), 2097152)))
    if stored != seal or row_ref['shape'] != [rows]:
        raise core.SurveyError('custody_mismatch', 'correction')
    for ref in seal['arrays']+seal['dictionaries']:
        original_reader.verify(ref)
    if contract is v2:
        if capacity_proof is None:
            raise core.SurveyError('custody_mismatch','correction')
        original_reader.member(capacity_proof)
    elif capacity_proof is not None:
        raise core.SurveyError('custody_mismatch','correction')
    original_reader.reject_unknown(extra=('geometry-seal.json',))
    by_id = {ref['array_id']: ref for ref in seal['arrays']}
    if 'aligned-xyz' in by_id:
        xyz_cells = original_reader.cells(by_id['aligned-xyz'])
        triples = iter(lambda: tuple(itertools.islice(xyz_cells, 3)), ())
        flags = original_reader.cells(by_id['aligned-flags'])
        def coordinates():
            for xyz, flag in zip(triples, flags, strict=True):
                if len(xyz) != 3 or flag != 0:
                    raise core.SurveyError('metadata_ineligible', 'correction')
                yield xyz
    else:
        by_role = {ref['role']: ref for ref in original_refs}
        def coordinates():
            yield from zip(*(original_reader.cells(by_role[key]) for key in
                             ('easting', 'northing', 'upward')), strict=True)
    coordinate_hash = sha256(b'{"datum":'+base.canonical_bytes(metadata['coordinates']['vertical_datum'])+b',"rows":[')
    count = 0
    for rid, xyz in zip(original_reader.cells(row_ref), coordinates(), strict=True):
        if count:
            coordinate_hash.update(b',')
        coordinate_hash.update(base.canonical_bytes([rid, *xyz]))
        count += 1
    coordinate_hash.update(b']}')
    if count != rows or coordinate_hash.hexdigest() != seal['coordinates_sha256']:
        raise core.SurveyError('custody_mismatch', 'correction')
    epoch = reference['epoch']
    refs = [reference[k] for k in ('vector_east_nT', 'vector_north_nT', 'vector_up_nT', 'scalar_F_nT')]
    if epoch['row_date_decimal_year'] is not None:
        refs.append(epoch['row_date_decimal_year'])
    for ref in refs:
        if ref['shape'] != [rows] or ref['ordered_ids_sha256'] != row_hash or ref['mask_array_id'] is not None:
            raise core.SurveyError('custody_mismatch', 'correction')
        reader.verify(ref)
    start, end = evaluator['valid_start_decimal_year'], evaluator['valid_end_decimal_year']
    if start > end:
        raise core.SurveyError('metadata_ineligible', 'correction')
    tolerance = evaluator['rounding_tolerance_nT']
    count, first_vector = 0, None
    for values in zip(*(reader.cells(ref) for ref in refs[:4]), strict=True):
        if first_vector is None:
            first_vector = values
        if values[3] <= 0 or values[3] != constant['F_nT'] or \
           values != first_vector or \
           any(abs(value-wanted) > tolerance for value, wanted in zip(values[:3], expected, strict=True)) or \
           abs(math.hypot(*values[:3])-values[3]) > tolerance:
            raise core.SurveyError('metadata_ineligible', 'correction')
        count += 1
    if count != rows:
        raise core.SurveyError('custody_mismatch', 'correction')
    if epoch['date_mode'] == 'survey_reference':
        if not start <= epoch['date_decimal_year'] <= end:
            raise core.SurveyError('metadata_ineligible', 'correction')
    elif epoch['date_mode'] == 'row_utc':
        dates = reader.cells(epoch['row_date_decimal_year'])
        count = 0
        def checked_times():
            nonlocal count
            for utc, mask, actual in zip(original_reader.cells(utc_ref),
                                         original_reader.cells(missing_ref), dates, strict=True):
                if mask & 1:
                    raise core.SurveyError('metadata_ineligible', 'correction')
                date, nano = base.utc_key(utc)
                first = datetime(date.year, 1, 1, tzinfo=timezone.utc)
                last = datetime(date.year+1, 1, 1, tzinfo=timezone.utc)
                expected_date = date.year + ((date-first).total_seconds()+nano*1e-9)/(last-first).total_seconds()
                if actual != expected_date or not start <= actual <= end:
                    raise core.SurveyError('custody_mismatch', 'correction')
                count += 1
                yield utc
        if _json_list_hash(checked_times()) != epoch['row_utc_sha256'] or count != rows:
            raise core.SurveyError('custody_mismatch', 'correction')
    reader.reject_unknown()
    return dict(schema='m03-authored-reference-verification/1', rows=rows,
        reference_sha256=reference['receipt_sha256'], coordinates_sha256=seal['coordinates_sha256'],
        original=seal['original'], source=definition, canonical_source_sha256=base.digest(constant),
        epoch=epoch, arrays=refs, ordered_ids_sha256=row_hash, field_acceptance='unresolved')
