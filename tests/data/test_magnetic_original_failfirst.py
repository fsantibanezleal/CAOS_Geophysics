"""Ledger dependency refusal, no native/matrix/scientific acceptance claim."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('original_matrix_gate',
    Path(__file__).parents[2]/'scripts/run_magnetic_frozen_matrix.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.parametrize('verdict', ['failed_no_complete_result','failed_native_lifetime','synthetic_predictive_fail'])
def test_failed_original_prerequisite_blocks_later_matrix_birth(verdict):
    assert runner.original_prerequisite_failed(dict(scientific_verdict=verdict))


@pytest.mark.parametrize('verdict', ['synthetic_predictive_pass','null_numerical_control','adverse_discrimination_requires_matched_A'])
def test_nonfailed_record_is_not_full_method_admission(verdict):
    # The latter still requires independent matched-A evaluation; this merely
    # preserves its factual ledger instead of inventing a failed engine run.
    assert not runner.original_prerequisite_failed(dict(scientific_verdict=verdict))
