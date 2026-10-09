"""Scoped adapter controls: original synthetic physics, never field acceptance."""

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import math
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType

import numpy as np
import pytest

import gravity_processing as core
import gravity_station_adapter as adapter


ROOT = Path(__file__).resolve().parents[2]
PRIVATE = "PRIVATE_STATION_CITATION_TOKEN_D:/private/source.zip"


def somigliana(latitude):
    # Same independent published constants/tolerance as the approved core gate.
    f, ge, gp = 1 / 298.257223563, 9.7803253359, 9.8321849378
    s = math.sin(math.radians(latitude)) ** 2
    return ge * (1 + ((1 - f) * gp / ge - 1) * s) / math.sqrt(1 - (2 * f - f**2) * s) * 1e5


def survey(count=1):
    return {
        "schema_version": "gravity-stations-1",
        "state": "observed_absolute",
        "history": [],
        "metadata": {
            "source_kind": "synthetic_control",
            "source_sha256": sha256(b"Original adapter analytical station controls").hexdigest(),
            "source_citation": "Authored analytical adapter controls, not field observations",
            "rights": "Authored test definition, Apache-2.0",
            "crs": "EPSG:4326",
            "reference_ellipsoid": "WGS84",
            "height_datum": "ellipsoidal",
            "height_unit": "m",
            "height_sign": "upward",
            "gravity_unit": "mGal",
            "gravity_sign": "downward",
            "gravity_quantity": "absolute_gravity",
            "gravity_datum": "Authored WGS84 normal-field control",
            "tide_system": "tide_free",
            "instrument_processing": {
                key: {
                    "status": "applied" if key == "calibration" else "not_applicable",
                    "citation": "Analytical controls have no meter drift or tides",
                }
                for key in ("calibration", "drift", "tide")
            },
        },
        "stations": [
            {
                "station_id": f"analytical-{i}",
                "latitude_deg": 45.0,
                "longitude_deg": i / 10,
                "receiver_height_m": 0.0,
                "surface_height_m": 0.0,
                "original_value": somigliana(45) + i,
                "value_mgal": somigliana(45) + i,
                "gravity_sigma": 0.1,
                "receiver_sigma_m": 0.0,
                "surface_sigma_m": 0.0,
                "latitude_sigma_deg": 0.0,
            }
            for i in range(count)
        ],
    }


def config(target="gravity_disturbance", **changes):
    cfg = {"target": target, "uncertainty_model": "independent_first_order"}
    if target in core.STATES[2:]:
        cfg.update(density_kg_m3=2670.0, density_sigma_kg_m3=0.0)
    if target == core.STATES[3]:
        cfg["uncertainty_model"] = "conservative_marginals"
    return {**cfg, **changes}


def terrain(rows, additions=None):
    return {
        "kind": "additive_residual_to_plate",
        "unit": "mGal",
        "height_reference": "WGS84_ellipsoid",
        "density_kg_m3": 2670.0,
        "source_sha256": sha256(b"Authored signed terrain residual, not a DEM").hexdigest(),
        "method": "Original analytical residual, no field terrain model",
        "station_ids": [r["station_id"] for r in rows],
        "additions_mgal": additions or [2.0] * len(rows),
        "sigma_mgal": [0.2] * len(rows),
    }


def request(dataset=None, cfg=None):
    dataset = survey() if dataset is None else dataset
    cfg = config() if cfg is None else cfg
    return {
        "schema_version": "gravity-station-adapter-request-1",
        "method": "gravity.station-corrections/v1",
        "dataset": dataset,
        "config": cfg,
        "input_dataset_sha256": core.digest(dataset),
        "submitted_config_sha256": core.digest(cfg),
    }


def rehash(req):
    req["input_dataset_sha256"] = core.digest(req["dataset"])
    req["submitted_config_sha256"] = core.digest(req["config"])
    return req


