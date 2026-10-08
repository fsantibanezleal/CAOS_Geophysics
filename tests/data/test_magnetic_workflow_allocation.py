"""No-fit source/path negatives; not full-workflow scientific acceptance."""
import importlib.util
from pathlib import Path

import pytest

import magnetic_original_adapter as adapter
import gravity_l2_metric as metric

spec = importlib.util.spec_from_file_location('original_workflow_gate',
    Path(__file__).parents[2]/'scripts/check_magnetic_original_workflow_allocation.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.mark.parametrize('changed', ['kernel', 'cap'])
def test_drift_or_increased_original_cap_refuses_before_request_parse(monkeypatch, changed):
    if changed == 'kernel':
        monkeypatch.setattr(metric, 'SOURCE_SHA256', 'f'*64)
    else:
        monkeypatch.setattr(adapter, 'LIMIT', 805306369)
    with pytest.raises(ValueError, match='Exact original phase source'):
        gate.workflow_allocation(b'Not parsed after refused source/cap')


def test_outside_request_or_existing_output_refuses_without_copy(tmp_path):
    root = tmp_path/'owned'
    root.mkdir()
    original = tmp_path/'outside.json'
    original.write_bytes(b'Never parsed')
    output = root/'report.json'
    dependencies = str(Path(metric.__file__).parent)
    with pytest.raises(ValueError, match='external input root'):
        gate.main(['--request', str(original), '--output', str(output), '--data-root', str(root),
                   '--dependencies', dependencies])
    assert not output.exists() and original.read_bytes() == b'Never parsed'
    inside = root/'request.json'
    inside.write_bytes(b'Never parsed either')
    output.write_bytes(b'Preserve known previous report')
    with pytest.raises(ValueError, match='fresh output'):
        gate.main(['--request', str(inside), '--output', str(output), '--data-root', str(root),
                   '--dependencies', dependencies])
    assert output.read_bytes() == b'Preserve known previous report'
