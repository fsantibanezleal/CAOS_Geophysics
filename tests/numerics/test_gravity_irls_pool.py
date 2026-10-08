"""Whole-cap lossless actual scientific ledger transport, not hash-only replay."""
from copy import deepcopy
from time import monotonic

import numpy as np
import pytest

import gravity_irls_corrected as corrected
import gravity_irls_pool as pool
import gravity_workflow_io as transport
from test_gravity_irls import native_problem, policy


@pytest.fixture(scope='module')
def actual():
    problem, prior = native_problem(null=False)
    result = corrected.solve_partition(problem, prior, policy(), monotonic()+120.)
    assert result['terminal']['status'] == 'converged'
    return problem, prior, result


def test_actual_partition_lossless_physics_archive(actual):
    problem, prior, result = actual
    encoded = pool.encode(result)
    restored = pool.decode(encoded)
    assert corrected.plain.survey._digest(restored) == corrected.plain.survey._digest(result)
    corrected.validate_partition(restored, problem, prior, policy())
    # Whole encoded archive transport obeys originalZIP/depth/scalar/member caps.
    wrapper = dict(schema='gravity-corrected-partition-archive-1', partition=encoded)
    binary = transport.archive_bytes(wrapper)
    read = transport.native_from_archive(binary)
    corrected.validate_partition(pool.decode(read['partition']), problem, prior, policy())


@pytest.mark.parametrize('dtype', [np.float64, np.int64, np.bool_])
def test_original_shapes_and_zero_arrays(dtype):
    original = dict(a=np.arange(12).astype(dtype).reshape(3, 4), b=np.empty((0, 2), dtype=dtype),
                    c=np.zeros(3, dtype=dtype), d=(None, True, 7, .13, 'upward'))
    restored = pool.decode(pool.encode(original))
    assert corrected.plain.survey._digest(restored) == corrected.plain.survey._digest(original)
    assert not restored['a'].flags.writeable


@pytest.mark.parametrize('fault', ['cycle', 'count', 'padding', 'extra', 'dtype', 'alias'])
def test_rehashed_pool_refuses(actual, fault):
    encoded = deepcopy(pool.encode(actual[2]))
    if fault == 'cycle':
        encoded['edges'].flat[encoded['edge_count']-1] = encoded['node_count']-1
    elif fault == 'count':
        encoded['float_count'] += 1
    elif fault == 'padding':
        candidate = next(v for v, count in [(encoded['nodes'], 6*encoded['node_count']),
            (encoded['edges'], encoded['edge_count']), (encoded['floats'], encoded['float_count'])] if v.size > count)
        candidate.flat[-1] = 1
    elif fault == 'extra':
        encoded['ignored'] = 'cannot hide extra data'
    elif fault == 'dtype':
        encoded['nodes'] = encoded['nodes'].astype(np.float64)
    elif fault == 'alias':
        encoded['edges'].flat[encoded['edge_count']-1] = encoded['edges'].flat[encoded['edge_count']-3]
    encoded['pool_sha256'] = corrected.plain.survey._digest({k:v for k,v in encoded.items() if k != 'pool_sha256'})
    with pytest.raises((ValueError, TypeError)):
        pool.decode(encoded)


def test_complete_native_cap_before_scan(monkeypatch):
    encoded = pool.encode(dict(a=np.zeros(2)))
    encoded['floats'] = np.zeros((4097, 1))
    monkeypatch.setattr(pool.survey, '_finite', lambda *args: pytest.fail('scan before whole shape guard'))
    with pytest.raises(ValueError):
        pool.decode(encoded)
