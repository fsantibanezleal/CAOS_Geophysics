"""Global streamed fits and original S1 diagnostic, not physical admission.

The owner must seal actual geometry in its contained worker before opening
measurements. This adapter never treats an opened authored S1 as field data.
Correction requests require the independent fold-local correction stage and
are not approximated by fitting uncorrected values.
"""
from __future__ import annotations

from hashlib import sha256
from contextlib import contextmanager
from functools import partial
import math
import os
from pathlib import Path
import time

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io


def select_candidate(candidates):
    if type(candidates) is not list or not candidates:
        raise core.SurveyError('nonconverged','fit')
    for item in candidates:
        if type(item) is not dict or set(item) != {'depth_m','damping','mean_rmse_nT'} or \
           any(type(item[k]) not in (int,float) or not math.isfinite(item[k]) or item[k]<0 for k in item) or \
           item['depth_m']==0 or item['damping']==0:
            raise core.SurveyError('invalid_contract','fit')
    best = min(c['mean_rmse_nT'] for c in candidates)
    return max((c for c in candidates if abs(c['mean_rmse_nT']-best)<=1e-9),key=lambda c:(c['damping'],c['depth_m']))


def predict_global(query, sources, coefficients, *, job_handle=None):
    if job_handle is not None:
        from magnetic_line_survey_runtime import require_job
        require_job(job_handle)
    np,hm = core.engines()
    if type(query) not in (np.ndarray,np.memmap) or query.ndim!=2 or query.shape[1]!=3 or \
       type(sources) not in (np.ndarray,np.memmap) or sources.ndim!=2 or sources.shape[1]!=3:
        raise core.SurveyError('invalid_contract','predict')
    n,m = len(query),len(sources)
    if not 1<=n<=core.ROW_LIMIT or not 1<=m<=core.SOURCE_LIMIT:
        raise core.SurveyError('resource_refused','predict')
    if (n>128 or m>32) and job_handle is None:
        raise core.SurveyError('resource_refused','predict')
    core._array(np,query,(n,3))
    core._array(np,sources,(m,3))
    core._array(np,coefficients,(m,))
    core._finite(np,query)
    core._finite(np,sources)
    core._finite(np,coefficients)
    result = np.empty(n,dtype=np.float64)
    model = hm.EquivalentSources(dtype='float64',parallel=False)
    from threadpoolctl import threadpool_limits
    try:
        with threadpool_limits(limits=1), np.errstate(over='raise',divide='raise',invalid='raise'):
            for row in core._chunks(n,4096):
                x = query[row]
                total,comp = np.zeros(len(x)),np.zeros(len(x))
                for column in core._chunks(m,128):
                    s = sources[column]
                    distances = np.zeros((len(x),len(s)))
                    for axis in range(3):
                        distances += (x[:,axis,None]-s[None,:,axis])**2
                    if np.any(distances<=0) or not np.isfinite(distances).all():
                        raise core.SurveyError('metadata_ineligible','predict')
                    kernel = model.jacobian(tuple(x[:,a] for a in range(3)),tuple(s[:,a] for a in range(3)))
                    if type(kernel) is not np.ndarray or kernel.dtype!=np.float64 or kernel.shape!=(len(x),len(s)):
                        raise core.SurveyError('custody_mismatch','predict')
                    core._finite(np,kernel)
                    core._sum_into(total,comp,kernel@coefficients[column])
                result[row]=total
    except (FloatingPointError,OverflowError):
        raise core.SurveyError('nonconverged','predict') from None
    core._finite(np,result)
    result.flags.writeable=False
    return result


@contextmanager
def mapping_lifetime():
    mappings = []
    try:
        yield mappings
    finally:
        # Windows does not permit deleting mapped members. Close every owned
        # native mapping before its external temporary directory is removed.
        for mapping in reversed(mappings):
            mapping.close()


