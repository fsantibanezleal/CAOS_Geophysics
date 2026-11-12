"""Run sealed linear magnetic L2 and sparse-IRLS folds through the M02 bridge.

These are local candidate calculations. They do not select beta, inspect
validation/outer observations, or claim field or method acceptance. Every fit
retains the exact source, allocation and fit-row seals.
"""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from time import monotonic

import numpy as np

import magnetic_forward
import magnetic_fit_assembly
import magnetic_inverse
import magnetic_likelihood
import magnetic_optimizer_adapter as adapter
import magnetic_original_optimizer as bridge
import magnetic_quantity
import magnetic_regularization
import magnetic_survey
import magnetic_survey_json
import physical_conditioned_optimizer
import physical_original_optimizer
import physical_original_quadratic
import physical_original_terminal
import physical_owned_spd
import physical_reduced_optimizer


MAX_WALL_SECONDS = 120.0
MAX_STEPS = 200
RESOURCE_LIMIT_BYTES = 805_306_368
TERMINAL = physical_owned_spd.TerminalPolicy(1e-12, 1e-6, 1e-8, 1e-6)


def _source_inventory(raw: bytes, geometry_seal: str) -> dict[str, str]:
    modules = (
        adapter, bridge, magnetic_fit_assembly, magnetic_forward,
        magnetic_inverse, magnetic_likelihood, magnetic_quantity,
        magnetic_regularization, magnetic_survey, magnetic_survey_json,
        physical_conditioned_optimizer,
        physical_original_optimizer, physical_original_quadratic,
        physical_original_terminal, physical_owned_spd,
        physical_reduced_optimizer,
    )
    inventory = {
        Path(module.__file__).name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in modules
    }
    inventory[Path(__file__).name] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    inventory["survey_request_sha256"] = hashlib.sha256(raw).hexdigest()
    inventory["geometry_seal_sha256"] = geometry_seal
    # Bind the installed SimPEG optimization and actual regularization
    # implementations used by this calculation.
    from simpeg import optimization
    for name, implementation in (
        ("simpeg.optimization", optimization),
        ("simpeg.regularization", magnetic_regularization.WeightedLeastSquares),
    ):
        vendor_path = Path(inspect.getfile(implementation))
        inventory[name] = hashlib.sha256(vendor_path.read_bytes()).hexdigest()
    return inventory


def _mesh(metadata):
    return magnetic_inverse.mesh_from_metadata(metadata)


def _owned(value):
    result = np.array(value, dtype=np.float64, copy=True, order="C")
    result.flags.writeable = False
    return result


