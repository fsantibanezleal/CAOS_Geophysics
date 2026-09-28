"""Independent ERT halfspace oracle and conditional field predictive gates."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

import ert as ert_pipeline
from ert import _mesh_sha256, Survey, flat_halfspace_factors, inverse_verdict, run, run_source

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/downloads/pygimli/slagdump.ohm"


def test_flat_homogeneous_oracle():
    pg = pytest.importorskip("pygimli")
    from pygimli.physics import ert

    pg.utils.noCache(True)
    survey = Survey(np.array([[0.0, 0], [2.0, 0], [4.0, 0], [6.0, 0]]),
                    np.array([[0, 3, 1, 2]]), np.array([1.0]), ())
    analytical = float(flat_halfspace_factors(survey)[0])
    assert analytical == pytest.approx(4 * math.pi, rel=1e-12)
    scheme = pg.DataContainerERT()
    for x in (0.0, 2.0, 4.0, 6.0):
        scheme.createSensor([x, 0.0, 0.0])
    scheme.createFourPointData(0, 0, 3, 1, 2)
    library_flat = float(ert.createGeometricFactors(scheme, numerical=False, forceFlatEarth=True)[0])
    assert library_flat == pytest.approx(analytical, rel=1e-5)
    mesh = pg.meshtools.createParaMesh(scheme.sensors(), paraDX=0.2,
                                       paraMaxCellSize=1, paraDepth=20, quality=33.6)
    refined = mesh.createH2()
    same_geometry = pg.meshtools.createParaMesh(scheme.sensors(), paraDX=0.2,
                                                paraMaxCellSize=1, paraDepth=20, quality=33.6)
    assert _mesh_sha256(mesh) == _mesh_sha256(same_geometry)
    assert _mesh_sha256(mesh) != _mesh_sha256(refined)
    coarse_response = ert.simulate(mesh=mesh, scheme=scheme, res=100.0, sr=False, calcOnly=True)
    fine_response = ert.simulate(mesh=refined, scheme=scheme, res=100.0, sr=False, calcOnly=True)
    coarse_rho = float(coarse_response["u"][0] / coarse_response["i"][0] * analytical)
    fine_rho = float(fine_response["u"][0] / fine_response["i"][0] * analytical)
    assert abs(fine_rho / 100 - 1) < 0.05
    assert abs(fine_rho - 100) < abs(coarse_rho - 100)


@pytest.fixture(scope="module")
def field_result():
    if not RAW.exists():
        pytest.skip("rights-restricted field raw asset is not present; run documented local acquisition")
    return run_source()


def test_topographic_factor_and_inverse(field_result):
    assert field_result["inverse_status"] == "passed"
    assert field_result["factors"]["flat_formula_max_relative_error"] < 1e-5
    assert field_result["factors"]["topography_median_abs_log_ratio"] > 0.01
    assert field_result["qc"]["topographic_relief_m"] > 10
    assert field_result["inverse"]["mesh_cells"] > 100


def test_field_result_receipt_and_uncertainty(field_result):
    assert field_result["source_sha256"] == hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert field_result["truth"] is None and field_result["field_geology_claim"] is None
    assert field_result["raw_publication"] is False
    assert field_result["weighting"]["source_error"] == "not supplied"
    assert field_result["weighting"]["chi_square_meaning"].startswith("conditional")
    assert field_result["qc"]["reciprocal_status"] == "not_available"
    model = field_result["inverse"]["model_resistivity_ohm_m"]
    assert len(model) == len(field_result["inverse"]["model_cell_center_xz_m"])
    assert len(model) == len(field_result["inverse"]["coverage_log10_sensitivity_per_cell"])
    assert np.isfinite(model).all() and (np.asarray(model) > 0).all()
    for digest in (field_result["configuration_sha256"], field_result["environment_versions_sha256"],
                   field_result["inverse"]["parameter_mesh_sha256"],
                   field_result["inverse"]["forward_mesh_sha256"]):
        assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    assert math.isfinite(field_result["sensitivity"]["alternate_mesh"]["heldout_log_r_rmse"])
    assert math.isfinite(field_result["sensitivity"]["doubled_assumed_error"]["heldout_log_r_rmse"])
    target = (ROOT / "data/raw/ert" / f"slagdump-m07-inverse-{field_result['code_sha256'][:12]}.json")
    assert target.exists()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == Path(str(target) + ".sha256").read_text().strip()
    assert json.loads(target.read_text(encoding="utf-8"))["source_sha256"] == field_result["source_sha256"]


def test_field_holdout_and_inverse_gate(field_result):
    split = field_result["split"]
    assert 0.15 <= split["heldout_count"] / 222 <= 0.25
    assert set(split["training_rows"]).isdisjoint(split["heldout_rows"])
    assert len(split["training_rows"] + split["heldout_rows"]) == 222
    assert field_result["inverse"]["engine_converged"] is True
    assert field_result["inverse"]["stopping_reason"] in {"objective-stagnation", "assumed-chi2-target"}
    assert field_result["inverse"]["heldout_improvement_vs_homogeneous"] >= 0.10
    assert field_result["inverse"]["heldout_log_r_rmse"] < field_result["baseline"]["heldout_log_r_rmse"]
    block = field_result["blocked_validation"]
    assert field_result["blocked_split"]["heldout_count"] >= 10
    assert block["engine_stopped_before_limit"] is True
    assert block["improvement_vs_homogeneous"] >= 0.10
    assert block["heldout_log_r_rmse"] < block["baseline_heldout_log_r_rmse"]
    assert len(field_result["inverse"]["signed_residual_r_ohm"]) == 222


def test_failed_inverse_never_claims_success(tmp_path, monkeypatch):
    assert inverse_verdict(engine_converged=False, improvement=0.8)[0] == "not-converged"
    assert inverse_verdict(engine_converged=True, improvement=0.09)[0] == "not-converged"
    assert inverse_verdict(engine_converged=True, improvement=math.nan)[0] == "not-converged"
    text = "\n".join(["# Wenner array with 2m", "8# Number of sensors", "#x z",
                      *(f"{2*i} 0" for i in range(8)), "5# Number of data", "#a b m n R",
                      *(f"{i+1} {i+4} {i+2} {i+3} {-1 if i == 0 else 1}" for i in range(5))])
    path = tmp_path / "negative.ohm"
    path.write_text(text + "\n", encoding="utf-8")
    result = run(path, source_sha256="0" * 64)
    assert result["inverse_status"] == "ineligible"
    assert "nonpositive resistance" in result["inverse_reason"]
    assert "inverse" not in result

    positive_path = tmp_path / "positive.ohm"
    positive_path.write_text(text.replace("1 4 2 3 -1", "1 4 2 3 1"), encoding="utf-8")

    def fail_factors(*_):
        raise ert_pipeline.ERTError("independent factor disagreement")

    monkeypatch.setattr(ert_pipeline, "factors", fail_factors)
    unverified = run(positive_path, source_sha256="0" * 64)
    assert unverified["inverse_status"] == "unverified"
    assert "independent factor disagreement" in unverified["inverse_reason"]
    assert unverified["qc"]["measurement_count"] == 5
    assert "inverse" not in unverified
