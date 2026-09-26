"""Recovery gates, deliberately separate from a waveform-decrease smoke test.

FWI_RECOVERY_PROBES can reuse local ignored probe files only when their source
digest matches the current solver. Otherwise the reference cases run afresh.
Never writes canonical data. CUDA tests must be serialized with other GPU jobs.
"""
import hashlib
import inspect
import json
import os
from pathlib import Path

import numpy as np
import pytest
import torch

import seismic
from geology import registry

ROOT = Path(__file__).resolve().parents[1]


def test_frequency_filter_has_physical_cutoff_and_gradient():
    dt = .001
    t = torch.arange(16000, dtype=torch.float64)*dt
    for frequency in (2., 5., 15.):
        x = torch.sin(2*torch.pi*frequency*t)
        y = seismic.lowpass(x, 5., dt)
        gain = float((y[4000:-4000]*x[4000:-4000]).sum()/x[4000:-4000].square().sum())
        assert gain == pytest.approx((1+(frequency/5)**12)**-.5, rel=.015, abs=2e-5)
    torch.manual_seed(43)
    x = torch.randn(1, 2, 512, dtype=torch.float64, requires_grad=True)
    direction = torch.randn_like(x)
    loss = seismic.lowpass(x, 8., dt).square().sum()
    loss.backward()
    eps = 1e-5
    finite = (seismic.lowpass(x.detach()+eps*direction, 8., dt).square().sum()
              - seismic.lowpass(x.detach()-eps*direction, 8., dt).square().sum())/(2*eps)
    assert float(finite) == pytest.approx(float((x.grad*direction).sum()), rel=1e-7)
    with pytest.raises(ValueError):
        seismic.lowpass(x, 0)


def test_spatial_regularization_and_initial_are_physical():
    a = torch.tensor(seismic.independent_start())
    b = torch.tensor(seismic.independent_start((255, 191), 6.25))
    assert float(seismic.physical_roughness(a)) == pytest.approx(float(seismic.physical_roughness(b, 6.25)), rel=1e-5)
    np.testing.assert_array_equal(a.numpy(), np.broadcast_to(1800+11*np.arange(96), (128, 96)))
    assert "truth" not in inspect.signature(seismic.invert_observations).parameters


def test_withheld_samples_do_not_influence_inverse_and_terminal_is_saved(monkeypatch):
    # Algebraic surrogate tests bookkeeping/leakage, NOT acoustic correctness.
    def algebraic(v, frequency=8., receivers=10, nt=256, *args, **kwargs):
        trace = torch.linspace(.1, 1., nt, device=v.device)
        return (v.mean()/2000)*trace[None, None].expand(3, receivers, nt)
    monkeypatch.setattr(seismic, "simulate", algebraic)
    start = torch.tensor(seismic.independent_start())
    obs = algebraic(start)*1.02
    active = torch.arange(10)%5 != 2
    changed = obs.clone()
    changed[:, ~active] *= 100
    with torch.no_grad():
        assert not torch.equal(obs, changed)
    first, _ = seismic.invert_observations(obs, start, active=active, iterations=1)
    second, _ = seismic.invert_observations(changed, start, active=active, iterations=1)
    for key, result in first.items():
        np.testing.assert_array_equal(result['model_tensor'].numpy(), second[key]['model_tensor'].numpy())
        identity = result['state_identity']
        np.testing.assert_array_equal(result['model_tensor'].numpy().T, result['frames'][identity['final_frame_index']])
        assert result['frame_history_indices'][-1] == identity['selected_iteration']
        assert result['history_records'][-1]['update'] == 1
        assert result['solver']['terminal_update_evaluated']
        assert result['history'][-1] == pytest.approx(float(seismic._relative_mse(result['predicted_tensor'], obs)))


def test_failed_and_negative_control_outcomes_are_not_relabelled_success():
    metrics = dict(model_rmse_ratio=1.1, active_relative_mse=.01, initial_active_relative_mse=.2,
                   withheld_relative_mse=.02, initial_withheld_relative_mse=.3)
    assert seismic.recovery_evaluation(metrics)['status'] == 'failed'
    result = seismic.recovery_evaluation(metrics, challenge=True)
    assert result['status'] == 'negative-control'
    assert 'whole_model_not_improved' in result['reason_codes']
    assert 'salt_cycle_skipping_challenge' in result['reason_codes']


