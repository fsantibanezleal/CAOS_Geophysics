"""Bounded multiresolution finite-difference FWI; truth never enters the inverse."""
from __future__ import annotations

from importlib.metadata import version
import time

import deepwave
import numpy as np
import torch
import torch.nn.functional as F

from geology import seismic_model, SEISMIC_SHAPE, SEISMIC_SPACING

DT = 0.0005
RECORD_SAMPLES = 3200
VELOCITY_BOUNDS = (1400.0, 4400.0)
SOURCE_X = (300.0, 800.0, 1275.0)
SOURCE_DEPTH = 75.0
CONTROL_GRIDS = ((1, 12), (9, 12), (17, 24), (33, 48))
CUTOFFS_HZ = (3.0, 5.0, 8.0, 14.0)
DEFAULT_ITERATIONS = 28  # optimizer calls per spatial stage, four stages
CALIBRATION_ID = "dipping-three-layer-smooth-perturbation-67031"


def independent_start(shape=SEISMIC_SHAPE, spacing=SEISMIC_SPACING):
    """Fixed trend in physical units, with no geological input."""
    return np.broadcast_to(1800 + np.arange(shape[1])*spacing*.88, shape).copy().astype(np.float32)


def simulate(v, frequency=8.0, receivers=40, nt=2200, callback=None, *,
             spacing=SEISMIC_SPACING, dt=DT, accuracy=4, source_x=SOURCE_X,
             receiver_x=None, gradient_sampling=1):
    """Return [shot,receiver,time] for [x,z] velocity, retaining legacy defaults.

    Physical acquisition coordinates and 300 m PML are invariant under mesh
    refinement. Source amplitudes retain the engine's point-source convention.
    """
    if not (frequency > 0 and dt > 0 and spacing > 0 and nt > 0):
        raise ValueError("Positive frequency, time step, spacing and sample count required")
    device = v.device
    sources_at = torch.tensor(
        [[[int(x/spacing), int(SOURCE_DEPTH/spacing)]] for x in source_x], device=device)
    if receiver_x is None:
        receiver_x = (torch.linspace(6, 120, receivers).long()*SEISMIC_SPACING).tolist()
    rx = torch.tensor([int(x/spacing) for x in receiver_x], device=device)
    receivers_at = torch.stack((rx, torch.full_like(rx, int(SOURCE_DEPTH/spacing))), dim=-1)
    receivers_at = receivers_at[None].repeat(len(source_x), 1, 1)
    if sources_at[..., 0].max() >= v.shape[0] or rx.max() >= v.shape[0] or sources_at[..., 1].max() >= v.shape[1]:
        raise ValueError("Acquisition lies outside velocity mesh")
    t = torch.arange(nt, device=device, dtype=v.dtype)*dt
    a = np.pi*frequency*(t-1.5/frequency)
    wavelet = (1-2*a*a)*torch.exp(-a*a)
    sources = wavelet[None, None].repeat(len(source_x), 1, 1)
    return deepwave.scalar(
        v, spacing, dt, source_amplitudes=sources, source_locations=sources_at,
        receiver_locations=receivers_at, pml_width=round(300/spacing),
        pml_freq=frequency, accuracy=accuracy, max_vel=4600,
        model_gradient_sampling_interval=gradient_sampling,
        forward_callback=callback, callback_frequency=max(1, round(.024/dt)))[-1]


def lowpass(x, cutoff_hz, dt=DT, order=6):
    """Differentiable zero-phase FFT Butterworth amplitude, padded to >=2N.

    H(f)=[1+(f/fc)^(2p)]^(-1/2), not a causal IIR or squared filtfilt response.
    Edge conditions are zero extension, applied identically to both traces.
    """
    if cutoff_hz is None:
        return x
    if not (0 < cutoff_hz < .5/dt) or order < 1:
        raise ValueError("Cutoff must lie between zero and Nyquist; order must be positive")
    n = x.shape[-1]
    nfft = 1 << (2*n-1).bit_length()
    frequencies = torch.fft.rfftfreq(nfft, dt, device=x.device, dtype=x.dtype)
    gain = (1+(frequencies/cutoff_hz).pow(2*order)).rsqrt()
    return torch.fft.irfft(torch.fft.rfft(x, n=nfft)*gain, n=nfft)[..., :n]


def physical_roughness(v, spacing=SEISMIC_SPACING):
    """Mean squared gradient with velocity/length scales 1000 m/s and 100 m."""
    return ((v[:, 1:]-v[:, :-1]).square().mean()
            + (v[1:]-v[:-1]).square().mean())/(10*spacing)**2


