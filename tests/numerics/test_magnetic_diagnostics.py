"""Local diagnostics independently replay their physical linear systems."""

import importlib.util
from pathlib import Path
from time import monotonic

import numpy as np
import pytest

from magnetic_diagnostics import resolution, line_spectrum
from magnetic_survey_json import InputError

spec = importlib.util.spec_from_file_location('diagnostic_control', Path(__file__).with_name('test_magnetic_optimizer_adapter.py'))
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def test_local_resolution_independent_choclo_and_physical_faces():
    physical = control.physical.__wrapped__()
    obj, kernel, _, _, r, _ = control.make(physical, 'linear_tmi_nT', False)
    # Interior reference has no bound lock; no true-model choice in diagnostic.
    result = resolution(obj, control.control.Q, deadline=monotonic()+120.)
    wk = kernel/.5
    oracle = np.linalg.solve(wk.T@wk+.3*r.T@r, wk.T@wk)
    actual = np.array(result['matrix']['data']).reshape(7, 7)
    np.testing.assert_allclose(actual, oracle, rtol=1e-10, atol=1e-8)
    np.testing.assert_allclose(result['singular_values']['data'], np.linalg.svd(np.vstack([wk, np.sqrt(.3)*r]), compute_uv=False), rtol=1e-10, atol=1e-8)
    with pytest.raises(InputError, match='deadline'):
        resolution(obj, control.control.Q, deadline=monotonic()-1.)


@pytest.mark.parametrize('n', [15, 16])
def test_horizontal_signed_spectrum_parseval_and_gap_rejection(n):
    xyz = np.column_stack([80.*np.arange(n), np.zeros(n), 120.+10*(np.arange(n)%3)]).astype(np.float64)
    residual = np.column_stack([3*np.cos(2*np.pi*np.arange(n)/n), -2*np.sin(2*np.pi*np.arange(n)/n)])
    result = line_spectrum(xyz, residual)
    assert result['status'] == 'available' and result['power_unit'] == 'nT^2*m'
    step = 1./(n*80.)
    window = np.hanning(n)
    variance = np.sum((window[:, None]*(residual-residual.mean(axis=0)))**2, axis=0)/np.sum(window**2)
    np.testing.assert_allclose(result['power'].sum(axis=0)*step, variance, rtol=1e-12, atol=1e-12)
    xyz[3, 0] += 5.
    assert line_spectrum(xyz, residual)['status'] == 'unavailable'
