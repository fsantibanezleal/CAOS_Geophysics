"""Ordinary M01 station correction boundary; no API, storage or host approval.

Accepts already strictly decoded native objects. Transport/owner/job integrity
and field-source verification remain separate main-owned responsibilities.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import re
from statistics import median
import sys
from types import ModuleType


CORE_SHA256 = "7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321"
PINS = {"boule": "0.5.0", "harmonica": "0.7.0", "numpy": "2.2.6", "scipy": "1.15.2"}
METHOD = "gravity.station-corrections/v1"
MAX_STATIONS = 400
MAX_DEPTH = 16
MAX_NODES = 200000
MAX_STRING_BYTES = 8192
MAX_KEY_BYTES = 128
MAX_CANONICAL_BYTES = 16 * 1024 * 1024
_ADAPTER_PATH = Path(__file__).resolve()
_CORE_PATH = _ADAPTER_PATH.with_name("gravity_processing.py")
_REQUEST_KEYS = {"schema_version", "method", "dataset", "config", "input_dataset_sha256", "submitted_config_sha256"}
_DATASET_KEYS = {"schema_version", "state", "metadata", "stations", "history"}
_PROCESSING_KEYS = {
    "method",
    "input_sha256",
    "output_sha256",
    "config",
    "engines",
    "python",
    "module_sha256",
    "uncertainty_model",
    "uncertainty_mgal",
    "uncertainty_components_mgal",
    "full_method_accepted",
    "warnings",
}
_CONFIG_KEYS = {"target", "uncertainty_model", "density_kg_m3", "density_sigma_kg_m3", "outlier_z", "terrain"}
_QC_KEYS = {
    "station_ids",
    "longitude_deg",
    "latitude_deg",
    "receiver_ellipsoidal_m",
    "surface_ellipsoidal_m",
    "original_mgal",
    "derived_mgal",
    "robust_z",
    "outlier_flag",
    "excluded_station_ids",
}
_COMPONENT_KEYS = {"observed_gravity", "latitude", "receiver_height", "surface_height", "density", "geoid", "terrain"}
_HISTORY_KEYS = {"name", "parameters", "additions_mgal", "input_values_sha256", "output_values_sha256"}
_ERRORS = {
    "adapter_contract": ("request", "Request does not match the reviewed station adapter contract."),
    "adapter_limit": ("request", "Request exceeds the reviewed local adapter bounds."),
    "input_identity": ("input_dataset_sha256", "Parent dataset integrity does not match the supplied identity."),
    "config_identity": (
        "submitted_config_sha256",
        "Submitted configuration integrity does not match the supplied identity.",
    ),
    "scientific_contract": (None, "Dataset or configuration does not satisfy the reviewed correction contract."),
    "runtime_incompatible": (
        "runtime",
        "Reviewed runtime, engine or scientific core identity is unavailable or incompatible.",
    ),
    "result_integrity": ("result", "Scientific result does not satisfy the reviewed adapter postconditions."),
    "execution_failed": (None, "Station correction execution failed without a publishable result."),
}


class GravityStationAdapterError(ValueError):
    """Only to_record() is a safe serialized failure surface, never context/locals."""

    def __init__(self, code):
        self.code = code if type(code) is str and code in _ERRORS else "execution_failed"
        self.field, self.message = _ERRORS[self.code]
        super().__init__(self.message)

    def to_record(self):
        return {"code": self.code, "field": self.field, "message": self.message, "retryable": False}


def _fail(code):
    raise GravityStationAdapterError(code) from None


def _need(condition):
    if not condition:
        _fail("result_integrity")


def _native(value):
    """Bound exact native structure before hooks, copies, imports or serialization."""
    nodes, ancestry = 0, set()

    def text(item, limit):
        if len(item) > limit:
            _fail("adapter_limit")
        try:
            if len(item.encode("utf-8")) > limit:
                _fail("adapter_limit")
        except UnicodeError:
            _fail("adapter_contract")

    def walk(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES:
            _fail("adapter_limit")
        kind = type(item)
        if kind is dict or kind is list:
            if depth > MAX_DEPTH:
                _fail("adapter_limit")
            if id(item) in ancestry:
                _fail("adapter_contract")
            ancestry.add(id(item))
            if kind is dict:
                for key, child in item.items():
                    nodes += 1
                    if nodes > MAX_NODES:
                        _fail("adapter_limit")
                    if type(key) is not str:
                        _fail("adapter_contract")
                    text(key, MAX_KEY_BYTES)
                    walk(child, depth + 1)
            else:
                for child in item:
                    walk(child, depth + 1)
            ancestry.remove(id(item))
        elif kind is str:
            text(item, MAX_STRING_BYTES)
        elif kind is int or kind is float:
            if kind is int and item.bit_length() > 1024:
                _fail("adapter_contract")
            try:
                if not math.isfinite(float(item)):
                    _fail("adapter_contract")
            except OverflowError:
                _fail("adapter_contract")
        elif kind is not bool and item is not None:
            _fail("adapter_contract")

    walk(value, 1)


def _digest(value):
    """The core's canonical semantics, streamed with an actual encoded-byte cap."""
    result, count = sha256(), 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), allow_nan=False)
    for part in encoder.iterencode(value):
        encoded = part.encode("utf-8")
        count += len(encoded)
        if count > MAX_CANONICAL_BYTES:
            _fail("adapter_limit")
        result.update(encoded)
    return result.hexdigest()


