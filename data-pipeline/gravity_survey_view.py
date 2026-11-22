"""Bounded projection of a fully replayed native gravity calibration archive.

This module does not admit sources, select candidates, refit, or evaluate sealed
observations. It emits one recorded fit/frame for an already verified archive.
"""
from __future__ import annotations

import json

import numpy as np

import gravity_irls_pool as corrected_pool
import gravity_irls as irls
import gravity_l2 as l2
import gravity_survey_l2 as survey
import gravity_workflow_io as transport


SCHEMA = "geophysics.gravity-survey-view/v1"
MAX_PACKET_BYTES = 4 * 1024**2
MAX_CELLS = 4096
MAX_STATIONS = 2048
MAX_STATES = 201
_L2 = "gravity-survey-l2-calibration-result-1"
_IRLS = "gravity-survey-irls-calibration-result-3"
_CORRECTED = "gravity-survey-irls-corrected-calibration-result-1"


def _digest(value):
    return survey._digest(value)


def _native_fit(result, fit_index):
    schema = result["schema"]
    if type(fit_index) is not int or not 0 <= fit_index <= 24:
        raise ValueError("view: fit index must be an exact integer in 0..24")
    if fit_index == 24:
        if result["final_solve"] is None:
            raise ValueError("view: selected development refit was not run")
        if schema == _L2:
            return result["final_solve"]
    else:
        candidate, fold = divmod(fit_index, 3)
        item = result["candidates"][candidate]["folds"][fold]["solve"]
        if schema == _L2:
            return item
    if schema == _IRLS:
        return result["fits"][fit_index]
    if schema == _CORRECTED:
        return corrected_pool.decode(result["fits"][fit_index])
    raise ValueError("view: unsupported calibration result schema")


def _fit_status(fit):
    if fit.get("schema") == "gravity-corrected-unstarted-1":
        return fit["status"], fit["reason"], 0
    if fit.get("schema") == "gravity-irls-corrected-partition-1":
        terminal = fit["terminal"]
        return terminal["status"], terminal["reason"], len(fit["models_q"])
    trace = fit["trace"]
    return fit["status"], fit["reason"], len(trace["models_kg_m3"])


def _corrected_history(fit):
    initial = fit["initialization"]["trace"]
    models = fit["models_q"] * 1000.0
    kinds, labels = fit["event_kinds"], fit["event_stages"]
    if len(models) > MAX_STATES or len(kinds) != len(models) or len(labels) != len(models):
        raise ValueError("view: corrected actual-state history shape/cap")
    stages = fit["stages"]
    history = []
    for row, (model, kind, stage_index) in enumerate(zip(models, kinds, labels)):
        if kind == 0:
            if row >= len(initial["models_kg_m3"]):
                raise ValueError("view: corrected initialization frame reference")
            source = initial
            metric_row = row
            phase = "initialization"
            stage = None
        elif kind == 1:
            source = None
            metric_row = None
            phase = "auxiliary_adoption"
            stage = int(stage_index)
        elif kind == 2:
            stage = int(stage_index)
            if not 0 <= stage < len(stages):
                raise ValueError("view: corrected native stage reference")
            source = stages[stage]["inner"]["trace"]
            metric_row = row - int(stages[stage]["adopted_row"])
            if not 0 <= metric_row < len(source["models_q"]):
                raise ValueError("view: corrected native frame reference")
            phase = "native_inner"
        else:
            raise ValueError("view: corrected frame kind")
        metrics = {} if source is None else {
            "phi_d": _number(source["phi_d"][metric_row]),
            "phi_m": _number(source["phi_m"][metric_row]),
            "phi_engine": _number(source["phi_engine"][metric_row]),
            "kkt_normalized": _number(source["kkt_normalized"][metric_row]),
            "line_search_count": (None if metric_row == 0 else int(source["line_search_counts"][metric_row - 1])),
            "cg_count": (None if metric_row == 0 else int(source["cg_counts"][metric_row - 1])),
        }
        history.append({"accepted_index": row, "phase": phase, "stage_index": stage,
                        **metrics})
    return history


def _number(value):
    result = float(value)
    if not np.isfinite(result):
        raise ValueError("view: nonfinite metric")
    return result


