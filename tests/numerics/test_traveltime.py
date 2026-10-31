"""Independent homogeneous oracle and predeclared whole-shot M09 gates."""

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import traveltime as pipeline
from traveltime import Survey, TraveltimeError, run, run_source, shot_splits

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get("GEOPHYSICS_LOCAL_DATA_ROOT", ROOT))
RAW = DATA_ROOT / "data/downloads/pygimli/koenigsee.sgt"


def test_homogeneous_forward_oracle():
    pg = pytest.importorskip("pygimli")
    from pygimli.physics import traveltime as tt

    pg.utils.noCache(True)
    points = np.asarray([[0., 0.], [3., 0.], [0., -4.], [3., -4.]])
    pairs = np.asarray([[0, 3], [3, 0], [1, 2]])
    scheme = tt.DataContainerTT()
    for x, y in points:
        scheme.createSensor([x, y])
    scheme.resize(len(pairs))
    scheme["s"], scheme["g"] = pairs[:, 0], pairs[:, 1]
    mesh = pg.meshtools.createGrid(x=np.linspace(0, 3, 31), y=np.linspace(-4, 0, 41))
    velocity = np.full(mesh.cellCount(), 1000.)
    predicted = np.asarray(tt.TravelTimeManager().simulate(
        mesh=mesh, scheme=scheme, vel=velocity, secNodes=8, returnArray=True))
    expected = np.asarray([5., 5., 5.]) / 1000.  # independent 3-4-5 geometry
    assert np.max(abs(predicted / expected - 1)) < 1e-3
    assert predicted[0] == pytest.approx(predicted[1], rel=1e-3)
    doubled = np.asarray(tt.TravelTimeManager().simulate(
        mesh=mesh, scheme=scheme, vel=2 * velocity, secNodes=8, returnArray=True))
    assert np.max(abs(2 * doubled / predicted - 1)) < 1e-3
    result = pipeline.homogeneous_oracle()
    assert result["max_relative_error"] < 1e-3
    assert result["reciprocity_relative_error"] < 1e-3
    assert result["max_speed_scaling_relative_error"] < 1e-3


@pytest.fixture(scope="module")
def field_result():
    if not RAW.exists():
        pytest.skip("rights-restricted .sgt absent; run documented local acquisition")
    pytest.importorskip("pygimli")
    return run_source()


def test_homogeneous_time_and_field_holdout(field_result):
    result = field_result
    assert result["inverse_status"] == "passed", result.get("inverse_reason")
    assert result["homogeneous_oracle"]["max_relative_error"] < 1e-3
    assert result["qc"]["topographic_relief_m"] > 0
    assert result["qc"]["pick_count"] == 714
    assert result["weighting"]["source_error"] == "not supplied"
    for name in ("interleaved", "central_block"):
        model = result["inverse"][name]
        assert model["engine_stopped_before_limit"] is True
        assert model["stopping_reason"] in {"objective-stagnation", "assumed-chi2-target"}
        assert model["heldout_improvement"] >= 0.10
        assert model["improved_held_shot_count"] >= 2
        assert model["heldout_rmse_s"] < model["baseline_heldout_rmse_s"]
        assert len(model["predicted_t_s"]) == result["qc"]["pick_count"]
        assert len(model["signed_residual_t_s"]) == result["qc"]["pick_count"]
        assert len(model["model_velocity_m_s"]) == model["mesh_cells"]
        assert len(model["raypath_coverage_m_per_cell"]) == model["mesh_cells"]
        assert np.isfinite(model["model_velocity_m_s"]).all()
        assert (np.asarray(model["model_velocity_m_s"]) > 0).all()
        assert np.isfinite(model["predicted_t_s"]).all()
        assert (np.asarray(model["predicted_t_s"]) > 0).all()
        assert 0 < model["coverage_nonzero_cell_fraction"] <= 1
        assert all(item["improvement"] > 0 for item in model["per_held_shot"])


