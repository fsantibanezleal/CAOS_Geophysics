"""M11 live custody/accounting registration and deletion refusal boundary."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

import numpy as np
import pytest
from alembic import command

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "data-pipeline"), str(ROOT / "tests" / "numerics"), str(ROOT / "tests" / "ops")]

import joint_survey_evaluation as evaluation
import joint_survey_plan as planner
from app.physical_classifier import classify_snapshot
from app.physical_contract import byte_sha, canonical
from app.physical_joint_custody import scan_stream
from app.physical_joint_native_contract import METHOD_ID, MODALITY, PARSER
from app.physical_posix import PrivateFiles
from app.physical_project_deletion import prepare_project_deletion
from physical_union_fixture import capsule
from test_joint_survey_intake import fixture as write_development


class MemoryFiles:
    """Exact byte map for snapshot logic; makes no native filesystem claim."""

    def __init__(self, bodies):
        self.bodies = bodies

    def read(self, key, *, cap, expected_bytes=None, expected_sha256=None):
        body = self.bodies[key]
        assert len(body) <= cap
        assert expected_bytes is None or len(body) == expected_bytes
        assert expected_sha256 is None or byte_sha(body) == expected_sha256
        return body

    def scan_joint_member(self, key, **arguments):
        return scan_stream(__import__("io").BytesIO(self.bodies[key]), **arguments)

    def names(self, key, *, limit):
        raise FileNotFoundError(key)

    def census(self, expected, *, empty_directories=()):
        assert set(expected) == set(self.bodies)
        return {key: dict(bytes=len(body), sha256=byte_sha(body)) for key, body in self.bodies.items()}


def _insert(connection, table, values):
    columns = tuple(values)
    connection.execute(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        tuple(values[key] for key in columns),
    )


@pytest.fixture
def joint_case(tmp_path, monkeypatch):
    owner, project = str(uuid4()), str(uuid4())
    dataset_id, job_id = str(uuid4()), str(uuid4())
    source_dir = tmp_path / "development"
    source_dir.mkdir()
    development, survey = write_development(source_dir, provided=False)
    plan = planner.plan_joint_survey(survey)
    sealed_dir = tmp_path / "sealed"
    sealed = {
        **{f"{modality}_rows": plan[modality]["sealed_rows"] for modality in ("gravity", "magnetic")},
        **{f"{modality}_observed": np.zeros(len(plan[modality]["sealed_rows"]))
           for modality in ("gravity", "magnetic")},
        **{f"{modality}_noise": np.ones(len(plan[modality]["sealed_rows"]))
           for modality in ("gravity", "magnetic")},
    }
    sealed_manifest = evaluation.write_joint_sealed(str(sealed_dir), plan, sealed)
    development["sealed_manifest"] = sealed_manifest
    (source_dir / "request.json").write_bytes(json.dumps(
        development, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
    sealed_payload = json.loads((sealed_dir / "sealed.json").read_bytes())

    bodies = {}
    members = {"development": {}, "sealed": {}}
    raw_rows, source_rows, dependency_rows = [], [], []
    primary_asset = primary_sha = None
    row_count = sum(len(survey[modality]["receivers_m"])
                    for modality in ("gravity", "magnetic"))
    for role, directory, manifest in (("development", source_dir, development),
                                      ("sealed", sealed_dir, sealed_payload)):
        descriptors = manifest["arrays"]
        for path in sorted(directory.iterdir()):
            name = path.name
            body = path.read_bytes()
            asset_id, source_id = str(uuid4()), str(uuid4())
            digest = byte_sha(body)
            descriptor = descriptors.get(name[:-4]) if name.endswith(".npy") else None
            physical_metadata = canonical(dict(schema="joint-native-member-1", role=role, name=name,
                descriptor=descriptor, scientific_values_decoded=False, scientific_accepted=False)).decode()
            source = dict(id=source_id, owner_id=owner, project_id=project, version=1,
                declared_format="joint_native", sha256=digest, expected_bytes=len(body),
                private_storage_permission="attested", rights_decision="mirror")
            asset = dict(id=asset_id, owner_id=owner, project_id=project, source_id=source_id,
                sha256=digest, byte_count=len(body), detected_format="joint_native", filename=name,
                validation_status="raw_metadata_checked", storage_key=f"projects/{owner}/{project}/{asset_id}",
                physical_metadata=physical_metadata)
            bodies[asset["storage_key"]] = body
            raw_rows.append(asset)
            source_rows.append(source)
            binding = dict(asset_id=asset_id, source_id=source_id, source_version=1, raw_sha256=digest,
                raw_bytes=len(body), rights_decision="mirror", private_storage_permission="attested",
                descriptor=descriptor)
            members[role][name] = binding
            dependency_rows.append(dict(dataset_id=dataset_id, role=role, name=name, asset_id=asset_id,
                source_id=source_id, raw_sha256=digest, raw_bytes=len(body), source_version=1))
            if role == "development" and name == "request.json":
                primary_asset, primary_sha = asset_id, digest

    dataset_payload = dict(schema="geophysics.joint-native-dataset/v1", dataset_id=dataset_id, version=1,
        owner_id=owner, project_id=project, raw_asset_id=primary_asset, parent_raw_sha256=primary_sha,
        parser_version=PARSER, modality=MODALITY, dimensions=dict(source_observations=row_count),
        manifests=dict(development=development, sealed=sealed_payload), members=members,
        qc_verdict="structural_native_members_only", scientific_values_decoded=False, scientific_accepted=False)
    dataset_body = canonical(dataset_payload)
    dataset_sha = byte_sha(dataset_body)
    dataset_key = f"derived/{owner}/{project}/datasets/{dataset_id}.json"
    bodies[dataset_key] = dataset_body
    dataset_row = dict(id=dataset_id, owner_id=owner, project_id=project, raw_asset_id=primary_asset,
        version=1, parser_version=PARSER, modality=MODALITY, row_count=row_count, raw_sha256=primary_sha,
        sha256=dataset_sha, byte_count=len(dataset_body), storage_key=dataset_key, kind="root",
        root_dataset_id=dataset_id, parent_dataset_id=None, payload_schema="geophysics.joint-native-dataset/v1")

    request = dict(schema="joint-native-custody-fixture/v1", fixture=True)
    request_body = canonical(request)
    request_sha = byte_sha(request_body)
    output_name = "result/receipt.npy"
    output_body = b"opaque retained M11 transport fixture; no scientific interpretation"
    output_sha = byte_sha(output_body)
    output_key = f"derived/{owner}/{project}/joint/{job_id}/{output_name}"
    bodies[output_key] = output_body
    result_key = f"derived/{owner}/{project}/results/{job_id}.json"
    result_payload = dict(schema="geophysics.joint-result-custody/v1", state="failed", job_id=job_id,
        owner_id=owner, project_id=project, dataset_id=dataset_id, dataset_sha256=dataset_sha,
        method_id=METHOD_ID, request_sha256=request_sha, native_bytes=len(output_body),
        members={output_name: dict(byte_count=len(output_body), sha256=output_sha)},
        scientific_acceptance=False, authenticity_verified=False, public_activation=False)
    result_body = canonical(result_payload)
    bodies[result_key] = result_body
    job_row = dict(id=job_id, owner_id=owner, project_id=project, dataset_id=dataset_id,
        dataset_sha256=dataset_sha, method_id=METHOD_ID, request_json=request_body.decode(),
        request_sha256=request_sha, preflight="{}", state="failed", cancel_requested=0,
        result_key=result_key, result_sha256=byte_sha(result_body), result_bytes=len(result_body),
        error_code="fixture_failure", error_message="retained fixture", created_at="2026-10-25T00:00:00+00:00",
        started_at="2026-10-25T00:00:00+00:00", finished_at="2026-10-25T00:00:01+00:00")
    artifact_row = dict(job_id=job_id, name=output_name, owner_id=owner, project_id=project,
        dataset_id=dataset_id, dataset_sha256=dataset_sha, method_id=METHOD_ID, request_sha256=request_sha,
        storage_key=output_key, byte_count=len(output_body), sha256=output_sha)

    config, database = capsule(tmp_path / "physical-union")
    monkeypatch.setenv("GEOPHYSICS_DB_PATH", str(database))
    monkeypatch.setenv("GEOPHYSICS_CANDIDATE_ROOT", str(tmp_path))
    command.upgrade(config, "0006_joint_artifacts")
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys=ON")
    timestamp = "2026-10-25T00:00:00+00:00"
    _insert(connection, "user", dict(id=owner, email="m11-fixture@example.invalid", hashed_password="unused",
        is_active=1, is_superuser=0, is_verified=0))
    _insert(connection, "projects", dict(id=project, owner_id=owner, name="M11 fixture", description="",
        created_at=timestamp, updated_at=timestamp))
    _insert(connection, "account_usage", dict(user_id=owner, raw_bytes=sum(row["byte_count"] for row in raw_rows)))
    for source in source_rows:
        _insert(connection, "source_records", dict(id=source["id"], project_id=project, owner_id=owner,
            original_filename=next(row["filename"] for row in raw_rows if row["source_id"]==source["id"]),
            version=1, provider="fixture", exact_url=None, doi=None, citation="fixture", retrieved_at=timestamp,
            rights_statement="private fixture custody", rights_decision="mirror", private_storage_permission="attested",
            declared_format="joint_native", expected_bytes=source["expected_bytes"], sha256=source["sha256"],
            attribution="fixture"))
    for asset in raw_rows:
        _insert(connection, "raw_assets", dict(id=asset["id"], project_id=project, owner_id=owner,
            source_id=asset["source_id"], filename=asset["filename"], client_mime="application/octet-stream",
            detected_format="joint_native", byte_count=asset["byte_count"], sha256=asset["sha256"],
            storage_key=asset["storage_key"], physical_metadata=asset["physical_metadata"],
            validation_status="raw_metadata_checked", created_at=timestamp))
    _insert(connection, "physical_dataset_families", dict(root_dataset_id=dataset_id, raw_asset_id=primary_asset,
        project_id=project, owner_id=owner, parser_version=PARSER, state="published", next_ordinal=2,
        published_count=1, reserved_count=0, created_us=1))
    _insert(connection, "observation_datasets", dict(dataset_row, created_at=timestamp))
    for dependency in dependency_rows:
        _insert(connection, "joint_dataset_sources", dependency)
    _insert(connection, "processing_jobs", job_row)
    _insert(connection, "joint_result_artifacts", artifact_row)
    connection.commit()
    rows = dict(
        projects=[dict(id=project, owner_id=owner)], raw_assets=raw_rows, source_records=source_rows,
        observation_datasets=[dataset_row], processing_jobs=[job_row],
        joint_dataset_sources=dependency_rows, joint_result_artifacts=[artifact_row],
    )
    return dict(connection=connection, files=MemoryFiles(bodies), rows=rows, owner=owner, project=project,
        source_policy="e"*64, ids=(str(uuid4()), str(uuid4())))


def test_live_classifier_quota_and_deletion_refusal_for_populated_m11(joint_case):
    connection, files, rows = joint_case["connection"], joint_case["files"], joint_case["rows"]
    owner, project = joint_case["owner"], joint_case["project"]
    connection.execute("BEGIN IMMEDIATE")
    before = connection.total_changes
    try:
        result = classify_snapshot(connection, files, approved_manifests={}, approved_installations={},
            native_metadata={}, expected_source_policy_sha256=joint_case["source_policy"])
        assert result.classification == "coherent_committed", result.reason
        charge = result.account_charges[owner]
        assert charge["raw"] == sum(r["byte_count"] for r in rows["raw_assets"])
        assert charge["datasets"] == rows["observation_datasets"][0]["byte_count"]
        assert charge["joint_members"] == rows["joint_result_artifacts"][0]["byte_count"]
        assert charge["joint_terminal_indices"] == rows["processing_jobs"][0]["result_bytes"]
        assert charge["joint_active"] == 0
        assert charge["total"] == (charge["raw"] + charge["datasets"] + charge["joint_members"]
            + charge["joint_terminal_indices"])
        assert result.operations[rows["processing_jobs"][0]["id"]] == "retain_nonsuccess"
        assert result.inventory_sha256 and connection.total_changes == before

        with pytest.raises(ValueError, match="current_deletion_joint_custody_unrepresentable"):
            prepare_project_deletion(connection, files=files, owner_id=owner, project_id=project,
                batch_id=joint_case["ids"][0], receipt_id=joint_case["ids"][1], created_us=1,
                expected_source_policy_sha256=joint_case["source_policy"], approved_manifests={},
                approved_installations={}, native_metadata={}, profile_records=[])
        assert connection.total_changes == before
        assert connection.execute("SELECT count(*) FROM physical_custody_batches").fetchone() == (0,)
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.skipif(os.name != "posix", reason="PrivateFiles enforces POSIX descriptor semantics")
def test_private_file_joint_scanner_streams_and_rejects_changed_digest(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    body = b"small opaque native member"
    (root / "member.npy").write_bytes(body)
    (root / "member.npy").chmod(0o600)
    files = PrivateFiles(root)
    try:
        assert files.scan_joint_member("member.npy", byte_count=len(body), sha256=byte_sha(body),
            descriptor=None) == dict(bytes=len(body), sha256=byte_sha(body))
        with pytest.raises(ValueError):
            files.scan_joint_member("member.npy", byte_count=len(body), sha256="0"*64, descriptor=None)
    finally:
        files.close()
