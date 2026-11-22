"""User-byte binding and executable M04 local workflow controls."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

from magnetic_survey_support import encode, request, rehash


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "data-pipeline" / "run_magnetic_survey.py"


def _source_csv(document) -> bytes:
    width = 3 if document["observations"]["quantity"] == "secondary_enu_nT" else 1
    columns = ["E_nT", "N_nT", "U_nT"] if width == 3 else ["value_nT"]
    values = document["observations"]["values"]["data"]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["row_id", *columns])
    for index, row_id in enumerate(document["acquisition"]["row_ids"]):
        writer.writerow([row_id, *[repr(float(value)) for value in values[index * width:(index + 1) * width]]])
    return output.getvalue().encode("utf-8")


def _request_for_original(original: bytes, document=None) -> bytes:
    document = request() if document is None else document
    digest = hashlib.sha256(original).hexdigest()
    document["source"]["original_sha256"] = digest
    document["source"]["original_bytes"] = len(original)
    document["processing"]["nodes"][0]["input_sha256"] = digest
    return encode(document)


def _run(args, data_root: Path):
    env = os.environ.copy()
    env["GEOPHYSICS_LOCAL_DATA_ROOT"] = str(data_root)
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, env=env, timeout=30)


def test_actual_user_bytes_and_reproduction(tmp_path):
    data_root = tmp_path / "research-data"
    data_root.mkdir()
    document = request()
    original = _source_csv(document)
    original_path = tmp_path / "original.dat"
    original_path.write_bytes(original)
    request_raw = _request_for_original(original)
    request_path = tmp_path / "request.json"
    request_path.write_bytes(request_raw)

    first_path = data_root / "run-a" / "geometry.json"
    first_path.parent.mkdir()
    first = _run(["validate", "--request", request_path, "--original", original_path,
                  "--output", first_path], data_root)
    assert first.returncode == 0, first.stdout + first.stderr
    first_receipt = json.loads(first.stdout)
    assert first_receipt["status"] == "validated"
    assert first_receipt["eligible_for_local_processing"] is True
    assert all(value is False for value in first_receipt["claims"].values())
    assert original_path.read_bytes() == original
    assert b"row_id,E_nT,N_nT,U_nT" not in first_path.read_bytes()

    second_path = data_root / "run-b" / "geometry.json"
    second_path.parent.mkdir()
    second = _run(["validate", "--request", request_path, "--original", original_path,
                   "--output", second_path], data_root)
    assert second.returncode == 0, second.stdout + second.stderr
    second_receipt = json.loads(second.stdout)
    assert second_receipt["geometry_seal_sha256"] == first_receipt["geometry_seal_sha256"]
    assert second_receipt["configuration_sha256"] == first_receipt["configuration_sha256"]
    assert second_path.read_bytes() == first_path.read_bytes()

    wrong_original = tmp_path / "wrong-original.dat"
    wrong_original.write_bytes(original + b"changed\n")
    rejected_output = data_root / "run-c" / "geometry.json"
    rejected_output.parent.mkdir()
    rejected = _run(["validate", "--request", request_path, "--original", wrong_original,
                     "--output", rejected_output], data_root)
    assert rejected.returncode == 2
    assert "do not match" in json.loads(rejected.stdout)["message"]
    assert not rejected_output.exists()


def test_hash_bound_source_cannot_be_paired_with_different_observations(tmp_path):
    data_root = tmp_path / "research-data"
    data_root.mkdir()
    document = request()
    original = _source_csv(document)
    original_path = tmp_path / "original.csv"
    original_path.write_bytes(original)
    document["source"]["original_sha256"] = hashlib.sha256(original).hexdigest()
    document["source"]["original_bytes"] = len(original)
    document["processing"]["nodes"][0]["input_sha256"] = document["source"]["original_sha256"]
    document["observations"]["values"]["data"][0] = 1.0
    rehash(document, "observations/values")
    request_path = tmp_path / "mismatched-request.json"
    request_path.write_bytes(encode(document))

    output = data_root / "mismatch" / "geometry.json"
    output.parent.mkdir()
    result = _run(["validate", "--request", request_path, "--original", original_path,
                   "--output", output], data_root)
    assert result.returncode == 2
    assert "do not match the sealed observations" in json.loads(result.stdout)["message"]
    assert not output.exists()


def test_calibration_orchestration_records_unaccepted_science(monkeypatch, tmp_path, capsys):
    import magnetic_candidate_matrix
    import magnetic_final_refit
    import run_magnetic_survey

    document = request()
    original = _source_csv(document)
    original_path = tmp_path / "original.dat"
    original_path.write_bytes(original)
    request_path = tmp_path / "request.json"
    request_path.write_bytes(_request_for_original(original, document))
    data_root = tmp_path / "research-data"
    data_root.mkdir()
    monkeypatch.setenv("GEOPHYSICS_LOCAL_DATA_ROOT", str(data_root))
    calls = []

    def matrix(raw, output, *, wall_seconds):
        calls.append((raw, output, wall_seconds))
        output.mkdir(parents=True)
        return {"selected": "candidate-01", "claims": {"candidate_matrix_complete": True}}

    def final_refit(raw, matrix_dir, output, *, wall_seconds):
        calls.append((raw, matrix_dir, output, wall_seconds))
        return {"status": "converged", "receipt_sha256": "a" * 64}

    monkeypatch.setattr(magnetic_candidate_matrix, "run_matrix", matrix)
    monkeypatch.setattr(magnetic_final_refit, "run_final_refit", final_refit)
    monkeypatch.setattr(magnetic_final_refit, "verify_final_refit",
                        lambda *args: {"status": "converged", "receipt_sha256": "a" * 64})
    result = run_magnetic_survey.main([
        "calibrate", "--request", str(request_path), "--original", str(original_path),
        "--output-dir", str(data_root / "run-01"),
    ])
    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["status"] == "calibrated"
    assert payload["method_accepted"] is False
    assert payload["online_admitted"] is False
    assert calls[0][0] == request_path.read_bytes()
    assert calls[1][0] == request_path.read_bytes()
    assert calls[1][2].name == "final-refit-candidate-01.json"


def test_output_cannot_escape_external_data_root(tmp_path):
    data_root = tmp_path / "research-data"
    data_root.mkdir()
    document = request()
    original = _source_csv(document)
    original_path = tmp_path / "original.dat"
    original_path.write_bytes(original)
    request_path = tmp_path / "request.json"
    request_path.write_bytes(_request_for_original(original, document))
    outside = tmp_path / "outside.json"
    result = _run(["validate", "--request", request_path, "--original", original_path,
                   "--output", outside], data_root)
    assert result.returncode == 2
    assert not outside.exists()
