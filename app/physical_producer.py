"""Saved correction-producer byte and digest bindings, with no numerical replay.

Verification binds one complete producing edge. Earlier correction inputs need
their own verified edge in the caller's complete ancestry audit. Source/runtime
approval is supplied independently; hash-valid data never grants host admission.
"""

import re

from app.physical_contract import (
    CORRECTION, J, M, byte_sha, canonical, decode_source, digest, fields,
    integer, require, sha, uuid,
)
from app.physical_wire import DATASET_KEYS, number, root_envelope, root_structure, scientific_digest, source_structure, terrain_structure


PARENT_KEYS = "schema owner_id project_id root_dataset_id raw_asset_id raw_sha256 raw_bytes output_dataset_id output_dataset_version output_dataset_sha256 output_dataset_bytes job_id method_id state scientific_verdict input_dataset_id input_dataset_sha256 request_sha256 submitted_parameters_sha256 scientific_request_sha256 result_sha256 result_bytes module_manifest module_manifest_sha256 adapter_result_sha256 adapter_receipt adapter_receipt_sha256 core_result_sha256 submitted_config_sha256 normalized_config_sha256"
REQUEST_KEYS = "schema job_id owner_id project_id dataset_id dataset_sha256 root_dataset_id raw_asset_id raw_sha256 raw_bytes method_id parameters submitted_parameters_sha256 scientific_request scientific_request_sha256 parent_production module_manifest module_manifest_sha256 limits admission_receipt_sha256"
RESULT_KEYS = "schema job_id owner_id project_id dataset_id dataset_sha256 output_dataset_id output_dataset_sha256 raw_asset_id raw_sha256 raw_bytes method_id request_sha256 submitted_parameters_sha256 scientific_request_sha256 scientific_result_sha256 module_manifest module_manifest_sha256 scientific_verdict scientific_result receipt"
RECEIPT_KEYS = "adapter_version adapter_module_sha256 core_module_sha256 request_sha256 input_dataset_sha256 submitted_config_sha256 normalized_config_sha256 output_dataset_sha256 correction_result_sha256 engines python python_implementation acceptance"
PRODUCTION_KEYS = "job_id method_id request_sha256 adapter_result_sha256 scientific_result_sha256 module_manifest_sha256 scientific_verdict"
PINS = dict(boule="0.5.0", harmonica="0.7.0", numpy="2.2.6", scipy="1.15.2")


def _same(left, right):
    # Dict equality would erase native 1 versus 1.0 representation.
    require(canonical(left, scientific=True) == canonical(right, scientific=True), "producer_native_identity")


def _decode(body, cap, depth=32, nodes=2250000):
    require(type(body) is bytes and 1 <= len(body) <= cap, "producer_source_bytes")
    return decode_source([body], max_bytes=cap, depth=depth, nodes=nodes)


def _manifest(value, approved):
    fields(value, "schema parser_sha256 wrapper_sha256 adapter_sha256 core_sha256 transform_sha256 runtime_manifest")
    require(value["schema"] == "geophysics.physical-modules/v1" and value["transform_sha256"] is None, "producer_manifest")
    for key in ("parser_sha256", "wrapper_sha256", "adapter_sha256", "core_sha256"):
        sha(value[key])
    runtime = value["runtime_manifest"]
    fields(runtime, "python python_implementation packages")
    require(type(runtime["python"]) is str and re.fullmatch(r"3\.12\.\d+", runtime["python"])
            and runtime["python_implementation"] == "CPython" and runtime["packages"] == PINS, "producer_runtime")
    require(type(approved) is dict, "producer_unregistered_manifest")
    _same(value, approved)


