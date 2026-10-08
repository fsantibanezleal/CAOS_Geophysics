"""Actual bounded physical input, no native fit or online-admission claim."""

import copy
import csv
import hashlib
import io
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.errors import ApiError
from app.magnetic_contract import (parse_magnetic_dataset, validate_magnetic_dataset,
                                  method_mapping, refuse_online_submission, MODALITY)
from app.processing_contract import canonical_bytes

sys.path.insert(0, str(Path(__file__).parents[1] / "data"))
from magnetic_survey_support import request


def control():
    owner, project, asset_id, source_id, dataset_id = [str(uuid4()) for _ in range(5)]
    doc = request()
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["row", "line", "E_m", "N_m", "U_m", "bE", "bN", "bU"])
    for i, row_id in enumerate(doc["acquisition"]["row_ids"]):
        writer.writerow([row_id, doc["acquisition"]["group_ids"][i],
                         *doc["geometry"]["receivers_m"]["data"][3*i:3*i+3],
                         *doc["observations"]["values"]["data"][3*i:3*i+3]])
    original = output.getvalue().encode()
    doc["source"].update(id=source_id, original_sha256=hashlib.sha256(original).hexdigest(),
                         original_bytes=len(original), rights="private_user_supplied")
    doc["processing"]["nodes"][0]["input_sha256"] = doc["source"]["original_sha256"]
    frame = doc["frame"]
    asset = SimpleNamespace(id=asset_id, source_id=source_id, owner_id=owner, project_id=project,
        sha256=doc["source"]["original_sha256"], byte_count=len(original), detected_format="magnetic_csv",
        physical_metadata=dict(coordinate_reference="local", local_crs=frame["crs"], axis_order="xy",
            horizontal_unit="m", vertical_unit="m", vertical_positive="up", vertical_datum=frame["vertical_datum"],
            measurement_unit="nT", component_frame="ENU", geometry=dict(row_id_column="row", line_id_column="line",
                x_column="E_m", y_column="N_m", z_column="U_m", value_column="bE", quantity="secondary_enu_nT",
                component_columns=dict(E="bE", N="bN", U="bU"))))
    source = SimpleNamespace(id=source_id, owner_id=owner, project_id=project, sha256=asset.sha256,
                             private_storage_permission="attested", rights_decision="mirror")
    refs = dict(dataset_id=dataset_id, owner_id=owner, project_id=project, asset=asset, source=source)
    return doc, original, refs


def dataset_record(payload):
    return SimpleNamespace(id=payload["dataset_id"], version=1, owner_id=payload["owner_id"],
        project_id=payload["project_id"], raw_asset_id=payload["raw_asset_id"], raw_sha256=payload["parent_raw_sha256"],
        parser_version=payload["parser_version"], modality=MODALITY, row_count=payload["dimensions"]["row"],
        sha256=hashlib.sha256(canonical_bytes(payload)).hexdigest())


def test_owned_original_dataset():
    doc, original, refs = control()
    raw = b" \n" + canonical_bytes(doc) + b"\n"
    payload = parse_magnetic_dataset(raw, original, **refs)
    assert payload["request_utf8"].encode() == raw
    assert payload["dimensions"] == {"row": 288, "component": 3}
    assert payload["geometry_plan"]["partition"]["outer_rows"]["shape"] == [72]
    assert validate_magnetic_dataset(payload, dataset_record(payload)) == doc
    assert not any(payload["geometry_plan"]["claims"].values())


