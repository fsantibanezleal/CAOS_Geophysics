"""Real geometry seal and token-level separation attacks on supplied bytes."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from magnetic_likelihood import SealedLikelihood
from magnetic_survey_json import InputError

spec = importlib.util.spec_from_file_location('likelihood_support', Path(__file__).with_name('magnetic_survey_support.py'))
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def data():
    request = support.request()
    request['observations']['values']['data'] = (np.arange(864, dtype=float)/100.).tolist()
    support.rehash(request, 'observations/values')
    return request


def test_row_authorized_values_and_one_time_outer():
    request = data()
    reader = SealedLikelihood(support.encode(request))
    partition = reader.plan['partition']
    outer = tuple(partition['outer_rows']['data'])
    with pytest.raises(InputError, match='frozen'):
        reader.read(outer, role='outer')
    for fold, part in enumerate(partition['folds']):
        rows = tuple(part['fit_rows']['data'])
        observed, noise = reader.read(rows, role='fit', fold=fold)
        np.testing.assert_array_equal(observed, np.array(request['observations']['values']['data']).reshape(288, 3)[list(rows)])
        assert noise['values'].shape == (144, 3)
        assert not observed.flags.writeable
        with pytest.raises(InputError, match='membership'):
            reader.read(outer, role='fit', fold=fold)
    frozen_hash = reader.freeze('b00-l2', np.zeros(528))
    assert len(frozen_hash) == 64
    observed, _ = reader.read(outer, role='outer')
    assert observed.shape == (72, 3)
    with pytest.raises(InputError, match='one-time'):
        reader.read(outer, role='outer')
    with pytest.raises(InputError, match='freeze'):
        reader.freeze('b01-l2', np.zeros(528))


def test_complete_noise_errors_not_hidden_by_partitions():
    request = data()
    reader = SealedLikelihood(support.encode(request))
    outer = reader.plan['partition']['outer_rows']['data'][0]
    request['noise']['values']['data'][outer*3] = 0.
    support.rehash(request, 'noise/values')
    with pytest.raises(InputError, match='Every declared SD'):
        SealedLikelihood(support.encode(request)).validate_noise()


def test_heldout_values_change_no_fit_or_seal():
    request = data()
    first = SealedLikelihood(support.encode(request))
    for row in first.plan['partition']['outer_rows']['data']:
        for component in range(3):
            request['observations']['values']['data'][row*3+component] += 1000.
    support.rehash(request, 'observations/values')
    second = SealedLikelihood(support.encode(request))
    assert first.plan['identity']['seal_sha256'] == second.plan['identity']['seal_sha256']
    assert first.plan['identity']['observations_sha256'] != second.plan['identity']['observations_sha256']
    rows = tuple(first.plan['partition']['folds'][0]['fit_rows']['data'])
    np.testing.assert_array_equal(first.read(rows, role='fit', fold=0)[0], second.read(rows, role='fit', fold=0)[0])


def test_principal_full_covariance_and_actual_scalar_indices():
    request = data()
    request['processing']['quantity'] = request['observations']['quantity'] = 'linear_tmi_nT'
    request['processing']['background_relation'] = 'projection_of_secondary_declared'
    request['observations']['values'] = support.descriptor('float64', [288, 1], np.arange(288, dtype=float).tolist())
    support.rehash(request, 'observations/values')
    sigma = .5+.001*np.arange(288)
    covariance = sigma[:, None]*sigma[None, :]*.2**abs(np.arange(288)[:, None]-np.arange(288))
    request['noise']['kind'] = 'full_covariance'
    request['noise']['unit'] = 'nT^2'
    request['noise']['values'] = support.descriptor('float64', [288, 288], covariance.ravel().tolist())
    reader = SealedLikelihood(support.encode(request))
    reader.validate_noise()
    rows = tuple(reader.plan['partition']['folds'][0]['validation_rows']['data'])
    observed, noise = reader.read(rows, role='validation', fold=0)
    np.testing.assert_array_equal(noise['values'], covariance[np.ix_(rows, rows)])
    np.testing.assert_array_equal(observed.ravel(), np.array(rows))
