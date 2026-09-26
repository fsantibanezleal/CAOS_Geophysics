"""Regressions for the independent release matrix, not the producer catalogue."""
import importlib.util
from pathlib import Path

import pytest


SCRIPT=Path(__file__).resolve().parents[1]/'scripts/check_artifacts.py'
SPEC=importlib.util.spec_from_file_location('artifact_contract',SCRIPT)
contract=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def test_expected_release_matrix_is_explicit():
    assert len(contract.EXPECTED_CASE_FAMILY)==20
    assert len(contract.EXPECTED_VARIANTS)==6
    assert sum(6*len(contract.EXPECTED_METHODS[family])
               for family in contract.EXPECTED_CASE_FAMILY.values())==348


@pytest.mark.parametrize('family',sorted(contract.EXPECTED_METHODS))
def test_same_omission_in_run_and_catalogue_is_rejected(family):
    expected=contract.EXPECTED_METHODS[family]
    missing=set(expected)-{next(iter(expected))}
    with pytest.raises(AssertionError,match='missing or unexpected run methods'):
        contract.assert_method_matrix(family,missing,missing)


def test_unexpected_method_is_rejected_even_when_catalogue_agrees():
    expected=contract.EXPECTED_METHODS['gravity']|{'fabricated'}
    with pytest.raises(AssertionError,match='missing or unexpected run methods'):
        contract.assert_method_matrix('gravity',expected,expected)


def test_catalogue_only_method_mismatch_is_rejected():
    expected=contract.EXPECTED_METHODS['mt']
    with pytest.raises(AssertionError,match='missing or unexpected catalogue methods'):
        contract.assert_method_matrix('mt',expected,expected-{'mt-neural'})
