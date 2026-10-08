"""Leaf DTO/custody gates on the existing migrated account API, without jobs.

The existing gravity fixture deliberately exercises generic byte binding only.
It is not M03 source registration, magnetic admission or lifecycle evidence.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import sqlite3
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.errors import ApiError
from app.magnetic_line_survey_wire import (
    SurveyExport, SurveyStart, WIRE_MAX_BYTES, bind_owned_survey_sources,
    parse_survey_export, parse_survey_start,
)
from app.models import User
from tests.api.conftest import PROCESSED_GRAVITY_CSV, processed_gravity_metadata


UUID_FIELDS = ("dataset_id", "original_asset_id", "metadata_asset_id", "request_asset_id")
HASH_FIELDS = ("dataset_sha256", "original_sha256", "metadata_sha256", "request_sha256")


def wire_body(auxiliary_count=2):
    result = {"schema": "m03-owner-start/1"}
    result.update({name: str(uuid4()) for name in UUID_FIELDS})
    result.update({name: hashlib.sha256(name.encode()).hexdigest() for name in HASH_FIELDS})
    result["auxiliary_asset_ids"] = [str(uuid4()) for _ in range(auxiliary_count)]
    result["auxiliary_sha256"] = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(auxiliary_count)]
    return result


@pytest.mark.parametrize("count", [0, 1, 16])
def test_exact_start_and_export_roundtrip(count):
    payload = wire_body(count)
    request = parse_survey_start(json.dumps(payload).encode())
    assert request.model_dump(mode="json", by_alias=True) == payload
    assert isinstance(request.dataset_id, UUID)
    for scope in ("private", "public"):
        export = {"schema": "m03-owner-export/1", "scope": scope}
        assert parse_survey_export(json.dumps(export).encode()).model_dump(by_alias=True) == export


@pytest.mark.parametrize("name", ["schema", *UUID_FIELDS, *HASH_FIELDS, "auxiliary_asset_ids", "auxiliary_sha256"])
def test_every_start_key_is_required(name):
    body = wire_body()
    del body[name]
    with pytest.raises(ValidationError):
        SurveyStart.model_validate(body)


@pytest.mark.parametrize("name", ["path", "csv_path", "metadata_path", "url", "worker_module", "callback", "owner_id",
                                 "project_id", "schema_version", "unknown"])
def test_unknown_path_url_owner_and_callback_fields_refuse(name):
    body = wire_body()
    body[name] = "../private/original.csv"
    with pytest.raises(ValidationError):
        SurveyStart.model_validate(body)


@pytest.mark.parametrize("field", [*UUID_FIELDS, "auxiliary_asset_ids"])
@pytest.mark.parametrize("value", [None, True, 7, [], {}, "not-a-uuid", "../file", "C:/private.csv",
                                 "https://provider.invalid/file", "12345678123456781234567812345678"])
def test_uuid_fields_do_not_coerce_paths_or_malformed_identity(field, value):
    body = wire_body()
    body[field] = [value] if field == "auxiliary_asset_ids" else value
    with pytest.raises(ValidationError):
        SurveyStart.model_validate(body)


@pytest.mark.parametrize("field", [*HASH_FIELDS, "auxiliary_sha256"])
@pytest.mark.parametrize("value", [None, True, 7, {}, "A" * 64, "g" * 64, "a" * 63, "a" * 65,
                                 "a" * 64 + "\n", " " + "a" * 64, "../sha256"])
def test_hash_fields_require_actual_lowercase_64hex_grammar(field, value):
    body = wire_body()
    body[field] = [value, "b" * 64] if field == "auxiliary_sha256" else value
    with pytest.raises(ValidationError):
        SurveyStart.model_validate(body)


def test_uuid_uniqueness_includes_every_reference_and_auxiliary():
    original = wire_body()
    names = [*UUID_FIELDS, "auxiliary0", "auxiliary1"]
    for first in range(len(names)):
        for second in range(first + 1, len(names)):
            body = copy.deepcopy(original)
            source = body[names[first]] if first < 4 else body["auxiliary_asset_ids"][first - 4]
            if second < 4:
                body[names[second]] = source
            else:
                body["auxiliary_asset_ids"][second - 4] = source
            with pytest.raises(ValidationError, match="unique"):
                SurveyStart.model_validate(body)


def test_auxiliary_length_bounds_and_matching_are_mandatory():
    with pytest.raises(ValidationError):
        SurveyStart.model_validate(wire_body(17))
    for ids, hashes in (([], ["a" * 64]), ([str(uuid4())], [])):
        body = wire_body(0)
        body.update(auxiliary_asset_ids=ids, auxiliary_sha256=hashes)
        with pytest.raises(ValidationError, match="lengths"):
            SurveyStart.model_validate(body)
    for field in ("auxiliary_asset_ids", "auxiliary_sha256"):
        body = wire_body()
        body[field] = tuple(body[field])
        with pytest.raises(ValidationError):
            SurveyStart.model_validate(body)


@pytest.mark.parametrize("payload", [{}, {"schema": "m03-owner-export/1"}, {"scope": "private"},
                                     {"schema": "m03-owner-start/1", "scope": "private"},
                                     {"schema": "m03-owner-export/1", "scope": "PUBLIC"},
                                     {"schema": "m03-owner-export/1", "scope": 1},
                                     {"schema": "m03-owner-export/1", "scope": "private", "path": "../export"}])
def test_export_refuses_missing_unknown_and_malformed_fields(payload):
    with pytest.raises(ValidationError):
        SurveyExport.model_validate(payload)


@pytest.mark.parametrize("raw", [b"", b"{", b"{} {}", b"[]", b"null", b"\xff", b"{\"scope\":NaN}",
                                 b"{\"scope\":Infinity}", b" " * (WIRE_MAX_BYTES + 1),
                                 b"[" * 1200 + b"]" * 1200])
@pytest.mark.parametrize("parser", [parse_survey_start, parse_survey_export])
def test_bounded_json_parser_refuses_malformed_or_non_object_body(raw, parser):
    with pytest.raises(ApiError) as error:
        parser(raw)
    assert error.value.status == 422 and error.value.code == "request_invalid"
    assert error.value.message == "Survey request fields are invalid"


def test_duplicate_json_keys_and_private_error_inputs_are_not_echoed():
    payload = json.dumps(wire_body())
    duplicate = payload[:-1] + ',"schema":"m03-owner-start/1"}'
    for raw, parser in ((duplicate.encode(), parse_survey_start),
                        (b'{"schema":"m03-owner-export/1","scope":"private","scope":"public"}',
                         parse_survey_export)):
        with pytest.raises(ApiError) as error:
            parser(raw)
        assert error.value.fields == ["body"]
    body = wire_body()
    body["C:/private/secret.csv"] = "sensitive caller text"
    with pytest.raises(ApiError) as error:
        parse_survey_start(json.dumps(body).encode())
    assert error.value.fields == ["body"]
    assert "sensitive" not in error.value.message


@pytest.fixture
def registered(harness):
    account = harness.account()
    project = harness.project()
    original, dataset = harness.processed_dataset(project["id"])
    attachments = []
    for index in range(4):
        body = PROCESSED_GRAVITY_CSV + f"S{6+index},{50+index},0,100,{index},0.1\n".encode()
        response = harness.upload(project["id"], body, processed_gravity_metadata(body))
        assert response.status_code == 201, response.text
        attachments.append(response.json())
    body = {
        "schema": "m03-owner-start/1", "dataset_id": dataset["dataset_id"],
        "dataset_sha256": dataset["sha256"], "original_asset_id": original["asset_id"],
        "original_sha256": original["sha256"], "metadata_asset_id": attachments[0]["asset_id"],
        "metadata_sha256": attachments[0]["sha256"], "request_asset_id": attachments[1]["asset_id"],
        "request_sha256": attachments[1]["sha256"],
        "auxiliary_asset_ids": [item["asset_id"] for item in attachments[2:]],
        "auxiliary_sha256": [item["sha256"] for item in attachments[2:]],
    }
    return harness, account, project, [original, *attachments], body


def bind(registered, body=None, *, user_id=None, project_id=None):
    harness, account, project, _assets, original_body = registered

    async def run():
        async with harness.app.state.sessions() as session:
            user = await session.get(User, UUID(user_id or account["id"]))
            return await bind_owned_survey_sources(
                session, harness.settings, UUID(project_id or project["id"]), user,
                SurveyStart.model_validate(body or original_body),
            )

    return asyncio.run(run())


def test_real_byte_binding_is_ordered_read_only_and_not_an_executor(registered):
    harness, account, project, assets, body = registered
    before = {path.relative_to(harness.settings.data_dir): path.read_bytes()
              for path in harness.settings.data_dir.rglob("*") if path.is_file()
              and not path.name.startswith("api.sqlite3")}
    bound = bind(registered)
    assert str(bound.owner_id) == account["id"] and str(bound.project_id) == project["id"]
    assert bound.dataset.sha256 == body["dataset_sha256"]
    for item, asset in zip([bound.original, bound.metadata, bound.request, *bound.auxiliaries], assets, strict=True):
        assert str(item.id) == asset["asset_id"]
        assert str(item.source_id) == asset["source"]["source_id"]
        assert item.rights_decision == "mirror" and item.private_storage_permission == "attested"
        assert len(item.path.read_bytes()) == item.byte_count
        assert hashlib.sha256(item.path.read_bytes()).hexdigest() == item.sha256
    after = {path.relative_to(harness.settings.data_dir): path.read_bytes()
             for path in harness.settings.data_dir.rglob("*") if path.is_file()
             and not path.name.startswith("api.sqlite3")}
    assert before == after
    with sqlite3.connect(harness.settings.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM processing_jobs").fetchone()[0] == 0
    # Binding intentionally does not pretend this gravity dataset is magnetic.
    assert bound.dataset.path.read_bytes().find(b"gravity_station") > 0


def test_missing_and_foreign_project_and_dataset_are_404(registered):
    harness, _account, project, _assets, body = registered
    other = harness.account("second@example.org")
    for kwargs in ({"user_id": other["id"]}, {"project_id": str(uuid4())}):
        with pytest.raises(ApiError) as error:
            bind(registered, **kwargs)
        assert error.value.status == 404
    other_project = harness.project()
    _asset, foreign = harness.processed_dataset(other_project["id"])
    for dataset_id in (str(uuid4()), foreign["dataset_id"]):
        candidate = {**body, "dataset_id": dataset_id}
        with pytest.raises(ApiError) as error:
            bind(registered, candidate)
        assert error.value.status == 404
    assert project["id"] != other_project["id"]


def test_every_asset_and_its_source_are_owner_and_project_bound_before_reads(registered, monkeypatch):
    import app.magnetic_line_survey_wire as wire

    harness = registered[0]
    other_project = harness.project("Other same-owner scope")
    other_account = harness.account("foreign@example.org")
    actual_verify = wire._verify_bytes
    for role in range(5):
        _check_asset_scope(registered, role, monkeypatch, other_project, other_account)
        monkeypatch.setattr(wire, "_verify_bytes", actual_verify)
        assert bind(registered).original.id == UUID(registered[-1]["original_asset_id"])


def _check_asset_scope(registered, role, monkeypatch, other_project, other_account):
    import app.magnetic_line_survey_wire as wire

    harness, account, project, assets, body = registered
    asset = assets[role]
    # A foreign final auxiliary must fail without reading even the valid original.
    monkeypatch.setattr(wire, "_verify_bytes", lambda *args: pytest.fail("Scope failure must precede file access"))
    mutations = [("raw_assets", "project_id", other_project["id"], asset["asset_id"], project["id"]),
                 ("raw_assets", "owner_id", other_account["id"], asset["asset_id"], account["id"]),
                 ("source_records", "project_id", other_project["id"], asset["source"]["source_id"], project["id"]),
                 ("source_records", "owner_id", other_account["id"],
                  asset["source"]["source_id"], account["id"])]
    for table, column, wrong, identity, correct in mutations:
        with sqlite3.connect(harness.settings.db_path) as db:
            db.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (wrong, identity))
        with pytest.raises(ApiError) as error:
            bind(registered, body)
        assert error.value.status == 404
        with sqlite3.connect(harness.settings.db_path) as db:
            db.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (correct, identity))


def test_dataset_row_owner_project_and_original_parent_binding(registered):
    harness, account, project, assets, body = registered
    other_project = harness.project()
    other_account = harness.account("foreign@example.org")
    mutations = [("project_id", other_project["id"], project["id"], 404),
                 ("owner_id", other_account["id"], account["id"], 404),
                 ("raw_asset_id", assets[1]["asset_id"], assets[0]["asset_id"], 409),
                 ("raw_sha256", "a" * 64, body["original_sha256"], 409),
                 ("storage_key", "../outside.json", None, 409)]
    with sqlite3.connect(harness.settings.db_path) as db:
        key = db.execute("SELECT storage_key FROM observation_datasets WHERE id=?", (body["dataset_id"],)).fetchone()[0]
    for column, wrong, correct, status in mutations:
        with sqlite3.connect(harness.settings.db_path) as db:
            db.execute(f"UPDATE observation_datasets SET {column}=? WHERE id=?", (wrong, body["dataset_id"]))
        with pytest.raises(ApiError) as error:
            bind(registered)
        assert error.value.status == status
        with sqlite3.connect(harness.settings.db_path) as db:
            db.execute(f"UPDATE observation_datasets SET {column}=? WHERE id=?", (correct or key, body["dataset_id"]))
        assert bind(registered).dataset.id == UUID(body["dataset_id"])


def test_every_asset_hash_source_receipt_size_and_path_are_checked(registered):
    for role in range(5):
        _check_asset_receipt(registered, role)


def _check_asset_receipt(registered, role):
    harness, _account, _project, assets, body = registered
    asset = assets[role]
    with sqlite3.connect(harness.settings.db_path) as db:
        key = db.execute("SELECT storage_key FROM raw_assets WHERE id=?", (asset["asset_id"],)).fetchone()[0]
    mutations = [("raw_assets", "sha256", "a" * 64, asset["sha256"], asset["asset_id"]),
                 ("source_records", "sha256", "A" * 64, asset["sha256"], asset["source"]["source_id"]),
                 ("source_records", "expected_bytes", asset["byte_count"] + 1, asset["byte_count"], asset["source"]["source_id"]),
                 ("raw_assets", "storage_key", "../outside", key, asset["asset_id"])]
    for table, column, wrong, correct, identity in mutations:
        with sqlite3.connect(harness.settings.db_path) as db:
            db.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (wrong, identity))
        with pytest.raises(ApiError) as error:
            bind(registered, body)
        assert error.value.status == 409 and error.value.code == "raw_integrity_failed"
        with sqlite3.connect(harness.settings.db_path) as db:
            db.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (correct, identity))


def test_caller_hashes_and_missing_asset_refuse(registered):
    for field in HASH_FIELDS:
        body = {**registered[-1], field: "a" * 64}
        with pytest.raises(ApiError) as error:
            bind(registered, body)
        assert error.value.status == 409
    for index in range(2):
        body = copy.deepcopy(registered[-1])
        body["auxiliary_sha256"][index] = "a" * 64
        with pytest.raises(ApiError) as error:
            bind(registered, body)
        assert error.value.status == 409
    for field in UUID_FIELDS[1:]:
        with pytest.raises(ApiError) as error:
            bind(registered, {**registered[-1], field: str(uuid4())})
        assert error.value.status == 404


def test_actual_dataset_and_all_original_bytes_cannot_be_replaced_or_truncated(registered):
    for role in range(6):
        _check_actual_file(registered, role)


def _check_actual_file(registered, role):
    bound = bind(registered)
    files = [bound.dataset, bound.original, bound.metadata, bound.request, *bound.auxiliaries]
    item = files[role]
    original = item.path.read_bytes()
    for tampered in (bytes([original[0] ^ 1]) + original[1:], original[:-1], original + b"x"):
        item.path.write_bytes(tampered)
        with pytest.raises(ApiError) as error:
            bind(registered)
        assert error.value.status == 409
        assert error.value.code == ("derived_integrity_failed" if role == 0 else "raw_integrity_failed")
        assert str(item.path) not in error.value.message
        item.path.write_bytes(original)
    moved = item.path.with_name(item.path.name + ".preserved")
    item.path.rename(moved)
    with pytest.raises(ApiError) as error:
        bind(registered)
    assert error.value.status == 409
    moved.rename(item.path)


def test_hardlink_alias_refuses_even_identical_bytes(registered):
    item = bind(registered).metadata
    os.link(item.path, item.path.with_name(item.path.name + ".alias"))
    with pytest.raises(ApiError) as error:
        bind(registered)
    assert error.value.code == "raw_integrity_failed"


def test_mutated_frozen_list_cannot_bypass_binding(registered):
    harness, account, project, _assets, body = registered
    request = SurveyStart.model_validate(body)
    request.auxiliary_asset_ids.append(request.original_asset_id)
    request.auxiliary_sha256.append(request.original_sha256)

    async def run():
        async with harness.app.state.sessions() as session:
            user = await session.get(User, UUID(account["id"]))
            await bind_owned_survey_sources(session, harness.settings, UUID(project["id"]), user, request)

    with pytest.raises(ValidationError, match="unique"):
        asyncio.run(run())
