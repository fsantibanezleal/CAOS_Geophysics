"""Global frozen-v1 fitting of the actually corrected original instrument channel.

This is not the opened-S1 diagnostic adapter. It consumes the independently
produced physical DAG and corrected geometry, retains every original row, and
executes all 24 inner fits and one final fit. A converged solve is not a
predictive/field PASS or an assembled SurveyResult.
"""
from __future__ import annotations

from functools import partial
from hashlib import sha256
import math
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
import magnetic_line_survey_contract_v2 as v2
import magnetic_line_survey_representation as representation
from magnetic_line_survey_fit import (
    _readonly, _rmse, _solve, mapped_array, mapping_lifetime,
    predict_global, select_candidate,
)


def select_resolution_candidate(candidates):
    """All32 three-fold averages, declared training-only tie ordering."""
    expected=[(g,depth,damping) for g in range(4) for depth in (200.,500.) for damping in (.0001,.01,1.,100.)]
    if type(candidates) is not list or len(candidates)!=32:
        raise core.SurveyError('nonconverged','fit')
    for item,identity in zip(candidates,expected,strict=True):
        core._closed(item,'source_geometry_index depth_m damping mean_rmse_nT','fit')
        if (item['source_geometry_index'],item['depth_m'],item['damping'])!=identity or \
           type(item['source_geometry_index']) is not int or type(item['mean_rmse_nT']) not in (int,float) or \
           not math.isfinite(item['mean_rmse_nT']) or item['mean_rmse_nT']<0:
            raise core.SurveyError('nonconverged','fit')
    best=min(item['mean_rmse_nT'] for item in candidates)
    return max((item for item in candidates if abs(item['mean_rmse_nT']-best)<=1e-9),
        key=lambda item:(item['damping'],item['depth_m'],-item['source_geometry_index']))