def _control_model(parameter, shape):
    lower, upper = VELOCITY_BOUNDS
    q = F.interpolate(parameter[None, None], size=shape, mode="bilinear", align_corners=True)[0, 0]
    return lower+(upper-lower)*torch.sigmoid(q)


def _parameterize(v, grid):
    lower, upper = VELOCITY_BOUNDS
    q = torch.logit(((v-lower)/(upper-lower)).clamp(.0001, .9999))
    q = F.interpolate(q[None, None], size=grid, mode="bilinear", align_corners=True)[0, 0]
    return torch.nn.Parameter(q.clone())


def _relative_mse(pred, observed):
    return (pred-observed).square().mean()/observed.square().mean().clamp_min(1e-20)


def _run_stage(current, observed, active, frequency, grid, cutoff, beta, iterations, *, progress=None):
    parameter = _parameterize(current, grid)
    optimizer = torch.optim.LBFGS(
        [parameter], lr=1., max_iter=1, history_size=15,
        line_search_fn="strong_wolfe", tolerance_grad=1e-8, tolerance_change=1e-10)
    target = lowpass(observed, cutoff)
    scale = target[:, active].square().mean().clamp_min(1e-20)
    records, frames, frame_indices = [], [], []
    closure_count = 0
    start = time.perf_counter()

    def closure():
        nonlocal closure_count
        closure_count += 1
        optimizer.zero_grad()
        v = _control_model(parameter, current.shape)
        pred = simulate(v, frequency, observed.shape[1], observed.shape[-1])
        data = (lowpass(pred, cutoff)[:, active]-target[:, active]).square().mean()/scale
        loss = data+beta*physical_roughness(v)
        if not torch.isfinite(loss):
            raise FloatingPointError("Nonfinite FWI objective")
        loss.backward()
        return loss

    # Evaluate every state AFTER its update, including the terminal one.
    for iteration in range(iterations+1):
        if iteration:
            optimizer.step(closure)
        with torch.no_grad():
            v = _control_model(parameter, current.shape)
            pred = simulate(v, frequency, observed.shape[1], observed.shape[-1])
            data = (lowpass(pred, cutoff)[:, active]-target[:, active]).square().mean()/scale
            roughness = physical_roughness(v)
            record = dict(
                update=iteration, control_grid=list(grid), cutoff_hz=cutoff,
                data_objective=float(data), regularization=float(beta*roughness),
                objective=float(data+beta*roughness), relative_mse=float(_relative_mse(pred, observed)),
                active_relative_mse=float(_relative_mse(pred[:, active], observed[:, active])),
                withheld_relative_mse=float(_relative_mse(pred[:, ~active], observed[:, ~active])))
            records.append(record)
            if iteration % 4 == 0 or iteration == iterations:
                frames.append(v.cpu().numpy().T.tolist())
                frame_indices.append(len(records)-1)
        if progress and (iteration % 8 == 0 or iteration == iterations):
            progress(dict(**record, closure_evaluations=closure_count, seconds=time.perf_counter()-start))
    return v.detach(), records, frames, frame_indices, closure_count