def mapped_array(reader, ref, destination, np, *, registry=None):
    """Verify chunks while creating an exclusive external read-only mapping."""
    schema.validate('ArrayRef',ref)
    destination = io.external_path(destination,directory=False)
    with destination.open('xb') as stream:
        for chunk in reader.chunks(ref):
            stream.write(chunk)
        stream.flush()
        os.fsync(stream.fileno())
    if ref['dtype'].startswith('ascii'):
        dtype = 'S'+str(io.WIDTHS[ref['dtype']])
    else:
        dtype = dict(float64='<f8',uint8='u1',uint32='<u4',uint64='<u8',int64='<i8')[ref['dtype']]
    if math.prod(ref['shape'])==0:
        value = np.empty(tuple(ref['shape']),dtype=dtype)
        value.flags.writeable=False
        return value
    array = np.memmap(destination,dtype=dtype,mode='r',shape=tuple(ref['shape']))
    if registry is not None:
        registry.append(array._mmap)
    return array


def _readonly(np,value):
    value = np.ascontiguousarray(value,dtype=np.float64)
    value.flags.writeable=False
    return value


def _rmse(residual):
    square = core._squared_norm(residual)
    value = math.sqrt(square/len(residual))
    if square>0 and value==0 or not math.isfinite(value):
        raise core.SurveyError('nonconverged','evaluate')
    return value


def _solve(xyz,sources,values,sigma,damping,job,workspace):
    from magnetic_line_survey_runtime import apis,counters,owned_bytes
    api,psapi = apis()
    before = counters(api,psapi,job,api.GetCurrentProcess())
    started = time.perf_counter()
    operator = core.GlobalOperator(xyz,sources,sigma,job_handle=job)
    try:
        solved = core.solve_global(operator,values,damping)
    except core.SurveyError as error:
        # Actual partial recurrence/calls are evidence only, never a successful
        # SolverReceipt or permission to continue an incomplete candidate matrix.
        error.partial_solve=dict(operator_forward_calls=operator.forward_calls,
            operator_adjoint_calls=operator.adjoint_calls,
            recurrence_estimates=getattr(operator,'solver_estimates',None))
        raise
    after = counters(api,psapi,job,api.GetCurrentProcess())
    timing = dict(cpu_s=after['cpu_s']-before['cpu_s'],wall_s=time.perf_counter()-started,
        peak_rss_bytes=after['peak_rss_bytes'],peak_committed_bytes=after['peak_committed_bytes'],
        scratch_bytes=owned_bytes(workspace),stop_cpu_s=None,stop_wall_s=None)
    receipt = {k:solved[k] for k in schema.SCHEMAS['SolverReceipt'] if k in solved}
    receipt.update(operator.solver_estimates,timing=timing,verdict='pass')
    return solved,operator,schema.validate('SolverReceipt',receipt)


