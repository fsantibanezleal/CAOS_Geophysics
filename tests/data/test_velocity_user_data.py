"""User-data physical controls, including actual frozen checkpoint inference."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import velocity_user_data as tool
from velocity_validation import acquisition, background, cell_length_matrix, GRID

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / "models/experimental/m12-velocity-cpu-20260928/m12-velocity.npz"
CHECKPOINT_SHA = "a06a29fc9b64e1797d9b96db10053097816256fa32b578ceb19c301b19b5a99d"


def request():
    rays = acquisition("A")
    return {"schema": tool.SCHEMA, "id": "owner-traveltimes",
            "source": {"citation": "Authored physical control", "rights": "owner-permitted", "scope": "synthetic-control"},
            "frame": "local-x-z-down", "units": {"distance": "m", "time": "s", "velocity": "m/s"},
            "ray_ids": [f"ray-{i}" for i in range(len(rays))], "rays_m": rays.tolist(),
            "times_s": (cell_length_matrix(rays) @ (1 / background().ravel())).tolist(),
            "sigma_s": [0.001] * len(rays), "lambda": 100.0}


def raw(doc):
    return json.dumps(doc).encode()


@pytest.mark.parametrize("change", [
    lambda d: d.update(frame="unknown"), lambda d: d.update(lambda_=1),
    lambda d: d["units"].update(distance="km"), lambda d: d["source"].update(rights="unknown"),
    lambda d: d["rays_m"][0].__setitem__(0, -1), lambda d: d["rays_m"][0].__setitem__(0, True),
    lambda d: d["rays_m"].__setitem__(0, [0, 0, 0, 0]), lambda d: d["times_s"].__setitem__(0, 0),
    lambda d: d["sigma_s"].__setitem__(0, -1), lambda d: d["ray_ids"].__setitem__(0, d["ray_ids"][1]),
    lambda d: d["times_s"].pop(), lambda d: d.__setitem__("lambda", True),
])
def test_bounded_physical_contract(change):
    d = request()
    change(d)
    with pytest.raises(tool.VelocityInputError):
        tool.validate_request(raw(d))


@pytest.mark.parametrize("payload", [b"{" * 13, b"[]" * 300000,
                                      b'{"id":1,"id":2}', b'{"id":NaN}', b'\xff',
                                      b'{"id":' + b'9' * 5000 + b'}'],
                         ids=["depth", "bytes", "duplicates", "nonfinite", "encoding", "integer-limit"])
def test_bounded_bytes_and_encoding(payload):
    with pytest.raises(tool.VelocityInputError):
        tool.validate_request(payload)


def test_identity_and_original_order():
    payload = raw(request())
    before = hashlib.sha256(payload).hexdigest()
    result = tool.calculate(payload)
    assert result["source"] == {"sha256": before, "bytes": len(payload)}
    assert result["request"]["ray_ids"] == request()["ray_ids"]
    assert hashlib.sha256(payload).hexdigest() == before
    assert result["results"]["classical"]["data_wrms"] < 1e-10
    assert not any(result["claims"].values())


def test_weighted_inverse_and_parameter_effect():
    d = request()
    a = cell_length_matrix(np.asarray(d["rays_m"]))
    d["times_s"] = (np.asarray(d["times_s"]) + np.linspace(-0.01, 0.02, len(a))).tolist()
    d["sigma_s"] = np.linspace(0.001, 0.008, len(a)).tolist()
    result = tool.calculate(raw(d))["results"]["classical"]
    # Build neighbour differences independently, not candidate gram helper.
    rows = []
    for z in range(GRID):
        for x in range(GRID):
            index = z * GRID + x
            for neighbor in ((index + 1,) if x + 1 < GRID else ()) + ((index + GRID,) if z + 1 < GRID else ()):
                row = np.zeros(GRID * GRID)
                row[index], row[neighbor] = 1, -1
                rows.append(row)
    diff = np.stack(rows)
    sigma = np.asarray(d["sigma_s"])
    s0 = 1 / background().ravel()
    b = a / (1000 * sigma[:, None])
    y = (d["times_s"] - a @ s0) / sigma
    q = np.linalg.solve(b.T @ b + d["lambda"] * diff.T @ diff + 0.01 * np.eye(GRID * GRID), b.T @ y)
    expected = np.clip(s0 + q / 1000, 1 / 4000, 1 / 1400)
    actual = 1 / np.asarray(result["velocity_m_s"]).ravel()
    np.testing.assert_allclose(1000 * (actual - s0), 1000 * (expected - s0), atol=1e-10, rtol=1e-10)
    bounded_q = 1000 * (actual - s0)
    assert result["regularizer"] == pytest.approx(d["lambda"] * np.sum((diff @ bounded_q) ** 2) + 0.01 * np.sum(bounded_q ** 2), rel=1e-9)
    changed = copy.deepcopy(d)
    changed["lambda"] = 1
    assert not np.allclose(result["velocity_m_s"], tool.calculate(raw(changed))["results"]["classical"]["velocity_m_s"])
    changed = copy.deepcopy(d)
    changed["sigma_s"][0] *= 10
    assert not np.array_equal(result["velocity_m_s"], tool.calculate(raw(changed))["results"]["classical"]["velocity_m_s"])


def test_actual_checkpoint_inference():
    result = tool.calculate(raw(request()), checkpoint=CHECKPOINT, checkpoint_sha256=CHECKPOINT_SHA)
    assert set(result["results"]) == {"classical", "learned"}
    assert result["learned_domain"] == {"training_geometry": True, "training_noise": True, "field_validated": False, "heldout_advantage": False}
    assert any("failed" in x for x in result["warnings"])
    assert not np.array_equal(result["results"]["classical"]["velocity_m_s"], result["results"]["learned"]["velocity_m_s"])
    d = request()
    d["rays_m"][0][1] += 1
    shifted = tool.calculate(raw(d), checkpoint=CHECKPOINT, checkpoint_sha256=CHECKPOINT_SHA)
    assert shifted["learned_domain"]["training_geometry"] is False
    with pytest.raises(tool.VelocityInputError, match="identity"):
        tool.calculate(raw(d), checkpoint=CHECKPOINT, checkpoint_sha256="0" * 64)


def test_bundle_roundtrip_and_corruption(tmp_path):
    result = tool.calculate(raw(request()))
    destination = tmp_path / "generation"
    assert tool.export_generation(result, destination) == result
    assert tool.verify_generation(destination) == result
    with pytest.raises(FileExistsError):
        tool.export_generation(result, destination)
    original = (destination / "result.json").read_bytes()
    (destination / "result.json").write_bytes(original + b" ")
    with pytest.raises(tool.VelocityInputError):
        tool.verify_generation(destination)


def test_failed_verification_has_no_success_manifest(tmp_path, monkeypatch):
    result = tool.calculate(raw(request()))
    def fail(*args):
        raise tool.VelocityInputError("Injected integrity failure")
    monkeypatch.setattr(tool, "_verify_result", fail)
    with pytest.raises(tool.VelocityInputError):
        tool.export_generation(result, tmp_path / "failure")
    assert (tmp_path / "failure/result.json").exists()
    assert not (tmp_path / "failure/manifest.json").exists()


def test_rehashed_result_does_not_bypass_physical_reopen(tmp_path):
    result = tool.calculate(raw(request()))
    for field in ("residual_s", "data_chi_square", "regularizer"):
        changed = copy.deepcopy(result)
        if field == "residual_s":
            changed["results"]["classical"][field][0] += 1
        else:
            changed["results"]["classical"][field] += 1
        with pytest.raises(tool.VelocityInputError):
            tool.export_generation(changed, tmp_path / field)
        assert not (tmp_path / field / "manifest.json").exists()


def test_upper_row_count_and_finite_export(tmp_path):
    d = request()
    d["rays_m"] = (d["rays_m"] * 16)
    d["times_s"] = d["times_s"] * 16
    d["sigma_s"] = d["sigma_s"] * 16
    d["ray_ids"] = [f"upper-{i}" for i in range(2048)]
    result = tool.calculate(raw(d))
    assert len(result["results"]["classical"]["predicted_s"]) == 2048
    assert tool.export_generation(result, tmp_path / "upper") == result


def test_cli_actual_input_and_no_overwrite(tmp_path):
    source, destination = tmp_path / "survey.json", tmp_path / "output"
    source.write_bytes(raw(request()))
    command = [sys.executable, str(ROOT / "scripts/process_velocity.py"), "--input", str(source), "--output", str(destination)]
    done = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    tool.verify_generation(destination)
    repeat = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert repeat.returncode == 2
    assert tool.verify_generation(destination)["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
