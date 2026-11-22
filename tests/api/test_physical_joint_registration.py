"""M11 live custody, accounting, and retained project-deletion projection."""

from __future__ import annotations

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
from app.physical_deleted_inventory import validate_current_inventory
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
        if not set(self.bodies) <= set(expected):
            raise ValueError("fixture_unknown_namespace")
        if not all(not record.get("required", True) or key in self.bodies
                   for key, record in expected.items()):
            raise ValueError("fixture_missing_file")
        if not all(len(self.bodies[key]) == record["bytes"]
                   and byte_sha(self.bodies[key]) == record["sha256"]
                   for key, record in expected.items() if key in self.bodies and record["bytes"] is not None):
            raise ValueError("fixture_file_identity")
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


def test_live_classifier_quota_and_m11_deletion_projection(joint_case):
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

        # These exact paths are live M11 custody: all source copies, the
        # dataset index, the failed terminal result index, and its member.
        # Deletion must not silently omit any of them from the tombstone.
        assert {r["storage_key"] for r in rows["raw_assets"]} <= set(files.bodies)
        assert rows["observation_datasets"][0]["storage_key"] in files.bodies
        assert rows["processing_jobs"][0]["result_key"] in files.bodies
        assert rows["joint_result_artifacts"][0]["storage_key"] in files.bodies

        plan = prepare_project_deletion(connection, files=files, owner_id=owner, project_id=project,
            batch_id=joint_case["ids"][0], receipt_id=joint_case["ids"][1], created_us=1,
            expected_source_policy_sha256=joint_case["source_policy"], approved_manifests={},
            approved_installations={}, native_metadata={}, profile_records=[])
        inventory, custody = plan["inventory"], plan["custody"]
        assert inventory["schema"] == "geophysics.physical-deleted-inventory/v2"
        assert {r["asset_id"] for r in inventory["joint_raw_assets"]} == {r["id"] for r in rows["raw_assets"]}
        assert inventory["joint_sources"]
        assert inventory["joint_result_indexes"][0]["state"] == "failed"
        assert inventory["joint_result_members"][0]["storage_key"] == rows["joint_result_artifacts"][0]["storage_key"]
        assert custody["schema"] == "geophysics.physical-custody/v3"
        assert {s["leaf"] for s in custody["initial_files"]} >= {
            f"results/{rows['processing_jobs'][0]['id']}.json",
            f"joint/{rows['processing_jobs'][0]['id']}/{rows['joint_result_artifacts'][0]['name']}",
        }
        assert connection.total_changes > before
        assert connection.execute("SELECT count(*) FROM physical_custody_batches").fetchone() == (1,)
        receipt = dict(owner_id=owner, project_id=project,
            asset_manifest=[dict(asset_id=r["asset_id"],sha256=r["sha256"],byte_count=r["bytes"])
                            for r in inventory["raw_assets"]],
            derived_manifest=(
                [dict(kind="dataset",id=r["dataset_id"],sha256=r["sha256"],byte_count=r["bytes"])
                 for r in inventory["datasets"]] +
                [dict(kind="result",id=r["job_id"],sha256=r["sha256"],byte_count=r["bytes"])
                 for r in inventory["joint_result_indexes"]] +
                [dict(kind="joint_artifact",id=r["job_id"],name=r["name"],
                    relative_path=f"joint/{r['job_id']}/{r['name']}",sha256=r["sha256"],byte_count=r["bytes"])
                 for r in inventory["joint_result_members"]]))
        assert validate_current_inventory(inventory,receipt,
            expected_source_policy_sha256=joint_case["source_policy"],approved_installations={}) is None
        corrupt = dict(inventory)
        corrupt["joint_result_members"] = [dict(inventory["joint_result_members"][0],sha256="f"*64)]
        with pytest.raises(ValueError,match="current_deletion_joint_index_member_projection"):
            validate_current_inventory(corrupt,receipt,
                expected_source_policy_sha256=joint_case["source_policy"],approved_installations={})
    finally:
        connection.rollback()
        connection.close()


def test_queued_m11_job_is_charged_once_from_the_joint_audit(joint_case):
    connection, files, rows = joint_case["connection"], joint_case["files"], joint_case["rows"]
    owner = joint_case["owner"]
    job = rows["processing_jobs"][0]
    result_keys = [job["result_key"], rows["joint_result_artifacts"][0]["storage_key"]]
    connection.execute("UPDATE processing_jobs SET state='queued',cancel_requested=0,worker_id=NULL,"
        "result_key=NULL,result_sha256=NULL,result_bytes=NULL,error_code=NULL,error_message=NULL,"
        "started_at=NULL,finished_at=NULL,wall_ms=NULL,peak_rss_bytes=NULL,scratch_bytes=NULL WHERE id=?",
        (job["id"],))
    connection.execute("DELETE FROM joint_result_artifacts WHERE job_id=?", (job["id"],))
    connection.commit()
    for key in result_keys:
        files.bodies.pop(key)
    rows["joint_result_artifacts"] = []
    job.update(state="queued", cancel_requested=0, worker_id=None, result_key=None,
        result_sha256=None, result_bytes=None, error_code=None, error_message=None,
        started_at=None, finished_at=None, wall_ms=None, peak_rss_bytes=None, scratch_bytes=None)

    from app.physical_joint_native_contract import MAX_BYTES
    connection.execute("BEGIN IMMEDIATE")
    try:
        result = classify_snapshot(connection, files, approved_manifests={}, approved_installations={},
            native_metadata={}, expected_source_policy_sha256=joint_case["source_policy"])
        assert result.classification == "prepared_uncommitted", result.reason
        charge = result.account_charges[owner]
        assert charge["joint_active"] == MAX_BYTES
        assert charge["legacy_active"] == 0
        assert charge["joint_terminal_indices"] == charge["joint_members"] == 0
        assert charge["total"] == charge["raw"] + charge["datasets"] + MAX_BYTES
    finally:
        connection.rollback()
        connection.close()


