"""Native free/active max guards; existing INTERIOR branch assertions untouched."""
import numpy as np
import pytest

import gravity_irls_face as face


def operands():
    return (np.array([-1., 1., .2, -.1]), np.zeros(4),
        np.array([2., -3., .1, -.1]), np.full(4, -1.), np.ones(4))


def test_all_binding_tied_plateau_is_exact_constant_scale_not_free_tie():
    q, ref, g, lo, hi = operands()
    actual = face._classify(q, ref, g, lo, hi)
    assert actual['branch'] == 'native_binding_max_constant_scale'
    assert actual['constant_scale'] and actual['derivative_supported']
    np.testing.assert_array_equal(actual['binding'], [True, True, False, False])
    np.testing.assert_array_equal(actual['maxima'], [0, 1])
    assert actual['free_scale_gap'] == .8
    assert actual['maximum_index'] is None
    assert not actual['binding'].flags.writeable and not actual['free'].flags.writeable
    # The earlier approved policy still refuses ALL ties; no old test changed.
    assert face.interior._branch(q, ref, lo, hi) == ('disabled_tied_max', None)


@pytest.mark.parametrize('coordinate', [0, 1])
def test_inward_gradient_at_max_bound_is_not_frozen(coordinate):
    q, ref, g, lo, hi = operands()
    g[coordinate] *= -1.
    actual = face._classify(q, ref, g, lo, hi)
    assert not actual['binding'][coordinate]
    assert actual['branch'] == 'disabled_free_tied_max'
    assert not actual['derivative_supported'] and not actual['constant_scale']


@pytest.mark.parametrize('sign', [-1., 1.])
@pytest.mark.parametrize('offset', [-.125, .25])
def test_unique_binding_and_free_max_with_original_signed_reference(sign, offset):
    q = sign*np.array([1., .2, -.1, .05])+offset
    ref = np.full(4, offset)
    lo, hi = np.full(4, offset-1.), np.full(4, offset+1.)
    g = np.array([-sign*2., .1, -.1, .1])
    actual = face._classify(q, ref, g, lo, hi)
    assert actual['branch'] == 'native_binding_max_constant_scale'
    assert actual['maximum_index'] == 0 and actual['constant_scale']
    g[0] *= -1.
    actual = face._classify(q, ref, g, lo, hi)
    assert actual['branch'] == 'native_free_unique_max_rank_one'
    assert not actual['binding'][0] and not actual['constant_scale']


@pytest.mark.parametrize('kind', ['null', 'empty', 'free_tie'])
def test_unsupported_branch_disables_before_any_construction(kind):
    q, ref, g, lo, hi = operands()
    if kind == 'null':
        q[:] = 0.
    elif kind == 'empty':
        q[2:] = [-1., 1.]
        g[2:] = [1., -1.]
    else:
        q[:] = [.3, -.3, .2, -.1]
    actual = face._classify(q, ref, g, lo, hi)
    assert actual['branch'] == {'null':'disabled_null', 'empty':'disabled_empty_free_face',
        'free_tie':'disabled_free_tied_max'}[kind]
    assert not actual['derivative_supported']


@pytest.mark.parametrize('kind', ['active_sign', 'active_move', 'free_to_plateau', 'bound_cross', 'no_move'])
def test_trial_sign_feasibility_plateau_and_active_coordinates(kind):
    q, ref, g, lo, hi = operands()
    original = face._classify(q, ref, g, lo, hi)
    qt, gt = q.copy(), g.copy()
    qt[2] += .01
    if kind == 'active_sign':
        gt[0] = -1.
    elif kind == 'active_move':
        qt[0] = np.nextafter(qt[0], 0.)
    elif kind == 'free_to_plateau':
        qt[2] = 1.
        gt[2] = -1.
    elif kind == 'bound_cross':
        qt[2] = np.nextafter(1., np.inf)
    else:
        qt = q.copy()
    assert not face._same_face_trial(q, qt, gt, ref, lo, hi, original)
    assert face._same_face_trial(q, np.array([-1., 1., .21, -.1]), g, ref, lo, hi, original)


def test_bad_native_source_and_impossible_box_refused(monkeypatch):
    q, ref, g, lo, hi = operands()
    with pytest.raises(ValueError, match='feasible box'):
        face._classify(q, ref, g, np.zeros(4), hi)
    monkeypatch.setattr(face, 'VENDOR_SHA256', '0'*64)
    with pytest.raises(ValueError, match='binding source drift'):
        face._classify(q, ref, g, lo, hi)