def _sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _same_file(module):
    if type(module) is not ModuleType:
        return False
    filename = vars(module).get("__file__")
    # Reject a shadow path lexically before any filesystem resolution (including
    # a possible remote/UNC target). Only the fixed own sibling is resolved.
    return (
        type(filename) is str
        and Path(os.path.abspath(filename)) == _CORE_PATH
        and Path(filename).resolve(strict=True) == _CORE_PATH.resolve(strict=True)
    )


def _load_core():
    try:
        if (
            platform.python_implementation() != "CPython"
            or re.fullmatch(r"3\.12\.(0|[1-9][0-9]{0,2})", platform.python_version()) is None
            or sha256(_CORE_PATH.read_bytes()).hexdigest() != CORE_SHA256
        ):
            _fail("runtime_incompatible")
        if "gravity_processing" in sys.modules and not _same_file(sys.modules["gravity_processing"]):
            _fail("runtime_incompatible")
        import gravity_processing as core

        if (
            not _same_file(core)
            or core.PINS != PINS
            or {name: version(name) for name in PINS} != PINS
            or type(vars(core).get("GravityContractError")) is not type
            or not issubclass(core.GravityContractError, ValueError)
        ):
            _fail("runtime_incompatible")
        return core
    except Exception:
        _fail("runtime_incompatible")


def _number(value, nonnegative=False):
    return type(value) in (int, float) and math.isfinite(float(value)) and (not nonnegative or value >= 0)


def _array(value, count, *, nonnegative=False, nullable=False):
    _need(type(value) is list and len(value) == count)
    _need(all((nullable and item is None) or _number(item, nonnegative) for item in value))


def _keys(value, keys):
    _need(type(value) is dict and value.keys() == keys)


def _postconditions(core, request, result, normalized):
    """Fresh-call schema/identity/conservation checks, not an external replay claim."""
    _native(result)
    _keys(result, {"dataset", "processing", "qc"})
    dataset, processing, qc = result["dataset"], result["processing"], result["qc"]
    _keys(dataset, _DATASET_KEYS)
    _keys(processing, _PROCESSING_KEYS)
    _keys(qc, _QC_KEYS)
    _keys(processing["config"], _CONFIG_KEYS)
    _keys(processing["engines"], set(PINS))
    _keys(processing["uncertainty_components_mgal"], _COMPONENT_KEYS)
    parent = request["dataset"]
    rows = parent["stations"]
    count = len(rows)
    _need(dataset["schema_version"] == "gravity-stations-1" and dataset["state"] == normalized["target"])
    _need(_digest(dataset["metadata"]) == _digest(parent["metadata"]))
    _need(type(dataset["stations"]) is list and len(dataset["stations"]) == count)
    for before, after in zip(rows, dataset["stations"], strict=True):
        _keys(after, set(before))
        unchanged = deepcopy(after)
        unchanged["value_mgal"] = before["value_mgal"]
        _need(_digest(unchanged) == _digest(before))
        _need(_number(after["value_mgal"]))
    _need(processing["method"] == "M01-local-station-corrections")
    _need(processing["input_sha256"] == request["input_dataset_sha256"])
    _need(processing["output_sha256"] == _digest(dataset))
    _need(processing["module_sha256"] == CORE_SHA256)
    _need(processing["engines"] == PINS and processing["python"] == platform.python_version())
    _need(_digest(processing["config"]) == _digest(normalized))
    _need(processing["uncertainty_model"] == normalized["uncertainty_model"])
    _need(processing["full_method_accepted"] is False)
    _need(type(processing["warnings"]) is list and bool(processing["warnings"]))
    _need(all(type(w) is str and bool(w.strip()) for w in processing["warnings"]))
    factor = core.UNIT_FACTORS[parent["metadata"]["gravity_unit"]]
    sign = 1 if parent["metadata"]["gravity_sign"] == "downward" else -1
    original = [float(row["original_value"]) * factor * sign for row in rows]
    values = original.copy()
    history = dataset["history"]
    expected_count = core.STATE_LENGTHS[core.STATES.index(normalized["target"])]
    _need(type(history) is list and len(history) == expected_count)
    _need(_digest(history[: len(parent["history"])]) == _digest(parent["history"]))
    ref = {"ellipsoid": "WGS84", "height_reference": "WGS84_ellipsoid", "boule": PINS["boule"]}
    parameters = [
        ref,
        {**ref, "height_term": "gamma(phi,0)-gamma(phi,h)"},
        {
            "harmonica": PINS["harmonica"],
            "density_kg_m3": normalized["density_kg_m3"],
            "density_sigma_kg_m3": normalized["density_sigma_kg_m3"],
            "geometry": "land_infinite_plate",
            "height_reference": "WGS84_ellipsoid",
        },
        normalized["terrain"],
    ]
    for i, record in enumerate(history):
        _keys(record, _HISTORY_KEYS)
        _need(record["name"] == core.HISTORY_NAMES[i])
        _need(_digest(record["parameters"]) == _digest(parameters[i]))
        _array(record["additions_mgal"], count)
        _need(record["input_values_sha256"] == _digest(values))
        values = [a + b for a, b in zip(values, record["additions_mgal"], strict=True)]
        _need(record["output_values_sha256"] == _digest(values))
    _need(_digest(values) == _digest([row["value_mgal"] for row in dataset["stations"]]))
    _need(qc["station_ids"] == [row["station_id"] for row in rows])
    for key in ("longitude_deg", "latitude_deg"):
        _array(qc[key], count)
        _need(_digest(qc[key]) == _digest([float(row[key]) for row in rows]))
    for key, field in (("receiver_ellipsoidal_m", "receiver_height_m"), ("surface_ellipsoidal_m", "surface_height_m")):
        _array(qc[key], count)
        heights = [
            float(row[field]) + (float(row["geoid_m"]) if parent["metadata"]["height_datum"] == "orthometric" else 0.0)
            for row in rows
        ]
        _need(_digest(qc[key]) == _digest(heights))
    for key, expected in (("original_mgal", original), ("derived_mgal", values)):
        _array(qc[key], count)
        _need(_digest(qc[key]) == _digest(expected))
    _array(qc["robust_z"], count, nonnegative=True, nullable=True)
    _need(type(qc["outlier_flag"]) is list and len(qc["outlier_flag"]) == count)
    _need(all(type(flag) is bool for flag in qc["outlier_flag"]))
    _need(qc["excluded_station_ids"] == [])
    centre = median(values)
    mad = median([abs(v - centre) for v in values])
    if count < 5 or mad == 0:
        _need(qc["robust_z"] == [None] * count and qc["outlier_flag"] == [False] * count)
    else:
        scores = [abs(v - centre) / (1.4826 * mad) for v in values]
        _need(
            all(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12) for a, b in zip(qc["robust_z"], scores, strict=True))
        )
        _need(qc["outlier_flag"] == [s > normalized["outlier_z"] for s in scores])
    _array(processing["uncertainty_mgal"], count, nonnegative=True)
    components = processing["uncertainty_components_mgal"]
    for component in components.values():
        _array(component, count, nonnegative=True)
    for i, actual in enumerate(processing["uncertainty_mgal"]):
        expected = (
            math.sqrt(sum(c[i] ** 2 for c in components.values()))
            if processing["uncertainty_model"] == "independent_first_order"
            else sum(c[i] for c in components.values())
        )
        _need(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12))


