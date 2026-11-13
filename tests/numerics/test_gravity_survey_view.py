"""Native replay occurs before inspection projection; no selection or solve."""
from copy import deepcopy

import numpy as np
import pytest

import gravity_l2 as l2
import gravity_survey_view as view
import gravity_workflow_io as transport
from test_gravity_l2_selection import calibration_request
from test_gravity_irls_corrected_workflow import request as corrected_request
import gravity_irls_corrected_workflow as corrected_workflow
import gravity_irls as irls
from test_gravity_irls_workflow import request as irls_request


@pytest.fixture(scope="module")
def archive():
    request = calibration_request()
    result = l2.calibrate_gravity_l2(request)
    return {"schema": "gravity-calibration-archive-1", "request": request, "result": result}


@pytest.fixture(scope="module")
def corrected_archive():
    request = corrected_request()
    result = corrected_workflow.calibrate(request)
    return {"schema": "gravity-calibration-archive-1", "request": request, "result": result}


@pytest.fixture(scope="module")
def irls_archive():
    request = irls_request()
    result = irls.calibrate_gravity_irls(request)
    return {"schema": "gravity-calibration-archive-1", "request": request, "result": result}


def test_projection_replays_then_returns_actual_frame_and_development_only(archive, monkeypatch):
    expected_model = archive["result"]["final_solve"]["trace"]["models_kg_m3"][0]

    def forbidden(*_args, **_kwargs):
        pytest.fail("inspection must not optimize or calibrate")

    monkeypatch.setattr(l2, "_solve_partition", forbidden)
    monkeypatch.setattr(l2, "calibrate_gravity_l2", forbidden)
    packet = view.project_verified_calibration(archive, 24, 0)

    assert packet["schema"] == view.SCHEMA
    assert packet["selection"]["status"] == "selected"
    assert len(packet["selection"]["candidates"]) == 8
    assert sum(len(c["folds"]) for c in packet["selection"]["candidates"]) == 24
    assert packet["fit"]["status"] == "converged"
    np.testing.assert_array_equal(packet["cells"]["density_kg_m3"], expected_model)
    stations = packet["stations"]
    assert stations["residual_convention"] == "observed_minus_predicted"
    assert stations["acceleration_unit"] == "mGal" and stations["vertical_positive"] == "up"
    np.testing.assert_allclose(stations["residual_observed_minus_predicted_mgal"],
                               np.asarray(stations["observed_mgal"]) - np.asarray(stations["predicted_mgal"]))
    assert stations["row_indices"] == archive["result"]["plan"]["development_rows"].tolist()
    assert not set(stations["row_indices"]) & set(archive["result"]["plan"]["outer_rows"].tolist())
    assert packet["scope"]["field_eligible"] is False
    assert packet["scope"]["full_M02_accepted"] is False


def test_archive_bytes_gate_and_exact_actual_frame(archive):
    data = transport.archive_bytes(archive)
    packet = view.project_archive_bytes(data, 24, 0)
    assert packet["fit"]["frame_index"] == 0
    assert packet["fit"]["fit_sha256"] == view.project_verified_calibration(archive, 24, 0)["fit"]["fit_sha256"]
    with pytest.raises(ValueError, match="frame index"):
        view.project_verified_calibration(archive, 24, 10_000)
    with pytest.raises(ValueError, match="fit index"):
        view.project_verified_calibration(archive, True, 0)


def test_full_replay_rejects_rehashed_failed_score_before_projection(archive):
    changed = deepcopy(archive)
    changed["result"]["candidates"][0]["score_q"] = 1.0
    changed["result"]["result_sha256"] = l2.survey._digest(
        {k: v for k, v in changed["result"].items() if k != "result_sha256"})
    with pytest.raises(ValueError, match="eligibility|candidate|score"):
        view.project_verified_calibration(changed, 24, 0)


def test_corrected_cpu2_pool_projection_keeps_phase_and_stage_semantics(corrected_archive):
    packet = view.project_verified_calibration(corrected_archive, 24, 0)
    assert packet["method"] == "irls"
    assert packet["fit"]["runtime_epoch"] == corrected_archive["result"]["runtime_epoch"]
    assert packet["fit"]["accepted_state_count"] == len(packet["history"])
    assert packet["history"][0]["phase"] == "initialization"
    assert "model_kg_m3" not in packet["history"][0]
    assert packet["cells"]["density_kg_m3"] is not None
    assert len(packet["fit"]["stage_book"]) == 21
    assert packet["fit"]["stage_book"][-1]["inner_status"] == "converged"


def test_legacy_irls_fit_references_project_without_upgrading_policy(irls_archive):
    packet = view.project_verified_calibration(irls_archive, 24, 0)
    assert packet["method"] == "irls"
    assert packet["fit"]["runtime_epoch"] == irls_archive["result"]["provenance"]["runtime_epoch"]
    assert packet["fit"]["accepted_state_count"] == len(packet["history"])
    assert packet["history"][0]["phase"] == "native_inner"
    assert packet["scope"]["full_M02_accepted"] is False
    assert len(packet["fit"]["stage_book"]) == 21