def reject(req, code):
    with pytest.raises(adapter.GravityStationAdapterError) as caught:
        adapter.run_station_corrections(req)
    record = caught.value.to_record()
    assert set(record) == {"code", "field", "message", "retryable"}
    assert record["code"] == code and record["retryable"] is False
    assert PRIVATE not in json.dumps(record) and PRIVATE not in str(caught.value)
    assert caught.value.__suppress_context__ is True
    return record


@pytest.mark.parametrize("target", core.STATES[1:])
def test_real_core_parity_preserves_request(target, monkeypatch):
    data = survey(7)
    cfg = config(target)
    if target == core.STATES[3]:
        cfg["terrain"] = terrain(data["stations"])
    req = request(data, cfg)
    unchanged = deepcopy(req)
    expected = core.process_survey(data, cfg)
    calls = []
    real = core.process_survey

    def counted(dataset, configuration):
        assert dataset == data and configuration == cfg
        calls.append(1)
        return real(dataset, configuration)

    monkeypatch.setattr(core, "process_survey", counted)
    result = adapter.run_station_corrections(req)
    assert calls == [1] and req == unchanged
    assert set(result) == {"schema_version", "method", "correction_result", "receipt"}
    assert result["schema_version"] == "gravity-station-adapter-result-1"
    assert result["method"] == "gravity.station-corrections/v1"
    assert core.digest(result["correction_result"]) == core.digest(expected)
    result["correction_result"]["dataset"]["stations"][0]["original_value"] = -123
    assert req == unchanged


@pytest.mark.parametrize("count", [1, 400])
def test_exact_station_bounds_without_thinning(count):
    req = request(survey(count))
    result = adapter.run_station_corrections(req)
    assert len(result["correction_result"]["dataset"]["stations"]) == count
    assert result["correction_result"]["qc"]["excluded_station_ids"] == []
    assert result["receipt"]["input_dataset_sha256"] == core.digest(req["dataset"])


@pytest.mark.parametrize("mutation", ["schema", "method", "extra", "missing", "csv", "flags", "ops", "mask"])
def test_exact_contract_and_unsupported_inputs(mutation):
    req = request()
    if mutation == "schema":
        req["schema_version"] = "gravity-transform-request-1"
    elif mutation == "method":
        req["method"] = "M01"
    elif mutation == "extra":
        req[PRIVATE] = True
    elif mutation == "missing":
        del req["config"]
    elif mutation in ("csv", "flags", "ops"):
        req["dataset"] = {
            "schema_version": "gravity-station-csv/v1",
            "OG": "already processed",
            "CBA": "unknown correction lineage",
        }
        if mutation == "flags":
            req["method"] = "gravity.station-outlier-flags/v1"
        if mutation == "ops":
            req["method"] = "gravity.unknown-ops/v1"
        rehash(req)
    else:
        req["dataset"]["mask"] = [False]
        rehash(req)
    reject(req, "scientific_contract" if mutation in ("csv", "mask") else "adapter_contract")


@pytest.mark.parametrize("mutation", ["parent", "config", "malformed_parent", "malformed_config", "source_as_parent"])
def test_exact_input_and_config_identity(mutation, monkeypatch):
    req = request()
    if mutation == "parent":
        req["dataset"]["stations"][0]["original_value"] += 1
    elif mutation == "config":
        req["config"]["outlier_z"] = 7
    elif mutation == "malformed_parent":
        req["input_dataset_sha256"] = "A" * 64
    elif mutation == "malformed_config":
        req["submitted_config_sha256"] = ["0" * 64]
    else:
        req["input_dataset_sha256"] = req["dataset"]["metadata"]["source_sha256"]
    monkeypatch.setattr(core, "process_survey", lambda *args: pytest.fail("stale identity reached numerics"))
    reject(req, "config_identity" if "config" in mutation else "input_identity")