def fit_l2_fold(raw: bytes, fold_index: int, beta: float, *, wall_seconds: float = MAX_WALL_SECONDS):
    """Fit one presealed development fold; never score or inspect held-out rows.

    ``raw`` is the complete closed survey request. The sealed geometry planner
    supplies fit rows before this function decodes values/noise. Only affine
    secondary-ENU and linear-TMI quantities are admitted by the current
    source-bound solver bridge.
    """
    if type(raw) is not bytes:
        raise TypeError("request: bounded immutable bytes required")
    if type(fold_index) is not int or fold_index not in (0, 1, 2):
        raise ValueError("fold: expected sealed development fold 0, 1, or 2")
    if type(beta) is not float or not np.isfinite(beta) or beta <= 0.0:
        raise ValueError("beta: finite positive dimensionless value required")
    if type(wall_seconds) not in (int, float) or not np.isfinite(wall_seconds) or not 0.0 < wall_seconds <= MAX_WALL_SECONDS:
        raise ValueError("wall_seconds: finite value in (0, 120] required")

    started = monotonic()
    deadline = started + float(wall_seconds)
    handle = magnetic_survey_json.parse_request(raw)
    plan = magnetic_survey.plan_geometry(handle)
    if not plan["eligibility"]["local_processing"]:
        raise ValueError("survey: local processing rights or lineage are unresolved")
    metadata = handle.metadata()
    if metadata["processing"]["quantity"] not in adapter.LINEAR_QUANTITIES:
        raise ValueError("quantity: current original-noise adapter supports affine quantities only")

    # Geometry and row membership are fixed before observation or covariance
    # payloads are decoded. Outer and validation rows never enter the fit.
    fold = plan["partition"]["folds"][fold_index]
    fit_rows = tuple(fold["fit_rows"]["data"])
    if not fit_rows or tuple(sorted(set(fit_rows))) != fit_rows:
        raise ValueError("partition: fit rows must be nonempty, unique, and ordered")
    operator = magnetic_inverse.build_operator(raw, fit_rows, deadline=deadline)
    quantity_components = 3 if metadata["processing"]["quantity"] == "secondary_enu_nT" else 1
    flat_rows = (np.asarray(fit_rows, dtype=np.int64)[:, None] * quantity_components
                 + np.arange(quantity_components, dtype=np.int64)).reshape(-1)
    document, selected_observations, selected_noise = magnetic_fit_assembly.read_selected_likelihood(
        handle, tuple(int(index) for index in flat_rows), plan["identity"]["seal_sha256"]
    )
    observed = _owned(selected_observations)
    if document["noise"]["kind"] == "diagonal_sd":
        noise = {"kind": "diagonal_sd", "values": _owned(selected_noise)}
    else:
        noise = {"kind": "full_covariance", "values": _owned(selected_noise)}

    prior = metadata["prior"]
    lower = _owned(np.asarray(prior["lower_si"]["data"], dtype=np.float64) / 0.01)
    upper = _owned(np.asarray(prior["upper_si"]["data"], dtype=np.float64) / 0.01)
    start_q = _owned(np.asarray(prior["start_si"]["data"], dtype=np.float64) / 0.01)
    reference_q = _owned(np.asarray(prior["reference_si"]["data"], dtype=np.float64) / 0.01)
    lengths_m = _owned(np.asarray(prior["lengths_m"]["data"], dtype=np.float64))
    regularizer = adapter.MagneticRegularizer(_mesh(metadata), reference_q, lengths_m)
    if regularizer.parameter_count != operator.parameters:
        raise ValueError("prior: active model count differs from the sealed forward mesh")

    geometry_seal = plan["identity"]["seal_sha256"]
    inventory = _source_inventory(raw, geometry_seal)
    inventory_sha256 = magnetic_survey_json.digest(inventory)
    source_components = 3 * len(metadata["geometry"]["usable"]["data"])
    allocation = {
        "schema": "magnetic-linear-l2-allocation-1",
        "source_components": source_components,
        "fit_components": int(observed.size),
        "parameters": operator.parameters,
        "covariance": noise["kind"] == "full_covariance",
        "limit_bytes": RESOURCE_LIMIT_BYTES,
        "steps": MAX_STEPS,
        "wall_seconds": float(wall_seconds),
        "runtime_epoch": physical_original_optimizer.LINEAR_EPOCH,
    }
    allocation_sha256 = magnetic_survey_json.digest(allocation)
    objective = adapter.MagneticObjective(
        operator, regularizer, observed, noise, lower, upper, beta,
        inventory_sha256, allocation_sha256,
    )
    budget = physical_original_optimizer.ConditionedBudget(
        deadline, MAX_STEPS, RESOURCE_LIMIT_BYTES, RESOURCE_LIMIT_BYTES,
        allocation_sha256,
    )

    try:
        solved = adapter.solve_linear(
            objective, start_q, source_components=source_components,
            budget=budget, terminal=TERMINAL,
        )
        terminal_audits = tuple({
            "iteration": row.get("iteration"),
            "seconds": row.get("seconds"),
            "failure": row.get("failure"),
            "phase": (row.get("check") or {}).get("phase"),
            "proof_basis": (row.get("check") or {}).get("proof_basis"),
            "check_reason": (row.get("check") or {}).get("reason"),
            "actions": (row.get("check") or {}).get("actions"),
            "preconditioner_basis_actions": (row.get("check") or {}).get("preconditioner_basis_actions"),
            "source_normalized_kkt_upper": (row.get("check") or {}).get("source_normalized_kkt_upper"),
            "kappa_upper": (row.get("check") or {}).get("kappa_upper"),
            "mu_lower": ((row.get("check") or {}).get("bounds") or {}).get("mu_lower"),
            "residual_radius_upper": (row.get("check") or {}).get("residual_radius_upper"),
            "inside_original_bounds": (row.get("check") or {}).get("inside_original_bounds"),
            "free_error_inf_upper": (row.get("check") or {}).get("free_error_inf_upper"),
            "active_sign_pass": (row.get("check") or {}).get("active_sign_pass"),
            "bounds": (row.get("check") or {}).get("bounds"),
            "passed": (row.get("check") or {}).get("passed"),
        } for row in solved.get("terminal_audits", ()))
        if solved["status"] != "converged":
            candidate_q = solved.get("q")
            if type(candidate_q) is np.ndarray and candidate_q.dtype == np.float64:
                candidate_q = _owned(candidate_q)
            else:
                candidate_q = None
            return {
                "schema": "magnetic-linear-l2-fold-result-1",
                "status": "failed",
                "reason": solved.get("reason") or "optimizer_not_converged",
                "quantity": operator.quantity,
                "fold_index": fold_index,
                "fit_rows": list(fit_rows),
                "geometry_seal_sha256": geometry_seal,
                "source_inventory": inventory,
                "source_inventory_sha256": inventory_sha256,
                "allocation": allocation,
                "allocation_plan_sha256": allocation_sha256,
                "beta": beta,
                "model_q": candidate_q,
                "prediction_nT": None,
                "residual_observed_minus_predicted_nT": None,
                "objective": None,
                "normalized_projected_kkt_inf": None,
                "iterations": solved.get("iterations"),
                "elapsed_seconds": monotonic() - started,
                "trace": solved.get("trace"),
                "terminal_audits": terminal_audits,
                "claims": {
                    "field_observations": False,
                    "field_geology_validated": False,
                    "candidate_selected": False,
                    "outer_evaluation_performed": False,
                    "method_accepted": False,
                    "online_admitted": False,
                },
            }
        final_q = _owned(solved["q"])
        components = objective.components(final_q)
        gradient = objective.evaluate(final_q, return_g=True, return_H=False)[1]
        projected = gradient.copy()
        projected[(final_q == lower) & (gradient > 0.0)] = 0.0
        projected[(final_q == upper) & (gradient < 0.0)] = 0.0
        initial_gradient = objective.evaluate(start_q, return_g=True, return_H=False)[1]
        normalized_kkt = float(np.linalg.norm(projected, np.inf) /
                               max(1.0, float(np.linalg.norm(initial_gradient, np.inf))))
        prediction = _owned(operator.evaluate(final_q)["prediction_nT"])
        residual = _owned(observed - prediction)
        success = solved["status"] == "converged" and normalized_kkt <= TERMINAL.required_kkt_normalized
        return {
            "schema": "magnetic-linear-l2-fold-result-1",
            "status": "converged" if success else "failed",
            "reason": None if success else "independent_projected_kkt",
            "quantity": operator.quantity,
            "fold_index": fold_index,
            "fit_rows": list(fit_rows),
            "geometry_seal_sha256": geometry_seal,
            "source_inventory": inventory,
            "source_inventory_sha256": inventory_sha256,
            "allocation": allocation,
            "allocation_plan_sha256": allocation_sha256,
            "beta": beta,
            "model_q": final_q,
            "parameter_unit": "q=chi_si/0.01",
            "prediction_nT": prediction,
            "residual_observed_minus_predicted_nT": residual,
            "objective": components,
            "normalized_projected_kkt_inf": normalized_kkt,
            "iterations": solved["iterations"],
            "elapsed_seconds": monotonic() - started,
            "trace": solved.get("trace"),
            "terminal_audits": terminal_audits,
            "claims": {
                "field_observations": False,
                "field_geology_validated": False,
                "candidate_selected": False,
                "outer_evaluation_performed": False,
                "method_accepted": False,
                "online_admitted": False,
            },
        }
    finally:
        objective.release_state()