def blocked_global_diagnostic(seal_root, sealed, measurement_root, measurements, metadata, request, output, *, temp_root, job_handle):
    """Execute every frozen fit for already-opened, uncorrected authored controls.

    Deliberately NOT a SurveyResult/field eligibility adapter. The actual owner
    invokes this after producing `sealed` in the same contained process. A
    public replay input cannot inject this in-memory producer return.
    """
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    request = schema.validate('SurveyRequest',request)
    metadata = schema.validate('SurveyInput',metadata)
    if request['operations'] or metadata['source_kind']!='original_synthetic_acquisition' or \
       metadata['authored_control'] is None or metadata['quantity']['kind']!='scalar_total_field_anomaly':
        raise core.SurveyError('metadata_ineligible','fit')
    seal = schema.validate('GeometrySeal',sealed['geometry'])
    seal_root,output = io.external_path(seal_root),io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','fit')
    if base.strict_json(base.read_bounded(core._plain_path(seal_root/'geometry-seal.json'),2097152)) != seal or \
       seal['original'] != metadata['original'] or measurements['original'] != seal['original'] or \
       sealed['partitions']['request_sha256']!=base.digest(request):
        raise core.SurveyError('custody_mismatch','fit')
    stored = base.strict_json(base.read_bounded(core._plain_path(io.external_path(measurement_root)/'measurement-pass.json'),2097152))
    if stored!=measurements or measurements['rows']!=seal['rows'] or measurements['geometry_sha256']!=sealed['partitions']['geometry_sha256']:
        raise core.SurveyError('custody_mismatch','fit')
    reader = io.Reader(seal_root)
    for ref in seal['arrays']+seal['dictionaries']:
        reader.verify(ref)
    reader.reject_unknown(extra=('geometry-seal.json',))
    mr = io.Reader(measurement_root)
    for ref in measurements['arrays']:
        mr.verify(ref)
    mr.reject_unknown(extra=('measurement-pass.json',))
    output.mkdir()
    np,_ = core.engines()
    with io.scratch_directory(temp_root) as scratch, mapping_lifetime() as mappings:
        scratch = Path(scratch)
        map_array = partial(mapped_array,registry=mappings)
        geom = {r['role']:r for r in metadata['arrays']}
        axes = [map_array(reader,geom[k],scratch/(k+'.bin'),np) for k in ('easting','northing','upward')]
        xyz = _readonly(np,np.column_stack(axes))
        del axes
        measured = {r['role']:r for r in measurements['arrays']}
        values = map_array(mr,measured['magnetic'],scratch/'values.bin',np)
        sigmas = map_array(mr,measured['uncertainty'],scratch/'sigma.bin',np)
        masks = map_array(mr,measured['missing_mask'],scratch/'missing.bin',np)
        ids = map_array(reader,geom['row_id'],scratch/'ids.bin',np)
        channel_hash = sha256()
        channel_hash.update(b'[')
        for position in range(seal['rows']):
            if position:
                channel_hash.update(b',')
            channel_hash.update(base.canonical_bytes([bytes(ids[position]).decode('ascii'),
                None if int(masks[position]) & 16 else float(values[position])]))
        channel_hash.update(b']')
        if request['channel_sha256'] != channel_hash.hexdigest() or request['split']['sealed_values_sha256'] != channel_hash.hexdigest():
            raise core.SurveyError('custody_mismatch','fit')
        cfg = request['equivalent_sources']
        weighted = cfg['weights_policy']=='admitted_inverse_variance'
        if weighted and (metadata['uncertainty'] is None or metadata['uncertainty']['meaning']!='independent_one_sigma' or
                         metadata['uncertainty']['independence_assumption']!='row_independent'):
            raise core.SurveyError('metadata_ineligible','fit')
        parts = sealed['partitions']['partitions']
        inventories = []
        for index,part in enumerate(parts):
            if any(part[key] not in seal['arrays'] for key in ('training','validation','exclusions','sources','source_members')):
                raise core.SurveyError('custody_mismatch','fit')
            train = map_array(reader,part['training'],scratch/f'train{index}.bin',np)
            valid = map_array(reader,part['validation'],scratch/f'valid{index}.bin',np)
            support = map_array(reader,sealed['support']['partitions'][index]['validation_mask'],scratch/f'support{index}.bin',np)
            sources = map_array(reader,part['sources'],scratch/f'sources{index}.bin',np)
            for positions in (train,valid):
                if np.any(positions>=seal['rows']) or np.any(masks[positions] & (2|16)) or weighted and np.any(masks[positions]&32):
                    raise core.SurveyError('metadata_ineligible','fit')
            valid = valid[support==0]
            if len(valid)==0:
                raise core.SurveyError('metadata_ineligible','fit')
            inventories.append((train,valid,sources))
        candidates,rows = [],[]
        current = None
        try:
            for depth in cfg['depth_candidates_m']:
                for damping in cfg['damping_candidates']:
                    scores = []
                    for number,(train,valid,source) in enumerate(inventories[1:],1):
                        current = dict(fold_id=parts[number]['fold_id'],depth_m=depth,damping=damping)
                        sources = source.copy()
                        sources[:,2] = min(float(xyz[i,2]) for i in train)-depth
                        sources.flags.writeable=False
                        fitted,operator,receipt = _solve(_readonly(np,xyz[train]),sources,_readonly(np,values[train]),
                            _readonly(np,sigmas[train]) if weighted else None,damping,job_handle,scratch)
                        prediction = predict_global(_readonly(np,xyz[valid]),sources,fitted['coefficients'],job_handle=job_handle)
                        rmse = _rmse(values[valid]-prediction)
                        scores.append(rmse)
                        rows.append(schema.validate('CandidateFit',dict(**current,solve=receipt,scored=len(valid),
                            excluded=parts[number]['validation']['shape'][0]-len(valid),rmse_nT=rmse,
                            verdict=dict(overall='pass',gates=[dict(gate_id='solve',verdict='pass',evidence_sha256=base.digest(receipt),reason=None)],
                                numerical_success=True,reasons=[]))))
                        del operator,fitted,prediction,sources
                    candidates.append(dict(depth_m=depth,damping=damping,mean_rmse_nT=math.fsum(scores)/3))
            selected = select_candidate(candidates)
            train,valid,source = inventories[0]
            sources = source.copy()
            sources[:,2] = min(float(xyz[i,2]) for i in train)-selected['depth_m']
            sources.flags.writeable=False
            current = dict(fold_id='final',depth_m=selected['depth_m'],damping=selected['damping'])
            fitted,operator,receipt = _solve(_readonly(np,xyz[train]),sources,_readonly(np,values[train]),
                _readonly(np,sigmas[train]) if weighted else None,selected['damping'],job_handle,scratch)
            # The outer observations are accessed for scoring exactly here,
            # after candidate selection and the one final training fit.
            prediction = predict_global(_readonly(np,xyz[valid]),sources,fitted['coefficients'],job_handle=job_handle)
            residual = _readonly(np,values[valid]-prediction)
            rmse,signal = _rmse(residual),_rmse(values[valid])
            source_hash = parts[0]['sources']['ordered_ids_sha256']
            source_ref = io.write_array(output,'final-sources','source_position',sources,[len(sources),3],'float64','m',source_hash)
            scales = io.write_array(output,'final-scales','source_scale',operator.scales,[len(sources)],'float64','1_per_m',source_hash)
            coefficients = io.write_array(output,'final-coefficients','coefficient',fitted['coefficients'],[len(sources)],'float64','nT*m',source_hash)
            table = io.write_table(output,'candidates','candidate_fit',rows)
            fit = schema.validate('FitReceipt',dict(solver=request['solver'],candidates=table,selected_depth_m=selected['depth_m'],
                selected_damping=selected['damping'],sources=source_ref,column_scales=scales,coefficients=coefficients,
                solve=receipt,fit_count=25))
            identity = sha256()
            for index in valid:
                identity.update(bytes(ids[index]).ljust(64,b'\0'))
            evaluation_arrays = [io.write_array(output,'outer-'+role,role,array,[len(valid)],'float64','nT',identity.hexdigest())
                                 for role,array in [('magnetic',values[valid]),('predicted',prediction),('residual',residual)]]
            threshold = max(.05*signal,1e-6) # protected original S1 gate
            predictive = 'pass' if rmse<=threshold else 'fail'
            result = dict(schema='m03-global-blocked-diagnostic/1',fit=fit,candidate_scores=candidates,evaluation_count=1,
                outer_arrays=evaluation_arrays,outer_scored=len(valid),outer_total=parts[0]['validation']['shape'][0],
                rmse_nT=rmse,signal_rms_nT=signal,s1_threshold_nT=threshold,
                s1_predictive_verdict=predictive if metadata['authored_control']['regime']=='S1' else 'unresolved',
                field_acceptance='unresolved',physical_reference_admission='not_established',geometry_sha256=base.digest(seal),
                request_sha256=base.digest(request),original=metadata['original'])
            core._write_member(output,'blocked-diagnostic.json',base.canonical_bytes(result))
            return result
        except core.SurveyError as error:
            # Failed candidates cannot be selected or upgraded by finite output.
            # No zero-valued fictional SolverReceipt substitutes for failure.
            core._write_member(output,'fit-failure.json',base.canonical_bytes(dict(schema='m03-global-fit-failure/1',
                candidate=current,error=error.error,completed_candidates=rows,field_acceptance='unresolved')))
            raise