def _maybe_number(value):
    return None if value is None else _number(value)


def _history(fit):
    if fit.get("schema") == "gravity-irls-corrected-partition-1":
        return _corrected_history(fit)
    if fit.get("schema") == "gravity-corrected-unstarted-1":
        return []
    trace = fit["trace"]
    models = trace["models_kg_m3"]
    if len(models) > MAX_STATES:
        raise ValueError("view: accepted-state cap")
    stages = trace.get("stage_indices")
    history = []
    for row, model in enumerate(models):
        history.append({
            "accepted_index": row,
            "phase": "native_inner" if fit.get("irls_terminal") else "l2",
            "stage_index": int(stages[row]) if stages is not None else None,
            "phi_d": _number(trace["phi_d"][row]),
            "phi_m": _number(trace["phi_m"][row]),
            "phi_engine": _number(trace["phi_engine"][row]),
            "kkt_normalized": _number(trace["kkt_normalized"][row]),
            "line_search_count": (None if row == 0 else int(trace["line_search_counts"][row - 1])),
            "cg_count": (None if row == 0 else int(trace["cg_counts"][row - 1])),
        })
    return history


def _candidate_projection(result):
    output = []
    for candidate in result["candidates"]:
        folds = []
        for fold_index, fold in enumerate(candidate["folds"]):
            solve = fold["solve"]
            if "status" in fold:
                status, reason = fold["status"], fold["reason"]
            elif type(solve) is int:
                status, reason, _ = _fit_status(_native_fit(result, solve))
            else:
                status, reason = solve["status"], solve["reason"]
            folds.append({
                "fit_index": int(solve) if type(solve) is int else int(3 * candidate["index"] + fold_index),
                "status": status,
                "reason": reason,
                "validation_phi_d": (None if fold.get("validation_phi_d") is None
                                     else _number(fold["validation_phi_d"])),
                "validation_wrms": (None if fold.get("validation_wrms") is None
                                    else _number(fold["validation_wrms"])),
                "validation_rmse_mgal": (None if fold.get("validation_rmse_mgal") is None
                                         else _number(fold["validation_rmse_mgal"])),
            })
        output.append({"index": int(candidate["index"]), "beta": _number(candidate["beta_candidate"]),
                       "eligible": bool(candidate["eligible"]),
                       "score": None if candidate.get("score_q") is None else _number(candidate["score_q"]),
                       "reason": candidate["reason"], "folds": folds})
    if len(output) != 8 or any(len(c["folds"]) != 3 for c in output):
        raise ValueError("view: all eight candidates and 24 fold verdicts required")
    return output


def _recipe_identity(archive, result):
    request = archive["request"]
    if result["schema"] == _CORRECTED:
        runtime, policy, sources = result["runtime_epoch"], result["policy"], result["source_inventory"]
    else:
        provenance = result["provenance"]
        runtime = provenance["runtime_epoch"]
        policy = request["policy"]
        sources = provenance["runtime_versions"]
    return _digest({"request_sha256": _digest(request), "runtime_epoch": runtime,
                    "policy": policy, "source_inventory": sources})


def _runtime_identity(result):
    if result["schema"] == _CORRECTED:
        return result["runtime_epoch"], _digest(result["policy"])
    provenance = result["provenance"]
    return provenance["runtime_epoch"], provenance["policy_sha256"]