def test_exact_parent_resume_and_no_double_correction():
    data = survey()
    # Genuine exact-parent integer representation, not reconstructable float substitution.
    data["stations"][0].update(original_value=980000, value_mgal=980000)
    raw = deepcopy(data)
    first = adapter.run_station_corrections(request(data))
    assert first["receipt"]["input_dataset_sha256"] == core.digest(raw)
    assert type(raw["stations"][0]["value_mgal"]) is int
    assert data == raw
    parent = first["correction_result"]["dataset"]
    second = adapter.run_station_corrections(request(parent, config(core.STATES[2])))
    assert second["receipt"]["input_dataset_sha256"] == core.digest(parent)
    assert second["correction_result"]["dataset"] == core.process_survey(raw, config(core.STATES[2]))["dataset"]
    bouguer = second["correction_result"]["dataset"]
    third_cfg = config(core.STATES[3], terrain=terrain(bouguer["stations"], [-2.0]))
    third = adapter.run_station_corrections(request(bouguer, third_cfg))
    assert third["receipt"]["input_dataset_sha256"] == core.digest(bouguer)
    assert third["correction_result"]["qc"]["derived_mgal"][0] == pytest.approx(
        second["correction_result"]["qc"]["derived_mgal"][0] - 2, abs=1e-10
    )
    for target in core.STATES[1:3]:
        reject(request(bouguer, config(target)), "scientific_contract")
    for damage in ("values", "history_hash", "prior_parameters", "history_order"):
        changed = deepcopy(parent)
        if damage == "values":
            changed["stations"][0]["value_mgal"] += 1
        elif damage == "history_hash":
            changed["history"][0]["output_values_sha256"] = "0" * 64
        elif damage == "prior_parameters":
            changed["history"][0]["parameters"]["ellipsoid"] = "Unknown"
        else:
            changed["history"].reverse()
        reject(request(changed, config(core.STATES[2])), "scientific_contract")


def test_formula_sign_and_uncertainty_oracles():
    data = survey(7)
    for row, latitude in zip(data["stations"], (-90, -60, -45, 0, 45, 60, 90), strict=True):
        row.update(latitude_deg=latitude, original_value=somigliana(latitude), value_mgal=somigliana(latitude))
    surface = adapter.run_station_corrections(request(data))["correction_result"]
    np.testing.assert_allclose(surface["qc"]["derived_mgal"], 0, atol=1e-5, rtol=0)
    known = survey()
    row = known["stations"][0]
    row.update(
        receiver_height_m=1000, surface_height_m=1000, original_value=980311.28969268, value_mgal=980311.28969268
    )
    height = adapter.run_station_corrections(request(known))["correction_result"]
    assert height["qc"]["derived_mgal"][0] == pytest.approx(0, abs=1e-7)
    assert height["dataset"]["history"][1]["additions_mgal"][0] == pytest.approx(308.48724505, abs=1e-7)
    plate = 2 * math.pi * 6.67430e-11 * 2670 * 1000 * 1e5
    row.update(original_value=980311.28969268 + plate + 12, value_mgal=980311.28969268 + plate + 12)
    cfg = config(core.STATES[2])
    derived = adapter.run_station_corrections(request(known, cfg))["correction_result"]
    assert derived["dataset"]["history"][2]["additions_mgal"][0] == pytest.approx(-plate, abs=1e-10)
    assert derived["qc"]["derived_mgal"][0] == pytest.approx(12, abs=1e-8)
    for unit, factor, sign in (("m/s^2", 1e5, 1), ("microGal", 1e-3, 1), ("mGal", 1, -1)):
        converted = deepcopy(known)
        converted["metadata"].update(gravity_unit=unit, gravity_sign="upward" if sign < 0 else "downward")
        for r in converted["stations"]:
            r["original_value"] /= factor * sign
            r["gravity_sigma"] /= factor
            r["value_mgal"] = float(r["original_value"]) * factor * sign
        other = adapter.run_station_corrections(request(converted, cfg))["correction_result"]
        np.testing.assert_allclose(other["qc"]["derived_mgal"], derived["qc"]["derived_mgal"], atol=1e-8, rtol=0)
        np.testing.assert_allclose(
            other["processing"]["uncertainty_mgal"], derived["processing"]["uncertainty_mgal"], atol=1e-12, rtol=0
        )
    orthometric = survey()
    orthometric["metadata"].update(height_datum="orthometric", geoid_model="Authored constant 30-m geoid")
    orthometric["stations"][0].update(
        receiver_height_m=970,
        surface_height_m=870,
        geoid_m=30,
        geoid_sigma_m=2,
        receiver_sigma_m=0.5,
        surface_sigma_m=0.7,
        latitude_sigma_deg=0.0002,
    )
    uncertainty = adapter.run_station_corrections(request(orthometric, config(core.STATES[2], density_sigma_kg_m3=20)))[
        "correction_result"
    ]
    components = uncertainty["processing"]["uncertainty_components_mgal"]
    gradient = -(3 * 980311.28969268 - 4 * 980345.55889093 + 980379.82987947) / (2 * (1000 / 9))
    coefficient = 2 * math.pi * 6.67430e-11 * 1e5
    assert components["receiver_height"][0] == pytest.approx(gradient * 0.5, abs=3e-7)
    assert components["surface_height"][0] == pytest.approx(coefficient * 2670 * 0.7, abs=1e-12)
    assert components["density"][0] == pytest.approx(coefficient * 900 * 20, abs=1e-12)
    assert components["geoid"][0] == pytest.approx((gradient - coefficient * 2670) * 2, abs=1.2e-6)
    assert uncertainty["processing"]["uncertainty_mgal"][0] == pytest.approx(
        math.sqrt(sum(v[0] ** 2 for v in components.values()))
    )
    del orthometric["stations"][0]["geoid_sigma_m"]
    reject(request(orthometric, cfg), "scientific_contract")


