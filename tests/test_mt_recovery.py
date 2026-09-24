"""Independent MT recovery, matched objective and state-identity gates (CPU only)."""
import json

import numpy as np
import pytest
import torch

from electromagnetics import (
    MU, MT_BOUNDS, bootstrap_mt, calibrate_mt_bootstrap, identifiability,
    impedance, invert_mt, objective_residual, torch_objective,
)


def oracle_halfspace(rho, frequency):
    """Independent closed form; does not call the implementation under test."""
    return (1+1j)*np.sqrt(np.pi*np.asarray(frequency)*MU*rho)


def test_mt_objective_parity_with_mask_and_heteroscedastic_noise():
    f = np.geomspace(.005, 500, 29)
    h = np.array([230., 670.])
    x = np.log([250., 8., 540.])
    obs = impedance([210., 11., 490.], h, f)
    sigma = abs(obs)*np.linspace(.01, .05, len(f))
    mask = np.arange(len(f)) % 3 != 0
    beta = .23
    residual = objective_residual(x, h, f, obs, sigma, beta, mask)
    loss = torch_objective(
        torch.tensor(x), torch.tensor(h), torch.tensor(f), torch.tensor(obs),
        torch.tensor(sigma), beta, torch.tensor(mask))
    r = (impedance(np.exp(x), h, f)[mask]-obs[mask])/sigma[mask]
    expected = (np.sum(r.real**2)+np.sum(r.imag**2))/(2*mask.sum()) + beta*np.mean(np.diff(x)**2)
    assert float(loss) == pytest.approx(expected, rel=1e-12)
    assert np.sum(residual**2) == pytest.approx(expected, rel=1e-12)


@pytest.fixture(scope="module")
def halfspace_fits():
    f = np.geomspace(.01, 100, 24)
    obs = oracle_halfspace(240., f)
    sigma = abs(obs)*.02
    return f, obs, sigma, invert_mt([], f, obs, sigma, seed=72001, adam_steps=400, neural_steps=600, record_every=13)


def test_all_solvers_recover_independent_known_halfspace(halfspace_fits):
    _, _, _, fits = halfspace_fits
    for result in fits.values():
        assert result["device"] == "cpu"
        assert result["model"][0] == pytest.approx(240, rel=2e-4)
        assert result["metrics"]["active_component_wrms"] < .003
        assert result["solver"]["bounds_ohm_m"] == list(MT_BOUNDS)
        assert result["solver"]["initial_model"] == [100.]
        assert result["target"]["units"] == "ohm m"


def test_saved_states_losses_predictions_and_final_identity(halfspace_fits):
    f, obs, sigma, fits = halfspace_fits
    for method in fits.values():
        assert method["model"] == method["frames"][-1]
        assert len(method["frames"]) == len(method["history"]) == len(method["states"])
        for model, value, state in zip(method["frames"], method["history"], method["states"]):
            actual = np.sum(objective_residual(np.log(model), [], f, obs, sigma, .001)**2)
            assert value == pytest.approx(actual, rel=1e-12, abs=1e-15)
            assert value == state["objective"]["total"]
            assert MT_BOUNDS[0] <= min(model) <= max(model) <= MT_BOUNDS[1]
        prediction = impedance(method["model"], [], f)
        np.testing.assert_array_equal(prediction.real, method["predicted"]["real"])
        np.testing.assert_array_equal(prediction.imag, method["predicted"]["imag"])
        np.testing.assert_array_equal((obs-prediction).real, method["residual"]["real"])
        assert method["states"][-1]["kind"] == "selected_final"
        assert method["state_identity"]["final_frame_index"] == len(method["frames"])-1
        assert method["state_identity"]["predictions"] == "final-model"
        assert method["state_identity"]["selected_iteration"] == method["states"][-1]["step"]
        json.dumps(method, allow_nan=False)


def test_post_update_alias_regression_multilayer():
    f = np.geomspace(.01, 100, 20)
    h = [200, 400]
    obs = impedance([350., 18., 650.], h, f)
    sigma = abs(obs)*.025
    fits = invert_mt(h, f, obs, sigma, methods=("mt-adam", "mt-neural"), adam_steps=17,
                    neural_steps=17, record_every=1, beta=.2)
    for result in fits.values():
        for model, loss in zip(result["frames"], result["history"]):
            expected = np.sum(objective_residual(np.log(model), h, f, obs, sigma, .2)**2)
            assert loss == pytest.approx(expected, rel=1e-12)
        assert result["history"][-1] <= min(result["history"][:-1])+1e-12


def test_multilayer_known_recovery_and_withheld_frequency_metrics():
    # Independent two-layer reflection coefficient, not the tanh recursion.
    f = np.geomspace(.001, 1000, 40)
    rho, h = np.array([120., 12.]), [350.]
    w = oracle_halfspace(rho[0], f)
    bottom = oracle_halfspace(rho[1], f)
    k = (1+1j)*np.sqrt(np.pi*f*MU/rho[0])
    reflection = (bottom-w)/(bottom+w)*np.exp(-2*k*h[0])
    obs = w*(1+reflection)/(1-reflection)
    mask = np.arange(len(f)) % 2 == 0
    result = invert_mt(h, f, obs, abs(obs)*.02, active=mask, beta=0, methods=("mt-lm",))["mt-lm"]
    np.testing.assert_allclose(result["model"], rho, rtol=1e-7)
    assert result["metrics"]["withheld_component_wrms"] < 1e-6
    np.testing.assert_allclose(impedance(rho, h, f), obs, rtol=1e-12)


