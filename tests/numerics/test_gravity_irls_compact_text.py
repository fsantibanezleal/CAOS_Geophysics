"""Lossless text representation only, not a scientific fixture or solver gate."""
from copy import deepcopy

import numpy as np
import pytest

import gravity_irls_pool as pool
import gravity_l2 as l2
import gravity_survey_l2 as survey


def value():
    return {'audit': tuple(f'{i:04d}.'+'1234567890'*9 for i in range(200)),
        'text': ('station:á', '上', '', 'repeat', 'repeat'),
        'array': np.array([np.nextafter(1., 2.), -0., 1e-300]),
        'flags': (None, False, 1, 1.)}


def test_exact_text_float_bits_and_unchanged_complete_caps():
    original = value()
    old, compact = pool.encode(original), pool.encode_compact(original)
    assert old['schema'] == 'gravity-irls-typed-pool-1'
    assert compact['schema'] == 'gravity-irls-typed-pool-2'
    restored = pool.decode(compact)
    assert restored['audit'] == original['audit'] and restored['text'] == original['text']
    np.testing.assert_array_equal(restored['array'].view(np.uint64), original['array'].view(np.uint64))
    assert restored['flags'] == original['flags'] and pool.decode(old)['audit'] == original['audit']
    with pytest.raises(ValueError, match='complete native'):
        l2._result_native_metadata({'fits': tuple(deepcopy(old) for _ in range(25))})
    complete = {'fits': tuple(deepcopy(compact) for _ in range(25))}
    l2._result_native_metadata(complete)
    assert sum(f['strings']['bytes'].nbytes for f in complete['fits']) < 256*1024**2
    for fitted in complete['fits']:
        assert pool.decode(fitted)['audit'] == original['audit']


@pytest.mark.parametrize('fault', ('byte', 'utf8', 'offset', 'padding', 'count', 'dtype', 'raw_hash', 'unused_text'))
def test_rehashed_compact_denials(fault):
    bad = deepcopy(pool.encode_compact(value()))
    text = bad['strings']
    if fault == 'byte': text['bytes'].flat[0] = 256
    if fault == 'utf8': text['bytes'].flat[0] = 255
    if fault == 'offset': text['offsets'].flat[0] = 1
    if fault == 'padding': text['bytes'].flat[-1] = 1
    if fault == 'count': text['count'] += 1
    if fault == 'dtype': text['bytes'] = text['bytes'].astype(np.int32)
    if fault == 'raw_hash': bad['raw_sha256'] = 'f'*64
    if fault == 'unused_text': text['offsets'].flat[1] = 0
    bad['pool_sha256'] = survey._digest({k:v for k,v in bad.items() if k != 'pool_sha256'})
    with pytest.raises((ValueError, TypeError)):
        pool.decode(bad)