def test_model_region_and_withheld_metrics_against_direct_arrays():
    truth = np.full((128, 96), 2400.)
    initial = np.full_like(truth, 2100.)
    model = truth.copy()
    model[:, :24] -= 40
    model[:, 24:48] += 80
    model[:, 48:] -= 120
    observed = torch.ones(3, 10, 128, dtype=torch.float64)
    initial_predicted = observed*.8
    predicted = observed*.98
    active = torch.arange(10)%5 != 2
    predicted[:, ~active] = .96
    metrics = seismic.recovery_metrics(model, truth, initial, predicted, observed, initial_predicted, active, .01)
    assert metrics['initial_velocity_rmse'] == 300
    assert metrics['velocity_rmse'] == pytest.approx(np.sqrt(np.mean((model-truth)**2)))
    assert metrics['model_rmse_ratio'] == pytest.approx(metrics['velocity_rmse']/300)
    assert metrics['velocity_bias'] == pytest.approx(np.mean(model-truth))
    assert metrics['shallow_rmse'] == 40
    assert metrics['middle_rmse'] == 80
    assert metrics['deep_rmse'] == 120
    assert metrics['active_wrms'] == pytest.approx(2)
    assert metrics['withheld_wrms'] == pytest.approx(4)
    assert metrics['active_relative_mse'] == pytest.approx(.0004)
    assert metrics['withheld_relative_mse'] == pytest.approx(.0016)
    assert metrics['initial_withheld_relative_mse'] == pytest.approx(.04)


def test_batch_fresh_prepare_needs_no_ignored_reference_files(tmp_path, monkeypatch):
    import seismic_batch as batch
    monkeypatch.setattr(batch, 'EXPERIMENTS', tmp_path)
    monkeypatch.setattr(batch, 'CANDIDATE', tmp_path/'candidate')
    monkeypatch.setattr(batch, 'PLAN', tmp_path/'receipts/plan.json')
    batch.prepare()
    plan = json.loads(batch.PLAN.read_text())
    assert len(plan['jobs']) == 24
    assert len({(j['case']['id'], j['variant']) for j in plan['jobs']}) == 24
    assert plan['reference_reuse'] == []
    assert plan['controls']['iterations_per_stage'] == 28
    assert not batch.CANDIDATE.exists(), 'Preparation must not fabricate result files'
    assert not (tmp_path/'catalog.json').exists()


def test_batch_rejects_canonical_target_and_missing_gpu_handoff(tmp_path, monkeypatch):
    import seismic_batch as batch
    import sys
    for name in ('CANDIDATE', 'RECEIPTS', 'PLAN', 'LEDGER', 'MEMORY_LOG'):
        monkeypatch.setattr(batch, name, getattr(batch, name))
    monkeypatch.setattr(batch, 'EXPERIMENTS', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['seismic_batch.py', 'prepare', '--output', str(tmp_path.parent/'canonical')])
    with pytest.raises(SystemExit) as exc:
        batch.main()
    assert exc.value.code == 2
    monkeypatch.setattr(sys, 'argv', ['seismic_batch.py', 'run', '--output', str(tmp_path/'candidate'),
                                    '--receipts', str(tmp_path/'receipts')])
    with pytest.raises(SystemExit) as exc:
        batch.main()
    assert exc.value.code == 2
    assert not (tmp_path/'candidate').exists()


def test_batch_resume_rejects_changed_fingerprint_or_reduced_budget(tmp_path):
    import seismic_batch as batch
    path = tmp_path/'FWI_LAYERED'/'noise.json'
    path.parent.mkdir()
    method = dict(model=[[1800.]], frames=[[[1800.]]],
                  state_identity=dict(final_frame_index=0),
                  solver=dict(optimizer_calls=112, terminal_update_evaluated=True),
                  evaluation=dict(status='recovered'))
    result = dict(id='FWI_LAYERED', variant='noise', provenance=dict(generator_fingerprint='frozen'),
                  parameters=dict(iterations=28), methods={'fwi-l2':method, 'fwi-multiscale':method})
    path.write_text(json.dumps(result))
    assert batch.complete(path, 'frozen')
    assert not batch.complete(path, 'different')
    result['parameters']['iterations'] = 7
    path.write_text(json.dumps(result))
    assert not batch.complete(path, 'frozen')


