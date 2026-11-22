"""Real ordinary full waveform workflow, NOT actual SDK/native/field admission."""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

PRODUCT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PRODUCT / "tests/fixtures/waveform_m08"))
sys.path.insert(0, str(PRODUCT / "scripts"))
sys.path.insert(0, str(PRODUCT / "data-pipeline"))
from waveform_m08_child import calculate_bytes  # noqa: E402
from waveform_processing import process_waveform_record  # noqa: E402
from waveform_evaluation import evaluate_waveform_candidates  # noqa: E402
from waveform_m08_export import plan_export, write_export, verify_export, copy_export  # noqa: E402
from waveform_m08_files import create_output, open_output  # noqa: E402


@pytest.mark.parametrize("case", ("nominal1", "nominal3", "upper3"))
def test_actual_full_science_same_input_and_postseal_export(tmp_path, case):
    from full_workflow import make_case

    fixture = make_case(case)
    identities = fixture["manifest"]["inputs"]
    result, sealed = calculate_bytes(fixture["mseed"], fixture["stationxml"], fixture["request"])
    assert result.metadata["status"] == "computed"
    assert all(flag is False for flag in result.metadata["acceptance"].values())
    assert result.metadata["field_truth"] is None
    baseline = process_waveform_record(fixture["mseed"], fixture["stationxml"], json.loads(fixture["request"]))
    assert baseline.metadata["status"] == "computed"
    assert result.metadata["array_descriptors"] == baseline.metadata["array_descriptors"]
    assert result.metadata["sources"] == baseline.metadata["sources"]
    assert result.metadata["request"]["scientific_sha256"] == baseline.metadata["request"]["scientific_sha256"]
    assert baseline.metadata["request"]["original_json_sha256"] is None
    assert baseline.metadata["request"]["original_json_bytes"] is None
    assert result.metadata["request"]["original_json_sha256"] == identities["request"]["sha256"]
    assert result.metadata["request"]["original_json_bytes"] == identities["request"]["bytes"]
    assert set(result.arrays) == set(baseline.arrays)
    for key, array in result.arrays.items():
        assert array.flags.owndata and not array.flags.writeable
        np.testing.assert_array_equal(array, baseline.arrays[key])
    for index in range(len(fixture["manifest"]["channels"])):
        assert result.arrays[(index, "counts")].shape == (fixture["manifest"]["samples_per_channel"],)
        assert result.arrays[(index, "physical_native")].shape == result.arrays[(index, "counts")].shape
        assert result.arrays[(index, "filtered_native")].shape == result.arrays[(index, "counts")].shape
        assert result.arrays[(index, "characteristic")].shape == result.arrays[(index, "counts")].shape
        assert all(
            (index, name) in result.arrays
            for name in (
                "counts_psd",
                "physical_psd",
                "filtered_psd",
                "response_frequency_hz",
                "response_real",
                "response_imag",
                "inverse_real",
                "inverse_imag",
                "edge_valid",
                "filter_sos",
                "time_taper",
            )
        )
    stage_path, final_path = tmp_path / "stage", tmp_path / "final"
    with create_output(stage_path, trusted_parent=tmp_path) as stage:
        receipt = write_export(plan_export(result, sealed), stage)
        assert receipt["bytes"] <= 33554432 and receipt["runtime_authorized"] is False
    with open_output(stage_path) as stage:
        assert verify_export(stage) == sealed
        before = {name: hashlib.sha256((stage_path / name).read_bytes()).hexdigest() for name in stage.names(55)}
        # Reference is supplied only here, after computation/seal/export/reopen.
        evaluated = evaluate_waveform_candidates(sealed, fixture["reference"])
        assert evaluated["status"] == "not_evaluable" and evaluated["field_truth"] is None
        with create_output(final_path, trusted_parent=tmp_path) as final:
            final_receipt = copy_export(stage, final, evaluation=json.dumps(evaluated).encode())
            assert final_receipt["runtime_authorized"] is False
        assert before == {
            name: hashlib.sha256((stage_path / name).read_bytes()).hexdigest() for name in stage.names(55)
        }
    with open_output(final_path) as final:
        assert verify_export(final) == sealed
        assert json.loads((final_path / "receipt.json").read_bytes())["resources"] == "unavailable"
        assert (final_path / "calculation.json").read_bytes() == sealed.metadata_bytes
    for name, row in identities.items():
        assert len(fixture[name]) == row["bytes"] and hashlib.sha256(fixture[name]).hexdigest() == row["sha256"]
