"""Original-row streamed lag/base/heading/main-reference correction DAG.

No native fit, inferred field metadata, full-survey calibration or successful
SurveyResult is fabricated here. Every original row is retained in disk-backed
storage. Leveling and microlevel require their distinct fold/grid stages.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import itertools
import math

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
from magnetic_line_survey_geometry import geometry_index
from magnetic_line_survey_reference import validate_authored_reference
from magnetic_lines import _utc_ns


def run_instrument_worker(plan, workspace, job_handle, *, package_root=None,original_documents=None):
    """Execute original intake/seal/measurement/physical edges inside actual Job.

    This fixed component plan is not an owner HTTP recipe or full Result. The
    eventual full worker composes this same stage with global fit/export/replay.
    """
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    keys='schema csv_path geometry_root inspection metadata request request_root navigation_root auxiliary_roots reference_definitions'
    if type(plan) is dict and plan.get('schema')=='m03-full-result-plan/1':
        keys+=' run_id'
    core._closed(plan,keys,'correction')
    if plan['schema'] not in ('m03-instrument-correction-plan/1', 'm03-physical-fit-plan/1','m03-physical-grid-plan/1','m03-full-result-plan/1'):
        raise core.SurveyError('invalid_contract', 'correction')
    metadata, request = schema.validate('SurveyInput', plan['metadata']), schema.validate('SurveyRequest', plan['request'])
    from magnetic_line_survey_seal import seal_geometry
    from magnetic_line_survey_measurements import decode_measurements
    workspace = io.external_path(workspace)
    print('m03-worker:instrument-seal', flush=True)
    sealed = seal_geometry(plan['geometry_root'], plan['inspection'], metadata, request, plan['request_root'],
        workspace/'sealed', temp_root=workspace, navigation_root=plan['navigation_root'])
    print('m03-worker:instrument-measurements', flush=True)
    measurements = decode_measurements(plan['csv_path'], plan['geometry_root'], plan['inspection'], workspace/'measurements')
    print('m03-worker:instrument-corrections', flush=True)
    result = correct_instrument(workspace/'sealed', sealed, plan['geometry_root'], plan['inspection'],
        workspace/'measurements', measurements, metadata, request, workspace/'corrected', temp_root=workspace,
        auxiliary_roots=plan['auxiliary_roots'], reference_definitions=plan['reference_definitions'])
    core._write_member(workspace, 'instrument-ready.json', base.canonical_bytes(dict(schema='m03-instrument-ready/1',
        original=metadata['original'], rows=result['rows'], result_sha256=base.digest(result),
        output_sha256=result['output_sha256'], edges=len(result['edges']), numerical_admission='not_established',
        full_result='not_assembled', field_acceptance='unresolved')))
    if plan['schema'] in ('m03-physical-fit-plan/1','m03-physical-grid-plan/1','m03-full-result-plan/1'):
        from magnetic_line_survey_physical_fit import fit_corrected
        print('m03-worker:physical-global-fit', flush=True)
        fitted = fit_corrected(workspace/'sealed', sealed, workspace/'measurements', measurements,
            workspace/'corrected', result, metadata, request, workspace/'fit', temp_root=workspace, job_handle=job_handle)
        core._write_member(workspace, 'physical-fit-ready.json', base.canonical_bytes(dict(
            schema='m03-physical-fit-ready/1', original=metadata['original'], rows=fitted['rows'],
            result_sha256=base.digest(fitted), fit_count=fitted['fit']['fit_count'], evaluation_count=fitted['evaluation_count'],
            full_result='not_assembled', field_acceptance='unresolved', predictive_acceptance='not_established')))
        if plan['schema'] in ('m03-physical-grid-plan/1','m03-full-result-plan/1'):
            from magnetic_line_survey_grid import predict_grids
            print('m03-worker:physical-global-grid',flush=True)
            grids=predict_grids(workspace/'sealed',sealed,workspace/'fit',fitted,metadata,request,
                workspace/'grids',temp_root=workspace,job_handle=job_handle)
            core._write_member(workspace,'physical-grid-ready.json',base.canonical_bytes(dict(
                schema='m03-physical-grid-ready/1',original=metadata['original'],rows=fitted['rows'],
                result_sha256=base.digest(grids),grid_count=len(grids['grid']),
                full_result='not_assembled',field_acceptance='unresolved',predictive_acceptance='not_established')))
            if plan['schema']=='m03-full-result-plan/1':
                from magnetic_line_survey_environment import environment_identity
                from magnetic_line_survey_result import assemble_fixed_result
                if package_root is None:
                    raise core.SurveyError('custody_mismatch','export')
                print('m03-worker:full-environment',flush=True)
                environment=environment_identity(package_root,job_handle=job_handle)
                print('m03-worker:semantic-result',flush=True)
                full=assemble_fixed_result(workspace,sealed,measurements,result,fitted,grids,metadata,request,
                    plan['request_root'],plan['navigation_root'],plan['auxiliary_roots'],plan['reference_definitions'],
                    run_id=plan['run_id'],environment=environment,temp_root=workspace,job_handle=job_handle,
                    original_documents=original_documents)
                core._write_member(workspace,'result-ready.json',base.canonical_bytes(dict(
                    schema='m03-full-result-ready/1',result_sha256=base.digest(full),rows=full['inventory']['original_rows'],
                    policy_epoch=full['policy_epoch'],scientific_verdict=full['verdict']['overall'])))
    return 0


def _authored(identity, canonical_sha, metadata):
    if metadata['source_kind'] != 'original_synthetic_acquisition' or identity['source_verification'] != 'authored' or \
       identity['rights']['decision'] != 'allowed' or identity['rights']['private_processing'] != 'allowed':
        raise core.SurveyError('metadata_ineligible', 'correction')
    if identity['source_sha256'] != canonical_sha or identity['canonical_records_sha256'] != canonical_sha or \
       identity['source_receipt_sha256'] != base.digest({k:v for k,v in identity.items() if k!='source_receipt_sha256'}):
        raise core.SurveyError('custody_mismatch', 'correction')


def _base_index(db, series, root, metadata):
    clock = base.digest(dict(measurement_basis='UTC', auxiliary_basis='UTC', offset_s=0.,
                             definition='authored shared synthetic2001 clock'))
    if metadata['acquisition']['timestamp_basis'] != 'UTC' or series['clock']['synchronization_evidence_sha256'] != clock:
        raise core.SurveyError('metadata_ineligible', 'correction')
    utc, values = series['utc'], series['intensity']
    rows = utc['shape'][0]
    if not 2 <= rows <= 16000000 or values['shape'] != [rows] or \
       utc['role'] != 'utc' or values['role'] != 'base' or \
       any(ref['mask_array_id'] is not None for ref in (utc, values)) or \
       utc['ordered_ids_sha256'] != values['ordered_ids_sha256']:
        raise core.SurveyError('invalid_contract', 'correction')
    reader, canonical, ordered = io.Reader(root), sha256(b'['), sha256()
    db.execute('CREATE TABLE base_series (t INTEGER PRIMARY KEY, value REAL)')
    origin = previous = None
    count = 0
    for text, value in zip(reader.cells(utc), reader.cells(values), strict=True):
        absolute = _utc_ns(text)
        if origin is None:
            origin = absolute
        relative = absolute-origin
        if not -(2**63) <= relative < 2**63 or previous is not None and relative <= previous:
            raise core.SurveyError('invalid_contract', 'correction')
        previous = relative
        ordered.update(text.encode('ascii').ljust(30, b'\0'))
        if count:
            canonical.update(b',')
        canonical.update(base.canonical_bytes(dict(utc=text, intensity_nT=value)))
        db.execute('INSERT INTO base_series VALUES (?,?)', (relative, value))
        count += 1
    canonical.update(b']')
    if count != rows or ordered.hexdigest() != utc['ordered_ids_sha256']:
        raise core.SurveyError('custody_mismatch', 'correction')
    _authored(series['identity'], canonical.hexdigest(), metadata)
    reader.reject_unknown()
    return origin


def _heading(parameters, root, metadata):
    calibration = parameters['calibration']
    values = {k:parameters[k] for k in ('a0_nT', 'ac_nT', 'as_nT', 'convention')}
    _authored(calibration['identity'], base.digest(values), metadata)
    if calibration['coefficient_receipt_sha256'] != base.digest(values) or \
       calibration['calibration_row_ids']['role'] != 'row_id' or calibration['calibration_row_ids']['shape'] != [0]:
        # Nonempty/learned calibration needs its training-only estimator, not an
        # inference from a caller-provided coefficient hash.
        raise core.SurveyError('metadata_ineligible', 'correction')
    reader = io.Reader(root)
    reader.verify(calibration['calibration_row_ids'])
    reader.reject_unknown()


def correct_instrument(seal_root, sealed, geometry_root, inspection, measurement_root, measurements,
                       metadata, request, output, *, temp_root, auxiliary_roots, reference_definitions):
    """Complete these requested physical edges on all original rows, stdlib only.

    auxiliary_roots maps only literal operation names to explicit external roots;
    it is internal owner assembly, not a user JSON mapping/path dereference.
    Original measurement identity and current seal are independently rechecked.
    """
    metadata, request = schema.validate('SurveyInput', metadata), schema.validate('SurveyRequest', request)
    seal = schema.validate('GeometrySeal', sealed['geometry'])
    output = io.external_path(output)
    operations = [operation['operation'] for operation in request['operations']]
    if output.exists():
        raise core.SurveyError('custody_mismatch', 'correction')
    if type(auxiliary_roots) is not dict or type(reference_definitions) is not dict or \
       set(auxiliary_roots) != set(operations)-{'lag'} or set(reference_definitions) != ({'main_field'} if 'main_field' in operations else set()):
        raise core.SurveyError('invalid_contract', 'correction')
    if any(name not in ('lag', 'diurnal', 'heading', 'main_field') for name in operations):
        raise core.SurveyError('unsupported_operation', 'correction')
    if metadata['source_kind'] != 'original_synthetic_acquisition' or \
       metadata['rights']['decision'] != 'allowed' or metadata['rights']['private_processing'] != 'allowed' or \
       metadata['quantity']['kind'] not in ('scalar_total_intensity','scalar_total_field_anomaly') or \
       ('main_field' in operations and metadata['quantity']['kind']!='scalar_total_intensity'):
        raise core.SurveyError('metadata_ineligible', 'correction')
    if metadata['original'] != inspection['original'] or metadata['arrays'] != inspection['arrays'] or \
       seal['original'] != metadata['original'] or sealed['partitions']['request_sha256'] != base.digest(request):
        raise core.SurveyError('custody_mismatch', 'correction')
    sr = io.Reader(seal_root)
    if base.strict_json(base.read_bounded(core._plain_path(sr.root/'geometry-seal.json'), 2097152)) != seal:
        raise core.SurveyError('custody_mismatch', 'correction')
    for ref in seal['arrays']+seal['dictionaries']:
        sr.verify(ref)
    sr.reject_unknown(extra=('geometry-seal.json',))
    mr = io.Reader(measurement_root)
    core._closed(measurements, 'schema original rows geometry_sha256 arrays numerical_admission', 'correction')
    if base.strict_json(base.read_bounded(core._plain_path(mr.root/'measurement-pass.json'), 2097152)) != measurements or \
       measurements['schema'] != 'm03-measurement-pass/1' or measurements['original'] != seal['original'] or \
       measurements['geometry_sha256'] != inspection['geometry_sha256'] or measurements['rows'] != seal['rows']:
        raise core.SurveyError('custody_mismatch', 'correction')
    for ref in measurements['arrays']:
        mr.verify(ref)
    mr.reject_unknown(extra=('measurement-pass.json',))
    refs = {ref['role']:ref for ref in measurements['arrays']}
    if set(refs) != {'magnetic', 'uncertainty', 'missing_mask'}:
        raise core.SurveyError('custody_mismatch', 'correction')
    original_hash = next(ref['ordered_ids_sha256'] for ref in inspection['arrays'] if ref['role']=='row_id')
    if any(ref['shape'] != [seal['rows']] or ref['ordered_ids_sha256'] != original_hash for ref in refs.values()):
        raise core.SurveyError('custody_mismatch', 'correction')
    state, channels, edges = deepcopy(metadata['channel_state']), [], []
    with geometry_index(geometry_root, inspection, temp_root=temp_root) as (db, gr, _, sensors):
        db.execute('ALTER TABLE rows ADD COLUMN value REAL')
        db.execute('ALTER TABLE rows ADD COLUMN qc INTEGER')
        db.execute('ALTER TABLE rows ADD COLUMN heading REAL')
        heading = next(ref for ref in inspection['arrays'] if ref['role']=='heading')
        source_hash = sha256(b'[')
        for pos, (rid, sensor), value, mask, azimuth in zip(range(seal['rows']),
                db.execute('SELECT id,sensor FROM rows ORDER BY pos'), mr.cells(refs['magnetic']),
                mr.cells(refs['missing_mask']), gr.cells(heading), strict=True):
            value = None if mask & 16 else value
            qc = 1 << 13 if sensors[sensor]['sensor_id'] != request['sensor_id'] else 1 if value is None else 0
            if pos:
                source_hash.update(b',')
            source_hash.update(base.canonical_bytes([rid, value]))
            db.execute('UPDATE rows SET value=?,qc=?,heading=? WHERE pos=?',
                       (value, qc, None if mask & 64 else azimuth, pos))
        source_hash.update(b']')
        parent = source_hash.hexdigest()
        if parent != request['channel_sha256'] or request['split']['sealed_values_sha256'] != parent or \
           any(op['input_channel_sha256'] != parent for op in request['operations']):
            raise core.SurveyError('custody_mismatch', 'correction')
        kind, reference = metadata['quantity']['kind'], None
        output.mkdir()
        def emit(index, original=False):
            flags = io.write_array(output, f'channel{index}-flags', 'qc_mask',
                (value for value, in db.execute('SELECT qc FROM rows ORDER BY pos')), [seal['rows']],
                'uint32', 'identity', original_hash)
            data = io.write_array(output, f'channel{index}-values', 'magnetic',
                (0. if value is None else value for value, in db.execute('SELECT value FROM rows ORDER BY pos')),
                [seal['rows']], 'float64', 'nT', original_hash, mask=flags['array_id'])
            channels.append(schema.validate('ChannelReceipt', dict(channel_id='original' if original else f'derived{index:02d}',
                kind=kind, role='original' if original else 'derived', data=data, state=deepcopy(state),
                parent_sha256=None if original else edges[-1]['parent_sha256'],
                reference_receipt_sha256=None if reference is None else reference['receipt_sha256'])))
            return flags
        masks = [emit(0, original=True)]
        signs = dict(lag='position_time_plus_tau', diurnal='subtract_base_perturbation',
                     heading='subtract_heading_model', main_field='subtract_reference_F')
        for index, operation in enumerate(request['operations'], 1):
            name, parameters = operation['operation'], operation['parameters']
            known = [s for s in state if s['operation']==name]
            if len(known)!=1 or known[0]['status']!='not_applied':
                raise core.SurveyError('metadata_ineligible', 'correction')
            reference_verification = None
            if name == 'lag':
                nav = sealed.get('navigation')
                if nav is None or nav['operation_sha256'] != base.digest(operation) or nav['unsupported_rows'] != 0 or \
                   nav['coordinates_sha256'] != seal['coordinates_sha256'] or nav['original'] != seal['original']:
                    raise core.SurveyError('custody_mismatch', 'correction')
                xyz = sr.cells(nav['coordinates'])
                triples = iter(lambda: tuple(itertools.islice(xyz, 3)), ())
                for pos, triple, qc in zip(range(seal['rows']), triples, sr.cells(nav['mask']), strict=True):
                    if len(triple)!=3 or qc:
                        raise core.SurveyError('metadata_ineligible', 'correction')
                    db.execute('UPDATE rows SET e=?,n=?,z=? WHERE pos=?', (*triple, pos))
            elif name == 'diurnal':
                origin = _base_index(db, parameters['base'], auxiliary_roots[name], metadata)
                gap = Fraction.from_float(parameters['max_bracket_gap_s'])*1000000000
                intervals = [(_utc_ns(v['start']), _utc_ns(v['end'])) for v in parameters['valid_intervals']]
                for pos, utc, value, qc in db.execute('SELECT pos,utc,value,qc FROM rows ORDER BY pos'):
                    if qc:
                        continue
                    if not utc or not any(start <= _utc_ns(utc) <= end for start, end in intervals):
                        db.execute('UPDATE rows SET value=NULL,qc=qc|32 WHERE pos=?', (pos,))
                        continue
                    t = _utc_ns(utc)-origin
                    left = db.execute('SELECT t,value FROM base_series WHERE t<=? ORDER BY t DESC LIMIT 1', (t,)).fetchone()
                    right = db.execute('SELECT t,value FROM base_series WHERE t>=? ORDER BY t LIMIT 1', (t,)).fetchone()
                    if left is None or right is None or right[0]-left[0] > gap:
                        db.execute('UPDATE rows SET value=NULL,qc=qc|32 WHERE pos=?', (pos,))
                    else:
                        weight = 0. if left[0]==right[0] else float(Fraction(t-left[0], right[0]-left[0]))
                        perturbation = math.fsum(((1-weight)*left[1], weight*right[1]))-parameters['base_reference_nT']
                        db.execute('UPDATE rows SET value=? WHERE pos=?', (value-perturbation, pos))
            elif name == 'heading':
                _heading(parameters, auxiliary_roots[name], metadata)
                for pos, value, azimuth, qc in db.execute('SELECT pos,value,heading,qc FROM rows ORDER BY pos'):
                    if qc:
                        continue
                    if azimuth is None:
                        db.execute('UPDATE rows SET value=NULL,qc=qc|8 WHERE pos=?', (pos,))
                    else:
                        h = math.radians(azimuth)
                        correction = parameters['a0_nT']+parameters['ac_nT']*math.cos(h)+parameters['as_nT']*math.sin(h)
                        db.execute('UPDATE rows SET value=? WHERE pos=?', (value-correction, pos))
            else:
                if db.execute('SELECT 1 FROM rows WHERE qc&32 LIMIT 1').fetchone():
                    raise core.SurveyError('metadata_ineligible', 'correction')
                reference = parameters['evaluated_reference']
                reference_verification = validate_authored_reference(auxiliary_roots[name], reference, metadata, seal,
                    seal_root, definition=reference_definitions[name])
                rr = io.Reader(auxiliary_roots[name])
                for pos, field in enumerate(rr.cells(reference['scalar_F_nT'])):
                    db.execute('UPDATE rows SET value=value-? WHERE pos=? AND value IS NOT NULL', (field, pos))
                kind = 'scalar_total_field_anomaly'
            if any(value is not None and not math.isfinite(value) for value, in db.execute('SELECT value FROM rows')):
                raise core.SurveyError('metadata_ineligible', 'correction')
            # Explicit streamed edge domain, binding geometry and masks as well
            # as values. Not falsely equal to the bounded inline JSON DAG hash.
            identity = sha256(b'm03-correction-row-edge/1\0'+base.canonical_bytes(dict(operation=name, kind=kind)))
            for rid, e, n, z, value, qc in db.execute('SELECT id,e,n,z,value,qc FROM rows ORDER BY pos'):
                encoded = base.canonical_bytes([rid, e, n, z, value, qc])
                identity.update(len(encoded).to_bytes(8, 'little')+encoded)
            child = identity.hexdigest()
            evidence = base.digest(dict(operation=name, parent=parent, output=child, parameters=parameters))
            state.append(dict(operation=name, status='applied', parent_channel_sha256=parent, output_channel_sha256=child,
                evidence_sha256=evidence, parameters=parameters, units='m' if name=='lag' else 'nT', sign=signs[name], applied_by='processor'))
            edges.append(dict(operation=name, parent_sha256=parent, output_sha256=child,
                evidence_sha256=evidence, reference_verification=reference_verification))
            masks.append(emit(index))
            parent = child
        result = dict(schema='m03-instrument-corrections/1', original=seal['original'], rows=seal['rows'],
            geometry_sha256=base.digest(seal), request_sha256=base.digest(request), input_channel_sha256=request['channel_sha256'],
            output_sha256=parent, channels=channels, masks=masks, edges=edges, field_acceptance='unresolved',
            numerical_admission='not_established', original_rows_retained=seal['rows'])
        core._write_member(output, 'instrument-corrections.json', base.canonical_bytes(result))
        reader = io.Reader(output)
        for ref in [channel['data'] for channel in channels]+masks:
            reader.verify(ref)
        reader.reject_unknown(extra=('instrument-corrections.json',))
        return result