def test_uncertainty_kind_and_flags_preserved():
    data = survey(7)
    data["stations"][-1]["original_value"] += 100
    data["stations"][-1]["value_mgal"] += 100
    result = adapter.run_station_corrections(request(data))["correction_result"]
    assert result["qc"]["outlier_flag"] == [False] * 6 + [True]
    assert result["qc"]["excluded_station_ids"] == [] and len(result["dataset"]["stations"]) == 7
    assert result["processing"]["uncertainty_model"] == "independent_first_order"
    conservative = adapter.run_station_corrections(request(data, config(uncertainty_model="conservative_marginals")))[
        "correction_result"
    ]
    assert conservative["processing"]["uncertainty_model"] == "conservative_marginals"
    for i in range(7):
        assert conservative["processing"]["uncertainty_mgal"][i] == sum(
            v[i] for v in conservative["processing"]["uncertainty_components_mgal"].values()
        )
    zero = survey()
    zero["stations"][0]["gravity_sigma"] = 0
    assert adapter.run_station_corrections(request(zero))["correction_result"]["processing"]["uncertainty_mgal"] == [
        0.0
    ]


@pytest.mark.parametrize("damage", ["datum", "sigma", "instrument", "bool_number", "duplicates", "density", "terrain"])
def test_missing_physics_never_guessed(damage):
    data, cfg = survey(2), config()
    if damage == "datum":
        del data["metadata"]["height_datum"]
    elif damage == "sigma":
        data["stations"][0]["gravity_sigma"] = None
    elif damage == "instrument":
        data["metadata"]["instrument_processing"]["drift"]["status"] = "unknown"
    elif damage == "bool_number":
        data["stations"][0]["latitude_sigma_deg"] = False
    elif damage == "duplicates":
        data["stations"][1]["longitude_deg"] = 0.0
    elif damage == "density":
        cfg["target"] = core.STATES[2]
    else:
        cfg = config(core.STATES[3])
    original = deepcopy(data)
    reject(request(data, cfg), "scientific_contract")
    assert data == original