def test_weak_deep_layer_and_bounds_are_not_claimed_resolved():
    f = np.geomspace(10, 100, 16)
    model, h = [100., 200., 500.], [20000., 30000.]
    z = impedance(model, h, f)
    diagnostics = identifiability(model, h, f, abs(z)*.03, np.ones(len(f), bool))
    assert diagnostics["status"] == "unresolved"
    assert diagnostics["effective_rank"] < 3
    assert 2 in diagnostics["unresolved_layers"]
    f = np.geomspace(.01, 100, 20)
    obs = oracle_halfspace(10000., f)
    result = invert_mt([], f, obs, abs(obs)*.025, methods=("mt-lm",))["mt-lm"]
    assert result["identifiability"]["near_bound"] == [True]
    assert result["evaluation"]["status"] == "failed"
    assert result["model"][0] <= MT_BOUNDS[1]
    ensemble = bootstrap_mt([MT_BOUNDS[1]], [], f, abs(obs)*.025, samples=20)
    assert ensemble["members"] == 20
    assert max(row[0] for row in ensemble["samples"]) <= MT_BOUNDS[1]


def test_seed_is_reproducible_and_does_not_mutate_global_rng():
    f = np.geomspace(.01, 100, 12)
    obs = oracle_halfspace(300., f)
    before = torch.random.get_rng_state().clone()
    first = invert_mt([], f, obs, abs(obs)*.03, methods=("mt-neural",), neural_steps=12, seed=123)
    assert torch.equal(before, torch.random.get_rng_state())
    second = invert_mt([], f, obs, abs(obs)*.03, methods=("mt-neural",), neural_steps=12, seed=123)
    assert first["mt-neural"]["model"] == second["mt-neural"]["model"]


@pytest.mark.parametrize("change", [
    {"sigma": [0, .1]}, {"sigma": [np.nan, .1]}, {"frequencies": [1, 1]},
    {"frequencies": [-1, 2]}, {"active": [False, False]}, {"active": [1, 0]},
    {"initial": [0]}, {"beta": -1}, {"bounds": (100, 1)}, {"observed": [complex(np.nan, 0), 1]},
])
def test_invalid_sounding_fails_closed(change):
    args = dict(thickness=[], frequencies=[1, 2], observed=[.1+.1j, .2+.2j], sigma=[.01, .02], methods=("mt-lm",))
    args.update(change)
    with pytest.raises(ValueError):
        invert_mt(**args)


def test_conditional_bootstrap_reproducibility_and_analytic_scale():
    f = np.geomspace(.01, 100, 16)
    sigma = abs(oracle_halfspace(170., f))*.04
    one = bootstrap_mt([170.], [], f, sigma, beta=0, samples=128, seed=88101)
    two = bootstrap_mt([170.], [], f, sigma, beta=0, samples=128, seed=88101)
    assert one == two
    assert one["kind"] == "conditional-parametric-bootstrap"
    assert one["members"] == 128 and not one["failures"]
    assert "coverage" not in one  # Never invent field coverage from one conditional ensemble.
    assert one["lower"][0] < 170 < one["upper"][0]
    analytic_sd = 2*170*.04/np.sqrt(len(f))
    assert one["std"][0] == pytest.approx(analytic_sd, rel=.25)
    assert one["mean"][0] == pytest.approx(170, rel=.015)
    assert len(set(one["sample_seeds"])) == one["members"]
    json.dumps(one, allow_nan=False)


def test_independently_seeded_halfspace_coverage_experiment():
    f = np.geomspace(.01, 100, 12)
    rho = 230.
    sigma = abs(oracle_halfspace(rho, f))*.05
    result = calibrate_mt_bootstrap([rho], [], f, sigma, realizations=24, samples=64, seed=88331, beta=0)
    assert result["failures"] == 0
    assert result["coverage_per_layer"][0] >= .75
    covered = [row["interval_ohm_m"][0][0] <= rho <= row["interval_ohm_m"][1][0] for row in result["rows"]]
    assert result["coverage_per_layer"][0] == np.mean(covered)
    assert all(row["noise_seed"] != row["bootstrap_seed"] for row in result["rows"])
    assert len({row["noise_seed"] for row in result["rows"]}) == 24
    assert result["mean_width_ohm_m"][0] > 0
    assert result["coverage_wilson95_lower"][0] < result["coverage_per_layer"][0]
    assert result["coverage_wilson95_upper"][0] > result["coverage_per_layer"][0]
    json.dumps(result, allow_nan=False)


def test_failed_bootstrap_members_are_retained_and_not_false_intervals(monkeypatch):
    import electromagnetics
    def failure(*args, **kwargs):
        raise RuntimeError("deliberate failure test")
    monkeypatch.setattr(electromagnetics, "_trf_only", failure)
    f = np.geomspace(.01, 100, 10)
    result = bootstrap_mt([170.], [], f, abs(oracle_halfspace(170., f))*.04, samples=20)
    assert result["status"] == "incomplete" and result["members"] == 0
    assert len(result["failures"]) == 20
    assert result["lower"] == result["upper"] == []
    assert result["interval_ohm_m"] is None
    json.dumps(result, allow_nan=False)
