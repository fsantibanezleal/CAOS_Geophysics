"""Independent bounded dense controls BEFORE the actual failed candidate."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'data-pipeline'))
import magnetic_line_survey as core
import magnetic_line_survey_hp as hp
import magnetic_line_survey_capacity_hp as capacity


def dense_case(weighted):
    np, _ = core.engines()
    xyz = np.array([[0., 0., 10.], [5., 0., 12.], [1., 7., 10.], [9., 8., 14.], [4., 3., 11.], [7., 2., 10.]])
    sources = np.array([[1., 1., -20.], [8., 6., -20.], [-5., 3., -20.]])
    sigma = np.array([1., 2., .5, 3., 1.2, .7]) if weighted else None
    y = np.array([2., -1., 3., .5, 2.5, -2.])
    for item in (xyz, sources, sigma, y):
        if item is not None: item.flags.writeable = False
    # Independent NumPy construction: no production kernel/scales/P helpers.
    g = 1/np.sqrt(np.sum((xyz[:, None, :]-sources[None, :, :])**2, axis=2))
    scales = np.std(g, axis=0, ddof=0)
    a = g/scales
    if weighted: a = a/sigma[:, None]
    b = y/sigma if weighted else y
    return np, xyz, sources, sigma, y, scales, a, b


@pytest.mark.parametrize('weighted', [False, True])
def test_dense_objective_actions_adjoint_reconstruction(weighted):
    np, xyz, sources, sigma, y, scales, a, b = dense_case(weighted)
    damping = .01
    model = core.GlobalOperator(xyz, sources, sigma, chunk_rows=2, chunk_sources=2)
    augmented = hp.AugmentedOperator(model, damping)
    p = 1/np.sqrt(np.sum(a*a, axis=0)+damping)
    h = np.vstack((a, np.sqrt(damping)*np.eye(3)))
    expected = h*p
    np.testing.assert_allclose(model.scales, scales, rtol=1e-13)
    np.testing.assert_allclose(augmented.p, p, rtol=1e-13)
    z = np.array([2., -3., 4.])
    u = np.arange(9, dtype=np.float64)-3
    np.testing.assert_allclose(augmented.operator@z, expected@z, rtol=1e-13, atol=1e-13)
    np.testing.assert_allclose(augmented.operator.rmatvec(u), expected.T@u, rtol=1e-13, atol=1e-13)
    assert np.dot(u, augmented.operator@z) == pytest.approx(np.dot(z, augmented.operator.rmatvec(u)), rel=1e-13)
    rhs = np.concatenate((b, np.zeros(3)))
    c = p*z
    assert np.sum((expected@z-rhs)**2) == pytest.approx(np.sum((a@c-b)**2)+damping*np.dot(c, c), rel=1e-13)
    # Negative control: AP with scalar damping penalizes z and is NOT J(Pz).
    wrong = np.sum((a@c-b)**2)+damping*np.dot(z, z)
    assert abs(wrong-np.sum((expected@z-rhs)**2)) > .1
    fresh = core.GlobalOperator(xyz, sources, sigma, chunk_rows=3, chunk_sources=1)
    np.testing.assert_allclose(hp.preconditioner(fresh, damping), p, rtol=1e-13)
    solved = hp.solve_hp(fresh, y, damping)
    oracle = np.linalg.lstsq(h, rhs, rcond=None)[0]
    np.testing.assert_allclose(solved['scaled_coefficients'], oracle, rtol=1e-9, atol=1e-9)
    gradient = a.T@(a@solved['scaled_coefficients']-b)+damping*solved['scaled_coefficients']
    diag = solved['receipt']['original_diagnostics']
    assert diag['stationarity_inf'] == pytest.approx(np.max(np.abs(gradient)), abs=2e-12)
    assert diag['objective'] == pytest.approx(np.sum((h@oracle-rhs)**2), rel=1e-12)
    assert solved['receipt']['condition_domain'].startswith('B=HP')
    assert solved['receipt']['scalar_lsmr_damp'] == 0


def test_actual_stop7_is_retained_and_refused(monkeypatch):
    import scipy.sparse.linalg
    np, xyz, sources, sigma, y, _, _, _ = dense_case(False)
    monkeypatch.setattr(scipy.sparse.linalg, 'lsmr', lambda *a, **k: (np.zeros(3), 7, 2000, 2., 1., 3., 4., 0.))
    model = core.GlobalOperator(xyz, sources)
    with pytest.raises(core.SurveyError): hp.solve_hp(model, y, .01)
    state = model.hp_failure_state
    assert state['receipt']['istop'] == 7 and state['receipt']['iterations'] == 2000
    assert state['receipt']['original_diagnostics']['stationarity_relative'] > 1e-9
    assert state['receipt']['numerical_verdict'] == 'fail'
    assert state['receipt']['coefficients_sha256'] == hp.content_sha256(state['coefficients'])


def test_zero_objective_and_invalid_damping():
    np, xyz, sources, _, _, _, _, _ = dense_case(False)
    y = np.zeros(6); y.flags.writeable = False
    solved = hp.solve_hp(core.GlobalOperator(xyz, sources), y, 1.)
    assert solved['receipt']['istop'] == 0
    assert solved['receipt']['original_diagnostics']['objective'] == 0
    for wrong in (True, 0., -1., float('nan'), float('inf')):
        with pytest.raises(core.SurveyError): hp.AugmentedOperator(core.GlobalOperator(xyz, sources), wrong)


def test_exact_increased97_proof_and_member_refusal():
    training = [294, 168, 195, 249]
    validation = [33, 66, 66, 33]
    sources = [[66, 45, 48, 57], [148, 91, 101, 127], [240, 137, 164, 203], [292, 168, 193, 247]]
    result, proof = capacity.plan_capacity(363, training, validation, sources, logical_members=125, arrays=104)
    assert proof['inner_fit_pairs']+proof['final_fit_pairs'] == 10939745040
    assert proof['additional_vector_bytes'] == 144448
    assert proof['mandatory_fit_count'] == 97 and proof['maximum_fit_count'] == 97
    assert proof['logical_members'] == 126 and proof['arrays'] == 104
    assert proof['preconditioner_table_bytes'] == 2494464
    assert proof['preconditioner_verification_pairs'] == 8192520
    assert result['profile'] == 'm03-offline-hp/1'
    with pytest.raises(core.SurveyError): capacity.plan_capacity(363, training, validation, sources, logical_members=192)


def test_selective_decoding_does_not_unpack_outer_nan():
    import struct
    from magnetic_line_survey_hp_prerequisite import selected_cells
    class EncodedCustody:
        def chunks(self, ref):
            # A semantic full-channel decoder would reject the unopened NaNs.
            yield struct.pack('<3d', 4., float('nan'), 7.)
            yield struct.pack('<2d', float('nan'), 9.)
    assert selected_cells(EncodedCustody(), {'dtype':'float64', 'shape':[5]}, [0, 2, 4]) == [4., 7., 9.]
    with pytest.raises(core.SurveyError):
        selected_cells(EncodedCustody(), {'dtype':'float64', 'shape':[5]}, [4, 0])


def test_active_monitor_absence_race_does_not_exempt_present_unsafe_file(tmp_path, monkeypatch):
    import magnetic_line_survey_runtime as runtime
    path = tmp_path/'producer-completed.bin'
    path.write_bytes(b'owned-test')
    monkeypatch.setattr(runtime.os, 'walk', lambda *a, **k: [(str(tmp_path), [], [path.name])])
    def disappeared(*a, **k):
        path.unlink()
        raise core.SurveyError('custody_mismatch', 'ingest')
    monkeypatch.setattr(runtime, 'external_path', disappeared)
    assert runtime.owned_bytes(tmp_path, allow_disappearing=True) == 0
    path.write_bytes(b'owned-test')
    def unsafe_present(*a, **k): raise core.SurveyError('custody_mismatch', 'ingest')
    monkeypatch.setattr(runtime, 'external_path', unsafe_present)
    with pytest.raises(core.SurveyError): runtime.owned_bytes(tmp_path, allow_disappearing=True)
    with pytest.raises(core.SurveyError): runtime.owned_bytes(tmp_path)