def test_m11_project_deletion_transfers_all_indexes_and_members_for_restart(joint_case):
    from app.physical_project_deletion import transfer_project_deletion
    connection, files = joint_case["connection"], joint_case["files"]
    owner, project = joint_case["owner"], joint_case["project"]
    connection.execute("BEGIN IMMEDIATE")
    try:
        plan = prepare_project_deletion(connection, files=files, owner_id=owner, project_id=project,
            batch_id=joint_case["ids"][0], receipt_id=joint_case["ids"][1], created_us=2,
            expected_source_policy_sha256=joint_case["source_policy"], approved_manifests={},
            approved_installations={}, native_metadata={}, profile_records=[])
        connection.commit()
        connection.execute("BEGIN IMMEDIATE")
        assert classify_snapshot(connection,files,approved_manifests={},approved_installations={},
            native_metadata={},expected_source_policy_sha256=joint_case["source_policy"]).classification == "prepared_uncommitted"

        # Model the production directory rename as an exact key relocation.
        moved = {}
        for key, body in list(files.bodies.items()):
            if key.startswith(f"projects/{owner}/{project}/"):
                moved[f".deleting/{owner}--{project}/" + key.split(f"projects/{owner}/{project}/",1)[1]] = body
            elif key.startswith(f"derived/{owner}/{project}/"):
                moved[f".deleting/{owner}--{project}--derived/" + key.split(f"derived/{owner}/{project}/",1)[1]] = body
            else:
                moved[key] = body
        files.bodies = moved

        from app.physical_project_deletion import retire_project_forest_relations, retire_project_forest_families
        retire_project_forest_relations(connection,owner_id=owner,project_id=project)
        connection.execute("DELETE FROM processing_jobs WHERE owner_id=? AND project_id=?",(owner,project))
        connection.execute("DELETE FROM observation_datasets WHERE owner_id=? AND project_id=?",(owner,project))
        retire_project_forest_families(connection,owner_id=owner,project_id=project)
        connection.execute("DELETE FROM raw_assets WHERE owner_id=? AND project_id=?",(owner,project))
        connection.execute("DELETE FROM source_records WHERE owner_id=? AND project_id=?",(owner,project))
        connection.execute("DELETE FROM projects WHERE owner_id=? AND id=?",(owner,project))
        used_raw=sum(r["bytes"] for r in plan["inventory"]["raw_assets"])
        connection.execute("UPDATE account_usage SET raw_bytes=raw_bytes-? WHERE user_id=?",(used_raw,owner))

        inventory, custody = plan["inventory"], plan["custody"]
        asset_manifest = [dict(asset_id=r["asset_id"],sha256=r["sha256"],byte_count=r["bytes"])
                          for r in inventory["raw_assets"]]
        derived_manifest = ([dict(kind="dataset",id=r["dataset_id"],sha256=r["sha256"],byte_count=r["bytes"])
                             for r in inventory["datasets"]] +
            [dict(kind="result",id=r["job_id"],sha256=r["sha256"],byte_count=r["bytes"])
             for r in inventory["joint_result_indexes"]] +
            [dict(kind="joint_artifact",id=r["job_id"],name=r["name"],
                relative_path=f"joint/{r['job_id']}/{r['name']}",sha256=r["sha256"],byte_count=r["bytes"])
             for r in inventory["joint_result_members"]])
        _insert(connection,"deletion_receipts",dict(id=custody["deletion_receipt_id"],owner_id=owner,
            project_id=project,deleted_at="2026-10-25 12:00:00",backup_purge_status="not_attempted",
            asset_hashes=json.dumps([r["sha256"] for r in asset_manifest]),
            asset_manifest=json.dumps(asset_manifest),derived_manifest=json.dumps(derived_manifest)))
        transfer_project_deletion(connection,inventory=inventory,custody=custody,
            expected_source_policy_sha256=joint_case["source_policy"],approved_installations={})
        connection.commit()

        connection.execute("BEGIN IMMEDIATE")
        result = classify_snapshot(connection,files,approved_manifests={},approved_installations={},
            native_metadata={},expected_source_policy_sha256=joint_case["source_policy"])
        assert result.classification == "coherent_committed", result.reason
        assert result.operations[custody["batch_id"]] == "retain_debt"
        assert result.operations[custody["deletion_receipt_id"]] == "retain_deleted_projection"
        connection.rollback()

        original_bodies = files.bodies
        bad_keys = [inventory["joint_result_members"][0]["storage_key"],
            f"derived/{owner}/{project}/results/{inventory['joint_result_indexes'][0]['job_id']}.json",
            f"projects/{owner}/{project}/{inventory['joint_raw_assets'][0]['asset_id']}"]
        for source_key in bad_keys:
            retired_key = source_key.replace(f"derived/{owner}/{project}/",f".deleting/{owner}--{project}--derived/")
            retired_key = retired_key.replace(f"projects/{owner}/{project}/",f".deleting/{owner}--{project}/")
            damaged = dict(original_bodies)
            damaged[retired_key] = b"tampered M11 member"
            files.bodies = damaged
            connection.execute("BEGIN IMMEDIATE")
            result = classify_snapshot(connection,files,approved_manifests={},approved_installations={},
                native_metadata={},expected_source_policy_sha256=joint_case["source_policy"])
            assert result.classification == "inconsistent"
            assert not result.operations and not result.account_charges
            connection.rollback()
        files.bodies = original_bodies
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