def _configuration(value, station_ids, *, normalized=False):
    require(type(value) is dict, "producer_configuration")
    required = {"target", "uncertainty_model"}
    allowed = required | {"density_kg_m3", "density_sigma_kg_m3", "outlier_z", "terrain"}
    require(required <= set(value) <= allowed and (not normalized or set(value) == allowed), "producer_configuration")
    require(value["target"] in ("gravity_disturbance", "bouguer_disturbance", "terrain_adjusted_disturbance") and
            value["uncertainty_model"] in ("independent_first_order", "conservative_marginals"), "producer_configuration")
    for name, low, high in (("density_kg_m3", 1, 10000), ("density_sigma_kg_m3", 0, 10000), ("outlier_z", 1, float("inf"))):
        if name in value:
            number(value[name], low, high)
    if value["target"] != "gravity_disturbance":
        require({"density_kg_m3", "density_sigma_kg_m3"} <= set(value), "producer_configuration")
    terrain = value.get("terrain")
    if terrain is not None:
        terrain_structure(terrain, station_ids)
    require((terrain is not None) == (value["target"] == "terrain_adjusted_disturbance"), "producer_terrain")


def _adapter(value, manifest):
    fields(value, "schema_version method correction_result receipt")
    require(value["schema_version"] == "gravity-station-adapter-result-1" and value["method"] == CORRECTION, "producer_adapter")
    core = value["correction_result"]
    fields(core, "dataset processing qc")
    root_structure(core["dataset"])
    processing = core["processing"]
    fields(processing, "method input_sha256 output_sha256 config engines python module_sha256 uncertainty_model uncertainty_mgal uncertainty_components_mgal full_method_accepted warnings")
    ids = [s["station_id"] for s in core["dataset"]["stations"]]
    count = len(ids)
    _configuration(processing["config"], ids, normalized=True)
    require(processing["uncertainty_model"] == processing["config"]["uncertainty_model"], "producer_error_kind")
    components = processing["uncertainty_components_mgal"]
    fields(components, "observed_gravity latitude receiver_height surface_height density geoid terrain")
    for vector in (processing["uncertainty_mgal"], *components.values()):
        require(type(vector) is list and len(vector) == count, "producer_error_shape")
        for item in vector:
            number(item, 0)
    require(type(processing["warnings"]) is list and len(processing["warnings"]) <= 64 and
            all(type(item) is str and len(item.encode("utf-8")) <= 8192 for item in processing["warnings"]), "producer_warnings")
    qc = core["qc"]
    fields(qc, "station_ids longitude_deg latitude_deg receiver_ellipsoidal_m surface_ellipsoidal_m original_mgal derived_mgal robust_z outlier_flag excluded_station_ids")
    require(qc["station_ids"] == ids and qc["excluded_station_ids"] == [] and
            type(qc["outlier_flag"]) is list and len(qc["outlier_flag"]) == count and
            all(type(flag) is bool for flag in qc["outlier_flag"]), "producer_qc_structure")
    for key in ("longitude_deg", "latitude_deg", "receiver_ellipsoidal_m", "surface_ellipsoidal_m", "original_mgal", "derived_mgal", "robust_z"):
        require(type(qc[key]) is list and len(qc[key]) == count, "producer_qc_shape")
        for item in qc[key]:
            if item is None:
                require(key == "robust_z", "producer_qc_null")
            else:
                number(item)
    _same(qc["derived_mgal"], [s["value_mgal"] for s in core["dataset"]["stations"]])
    receipt = value["receipt"]
    fields(receipt, RECEIPT_KEYS)
    require(receipt["adapter_version"] == "1", "producer_adapter_version")
    for key in RECEIPT_KEYS.split():
        if key.endswith("sha256"):
            sha(receipt[key])
    fields(receipt["acceptance"], "host_approved full_method_accepted field_source_verified")
    require(all(flag is False for flag in receipt["acceptance"].values()) and processing["full_method_accepted"] is False,
            "producer_false_acceptance")
    runtime = manifest["runtime_manifest"]
    require(receipt["engines"] == processing["engines"] == runtime["packages"]
            and receipt["python"] == processing["python"] == runtime["python"]
            and receipt["python_implementation"] == runtime["python_implementation"]
            and receipt["adapter_module_sha256"] == manifest["adapter_sha256"]
            and receipt["core_module_sha256"] == processing["module_sha256"] == manifest["core_sha256"], "producer_runtime_binding")
    require(processing["method"] == "M01-local-station-corrections" and
            receipt["correction_result_sha256"] == scientific_digest(core) and
            receipt["output_dataset_sha256"] == processing["output_sha256"] == scientific_digest(core["dataset"]) and
            receipt["input_dataset_sha256"] == processing["input_sha256"] and
            receipt["normalized_config_sha256"] == scientific_digest(processing["config"]), "producer_core_binding")
    return receipt, core


