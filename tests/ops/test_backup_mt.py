"""Actual parallel MT API integration without mutating its checkout/environment."""

from contextlib import closing
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import ops_recovery as ops


@pytest.fixture(scope="module")
def mt_case(tmp_path_factory):
    selected = os.environ.get("GEOPHYSICS_OPS_MT_CHECKOUT")
    if not selected:
        pytest.skip("Explicit read-only MT checkout required; see ops guide integration command")
    checkout = Path(selected).resolve(strict=True)
    assert (checkout / "app/mt_contract.py").is_file()
    root = tmp_path_factory.mktemp("mt")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MPLCONFIGDIR=str(root / "mpl"))
    env.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("mt_drill.py")), str(checkout), str(root)],
                            cwd=checkout, env=env, capture_output=True, timeout=240)
    assert result.returncode == 0, result.stderr.decode(errors="replace")[-8000:]
    return root


def test_real_mt_recovery(mt_case):
    evidence = ops.read_json(mt_case / "integration.json")
    assert evidence["receipt"]["removed_file_count"] == 4
    assert evidence["receipt"]["surviving_file_count"] == 7
    assert evidence["receipt"]["host_drill"] == "not_run"


VARIANTS = ["modality", "parser", "dataset_schema", "dataset_extra", "axis", "dimension", "raw_bytes",
            "source", "frame", "sign", "variance", "components", "method", "failed_method", "request_schema",
            "request_identity", "parameter_extra", "parameter_boolean", "qc_job", "qc_hash", "result_schema",
            "result_extra", "result_raw", "environment", "frequency", "screen_schema", "screen_extra",
            "screen_truth", "screen_inverse", "tensor", "inverse_schema", "inverse_method", "inverse_truth",
            "inverse_thickness", "inverse_mask", "inverse_model", "inverse_samples", "inverse_extra",
            "uncertainty_extra", "provenance_extra", "provenance_rotation", "m05_inverse", "m05_schema", "m05_parameter",
            "m05_qc_hash", "m05_screen_inverse", "result_axis", "result_dimensions", "request_extra", "request_raw"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_mt_unknown_variants(mt_case, tmp_path, variant):
    private = tmp_path / "private"
    shutil.copytree(mt_case / "restored/private", private)
    database = private / "api.sqlite3"
    with closing(sqlite3.connect(database)) as db, db:
        db.row_factory = sqlite3.Row
        dataset = dict(db.execute("SELECT * FROM observation_datasets WHERE modality='edi_transfer_function'").fetchone())
        method = ops.M05 if variant.startswith("m05_") else ops.M06
        job = dict(db.execute("SELECT * FROM processing_jobs WHERE method_id=?", (method,)).fetchone())
        data_path, result_path = private / dataset["storage_key"], private / job["result_key"]
        data, result = ops.read_json(data_path), ops.read_json(result_path)
        request = json.loads(job["request_json"])
        # Deliberately re-hash mutations: these gates must reject contract drift, not merely broken content hashes.
        if variant == "modality":
            data["modality"] = "unknown"
            db.execute("UPDATE observation_datasets SET modality='unknown' WHERE id=?", (dataset["id"],))
        elif variant == "parser":
            data["parser_version"] = "edi-strict-envelope/v2"
            db.execute("UPDATE observation_datasets SET parser_version=? WHERE id=?", (data["parser_version"], dataset["id"]))
        elif variant == "dataset_schema":
            data["schema"] += "-unknown"
        elif variant == "dataset_extra":
            data["observed_mgal"] = []
        elif variant == "axis":
            data["axis_order"] = ["station"]
        elif variant == "dimension":
            data["dimensions"] = {"station": 24}
        elif variant == "raw_bytes":
            data["parent_raw_bytes"] += 1
        elif variant == "source":
            data["source"]["provider"] = "unbound"
        elif variant in ("frame", "sign", "variance", "components"):
            if variant == "frame":
                data["physical_metadata"]["component_frame"] = "unknown"
            else:
                name = {"sign": "sign_convention", "variance": "variance_convention", "components": "tensor_components"}[variant]
                data["physical_metadata"]["geometry"][name] = ["unknown"] if variant == "components" else "unknown"
        elif variant in ("method", "failed_method"):
            db.execute("UPDATE processing_jobs SET method_id=? WHERE id=?", ("mt.edi-unknown/v1", job["id"]))
            request["method_id"] = result["method_id"] = "mt.edi-unknown/v1"
            if variant == "failed_method":
                db.execute("UPDATE processing_jobs SET state='failed',result_key=NULL,result_sha256=NULL,result_bytes=NULL WHERE id=?", (job["id"],))
                result_path.unlink()
        elif variant == "request_schema":
            request["schema"] += "-unknown"
        elif variant == "request_identity":
            request["job_id"] = dataset["id"]
        elif variant == "parameter_extra":
            request["parameters"]["unknown"] = 1
        elif variant == "parameter_boolean":
            request["parameters"]["seed"] = True
        elif variant == "qc_job":
            request["parameters"]["qc_job_id"] = job["id"]
        elif variant == "qc_hash":
            request["qc_screen_sha256"] = result["qc_screen_sha256"] = "0" * 64
        elif variant == "result_schema":
            result["schema"] += "-unknown"
        elif variant == "result_extra":
            result["model"] = []
        elif variant == "result_raw":
            result["raw_bytes"] += 1
        elif variant == "environment":
            result["environment"]["packages"]["unknown"] = "1"
            result["environment_sha256"] = hashlib.sha256(ops.canonical(result["environment"])).hexdigest()
        elif variant == "frequency":
            result["frequency_hz"][0] = -1
        elif variant == "screen_schema":
            result["screen"]["schema"] += "-unknown"
        elif variant == "screen_extra":
            result["screen"]["unknown"] = 1
        elif variant == "screen_truth":
            result["screen"]["truth"] = [100]
        elif variant == "screen_inverse":
            result["screen"]["inversion_performed"] = True
        elif variant == "tensor":
            result["screen"]["tensor"]["real"] = []
        elif variant == "inverse_schema":
            result["inverse"]["schema"] += "-unknown"
        elif variant == "inverse_method":
            result["inverse"]["methods"]["unknown"] = {}
        elif variant == "inverse_truth":
            result["inverse"]["truth"] = [100]
        elif variant == "inverse_thickness":
            result["inverse"]["thickness"] = []
        elif variant == "inverse_mask":
            result["inverse"]["active"][0] = False
        elif variant == "inverse_model":
            result["inverse"]["methods"]["mt-lm"]["model"] = [True, 10]
        elif variant == "inverse_samples":
            result["inverse"]["methods"]["mt-lm"]["uncertainty"]["samples"] = []
        elif variant == "inverse_extra":
            result["inverse"]["methods"]["mt-lm"]["unknown"] = 1
        elif variant == "uncertainty_extra":
            result["inverse"]["methods"]["mt-lm"]["uncertainty"]["unknown"] = 1
        elif variant == "provenance_extra":
            result["screen"]["provenance"]["unknown"] = 1
        elif variant == "provenance_rotation":
            result["screen"]["provenance"]["original_rotation_deg"][0] += 1
        elif variant == "m05_inverse":
            result["inverse"] = {}
        elif variant == "m05_schema":
            result["schema"] += "-unknown"
        elif variant == "m05_parameter":
            request["parameters"] = {"unknown": 1}
        elif variant == "m05_qc_hash":
            result["qc_screen_sha256"] = "0" * 64
        elif variant == "m05_screen_inverse":
            result["screen"]["inversion_performed"] = True
        elif variant == "result_axis":
            result["axis_order"] = ["station"]
        elif variant == "result_dimensions":
            result["dimensions"] = {"station": 24}
        elif variant == "request_extra":
            request["unknown"] = 1
        elif variant == "request_raw":
            request["raw_asset_id"] = dataset["id"]
        else:
            raise AssertionError(variant)
        data_bytes = ops.canonical(data)
        data_path.write_bytes(data_bytes)
        dataset_hash = hashlib.sha256(data_bytes).hexdigest()
        db.execute("UPDATE observation_datasets SET sha256=?,byte_count=? WHERE id=?", (dataset_hash, len(data_bytes), dataset["id"]))
        for other in db.execute("SELECT * FROM processing_jobs WHERE dataset_id=?", (dataset["id"],)).fetchall():
            other_request = request if other["id"] == job["id"] else json.loads(other["request_json"])
            other_request["dataset_sha256"] = dataset_hash
            request_hash = hashlib.sha256(ops.canonical(other_request)).hexdigest()
            db.execute("UPDATE processing_jobs SET request_json=?,request_sha256=?,dataset_sha256=? WHERE id=?",
                       (ops.canonical(other_request).decode(), request_hash, dataset_hash, other["id"]))
            if other["result_key"]:
                path = private / other["result_key"]
                payload = result if other["id"] == job["id"] else ops.read_json(path)
                payload.update(dataset_sha256=dataset_hash, request_sha256=request_hash, parameters=other_request["parameters"])
                encoded = ops.canonical(payload)
                path.write_bytes(encoded)
                db.execute("UPDATE processing_jobs SET result_sha256=?,result_bytes=? WHERE id=?",
                           (hashlib.sha256(encoded).hexdigest(), len(encoded), other["id"]))
    with closing(ops.open_database(database)) as db, pytest.raises(ops.RecoveryError):
        ops.inventory(db, private, ops.Limits())
    # Full backup path must refuse before publishing any success output.
    template = ops.read_json(mt_case / "integration.json")["args"]
    args = SimpleNamespace(**template)
    args.source, args.database = str(private), str(database)
    args.fixture_root = str(tmp_path.parent.parent)
    args.scratch_parent = str(mt_case / "scratch")
    args.new_output = str(tmp_path / "rejected")
    args.maintenance_proof = str(tmp_path / "proof.json")
    ops.write_new(Path(args.maintenance_proof), ops.canonical({
        "schema": ops.PROOF_SCHEMA, "source": args.source, "database": args.database,
        "deployment_id": args.deployment_id, "mode": "fixture", "issued_at": ops.stamp(),
        "expires_at": (ops.now() + timedelta(minutes=30)).isoformat(), "ingress_blocked": True,
        "all_writers_accounted": True, "units": [],
    }))
    with pytest.raises(ops.RecoveryError):
        ops.capture(args)
    assert not Path(args.new_output).exists()


def test_mt_unknown_restore_schema(mt_case, tmp_path):
    """An authenticated/re-hashed archive still cannot introduce a new MT result schema."""
    template = ops.read_json(mt_case / "integration.json")["args"]
    age = ops.Age(Path(template["age_binary"]), Path(template["identity"]), template["recipient"], ops.Limits())
    before = (mt_case / "backup/snapshot.age").read_bytes()
    archive = tmp_path / "original.tar"
    age.decrypt(mt_case / "backup/snapshot.age", archive, ops.Limits().archive)
    private = tmp_path / "private"
    manifest = ops.extract_archive(archive, private, ops.Limits())
    with closing(sqlite3.connect(private / "api.sqlite3")) as db, db:
        key = db.execute("SELECT result_key FROM processing_jobs WHERE method_id=?", (ops.M06,)).fetchone()[0]
        result = ops.read_json(private / key)
        result["inverse"]["schema"] = "inverse-earth/edi-1d/v2"
        encoded = ops.canonical(result)
        (private / key).write_bytes(encoded)
        result_hash = hashlib.sha256(encoded).hexdigest()
        db.execute("UPDATE processing_jobs SET result_sha256=?,result_bytes=? WHERE result_key=?", (result_hash, len(encoded), key))
    for name in (key, "api.sqlite3"):
        manifest["files"][name].update(sha256=ops.sha_file(private / name, ops.Limits().file), bytes=(private / name).stat().st_size)
    changed_tar, snapshot = tmp_path / "changed.tar", tmp_path / "changed.age"
    ops.make_archive(changed_tar, manifest, private)
    age.encrypt(changed_tar, snapshot)
    snapshot_hash = ops.sha_file(snapshot, ops.Limits().archive)
    plain_authority = tmp_path / "authority.json"
    age.decrypt(mt_case / "backup/authority.age", plain_authority, ops.JSON_CAP)
    authority = ops.read_json(plain_authority)
    authority["snapshots"][0]["sha256"] = snapshot_hash
    updated = tmp_path / "updated.json"
    ops.write_new(updated, ops.canonical(authority))
    ciphertext_authority = tmp_path / "authority.age"
    age.encrypt(updated, ciphertext_authority)
    args = ops.parser().parse_args([
        "restore", "--deployment-id", template["deployment_id"], "--age-binary", template["age_binary"],
        "--identity", template["identity"], "--scratch-parent", template["scratch_parent"],
        "--snapshot", str(snapshot), "--snapshot-sha256", snapshot_hash,
        "--authority", str(ciphertext_authority), "--authority-sha256", ops.sha_file(ciphertext_authority, ops.JSON_CAP),
        "--new-target", str(tmp_path / "rejected"), "--fixture-root", str(tmp_path.parent.parent),
    ])
    with pytest.raises(ops.RecoveryError, match="unknown_or_changed_result_schema"):
        ops.restore(args)
    assert not (tmp_path / "rejected").exists()
    assert (mt_case / "backup/snapshot.age").read_bytes() == before
