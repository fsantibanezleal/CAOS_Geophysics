"""Real, already inspected STEAD display replay, not a new untouched study.

The response-corrected ordinary method cannot consume normalized STEAD counts
without instrument metadata. Here ONLY the frozen counts comparator is replayed
against independent direct sums on the exact same 23 inputs; M13 is not run.
"""

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from phase_picking import classical_stalta_picks

ASSETS = ROOT / "data/derived/phase/browser-assets/stead"
MANIFEST_SHA = "d4d2b5b1a98d3a7a2077baab7750c8a96e4b5152b6930e4a09ae4bdc97db8394"
SELECTION_SHA = "0d15ae67096df0a39761e1d2a5e7ab110d6a8eb862adba132d0d0a7e391d9cd8"
COMPARATOR_SHA = "daef04c71c81c6c3b63bdaab72d6ccd74445bb2ee3268ff52004b3bae393938a"


def pinned_json(path, expected):
    with path.open("rb") as handle:
        raw = handle.read(2097153)
    assert len(raw) <= 2097152 and hashlib.sha256(raw).hexdigest() == expected
    return json.loads(raw)


def direct_comparator(values):
    """Scalar direct window oracle; no cumulative sums or picker library call."""
    energy = [sum(float(x) ** 2 for x in row) for row in values]
    characteristic = [0.0] * len(values)
    for i in range(119, len(values)):
        characteristic[i] = (math.fsum(energy[i - 11:i + 1]) / 12) / max(
            math.fsum(energy[i - 119:i + 1]) / 120, 1e-12
        )
    crossings = [i for i in range(1, len(values)) if characteristic[i] >= 2.5 > characteristic[i - 1]]
    first = crossings[0] if crossings else None
    second = next((i for i in crossings if i >= first + 40), None) if first is not None else None
    # Preserve the frozen comparator's index*dt operation, not a different
    # division rounding dialect (702*0.01 is not bit-identical to 702/100).
    return {"P": first * 0.01 if first is not None else None,
            "S": second * 0.01 if second is not None else None}, characteristic