@pytest.mark.parametrize(
    "damage",
    [
        "nan",
        "inf",
        "huge_int",
        "cycle",
        "custom",
        "subclass",
        "decimal",
        "array",
        "bytes",
        "nonstring_key",
        "surrogate",
        "depth",
        "nodes",
        "value_size",
        "key_size",
        "canonical_size",
        "empty",
        "stations",
    ],
)
def test_bounded_native_request_before_numerics(damage, monkeypatch):
    req = request()
    value = req["dataset"]["metadata"]
    if damage in ("nan", "inf"):
        value["rights"] = float(damage)
    elif damage == "huge_int":
        value["rights"] = 1 << 2048
    elif damage == "cycle":
        value["rights"] = req
    elif damage == "custom":

        class Hook:
            def __deepcopy__(self, memo):
                pytest.fail("custom copy hook executed")

            def __str__(self):
                pytest.fail("custom string hook executed")

        value["rights"] = Hook()
    elif damage == "subclass":

        class Mapping(dict):
            def items(self):
                pytest.fail("mapping hook executed")

        value["rights"] = Mapping()
    elif damage == "decimal":
        value["rights"] = Decimal("1")
    elif damage == "array":
        value["rights"] = np.array([object()], dtype=object)
    elif damage == "bytes":
        value["rights"] = b"not decoded JSON"
    elif damage == "nonstring_key":
        value[1] = PRIVATE
    elif damage == "surrogate":
        value["rights"] = "\ud800"
    elif damage == "depth":
        nested = []
        for _ in range(17):
            nested = [nested]
        value["rights"] = nested
    elif damage == "nodes":
        monkeypatch.setattr(adapter, "MAX_NODES", 5)
    elif damage == "value_size":
        value["rights"] = "x" * 8193
    elif damage == "key_size":
        value["x" * 129] = PRIVATE
    elif damage == "canonical_size":
        monkeypatch.setattr(adapter, "MAX_CANONICAL_BYTES", 64)
    elif damage == "empty":
        req["dataset"]["stations"] = []
    else:
        req["dataset"]["stations"] *= 401
    monkeypatch.setattr(core, "process_survey", lambda *args: pytest.fail("invalid native input reached numerics"))
    code = (
        "adapter_limit"
        if damage in ("depth", "nodes", "value_size", "key_size", "canonical_size", "empty", "stations")
        else "adapter_contract"
    )
    reject(req, code)


@pytest.mark.parametrize(
    "damage",
    [
        "implementation",
        "version",
        "engines",
        "pins",
        "core_hash",
        "core_read",
        "shadow",
        "missing_file",
        "invalid_file",
        "import_failure",
        "returned_shadow",
        "invalid_exception_class",
    ],
)
def test_runtime_and_core_pin_fail_closed(damage, monkeypatch, tmp_path):
    req = request()
    if damage == "implementation":
        monkeypatch.setattr(adapter.platform, "python_implementation", lambda: "PyPy")
    elif damage == "version":
        monkeypatch.setattr(adapter.platform, "python_version", lambda: "3.11.10")
    elif damage == "engines":
        monkeypatch.setattr(adapter, "version", lambda name: "unreviewed")
    elif damage == "pins":
        monkeypatch.setattr(core, "PINS", {**core.PINS, "boule": "unreviewed"})
    elif damage in ("core_hash", "core_read"):
        real_read = Path.read_bytes

        def altered(path):
            if path.resolve() == Path(core.__file__).resolve():
                if damage == "core_read":
                    raise OSError(PRIVATE)
                return b"changed trusted file"
            return real_read(path)

        monkeypatch.setattr(Path, "read_bytes", altered)
    elif damage in ("shadow", "missing_file", "invalid_file", "returned_shadow", "invalid_exception_class"):
        fake = ModuleType("gravity_processing")
        fake.process_survey = lambda *args: pytest.fail("shadow invoked")
        if damage in ("shadow", "returned_shadow"):
            wrong = tmp_path / "shadow.py"
            wrong.write_text("# nonexecuted shadow control", encoding="utf-8")
            fake.__file__ = str(wrong)
        elif damage == "invalid_file":
            fake.__file__ = object()
        elif damage == "invalid_exception_class":
            fake.__file__ = core.__file__
            fake.PINS = core.PINS
            fake.GravityContractError = PRIVATE
        if damage == "returned_shadow":
            real_import = __import__

            def returned(name, *args, **kwargs):
                return fake if name == "gravity_processing" else real_import(name, *args, **kwargs)

            monkeypatch.setattr("builtins.__import__", returned)
        else:
            monkeypatch.setitem(sys.modules, "gravity_processing", fake)
    else:
        real_import = __import__

        def unavailable(name, *args, **kwargs):
            if name == "gravity_processing":
                raise ImportError(PRIVATE)
            return real_import(name, *args, **kwargs)

        monkeypatch.delitem(sys.modules, "gravity_processing")
        monkeypatch.setattr("builtins.__import__", unavailable)
    monkeypatch.setattr(core, "process_survey", lambda *args: pytest.fail("incompatible runtime reached numerics"))
    reject(req, "runtime_incompatible")


