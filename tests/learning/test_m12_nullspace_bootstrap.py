from __future__ import annotations

import numpy as np
import pytest

from scripts.report_m12_nullspace_bootstrap import paired_bootstrap_ratio


def test_paired_case_bootstrap_is_reproducible_and_contains_observed_ratio():
    learned = np.array([1.0, 2.0, 4.0, 5.0])
    classical = np.array([2.0, 3.0, 5.0, 7.0])
    first = paired_bootstrap_ratio(learned, classical, seed=19, draws=2000)
    second = paired_bootstrap_ratio(learned, classical, seed=19, draws=2000)
    assert first == second
    assert first["paired_resampling_unit"] == "case_id"
    assert first["percentile_95_interval"][0] <= first["observed_ratio_of_means"]
    assert first["percentile_95_interval"][1] >= first["observed_ratio_of_means"]


@pytest.mark.parametrize(
    "learned,classical,kwargs",
    [
        ([1.0, np.nan], [2.0, 3.0], {}),
        ([1.0, 2.0], [2.0, 0.0], {}),
        ([1.0], [2.0], {}),
        ([1.0, 2.0], [2.0, 3.0], {"draws": 999}),
    ],
)
def test_paired_case_bootstrap_rejects_invalid_inputs(learned, classical, kwargs):
    with pytest.raises(ValueError):
        paired_bootstrap_ratio(np.asarray(learned), np.asarray(classical), **kwargs)
