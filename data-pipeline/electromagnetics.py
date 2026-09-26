"""CPU layered-earth MT: matched objectives, explicit states and conditional uncertainty.

Plain module imported by scripts; no package installation. E/H impedance is in ohm,
rho in ohm m, thickness in m, frequencies in Hz, exp(+i omega t) convention.
"""
from __future__ import annotations

import hashlib
import numpy as np
from scipy.optimize import least_squares
import torch

from geology import mt_model

MU = 4e-7 * np.pi
MT_BOUNDS = (1.0, 6000.0)
METHODS = ("mt-lm", "mt-adam", "mt-neural")
OBJECTIVE_DEFINITION = (
    "J = sum_active((Re(dZ)/sigma)^2+(Im(dZ)/sigma)^2)/(2*N_active)"
    " + beta*sum(diff(log(rho))^2)/(N_layers-1); prior=0 for one layer"
)


def impedance(rho, thickness, frequencies):
    """Quasi-static isotropic 1D plane-wave recursion; bottom layer is infinite."""
    rho, thickness, frequencies = map(lambda a: np.asarray(a, dtype=float), (rho, thickness, frequencies))
    if rho.ndim != 1 or not len(rho) or thickness.shape != (len(rho)-1,):
        raise ValueError("Require n resistivities and n-1 finite-layer thicknesses")
    if frequencies.ndim != 1 or not len(frequencies):
        raise ValueError("Frequencies must be a nonempty vector")
    for values in (rho, thickness, frequencies):
        if not np.isfinite(values).all() or np.any(values <= 0):
            raise ValueError("Resistivity, thickness and frequency must be finite and positive")
    omega = 2*np.pi*frequencies
    z = np.sqrt(1j*omega*MU*rho[-1])
    for j in range(len(rho)-2, -1, -1):
        k = np.sqrt(1j*omega*MU/rho[j])
        w = np.sqrt(1j*omega*MU*rho[j])
        t = np.tanh(k*thickness[j])
        z = w*(z+w*t)/(w+z*t)
    return z


def torch_impedance(logrho, thickness, frequencies):
    rho = logrho.exp()
    omega = 2*np.pi*frequencies
    z = torch.sqrt(1j*omega*MU*rho[-1])
    for j in range(len(rho)-2, -1, -1):
        k = torch.sqrt(1j*omega*MU/rho[j])
        w = torch.sqrt(1j*omega*MU*rho[j])
        t = torch.tanh(k*thickness[j])
        z = w*(z+w*t)/(w+z*t)
    return z


def curves(z, f):
    z, f = np.asarray(z), np.asarray(f)
    return dict(real=z.real.tolist(), imag=z.imag.tolist(),
                apparent=(abs(z)**2/(MU*2*np.pi*f)).tolist(), phase=np.angle(z, deg=True).tolist())


def objective_residual(logrho, thickness, frequencies, observed, sigma, beta, active=None):
    """Squared Euclidean norm is J, not SciPy's half-sum cost."""
    f, obs, sig = np.asarray(frequencies), np.asarray(observed), np.asarray(sigma)
    mask = np.ones(len(f), dtype=bool) if active is None else np.asarray(active, dtype=bool)
    r = (impedance(np.exp(logrho), thickness, f)[mask]-obs[mask])/sig[mask]
    data = np.r_[r.real, r.imag]/np.sqrt(2*mask.sum())
    prior = np.sqrt(beta/max(len(logrho)-1, 1))*np.diff(logrho)
    return np.r_[data, prior]


def torch_objective(logrho, thickness, frequencies, observed, sigma, beta, active=None):
    """Same real-component mean and layer-difference mean as objective_residual."""
    pred = torch_impedance(logrho, thickness, frequencies)
    mask = torch.ones_like(frequencies, dtype=torch.bool) if active is None else active
    r = (pred[mask]-observed[mask])/sigma[mask]
    prior = beta*torch.diff(logrho).square().mean() if logrho.numel() > 1 else logrho.sum()*0
    return r.abs().square().mean()/2 + prior


