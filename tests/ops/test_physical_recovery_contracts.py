"""Pure fixture contracts: no CLI, filesystem recovery, provider or native claims."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from uuid import uuid4

import pytest

from app.physical_contract import ContractError, canonical, decode_source, digest, parse_record, wrap_legacy_receipt
from app.physical_recovery import classify_fixture, merge_authorities, bridge_legacy_fixture, verify_patch_descriptor
from scripts.ops_physical_source_pin import CANDIDATE_PATHS, verify_selected_sources
from scripts.ops_physical_recovery import dispatch_authority


def uid():
    return str(uuid4())


def descriptor(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "base64": base64.b64encode(body).decode()}


def legacy():
    return dict(id=uid(), project_id=uid(), owner_id=uid(), deleted_at="2026-10-03 01:02:03.123456",
                asset_hashes=[], asset_manifest=[], derived_manifest=[], backup_purge_status="not_attempted")


def tombstone(receipt):
    return dict(schema="geophysics.physical-deletion/v2", id=receipt["id"], project_id=receipt["project_id"],
                owner_id=receipt["owner_id"], deleted_at=receipt["deleted_at"], origin_revision="0003_processing_jobs",
                legacy_receipt=wrap_legacy_receipt(canonical(receipt), origin_cipher_sha256="a"*64), physical_inventory=None)


def authority():
    return dict(schema="geophysics.recovery-authority/v2", deployment_id=uid(), fixture_only=True, sequence=1,
                predecessor_sha256=None, observed_at="2026-10-03T01:00:00Z", validation_policy_sha256="b"*64,
                database_schemas=[dict(revision="0003_processing_jobs", ddl_sha256="33a96998cd77c595a0d983461f84e1367a813e460b9c13222d07490fd9b86709")],
                legacy_predecessor=None, tombstones=[], snapshots=[])


@pytest.mark.parametrize("source", [
    b'{"a":1,"a":2}', b'{"a":1,"\\u0061":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e400}',
    b'\xef\xbb\xbf{}', b'"\\ud800"', b'{"a":1} trailing', b'{"a":', b'{"a":01}', b'{"a":' + b'1'*129 + b'}',
])
def test_strict_complete_source_rejects_duplicates_nonfinite_encoding_partial_and_trailing(source):
    with pytest.raises(ContractError):
        decode_source([source], max_bytes=1024)


def test_stream_sentinel_never_exposes_partial_or_reads_unbounded_tail():
    touched = []
    def chunks():
        yield b'{"x":1}'
        yield b'x'*64
        touched.append(True)
        yield b'never read'
    with pytest.raises(ContractError, match="limit"):
        decode_source(chunks(), max_bytes=16)
    assert touched == []


def test_native_number_and_null_omission_digest_domains_are_distinct():
    assert digest({"x": 1}) != digest({"x": 1.0})
    assert digest({"terrain": None}) != digest({})
    assert digest({"name": "Señal"}) != digest({"name": "Señal"}, scientific=True)
    assert decode_source([b'{"terrain":null}'], max_bytes=128) == {"terrain": None}


@pytest.mark.parametrize("lexeme", ["1.0", "1e0", "true", '"1"'])
def test_integer_registration_fields_reject_coercible_lexemes(lexeme):
    value = authority()
    source = canonical(value).replace(b'"sequence":1', b'"sequence":' + lexeme.encode())
    with pytest.raises(ContractError):
        parse_record([source])


def test_observed_wire_and_native_sql_receipt_bytes_preserved_distinctly():
    value = legacy()
    wire = json.dumps(value, ensure_ascii=False, indent=2).encode()
    evidence = wrap_legacy_receipt(wire, origin_cipher_sha256="a"*64)
    assert base64.b64decode(evidence["record"]["base64"]) == wire
    assert evidence["record"]["sha256"] != evidence["canonical_record_sha256"]
    assert evidence["sqlite_json"] is None
    native = {key: b' [ ] ' for key in ("asset_hashes", "asset_manifest", "derived_manifest")}
    sql_evidence = wrap_legacy_receipt(canonical(value), sqlite_json=native)
    assert all(base64.b64decode(sql_evidence["sqlite_json"][key]["base64"]) == body for key, body in native.items())
    assert sql_evidence["origin_cipher_sha256"] is None
    parse_record([canonical(evidence)])


def test_receipt_rehashed_extra_missing_or_native_disagreement_refuses():
    value = wrap_legacy_receipt(canonical(legacy()), origin_cipher_sha256="a"*64)
    for mutate in (lambda x: x.update(extra=True), lambda x: x.pop("record"),
                   lambda x: x.update(canonical_record_sha256="f"*64), lambda x: x.update(sqlite_json={})):
        wrong = copy.deepcopy(value)
        mutate(wrong)
        with pytest.raises(ContractError):
            parse_record([canonical(wrong)])


def test_future_schema_dispatch_is_closed_without_legacy_fallback():
    value = authority()
    value["schema"] = "geophysics.recovery-authority/v3"
    with pytest.raises(ContractError, match="schema"):
        parse_record([canonical(value)])


def test_cumulative_authority_identity_and_latest_watermark_bindings():
    before = authority()
    after = copy.deepcopy(before)
    after.update(sequence=2, predecessor_sha256=digest(before), observed_at="2026-10-03T01:01:00Z")
    after["tombstones"] = [tombstone(legacy())]
    watermark = dict(deployment_id=after["deployment_id"], authority_sha256=digest(after), sequence=2,
                     observed_at=after["observed_at"], validation_policy_sha256=after["validation_policy_sha256"])
    assert merge_authorities(before, after, predecessor_cipher_sha256=digest(before), current_cipher_sha256=digest(after), latest=watermark) == after
    wrong = dict(watermark, sequence=1)
    with pytest.raises(ContractError):
        merge_authorities(before, after, predecessor_cipher_sha256=digest(before), current_cipher_sha256=digest(after), latest=wrong)
    bad = copy.deepcopy(after)
    bad.update(sequence=3)
    with pytest.raises(ContractError):
        merge_authorities(before, bad, predecessor_cipher_sha256=digest(before), current_cipher_sha256=digest(after), latest=watermark)


def test_legacy_bridge_permits_absent_later_nodes_but_rejects_overlapping_hash():
    receipt = legacy()
    raw, child = uid(), uid()
    receipt.update(asset_hashes=["a"*64], asset_manifest=[dict(asset_id=raw, sha256="a"*64, byte_count=3)],
                   derived_manifest=[dict(kind="dataset", id=child, sha256="c"*64, byte_count=4)])
    auth = authority()
    auth["tombstones"] = [tombstone(receipt)]
    snapshot = dict(projects={receipt["project_id"]: receipt["owner_id"]},
                    files={raw: dict(owner_id=receipt["owner_id"], project_id=receipt["project_id"], sha256="a"*64, bytes=3)},
                    receipts={})
    before = copy.deepcopy(snapshot)
    result = bridge_legacy_fixture(snapshot, auth)
    assert result["removed_projects"] == (receipt["project_id"],)
    assert snapshot == before
    snapshot["files"][raw]["sha256"] = "b"*64
    with pytest.raises(ContractError):
        bridge_legacy_fixture(snapshot, auth)


@pytest.mark.parametrize("version", ["3.7.0", "3.44.5", "3.45.0", "3.50.0", "3.50.6", "3.51.2", "3.51.3", "3.44.6", "3.50.7"])
def test_version_alone_never_admits_a_native_patch_tuple(version):
    with pytest.raises(ContractError):
        verify_patch_descriptor(dict(sqlite_version=version), supported=())


def test_exact_candidate_path_policy_has_no_active_0004_or_runtime_admission():
    assert len(CANDIDATE_PATHS) == 47
    assert "app/migrations/candidates/0004_physical_persistence.py" in CANDIDATE_PATHS
    assert "app/migrations/versions/0004_physical_persistence.py" not in CANDIDATE_PATHS
    with pytest.raises(ContractError):
        verify_selected_sources(b'{"schema":"future"}', {})


def test_unknown_or_partial_inventory_is_inconsistent_not_success_or_abandonment():
    outcome = classify_fixture({}, {})
    assert outcome.classification == "inconsistent"
    assert outcome.runtime is False and outcome.fixture_only is True


def patch_descriptor():
    # Synthetic PRIVATE fixture descriptor, NEVER an installed-build receipt.
    return dict(schema="geophysics.sqlite-wal-patch-build/v1", sqlite_version="3.50.7", sqlite_source_id="fixture-source-id",
                platform="windows-local", python="3.12.12", python_implementation="CPython", linkage="dynamic",
                binaries=[dict(role="interpreter", artifact_id="fixture-python", bytes=3, sha256="a"*64),
                          dict(role="sqlite_library", artifact_id="fixture-sqlite", bytes=4, sha256="b"*64)],
                patch_provenance=dict(kind="upstream_documented_backport", upstream_reference="https://sqlite.org/fixture-reference",
                                      reference_receipt_sha256="c"*64, patch_evidence_sha256="d"*64,
                                      distribution_id=None, distribution_version=None),
                validation_policy_sha256="e"*64, reviewed_evidence_sha256="f"*64)


def test_exact_private_patch_fixture_tuple_compares_without_runtime_admission():
    value = patch_descriptor()
    assert verify_patch_descriptor(value, supported=[copy.deepcopy(value)])["runtime"] is False
    with pytest.raises(ContractError, match="unregistered"):
        verify_patch_descriptor(value, supported=())
    substituted = copy.deepcopy(value)
    substituted["binaries"][1]["sha256"] = "e"*64
    with pytest.raises(ContractError):
        verify_patch_descriptor(substituted, supported=[value])


@pytest.mark.parametrize("change", [
    {"sqlite_version": "3.45.0"}, {"sqlite_source_id": None}, {"linkage": "unknown"},
    {"binaries": []}, {"python": "3.13.0"}, {"extra": True},
])
def test_patch_fields_backport_version_binary_and_python_negatives(change):
    value = patch_descriptor()
    value.update(change)
    with pytest.raises(ContractError):
        verify_patch_descriptor(value, supported=[value])


def test_authority_rewrite_same_project_original_wire_digest_is_rejected():
    old = authority()
    old["tombstones"] = [tombstone(legacy())]
    new = copy.deepcopy(old)
    new.update(sequence=2, predecessor_sha256=digest(old), observed_at="2026-10-03T01:01:00Z")
    preserved = new["tombstones"][0]["legacy_receipt"]
    wire = json.dumps(json.loads(base64.b64decode(preserved["record"]["base64"])), indent=2).encode()
    new["tombstones"][0]["legacy_receipt"] = wrap_legacy_receipt(wire, origin_cipher_sha256="a"*64)
    latest = dict(deployment_id=new["deployment_id"], authority_sha256=digest(new), sequence=2,
                  observed_at=new["observed_at"], validation_policy_sha256=new["validation_policy_sha256"])
    with pytest.raises(ContractError, match="rewrite"):
        merge_authorities(old, new, predecessor_cipher_sha256=digest(old), current_cipher_sha256=digest(new), latest=latest)


def test_closed_positive_legacy_dispatch_and_complete_eof():
    value = authority()
    inputs = dict(snapshot_schema="geophysics.restricted-snapshot/v1", database_revision="0003_processing_jobs",
                  ddl_sha256=value["database_schemas"][0]["ddl_sha256"], deployment_id=value["deployment_id"], fixture_only=True)
    assert dispatch_authority([canonical(value)], **inputs) == value
    with pytest.raises(ContractError):
        dispatch_authority([canonical(value), b'{'], **inputs)
    with pytest.raises(ContractError):
        dispatch_authority([canonical(value)], **dict(inputs, database_revision="0004_physical_persistence"))


@pytest.mark.parametrize("change", [{"tombstones": [tombstone(legacy()), tombstone(legacy())]}, {"database_schemas": []},
                                    {"fixture_only": 1}, {"observed_at": "2026-02-30T00:00:00Z"}])
def test_authority_complete_fields_order_time_and_boolean_refuse(change):
    value = authority()
    value.update(change)
    if "tombstones" in change:
        value["tombstones"].sort(key=lambda x: x["project_id"], reverse=True)
    with pytest.raises(ContractError):
        parse_record([canonical(value)])


def test_source_budget_counts_keys_and_root_depth_before_construction():
    with pytest.raises(ContractError, match="structure_limit"):
        decode_source([b'{"a":1}'], max_bytes=32, nodes=2)
    with pytest.raises(ContractError, match="structure_limit"):
        decode_source([b'[[0]]'], max_bytes=32, depth=2)


@pytest.mark.parametrize("source", [b'{"x":1\xd9\xa2}', b'{"x":1e\xd9\xa2}'])
def test_number_tokens_use_ascii_json_grammar_not_unicode_digits(source):
    with pytest.raises(ContractError):
        decode_source([source], max_bytes=32)


def custody_fixture():
    owner, project, batch, root, raw = [uid() for _ in range(5)]
    return dict(schema="geophysics.physical-custody/v1", batch_id=batch, owner_id=owner, project_id=project,
                origin_kind="root_stage", origin_id=root, stage_id=root, deletion_receipt_id=None,
                raw_asset_id=raw, raw_sha256="a"*64, raw_bytes=7, parser_version="gravity-stations-json/v1",
                method_id=None, capacity_bytes=32*1048576,
                initial_files=[dict(ordinal=1, role="input_spool", location="stage", artifact_id=None,
                                    leaf="input.json", max_bytes=16*1048576, actual_bytes=7, actual_sha256="a"*64)],
                removed_ordinals=[])


def test_complete_custody_registered_namespace_and_removed_charge_are_literal():
    from app.physical_contract import validate_custody
    value = custody_fixture()
    before = copy.deepcopy(value)
    assert validate_custody(value)["retained_bytes"] == 7
    initial = validate_custody(value)["initial_inventory_sha256"]
    value["removed_ordinals"] = [1]
    audited = validate_custody(value)
    assert audited["retained_bytes"] == 0 and audited["initial_inventory_sha256"] == initial
    assert before["removed_ordinals"] == []


@pytest.mark.parametrize("change", [
    {"capacity_bytes": 0}, {"capacity_bytes": 1}, {"raw_asset_id": None}, {"stage_id": None},
    {"stage_id": uid()}, {"removed_ordinals": [2]}, {"removed_ordinals": [1,1]}, {"extra": True},
])
def test_custody_header_complete_null_origin_capacity_and_removed_subset_refuse(change):
    from app.physical_contract import validate_custody
    value = custody_fixture()
    value.update(change)
    with pytest.raises(ContractError):
        validate_custody(value)


@pytest.mark.parametrize("change", [
    {"role": "cache", "leaf": "cache-01.bin", "max_bytes": 1048576}, {"leaf": "../input.json"},
    {"role": "stdout_log"}, {"actual_bytes": None}, {"actual_bytes": 16*1048576+1},
    {"artifact_id": uid()}, {"max_bytes": 16*1048576+1}, {"location": "pending_target"},
    {"actual_sha256": None}, {"ordinal": 1.0},
])
def test_custody_file_roles_no_arbitrary_cache_path_measurement_or_alias(change):
    from app.physical_contract import validate_custody
    value = custody_fixture()
    value["initial_files"][0].update(change)
    with pytest.raises(ContractError):
        validate_custody(value)


def test_two_byte_copies_charge_twice_and_deletion_rename_partition_is_not_deduplication():
    from app.physical_contract import validate_custody
    value = custody_fixture()
    value.update(origin_kind="project_deletion", origin_id=value["project_id"], stage_id=None,
                 deletion_receipt_id=uid(), raw_asset_id=None, raw_sha256=None, raw_bytes=None,
                 parser_version=None, capacity_bytes=14)
    value["initial_files"] = [dict(ordinal=i, role="raw_delete", location="deleting_raw", artifact_id=identifier,
                                  leaf=identifier, max_bytes=1024*1048576, actual_bytes=7, actual_sha256="a"*64)
                              for i,identifier in enumerate((uid(),uid()), 1)]
    assert validate_custody(value)["retained_bytes"] == 14
    value["initial_files"][1]["leaf"] = value["initial_files"][0]["leaf"]
    with pytest.raises(ContractError):
        validate_custody(value)


CANDIDATE_DDL = "7496e07c6d4454a556e3b094b16ad458e06aa4cf57727e434dd7fb002fb59d86"


def empty_inventory():
    from app.models import Base
    from app.physical_persistence import TABLES
    value = dict(schema="geophysics.physical-inventory/v1", database_revision="0004_physical_persistence",
                 ddl_sha256=CANDIDATE_DDL, source_policy_sha256="e"*64, storage_generation=uid(), lease_generation=1,
                 rows={name: [] for name in (*Base.metadata.tables, *TABLES, "alembic_version")},
                 files={"@database": dict(bytes=None, sha256=None, role="native_metadata", owner_id=None, project_id=None, origin_id=None),
                        ".physical-writers.lock": dict(bytes=1, sha256=hashlib.sha256(b"\0").hexdigest(), role="writer_lock",
                                                       owner_id=None, project_id=None, origin_id=None)})
    value["rows"]["alembic_version"] = [dict(version_num=dict(type="text", value=value["database_revision"]))]
    return value, {hashlib.sha256(b"\0").hexdigest(): b"\0"}


def sql_row(values, bodies, *, json_columns=(), blob_columns=()):
    result = {}
    for name, value in values.items():
        if value is None:
            result[name] = dict(type="null", value=None)
        elif name in json_columns or name in blob_columns:
            assert type(value) is bytes
            h = hashlib.sha256(value).hexdigest()
            bodies[h] = value
            result[name] = dict(type="json_text" if name in json_columns else "blob", bytes=len(value), sha256=h)
        else:
            result[name] = dict(type="integer" if type(value) is int else "real" if type(value) is float else "text", value=value)
    return result


def root_stage_inventory():
    value, bodies = empty_inventory()
    owner, project, source, raw, root, batch = [uid() for _ in range(6)]
    raw_body = b'{"bad":1}'  # Owned before structural parse; NO published dataset.
    h = hashlib.sha256(raw_body).hexdigest()
    bodies[h] = raw_body
    now = "2026-10-03 01:02:03.123456"
    rows = value["rows"]
    rows["user"] = [sql_row(dict(id=owner, email="private-fixture@example.org", hashed_password="fixture",
                                 is_active=1, is_superuser=0, is_verified=1), bodies)]
    rows["projects"] = [sql_row(dict(id=project, owner_id=owner, name="Fixture", description="", created_at=now, updated_at=now), bodies)]
    rows["source_records"] = [sql_row(dict(id=source, project_id=project, owner_id=owner, original_filename="survey.json", version=1,
                 provider="User upload", exact_url=None, doi=None, citation=None, retrieved_at=now, rights_statement="Private fixture",
                 rights_decision="mirror", private_storage_permission="attested", declared_format="gravity_stations_json",
                 expected_bytes=len(raw_body), sha256=h, attribution="Fixture"), bodies)]
    raw_key = f"projects/{owner}/{project}/{raw}"
    rows["raw_assets"] = [sql_row(dict(id=raw, project_id=project, owner_id=owner, source_id=source, filename="survey.json",
                 client_mime="application/json", detected_format="gravity_stations_json", byte_count=len(raw_body), sha256=h,
                 storage_key=raw_key, physical_metadata=b' {} ', validation_status="raw_metadata_checked", created_at=now),
                 bodies, json_columns=("physical_metadata",))]
    rows["account_usage"] = [sql_row(dict(user_id=owner, raw_bytes=len(raw_body)), bodies)]
    rows["physical_custody_batches"] = [sql_row(dict(batch_id=batch, project_id=project, owner_id=owner, origin_kind="root_stage",
                 origin_id=root, stage_id=root, deletion_receipt_id=None, raw_asset_id=raw, raw_sha256=h, raw_bytes=len(raw_body),
                 parser_version="gravity-stations-json/v1", method_id=None, state="active", capacity_bytes=32*1048576,
                 charged_bytes=32*1048576, inventory_bytes=None, inventory_sha256=None, created_us=1, sealed_us=None, removed_us=None), bodies)]
    rows["physical_custody_files"] = [sql_row(dict(batch_id=batch, ordinal=1, role="input_spool", location="stage",
                 artifact_id=None, leaf="input.json", max_bytes=16*1048576, actual_bytes=None, actual_sha256=None, state="reserved"), bodies)]
    stage_key = f".job-staging/{root}/input.json"
    value["files"][raw_key] = dict(bytes=len(raw_body), sha256=h, role="raw", owner_id=owner, project_id=project, origin_id=raw)
    value["files"][stage_key] = dict(bytes=len(raw_body), sha256=h, role="input_spool", owner_id=owner, project_id=project, origin_id=batch)
    return value, bodies, owner


def classify(value, bodies):
    return classify_fixture(value, bodies, schema_registry={"0004_physical_persistence": CANDIDATE_DDL}, source_policy_sha256="e"*64)


def test_complete_root_stage_reservation_is_retained_not_published_or_adopted():
    value, bodies, owner = root_stage_inventory()
    before = copy.deepcopy((value, bodies))
    outcome = classify(value, bodies)
    assert (outcome.classification, outcome.disposition) == ("prepared_uncommitted", "retain_reservation")
    assert outcome.account_charges[owner] == 32*1048576+9
    assert outcome.runtime is False and outcome.fixture_only is True
    assert (value, bodies) == before


@pytest.mark.parametrize("mutate", [
    lambda v: v["rows"].pop("access_tokens"),
    lambda v: v["rows"].update(future=[]),
    lambda v: v["rows"]["raw_assets"][0].update(extra=dict(type="null", value=None)),
    lambda v: v["rows"]["account_usage"][0]["raw_bytes"].update(value=0),
    lambda v: v["rows"]["physical_custody_batches"][0]["charged_bytes"].update(value=0),
    lambda v: v["rows"]["raw_assets"][0]["owner_id"].update(value=uid()),
    lambda v: v["files"].update(unknown=dict(bytes=0, sha256="a"*64, role="stdout_log", owner_id=uid(), project_id=uid(), origin_id=uid())),
    lambda v: v["files"].pop(next(k for k in v["files"] if k.startswith("projects/"))),
    lambda v: v["rows"]["physical_custody_files"][0]["leaf"].update(value="../input.json"),
    lambda v: v["rows"]["physical_custody_files"][0]["role"].update(value="cache"),
    lambda v: v["rows"]["physical_custody_batches"][0]["state"].update(value="future"),
])
def test_complete_inventory_rejects_unknown_partial_foreign_file_custody_or_accounting(mutate):
    value, bodies, _ = root_stage_inventory()
    mutate(value)
    before = copy.deepcopy(value)
    outcome = classify(value, bodies)
    assert outcome.classification == "inconsistent" and outcome.disposition == "preserve_inconsistent"
    assert value == before


def test_complete_body_barrier_cannot_accept_only_a_rehashed_descriptor():
    value, bodies, _ = root_stage_inventory()
    key = next(k for k in value["files"] if k.startswith("projects/"))
    h = value["files"][key]["sha256"]
    bodies[h] = b'{"bad":2}'
    assert classify(value, bodies).classification == "inconsistent"


def test_inventory_native_metadata_projection_is_not_a_logical_state_change():
    value, bodies, _ = root_stage_inventory()
    first = classify(value, bodies)
    value["files"]["@wal"] = copy.deepcopy(value["files"]["@database"])
    value["files"]["@shm"] = copy.deepcopy(value["files"]["@database"])
    second = classify(value, bodies)
    assert first.inventory_sha256 == second.inventory_sha256
    assert second.fixture_only and not second.runtime  # NOT live existence proof.


@pytest.mark.parametrize("mutate", [
    lambda v: v.update(lease_generation=1.0),
    lambda v: v.update(ddl_sha256="b"*64),
    lambda v: v.update(source_policy_sha256="b"*64),
    lambda v: v["rows"]["raw_assets"][0]["byte_count"].update(type="real", value=9.0),
    lambda v: v["rows"]["physical_custody_files"][0]["max_bytes"].update(value=16*1048576+1),
    lambda v: v["rows"]["physical_custody_batches"][0]["inventory_sha256"].update(type="text", value="a"*64),
    lambda v: v["rows"]["physical_custody_batches"][0]["raw_sha256"].update(value="a"*64),
    lambda v: v["rows"]["physical_custody_batches"][0]["stage_id"].update(value=uid()),
    lambda v: v["rows"]["physical_custody_files"][0]["actual_bytes"].update(type="integer", value=0),
    lambda v: v["files"][".physical-writers.lock"].update(bytes=0),
    lambda v: v["files"]["@database"].update(bytes=1),
    lambda v: v["files"].pop("@database"),
    lambda v: v["files"].pop(".physical-writers.lock"),
])
def test_cut_identity_native_types_unsealed_custody_and_metadata_refusals(mutate):
    value, bodies, _ = root_stage_inventory()
    mutate(value)
    before = copy.deepcopy((value,bodies))
    assert classify(value,bodies).classification == "inconsistent"
    assert (value,bodies) == before


def test_complete_root_source_never_exposes_output_before_eof_or_on_late_error():
    from app.physical_recovery import classify_fixture_source
    value, bodies, _ = root_stage_inventory()
    kwargs = dict(schema_registry={"0004_physical_persistence": CANDIDATE_DDL}, source_policy_sha256="e"*64)
    events = []
    def complete():
        yield canonical(value)
        events.append("eof")
    result = classify_fixture_source(complete(), bodies, **kwargs)
    assert events == ["eof"] and result.disposition == "retain_reservation"
    def bad():
        yield canonical(value)
        yield b' not-json'
    assert classify_fixture_source(bad(), bodies, **kwargs).classification == "inconsistent"
    duplicate = canonical(value).replace(b'"lease_generation":1', b'"lease_generation":1,"lease_generation":1')
    assert classify_fixture_source([duplicate], bodies, **kwargs).classification == "inconsistent"


def test_reservation_account_quota_counts_copies_and_never_deduplicates_hashes():
    value, bodies, owner = root_stage_inventory()
    batch = value["rows"]["physical_custody_batches"][0]
    slot = value["rows"]["physical_custody_files"][0]
    original_batch = copy.deepcopy(batch)
    original_slot = copy.deepcopy(slot)
    for i in range(32):
        b, s = copy.deepcopy(original_batch), copy.deepcopy(original_slot)
        b["batch_id"]["value"] = uid()
        b["stage_id"]["value"] = b["origin_id"]["value"] = uid()
        s["batch_id"]["value"] = b["batch_id"]["value"]
        value["rows"]["physical_custody_batches"].append(b)
        value["rows"]["physical_custody_files"].append(s)
    value["rows"]["physical_custody_batches"].sort(key=lambda x:x["batch_id"]["value"])
    value["rows"]["physical_custody_files"].sort(key=lambda x:x["batch_id"]["value"])
    result = classify(value,bodies)
    assert result.classification == "inconsistent" and result.reason == "account_quota"


def test_external_snapshot_cipher_sentinel_is_never_valid_v2_registration():
    value = dict(schema="geophysics.snapshot-registration/v2", snapshot_id=uid(), sha256="0"*64,
                 created_at="2026-10-03T00:00:00Z", expires_at="2026-10-04T00:00:00Z", policy_id="fixture",
                 snapshot_schema="geophysics.restricted-snapshot/v2", database_revision="0004_physical_persistence",
                 source_policy_sha256="e"*64, legacy_registration=None)
    with pytest.raises(ContractError):
        parse_record([canonical(value)])


def test_custody_positive_dispatch_whole_eof_rejects_duplicate_and_future_schema():
    value = custody_fixture()
    assert parse_record([canonical(value)]) == value
    for body in (canonical(value)+b' x', canonical(value).replace(b'"capacity_bytes":33554432', b'"capacity_bytes":33554432,"capacity_bytes":33554432'),
                 canonical(dict(value,schema="geophysics.physical-custody/v2"))):
        with pytest.raises(ContractError):
            parse_record([body])


def test_unrelated_project_uuid_cannot_hide_outside_the_selected_stage():
    value,bodies,_ = root_stage_inventory()
    project = copy.deepcopy(value["rows"]["projects"][0])
    project["id"]["value"] = "not-a-uuid"
    value["rows"]["projects"].append(project)
    value["rows"]["projects"].sort(key=lambda x:x["id"]["value"])
    assert classify(value,bodies).classification == "inconsistent"


def test_per_schema_bytes_checked_before_constructing_typed_tree(monkeypatch):
    from app import physical_contract as contract
    built = []
    original = contract._Reader.value
    def spy(self, *args, **kwargs):
        if kwargs.get("build", True):
            built.append(True)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(contract._Reader, "value", spy)
    source = b'{"schema":"geophysics.snapshot-registration/v2"}' + b' '*65536
    with pytest.raises(ContractError, match="limit"):
        parse_record([source])
    assert built == []


def test_source_policy_cannot_select_its_own_independent_review_pins():
    policy = dict(schema="geophysics.ops-physical-source-policy/v2",policy_id="m01-physical-persistence-v2",
                  runtime_commit="a"*40,ops_commit="b"*40,database_schemas={},files=dict(runtime={},ops={}),module_manifests={})
    with pytest.raises(ContractError,match="independent_source_review"):
        verify_selected_sources(canonical(policy),dict(runtime={},ops={}))
    with pytest.raises(ContractError,match="independent_source_review"):
        verify_selected_sources(canonical(policy),dict(runtime={},ops={}),reviewed_runtime_commit="c"*40,
                                reviewed_ops_commit="b"*40,reviewed_schema_registry={})