def invert_observations(observed, initial, frequency=8., *, iterations=DEFAULT_ITERATIONS,
                        beta=.001, active=None, progress=None):
    """Fit matched FWI schedules; there is deliberately no truth argument.

    Shared data-only 3 Hz 1D background; then equal 2D grids, priors, data and
    optimizer-call budgets. Only the 2D frequency schedule differs. Withheld
    samples do not select a state, schedule or stopping time.
    """
    if iterations < 1:
        raise ValueError("At least one optimizer call per stage is required")
    if observed.ndim != 3 or not torch.isfinite(observed).all():
        raise ValueError("Finite [shot,receiver,time] observations required")
    if tuple(initial.shape) != SEISMIC_SHAPE:
        raise ValueError("Canonical inverse mesh must remain 128 by 96")
    if active is None:
        active = torch.arange(observed.shape[1], device=observed.device) % 5 != 2
    if active.dtype != torch.bool or not active.any() or active.all():
        raise ValueError("Both fitted and withheld receivers are required")
    with torch.no_grad():
        initial_pred = simulate(initial, frequency, observed.shape[1], observed.shape[-1])
    background, bg_records, bg_frames, bg_indices, bg_calls = _run_stage(
        initial, observed, active, frequency, CONTROL_GRIDS[0], CUTOFFS_HZ[0], beta, iterations,
        progress=progress)
    methods = {}
    for continuation in (False, True):
        current = background.clone()
        records = [dict(r, phase="background") for r in bg_records]
        frames, frame_indices = list(bg_frames), list(bg_indices)
        closure_evaluations = bg_calls
        for stage in range(1, len(CONTROL_GRIDS)):
            cutoff = CUTOFFS_HZ[stage] if continuation else None
            current, new_records, new_frames, new_indices, calls = _run_stage(
                current, observed, active, frequency, CONTROL_GRIDS[stage], cutoff, beta, iterations,
                progress=progress)
            frame_indices.extend([len(records)+i for i in new_indices])
            records.extend([dict(r, phase=f"spatial-{stage}") for r in new_records])
            frames.extend(new_frames)
            closure_evaluations += calls
        with torch.no_grad():
            final_pred = simulate(current, frequency, observed.shape[1], observed.shape[-1])
        key = "fwi-multiscale" if continuation else "fwi-l2"
        methods[key] = dict(
            model_tensor=current, predicted_tensor=final_pred, initial_prediction_tensor=initial_pred,
            background_tensor=background, history=[r["relative_mse"] for r in records],
            history_records=records, frames=frames, frame_history_indices=frame_indices,
            frame_indices=frame_indices,
            state_identity=dict(final_frame_index=len(frames)-1, selected_iteration=len(records)-1,
                                frame_quantity="velocity_m_s", predictions="final-model"),
            solver=dict(
                optimizer="L-BFGS with strong-Wolfe line search", stopping="finite_budget",
                iterations_per_stage=iterations, optimizer_calls=iterations*len(CONTROL_GRIDS),
                closure_evaluations=closure_evaluations, terminal_update_evaluated=True,
                selected_state="terminal evaluated state", bounds_m_s=list(VELOCITY_BOUNDS),
                control_grids=[list(g) for g in CONTROL_GRIDS],
                cutoffs_hz=list(CUTOFFS_HZ) if continuation else [3., None, None, None],
                filter="zero-padded zero-phase order-6 Butterworth amplitude in FFT domain",
                beta=beta, regularizer="mean squared physical velocity gradient; scales 1000 m/s and 100 m",
                calibration_id=CALIBRATION_ID, truth_used_by_inverse=False,
                matched_comparison="shared data-only 1D background; equal spatial grids, priors and optimizer calls"))
    return methods, active


def recovery_metrics(model, truth, initial, predicted, observed, initial_predicted, active, sigma):
    """Independent diagnostics, none used by the inverse or model selection."""
    def rmse(a, b):
        return float(np.sqrt(np.mean((a-b)**2)))
    initial_rmse = rmse(initial, truth)
    final_rmse = rmse(model, truth)
    metrics = dict(
        initial_velocity_rmse=initial_rmse, velocity_rmse=final_rmse,
        model_rmse_ratio=final_rmse/max(initial_rmse, 1e-20),
        initial_relative_mse=float(_relative_mse(initial_predicted, observed)),
        relative_mse=float(_relative_mse(predicted, observed)),
        velocity_bias=float(np.mean(model-truth)), velocity_min=float(model.min()),
        velocity_max=float(model.max()), bound_fraction=float(np.mean((model < 1401) | (model > 4399))))
    for name, mask in (("active", active), ("withheld", ~active)):
        error = predicted[:, mask]-observed[:, mask]
        metrics[f"{name}_wrms"] = float(error.square().mean().sqrt()/max(sigma, 1e-20))
        metrics[f"{name}_relative_mse"] = float(_relative_mse(predicted[:, mask], observed[:, mask]))
        metrics[f"initial_{name}_relative_mse"] = float(_relative_mse(initial_predicted[:, mask], observed[:, mask]))
    z = np.arange(truth.shape[1])*SEISMIC_SPACING
    for name, mask in (("shallow", z < 300), ("middle", (z >= 300) & (z < 600)), ("deep", z >= 600)):
        metrics[f"{name}_initial_rmse"] = rmse(initial[:, mask], truth[:, mask])
        metrics[f"{name}_rmse"] = rmse(model[:, mask], truth[:, mask])
    anomalous = np.abs(truth-initial) >= 200
    for name, mask in (("departure", anomalous), ("background", ~anomalous)):
        if np.any(mask):
            metrics[f"{name}_initial_rmse"] = rmse(initial[mask], truth[mask])
            metrics[f"{name}_rmse"] = rmse(model[mask], truth[mask])
    return metrics