def run_station_corrections(request: dict) -> dict:
    """Run one reviewed local reduction; preserve exact parents and false acceptance."""
    _native(request)
    if (
        type(request) is not dict
        or request.keys() != _REQUEST_KEYS
        or request["schema_version"] != "gravity-station-adapter-request-1"
        or request["method"] != METHOD
        or type(request["dataset"]) is not dict
        or type(request["config"]) is not dict
    ):
        _fail("adapter_contract")
    rows = request["dataset"].get("stations")
    if type(rows) is not list:
        _fail("scientific_contract")
    if not 1 <= len(rows) <= MAX_STATIONS:
        _fail("adapter_limit")
    request_hash = _digest(request)
    if not _sha(request["input_dataset_sha256"]) or request["input_dataset_sha256"] != _digest(request["dataset"]):
        _fail("input_identity")
    if not _sha(request["submitted_config_sha256"]) or request["submitted_config_sha256"] != _digest(request["config"]):
        _fail("config_identity")
    admitted = deepcopy(request)
    core = _load_core()
    contract_error = core.GravityContractError
    try:
        normalized = deepcopy(vars(core.CorrectionConfig.parse(admitted["config"])))
        result = core.process_survey(deepcopy(admitted["dataset"]), deepcopy(admitted["config"]))
    except contract_error:
        _fail("scientific_contract")
    except Exception:
        _fail("execution_failed")
    try:
        _postconditions(core, admitted, result, normalized)
        receipt = {
            "adapter_version": "1",
            "adapter_module_sha256": sha256(_ADAPTER_PATH.read_bytes()).hexdigest(),
            "core_module_sha256": CORE_SHA256,
            "request_sha256": request_hash,
            "input_dataset_sha256": admitted["input_dataset_sha256"],
            "submitted_config_sha256": admitted["submitted_config_sha256"],
            "normalized_config_sha256": _digest(result["processing"]["config"]),
            "output_dataset_sha256": _digest(result["dataset"]),
            "correction_result_sha256": _digest(result),
            "engines": deepcopy(PINS),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "acceptance": {"host_approved": False, "full_method_accepted": False, "field_source_verified": False},
        }
    except Exception:
        _fail("result_integrity")
    return {
        "schema_version": "gravity-station-adapter-result-1",
        "method": METHOD,
        "correction_result": result,
        "receipt": receipt,
    }
