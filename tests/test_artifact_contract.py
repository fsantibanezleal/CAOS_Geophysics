"""Regressions for the independent release matrix, not the producer catalogue."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from rebuild import jsonable
from catalog import absolute_percentile,display_scale,update_extrema


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


def test_fwi_export_precision_round_trips_float32_state():
    model_value=np.float32(2100.1234)
    assert np.float32(jsonable(float(model_value),10))==model_value
    assert np.float32(jsonable(float(model_value),7))!=model_value


def test_case_display_scale_preserves_cross_condition_amplitude():
    stats=[0.,0.]
    update_extrema(stats,[[-0.2,0.4],[0.8]])
    update_extrema(stats,[[-0.5,1.3]])
    scale=display_scale(stats)
    assert scale['signed'] and scale['maximum']>1.3
    assert scale['range']==[-scale['maximum'],scale['maximum']]
    assert scale['maximum']==pytest.approx(1.3,rel=2e-6)


def test_reference_inverse_percentile_is_absolute_and_not_truth_driven():
    assert absolute_percentile([-4.,0.,1.,10.],0.9)==4.
    with pytest.raises(ValueError,match='Invalid inverse model'):
        absolute_percentile([float('nan')])


@pytest.mark.parametrize('name',['validation.json','fwi-replay.json'])
def test_release_evidence_uses_platform_stable_lf(name):
    path=contract.ROOT/name
    assert path.is_file()
    assert b'\r\n' not in path.read_bytes(),f'{name} would differ between Windows build and GitHub Pages'