@pytest.mark.parametrize("exception", [core.GravityContractError, ValueError, RuntimeError, OSError])
def test_safe_errors_do_not_disclose_input(exception, monkeypatch, capsys):
    req = request()
    req["dataset"]["metadata"]["source_citation"] = PRIVATE
    rehash(req)

    def failed(*args):
        raise exception(PRIVATE)

    monkeypatch.setattr(core, "process_survey", failed)
    reject(req, "scientific_contract" if exception is core.GravityContractError else "execution_failed")
    assert capsys.readouterr() == ("", "")
    unknown = adapter.GravityStationAdapterError(PRIVATE)
    assert unknown.to_record()["code"] == "execution_failed" and PRIVATE not in str(unknown)


@pytest.mark.parametrize(
    "damage",
    [
        "root_extra",
        "processing_extra",
        "processing_missing",
        "config_extra",
        "qc_extra",
        "component_extra",
        "method",
        "input_hash",
        "output_hash",
        "module",
        "engines",
        "python",
        "full_acceptance",
        "normalized_config",
        "state",
        "original",
        "history",
        "qc_values",
        "errors",
        "error_shape",
        "bool_error",
        "flags",
        "excluded",
        "warning_type",
        "nonfinite",
    ],
)
def test_result_receipt_integrity(damage, monkeypatch):
    req = request()
    result = core.process_survey(req["dataset"], req["config"])
    p, qc = result["processing"], result["qc"]
    if damage == "root_extra":
        result[PRIVATE] = True
    elif damage == "processing_extra":
        p[PRIVATE] = True
    elif damage == "processing_missing":
        del p["warnings"]
    elif damage == "config_extra":
        p["config"][PRIVATE] = True
    elif damage == "qc_extra":
        qc[PRIVATE] = True
    elif damage == "component_extra":
        p["uncertainty_components_mgal"][PRIVATE] = [0]
    elif damage in ("method", "input_hash", "output_hash", "module", "engines", "python", "full_acceptance"):
        key = {
            "method": "method",
            "input_hash": "input_sha256",
            "output_hash": "output_sha256",
            "module": "module_sha256",
            "engines": "engines",
            "python": "python",
            "full_acceptance": "full_method_accepted",
        }[damage]
        p[key] = True if damage == "full_acceptance" else PRIVATE
    elif damage == "normalized_config":
        p["config"]["outlier_z"] = 7
    elif damage == "state":
        result["dataset"]["state"] = core.STATES[2]
    elif damage == "original":
        result["dataset"]["stations"][0]["original_value"] += 1
        p["output_sha256"] = core.digest(result["dataset"])
    elif damage == "history":
        result["dataset"]["history"][0]["output_values_sha256"] = "0" * 64
        p["output_sha256"] = core.digest(result["dataset"])
    elif damage == "qc_values":
        qc["derived_mgal"][0] += 1
    elif damage == "errors":
        p["uncertainty_mgal"][0] += 1
    elif damage == "error_shape":
        p["uncertainty_components_mgal"]["terrain"] = []
    elif damage == "bool_error":
        p["uncertainty_mgal"][0] = False
    elif damage == "flags":
        qc["outlier_flag"][0] = 0
    elif damage == "excluded":
        qc["excluded_station_ids"] = ["analytical-0"]
    elif damage == "warning_type":
        p["warnings"] = [True]
    else:
        qc["robust_z"] = [float("nan")]
    monkeypatch.setattr(core, "process_survey", lambda *args: result)
    reject(req, "result_integrity")


