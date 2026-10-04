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


def test_independent_frozen_membership_hash():
    import hashlib
    p = plan(request())
    ids = p["partition"]["unit_ids"]
    ordered = sorted(set(ids), key=lambda uid: (hashlib.sha256((
        "magnetic-geometry-seal-1|104729|"+uid).encode()).hexdigest(), uid))
    membership = dict(units=[dict(id=uid, rows=[i for i, u in enumerate(ids) if u == uid]) for uid in ordered],
                      outer=p["partition"]["outer_rows"]["data"],
                      development=p["partition"]["development_rows"]["data"],
                      folds=[dict(fit=f["fit_rows"]["data"], validation=f["validation_rows"]["data"],
                                  buffered=f["buffered_rows"]["data"]) for f in p["partition"]["folds"]],
                      final=p["final_refit_rows"]["data"])
    assert digest(membership) == "2336754f197bcf8470fdcf267df80af962f2483860bad37b5dacefb9691f2d45"


def test_permutation_preserves_unit_identity_and_row_mapping():
    doc = request()
    p = plan(doc)
    order = list(reversed(range(288)))
    for key in ("row_ids", "group_ids"):
        doc["acquisition"][key] = [doc["acquisition"][key][i] for i in order]
    g = doc["geometry"]
    g["qc_reason"] = [g["qc_reason"][i] for i in order]
    for key, stride in (("usable", 1), ("receivers_m", 3)):
        data = g[key]["data"]
        g[key]["data"] = [value for i in order for value in data[i*stride:(i+1)*stride]]
        rehash(doc, "geometry/"+key)
    for path in ("observations/values", "noise/values"):
        data = doc[path.split("/")[0]]["values"]["data"]
        doc[path.split("/")[0]]["values"]["data"] = [v for i in order for v in data[3*i:3*i+3]]
        rehash(doc, path)
    q = plan(doc)
    assert set(q["partition"]["unit_ids"]) == set(p["partition"]["unit_ids"])
    for key in ("outer_rows", "development_rows"):
        before = {p["inventory"]["row_ids"][i] for i in p["partition"][key]["data"]}
        after = {q["inventory"]["row_ids"][i] for i in q["partition"][key]["data"]}
        assert before == after
    # Original-order seal changes; never sort inventory to hide a permutation.
    assert p["identity"]["seal_sha256"] != q["identity"]["seal_sha256"]


@pytest.mark.parametrize("attack", ["rank", "width", "edge", "zero_active", "prior", "frame_units", "too_few_rows"])
def test_more_physical_and_partition_negatives(attack):
    doc = request()
    if attack == "rank":
        # Distinct source groups but horizontal sites exactly collinear.
        data = doc["geometry"]["receivers_m"]["data"]
        for i in range(288):
            data[3*i] = float(1000*i)
            data[3*i+1] = float(2000*i)
        rehash(doc, "geometry/receivers_m")
    elif attack == "width":
        doc["geometry"]["mesh"]["widths_x_m"]["data"][0] = 0
        rehash(doc, "geometry/mesh/widths_x_m")
    elif attack == "edge":
        doc["geometry"]["mesh"]["origin_m"]["data"][0] = 1e7
        rehash(doc, "geometry/mesh/origin_m")
    elif attack == "zero_active":
        doc["geometry"]["mesh"]["active"]["data"] = [False]*528
        rehash(doc, "geometry/mesh/active")
    elif attack == "prior":
        doc["prior"]["upper_si"]["data"][0] = .11
        rehash(doc, "prior/upper_si")
    elif attack == "frame_units":
        doc["frame"]["coordinate_unit"] = "degree"
    else:
        doc["geometry"]["usable"]["data"] = [i % 24 == 0 for i in range(288)]
        doc["geometry"]["qc_reason"] = ["accepted" if i % 24 == 0 else "provider_qc_excluded" for i in range(288)]
        rehash(doc, "geometry/usable")
    with pytest.raises(InputError):
        plan(doc)


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
    from magnetic_survey import _buffer
    assert _buffer([0, 1], [2], [(0., 0., 120.), (0., 1., 120.), (600., 0., 120.)], 600.) == ([1], [0])
    doc = request()
    doc["geometry"]["partition"]["buffer_m"] = 600.0
    with pytest.raises(InputError) as failure:
        plan(doc)
    assert failure.value.code == "partition"


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
