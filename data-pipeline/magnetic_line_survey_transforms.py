"""Frozen physical FFT formulas under the separately bounded full-survey schema.

No filling, downward continuation, spectral inference of field truth or role
alias for the pending dimensionless microlevel transfer. Native entry requires
actual owner containment; ordinary bounded-transform code/caps stay unchanged.
"""
from __future__ import annotations

import math

import magnetic_line_survey as core
import magnetic_line_survey_contract as schema


def _grid(values, config, masks, job_handle):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    config = schema.validate('SurveyGrid', config)
    np, _ = core.engines()
    shape = (config['ny'], config['nx'])
    core._array(np, values, shape)
    core._finite(np, values)
    if type(masks) not in (np.ndarray, np.memmap) or masks.dtype != np.dtype('<u4') or \
       masks.shape != shape or masks.flags.writeable or not masks.flags.c_contiguous:
        raise core.SurveyError('invalid_contract', 'transform')
    cells = math.prod(shape)
    boundary = config['boundary_policy']
    pe, pn = boundary['pad_e_cells'], boundary['pad_n_cells']
    if boundary['mode']=='periodic' and (pe or pn or boundary['detrend']!='none' or boundary['taper']!='none'):
        raise core.SurveyError('invalid_contract', 'transform')
    if cells > 1048576 or pe*2 > config['nx'] or pn*2 > config['ny']:
        raise core.SurveyError('resource_refused', 'transform')
    fft_cells = (shape[0]+2*pn)*(shape[1]+2*pe)
    # Independent phase allocation check before allocating native FFT work.
    core.allocation_bounds(1, 1, cells, core._count(fft_cells, 0, 4194304))
    for origin, spacing, count in ((config['origin_e_m'], config['spacing_e_m'], config['nx']),
                                    (config['origin_n_m'], config['spacing_n_m'], config['ny'])):
        with np.errstate(over='ignore', invalid='ignore'):
            axis = origin+np.arange(count)*spacing
            steps = np.diff(axis)
        if not np.isfinite(axis).all() or np.any(steps<=0) or np.any(np.abs(steps-spacing)>64*core.EPSILON*spacing):
            raise core.SurveyError('metadata_ineligible', 'transform')
    return np, config


def _real_inverse(np, coefficients):
    output = np.fft.ifft2(coefficients)
    scale = max(1., float(np.max(np.abs(output.real))))
    if not np.isfinite(output).all() or float(np.max(np.abs(output.imag))) > 1024*core.EPSILON*scale:
        raise core.SurveyError('nonconverged', 'transform')
    return output.real


def continue_plane(values, config, masks, *, datum, source_free, job_handle):
    """Same declared-boundary exp(-|k|*positive_delta) as the original oracle."""
    np, config = _grid(values, config, masks, job_handle)
    if type(datum) is not str or datum != config['datum'] or source_free is not True or np.any(masks):
        raise core.SurveyError('metadata_ineligible', 'transform')
    delta = config['continuation_delta_m']
    if delta is None or not math.isfinite(config['plane_upward_m']+delta) or \
       config['plane_upward_m']+delta <= config['plane_upward_m']:
        raise core.SurveyError('metadata_ineligible', 'transform')
    if 2*values.size > 1048576:
        raise core.SurveyError('resource_refused', 'transform')
    boundary = config['boundary_policy']
    pe, pn = boundary['pad_e_cells'], boundary['pad_n_cells']
    from threadpoolctl import threadpool_limits
    try:
        with threadpool_limits(limits=1), np.errstate(over='raise', invalid='raise', divide='raise'):
            mean = float(np.mean(values)) if boundary['detrend']=='remove_mean' else 0.
            work = values-mean
            if boundary['taper']=='hann':
                work = work*np.hanning(config['ny'])[:,None]*np.hanning(config['nx'])[None,:]
            if pe or pn:
                work = np.pad(work, ((pn,pn),(pe,pe)), mode='constant' if boundary['mode']=='zero_pad' else 'reflect')
            ke = 2*np.pi*np.fft.fftfreq(work.shape[1], config['spacing_e_m'])
            kn = 2*np.pi*np.fft.fftfreq(work.shape[0], config['spacing_n_m'])
            transfer = np.exp(-np.hypot(kn[:,None], ke[None,:])*delta)
            transformed = _real_inverse(np, np.fft.fft2(work)*transfer)
            result = np.ascontiguousarray(transformed[pn:pn+config['ny'], pe:pe+config['nx']]+mean)
    except (FloatingPointError, OverflowError):
        raise core.SurveyError('nonconverged', 'transform') from None
    core._finite(np, result)
    result.flags.writeable = False
    return dict(values=result, plane_upward_m=config['plane_upward_m']+delta,
                boundary_policy=dict(boundary), mean_removed_nT=mean,
                domain_interpretation='declared_complete_source_free_plane_not_provider_authentication')


def power_spectrum(values, grid_config, spectrum_config, masks, *, job_handle):
    """Complete rectangle, two-sided window-normalized bin power, no hole fill."""
    np, grid = _grid(values, grid_config, masks, job_handle)
    config = schema.validate('SurveySpectrum', spectrum_config)
    rectangle = config['rectangle']
    e, n, nx, ny = (rectangle[key] for key in ('e_start','n_start','nx','ny'))
    if e+nx > grid['nx'] or n+ny > grid['ny'] or nx*ny > 1048576 or np.any(masks[n:n+ny,e:e+nx]):
        raise core.SurveyError('metadata_ineligible', 'transform')
    from threadpoolctl import threadpool_limits
    try:
        with threadpool_limits(limits=1), np.errstate(over='raise', invalid='raise', divide='raise'):
            crop = values[n:n+ny,e:e+nx]
            window = np.ones((ny,nx)) if config['window']=='rectangular' else np.hanning(ny)[:,None]*np.hanning(nx)[None,:]
            c2 = float(np.mean(window*window))
            if c2 <= 0:
                raise core.SurveyError('metadata_ineligible', 'transform')
            mean = float(np.mean(crop))
            work = window*(crop-mean)
            coefficients = np.fft.fft2(work)
            power = np.abs(coefficients)**2/(nx*ny)**2/c2
            expected = float(np.mean(work*work)/c2)
            actual = float(power.sum())
            if not math.isfinite(expected) or not math.isfinite(actual) or \
               abs(actual-expected) > 1e-10*max(expected, actual, 1e-12):
                raise core.SurveyError('nonconverged', 'transform')
            fe, fn = np.fft.fftfreq(nx, grid['spacing_e_m']), np.fft.fftfreq(ny, grid['spacing_n_m'])
            azimuth = np.degrees(np.arctan2(fe[None,:],fn[:,None]))%360
            nonzero = (fe[None,:]!=0)|(fn[:,None]!=0)
            sectors = []
            for sector in config['direction_sectors']:
                selected = nonzero & (azimuth>=sector['azimuth_start_deg']) & (azimuth<sector['azimuth_end_deg'])
                sectors.append(dict(sector_id=sector['sector_id'], bin_count=int(selected.sum()), power_nT2=float(power[selected].sum())))
            multiplier = 2*np.pi if config['axis_unit']=='rad_per_m' else 1.
            east, north = fe*multiplier, fn*multiplier
    except (FloatingPointError, OverflowError):
        raise core.SurveyError('nonconverged', 'transform') from None
    for array in (power, east, north):
        core._finite(np, array)
        array.flags.writeable = False
    return dict(config=config, power=power, east_axis=east, north_axis=north, window_mean_square=c2,
        mean_removed_nT=mean, parseval_sum_nT2=actual, windowed_mean_square_nT2=expected, sectors=sectors)
