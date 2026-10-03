"""Local course oracles; never writes canonical data or changes scientific sources."""
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from edi import EDIError, read_edi, screen_edi, invert_edi  # noqa: E402
from electromagnetics import bootstrap_mt, impedance, invert_mt, objective_residual  # noqa: E402

FIXTURE = ROOT / "data/fixtures/edi/two-layer-noisy-rotated.edi"
WORKED = ROOT / "frontend/src/data/online-mt-worked.json"
MU0 = 4 * np.pi * 1e-7


def reflection(rho, h, f):
    """Independent two-layer reflection expression, no tanh or production forward call."""
    w = (1 + 1j) * np.sqrt(np.pi * np.asarray(f) * MU0 * rho[0])
    if len(rho) == 1:
        return w
    basement = (1 + 1j) * np.sqrt(np.pi * np.asarray(f) * MU0 * rho[1])
    k = (1 + 1j) * np.sqrt(np.pi * np.asarray(f) * MU0 / rho[0])
    q = (basement - w) / (basement + w) * np.exp(-2 * k * h[0])
    return w * (1 + q) / (1 - q)


def objective(model, h, f, obs, sigma, mask, beta):
    diff = (reflection(model, h, f) - obs) / sigma
    data = float(np.mean(abs(diff[mask]) ** 2) / 2)
    prior = float(beta * np.mean(np.diff(np.log(model)) ** 2)) if len(model) > 1 else 0.0
    return data + prior, data, prior


def worked_case():
    sounding = read_edi(FIXTURE)
    f, (obs, sigma) = sounding.frequencies, sounding.select("xy")
    mask = np.arange(len(f)) % 5 != 4
    cases = []
    for name, h, beta in [("fixed", [350.0], .001), ("thin", [280.0], .001),
                          ("thick", [420.0], .001), ("halfspace", [], .001),
                          ("beta", [350.0], .01)]:
        starts = [[100.] * (len(h) + 1), [30.] * (len(h) + 1), [1000.] * (len(h) + 1)]
        if name != "fixed":
            # The actual online controls reuse the winning main start; they do
            # not perform a second three-start selection or tune on holdout.
            starts = [[100.]] if name == "halfspace" else [cases[0]["selected_start"]]
        trials = [invert_mt(h, f, obs, sigma, active=mask, initial=start, beta=beta,
                           methods=("mt-lm",))["mt-lm"] for start in starts]
        selected = min((i for i, fit in enumerate(trials) if fit["solver"]["success"]),
                       key=lambda i: trials[i]["metrics"]["objective"])
        fit = trials[selected]
        z = reflection(fit["model"], h, f)
        total, data, prior = objective(fit["model"], h, f, obs, sigma, mask, beta)
        cases.append(dict(id=name, thickness_m=h, beta=beta, model_ohm_m=fit["model"],
                          selected_start=starts[selected], training_objective=total,
                          data_objective=data, prior_objective=prior,
                          training_wrms=float(np.sqrt(data)),
                          heldout_wrms=float(np.sqrt(np.mean(abs((z[~mask]-obs[~mask])/sigma[~mask])**2)/2)),
                          predicted_real_ohm=z.real.tolist(), predicted_imag_ohm=z.imag.tolist(),
                          trial_objectives=[item["metrics"]["objective"] for item in trials]))
    return dict(schema="geophysics.mt-course-worked/v1", synthetic=True,
                source_sha256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), source_bytes=FIXTURE.stat().st_size,
                source_id="TWO_LAYER_NOISY_ROTATED", noise_seed=67201,
                evaluation_truth_ohm_m=[120., 12.], evaluation_thickness_m=[350.],
                truth_passed_to_solver=False, frame_degrees=27.,
                backend_reference="7b69404", local_base="afac8ab",
                environment={name: importlib.metadata.version(name) for name in ("numpy", "scipy", "mt-metadata")},
                executed_source_sha256={name: hashlib.sha256((ROOT / "data-pipeline" / name).read_bytes()).hexdigest()
                                        for name in ("edi.py", "electromagnetics.py")},
                scientific_function_sha256={fn.__name__: hashlib.sha256(inspect.getsource(fn).replace("\r\n", "\n").encode()).hexdigest()
                                            for fn in (read_edi, impedance, invert_mt, objective_residual, bootstrap_mt)},
                functions="read_edi, invert_mt; online frozen mask and training-only three-start rule",
                frequency_hz=f.tolist(), observed_real_ohm=obs.real.tolist(), observed_imag_ohm=obs.imag.tolist(),
                sigma_per_real_component_ohm=sigma.tolist(), training_mask=mask.tolist(), cases=cases)