def fit_corrected(seal_root, sealed, measurement_root, measurements, correction_root, corrected,
                  metadata, request, output, *, temp_root, job_handle):
    """Fit one global operator per frozen fold; outer scores only after selection.

    Only the current in-process producer composition calls this entry point.
    No caller may relabel raw intensity as an anomaly or inject a diagnostic
    fit/result envelope. Fixed independent physical corrections are already
    verified on the original row order. Learned/fold-local leveling is separate.
    """
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    resolution=request.get('schema')=='magnetic-line-survey-request/2'
    contract=v2 if resolution else schema
    request, metadata = contract.validate('SurveyRequest', request), contract.validate('SurveyInput', metadata)
    seal = contract.validate('GeometrySeal', sealed['geometry'])
    output = io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch', 'fit')
    if metadata['source_kind'] != 'original_synthetic_acquisition' or metadata['authored_control'] is None or \
       any(op['operation'] not in ('lag', 'diurnal', 'heading', 'main_field') for op in request['operations']):
        raise core.SurveyError('metadata_ineligible', 'fit')
    core._closed(corrected, 'schema original rows geometry_sha256 request_sha256 input_channel_sha256 '
        'output_sha256 channels masks edges field_acceptance numerical_admission original_rows_retained', 'fit')
    reader, measured, derived = representation.Reader(seal_root), io.Reader(measurement_root), io.Reader(correction_root)
    if base.strict_json(base.read_bounded(core._plain_path(reader.root/'geometry-seal.json'), 2097152)) != seal or \
       base.strict_json(base.read_bounded(core._plain_path(measured.root/'measurement-pass.json'), 2097152)) != measurements or \
       base.strict_json(base.read_bounded(core._plain_path(derived.root/'instrument-corrections.json'), 2097152)) != corrected or \
       corrected['schema'] != 'm03-instrument-corrections/1' or corrected['geometry_sha256'] != base.digest(seal) or \
       corrected['request_sha256'] != base.digest(request) or corrected['input_channel_sha256'] != request['channel_sha256'] or \
       corrected['original'] != seal['original'] or seal['original'] != metadata['original'] or \
       measurements['original'] != seal['original'] or corrected['rows'] != seal['rows'] or \
       corrected['original_rows_retained'] != seal['rows'] or measurements['rows'] != seal['rows'] or \
       sealed['partitions']['request_sha256'] != base.digest(request):
        raise core.SurveyError('custody_mismatch', 'fit')
    for ref in seal['arrays']+seal['dictionaries']:
        reader.verify(ref)
    if resolution:
        proof=base.strict_json(reader.member(sealed['capacity_proof']))
        if proof['capacity']!=seal['capacity'] or proof['source_counts_by_geometry']!=seal['source_counts_by_geometry'] or \
           proof['request_sha256']!=base.digest(request) or proof['value_access']!='not_opened' or \
           proof['proof']['mandatory_fit_count']!=97:
            raise core.SurveyError('custody_mismatch','fit')
    reader.reject_unknown(extra=('geometry-seal.json',))
    for ref in measurements['arrays']:
        measured.verify(ref)
    measured.reject_unknown(extra=('measurement-pass.json',))
    if len(corrected['channels']) != len(request['operations'])+1 or \
       len(corrected['channels']) != len(corrected['masks']) or len(corrected['edges']) != len(request['operations']):
        raise core.SurveyError('custody_mismatch', 'fit')
    row_hash = next(ref['ordered_ids_sha256'] for ref in metadata['arrays'] if ref['role']=='row_id')
    parent = request['channel_sha256']
    for index, channel in enumerate(corrected['channels']):
        channel = schema.validate('ChannelReceipt', channel)
        mask = schema.validate('ArrayRef', corrected['masks'][index])
        if channel['data']['role'] != 'magnetic' or channel['data']['dtype'] != 'float64' or \
           channel['data']['unit'] != 'nT' or mask['role'] != 'qc_mask' or mask['dtype'] != 'uint32' or \
           mask['unit'] != 'identity' or channel['data']['mask_array_id'] != mask['array_id'] or \
           any(ref['shape'] != [seal['rows']] or ref['ordered_ids_sha256'] != row_hash for ref in (channel['data'], mask)):
            raise core.SurveyError('custody_mismatch', 'fit')
        derived.verify(channel['data'])
        derived.verify(mask)
        if index:
            edge = corrected['edges'][index-1]
            state = channel['state'][-1]
            if edge['operation'] != request['operations'][index-1]['operation'] or \
               edge['parent_sha256'] != parent or channel['parent_sha256'] != parent or \
               state['status'] != 'applied' or state['output_channel_sha256'] != edge['output_sha256'] or \
               state['evidence_sha256'] != edge['evidence_sha256']:
                raise core.SurveyError('custody_mismatch', 'fit')
            parent = edge['output_sha256']
    derived.reject_unknown(extra=('instrument-corrections.json',))
    if parent != corrected['output_sha256'] or channel['kind'] != 'scalar_total_field_anomaly':
        raise core.SurveyError('metadata_ineligible', 'fit')
    cfg = request['equivalent_sources']
    weighted = cfg['weights_policy']=='admitted_inverse_variance'
    if weighted and (metadata['uncertainty'] is None or metadata['uncertainty']['meaning']!='independent_one_sigma' or
                     metadata['uncertainty']['independence_assumption']!='row_independent'):
        raise core.SurveyError('metadata_ineligible', 'fit')
    output.mkdir()
    np, _ = core.engines()
    with io.scratch_directory(temp_root) as scratch, mapping_lifetime() as mappings:
        scratch = Path(scratch)
        map_array = partial(mapped_array, registry=mappings)
        geometry = {ref['role']:ref for ref in metadata['arrays']}
        if 'navigation' in sealed:
            xyz = map_array(reader, sealed['navigation']['coordinates'], scratch/'xyz.bin', np)
        else:
            axes = [map_array(reader, geometry[role], scratch/(role+'.bin'), np)
                    for role in ('easting','northing','upward')]
            xyz = _readonly(np, np.column_stack(axes))
            del axes
        values = map_array(derived, channel['data'], scratch/'values.bin', np)
        flags = map_array(derived, mask, scratch/'flags.bin', np)
        original_values = {ref['role']:ref for ref in measurements['arrays']}
        sigma = map_array(measured, original_values['uncertainty'], scratch/'sigma.bin', np)
        missing = map_array(measured, original_values['missing_mask'], scratch/'missing.bin', np)
        ids = map_array(reader, geometry['row_id'], scratch/'ids.bin', np)
        line_indexes = map_array(reader, geometry['line_index'], scratch/'line.bin', np)
        parts, inventories = sealed['partitions']['partitions'], []
        source_maps={}
        if resolution:
            # All16 readonly source arrays require at most48*M float64 cells;
            # the existing64*M phase allowance also covers the live source copy,
            # scales and coefficients. Training/validation mappings are SHARED
            # across geometries, not sixteen copies of the original N rows.
            for item in seal['source_maps']:
                key=(item['source_geometry_index'],item['fold_id'])
                source_maps[key]=map_array(reader,item['sources'],scratch/f'source{key[0]}{key[1]}.bin',np)
            if len(source_maps)!=16:
                raise core.SurveyError('custody_mismatch','fit')
        for number, part in enumerate(parts):
            support_ref = sealed['support']['partitions'][number]['validation_mask']
            if any(part[key] not in seal['arrays'] for key in (('training','validation','exclusions') if resolution else
                    ('training','validation','exclusions','sources','source_members'))) or \
               support_ref not in seal['arrays']:
                raise core.SurveyError('custody_mismatch', 'fit')
            train = map_array(reader, part['training'], scratch/f'train{number}.bin', np)
            valid = map_array(reader, part['validation'], scratch/f'valid{number}.bin', np)
            support = map_array(reader, support_ref, scratch/f'support{number}.bin', np)
            sources = source_maps[(0,part['fold_id'])] if resolution else map_array(reader, part['sources'], scratch/f'sources{number}.bin', np)
            for positions in (train, valid):
                if np.any(positions >= seal['rows']) or np.any(flags[positions]) or np.any(missing[positions] & (2|16)) or \
                   weighted and np.any(missing[positions] & 32):
                    # Current correction profile refuses unsupported rows, never
                    # silently changes a sealed source map or fills missing data.
                    raise core.SurveyError('metadata_ineligible', 'fit')
            valid = valid[support==0]
            if len(valid)==0:
                raise core.SurveyError('metadata_ineligible', 'fit')
            inventories.append((train, valid, sources))
        candidates, rows, current = [], [], None
        try:
            for geometry_index in range(4 if resolution else 1):
              for depth in cfg['depth_candidates_m']:
                for damping in cfg['damping_candidates']:
                    scores = []
                    for number, (train, valid, source) in enumerate(inventories[1:], 1):
                        current = dict(fold_id=parts[number]['fold_id'], depth_m=depth, damping=damping)
                        if resolution:
                            current['source_geometry_index']=geometry_index
                            source=source_maps[(geometry_index,parts[number]['fold_id'])]
                        sources = source.copy()
                        sources[:,2] = min(float(xyz[i,2]) for i in train)-depth
                        sources.flags.writeable = False
                        fitted, operator, receipt = _solve(_readonly(np,xyz[train]), sources, _readonly(np,values[train]),
                            _readonly(np,sigma[train]) if weighted else None, damping, job_handle, scratch)
                        prediction = predict_global(_readonly(np,xyz[valid]), sources, fitted['coefficients'], job_handle=job_handle)
                        rmse = _rmse(values[valid]-prediction)
                        scores.append(rmse)
                        rows.append(contract.validate('CandidateFit', dict(**current, solve=receipt, scored=len(valid),
                            excluded=part_excluded(parts[number], valid), rmse_nT=rmse,
                            verdict=dict(overall='pass', gates=[dict(gate_id='solve', verdict='pass',
                                evidence_sha256=base.digest(receipt), reason=None)], numerical_success=True, reasons=[]))))
                        del fitted, operator, prediction, sources
                    candidate=dict(depth_m=depth, damping=damping, mean_rmse_nT=math.fsum(scores)/3)
                    if resolution:
                        candidate['source_geometry_index']=geometry_index
                    candidates.append(candidate)
            if len(rows)!=(96 if resolution else 24):
                raise core.SurveyError('nonconverged','fit')
            selected = select_resolution_candidate(candidates) if resolution else select_candidate(candidates)
            train, valid, source = inventories[0]
            if resolution:
                source=source_maps[(selected['source_geometry_index'],'final')]
            sources = source.copy()
            sources[:,2] = min(float(xyz[i,2]) for i in train)-selected['depth_m']
            sources.flags.writeable = False
            current = dict(fold_id='final', depth_m=selected['depth_m'], damping=selected['damping'])
            fitted, operator, receipt = _solve(_readonly(np,xyz[train]), sources, _readonly(np,values[train]),
                _readonly(np,sigma[train]) if weighted else None, selected['damping'], job_handle, scratch)
            prediction = predict_global(_readonly(np,xyz[valid]), sources, fitted['coefficients'], job_handle=job_handle)
            residual = _readonly(np, values[valid]-prediction)
            selected_map=seal['source_maps'][selected['source_geometry_index']*4] if resolution else parts[0]
            source_hash = selected_map['sources']['ordered_ids_sha256']
            source_ref = io.write_array(output, 'physical-sources', 'source_position', sources,
                [len(sources),3], 'float64', 'm', source_hash)
            scales = io.write_array(output, 'physical-scales', 'source_scale', operator.scales,
                [len(sources)], 'float64', '1_per_m', source_hash)
            coefficients = io.write_array(output, 'physical-coefficients', 'coefficient', fitted['coefficients'],
                [len(sources)], 'float64', 'nT*m', source_hash)
            table = representation.write_table(output,'physical-candidates','candidate_fit_v2',rows) if resolution else \
                io.write_table(output, 'physical-candidates', 'candidate_fit', rows)
            fit_fields=dict(solver=request['solver'], candidates=table,
                selected_depth_m=selected['depth_m'], selected_damping=selected['damping'], sources=source_ref,
                column_scales=scales, coefficients=coefficients, solve=receipt, fit_count=97 if resolution else 25)
            if resolution:
                fit_fields['selected_source_geometry_index']=selected['source_geometry_index']
            fit = contract.validate('FitReceipt',fit_fields)
            identity = sha256()
            for i in valid:
                identity.update(bytes(ids[i]).ljust(64,b'\0'))
            ordered = identity.hexdigest()
            outer = [io.write_array(output, 'physical-outer-'+role, role, array, [len(valid)], 'float64', 'nT', ordered)
                for role, array in (('magnetic',values[valid]), ('predicted',prediction), ('residual',residual))]
            positions = io.write_array(output, 'physical-outer-index', 'partition_index', valid,
                [len(valid)], 'uint64', 'identity', ordered)
            lines = list(reader.table(metadata['acquisition']['line_dictionary']))
            # Two linear passes, not one N-row scan/allocation for each line.
            counts = {}
            for i in reader.cells(parts[0]['validation']):
                line = int(line_indexes[i])
                item = counts.setdefault(line, [0, 0, 0., 0., 0., 0.])
                item[0] += 1
            for index, i in enumerate(valid):
                item = counts[int(line_indexes[i])]
                item[1] += 1
                for offset, value in ((2, float(residual[index])), (4, float(values[i]))):
                    square = value*value
                    if not math.isfinite(square) or value != 0 and square == 0:
                        raise core.SurveyError('nonconverged', 'evaluate')
                    increment = square-item[offset+1]
                    total = item[offset]+increment
                    item[offset+1] = (total-item[offset])-increment
                    item[offset] = total
            line_rows = [dict(line_id=lines[line]['line_id'], scored=item[1], excluded=item[0]-item[1],
                rmse_nT=math.sqrt(item[2]/item[1]) if item[1] else None,
                signal_rms_nT=math.sqrt(item[4]/item[1]) if item[1] else None) for line,item in sorted(counts.items())]
            per_line = io.write_table(output, 'physical-line-evaluation', 'line_evaluation', line_rows)
            result = dict(schema='m03-global-physical-fit/2' if resolution else 'm03-global-physical-fit/1', original=seal['original'], rows=seal['rows'],
                geometry_sha256=base.digest(seal), request_sha256=base.digest(request),
                correction_sha256=base.digest(corrected), output_channel_sha256=corrected['output_sha256'],
                fit=fit, candidate_scores=candidates, evaluation_count=1, outer_arrays=outer,
                outer_positions=positions, per_line=per_line, scored=len(valid),
                excluded=part_excluded(parts[0],valid), coverage=len(valid)/parts[0]['validation']['shape'][0],
                rmse_nT=_rmse(residual), signal_rms_nT=_rmse(values[valid]),
                field_acceptance='unresolved', predictive_acceptance='not_established', full_result='not_assembled')
            core._write_member(output, 'physical-fit.json', base.canonical_bytes(result))
            return result
        except core.SurveyError as error:
            core._write_member(output, 'physical-fit-failure.json', base.canonical_bytes(dict(
                schema='m03-global-physical-fit-failure/2', candidate=current, error=error.error,
                partial_solve=getattr(error,'partial_solve',None),
                completed_candidates=rows, field_acceptance='unresolved')))
            raise


def part_excluded(part, valid):
    return part['validation']['shape'][0]-len(valid)
