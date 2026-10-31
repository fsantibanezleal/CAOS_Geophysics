"""Original-byte, owned physical profile admission without native execution."""
from copy import deepcopy
from types import SimpleNamespace
import hashlib
import json
import sys
from uuid import uuid4

import pytest

from app.errors import ApiError
from app.profile_contract import parse_profile_envelope, validate_profile_dataset


def profile_fixture():
    owner, project, asset_id, source_id = (str(uuid4()) for _ in range(4))
    raw = ("# Wenner array with 2m\n8# Number of sensors\n#x z\n"
           + "".join(f"{2*i} 0\n" for i in range(8))
           + "5# Number of data\n#a b m n R\n"
           + "".join(f"{i+1} {i+4} {i+2} {i+3} 1\n" for i in range(5))).encode()
    digest = hashlib.sha256(raw).hexdigest()
    physical = {"coordinate_reference": "local", "local_crs": "Declared baseline",
                "axis_order": "xy", "horizontal_unit": "m", "vertical_unit": "m",
                "vertical_positive": "up", "vertical_datum": "Declared datum",
                "measurement_unit": "ohm", "component_frame": "ABMN",
                "geometry": {"electrode_count": 8, "measurement_count": 5}}
    asset = SimpleNamespace(id=asset_id, source_id=source_id, owner_id=owner, project_id=project,
                            detected_format="ert_ohm", sha256=digest, byte_count=len(raw),
                            physical_metadata=physical)
    source = SimpleNamespace(id=source_id, owner_id=owner, project_id=project,
                             private_storage_permission="attested", rights_decision="derivative-only")
    meta = {"schema": "geophysics.supplied-profile/v1", "method": "ert.topographic-profile/v1",
            "source": {"source_id": source_id, "kind": "user_upload", "citation": "Declared own survey",
                       "rights": {"holder": "Operator", "processing_allowed": True,
                                  "redistribution_allowed": False}, "sha256": digest, "bytes": len(raw)},
            "frame": {"horizontal_reference": "Declared baseline", "vertical_datum": "Declared datum",
                      "coordinate_unit": "m", "vertical_positive": "up",
                      "profile_axes": ["distance", "elevation"]},
            "weights": {"policy": "provider-example-conditional/v1"}}
    return raw, asset, source, meta


def admit(raw, asset, source, meta):
    return parse_profile_envelope(raw, metadata=meta, dataset_id=str(uuid4()),
                                  owner_id=asset.owner_id, project_id=asset.project_id,
                                  asset=asset, source=source)


def test_original_and_physical_bindings():
    raw, asset, source, meta = profile_fixture()
    before = json.dumps(meta, sort_keys=True)
    result = admit(raw, asset, source, meta)
    assert result["parent_raw_sha256"] == asset.sha256
    assert result["profile_metadata"] == meta
    assert result["dimensions"] == {"sensor": 8, "measurement": 5}
    assert result["geometry"]["row_ids_zero_based"] == list(range(5))
    assert result["truth"] is None
    assert json.dumps(meta, sort_keys=True) == before
    dataset = SimpleNamespace(id=result["dataset_id"], owner_id=asset.owner_id,
                              project_id=asset.project_id, raw_asset_id=asset.id,
                              raw_sha256=asset.sha256, parser_version=result["parser_version"],
                              modality=result["modality"], row_count=5)
    validate_profile_dataset(result, dataset)
    for key in ("owner_id", "project_id", "parent_raw_sha256"):
        corrupt = deepcopy(result)
        corrupt[key] = "changed"
        with pytest.raises(ApiError):
            validate_profile_dataset(corrupt, dataset)
    mutations = [("observed", None), ("observed", [float("nan")]*5),
                 ("geometry", []), ("dimensions", None),
                 ("method_id", "traveltime.first-arrival-profile/v1"),
                 ("observation_unit", "ohm.m"), ("axis_order", ["sensor"])]
    for key, value in mutations:
        corrupt = deepcopy(result)
        corrupt[key] = value
        with pytest.raises(ApiError):
            validate_profile_dataset(corrupt, dataset)
    corrupt = deepcopy(result)
    corrupt["geometry"]["abmn_zero_based"][0][0] = 8
    with pytest.raises(ApiError):
        validate_profile_dataset(corrupt, dataset)


@pytest.mark.parametrize("field,value", [("vertical_positive", "down"), ("vertical_unit", "ft"),
    ("horizontal_unit", "km"), ("measurement_unit", "ohm.m"), ("local_crs", "Another frame"),
    ("vertical_datum", "Another datum"), ("component_frame", "source-receiver")])
def test_reject_metadata_drift_before_native_load(monkeypatch, field, value):
    raw, asset, source, meta = profile_fixture()
    asset.physical_metadata[field] = value
    # A native import at admission is a defect, not a dependency to install here.
    monkeypatch.setitem(sys.modules, "pygimli", None)
    with pytest.raises(ApiError):
        admit(raw, asset, source, meta)


def test_original_and_ownership_drift_rejected():
    raw, asset, source, meta = profile_fixture()
    for section, key, value in (("source", "sha256", "0"*64), ("source", "bytes", len(raw)+1),
                                ("source", "source_id", str(uuid4()))):
        changed = deepcopy(meta)
        changed[section][key] = value
        with pytest.raises(ApiError):
            admit(raw, asset, source, changed)
    with pytest.raises(ApiError):
        admit(raw+b"\n", asset, source, meta)
    source.owner_id = str(uuid4())
    with pytest.raises(ApiError):
        admit(raw, asset, source, meta)


def test_rights_and_declared_counts_are_not_guessed():
    raw, asset, source, meta = profile_fixture()
    source.rights_decision = "forbidden"
    with pytest.raises(ApiError):
        admit(raw, asset, source, meta)
    source.rights_decision = "derivative-only"
    asset.physical_metadata["geometry"]["electrode_count"] = 9
    with pytest.raises(ApiError):
        admit(raw, asset, source, meta)
    asset.physical_metadata = None
    with pytest.raises(ApiError):
        admit(raw, asset, source, meta)
