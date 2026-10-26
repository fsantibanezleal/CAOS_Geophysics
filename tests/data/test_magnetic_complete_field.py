"""Field admission negatives, using supplied bytes, not invented acquisitions."""

import json
from pathlib import Path

import pytest

from magnetic_field_evaluation import inspect_clear_lake, ORIGINAL_CAP, ROWS_CAP
from magnetic_survey_json import InputError


def record():
    records = json.loads((Path(__file__).parents[2]/'data'/'source-ledger.json').read_text())['sources']
    return next(r for r in records if r['source_id'] == 'clear-lake-author-potentials-v2')


def test_actual_wrong_complete_bytes_reject_before_zip(tmp_path):
    path = tmp_path/'wrong.zip'
    path.write_bytes(b'not an acquisition')
    with pytest.raises(InputError, match='complete field original'):
        inspect_clear_lake(path, record())


def test_repo_original_rejected_before_read():
    with pytest.raises(InputError):
        inspect_clear_lake(Path(__file__).parents[2]/'data'/'source-ledger.json', record())


def test_frozen_finite_caps_and_exact_identity():
    assert ORIGINAL_CAP == 134217728 and ROWS_CAP == 2048
    r = record()
    assert r['expected_bytes'] == 121295137
    assert r['sha256'] == '337a2d9070493773af06aee11a19d591e6468ecf0f062dd75c194a04476c0cdf'
    assert r['archive_contract']['selected_members']['data/aeromagnetic_data.csv']['bytes'] == 28531313
