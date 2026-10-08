"""External data roots, no hidden raw/model/temp repository fallback."""

from pathlib import Path

import pytest

from magnetic_local_paths import local_data_root, data_output, external_path
from magnetic_survey_json import InputError


def test_root_requires_explicit_external_device(monkeypatch, tmp_path):
    monkeypatch.delenv('GEOPHYSICS_LOCAL_DATA_ROOT', raising=False)
    with pytest.raises(InputError, match='no repository fallback'):
        local_data_root()
    monkeypatch.setenv('GEOPHYSICS_LOCAL_DATA_ROOT', str(tmp_path))
    assert local_data_root() == tmp_path.resolve()
    assert data_output(tmp_path/'generation') == tmp_path/'generation'
    with pytest.raises(InputError, match='child'):
        data_output(tmp_path.parent/'elsewhere')
    with pytest.raises(InputError):
        data_output(tmp_path)


@pytest.mark.parametrize('path', [Path(__file__).parents[2]/'data'/'raw'/'new.json',
                                Path(__file__).parents[2]/'models'/'new.npy', Path('relative.json')])
def test_repository_and_relative_generation_forbidden(path):
    with pytest.raises(InputError, match='repository|absolute'):
        external_path(path)


def test_nested_git_root_detected_before_creation(tmp_path):
    checkout = tmp_path/'other_checkout'
    checkout.mkdir()
    (checkout/'.git').mkdir()
    with pytest.raises(InputError, match='repository'):
        external_path(checkout/'raw'/'model.npy')