def _validate(thickness, frequencies, observed, sigma, active, initial, beta, bounds):
    f, h = np.asarray(frequencies, dtype=float), np.asarray(thickness, dtype=float)
    obs, sig = np.asarray(observed, dtype=complex), np.asarray(sigma, dtype=float)
    if f.ndim != 1 or obs.shape != f.shape or sig.shape != f.shape or len(f) == 0:
        raise ValueError("Frequency, observation and sigma vectors must have the same nonzero length")
    if not np.isfinite(obs).all() or not np.isfinite(sig).all() or np.any(sig <= 0):
        raise ValueError("Finite complex observations and positive per-real-component sigma are required")
    if len(np.unique(f)) != len(f):
        raise ValueError("Frequencies must be unique")
    mask = np.ones(len(f), dtype=bool) if active is None else np.asarray(active)
    if mask.shape != f.shape or mask.dtype != bool or not mask.any():
        raise ValueError("Active mask must be boolean with at least one fitted frequency")
    bounds = np.asarray(bounds, dtype=float)
    if bounds.shape != (2,) or not np.isfinite(bounds).all() or not 0 < bounds[0] < bounds[1]:
        raise ValueError("Bounds must be two ordered positive resistivities")
    start = np.full(len(h)+1, 100.) if initial is None else np.asarray(initial, dtype=float).copy()
    impedance(start, h, f)
    if np.any(start <= bounds[0]) or np.any(start >= bounds[1]):
        raise ValueError("Initial resistivities must be strictly inside the common bounds")
    if not np.isfinite(beta) or beta < 0:
        raise ValueError("Regularization weight must be finite and nonnegative")
    return h, f, obs, sig, mask, start, bounds


def identifiability(model, thickness, frequencies, sigma, active, bounds=MT_BOUNDS):
    """Data-only local linear sensitivity, not posterior or global uniqueness."""
    x = np.log(model)
    f, sig, mask = np.asarray(frequencies), np.asarray(sigma), np.asarray(active)
    jac = []
    for j in range(len(x)):
        delta = np.zeros(len(x))
        delta[j] = 1e-5
        dz = (impedance(np.exp(x+delta), thickness, f)-impedance(np.exp(x-delta), thickness, f))/(2e-5)
        r = dz[mask]/sig[mask]
        jac.append(np.r_[r.real, r.imag])
    jac = np.asarray(jac).T
    _, singular, vt = np.linalg.svd(jac, full_matrices=True)
    # A unit log-rho perturbation along a weak direction produces <=1 noise unit
    # or <0.1% of the best-resolved direction. Thresholds are declared, not tuned.
    threshold = max(1., float(singular[0])*1e-3)
    rank = int(np.sum(singular > threshold))
    weak_participation = np.sum(vt[rank:]**2, axis=0)
    numerical_rank = int(np.sum(singular > max(float(singular[0])*1e-10, 1e-12)))
    covariance = (vt[:numerical_rank].T/(singular[:numerical_rank]**2)) @ vt[:numerical_rank]
    local_sd = np.sqrt(np.maximum(0, np.diag(covariance)))
    near_bound = (x-np.log(bounds[0]) < .01) | (np.log(bounds[1])-x < .01)
    weak = (weak_participation > .1) | (local_sd > np.log(2)) | near_bound
    return dict(
        kind="data-only local linearized identifiability, conditional on fixed thickness",
        singular_values=singular.tolist(), effective_rank=rank, parameter_count=len(x),
        singular_threshold=threshold, numerical_rank=numerical_rank,
        condition_number=float(singular[0]/singular[-1]) if len(singular) == len(x) and singular[-1] > 1e-12 else None,
        local_logrho_sd=local_sd.tolist(), weak_direction_participation=weak_participation.tolist(),
        near_bound=near_bound.tolist(), unresolved_layers=np.flatnonzero(weak).tolist(),
        status="unresolved" if weak.any() or rank < len(x) else "locally_resolved",
        caveat="Linearization excludes thickness, dimensionality, correlated noise and static-shift uncertainty; not a uniqueness proof.",
    )


def _model_hash(model):
    return hashlib.sha256(np.asarray(model, dtype="<f8").tobytes()).hexdigest()


