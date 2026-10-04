"""Deterministic geometry membership is independent of signal and uncertainty."""

import copy
import pytest
from magnetic_survey_support import descriptor, digest, encode, request, rehash
from magnetic_survey_json import InputError, parse_request
from magnetic_survey import plan_geometry


def plan(doc):
    return plan_geometry(parse_request(encode(doc)))


def test_original_inventory_and_masks():
    doc = request()
    p = plan(doc)
    assert p["inventory"]["row_ids"] == doc["acquisition"]["row_ids"]
    assert p["inventory"]["receivers_m"] == doc["geometry"]["receivers_m"]
    doc["geometry"]["usable"]["data"][0] = False
    doc["geometry"]["qc_reason"][0] = "provider_qc_excluded"
    rehash(doc, "geometry/usable")
    q = plan(doc)
    assert len(q["inventory"]["row_ids"]) == 288
    assert q["partition"]["unit_ids"][0] is None
    assert 0 not in q["partition"]["development_rows"]["data"]
    assert 0 not in q["partition"]["outer_rows"]["data"]


@pytest.mark.parametrize("rights,local,redistribute", [
    ("private_user_supplied", True, False), ("redistribution_permitted", True, True),
    ("provider_link_only", True, False), ("unresolved", False, False)])
def test_physical_eligibility_and_rights(rights, local, redistribute):
    doc = request()
    doc["source"]["rights"] = rights
    result = plan(doc)
    assert result["eligibility"]["local_processing"] is local
    assert result["eligibility"]["redistribution"] is redistribute
    assert "likelihood_not_validated" in result["eligibility"]["reasons"]
    assert all(value is False for value in result["claims"].values())


def test_sealed_geometry_and_value_independence():
    doc = request()
    p = plan(doc)
    outer = p["partition"]["outer_rows"]["data"]
    assert sorted({doc["acquisition"]["group_ids"][i] for i in outer}) == ["S2-L01", "S2-L04", "S2-L11"]
    assert len(outer) == 72
    assert len(p["partition"]["development_rows"]["data"]) == 216
    assert len(p["final_refit_rows"]["data"]) == 216
    assert len(set(p["partition"]["unit_ids"])) == 12
    for fold in p["partition"]["folds"]:
        assert [len(fold[key]["data"]) for key in ("fit_rows", "validation_rows", "buffered_rows")] == [144, 72, 0]
    doc["observations"]["values"]["data"] = [i*.001 for i in range(864)]
    rehash(doc, "observations/values")
    doc["noise"]["values"]["data"] = [1.25]*864
    rehash(doc, "noise/values")
    doc["source"]["original_sha256"] = "d"*64
    doc["processing"]["nodes"][0]["input_sha256"] = "d"*64
    q = plan(doc)
    assert p["partition"] == q["partition"]
    assert p["identity"]["seal_sha256"] == q["identity"]["seal_sha256"]
    assert p["identity"]["configuration_sha256"] == q["identity"]["configuration_sha256"]
    assert p["identity"]["observations_sha256"] != q["identity"]["observations_sha256"]
    assert p["identity"]["noise_sha256"] != q["identity"]["noise_sha256"]


@pytest.mark.parametrize("attack", ["duplicate_xyz", "duplicate_id", "one_group", "tie_bridge", "interior", "qc_mismatch", "buffer_exhaustion"])
def test_geometry_negatives_without_fallback(attack):
    doc = request()
    g = doc["geometry"]
    if attack == "duplicate_xyz":
        g["receivers_m"]["data"][3:6] = g["receivers_m"]["data"][:3]
        rehash(doc, "geometry/receivers_m")
    elif attack == "duplicate_id":
        doc["acquisition"]["row_ids"][1] = doc["acquisition"]["row_ids"][0]
    elif attack == "one_group":
        doc["acquisition"]["group_ids"] = ["same"]*288
    elif attack == "tie_bridge":
        doc["acquisition"]["group_ids"][24] = "S2-L00"
    elif attack == "interior":
        g["receivers_m"]["data"][:3] = [-400, -300, -1800]
        rehash(doc, "geometry/receivers_m")
    elif attack == "qc_mismatch":
        g["qc_reason"][0] = "invalid_measurement"
    else:
        g["partition"]["buffer_m"] = 100000.0
    with pytest.raises(InputError):
        plan(doc)


def test_exact_buffer_equality_not_relaxed():
    doc = request()
    doc["geometry"]["partition"]["buffer_m"] = 600.0
    p = plan(doc)
    outer = p["partition"]["outer_rows"]["data"]
    final = p["final_refit_rows"]["data"]
    xyz = doc["geometry"]["receivers_m"]["data"]
    for i in final:
        assert all((xyz[3*i]-xyz[3*j])**2+(xyz[3*i+1]-xyz[3*j+1])**2 > 600**2 for j in outer)
    assert len(final) < 216


def test_unverified_external_lineage_is_not_admitted():
    doc = request()
    previous = doc["processing"]["nodes"][0]
    params = dict(kind="external_preprocessed", record_sha256="a"*64, bundle_sha256="b"*64)
    doc["processing"]["nodes"].append(dict(id="external", parents=["original"],
        operation="declared_external_correction", input_sha256=previous["output_sha256"],
        output_sha256=previous["output_sha256"], parameters=params,
        parameters_sha256=digest(params), citation="Unregistered external record"))
    doc["processing"]["final_node"] = "external"
    p = plan(doc)
    assert not p["eligibility"]["lineage_verified"]
    assert not p["eligibility"]["local_processing"]
    assert "unresolved_lineage" in p["eligibility"]["reasons"]