@pytest.mark.parametrize("attack", ["owner", "source", "original", "size", "datum", "unit", "frame", "rights", "scope", "extra", "lexical", "binding"])
def test_input_drift_refused(attack):
    doc, original, refs = control()
    if attack == "owner": refs["asset"].owner_id = str(uuid4())
    if attack == "source": refs["source"].id = str(uuid4())
    if attack == "original": original += b"changed"
    if attack == "size": refs["asset"].byte_count += 1
    if attack == "datum": refs["asset"].physical_metadata["vertical_datum"] = "different"
    if attack == "unit": refs["asset"].physical_metadata["measurement_unit"] = "T"
    if attack == "frame": refs["asset"].physical_metadata["component_frame"] = "NED"
    if attack == "rights": doc["source"]["rights"] = "redistribution_permitted"
    if attack == "scope": doc["source"]["scope"] = "declared_subset"
    if attack == "extra": doc["truth"] = []
    if attack == "binding": doc["policy"]["optimizer_binding"]["epoch"] = "pretend"
    raw = canonical_bytes(doc) if attack != "lexical" else b'{"schema":1,"schema":2}'
    with pytest.raises(ApiError) as error:
        parse_magnetic_dataset(raw, original, **refs)
    assert error.value.status == (404 if attack in ("owner", "source") else 422)


@pytest.mark.parametrize("attack", ["geometry", "request", "rows", "permission", "original", "unknown"])
def test_dataset_readback_is_not_a_geometry_hash_cast(attack):
    doc, original, refs = control()
    payload = parse_magnetic_dataset(canonical_bytes(doc), original, **refs)
    record = dataset_record(payload)
    changed = copy.deepcopy(payload)
    if attack == "geometry": changed["geometry_plan"]["inventory"]["row_ids"][0] = "drift"
    if attack == "request": changed["request_utf8"] += " "
    if attack == "rows": record.row_count -= 1
    if attack == "permission": changed["private_storage_permission"] = "unknown"
    if attack == "original": changed["parent_raw_bytes"] += 1
    if attack == "unknown": changed["unknown"] = True
    with pytest.raises(ApiError): validate_magnetic_dataset(changed, record)


def test_source_backed_mapping_and_closed_online():
    doc, original, refs = control()
    payload = parse_magnetic_dataset(canonical_bytes(doc), original, **refs)
    mapping = method_mapping(payload, dataset_record(payload))
    assert mapping["online_admitted"] is False and mapping["lane"] == "local_replay"
    for entry in mapping["functions"].values():
        raw = (Path(__file__).parents[2] / "data-pipeline" / entry["file"]).read_bytes()
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(ApiError, match="local surveyed-input") as error: refuse_online_submission()
    assert error.value.code == "magnetic_online_not_admitted"


@pytest.mark.parametrize("attack", ["observations", "coordinates", "row", "line", "header", "subset", "extra_row", "quantity"])
def test_original_columns_are_actual_observations(attack):
    from magnetic_survey_support import rehash
    doc, original, refs = control()
    if attack == "observations":
        doc["observations"]["values"]["data"][0] = 1.
        rehash(doc, "observations/values")
    if attack == "coordinates":
        doc["geometry"]["receivers_m"]["data"][0] += 1.
        rehash(doc, "geometry/receivers_m")
    if attack == "row": original = original.replace(b"S2-L00-S00", b"changed", 1)
    if attack == "line": original = original.replace(b",S2-L00,", b",wrong,", 1)
    if attack == "header": original = original.replace(b"bE,bN,bU", b"bE,bE,bU", 1)
    if attack == "subset": original = b"\n".join(original.splitlines()[:-1]) + b"\n"
    if attack == "extra_row": original += original.splitlines()[1] + b"\n"
    if attack == "quantity": refs["asset"].physical_metadata["geometry"]["quantity"] = "exact_total_anomaly_nT"
    if attack in ("row", "line", "header", "subset", "extra_row"):
        # Even an internally consistent original hash cannot waive correspondence.
        digest = hashlib.sha256(original).hexdigest()
        refs["asset"].sha256 = refs["source"].sha256 = doc["source"]["original_sha256"] = digest
        refs["asset"].byte_count = doc["source"]["original_bytes"] = len(original)
        doc["processing"]["nodes"][0]["input_sha256"] = digest
    with pytest.raises(ApiError): parse_magnetic_dataset(canonical_bytes(doc), original, **refs)