def _stage_book(archive, fit):
    if fit.get("schema") == "gravity-corrected-unstarted-1":
        return []
    if fit.get("schema") == "gravity-irls-corrected-partition-1":
        rows = []
        for stage in fit["stages"]:
            inner = stage["inner"]
            rows.append({
                "index": int(stage["index"]), "epsilon": [float(v) for v in stage["epsilon"]],
                "weight_sha256": stage["weight_sha256"], "operator_sha256": stage["operator_sha256"],
                "start_row": int(stage["start_row"]), "adopted_row": int(stage["adopted_row"]),
                "stop_row": int(stage["stop_row"]),
                "attempt_count": int(stage["attempt_span"][1] - stage["attempt_span"][0]),
                "inner_status": inner["status"], "inner_reason": inner["reason"],
                "inner_iterations": int(inner["iterations"]),
                "inner_phi_d": _maybe_number(inner["phi_d"]), "inner_phi_m": _maybe_number(inner["phi_m"]),
                "inner_phi_engine": _maybe_number(inner["phi_engine"]),
                "inner_kkt_normalized": _maybe_number(inner["kkt_normalized"]),
            })
        return rows
    if not fit.get("irls_terminal"):
        return []
    result, request = archive["result"], archive["request"]
    book_index = fit["stages"]
    shared_trace = {key: fit["trace"][key] for key in ("models_kg_m3", "stage_indices")}
    rows = irls.decode_stage_book(
        result["stage_books"][book_index], shared_trace,
        parameter_count=len(result["plan"]["geometry"]["active_cell_indices"]),
        beta_engine=fit["beta_engine"], initial_epsilon=fit["initial_epsilon"],
        policy=request["policy"]["irls"],
    )
    projected = []
    for row in rows:
        projected.append({
            "index": int(row["index"]), "accepted_span": [int(v) for v in (row["accepted_start"], row["accepted_stop"])],
            "model_span": [int(v) for v in (row["model_row_start"], row["model_row_stop"])],
            "beta_engine": _number(row["beta_engine"]), "epsilon": list(row["epsilon"]),
            "weight_sha256": list(row["weight_sha256"]), "operator_sha256": list(row["operator_sha256"]),
            "status": row["status"], "reason": row["reason"], "metrics": row["metrics"],
        })
    return projected


def _terminal_metrics(fit):
    if fit.get("schema") == "gravity-corrected-unstarted-1":
        return {key: None for key in ("phi_d", "phi_m", "phi_engine", "wrms", "kkt_normalized",
                                     "canonical_absolute_kkt", "canonical_weight_mismatch")}
    if fit.get("schema") == "gravity-irls-corrected-partition-1":
        if fit["stages"]:
            stage = fit["stages"][-1]
            inner = stage["inner"]
            source = inner
            canonical_abs = stage["canonical_absolute_kkt"]
            canonical_norm = stage["canonical_normalized_kkt"]
            mismatch = stage["canonical_weight_mismatch"]
        else:
            source = fit["initialization"]
            canonical_abs = canonical_norm = mismatch = None
        return {"phi_d": _maybe_number(source.get("phi_d")), "phi_m": _maybe_number(source.get("phi_m")),
                "phi_engine": _maybe_number(source.get("phi_engine")), "wrms": _maybe_number(source.get("wrms")),
                "kkt_normalized": _maybe_number(canonical_norm),
                "canonical_absolute_kkt": _maybe_number(canonical_abs),
                "canonical_weight_mismatch": _maybe_number(mismatch)}
    return {key: _maybe_number(fit.get(key)) for key in
            ("phi_d", "phi_m", "phi_engine", "wrms", "kkt_normalized")} | {
                "canonical_absolute_kkt": None, "canonical_weight_mismatch": None}