def fit_sparse_fold(raw: bytes, fold_index: int, beta: float, *,
                    l2_result: dict, wall_seconds: float = MAX_WALL_SECONDS):
    """Run the frozen eight-epsilon, fixed-beta SimPEG sparse IRLS policy.

    Each reweight step constructs a source-bound frozen quadratic and runs the
    accepted M02 original-noise solver. The outer loop checks the actual
    fixed-epsilon objective and refreshed projected gradient; solver convergence
    alone never advances the epsilon schedule.
    """
    if type(raw) is not bytes:
        raise TypeError("request: bounded immutable bytes required")
    if type(fold_index) is not int or fold_index not in (0, 1, 2):
        raise ValueError("fold: expected sealed development fold 0, 1, or 2")
    if type(beta) is not float or not np.isfinite(beta) or beta <= 0.:
        raise ValueError("beta: finite positive dimensionless value required")
    if type(l2_result) is not dict or l2_result.get("schema") != "magnetic-linear-l2-fold-result-1":
        raise TypeError("l2_result: source-bound L2 fold result required")
    if (l2_result.get("status") != "converged" or l2_result.get("fold_index") != fold_index
            or l2_result.get("beta") != beta):
        raise ValueError("l2_result: converged result for this fold and beta required")
    if (type(l2_result.get("terminal_audits")) not in (tuple, list)
            or not l2_result["terminal_audits"]
            or any(row.get("passed") is not True for row in l2_result["terminal_audits"])
            or type(l2_result.get("normalized_projected_kkt_inf")) not in (int, float)
            or not np.isfinite(l2_result["normalized_projected_kkt_inf"])
            or l2_result["normalized_projected_kkt_inf"] > TERMINAL.required_kkt_normalized):
        raise ValueError("l2_result: terminal certificates and independent KKT must pass")
    if (type(wall_seconds) not in (int, float) or not np.isfinite(wall_seconds)
            or not 0. < wall_seconds <= MAX_WALL_SECONDS):
        raise ValueError("wall_seconds: finite value in (0, 120] required")

    started = monotonic()
    deadline = started + float(wall_seconds)
    handle = magnetic_survey_json.parse_request(raw)
    plan = magnetic_survey.plan_geometry(handle)
    if not plan["eligibility"]["local_processing"]:
        raise ValueError("survey: local processing rights or lineage are unresolved")
    metadata = handle.metadata()
    if metadata["processing"]["quantity"] not in adapter.LINEAR_QUANTITIES:
        raise ValueError("quantity: current original-noise adapter supports affine quantities only")

    fold = plan["partition"]["folds"][fold_index]
    fit_rows = tuple(fold["fit_rows"]["data"])
    if not fit_rows or tuple(sorted(set(fit_rows))) != fit_rows:
        raise ValueError("partition: fit rows must be nonempty, unique, and ordered")
    operator = magnetic_inverse.build_operator(raw, fit_rows, deadline=deadline)
    l2_model = l2_result.get("model_q")
    if (type(l2_model) is not np.ndarray or l2_model.dtype != np.float64
            or l2_model.shape != (operator.parameters,) or not np.isfinite(l2_model).all()):
        raise TypeError("l2_result: finite float64 model with the sealed active-cell count required")
    components = 3 if metadata["processing"]["quantity"] == "secondary_enu_nT" else 1
    flat_rows = (np.asarray(fit_rows, dtype=np.int64)[:, None] * components
                 + np.arange(components, dtype=np.int64)).reshape(-1)
    document, selected_observations, selected_noise = magnetic_fit_assembly.read_selected_likelihood(
        handle, tuple(int(index) for index in flat_rows), plan["identity"]["seal_sha256"]
    )
    observed = _owned(selected_observations)
    noise = {"kind": document["noise"]["kind"], "values": _owned(selected_noise)}
    prior = metadata["prior"]
    lower = _owned(np.asarray(prior["lower_si"]["data"], dtype=np.float64) / .01)
    upper = _owned(np.asarray(prior["upper_si"]["data"], dtype=np.float64) / .01)
    reference_q = _owned(np.asarray(prior["reference_si"]["data"], dtype=np.float64) / .01)
    lengths_m = _owned(np.asarray(prior["lengths_m"]["data"], dtype=np.float64))
    if len(reference_q) != operator.parameters:
        raise ValueError("prior: active model count differs from the sealed forward mesh")
    if np.any((l2_model < lower) | (l2_model > upper)):
        raise ValueError("l2_result: model lies outside this survey's declared bounds")
    l2_request_sha256 = l2_result.get("source_inventory", {}).get("survey_request_sha256")
    if l2_request_sha256 != hashlib.sha256(raw).hexdigest():
        raise ValueError("l2_result: source request differs from the sparse fit request")
    if l2_result.get("geometry_seal_sha256") != plan["identity"]["seal_sha256"]:
        raise ValueError("l2_result: geometry seal differs from the sparse fit")
    l2_model_sha256 = hashlib.sha256(np.asarray(l2_model, dtype="<f8", order="C").tobytes()).hexdigest()

    geometry_seal = plan["identity"]["seal_sha256"]
    inventory = _source_inventory(raw, geometry_seal)
    if l2_result.get("source_inventory") != inventory:
        raise ValueError("l2_result: source inventory differs from the sparse fit")
    if (l2_result.get("fit_rows") != list(fit_rows)
            or l2_result.get("source_inventory_sha256") != magnetic_survey_json.digest(inventory)):
        raise ValueError("l2_result: fit-row or inventory digest differs from the sparse fit")
    inventory_sha256 = magnetic_survey_json.digest(inventory)
    source_components = 3 * len(metadata["geometry"]["usable"]["data"])
    allocation = {
        "schema": "magnetic-linear-sparse-allocation-1",
        "source_components": source_components,
        "fit_components": int(observed.size),
        "parameters": operator.parameters,
        "covariance": noise["kind"] == "full_covariance",
        "limit_bytes": RESOURCE_LIMIT_BYTES,
        "inner_steps": MAX_STEPS,
        "epsilon_schedule_q": list(magnetic_regularization.SPARSE_EPSILON_Q),
        "outer_updates_per_epsilon": 20,
        "start_policy": "same_fold_same_beta_converged_l2",
        "start_model_q_sha256": l2_model_sha256,
        "wall_seconds": float(wall_seconds),
        "runtime_epoch": physical_original_optimizer.LINEAR_EPOCH,
    }
    allocation_sha256 = magnetic_survey_json.digest(allocation)
    history = []
    stages = []
    current_q = np.array(l2_model, dtype=np.float64, copy=True, order="C")
    final_stage_gradient_limit = None
    final_projected_gradient_inf = None
    failure = None

    for epsilon_index, epsilon_q in enumerate(magnetic_regularization.SPARSE_EPSILON_Q):
        if monotonic() >= deadline:
            failure = "wall_cap"
            break
        regularizer = adapter.MagneticRegularizer(
            magnetic_inverse.mesh_from_metadata(metadata), reference_q, lengths_m,
            "sparse", float(epsilon_q), current_q,
        )
        objective = adapter.MagneticObjective(
            operator, regularizer, observed, noise, lower, upper, beta,
            inventory_sha256, allocation_sha256, stage_index=epsilon_index,
        )
        initial_gradient = objective.evaluate(current_q, return_g=True, return_H=False)[1]
        gradient_limit = 1e-7 * max(1., float(np.linalg.norm(initial_gradient, np.inf)))
        final_stage_gradient_limit = gradient_limit
        sparse_at_start = regularizer.source.evaluate_sparse(current_q, float(epsilon_q))
        previous_true = float(objective._state(current_q)[0]
                              + beta * sparse_at_start["true_fixed_epsilon_psi"])
        stage_converged = False
        last_model_relative = None
        last_weights_relative = None
        last_projected_gradient = None
        try:
            for outer_index in range(20):
                if monotonic() >= deadline:
                    failure = "wall_cap"
                    break
                budget = physical_original_optimizer.ConditionedBudget(
                    deadline, MAX_STEPS, RESOURCE_LIMIT_BYTES, RESOURCE_LIMIT_BYTES,
                    allocation_sha256,
                )
                solved = adapter.solve_linear(
                    objective, current_q, source_components=source_components,
                    budget=budget, terminal=TERMINAL,
                )
                certificates = tuple(solved.get("terminal_audits", ()))
                core_certificate = bool(certificates and certificates[-1].get("check", {}).get("passed"))
                if solved.get("status") != "converged" or not core_certificate:
                    failure = solved.get("reason") or "inner_core_certificate_failed"
                    attempts = tuple(solved.get("conditioning_attempts", ()))
                    last_attempt = attempts[-1] if attempts else {}
                    failed_trial = solved.get("failed_trial")
                    failed_model = solved.get("q")
                    if (type(failed_model) is not np.ndarray or failed_model.dtype != np.float64
                            or failed_model.shape != current_q.shape or not np.isfinite(failed_model).all()):
                        failed_model = None
                    compact_trial = None
                    if type(failed_trial) is dict:
                        compact_trial = {
                            key: failed_trial[key] for key in ("iteration", "reason", "best_observed_phi")
                            if key in failed_trial and type(failed_trial[key]) in (int, float, str)
                        }
                        line_search = failed_trial.get("last_actual_line_search")
                        if type(line_search) is dict:
                            compact_trial["last_actual_line_search"] = {
                                key: line_search[key] for key in (
                                    "iteration", "trial", "alpha", "phi_current", "phi_trial",
                                    "projected_slope", "trial_model_sha256", "accepted",
                                ) if key in line_search and type(line_search[key]) in (int, float, str, bool)
                            }
                    history.append({
                        "epsilon_q": float(epsilon_q), "outer_iteration": outer_index + 1,
                        "start_model_q": _owned(current_q),
                        "inner_model_q": None if failed_model is None else _owned(failed_model),
                        "inner_model_q_sha256": (
                            None if failed_model is None else hashlib.sha256(
                                np.asarray(failed_model, dtype="<f8", order="C").tobytes()
                            ).hexdigest()
                        ),
                        "inner_status": solved.get("status"),
                        "inner_reason": failure,
                        "inner_iterations": solved.get("iterations"),
                        "inner_failed_trial": compact_trial,
                        "conditioning_attempt_count": len(attempts),
                        "last_conditioning_attempt": {
                            key: last_attempt.get(key) for key in (
                                "phase", "branch", "failure", "iterations", "cumulative_CG",
                                "cg_remaining", "resource", "prospective_peak_bytes",
                                "preflight_seconds", "total_phase_seconds",
                            ) if key in last_attempt
                        },
                        "terminal_audits": certificates,
                        "core_certificate": core_certificate,
                        "monotonicity_pass": None,
                    })
                    break
                candidate_q = np.array(solved["q"], dtype=np.float64, copy=True, order="C")
                before = current_q.copy()
                model_relative = float(np.linalg.norm(candidate_q - before, np.inf)
                                       / max(1., float(np.linalg.norm(candidate_q, np.inf))))
                refreshed = regularizer.source.evaluate_sparse(candidate_q, float(epsilon_q))
                phi_d, _, _, surrogate_gradient, _ = objective._state(candidate_q)
                frozen_gradient = regularizer.evaluate(candidate_q)["gradient_q"]
                true_gradient = (surrogate_gradient - beta * frozen_gradient
                                 + beta * refreshed["true_gradient_q"])
                projected = true_gradient.copy()
                projected[(candidate_q == lower) & (true_gradient > 0.)] = 0.
                projected[(candidate_q == upper) & (true_gradient < 0.)] = 0.
                projected_inf = float(np.linalg.norm(projected, np.inf))
                true_objective = float(phi_d + beta * refreshed["true_fixed_epsilon_psi"])
                monotonic_allowance = float(64. * np.finfo(np.float64).eps
                    * max(1., abs(previous_true), abs(true_objective)))
                old_weights = 1. / np.hypot(before - reference_q, float(epsilon_q))
                new_weights = refreshed["smallness_irls_weights"]
                weights_relative = float(np.linalg.norm(new_weights - old_weights, np.inf)
                    / max(1., float(np.linalg.norm(old_weights, np.inf))))
                if not np.isfinite([model_relative, weights_relative, projected_inf,
                                    true_objective, phi_d, monotonic_allowance]).all():
                    failure = "nonfinite_outer_state"
                    break
                if true_objective > previous_true + monotonic_allowance:
                    failure = "true_fixed_epsilon_objective_increased"
                    history.append({
                        "epsilon_q": float(epsilon_q), "outer_iteration": outer_index + 1,
                        "model_q": _owned(candidate_q), "true_objective": true_objective,
                        "previous_true_objective": previous_true,
                        "monotonic_allowance": monotonic_allowance,
                        "model_relative": model_relative,
                        "weights_relative": weights_relative,
                        "projected_gradient_inf": projected_inf,
                        "inner_iterations": solved.get("iterations"),
                        "core_certificate": core_certificate,
                        "monotonicity_pass": False,
                    })
                    break
                current_q = candidate_q
                last_model_relative = model_relative
                last_weights_relative = weights_relative
                last_projected_gradient = projected_inf
                final_projected_gradient_inf = projected_inf
                history.append({
                    "epsilon_q": float(epsilon_q), "outer_iteration": outer_index + 1,
                    "model_q": _owned(candidate_q), "true_objective": true_objective,
                    "previous_true_objective": previous_true,
                    "monotonic_allowance": monotonic_allowance,
                    "model_relative": model_relative,
                    "weights_relative": weights_relative,
                    "projected_gradient_inf": projected_inf,
                    "gradient_limit": gradient_limit,
                    "inner_iterations": solved.get("iterations"),
                    "terminal_audits": certificates,
                    "core_certificate": core_certificate,
                    "monotonicity_pass": True,
                })
                previous_true = true_objective
                objective.release_state()
                if (model_relative <= 1e-5 and projected_inf <= gradient_limit
                        and core_certificate):
                    stage_converged = True
                    break
                # The next IRLS quadratic must be rebuilt with the exact new
                # iterate's canonical weights and identity.
                objective.release_state()
                regularizer = adapter.MagneticRegularizer(
                    magnetic_inverse.mesh_from_metadata(metadata), reference_q, lengths_m,
                    "sparse", float(epsilon_q), current_q,
                )
                objective = adapter.MagneticObjective(
                    operator, regularizer, observed, noise, lower, upper, beta,
                    inventory_sha256, allocation_sha256, stage_index=epsilon_index,
                )
            if failure is not None:
                stages.append({
                    "epsilon_q": float(epsilon_q), "status": "failed",
                    "reason": failure,
                    "outer_updates": len([row for row in history
                                          if row.get("epsilon_q") == epsilon_q]),
                    "model_relative": last_model_relative,
                    "weights_relative": last_weights_relative,
                    "projected_gradient_inf": last_projected_gradient,
                    "gradient_limit": gradient_limit,
                })
                break
            stages.append({
                "epsilon_q": float(epsilon_q),
                "outer_updates": len([row for row in history if row["epsilon_q"] == epsilon_q]),
                "status": "converged" if stage_converged else "failed",
                "model_relative": last_model_relative,
                "weights_relative": last_weights_relative,
                "projected_gradient_inf": last_projected_gradient,
                "gradient_limit": gradient_limit,
            })
            if not stage_converged:
                failure = "irls_iteration_cap"
                break
        finally:
            objective.release_state()

    success = failure is None and len(stages) == len(magnetic_regularization.SPARSE_EPSILON_Q)
    result = {
        "schema": "magnetic-linear-sparse-fold-result-1",
        "status": "converged" if success else "failed",
        "reason": None if success else (failure or "epsilon_schedule_incomplete"),
        "quantity": operator.quantity,
        "fold_index": fold_index,
        "fit_rows": list(fit_rows),
        "geometry_seal_sha256": geometry_seal,
        "source_inventory": inventory,
        "source_inventory_sha256": inventory_sha256,
        "allocation": allocation,
        "allocation_plan_sha256": allocation_sha256,
        "start_policy": "same_fold_same_beta_converged_l2",
        "start_model_q_sha256": l2_model_sha256,
        "beta": beta,
        "model_q": _owned(current_q),
        "parameter_unit": "q=chi_si/0.01",
        "epsilon_schedule_q": list(magnetic_regularization.SPARSE_EPSILON_Q),
        "stages": stages,
        "history": history,
        "elapsed_seconds": monotonic() - started,
        "claims": {
            "field_observations": False,
            "field_geology_validated": False,
            "candidate_selected": False,
            "outer_evaluation_performed": False,
            "method_accepted": False,
            "online_admitted": False,
        },
    }
    if success:
        final_regularizer = adapter.MagneticRegularizer(
            magnetic_inverse.mesh_from_metadata(metadata), reference_q, lengths_m,
            "sparse", float(magnetic_regularization.SPARSE_EPSILON_Q[-1]), current_q,
        )
        final_state = final_regularizer.source.evaluate_sparse(
            current_q, float(magnetic_regularization.SPARSE_EPSILON_Q[-1])
        )
        final_operator = adapter.MagneticObjective(
            operator, final_regularizer, observed, noise, lower, upper, beta,
            inventory_sha256, allocation_sha256,
            stage_index=len(magnetic_regularization.SPARSE_EPSILON_Q) - 1,
        )
        try:
            phi_d = float(final_operator._state(current_q)[0])
            prediction = _owned(operator.evaluate(current_q)["prediction_nT"])
            result.update(
                prediction_nT=prediction,
                residual_observed_minus_predicted_nT=_owned(observed - prediction),
                objective={
                    "phi_d": phi_d,
                    "phi_m_true_fixed_epsilon": final_state["true_fixed_epsilon_psi"],
                    "phi_engine_true_fixed_epsilon": float(
                        phi_d + beta * final_state["true_fixed_epsilon_psi"]
                    ),
                    "phi_m_surrogate_quadratic": final_state["surrogate_quadratic"],
                    "epsilon_q": float(magnetic_regularization.SPARSE_EPSILON_Q[-1]),
                },
                normalized_projected_gradient_inf=(
                    final_projected_gradient_inf / max(1.,
                        float(np.linalg.norm(initial_gradient, np.inf)))
                    if final_projected_gradient_inf is not None else None
                ),
                final_gradient_limit=final_stage_gradient_limit,
            )
        finally:
            final_operator.release_state()
    return result
