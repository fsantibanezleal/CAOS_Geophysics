"""Independent exact-overlap and unchanged adverse negative controls."""

import numpy as np
import pytest

from magnetic_s2_evaluation import integrated_truth, evaluate_model, adverse_verdict


def mesh():
    return dict(origin_m=dict(data=[0.,0.,0.]), widths_x_m=dict(data=[1.,2.]),
                widths_y_m=dict(data=[2.]), widths_z_m=dict(data=[3.]), active=dict(data=[True,True]))


def test_off_grid_volume_overlap_not_center_sample():
    # Separate helper control uses binary-exact moments; frozen S2 is untouched.
    body = dict(bounds_m=[.25,1.5,.5,1.5,1.,2.], chi_si=.03125)
    result = integrated_truth(mesh(), [body])
    np.testing.assert_allclose(result['cell_chi_si'], [.0234375/6., .015625/12.], rtol=0., atol=0.)
    assert result['susceptibility_integral_si_m3'] == .0390625
    np.testing.assert_allclose(result['centroid_m'], [.875,1.,1.5], rtol=0., atol=0.)
    evaluated = evaluate_model(mesh(), [body], result['cell_chi_si'])
    assert evaluated['integral_error_si_m3'] == 0. and evaluated['volume_weighted_chi_rms_si'] == 0.
    # Cell-center inverse moment is distinct from exact body's centroid.
    assert evaluated['centroid_error_m'] > 0.
    assert evaluated['field_model_truth'] is None and not evaluated['geological_truth_claimed']


def test_null_has_no_fabricated_centroid_or_concentration():
    result = evaluate_model(mesh(), [], np.zeros(2))
    assert result['truth_centroid_m'] is None and result['fitted_centroid_m'] is None
    assert result['cell_weight_concentration'] is None and result['centroid_error_m'] is None


@pytest.mark.parametrize('a,b,verdict', [(1.3,1.,'adverse_degradation_demonstrated'),
    (1.1,1.,'unresolved_unable_to_discriminate'), (None,1.,'unresolved_unable_to_evaluate'),
    (1.,0.,'unresolved_unable_to_discriminate')])
def test_original_adverse_degradation_or_unresolved(a,b,verdict):
    assert adverse_verdict(a,b)['verdict'] == verdict