def report():
    manifest = pinned_json(ASSETS / "manifest.json", MANIFEST_SHA)
    selection = pinned_json(ROOT / "data/derived/phase/stead-browser-selection-profile.json", SELECTION_SHA)
    assert hashlib.sha256((ROOT / "data-pipeline/phase_picking.py").read_bytes()).hexdigest() == COMPARATOR_SHA
    assert manifest["selection"]["selected_before_heldout_scoring"] is True
    assert selection["test_performance_known_when_selected"] is False
    assert selection["chosen_using_trace_metadata_only"] is True
    assert selection["display_ids_sha256"] == manifest["selection"]["display_ids_sha256"]
    records = manifest["records"]
    assert len(records) == 24 and len({r["trace_id"] for r in records}) == 24
    assert hashlib.sha256("\n".join(sorted(r["trace_id"] for r in records)).encode()).hexdigest() == selection["display_ids_sha256"]
    rows = []
    maximum = 0.0
    metrics = {phase: {"reference_count": 0, "correct_within_0p5s": 0, "outside_tolerance": 0,
                      "missed": 0, "false_without_reference": 0, "timing_signed_s": []} for phase in ("P", "S")}
    for index, row in enumerate(records):
        if row["status"] == "qc-valid":
            assert row["waveform_file"] == f"trace-{index:02d}.f32" and row["waveform_bytes"] == 72000
            with (ASSETS / row["waveform_file"]).open("rb") as handle:
                raw = handle.read(72001)
            assert len(raw) == 72000 and hashlib.sha256(raw).hexdigest() == row["waveform_sha256"]
            values = np.frombuffer(raw, dtype="<f4").reshape(3, 6000).T
            assert np.isfinite(values).all()
            before = hashlib.sha256(memoryview(np.frombuffer(raw, dtype="<f4")).cast("B")).hexdigest()
            predicted = classical_stalta_picks(values, sample_interval_s=0.01)
            oracle, direct_cf = direct_comparator(values)
            # Independently check the exact existing cumulative-window recurrence
            # as well as its final crossing indices; no threshold epsilon/nudge.
            energy = np.sum(np.square(values.astype(np.float64)), axis=1)
            cumulative = np.concatenate(([0.0], np.cumsum(energy)))
            short = (cumulative[12:] - cumulative[:-12]) / 12
            long = (cumulative[120:] - cumulative[:-120]) / 120
            cumulative_cf = np.zeros(6000)
            cumulative_cf[119:] = short[108:] / np.maximum(long, 1e-12)
            np.testing.assert_allclose(cumulative_cf, direct_cf, rtol=1e-9, atol=1e-9)
            maximum = max(maximum, float(np.max(np.abs(cumulative_cf - direct_cf))))
            assert predicted == oracle
            assert hashlib.sha256(raw).hexdigest() == before
        else:
            assert row["status"] == "qc-rejected"
            assert "waveform_file" not in row and "waveform_sha256" not in row
            predicted = oracle = {"P": None, "S": None}
        residuals = {}
        for phase in ("P", "S"):
            reference, pick = row[f"analyst_{phase.lower()}_s"], predicted[phase]
            metric = metrics[phase]
            residual = None
            if reference is None:
                metric["false_without_reference"] += int(pick is not None)
            else:
                metric["reference_count"] += 1
                if pick is None:
                    metric["missed"] += 1
                else:
                    residual = pick - reference
                    metric["timing_signed_s"].append(residual)
                    metric["correct_within_0p5s" if abs(residual) <= 0.5 else "outside_tolerance"] += 1
            residuals[phase] = residual
        rows.append({"trace_id": row["trace_id"], "status": row["status"],
                     "waveform_sha256": row.get("waveform_sha256"), "reference_P_s": row["analyst_p_s"],
                     "reference_S_s": row["analyst_s_s"], "frozen_counts_comparator": predicted,
                     "direct_window_oracle": oracle, "signed_residual_s": residuals})
    return {
        "schema": "caos.m08-heldout-display-replay.v1", "status": "replayed",
        "scope": "Already inspected preselected display subset; not a new untouched accuracy study",
        "method": "frozen M08 normalized-counts provisional P/S comparator, not waveform-qc-classical/v1",
        "source": manifest["source"], "manifest_sha256": MANIFEST_SHA, "selection_sha256": SELECTION_SHA,
        "comparator_sha256": COMPARATOR_SHA, "test_selection_sha256": selection["test_selection_sha256"],
        "display_ids_sha256": selection["display_ids_sha256"], "selected": 24, "valid": 23, "qc_rejected": 1,
        "quake_selected": 16, "noise_selected": 8, "fixed_parameters": {
            "fs_hz": 100, "sta_samples": 12, "lta_samples": 120, "threshold": 2.5,
            "denominator_floor": 1e-12, "minimum_ps_samples": 40, "reference_tolerance_s": 0.5,
        }, "same_input_pick_agreement": True, "characteristic_max_abs_difference": maximum,
        "oracle_tolerance": {"rtol": 1e-9, "atol": 1e-9}, "metrics": metrics, "records": rows,
        "response_corrected_method_evaluated": False, "M13_executed": False, "field_truth": None,
        "method_accepted": False, "host_admitted": False,
    }


def test_real_heldout_same_input_direct_comparison_retains_failures():
    replay = report()
    assert replay["valid"] + replay["qc_rejected"] == replay["selected"]
    for metric in replay["metrics"].values():
        assert metric["reference_count"] == 16
        assert metric["correct_within_0p5s"] + metric["outside_tolerance"] + metric["missed"] == 16
    assert replay["same_input_pick_agreement"] is True and replay["M13_executed"] is False


def test_compact_replay_artifact_matches_actual_same_inputs():
    artifact = ROOT / "data/derived/waveform/m08-heldout-display-replay.json"
    assert json.loads(artifact.read_bytes()) == report()