@pytest.mark.parametrize("rho,h", [([100.], []), ([500.], []), ([120., 12.], [350.]), ([12., 120.], [280.]),
                                  ([1., 6000.], [2.]), ([6000., 1.], [4000.])])
def test_reflection_oracle(rho, h):
    f = np.geomspace(.001, 1000., 64)
    np.testing.assert_allclose(impedance(rho, h, f), reflection(rho, h, f), rtol=1e-11, atol=1e-15)
    if not h:
        z = reflection(rho, h, f)
        np.testing.assert_allclose(abs(z)**2 / (MU0 * 2 * np.pi * f), rho[0], rtol=1e-12)
        np.testing.assert_allclose(np.angle(z, deg=True), 45., atol=1e-12)


def test_forward_limiting_cases():
    # Mathematical forward limits, not online admission of zero/huge thickness.
    f = np.geomspace(.001, 1000., 64)
    np.testing.assert_allclose(reflection([120., 12.], [0.], f), reflection([12.], [], f), rtol=1e-12)
    np.testing.assert_allclose(impedance([120., 12.], [1e-12], f), reflection([12.], [], f), rtol=1e-12)
    with pytest.raises(ValueError, match="positive"):
        impedance([120., 12.], [0.], f)
    # More than 50 skin depths already realizes the upper-halfspace limit;
    # keep complex tanh arguments away from gratuitous floating-point overflow.
    np.testing.assert_allclose(impedance([120., 12.], [1e7], f[:4]), reflection([120.], [], f[:4]), rtol=1e-12)
    for h in ([2.], [350.], [4000.]):
        np.testing.assert_allclose(impedance([120., 120.], h, f), reflection([120.], [], f), rtol=1e-12)


def test_objective_mask_and_normalization():
    s = read_edi(FIXTURE)
    obs, sig = s.select("xy")
    mask = np.arange(len(obs)) % 5 != 4
    rho, beta = [90., 20.], .001
    residual = objective_residual(np.log(rho), [350.], s.frequencies, obs, sig, beta, mask)
    expected = objective(rho, [350.], s.frequencies, obs, sig, mask, beta)
    assert residual.shape == (2 * mask.sum() + 1,)
    assert residual @ residual == pytest.approx(expected[0], rel=1e-12)
    changed = obs.copy()
    changed[~mask] *= 100
    np.testing.assert_array_equal(residual, objective_residual(np.log(rho), [350.], s.frequencies, changed, sig, beta, mask))


def assert_function_binding(saved, actual, inverse_source):
    """Admit only the pinned offline Torch import relocation, not science drift."""
    assert saved.keys() == actual.keys()
    assert {key: value for key, value in saved.items() if key != "invert_mt"} == {
        key: value for key, value in actual.items() if key != "invert_mt"}
    assert hashlib.sha256(inverse_source.encode()).hexdigest() == actual["invert_mt"]
    if saved["invert_mt"] == actual["invert_mt"]:
        return
    assert (saved["invert_mt"], actual["invert_mt"]) == (
        "b13ecce15df4eef1374a261a50c545aa68e31c2ffcf6034a66fa0d956319726d",
        "371639c3aad2eb3251b978ee0a8cda4222f15d45a091f793717cc05aae17049d")
    offline_import = "        else:\n            import torch\n"
    assert inverse_source.count(offline_import) == 1
    restored = inverse_source.replace(offline_import, "        else:\n", 1)
    assert hashlib.sha256(restored.encode()).hexdigest() == saved["invert_mt"]


@pytest.mark.parametrize("changed", ["forward", "trf"])
def test_function_binding_rejects_scientific_changes(changed):
    saved = json.loads(WORKED.read_text(encoding="utf-8"))["scientific_function_sha256"]
    source = inspect.getsource(invert_mt).replace("\r\n", "\n")
    actual = {**saved, "invert_mt": hashlib.sha256(source.encode()).hexdigest()}
    if changed == "forward":
        actual["impedance"] = "0" * 64
    else:
        assert "max_nfev=max_nfev" in source
        source = source.replace("max_nfev=max_nfev", "max_nfev=99", 1)
        actual["invert_mt"] = hashlib.sha256(source.encode()).hexdigest()
    with pytest.raises(AssertionError):
        assert_function_binding(saved, actual, source)


