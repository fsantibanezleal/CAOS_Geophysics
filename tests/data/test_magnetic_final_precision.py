"""Analytical observer algebra only, no claimed full528/nonzero acceptance."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import eye

spec = importlib.util.spec_from_file_location('final_precision', Path(__file__).parents[1]/'fixtures/magnetic_survey/final_precision.py')
precision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(precision)


@pytest.mark.parametrize('covariance', [False, True])
def test_exact_stationarity_and_physical_units(covariance):
    kernel = np.array([[1., 2.], [3., -1.], [1., -1.]])
    reference = np.array([1., 2.])
    noise = dict(kind='full_covariance' if covariance else 'diagonal_sd',
        values=np.array([[2., .1, 0.], [.1, 3., .2], [0., .2, 1.]]) if covariance else np.array([.5, 1., 2.]))
    terms = [dict(alpha=1., weights=np.array([.7, .9]), derivative=eye(2, format='csr'))]
    result = precision.compare_final(kernel, kernel@reference, noise, terms, np.array([.4, .6]),
        reference, np.zeros(2), np.full(2, 10.), reference.copy(), np.array([.2, .4]), .3, .001)
    assert result['normalized_kkt_inf'] == 0.
    assert result['model_inf_q'] <= 1e-12 and result['prediction_rms_nT'] <= 1e-12
    assert result['objective_relative'] <= 1e-24


def test_true_p1_normalization_is_stage_entry_not_surrogate_or_candidate():
    kernel = np.array([[2.]])
    terms = [dict(alpha=1., weights=np.array([1.]), derivative=eye(1, format='csr'))]
    result = precision.compare_final(kernel, np.array([1.]), dict(kind='diagonal_sd', values=np.array([.5])),
        terms, np.ones(1), np.zeros(1), np.zeros(1), np.full(1, 10.), np.array([.4]), np.array([.2]), .3, .1)
    gradient = lambda q: 32*q-16+.6*q/np.sqrt(q*q+.01)
    assert result['normalized_kkt_inf'] == pytest.approx(abs(gradient(.4))/abs(gradient(.2)))
    assert result['normalized_kkt_inf'] > 1e-7  # a finite candidate is NOT qualified


def test_exact_active_sign_not_near_bound_projection():
    terms = [dict(alpha=1., weights=np.ones(1), derivative=eye(1, format='csr'))]
    args = (np.ones((1, 1)), np.array([-1.]), dict(kind='diagonal_sd', values=np.ones(1)),
        terms, np.ones(1), np.zeros(1), np.zeros(1), np.full(1, 10.))
    assert precision.compare_final(*args, np.zeros(1), np.zeros(1), .3, .1)['normalized_kkt_inf'] == 0.
    assert precision.compare_final(*args, np.array([1e-15]), np.zeros(1), .3, .1)['normalized_kkt_inf'] > .9