def invert_mt(thickness, frequencies, observed, sigma, *, active=None, initial=None,
              beta=.001, bounds=MT_BOUNDS, methods=METHODS, seed=0,
              adam_steps=1200, neural_steps=1800, max_nfev=400, record_every=20):
    """Fit one sounding on CPU without access to any true resistivity.

    Legacy key mt-lm remains for v2 compatibility; the actual solver is bounded TRF.
    Saved TRF residual evaluations can include rejected trials (explicitly labelled).
    All final selected models are appended as last frames with re-evaluated losses.
    """
    h, f, obs, sig, mask, initial, bounds = _validate(
        thickness, frequencies, observed, sigma, active, initial, beta, bounds)
    methods = tuple(methods)
    if not methods or len(set(methods)) != len(methods) or any(m not in METHODS for m in methods):
        raise ValueError("Select distinct implemented MT method keys")
    if min(adam_steps, neural_steps, max_nfev, record_every) < 1:
        raise ValueError("Solver budgets and recording interval must be positive")
    logbounds = np.log(bounds)
    x0 = np.log(initial)
    n = int(mask.sum())
    output = {}
    initial_prediction = impedance(initial, h, f)

    def evaluate(model):
        # Always evaluate the serialized physical model, never a mutable Parameter alias.
        residual = objective_residual(np.log(model), h, f, obs, sig, beta, mask)
        data = float(np.sum(residual[:2*n]**2))
        prior = float(np.sum(residual[2*n:]**2))
        return dict(total=data+prior, data=data, regularization=prior)

    for key in methods:
        frames, history, states = [], [], []

        def record(model, step, kind):
            model = np.clip(np.asarray(model, dtype=float), bounds[0], bounds[1]).copy()
            value = evaluate(model)
            frames.append(model.tolist())
            history.append(value["total"])
            states.append(dict(frame_index=len(frames)-1, step=int(step), kind=kind, objective=value))
            return value["total"]

        record(initial, 0, "initial")
        if key == "mt-lm":
            calls = 0
            call_indices = {}

            def residual(x):
                nonlocal calls
                calls += 1
                call_indices[tuple(x)] = calls
                model = np.exp(x)
                if np.linalg.norm(np.log(frames[-1])-x) > 1e-5:
                    record(model, calls, "residual_evaluation_not_accepted_iteration")
                return objective_residual(x, h, f, obs, sig, beta, mask)

            fit = least_squares(residual, x0, bounds=logbounds, method="trf",
                                max_nfev=max_nfev, ftol=1e-10, xtol=1e-10, gtol=1e-10)
            selected = np.clip(np.exp(fit.x), bounds[0], bounds[1])
            selected_step = call_indices[tuple(fit.x)]
            settings = dict(algorithm="scipy.optimize.least_squares(method=trf)",
                            max_nfev=max_nfev, nfev=int(fit.nfev), residual_calls=calls,
                            scipy_cost_multiplier_to_J=2, success=bool(fit.success),
                            stop_reason=str(fit.message), status=int(fit.status),
                            optimality=float(fit.optimality),
                            tolerance=dict(ftol=1e-10, xtol=1e-10, gtol=1e-10))
        else:
            # All tensors are explicitly CPU; this tiny solve must not contend with FWI.
            tf, th, sigt = [torch.tensor(v, dtype=torch.float64, device="cpu") for v in (f, h, sig)]
            obst = torch.tensor(obs, dtype=torch.complex128, device="cpu")
            mt = torch.tensor(mask, dtype=torch.bool, device="cpu")
            neural = key == "mt-neural"
            if neural:
                # Fork CPU RNG only and restore it, so sounding order does not affect other pipelines.
                with torch.random.fork_rng(devices=[]):
                    torch.random.default_generator.manual_seed(int(seed))
                    net = torch.nn.Sequential(
                        torch.nn.Linear(1, 24), torch.nn.Tanh(),
                        torch.nn.Linear(24, 24), torch.nn.Tanh(), torch.nn.Linear(24, 1),
                    ).double().cpu()
                torch.nn.init.zeros_(net[-1].weight)
                torch.nn.init.zeros_(net[-1].bias)
                nodes = torch.linspace(0, 1, len(initial), dtype=torch.float64, device="cpu")[:, None]
                p0 = (x0-logbounds[0])/(logbounds[1]-logbounds[0])
                offset = torch.tensor(np.log(p0/(1-p0)), dtype=torch.float64, device="cpu")

                def get_log():
                    return logbounds[0] + (logbounds[1]-logbounds[0])*torch.sigmoid(offset+net(nodes).squeeze(-1))
                params = list(net.parameters())
            else:
                param = torch.nn.Parameter(torch.tensor(x0, dtype=torch.float64, device="cpu"))
                params = [param]

                def get_log():
                    return param

            steps = neural_steps if neural else adam_steps
            lr = .015 if neural else .06
            optim = torch.optim.Adam(params, lr=lr)
            selected, best = initial.copy(), evaluate(initial)["total"]
            selected_step = 0
            finite = True
            for step in range(1, steps+1):
                # Fixed schedule is independent of true-model error.
                for group in optim.param_groups:
                    group["lr"] = lr*(.25 if step > 3*steps//4 else .5 if step > steps//2 else 1)
                optim.zero_grad()
                loss = torch_objective(get_log(), th, tf, obst, sigt, beta, mt)
                if not torch.isfinite(loss):
                    finite = False
                    break
                loss.backward()
                optim.step()
                with torch.no_grad():
                    if not neural:
                        param.clamp_(float(logbounds[0]), float(logbounds[1]))
                    candidate = np.clip(get_log().exp().detach().cpu().numpy(), bounds[0], bounds[1]).copy()
                # Evaluate AFTER the update using its own copied model. This fixes the alias bug.
                value = evaluate(candidate)["total"]
                if not np.isfinite(value):
                    finite = False
                    break
                if value < best:
                    best, selected, selected_step = value, candidate.copy(), step
                if step % record_every == 0 or step == steps:
                    record(candidate, step, "post_update")
            settings = dict(
                algorithm="Adam on bounded per-sounding neural parameters" if neural else "projected Adam on log resistivity",
                max_steps=steps, completed_steps=step, learning_rate=lr,
                learning_rate_schedule="1, 1/2, 1/4 at 0%, 50%, 75% of fixed budget",
                success=finite, converged=False,
                stop_reason="fixed_iteration_budget" if finite else "nonfinite_objective",
                seed=int(seed), parameterization="1-24-24-1 tanh; bounded sigmoid residual about common initial model" if neural else "clamped log resistivity",
            )
        record(selected, selected_step, "selected_final")
        pred = impedance(selected, h, f)
        r = (pred-obs)/sig
        r0 = (initial_prediction-obs)/sig
        diag = identifiability(selected, h, f, sig, mask, bounds)
        active_wrms = float(np.sqrt(np.mean(abs(r[mask])**2)/2))
        metrics = dict(
            wrms=float(np.sqrt(np.mean(abs(r)**2))),  # legacy complex convention
            active_component_wrms=active_wrms,
            withheld_component_wrms=float(np.sqrt(np.mean(abs(r[~mask])**2)/2)) if (~mask).any() else None,
            initial_component_wrms=float(np.sqrt(np.mean(abs(r0[mask])**2)/2)),
            objective=history[-1], data_objective=states[-1]["objective"]["data"],
            regularization_objective=states[-1]["objective"]["regularization"],
        )
        names = {
            "mt-lm": ("Bounded complex least squares (TRF)", "Mínimos cuadrados complejos acotados (TRF)"),
            "mt-adam": ("Projected Adam impedance inversion", "Inversión de impedancia por Adam proyectado"),
            "mt-neural": ("Per-sounding physics-guided neural inversion", "Inversión neuronal física por sondeo"),
        }
        settings.update(device="cpu", dtype="float64", bounds_ohm_m=bounds.tolist(),
                        beta=float(beta), initial_model=initial.tolist(), fixed_thickness_m=h.tolist(),
                        objective=OBJECTIVE_DEFINITION, residual_normalization="mean of 2*N_active real residual squares",
                        sigma_definition="standard deviation of each independent real and imaginary part",
                        regularization_normalization="mean squared adjacent log-resistivity differences")
        output[key] = dict(
            name=names[key][0], name_es=names[key][1], model=selected.tolist(),
            predicted=curves(pred, f), residual=curves(obs-pred, f), history=history, frames=frames,
            metrics=metrics, solver=settings, states=states, device="cpu",
            state=dict(selected_frame=len(frames)-1, selected_step=selected_step,
                       model_sha256=_model_hash(selected), history_quantity="complete matched objective J",
                       model_sha256_encoding="pre-export little-endian float64 physical model",
                       final_is_last_frame=True, predictions_from="selected_final"),
            objective=dict(definition=OBJECTIVE_DEFINITION, beta=float(beta), **states[-1]["objective"]),
            identifiability=diag,
            target=dict(quantity="electrical resistivity", units="ohm m", dimensionality="1D fixed-thickness layers",
                        provenance="inverse estimate from complex impedance; truth not supplied to solver"),
            state_identity=dict(final_frame_index=len(frames)-1, selected_iteration=selected_step,
                                frame_quantity="layer resistivity in ohm m", predictions="final-model"),
            evaluation=dict(status="failed" if not settings["success"] or active_wrms > 1.5 else "unresolved",
                            reason_codes=(["solver_failure"] if not settings["success"] else [])
                            + (["data_misfit_exceeds_threshold"] if active_wrms > 1.5 else [])
                            + (["local_identifiability_weak"] if diag["status"] == "unresolved" else [])
                            + ["no_independent_geological_truth"],
                            target="fixed-thickness layer resistivity", target_units="ohm m",
                            criteria="component WRMS <=1.5, finite solve, plus data-only local identifiability; no geology truth supplied",
                            model_recovery="not_evaluated_without_independent_truth"),
        )
    return output


def _trf_only(h, f, obs, sig, mask, initial, beta, bounds, max_nfev=300):
    """No history/diagnostics overhead for resampling; same objective and bounds."""
    fit = least_squares(objective_residual, np.log(initial), bounds=np.log(bounds),
                        args=(h, f, obs, sig, beta, mask), max_nfev=max_nfev,
                        ftol=1e-10, xtol=1e-10, gtol=1e-10, method="trf")
    if not fit.success or not np.isfinite(fit.x).all():
        raise RuntimeError(f"TRF resample did not converge: {fit.message}")
    return np.clip(np.exp(fit.x), bounds[0], bounds[1])


def bootstrap_mt(model, thickness, frequencies, sigma, *, active=None, initial=None,
                 beta=.001, bounds=MT_BOUNDS, samples=128, seed=31001, confidence=.95):
    """Percentile parametric bootstrap conditional on a fitted fixed-thickness model.

    Noise is independently N(0,sigma^2) in both real components and frequencies.
    No resample-dependent sigma, posterior claim, truth-based tuning or hidden failures.
    """
    model = np.asarray(model, dtype=float)
    center = impedance(model, thickness, frequencies)
    h, f, _, sig, mask, start, bounds = _validate(
        thickness, frequencies, center, sigma, active, initial, beta, bounds)
    if len(model) != len(start) or not np.isfinite(model).all() or np.any(model < bounds[0]) or np.any(model > bounds[1]):
        raise ValueError("Conditioning model must satisfy the fitted model bounds and shape")
    if samples < 20 or not 0 < confidence < 1:
        raise ValueError("Use at least 20 bootstrap samples and confidence in (0,1)")
    sequence = np.random.SeedSequence(seed)
    seeds = [int(s.generate_state(1)[0]) for s in sequence.spawn(samples)]
    models, failures, successful_seeds = [], [], []
    for sample_seed in seeds:
        rng = np.random.default_rng(sample_seed)
        obs = center + sig*(rng.normal(size=len(f))+1j*rng.normal(size=len(f)))
        try:
            models.append(_trf_only(h, f, obs, sig, mask, start, beta, bounds).tolist())
            successful_seeds.append(sample_seed)
        except (ValueError, RuntimeError, FloatingPointError) as error:
            failures.append(dict(seed=sample_seed, error=str(error)))
    alpha = (1-confidence)/2
    intervals = np.quantile(models, [alpha, 1-alpha], axis=0).tolist() if len(models) >= 20 else None
    return dict(
        kind="conditional-parametric-bootstrap", solver="bounded TRF",
        conditioning="Selected TRF resistivity, fixed thickness, fixed independent complex-Gaussian errors, acquisition, bounds and regularization",
        members=len(models), quantiles=[alpha, 1-alpha],
        lower=intervals[0] if intervals is not None else [],
        upper=intervals[1] if intervals is not None else [],
        mean=np.mean(models, axis=0).tolist() if models else [],
        std=np.std(models, axis=0, ddof=1).tolist() if len(models) > 1 else [],
        units="ohm m", target="fixed-thickness layer resistivity",
        confidence=confidence, interval_method="pointwise percentile, not simultaneous or posterior",
        conditioning_model=model.tolist(), fixed_thickness_m=h.tolist(), bounds_ohm_m=bounds.tolist(),
        sigma_per_real_component=sig.tolist(), active=mask.tolist(), initial_model=start.tolist(), beta=float(beta),
        sampling_law="independent Gaussian real and imaginary errors with supplied fixed sigma",
        seed=int(seed), sample_seeds=seeds, successful_seeds=successful_seeds, requested=samples,
        completed=len(models), failures=failures, samples=models, interval_ohm_m=intervals,
        status="computed" if not failures and intervals is not None else "incomplete",
        limitations="Conditional repeatability only: excludes structural, thickness, dimensionality and correlated-noise errors.",
    )


def calibrate_mt_bootstrap(model, thickness, frequencies, sigma, *, realizations=24, samples=64,
                           seed=52001, confidence=.95, beta=.001, initial=None, bounds=MT_BOUNDS):
    """Independent known-model Monte Carlo coverage experiment; never tunes intervals.

    This designated calibration model is not passed to inverse solves. Different
    SeedSequence children generate each observation and its conditional ensemble.
    Failed intervals count as noncoverage in the unconditional denominator.
    """
    if realizations < 2:
        raise ValueError("At least two independent calibration realizations required")
    model = np.asarray(model, dtype=float)
    center = impedance(model, thickness, frequencies)
    h, f, _, sig, mask, start, bounds = _validate(
        thickness, frequencies, center, sigma, None, initial, beta, bounds)
    rows, coverage, widths, bias = [], [], [], []
    child = np.random.SeedSequence(seed).spawn(realizations)
    for i, sequence in enumerate(child):
        noise_seed, bootstrap_seed = [int(s.generate_state(1)[0]) for s in sequence.spawn(2)]
        rng = np.random.default_rng(noise_seed)
        observed = center + sig*(rng.normal(size=len(f))+1j*rng.normal(size=len(f)))
        try:
            fit = _trf_only(h, f, observed, sig, mask, start, beta, bounds)
            ensemble = bootstrap_mt(fit, h, f, sig, initial=start, beta=beta, bounds=bounds,
                                    samples=samples, seed=bootstrap_seed, confidence=confidence)
            interval = np.asarray(ensemble["interval_ohm_m"])
            if ensemble["status"] != "computed":
                raise RuntimeError("At least one bootstrap solve failed; calibration interval counted as failure")
            covered = (model >= interval[0]) & (model <= interval[1])
            coverage.append(covered.tolist())
            widths.append((interval[1]-interval[0]).tolist())
            bias.append((fit-model).tolist())
            rows.append(dict(realization=i, noise_seed=noise_seed, bootstrap_seed=bootstrap_seed,
                             model=fit.tolist(), interval_ohm_m=interval.tolist(), covered=covered.tolist(),
                             bootstrap_completed=ensemble["completed"]))
        except (ValueError, RuntimeError, FloatingPointError) as error:
            coverage.append([False]*len(model))
            rows.append(dict(realization=i, noise_seed=noise_seed, bootstrap_seed=bootstrap_seed, failure=str(error)))
    measured = np.mean(coverage, axis=0)
    zscore = 1.959963984540054
    denominator = 1+zscore**2/realizations
    center = (measured+zscore**2/(2*realizations))/denominator
    radius = zscore*np.sqrt(measured*(1-measured)/realizations+zscore**2/(4*realizations**2))/denominator
    return dict(
        kind="independent_seeded_conditional_bootstrap_coverage", seed=int(seed),
        calibration_model=model.tolist(), confidence=confidence, realizations=realizations,
        fixed_thickness_m=h.tolist(), frequencies_hz=f.tolist(), sigma_per_real_component=sig.tolist(),
        beta=float(beta), bounds_ohm_m=bounds.tolist(), initial_model=start.tolist(),
        sampling_law="independent Gaussian real/imaginary errors with supplied fixed sigma",
        bootstrap_samples_per_realization=samples, failures=sum("failure" in r for r in rows),
        coverage_per_layer=measured.tolist(),
        coverage_monte_carlo_standard_error=np.sqrt(measured*(1-measured)/realizations).tolist(),
        coverage_wilson95_lower=(center-radius).tolist(),
        coverage_wilson95_upper=(center+radius).tolist(),
        mean_width_ohm_m=np.mean(widths, axis=0).tolist() if widths else None,
        bias_ohm_m=np.mean(bias, axis=0).tolist() if bias else None, rows=rows,
        statement="Measured coverage on this specified model/noise law only; no threshold tuning or field-coverage guarantee.",
    )


def solve_case(case, variant):
    """Existing v2 signature and arrays retained. Truth is used only to simulate/evaluate."""
    rho, h = mt_model(case["geometry"], 1.5 if variant == "contrast" else 1)
    f = np.geomspace(.001 if variant == "acquisition" else .01, 100, 36)
    active = np.arange(len(f)) % 2 == 0 if variant == "coverage" else np.ones(len(f), bool)
    clean = impedance(rho, h, f)
    relative = .10 if variant == "noise" else .025
    sigma = relative*abs(clean)
    rng = np.random.default_rng(case["seed"])
    observed = clean + sigma*(rng.normal(size=len(f))+1j*rng.normal(size=len(f)))
    initial = np.full(len(rho), 100.)
    beta = .3 if variant == "regularization" else .001
    methods = invert_mt(h, f, observed, sigma, active=active, initial=initial, beta=beta, seed=case["seed"])
    initial_rmse = float(np.sqrt(np.mean(np.log(initial/rho)**2)))
    for method in methods.values():
        error = float(np.sqrt(np.mean(np.log(np.asarray(method["model"])/rho)**2)))
        method["metrics"].update(log_model_rmse=error, initial_log_model_rmse=initial_rmse,
                                 model_error_ratio=error/initial_rmse if initial_rmse else None)
        method["evaluation"]["model_recovery"] = "improved_over_initial" if error < initial_rmse else "worse_than_initial"
        method["target"]["provenance"] = "original synthetic transfer functions; target truth used only for generation and evaluation"
        method["evaluation"]["reason_codes"].remove("no_independent_geological_truth")
        if error >= initial_rmse:
            method["evaluation"]["status"] = "failed"
            method["evaluation"]["reason_codes"].append("model_not_better_than_initial")
        elif method["identifiability"]["status"] == "locally_resolved" and method["evaluation"]["status"] != "failed":
            method["evaluation"]["status"] = "recovered"
            method["evaluation"]["reason_codes"].append("conditional_synthetic_recovery_over_initial")
        method["evaluation"]["criteria"] += "; synthetic recovery additionally requires log-model RMSE improvement over the independent 100 ohm m start"
    methods["mt-lm"]["uncertainty"] = bootstrap_mt(
        methods["mt-lm"]["model"], h, f, sigma, active=active, initial=initial,
        beta=beta, samples=128, seed=int(case["seed"])+100000)
    return dict(
        schema="inverse-earth/v2", **case, variant=variant,
        engine="Complex layered-earth recursion / SciPy TRF / CPU PyTorch",
        lane="computed replay", units="ohm m", data_units="ohm", truth=rho.tolist(),
        initial=initial.tolist(), thickness=h.tolist(), frequencies=f.tolist(),
        observed=curves(observed, f), clean=curves(clean, f), sigma=sigma.tolist(),
        active=active.tolist(), methods=methods,
        parameters=dict(noise_fraction=relative, regularization=beta, frequencies=int(active.sum()),
                        minimum_frequency_hz=float(f.min()), bounds_ohm_m=list(MT_BOUNDS),
                        noise_definition="sigma per independent real component; complex WRMS expectation sqrt(2)"),
        provenance=dict(kind="original synthetic 1D transfer functions", synthetic=True, seed=int(case["seed"]),
                        fixed_thickness="known construction thickness; conditional inversion, not joint layer-depth recovery"),
    )