def project_verified_calibration(archive, fit_index, frame_index):
    """Verify the entire archive, then emit one actual fit/frame as bounded JSON.

    Call this from a bounded worker. The full numerical replay is intentionally
    synchronous and is not suitable for an API request event loop.
    """
    transport.verify_calibration(archive)
    survey._keys(archive, ("schema", "request", "result"), "view archive")
    result, request = archive["result"], archive["request"]
    plan = result["plan"]
    result_sha = result.get("result_sha256")
    if result_sha is None:
        result_sha = _digest(result)
    fit = _native_fit(result, fit_index)
    status, reason, state_count = _fit_status(fit)
    history = _history(fit)
    if state_count != len(history):
        raise ValueError("view: replayed fit state count differs from projected history")
    if type(frame_index) is not int:
        raise TypeError("view: exact integer frame index required")
    if state_count == 0:
        if frame_index != -1:
            raise ValueError("view: a fit with no accepted state requires frame -1")
        model = None
        frame_digest = None
        history_row = None
    else:
        if not 0 <= frame_index < state_count:
            raise ValueError("view: frame index outside actual accepted states")
        history_row = history[frame_index]
        if fit.get("schema") == "gravity-irls-corrected-partition-1":
            model = np.asarray(fit["models_q"][frame_index] * 1000.0, dtype=np.float64)
        else:
            model = np.asarray(fit["trace"]["models_kg_m3"][frame_index], dtype=np.float64)
        frame_digest = _digest(model)

    geometry = plan["geometry"]
    bounds = geometry["active_cell_bounds_m"]
    if len(bounds) > MAX_CELLS:
        raise ValueError("view: active-cell cap")
    cells = {"active_cell_indices": geometry["active_cell_indices"].tolist(),
             "bounds_m": bounds.tolist(), "density_kg_m3": None if model is None else model.tolist()}

    plan_request = plan["request"]
    dev_rows = plan["development_rows"]
    station_spec = plan_request["stations"]
    if len(dev_rows) > MAX_STATIONS:
        raise ValueError("view: development station cap")
    observations = request["observations"]
    obs_positions = np.searchsorted(observations["rows"], dev_rows)
    observed = observations["gz_up_mgal"][obs_positions]
    if model is None:
        predicted = residual = None
    else:
        predicted_all = l2._physical_prediction(plan_request, model)
        predicted = predicted_all[dev_rows]
        residual = observed - predicted
    stations = {
        "row_indices": dev_rows.tolist(),
        "ids": [station_spec["station_ids"][i] for i in dev_rows],
        "partition_group_ids": [station_spec["partition_group_ids"][i] for i in dev_rows],
        "receivers_m": station_spec["receivers_m"][dev_rows].tolist(),
        "observed_mgal": observed.tolist(),
        "predicted_mgal": None if predicted is None else predicted.tolist(),
        "residual_observed_minus_predicted_mgal": None if residual is None else residual.tolist(),
        "residual_convention": "observed_minus_predicted",
        "acceleration_unit": "mGal", "vertical_positive": "up",
    }
    candidate_projection = _candidate_projection(result)
    selected = result["selected_index"]
    fit_sha = _digest(fit)
    frame_sha = frame_digest
    runtime_epoch, policy_sha = _runtime_identity(result)
    packet = {
        "schema": SCHEMA,
        "method": {"l2": "l2", "irls": "irls", "corrected": "irls"}[{
            _L2: "l2", _IRLS: "irls", _CORRECTED: "corrected"}[result["schema"]]],
        "calibration_sha256": result_sha,
        "plan_sha256": plan.get("plan_sha256", _digest(plan)),
        "selection": {"status": result["selection_status"], "selected_index": selected,
                      "candidates": candidate_projection},
        "fit": {"index": fit_index, "status": status, "reason": reason,
                "accepted_state_count": state_count,
                "frame_index": frame_index if state_count else None,
                "runtime_epoch": runtime_epoch, "policy_sha256": policy_sha,
                "fit_sha256": fit_sha, "frame_model_sha256": frame_sha,
                "recipe_sha256": _recipe_identity(archive, result),
                "beta_candidate": _number(fit["beta_candidate"]) if "beta_candidate" in fit else None,
                "beta_engine": _number(fit["beta_engine"]) if "beta_engine" in fit else None,
                "terminal": history_row, "terminal_metrics": _terminal_metrics(fit),
                "stage_book": _stage_book(archive, fit)},
        "cells": cells, "stations": stations,
        "history": history,
        "warnings": list(result.get("diagnostics", {}).get("warnings", ())),
        "scope": {"source_verification": "external_required_not_performed_by_solver",
                  "geometry_error_propagated": False, "field_eligible": False,
                  "full_M02_accepted": False, "API_accepted": False,
                  "host_accepted": False, "GPU_accepted": False},
    }
    encoded = json.dumps(packet, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_PACKET_BYTES:
        raise ValueError("view: complete single-frame packet exceeds 4 MiB")
    return packet


def project_archive_bytes(raw, fit_index, frame_index):
    """Transport gate, full native replay, and one bounded inspection projection."""
    if type(raw) is not bytes or not 22 <= len(raw) <= transport.MAX_FILE:
        raise ValueError("view: exact bounded archive bytes required")
    archive = transport.native_from_archive(raw)
    return project_verified_calibration(archive, fit_index, frame_index)
