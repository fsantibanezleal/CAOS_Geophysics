"""Changed retained-training-state prerequisite, explicitly scheduled only.

No minimize/CG, model adoption, test truth or fit historical upgrade. Run
through the existing device-exclusive validation DAG, never automatic suite
discovery against a private archive or an unreserved shared timing window.
"""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from time import monotonic

import numpy as np
import pytest

import gravity_face_gradient_oracle as oracle
import gravity_irls_face as face
import gravity_irls_original as original
import gravity_irls_pool as pool
import gravity_workflow_io as archive_io
from gravity_irls_corrected_workflow import _Workflow

ARCHIVE_SHA256 = 'de66a98317374ede83dfa2d32e13ee29afe3841130906933ff0724b1411d8751'


@pytest.mark.parametrize('fold', [1, 2])
def test_changed_original_retained_canonical_gradient(fold):
    archive_name = os.environ.get('GEOPHYSICS_M02_FACE_RESEARCH_ARCHIVE')
    output_name = os.environ.get('GEOPHYSICS_M02_FACE_RESEARCH_OUTPUT')
    data_root_name = os.environ.get('GEOPHYSICS_M02_FACE_RESEARCH_DATA_ROOT')
    temp_root_name = os.environ.get('GEOPHYSICS_M02_FACE_RESEARCH_TEMP_ROOT')
    if not all((archive_name, output_name, data_root_name, temp_root_name)):
        pytest.skip('explicit private archive, receipt and external device roots required')
    archive, output = Path(archive_name).resolve(), Path(output_name).resolve()
    assert Path(data_root_name).is_absolute() and Path(temp_root_name).is_absolute()
    device_data = Path(data_root_name).resolve()
    device_temp = Path(temp_root_name).resolve()
    repository = Path(__file__).resolve().parents[2]
    assert device_data.is_dir() and device_temp.is_dir()
    assert not device_data.is_relative_to(repository) and not device_temp.is_relative_to(repository)
    assert not repository.is_relative_to(device_data) and not repository.is_relative_to(device_temp)
    assert archive.is_relative_to(device_data) and archive != device_data
    assert output.is_relative_to(device_temp) and output != device_temp
    assert archive.is_file() and archive.stat().st_size < 64*1024**2
    receipt_path = output/f'fold{fold}-stage20.json'
    assert not receipt_path.exists(), 'immutable fresh research output only'
    output.mkdir(parents=True, exist_ok=True)
    started = monotonic()
    deadline = started+120.
    raw = archive.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256
    wrapper = archive_io.native_from_archive(raw)
    admitted = _Workflow('cpu3').admit(wrapper['request'])
    fit = pool.decode(wrapper['result']['fits'][fold])
    candidate = wrapper['result']['candidates'][0]
    assert candidate['index'] == 0 and candidate['folds'][fold]['solve'] == fold
    beta = admitted['policy']['beta_candidates'][0]
    assert beta == candidate['beta_candidate'] == .0001
    attempt = fit['attempts'][20]
    assert attempt['stage'] == 20 and attempt['outcome'] == 'disabled'
    q = fit['models_q'][attempt['model_row']].copy()
    rows = admitted['plan']['folds'][fold]['fit_rows']
    owner = original.GravityIRLSPartition(admitted['plan']['request'],
        admitted['observations']['gz_up_mgal'],
        {k: admitted['noise'][k] for k in ('kind', 'values')}, admitted['prior'], rows,
        beta, observation_rows=admitted['plan']['development_rows'], deadline=deadline)
    derivative = None
    try:
        derivative = face._CanonicalFaceLinearization(owner, q, admitted['policy']['irls'],
            20, fit['initial_epsilon'])
        assert derivative.face['branch'] == 'native_binding_max_constant_scale'
        assert derivative.face['free_scale_gap'] > 0.
        evidence = oracle.gradient_evidence(owner, derivative)
        assert evidence['enclosure_passed']
        # Keep the exact retained adverse diagnostic visible. This NEW
        # decomposition is not a rewrite of the old unqualified ideal-gate.
        historical_limit = Decimal('1e-12')*max(Decimal(1),
            Decimal.from_float(float(np.max(np.abs(evidence['native_gradient'])))))
        ideal_comparison = Decimal(evidence['native_ideal_error']) <= historical_limit
        if fold == 1:
            assert not ideal_comparison
        assert not evidence['native_fit_accepted'] and not evidence['recurrence_enabled']
        assert evidence['actual_CG_calls'] == evidence['actual_minimize_calls'] == 0
        derivative.check()
        inventory = owner.inventory.copy()
        binding = derivative.face['binding'].tolist()
        free = derivative.face['free'].tolist()
        maxima = derivative.face['maxima'].tolist()
    finally:
        if derivative is not None:
            derivative.close()
            assert derivative.live_payload_bytes == 0
        owner.close()
    seconds = monotonic()-started
    assert seconds <= 120.
    evidence['native_gradient'] = evidence['native_gradient'].tolist()
    receipt = dict(evidence, archive_sha256=ARCHIVE_SHA256, fold=fold, stage=20,
        retained_model_row=attempt['model_row'], retained_q=q.tolist(),
        native_binding=binding, free=free, maxima=maxima,
        original_native_inventory=inventory, actual_seconds=seconds, declared_seconds=120.,
        historical_ideal_comparison_passed=bool(ideal_comparison),
        full_physical_replay_passed=False, original_positive_assertions_passed=False)
    # Runtime scientific evidence, not a source-file edit. Exclusive creation
    # preserves earlier receipts and all original adverse archives.
    with receipt_path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, sort_keys=True, allow_nan=False, indent=2)
