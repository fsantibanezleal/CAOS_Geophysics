"""Run one sealed linear magnetic L2 fit fold through the current M02 bridge.

This is an executable local candidate calculation. It does not select beta,
run IRLS, inspect validation/outer observations, or claim field or method
acceptance. The result retains the exact source, allocation and fit-row seals.
"""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from time import monotonic

import numpy as np

import magnetic_forward
import magnetic_inverse
import magnetic_likelihood
import magnetic_optimizer_adapter as adapter
import magnetic_original_optimizer as bridge
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
TERMINAL = physical_owned_spd.TerminalPolicy(1e-7, 1e-6, 1e-8, 1e-6)


def _source_inventory(raw: bytes, geometry_seal: str) -> dict[str, str]:
    modules = (
        adapter, bridge, magnetic_forward, magnetic_inverse,
        magnetic_likelihood, magnetic_regularization, magnetic_survey,
        magnetic_survey_json, physical_conditioned_optimizer,
        physical_original_optimizer, physical_original_quadratic,
        physical_original_terminal, physical_owned_spd,
        physical_reduced_optimizer,
    )
    inventory = {
        Path(module.__file__).name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in modules
    }
    inventory["survey_request_sha256"] = hashlib.sha256(raw).hexdigest()
    inventory["geometry_seal_sha256"] = geometry_seal
    # Bind the installed SimPEG optimization implementation used by the actual
    # forward/regularization paths, as well as the M02 native optimizer source.
    from simpeg import optimization
    vendor_path = Path(inspect.getfile(optimization))
    inventory["simpeg.optimization"] = hashlib.sha256(vendor_path.read_bytes()).hexdigest()
    return inventory


def _likelihood(handle):
    """Materialize validated observations/noise only after geometry sealing."""
    from magnetic_fit_assembly import _likelihood as read_likelihood
    document, observed, noise = read_likelihood(handle)
    return document, observed, noise


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
    document, observations, noise_values = _likelihood(handle)
    quantity_components = 3 if document["processing"]["quantity"] == "secondary_enu_nT" else 1
    flat_rows = (np.asarray(fit_rows, dtype=np.int64)[:, None] * quantity_components
                 + np.arange(quantity_components, dtype=np.int64)).reshape(-1)
    observed = _owned(observations.reshape(-1, order="C")[flat_rows])
    if document["noise"]["kind"] == "diagonal_sd":
        noise = {"kind": "diagonal_sd", "values": _owned(noise_values.reshape(-1, order="C")[flat_rows, None])}
    else:
        principal = noise_values[np.ix_(flat_rows, flat_rows)]
        noise = {"kind": "full_covariance", "values": _owned(principal)}

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