def test_worked_case_replay():
    saved, actual = json.loads(WORKED.read_text(encoding="utf-8")), worked_case()
    assert saved["source_sha256"] == actual["source_sha256"] == "0d6b0fab71efe69d183445070aba1181604333f00fb6781bf6d2c9d9d2ee5e95"
    assert saved["source_bytes"] == actual["source_bytes"] == 8987
    assert_function_binding(saved["scientific_function_sha256"], actual["scientific_function_sha256"],
                            inspect.getsource(invert_mt).replace("\r\n", "\n"))
    for key in ("frequency_hz", "observed_real_ohm", "observed_imag_ohm", "sigma_per_real_component_ohm", "training_mask"):
        assert saved[key] == actual[key]
    for record, repeat in zip(saved["cases"], actual["cases"], strict=True):
        assert record["id"] == repeat["id"]
        for key, value in repeat.items():
            if key != "id":
                np.testing.assert_allclose(record[key], value, rtol=1e-7, atol=1e-9)
    fixed, thin, thick, half, beta = actual["cases"]
    assert abs(fixed["model_ohm_m"][0] / 120 - 1) < .06
    assert half["heldout_wrms"] > fixed["heldout_wrms"] * 4
    assert thick["model_ohm_m"][0] < fixed["model_ohm_m"][0] < thin["model_ohm_m"][0]
    assert thin["heldout_wrms"] < fixed["heldout_wrms"]  # Small holdout cannot establish correct thickness.
    assert beta["training_objective"] > fixed["training_objective"]


def test_reflection_oracle_and_conditional_bootstrap():
    s = read_edi(FIXTURE)
    _, sig = s.select("xy")
    mask = np.arange(len(sig)) % 5 != 4
    center = json.loads(WORKED.read_text(encoding="utf-8"))["cases"][0]
    ensemble = bootstrap_mt(center["model_ohm_m"], [350.], s.frequencies, sig, active=mask,
                            initial=center["selected_start"], beta=.001, samples=20, seed=61002)
    assert ensemble["status"] == "computed" and ensemble["samples"] and not ensemble["failures"]
    np.testing.assert_allclose(ensemble["interval_ohm_m"], np.quantile(ensemble["samples"], [.025, .975], axis=0))
    # Actually refit one member against an independent reflection-generated observation.
    rng = np.random.default_rng(ensemble["sample_seeds"][0])
    obs = reflection(center["model_ohm_m"], [350.], s.frequencies) + sig * (rng.normal(size=len(sig)) + 1j * rng.normal(size=len(sig)))
    repeat = invert_mt([350.], s.frequencies, obs, sig, active=mask, initial=center["selected_start"],
                       beta=.001, methods=("mt-lm",), max_nfev=300)["mt-lm"]
    np.testing.assert_allclose(ensemble["samples"][0], repeat["model"], rtol=1e-7)


def test_cl061_source_exclusion():
    path = ROOT / "data/downloads/clear-lake/USGS-GMEG.2022.cl061.edi"
    if not path.exists():
        pytest.skip("Original rights-aware ignored cl061 source not present; never substitute synthetic field evidence")
    assert path.stat().st_size == 16411
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83"
    screen = screen_edi(path, units="mt", variance_convention="complex")
    assert not screen["one_d_inversion_eligible"] and screen["truth"] is None and screen["methods"] == {}
    values = [screen["compatibility"][key] for key in ("xx_component_wrms", "yy_component_wrms", "antisymmetry_conservative_wrms")]
    np.testing.assert_allclose(values, [320.233260669, 109.507875314, 267.600037116], rtol=1e-7)
    with pytest.raises(EDIError, match="Tensor fails"):
        invert_edi(path, [350.], units="mt", variance_convention="complex", bootstrap_samples=0)


if __name__ == "__main__":
    print("COURSE_WORKED_JSON=" + json.dumps(worked_case(), allow_nan=False, separators=(",", ":")))