def recovery_evaluation(metrics, challenge=False):
    reasons = []
    if metrics["model_rmse_ratio"] >= 1:
        reasons.append("whole_model_not_improved")
    if metrics["active_relative_mse"] >= metrics["initial_active_relative_mse"]:
        reasons.append("waveform_not_improved")
    if metrics["withheld_relative_mse"] >= metrics["initial_withheld_relative_mse"]:
        reasons.append("withheld_data_not_improved")
    status = "failed" if reasons else "recovered"
    if challenge:
        status = "negative-control"
        reasons.append("salt_cycle_skipping_challenge")
    return dict(status=status, reason_codes=reasons,
                criterion="whole-model, active waveform and withheld waveform improve the independent start",
                scope="synthetic baseline improvement, not exact geology or field validation",
                optimizer_status="finite_budget")


def solve_case(case, variant, iterations=DEFAULT_ITERATIONS, *, progress=None):
    started = time.perf_counter()
    torch.manual_seed(case["seed"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    truth = seismic_model(case["geometry"], 1.15 if variant == "contrast" else 1)
    initial = independent_start()
    frequency = 5. if variant == "acquisition" else (9. if case["geometry"] == "salt" else 8.)
    receivers = 20 if variant == "coverage" else 40
    snapshots = []

    def callback(state):
        snapshots.append(state.get_wavefield("wavefield_0")[1].detach().cpu().numpy().T.tolist())

    with torch.no_grad():
        clean = simulate(torch.tensor(truth, device=device), frequency, receivers, RECORD_SAMPLES, callback)
        noise = .08 if variant == "noise" else .01
        sigma = float(clean.std())*noise
        observed = clean+torch.randn_like(clean)*sigma
    beta = .03 if variant == "regularization" else .001
    outputs, active = invert_observations(
        observed, torch.tensor(initial, device=device), frequency, iterations=iterations, beta=beta,
        progress=progress)
    methods = {}
    for key, output in outputs.items():
        model = output.pop("model_tensor").cpu().numpy()
        predicted = output.pop("predicted_tensor")
        initial_predicted = output.pop("initial_prediction_tensor")
        background = output.pop("background_tensor").cpu().numpy()
        metrics = recovery_metrics(model, truth, initial, predicted, observed, initial_predicted, active, sigma)
        continuation = key == "fwi-multiscale"
        methods[key] = dict(
            **output, name="Frequency-continuation acoustic FWI" if continuation else "Full-band acoustic FWI",
            name_es="FWI acústica con continuación en frecuencia" if continuation else "FWI acústica de banda completa",
            model=model.T.tolist(), background_model=background.T.tolist(),
            predicted=predicted.cpu().numpy()[:, :, ::8].tolist(),
            residual=(observed-predicted).cpu().numpy()[:, :, ::8].tolist(),
            metrics=metrics, evaluation=recovery_evaluation(metrics, case["geometry"] == "salt"), device=device,
            target=dict(quantity="acoustic velocity", units="m/s", dimensionality="2D [depth,distance]",
                        provenance="synthetic known velocity; not measured field truth"))
    return dict(
        schema="inverse-earth/v2", **case, variant=variant,
        engine=f"Deepwave {version('deepwave')} / PyTorch automatic differentiation",
        lane="computed replay", units="m/s", data_units="amplitude",
        truth=truth.T.tolist(), initial=initial.T.tolist(), observed=observed.cpu().numpy()[:, :, ::8].tolist(),
        wavefields=snapshots, grid=dict(shape=[96, 128], spacing=[12.5, 12.5]),
        dt=.004, wavefield_dt=.024, frequency=frequency,
        sources=[[x, SOURCE_DEPTH] for x in SOURCE_X],
        receivers=(torch.linspace(6, 120, receivers).long()*12.5).tolist(), methods=methods,
        active_receivers=active.cpu().tolist(),
        parameters=dict(
            frequency_hz=frequency, noise_fraction=noise, noise_sigma=sigma,
            receivers=receivers, regularization=beta, iterations=iterations,
            iterations_semantics="maximum L-BFGS calls per spatial stage (four stages)",
            internal_dt=DT, record_samples=RECORD_SAMPLES, record_duration_s=RECORD_SAMPLES*DT,
            spatial_accuracy=4, pml_thickness_m=300, calibration_id=CALIBRATION_ID,
            data_origin="same-operator synthetic pressure, independent additive Gaussian noise",
            withheld_policy="receiver index modulo 5 equals 2, excluded from objectives and state selection",
            initial_policy="independent 1800 + 0.88 z m/s trend, then data-only 1D background",
            runtime_seconds=time.perf_counter()-started))
