"""Authenticated original profile uploads preserve bytes and reject false units."""
from copy import deepcopy
import hashlib

import pytest

from tests.api.conftest import gravity_metadata
from test_profile_contract import profile_fixture


def upload_fixture(method):
    raw, asset, _, _ = profile_fixture()
    if method == "traveltime_sgt":
        raw = (b"5 # shot/geophone points\n#x y\n0 0\n1 0\n2 0\n3 0\n4 0\n"
               b"4 # measurements\n#s g t\n1 2 .001\n1 3 .002\n1 4 .003\n1 5 .004\n")
    metadata = gravity_metadata(raw)
    metadata.update(format=method, mime="text/plain",
                    filename="survey.ohm" if method == "ert_ohm" else "survey.sgt")
    metadata["physical"] = {**asset.physical_metadata,
                            "horizontal_datum": "Declared datum", "epoch_utc": "2026-10-04T00:00:00Z"}
    if method == "traveltime_sgt":
        metadata["physical"].update(measurement_unit="s", component_frame="source-receiver",
                                    geometry={"sensor_count": 5, "measurement_count": 4})
    return raw, metadata


@pytest.mark.parametrize("method", ["ert_ohm", "traveltime_sgt"])
def test_owned_original_profile_upload(harness, monkeypatch, method):
    harness.account()
    project = harness.project()
    raw, metadata = upload_fixture(method)
    # Native code is unnecessary for verifying the raw grammar and its units.
    monkeypatch.setitem(__import__("sys").modules, "pygimli", None)
    result = harness.upload(project["id"], raw, metadata)
    assert result.status_code == 201, result.text
    assert result.json()["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result.json()["byte_count"] == len(raw)
    for key, value in (("measurement_unit", "ms"), ("vertical_positive", "down")):
        changed = deepcopy(metadata)
        changed["physical"][key] = value
        rejected = harness.upload(project["id"], raw, changed)
        assert rejected.status_code == 422, rejected.text
    changed = deepcopy(metadata)
    changed["physical"]["geometry"]["measurement_count"] += 1
    rejected = harness.upload(project["id"], raw, changed)
    assert rejected.status_code == 415, rejected.text
