"""Source-bound full-grid prediction and transforms from the physical global fit."""
from __future__ import annotations

from functools import partial
from hashlib import sha256
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema
import magnetic_line_survey_io as io
import magnetic_line_survey_representation as representation
import magnetic_line_survey_contract_v2 as representation_schema
from magnetic_line_survey_fit import mapped_array, mapping_lifetime, predict_global, _readonly
from magnetic_line_survey_support import grid_ids, SAMPLING_UNRESOLVED


def predict_grids(seal_root, sealed, fit_root, fitted, metadata, request, output, *, temp_root, job_handle):
    """Keep sealed holes; never silently omit a requested ineligible transform."""
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    metadata, request = schema.validate('SurveyInput',metadata), schema.validate('SurveyRequest',request)
    representation_schema.validate('SurveyGrid',request['grid'])
    seal = schema.validate('GeometrySeal',sealed['geometry'])
    fit = schema.validate('FitReceipt',fitted['fit'])
    output = io.external_path(output)
    if output.exists():
        raise core.SurveyError('custody_mismatch','predict')
    reader, fr = io.Reader(seal_root), io.Reader(fit_root)
    if base.strict_json(base.read_bounded(core._plain_path(reader.root/'geometry-seal.json'),2097152)) != seal or \
       base.strict_json(base.read_bounded(core._plain_path(fr.root/'physical-fit.json'),2097152)) != fitted or \
       fitted['schema'] != 'm03-global-physical-fit/1' or fitted['original'] != metadata['original'] or \
       seal['original'] != metadata['original'] or fitted['geometry_sha256'] != base.digest(seal) or \
       fitted['request_sha256'] != base.digest(request) or fitted['evaluation_count'] != 1:
        raise core.SurveyError('custody_mismatch','predict')
    config = request['grid']
    if metadata['coordinates']['vertical_datum'] is None or config['datum'] != metadata['coordinates']['vertical_datum']:
        raise core.SurveyError('metadata_ineligible','predict')
    for ref in seal['arrays']+seal['dictionaries']:
        reader.verify(ref)
    reader.reject_unknown(extra=('geometry-seal.json',))
    for ref in [fit[key] for key in ('sources','column_scales','coefficients','candidates')] + \
               fitted['outer_arrays']+[fitted['outer_positions'],fitted['per_line']]:
        fr.verify(ref)
    fr.reject_unknown(extra=('physical-fit.json',))
    cells = config['ny']*config['nx']
    planes = 2 if config['continuation_delta_m'] is not None else 1
    spectral_cells=0 if request['spectrum'] is None else request['spectrum']['rectangle']['ny']*request['spectrum']['rectangle']['nx']
    if cells*planes+spectral_cells > 1048576 or sealed['geometry']['capacity']['exported_cells'] < cells*planes+spectral_cells:
        raise core.SurveyError('resource_refused','predict')
    support = sealed['support']['grid_mask']
    if support not in seal['arrays'] or support['role']!='grid_mask' or support['dtype']!='uint32' or \
       support['shape'] != [config['ny'],config['nx']] or support['ordered_ids_sha256'] != grid_ids(config):
        raise core.SurveyError('custody_mismatch','predict')
    output.mkdir()
    np, _ = core.engines()
    with io.scratch_directory(temp_root) as scratch, mapping_lifetime() as mappings:
        scratch = Path(scratch)
        mapper = partial(mapped_array,registry=mappings)
        sources = mapper(fr,fit['sources'],scratch/'sources.bin',np)
        coefficients = mapper(fr,fit['coefficients'],scratch/'coefficients.bin',np)
        masks = mapper(reader,support,scratch/'masks.bin',np)
        original_geom = {ref['role']:ref for ref in metadata['arrays']}
        if 'navigation' in sealed:
            xyz = mapper(reader,sealed['navigation']['coordinates'],scratch/'xyz.bin',np)
            upward = xyz[:,2]
        else:
            upward = mapper(reader,original_geom['upward'],scratch/'upward.bin',np)
        training = reader.cells(sealed['partitions']['partitions'][0]['training'])
        maximum_training_height = max(float(upward[i]) for i in training)
        if config['plane_upward_m'] < maximum_training_height or not np.all(sources[:,2] < config['plane_upward_m']):
            raise core.SurveyError('metadata_ineligible','predict')
        axes = []
        for name, origin, spacing, count in (('easting',config['origin_e_m'],config['spacing_e_m'],config['nx']),
                                            ('northing',config['origin_n_m'],config['spacing_n_m'],config['ny'])):
            axis = origin+np.arange(count)*spacing
            steps = np.diff(axis)
            if not np.isfinite(axis).all() or np.any(steps<=0) or np.any(np.abs(steps-spacing)>64*core.EPSILON*spacing):
                raise core.SurveyError('metadata_ineligible','predict')
            identity = sha256()
            for index in range(count):
                identity.update(f'{name}.{index}'.encode('ascii').ljust(64,b'\0'))
            axes.append(representation.write_array(output,name+'-axis','grid_axis',axis,[count],'float64','m',identity.hexdigest()))
        # Sampling-unresolved is the unchanged informational QC flag, not a
        # geometric hole. Every other support flag excludes the cell.
        exclusions = np.ascontiguousarray(masks & np.uint32(0xffffffff ^ SAMPLING_UNRESOLVED))
        exclusions.flags.writeable = False
        def plane(identifier, height):
            # Only one bounded query block; never allocate a full P*M.
            writer = io.Writer(output,identifier,role='grid_value',shape=[config['ny'],config['nx']],dtype='float64',
                               unit='nT',mask_array_id=support['array_id'])
            values = np.zeros((config['ny'],config['nx']),dtype=np.float64)
            for interval in core._chunks(cells,4096):
                indexes = np.arange(interval.start,interval.stop)
                eligible = exclusions.reshape(-1)[interval]==0
                query = _readonly(np,np.column_stack((config['origin_e_m']+(indexes[eligible]%config['nx'])*config['spacing_e_m'],
                    config['origin_n_m']+(indexes[eligible]//config['nx'])*config['spacing_n_m'],np.full(int(eligible.sum()),height))))
                block = np.zeros(interval.stop-interval.start)
                if len(query):
                    block[eligible] = predict_global(query,sources,coefficients,job_handle=job_handle)
                values.reshape(-1)[interval] = block
            for row in values:
                writer.append(b''.join(io.encoded_cell(value,'float64') for value in row))
            ref = writer.finish(grid_ids(config))
            values.flags.writeable = False
            return ref, values
        value_ref, values = plane('fitted-grid',config['plane_upward_m'])
        grids = [representation_schema.validate('SurveyGridReceipt',dict(grid_id='fitted',config=config,
            quantity='scalar_total_field_anomaly',easting_axis=axes[0],northing_axis=axes[1],
            values=value_ref,support_mask=support,role='fitted_plane'))]
        spectrum = None
        fft = dict(verdict='ineligible',reason='No positive requested height transfer',values_sha256=None,
                   maximum_direct_difference_nT=None)
        try:
            from magnetic_line_survey_transforms import continue_plane, power_spectrum
            if config['continuation_delta_m'] is not None:
                height = config['plane_upward_m']+config['continuation_delta_m']
                if not np.isfinite(height) or height <= config['plane_upward_m']:
                    raise core.SurveyError('metadata_ineligible','predict')
                cref, continued_values = plane('continued-grid',height)
                cconfig = dict(config,plane_upward_m=height,continuation_delta_m=None)
                grids.append(representation_schema.validate('SurveyGridReceipt',dict(grid_id='continued',config=cconfig,
                    quantity='scalar_total_field_anomaly',easting_axis=axes[0],northing_axis=axes[1],
                    values=cref,support_mask=support,role='continued_plane')))
                if not np.any(exclusions):
                    continued = continue_plane(values,config,exclusions,datum=config['datum'],source_free=True,job_handle=job_handle)
                    identity = sha256()
                    for value in continued['values'].reshape(-1):
                        identity.update(io.encoded_cell(value,'float64'))
                    fft = dict(verdict='eligible',reason=None,values_sha256=identity.hexdigest(),
                        maximum_direct_difference_nT=float(np.max(np.abs(continued['values']-continued_values))))
                    del continued
                else:
                    fft['reason']='Incomplete supported plane; no FFT fill/extrapolation'
                del continued_values
            if request['spectrum'] is not None:
                if not sealed['support']['spectrum_geometrically_qualified']:
                    raise core.SurveyError('metadata_ineligible','transform')
                internal = power_spectrum(values,config,request['spectrum'],exclusions,job_handle=job_handle)
                ny,nx = internal['power'].shape
                identity = base.digest(request['spectrum'])
                power = io.write_array(output,'spectrum-power','spectrum_power',internal['power'],[ny,nx],'float64','nT^2',identity)
                east = io.write_array(output,'spectrum-east','spectrum_axis',internal['east_axis'],[nx],'float64',
                    request['spectrum']['axis_unit'],identity)
                north = io.write_array(output,'spectrum-north','spectrum_axis',internal['north_axis'],[ny],'float64',
                    request['spectrum']['axis_unit'],identity)
                sectors = io.write_table(output,'sector-power','sector_power',internal['sectors']) if internal['sectors'] else None
                spectrum = schema.validate('SurveySpectrumReceipt',dict(config=request['spectrum'],power=power,
                    east_axis=east,north_axis=north,window_mean_square=internal['window_mean_square'],
                    mean_removed_nT=internal['mean_removed_nT'],parseval_sum_nT2=internal['parseval_sum_nT2'],sectors=sectors,microlevel=None))
            result = dict(schema='m03-physical-grid-workflow/1',original=seal['original'],geometry_sha256=base.digest(seal),
                request_sha256=base.digest(request),fit_sha256=base.digest(fitted),grid=grids,spectrum=spectrum,
                continuation_method='direct_equivalent_source_prediction',fft_continuation=fft,
                field_acceptance='unresolved',full_result='not_assembled')
            core._write_member(output,'grid-workflow.json',base.canonical_bytes(result))
            return result
        except core.SurveyError as error:
            core._write_member(output,'grid-failure.json',base.canonical_bytes(dict(schema='m03-physical-grid-failure/1',
                original=seal['original'],geometry_sha256=base.digest(seal),request_sha256=base.digest(request),
                fit_sha256=base.digest(fitted),completed_grid=grids,error=error.error,field_acceptance='unresolved')))
            raise