def test_pure_boundary_and_false_acceptance(monkeypatch, capsys):
    req = request()
    original = deepcopy(req)
    reads = []
    real_read = Path.read_bytes

    def tracked(path):
        reads.append(path.resolve())
        return real_read(path)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("adapter spawned a process"))
    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: pytest.fail("adapter used network"))
    for method in ("write_text", "write_bytes", "mkdir", "unlink"):
        monkeypatch.setattr(Path, method, lambda *args, **kwargs: pytest.fail("adapter wrote files"))
    result = adapter.run_station_corrections(req)
    receipt = result["receipt"]
    assert set(reads) == {Path(adapter.__file__).resolve(), Path(core.__file__).resolve()}
    assert req == original and capsys.readouterr() == ("", "")
    assert receipt["acceptance"] == {
        "host_approved": False,
        "full_method_accepted": False,
        "field_source_verified": False,
    }
    assert receipt["input_dataset_sha256"] != req["dataset"]["metadata"]["source_sha256"]
    assert receipt["request_sha256"] == core.digest(req)
    assert receipt["correction_result_sha256"] == core.digest(result["correction_result"])
    assert receipt["output_dataset_sha256"] == core.digest(result["correction_result"]["dataset"])
    assert receipt["submitted_config_sha256"] == core.digest(req["config"])
    assert receipt["normalized_config_sha256"] == core.digest(result["correction_result"]["processing"]["config"])
    assert receipt["normalized_config_sha256"] != receipt["submitted_config_sha256"]
    assert receipt["adapter_module_sha256"] == sha256(real_read(Path(adapter.__file__))).hexdigest()
    assert receipt["core_module_sha256"] == adapter.CORE_SHA256
    assert receipt["engines"] == core.PINS and receipt["python_implementation"] == "CPython"
    assert adapter.run_station_corrections(req) == result
    # Shared noncyclic native aliases remain valid, within counted bounds.
    data = survey(2)
    data["metadata"]["instrument_processing"]["tide"] = data["metadata"]["instrument_processing"]["drift"]
    data["stations"][1]["station_id"] = data["stations"][0]["station_id"] + "-other"
    assert adapter.run_station_corrections(request(data))["receipt"]["acceptance"]["host_approved"] is False


def test_lazy_import_and_system_exit_are_not_relabelled(monkeypatch):
    code = "import sys; import gravity_station_adapter; assert 'gravity_processing' not in sys.modules"
    fresh = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT / "data-pipeline", capture_output=True, text=True, timeout=20
    )
    assert fresh.returncode == 0, fresh.stderr

    def stopped(*args):
        raise KeyboardInterrupt()

    monkeypatch.setattr(core, "process_survey", stopped)
    with pytest.raises(KeyboardInterrupt):
        adapter.run_station_corrections(request())


def test_fresh_lazy_core_real_worked_control():
    worked = json.loads(
        (ROOT / "docs/methods/gravity-processing/examples/station-control.json").read_text(encoding="utf-8")
    )
    req = request(worked["dataset"], worked["config"])
    code = (
        "import json, sys; import gravity_station_adapter as a; "
        "assert 'gravity_processing' not in sys.modules; "
        "r = a.run_station_corrections(json.loads(sys.stdin.read())); "
        "assert 'gravity_processing' in sys.modules; "
        "print(json.dumps(r, sort_keys=True, allow_nan=False))"
    )
    child = subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(req),
        cwd=ROOT / "data-pipeline",
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert child.returncode == 0, child.stderr
    result = json.loads(child.stdout)
    assert result["correction_result"]["qc"]["derived_mgal"] == pytest.approx([12], abs=1e-8)
    assert result["correction_result"] == core.process_survey(worked["dataset"], worked["config"])
    assert result["receipt"]["request_sha256"] == core.digest(req)
    assert result["receipt"]["acceptance"] == {
        "host_approved": False,
        "full_method_accepted": False,
        "field_source_verified": False,
    }
