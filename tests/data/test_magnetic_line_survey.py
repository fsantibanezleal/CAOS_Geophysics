"""Allocation controls for the distinct provisional M03 streamed profile."""
from importlib import import_module
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data-pipeline"))


def module():
    return import_module("magnetic_line_survey")


def test_phase_allocation_capacity():
    p = module()
    bounds = p.allocation_bounds(8000000, 65536, 1048576, 4194304)
    assert bounds["fit_buffer_bytes"] == 3324665856
    assert bounds["transform_buffer_bytes"] == 2415919104
    assert bounds["fit_buffer_bytes"] < 4 * 1024**3
    small = p.plan_capacity(1000, 200, raw_bytes=100000)
    assert small["kernel_pair_bound"] == 1000 * 200 * 4004 * 25
    assert small["resource_state"] == "unmeasured"
    assert small["profile"] == "m03-offline-stream/1"
    # Geometry at simultaneous raw/source maxima exceeds the all-fit work cap;
    # a byte formula below RAM limit is NOT an admitted execution.
    with pytest.raises(p.SurveyError, match="resource_refused"):
        p.plan_capacity(8000000, 65536)


@pytest.mark.parametrize("n,m", [(True, 4), (3., 4), (0, 4), (8000001, 4),
                                  (3, False), (3, 65537), (3, -1)])
def test_capacity_native_counts(n, m):
    p = module()
    with pytest.raises(p.SurveyError):
        p.plan_capacity(n, m)


def test_auxiliary_and_scratch_capacity():
    p = module()
    plan = p.plan_capacity(200, 30, auxiliary_rows=1200,
                           crossover_candidates=900, raw_bytes=100000,
                           auxiliary_bytes=50000, exported_cells=1024,
                           fft_cells=4096)
    assert plan["scratch_bound_bytes"] == (
        2 * 150000 + 512 * 200 + 256 * 30 + 256 * 900 +
        256 * 1024 + 128 * 4096 + 268435456)
    for key, value in [("auxiliary_rows", 16000001), ("raw_bytes", 4294967297),
                       ("crossover_candidates", 8000001), ("exported_cells", 1048577),
                       ("fft_cells", 4194305), ("auxiliary_bytes", True)]:
        with pytest.raises(p.SurveyError):
            p.plan_capacity(200, 30, **{key: value})


def test_no_dense_global_or_hidden_tiles():
    p = module()
    plan = p.plan_capacity(1000000, 1000)
    assert plan["fit_buffer_bytes"] < 8 * 1000000 * 1000
    assert plan["resource_state"] == "unmeasured"
    # No old ordinary module edits/monkeypatched global limits.
    assert p.ROW_LIMIT == 8000000 and p.SOURCE_LIMIT == 65536


def test_safe_native_error_without_arbitrary_details():
    p = module()
    error = p.SurveyError("invalid_contract", "fit")
    assert error.error == {
        "schema": "magnetic-line-survey-error/1", "code": "invalid_contract",
        "stage": "fit", "field": None, "message": "invalid_contract:fit",
        "partial_manifest_sha256": None}
    assert str(error) == "invalid_contract:fit"