def _child(body):
    value = _decode(body, 16*M)
    fields(value, DATASET_KEYS)
    require((value["schema"], value["kind"], value["parser_version"], value["modality"],
             value["payload_schema"], value["structural_verdict"]) ==
            ("geophysics.physical-dataset/v2", "derived", "gravity-stations-json/v1",
             "gravity_physical_station", "gravity-station-adapter-result-1", "child_verified"), "producer_child_schema")
    for key in ("dataset_id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "parent_dataset_id"):
        uuid(value[key])
    for key in ("raw_sha256", "scientific_payload_sha256", "parent_dataset_sha256"):
        sha(value[key])
    integer(value["raw_bytes"], 1, 16*M)
    integer(value["version"], 2, J)
    require(value["dataset_id"] not in (value["root_dataset_id"], value["parent_dataset_id"]), "producer_child_identity")
    source_structure(value["source"])
    fields(value["production"], PRODUCTION_KEYS)
    return value


def verify_correction_producer(snapshot, *, input_bytes, child_bytes, request_bytes,
                               result_bytes, approved_manifest, job, production):
    """Validate one saved producing edge against complete bytes and SQL receipts.

    No file open, mutation, engine import, uncertainty reconstruction or solve.
    Caller owns coherent SQL/file read exclusion and whole-forest enumeration.
    Returns the unchanged supplied snapshot, only after all four bodies pass.
    """
    fields(snapshot, PARENT_KEYS)
    require(all(v is not None for v in snapshot.values()) and
            (snapshot["schema"], snapshot["method_id"], snapshot["state"], snapshot["scientific_verdict"]) ==
            ("geophysics.physical-parent-production/v1", CORRECTION, "succeeded", "passed"), "producer_snapshot")
    for key in ("owner_id", "project_id", "root_dataset_id", "raw_asset_id", "output_dataset_id", "job_id", "input_dataset_id"):
        uuid(snapshot[key])
    for key in PARENT_KEYS.split():
        if key.endswith("sha256"):
            sha(snapshot[key])
    integer(snapshot["raw_bytes"], 1, 16*M)
    integer(snapshot["output_dataset_version"], 2, J)
    for key, body, cap in (("output_dataset", child_bytes, 16*M), ("result", result_bytes, 64*M)):
        integer(snapshot[key+"_bytes"], 1, cap)
        require(type(body) is bytes and (len(body), byte_sha(body)) ==
                (snapshot[key+"_bytes"], snapshot[key+"_sha256"]), "producer_saved_bytes")
    require(byte_sha(input_bytes) == snapshot["input_dataset_sha256"], "producer_saved_input")
    child = _child(child_bytes)
    parent = _decode(input_bytes, 16*M)
    parent = root_envelope([input_bytes]) if parent.get("kind") == "root" else _child(input_bytes)
    require((child["parent_dataset_id"], child["parent_dataset_sha256"]) ==
            (parent["dataset_id"], byte_sha(input_bytes)) and parent["version"] < child["version"], "producer_edge")
    require((child["dataset_id"], child["version"]) ==
            (snapshot["output_dataset_id"], snapshot["output_dataset_version"]), "producer_output")
    for key in ("owner_id", "project_id", "root_dataset_id", "raw_asset_id", "raw_sha256", "raw_bytes"):
        require(snapshot[key] == child[key] == parent[key], "producer_family")
    _same(child["source"], parent["source"])
    require(parent["dataset_id"] == snapshot["input_dataset_id"], "producer_input")
    req = _decode(request_bytes, 34*M, 24, 500000)
    result = _decode(result_bytes, 64*M)
    fields(req, REQUEST_KEYS)
    fields(result, RESULT_KEYS)
    require(req["schema"] == "geophysics.physical-request/v2" and result["schema"] == "geophysics.physical-result/v2", "producer_wrapped_schema")
    for key in ("owner_id", "project_id", "raw_asset_id", "raw_sha256", "raw_bytes", "job_id", "method_id",
                "submitted_parameters_sha256", "scientific_request_sha256", "module_manifest_sha256"):
        require(req[key] == result[key] == snapshot[key], "producer_request_result")
    require(req["root_dataset_id"] == snapshot["root_dataset_id"] and
            req["dataset_id"] == result["dataset_id"] == snapshot["input_dataset_id"] and
            req["dataset_sha256"] == result["dataset_sha256"] == snapshot["input_dataset_sha256"] and
            digest(req) == result["request_sha256"] == snapshot["request_sha256"] and
            digest(req["parameters"]) == snapshot["submitted_parameters_sha256"], "producer_request_digest")
    _manifest(snapshot["module_manifest"], approved_manifest)
    _same(req["module_manifest"], snapshot["module_manifest"])
    _same(result["module_manifest"], snapshot["module_manifest"])
    require(digest(snapshot["module_manifest"]) == snapshot["module_manifest_sha256"], "producer_manifest_digest")
    science = req["scientific_request"]
    fields(science, "schema_version method dataset config input_dataset_sha256 submitted_config_sha256")
    require((science["schema_version"], science["method"]) == ("gravity-station-adapter-request-1", CORRECTION), "producer_scientific_request")
    _same(science["config"], req["parameters"])
    _configuration(science["config"], [s["station_id"] for s in science["dataset"]["stations"]])
    expected_input = parent["payload"] if parent["kind"] == "root" else parent["payload"]["correction_result"]["dataset"]
    _same(science["dataset"], expected_input)
    require(scientific_digest(science) == snapshot["scientific_request_sha256"] and
            scientific_digest(science["dataset"]) == science["input_dataset_sha256"] and
            scientific_digest(science["config"]) == science["submitted_config_sha256"] == snapshot["submitted_config_sha256"], "producer_scientific_digest")
    if parent["kind"] == "root":
        require(req["parent_production"] is None, "producer_root_snapshot")
    else:
        earlier = req["parent_production"]
        fields(earlier, PARENT_KEYS)
        require((earlier["output_dataset_id"], earlier["output_dataset_sha256"], earlier["output_dataset_bytes"]) ==
                (parent["dataset_id"], byte_sha(input_bytes), len(input_bytes)), "producer_earlier_snapshot")
        # Complete earlier-edge verification remains caller's ancestry barrier.
    payload = child["payload"]
    require(scientific_digest(payload) == child["scientific_payload_sha256"] ==
            result["scientific_result_sha256"] == snapshot["adapter_result_sha256"], "producer_adapter_digest")
    _same(payload, result["scientific_result"])
    receipt, _ = _adapter(payload, snapshot["module_manifest"])
    _same(receipt, snapshot["adapter_receipt"])
    require(scientific_digest(receipt) == snapshot["adapter_receipt_sha256"] and
            receipt["request_sha256"] == snapshot["scientific_request_sha256"] and
            receipt["input_dataset_sha256"] == science["input_dataset_sha256"] and
            receipt["submitted_config_sha256"] == snapshot["submitted_config_sha256"] and
            receipt["normalized_config_sha256"] == snapshot["normalized_config_sha256"] and
            receipt["correction_result_sha256"] == snapshot["core_result_sha256"], "producer_adapter_receipt")
    for key in PRODUCTION_KEYS.split():
        expected = snapshot["adapter_result_sha256"] if key == "scientific_result_sha256" else snapshot[key]
        require(child["production"][key] == expected, "producer_child_production")
    require((result["output_dataset_id"], result["output_dataset_sha256"], result["scientific_verdict"]) ==
            (child["dataset_id"], byte_sha(child_bytes), "passed"), "producer_result_output")
    limits = req["limits"]
    fields(limits, "cpu_ms wall_seconds rss_bytes scratch_bytes scientific_input_bytes child_output_bytes stdout_bytes stderr_bytes")
    ceilings = dict(cpu_ms=60000, wall_seconds=120, rss_bytes=768*M, scratch_bytes=256*M,
                    scientific_input_bytes=16*M, child_output_bytes=64*M, stdout_bytes=65536, stderr_bytes=65536)
    for key, ceiling in ceilings.items():
        integer(limits[key], 1, ceiling)
        if key in ("scientific_input_bytes", "child_output_bytes", "stdout_bytes", "stderr_bytes"):
            require(limits[key] == ceiling, "producer_fixed_limit")
    sha(req["admission_receipt_sha256"])
    measured = result["receipt"]
    fields(measured, "wall_ms cpu_ms peak_rss_bytes scratch_peak_bytes child_output_bytes environment environment_sha256 admission_receipt_sha256")
    for key, ceiling in (("wall_ms", limits["wall_seconds"]*1000), ("cpu_ms", limits["cpu_ms"]),
                         ("peak_rss_bytes", limits["rss_bytes"]), ("scratch_peak_bytes", limits["scratch_bytes"]),
                         ("child_output_bytes", limits["child_output_bytes"])):
        integer(measured[key], 0 if key in ("wall_ms", "cpu_ms", "scratch_peak_bytes") else 1, ceiling)
    require(measured["admission_receipt_sha256"] == req["admission_receipt_sha256"] and
            digest(measured["environment"]) == sha(measured["environment_sha256"]), "producer_resource_receipt")
    for key, resource_key in (("wall_ms", "wall_ms"), ("physical_cpu_ms", "cpu_ms"),
                              ("peak_rss_bytes", "peak_rss_bytes"), ("scratch_bytes", "scratch_peak_bytes")):
        require(job[key] == measured[resource_key], "producer_job_resource")
    require(job["result_key"] == f'derived/{snapshot["owner_id"]}/{snapshot["project_id"]}/results/{snapshot["job_id"]}.json'
            and job["finished_at"] is not None and job["error_code"] is None and job["error_message"] is None,
            "producer_job_terminal")
    require((job["id"], job["owner_id"], job["project_id"], job["dataset_id"], job["dataset_sha256"], job["method_id"],
             job["state"], job["request_sha256"], job["result_sha256"], job["result_bytes"]) ==
            tuple(snapshot[k] for k in ("job_id", "owner_id", "project_id", "input_dataset_id", "input_dataset_sha256", "method_id",
                                       "state", "request_sha256", "result_sha256", "result_bytes")), "producer_saved_job")
    for key in ("child_dataset_id", "job_id", "owner_id", "project_id", "root_dataset_id", "raw_asset_id", "parent_dataset_id",
                "parent_dataset_sha256", "method_id", "request_sha256", "submitted_parameters_sha256", "scientific_request_sha256",
                "scientific_result_sha256", "module_manifest_sha256", "result_sha256", "result_bytes", "scientific_verdict",
                "adapter_result_sha256", "adapter_receipt_sha256", "core_result_sha256", "submitted_config_sha256", "normalized_config_sha256"):
        mapped = {"child_dataset_id": "output_dataset_id", "parent_dataset_id": "input_dataset_id",
                  "parent_dataset_sha256": "input_dataset_sha256", "scientific_result_sha256": "adapter_result_sha256"}.get(key, key)
        require(production[key] == snapshot[mapped], "producer_saved_relation")
    saved_receipt = _decode(production["adapter_receipt_bytes"], 65536, 16, 10000)
    _same(saved_receipt, receipt)
    return snapshot