def test_field_receipt_and_uncertainty_boundary(field_result):
    result = field_result
    assert result["source_sha256"] == hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert result["rights_decision"] == "provider-link-only"
    assert result["raw_publication"] is False
    assert result["truth"] is None and result["field_geology_claim"] is None
    assert result["uncertainty_status"] == "assumed-not-calibrated"
    assert result["qc"]["reciprocal_status"] == "not_available"
    assert result["weighting"]["chi_square_meaning"].startswith("conditional")
    assert result["engine"]["thread_count"] == 1
    assert result["engine"]["cgls_max_iterations"] == 1000
    assert result["engine"]["cgls_residual_squared_tolerance"] == 1e-20
    for digest in (result["source_sha256"], result["code_sha256"],
                   result["configuration_sha256"], result["environment_versions_sha256"],
                   *(model[key] for model in result["inverse"].values()
                     for key in ("parameter_mesh_sha256", "forward_mesh_sha256"))):
        assert len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)
    for key in ("alternate_gradient_start", "finer_parameter_mesh"):
        sensitivity = result["sensitivity"][key]
        assert math.isfinite(sensitivity["heldout_rmse_s"])
        assert 0 < sensitivity["coverage_nonzero_cell_fraction"] <= 1
    target = Path(result["local_receipt_path"])
    assert target.is_relative_to(DATA_ROOT / "data/raw/traveltime")
    assert target.exists()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == Path(str(target) + ".sha256").read_text().strip()
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["source_sha256"] == result["source_sha256"]
    assert saved["inverse_status"] == result["inverse_status"]


def test_independent_process_fit_reproducibility():
    if not RAW.exists():
        pytest.skip("rights-restricted .sgt absent; run documented local acquisition")
    pytest.importorskip("pygimli")
    code = """
import json
from pathlib import Path
import sys
import os
sys.path.insert(0, 'data-pipeline')
import traveltime as m
path = Path(os.environ['GEOPHYSICS_LOCAL_DATA_ROOT']) / 'data/downloads/pygimli/koenigsee.sgt'
survey = m.parse_sgt(path)
tt, data = m._pygimli_data(path, survey)
fit = m._invert_once(tt, data, survey, m.shot_splits(survey)['interleaved'],
                     m.INVERSE_OPTIONS, retain_arrays=True)
print('M09_RESULT=' + json.dumps(fit, allow_nan=False))
"""

    def fresh_fit():
        completed = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True,
                                   text=True, check=True, timeout=180)
        payload = [line.removeprefix("M09_RESULT=") for line in completed.stdout.splitlines()
                   if line.startswith("M09_RESULT=")]
        assert len(payload) == 1, completed.stdout + completed.stderr
        return json.loads(payload[0])

    first, second = fresh_fit(), fresh_fit()
    assert first["parameter_mesh_sha256"] == second["parameter_mesh_sha256"]
    assert first["forward_mesh_sha256"] == second["forward_mesh_sha256"]
    assert first["iterations"] == second["iterations"]
    assert first["stopping_reason"] == second["stopping_reason"]
    assert np.allclose(first["model_cell_center_xy_m"], second["model_cell_center_xy_m"],
                       rtol=0, atol=1e-8)
    assert np.allclose(first["model_velocity_m_s"], second["model_velocity_m_s"],
                       rtol=pipeline.REPEAT_VELOCITY_RTOL,
                       atol=pipeline.REPEAT_VELOCITY_ATOL_M_S)
    assert np.allclose(first["predicted_t_s"], second["predicted_t_s"],
                       rtol=0, atol=pipeline.REPEAT_TIME_ATOL_S)
    assert abs(first["heldout_rmse_s"] - second["heldout_rmse_s"]) <= pipeline.REPEAT_TIME_ATOL_S
    assert first["heldout_improvement"] >= 0.10 and second["heldout_improvement"] >= 0.10


def test_whole_shot_splits_and_failure_gate(field_result, monkeypatch):
    result = field_result
    survey = Survey(np.asarray(result["observations"]["sensor_xy_m"]),
                    np.asarray(result["observations"]["shot_geophone_zero_based"]),
                    np.asarray(result["observations"]["picked_t_s"]))
    splits = shot_splits(survey)
    for name in ("interleaved", "central_block"):
        split = splits[name]
        training, held = split["training_rows"], split["held_rows"]
        assert set(training).isdisjoint(held)
        assert len(training) + len(held) == len(survey.time_s)
        assert set(survey.shot_geophone[training, 0]).isdisjoint(
            survey.shot_geophone[held, 0])
        assert len(split["held_shots"]) == 3
        assert result["split"][name]["sha256"] == pipeline._split_record(name, split)["sha256"]
    assert set(splits["interleaved"]["held_shots"]) != set(splits["central_block"]["held_shots"])
    good = result["inverse"]
    for mutation in ({"heldout_improvement": 0.09}, {"improved_held_shot_count": 1},
                     {"engine_stopped_before_limit": False}, {"heldout_improvement": math.nan}):
        failed = {**good, "central_block": {**good["central_block"], **mutation}}
        assert pipeline._field_verdict(failed)[0] == "not-converged"

    def fail_oracle():
        raise TraveltimeError("forced independent oracle failure")

    monkeypatch.setattr(pipeline, "homogeneous_oracle", fail_oracle)
    retained = run(RAW, source_sha256=result["source_sha256"])
    assert retained["inverse_status"] == "unverified"
    assert "forced independent oracle failure" in retained["inverse_reason"]
    assert retained["qc"]["pick_count"] == len(survey.time_s)
    assert "inverse" not in retained

    monkeypatch.setattr(pipeline, "homogeneous_oracle", lambda: result["homogeneous_oracle"])
    calls = 0

    def fail_second_fit(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"partial_marker": "retained first split"}
        raise TraveltimeError("forced blocked-fit failure")

    monkeypatch.setattr(pipeline, "_invert_once", fail_second_fit)
    partial = run(RAW, source_sha256=result["source_sha256"])
    assert partial["inverse_status"] == "not-converged"
    assert "forced blocked-fit failure" in partial["inverse_reason"]
    assert partial["inverse"]["interleaved"]["partial_marker"] == "retained first split"
    assert partial["qc"]["pick_count"] == len(survey.time_s)