@pytest.mark.parametrize('case_id', ['FWI_LAYERED', 'FWI_FAULT', 'FWI_NOISY', 'FWI_CYCLE_SKIP'])
def test_reference_recovery_state_and_forward_replay(case_id):
    assert torch.cuda.is_available(), 'Scientific release gate requires actual CUDA execution'
    torch.set_num_threads(4)
    case = next(c for c in registry() if c['id'] == case_id)
    probe_directory = os.environ.get('FWI_RECOVERY_PROBES')
    if probe_directory:
        run = json.loads((Path(probe_directory)/f'fwi-{case_id}-reference.json').read_text())
        source = (ROOT/'data-pipeline/seismic.py').read_bytes()
        digest = hashlib.sha256(source).hexdigest()
        if run['probe_solver_sha256'] != digest:
            # Explicitly authorized label-only migration. Byte equivalence proves
            # that no solver constants, operations or model selection changed.
            assert source.count(b'"negative-control"') == 1
            legacy = source.replace(b'"negative-control"', b'"expected-negative-control"')
            assert run['probe_solver_sha256'] == hashlib.sha256(legacy).hexdigest(), 'Stale scientific solver'
            for method in run['methods'].values():
                if method['evaluation']['status'] == 'expected-negative-control':
                    method['evaluation']['status'] = 'negative-control'
    else:
        run = seismic.solve_case(case, 'reference')
    truth = np.asarray(run['truth'])
    initial = np.asarray(run['initial'])
    initial_rmse = np.sqrt(np.mean((truth-initial)**2))
    with torch.no_grad():
        # Rebuild the full-rate observations to validate history as well as the 4 ms export.
        torch.manual_seed(case['seed'])
        clean = seismic.simulate(torch.tensor(truth.T, device='cuda', dtype=torch.float32),
                                 run['frequency'], nt=run['parameters']['record_samples'])
        obs = clean+torch.randn_like(clean)*run['parameters']['noise_sigma']
    for result in run['methods'].values():
        model = np.asarray(result['model'])
        rmse = np.sqrt(np.mean((model-truth)**2))
        assert result['metrics']['velocity_rmse'] == pytest.approx(rmse, rel=1e-6)
        assert result['metrics']['initial_velocity_rmse'] == pytest.approx(initial_rmse, rel=1e-6)
        if case_id != 'FWI_CYCLE_SKIP':
            assert rmse < initial_rmse, 'Nominal whole-model recovery must improve the independent start'
            assert result['evaluation']['status'] == 'recovered'
        else:
            assert result['evaluation']['status'] == 'negative-control'
        identity = result['state_identity']
        np.testing.assert_array_equal(model, result['frames'][identity['final_frame_index']])
        assert identity['predictions'] == 'final-model'
        assert result['frame_history_indices'][-1] == identity['selected_iteration']
        assert result['history_records'][-1]['update'] == run['parameters']['iterations']
        with torch.no_grad():
            pred = seismic.simulate(torch.tensor(model.T, dtype=torch.float32, device='cuda'),
                                    run['frequency'], nt=run['parameters']['record_samples'])
        np.testing.assert_allclose(pred.cpu().numpy()[:, :, ::8], result['predicted'], rtol=2e-5, atol=2e-5)
        np.testing.assert_allclose((obs-pred).cpu().numpy()[:, :, ::8], result['residual'], rtol=2e-4, atol=2e-5)
        assert result['history'][-1] == pytest.approx(float(seismic._relative_mse(pred, obs)), rel=2e-5)
        active = torch.tensor(run['active_receivers'], device='cuda')
        last = result['history_records'][-1]
        cutoff = result['solver']['cutoffs_hz'][-1]
        data_loss = (seismic.lowpass(pred, cutoff)[:, active]-seismic.lowpass(obs, cutoff)[:, active]).square().mean()
        data_loss /= seismic.lowpass(obs, cutoff)[:, active].square().mean()
        regularization = run['parameters']['regularization']*seismic.physical_roughness(torch.tensor(model.T))
        assert last['objective'] == pytest.approx(float(data_loss)+float(regularization), rel=2e-5)
        for lo, hi, region in [(0, 24, 'shallow'), (24, 48, 'middle'), (48, 96, 'deep')]:
            region_rmse = np.sqrt(np.mean((model[lo:hi]-truth[lo:hi])**2))
            assert result['metrics'][f'{region}_rmse'] == pytest.approx(region_rmse, rel=1e-6)


def test_deepwave_refined_discretization_and_adjoint():
    assert torch.cuda.is_available()
    torch.manual_seed(987)
    v = torch.tensor(seismic.independent_start(), device='cuda', dtype=torch.float64, requires_grad=True)
    target = seismic.simulate(v.detach()+80, nt=1600, receivers=12)
    def objective(model):
        pred = seismic.lowpass(seismic.simulate(model, nt=1600, receivers=12), 5.)
        return (pred-seismic.lowpass(target, 5.)).square().mean()
    loss = objective(v)
    loss.backward()
    direction = v.grad.detach()/v.grad.detach().norm()
    with torch.no_grad():
        finite = (objective(v+direction)-objective(v-direction))/2
    assert float(finite) == pytest.approx(float((v.grad*direction).sum()), rel=3e-3)
    # Accuracy-order comparison is an independent stencil, not independent software.
    with torch.no_grad():
        fourth = seismic.simulate(v.detach(), nt=1600, receivers=12, accuracy=4)
        eighth = seismic.simulate(v.detach(), nt=1600, receivers=12, accuracy=8)
    relative = float((fourth-eighth).norm()/eighth.norm())
    assert relative < .02