def test_failed_receipt_is_retained_and_checksums_guard_it(tmp_path):
    report = {"schema": "test-failed-m09", "source_sha256": "0" * 64,
              "code_sha256": "1" * 64, "qc": {"pick_count": 4},
              "inverse_status": "unverified", "inverse_reason": "oracle failure"}
    target = pipeline.save_local_receipt(report, root=tmp_path, kind="failed-test")
    assert target.exists()
    assert pipeline.save_local_receipt(report, root=tmp_path, kind="failed-test") == target
    target.write_text(target.read_text(encoding="utf-8") + "drift", encoding="utf-8")
    with pytest.raises(TraveltimeError, match="checksum drift"):
        pipeline.save_local_receipt(report, root=tmp_path, kind="failed-test")


def test_receipt_repeat_rejects_model_prediction_and_sensitivity_drift(tmp_path):
    model = {"parameter_mesh_sha256": "a" * 64, "forward_mesh_sha256": "b" * 64,
             "iterations": 4, "stopping_reason": "objective-stagnation",
             "model_cell_center_xy_m": [[0.0, -1.0], [1.0, -1.0]],
             "model_velocity_m_s": [1000.0, 1500.0],
             "predicted_t_s": [0.001, 0.002], "heldout_rmse_s": 0.001}
    sensitivity = {key: {"parameter_mesh_sha256": "a" * 64,
                         "forward_mesh_sha256": "b" * 64,
                         "iterations": 4, "stopping_reason": "objective-stagnation",
                         "heldout_rmse_s": 0.001}
                   for key in ("alternate_gradient_start", "finer_parameter_mesh")}
    report = {"schema": "test-repeated-m09", "source_sha256": "0" * 64,
              "code_sha256": "1" * 64, "qc": {"pick_count": 2},
              "unit_basis": "test", "inverse_status": "passed",
              "configuration_sha256": "2" * 64, "environment_versions_sha256": "3" * 64,
              "split": {name: {"sha256": "4" * 64}
                        for name in ("interleaved", "central_block")},
              "inverse": {name: deepcopy(model) for name in ("interleaved", "central_block")},
              "sensitivity": sensitivity}
    target = pipeline.save_local_receipt(report, root=tmp_path, kind="repeat-test")
    original = target.read_bytes()
    assert pipeline.save_local_receipt(report, root=tmp_path, kind="repeat-test") == target
    for section, key, value, expected in (
        ("inverse", "predicted_t_s", [0.00102, 0.002], "forward times"),
        ("inverse", "model_velocity_m_s", [1002.0, 1500.0], "velocity model"),
        ("sensitivity", "heldout_rmse_s", 0.00102, "finer_parameter_mesh"),
    ):
        changed = deepcopy(report)
        name = "interleaved" if section == "inverse" else "finer_parameter_mesh"
        changed[section][name][key] = value
        with pytest.raises(TraveltimeError, match=expected):
            pipeline.save_local_receipt(changed, root=tmp_path, kind="repeat-test")
        assert target.read_bytes() == original

    partial = deepcopy(report)
    partial["inverse_status"] = "not-converged"
    partial["inverse_reason"] = "blocked fit failed before sensitivity"
    del partial["inverse"]["central_block"]
    del partial["sensitivity"]
    failed_path = pipeline.save_local_receipt(partial, root=tmp_path, kind="partial-test")
    assert pipeline.save_local_receipt(partial, root=tmp_path, kind="partial-test") == failed_path
