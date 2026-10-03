"""Strict re-import of private EDI QC and layered-inverse bundles."""

from __future__ import annotations

import io
import math
import sys
import zipfile
from pathlib import Path

from app.mt_contract import M05_ID, M06_ID, M05Parameters, M06Parameters
from app.processing_contract import canonical_bytes, sha256


UNITS = {"frequency": "Hz", "impedance": "ohm E/H", "resistivity": "ohm m",
         "thickness": "m", "uncertainty": "ohm SD per real/imaginary component"}


def build_mt_bundle(dataset: dict, result: dict, dataset_sha: str, result_sha: str) -> bytes:
    from app.bundle import verify_bundle

    data = canonical_bytes(dataset)
    solved = canonical_bytes(result)
    if sha256(data) != dataset_sha or sha256(solved) != result_sha:
        raise ValueError("MT bundle inputs disagree with stored receipts")
    manifest = {
        "schema": "geophysics.processing-bundle/v1", "dataset_id": dataset["dataset_id"],
        "job_id": result["job_id"], "method_id": result["method_id"],
        "parameters": result["parameters"], "source": dataset["source"],
        "environment": result["environment"],
        "axes": ["frequency"], "dimensions": result["dimensions"], "units": UNITS,
        "provenance": {"raw_sha256": dataset["parent_raw_sha256"],
                       "raw_bytes": dataset["parent_raw_bytes"],
                       "dataset_sha256": dataset_sha, "request_sha256": result["request_sha256"],
                       "engine_sha256": result["engine_sha256"],
                       "parser_sha256": result["parser_sha256"],
                       "forward_sha256": result["forward_sha256"]},
        "members": {"dataset.json": {"sha256": dataset_sha, "bytes": len(data)},
                    "result.json": {"sha256": result_sha, "bytes": len(solved)}},
        "raw_bytes_included": False,
    }
    manifest["provenance"]["environment_sha256"] = result["environment_sha256"]
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", canonical_bytes(manifest))
        archive.writestr("dataset.json", data)
        archive.writestr("result.json", solved)
    encoded = output.getvalue()
    verify_bundle(encoded)
    return encoded


def _finite(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _close(a, b, tolerance=1e-9) -> bool:
    return _finite(a) and _finite(b) and math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance * 1e-12)


def verify_mt_contents(manifest: dict, dataset: dict, result: dict, dataset_sha: str) -> None:
    frequency = result.get("frequency_hz")
    screen = result.get("screen")
    source = dataset.get("source")
    physical = dataset.get("physical_metadata")
    dimensions = dataset.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("MT dataset dimensions are missing")
    provenance = screen.get("provenance", {}) if isinstance(screen, dict) else {}
    if not isinstance(provenance, dict):
        raise ValueError("MT source provenance is missing")
    count = dimensions.get("frequency")
    if (type(count) is not int or not 2 <= count <= 512
            or not isinstance(source, dict) or not isinstance(physical, dict)
            or result.get("method_id") not in (M05_ID, M06_ID)
            or result.get("schema") != "geophysics.processing-result/v1"
            or result.get("dataset_id") != dataset.get("dataset_id")
            or result.get("dataset_sha256") != dataset_sha
            or result.get("raw_asset_id") != dataset.get("raw_asset_id")
            or result.get("raw_sha256") != dataset.get("parent_raw_sha256")
            or result.get("raw_bytes") != dataset.get("parent_raw_bytes")
            or result.get("truth") is not None
            or result.get("source") != source or result.get("physical_metadata") != physical
            or result.get("axis_order") != ["frequency"]
            or result.get("dimensions") != {"frequency": count}
            or dataset.get("axis_order") != ["frequency"]
            or not isinstance(frequency, list) or len(frequency) != count
            or not all(_finite(value) and value > 0 for value in frequency)
            or frequency != sorted(set(frequency))
            or not isinstance(screen, dict) or screen.get("schema") != "inverse-earth/edi-screen/v1"
            or screen.get("frequencies_hz") != frequency
            or screen.get("truth") is not None or screen.get("methods") != {}
            or screen.get("inversion_performed") is not False
            or provenance.get("source_sha256") != dataset.get("parent_raw_sha256")
            or provenance.get("source_bytes") != dataset.get("parent_raw_bytes")
            or manifest.get("dataset_id") != dataset.get("dataset_id")
            or manifest.get("job_id") != result.get("job_id")
            or manifest.get("method_id") != result.get("method_id")
            or manifest.get("parameters") != result.get("parameters")
            or manifest.get("source") != source
            or not isinstance(result.get("environment"), dict)
            or manifest.get("environment") != result["environment"]
            or result.get("environment_sha256") != sha256(canonical_bytes(result["environment"]))
            or manifest.get("axes") != ["frequency"]
            or manifest.get("dimensions") != {"frequency": count}
            or manifest.get("units") != UNITS
            or manifest.get("provenance") != {
                "raw_sha256": dataset.get("parent_raw_sha256"),
                "raw_bytes": dataset.get("parent_raw_bytes"),
                "dataset_sha256": dataset_sha,
                "request_sha256": result.get("request_sha256"),
                "engine_sha256": result.get("engine_sha256"),
                "parser_sha256": result.get("parser_sha256"),
                "forward_sha256": result.get("forward_sha256"),
                "environment_sha256": result.get("environment_sha256"),
            }):
        raise ValueError("MT bundle identity, units or provenance mismatch")
    geometry = physical.get("geometry")
    if not isinstance(geometry, dict) or not isinstance(provenance, dict):
        raise ValueError("MT physical convention or provenance is missing")
    components = geometry.get("tensor_components")
    frame = physical.get("component_frame")
    if (not isinstance(components, list) or any(not isinstance(item, str) for item in components)
            or len(components) != len(set(components))
            or set(components) not in ({"Zxx", "Zxy", "Zyx", "Zyy"},
                                       {"Zxx", "Zxy", "Zyx", "Zyy", "Tx", "Ty"})
            or not isinstance(frame, str) or frame not in {"instrument axes", "geographic ENU"}
            or geometry.get("sign_convention") not in ("+", "-")
            or geometry.get("variance_convention") not in ("complex", "per-real-component")
            or (frame == "instrument axes" and geometry.get("rotation_reference") != "unspecified")
            or (frame == "geographic ENU" and geometry.get("rotation_reference") != "geographic-north")):
        raise ValueError("MT declared frame or tensor components are invalid")
    environment = result["environment"]
    packages = environment.get("packages")
    if (not isinstance(environment.get("python"), str) or not environment["python"]
            or not isinstance(packages, dict)
            or set(packages) != {"numpy", "scipy", "mt-metadata", "pandas", "matplotlib", "xarray"}
            or any(not isinstance(version, str) or not version for version in packages.values())):
        raise ValueError("MT runtime fingerprint is incomplete")
    measurement_unit = physical.get("measurement_unit")
    original_units = {"ohm": "ohm", "mV/km/nT": "mt"}.get(measurement_unit) if isinstance(measurement_unit, str) else None
    if (original_units is None or provenance.get("original_units") != original_units
            or provenance.get("output_units") != "ohm"
            or provenance.get("output_sign_convention") != "+"
            or provenance.get("original_sign_convention") != geometry.get("sign_convention")
            or provenance.get("variance_convention") != geometry.get("variance_convention")
            or screen.get("id") != geometry.get("station_id")
            or count != geometry.get("frequency_count")
            or provenance.get("tipper_present") is not
               (set(components) == {"Zxx", "Zxy", "Zyx", "Zyy", "Tx", "Ty"})
            or provenance.get("rotation_reference") !=
               ("geographic-north" if physical.get("component_frame") == "geographic ENU" else None)):
        raise ValueError("MT declared units, sign, variance, frame or tensor disagree with the screen")
    angles = provenance.get("original_rotation_deg")
    declared_angle = geometry.get("rotation_degrees")
    if (not isinstance(angles, list) or len(angles) != count or not _finite(declared_angle)
            or any(not _finite(angle) or abs((angle - declared_angle + 180) % 360 - 180) > 1e-7
                   for angle in angles)):
        raise ValueError("MT declared rotation disagrees with the screen")
    # Rebuild the necessary tensor screen from serialized observations, independently
    # of the screen's stored scores. This does not assign geological truth.
    tensor = screen.get("tensor")
    if not isinstance(tensor, dict):
        raise ValueError("MT tensor is missing")
    real, imaginary, sigma = (tensor.get(key) for key in ("real", "imag", "sigma"))
    if any(not isinstance(array, list) or len(array) != count for array in (real, imaginary, sigma)):
        raise ValueError("MT tensor shape mismatch")
    for matrix in (*real, *imaginary, *sigma):
        if (not isinstance(matrix, list) or len(matrix) != 2
                or any(not isinstance(row, list) or len(row) != 2 for row in matrix)
                or any(not _finite(value) for row in matrix for value in row)):
            raise ValueError("MT tensor component mismatch")
    if any(value <= 0 for matrix in sigma for row in matrix for value in row):
        raise ValueError("MT uncertainty must be positive")
    import numpy as np
    path = str(Path(__file__).resolve().parents[1] / "data-pipeline")
    if path not in sys.path:
        sys.path.insert(0, path)
    from electromagnetics import MU, impedance

    z = np.asarray(real) + 1j * np.asarray(imaginary)
    s = np.asarray(sigma)
    f = np.asarray(frequency)
    scores = {
        "xx_component_wrms": float(np.sqrt(np.mean(abs(z[:, 0, 0] / s[:, 0, 0]) ** 2) / 2)),
        "yy_component_wrms": float(np.sqrt(np.mean(abs(z[:, 1, 1] / s[:, 1, 1]) ** 2) / 2)),
        "antisymmetry_conservative_wrms": float(np.sqrt(np.mean(abs(
            (z[:, 0, 1] + z[:, 1, 0]) / (s[:, 0, 1] + s[:, 1, 0])) ** 2) / 2)),
    }
    compatibility = screen.get("compatibility", {})
    if not isinstance(compatibility, dict) or not isinstance(screen.get("observed"), dict):
        raise ValueError("MT compatibility or observed curves are missing")
    if (any(not _close(value, compatibility.get(key)) for key, value in scores.items())
            or compatibility.get("passes_screen") is not all(value <= 3 for value in scores.values())
            or screen.get("one_d_inversion_eligible") is not compatibility["passes_screen"]):
        raise ValueError("MT full-tensor screen mismatch")
    for label, sign, i, j in (("xy", 1, 0, 1), ("yx", -1, 1, 0)):
        curve = screen.get("observed", {}).get(label, {})
        if not isinstance(curve, dict):
            raise ValueError("MT observed curve is missing")
        observed = sign * z[:, i, j]
        apparent = abs(observed) ** 2 / (MU * 2 * np.pi * f)
        phase = np.angle(observed, deg=True)
        for key, expected in (("real", observed.real), ("imag", observed.imag),
                              ("apparent", apparent), ("phase", phase),
                              ("sigma_real_imag_ohm", s[:, i, j])):
            values = curve.get(key)
            if not isinstance(values, list) or len(values) != count or any(
                not _close(a, float(b)) for a, b in zip(values, expected)
            ):
                raise ValueError("MT observed curve differs from tensor")
    inverse = result.get("inverse")
    if result["method_id"] == M05_ID:
        M05Parameters.model_validate(result.get("parameters"))
        if inverse is not None or result.get("qc_screen_sha256") is not None:
            raise ValueError("M05 bundle must remain QC-only")
        return
    if not screen["one_d_inversion_eligible"] or not 12 <= count <= 64:
        raise ValueError("M06 bundle contains an ineligible full tensor")
    M06Parameters.model_validate(result.get("parameters"))
    if (not isinstance(inverse, dict) or inverse.get("schema") != "inverse-earth/edi-1d/v1"
            or inverse.get("truth") is not None or inverse.get("clean") is not None
            or inverse.get("frequencies") != frequency or inverse.get("compatibility") != compatibility
            or inverse.get("provenance") != provenance
            or inverse.get("tensor") != screen.get("tensor")
            or inverse.get("metadata") != screen.get("metadata")
            or inverse.get("observed") != {key: value for key, value in screen["observed"]["xy"].items()
                                               if key != "sigma_real_imag_ohm"}
            or inverse.get("sigma") != screen["observed"]["xy"]["sigma_real_imag_ohm"]
            or inverse.get("units") != "ohm m" or inverse.get("data_units") != "ohm"
            or inverse.get("geometry") != "operator-supplied fixed-thickness 1D model"
            or result.get("qc_screen_sha256") != sha256(canonical_bytes(screen))):
        raise ValueError("M06 bundle inverse identity mismatch")
    params = result["parameters"]
    h = params.get("thickness_m")
    model = inverse.get("methods", {}).get("mt-lm", {}).get("model")
    active = [i % 5 != 4 for i in range(count)]
    if (inverse.get("thickness") != h or inverse.get("active") != active
            or inverse.get("parameters", {}).get("regularization") != params.get("beta")
            or not isinstance(model, list) or len(model) != len(h) + 1
            or any(not _finite(value) or not 1 <= value <= 6000 for value in model)):
        raise ValueError("M06 bundle parameters or model mismatch")
    predicted = impedance(model, h, f)
    observed = z[:, 0, 1]
    method = inverse["methods"]["mt-lm"]
    for label, expected in (("predicted", predicted), ("residual", observed - predicted)):
        curve = method.get(label, {})
        for key, values in (("real", expected.real), ("imag", expected.imag)):
            if (not isinstance(curve.get(key), list) or len(curve[key]) != count
                    or any(not _close(a, float(b), 1e-7) for a, b in zip(curve[key], values))):
                raise ValueError("M06 predicted or residual array mismatch")
    if (not isinstance(method.get("uncertainty"), dict)
            or method["uncertainty"].get("status") != "computed"
            or method["uncertainty"].get("fixed_thickness_m") != h
            or method["uncertainty"].get("requested") != params.get("bootstrap_samples")):
        raise ValueError("M06 conditional uncertainty is incomplete")
    uncertainty = method["uncertainty"]
    samples = uncertainty.get("samples")
    if (not isinstance(samples, list) or len(samples) != params["bootstrap_samples"]
            or any(not isinstance(member, list) or len(member) != len(model)
                   or any(not _finite(value) or not 1 <= value <= 6000 for value in member)
                   for member in samples)
            or uncertainty.get("active") != active
            or uncertainty.get("conditioning_model") != model
            or uncertainty.get("sigma_per_real_component") != inverse["sigma"]
            or uncertainty.get("beta") != params["beta"]
            or uncertainty.get("units") != "ohm m" or uncertainty.get("failures") != []
            or uncertainty.get("completed") != len(samples)):
        raise ValueError("M06 conditional ensemble differs from its declared conditioning")
    quantiles = uncertainty.get("quantiles")
    confidence = uncertainty.get("confidence")
    if (not isinstance(quantiles, list) or len(quantiles) != 2
            or any(not _finite(value) or not 0 < value < 1 for value in quantiles)
            or not _finite(confidence) or not 0 < confidence < 1
            or not _close(quantiles[0], (1 - confidence) / 2)
            or not _close(quantiles[1], (1 + confidence) / 2)):
        raise ValueError("M06 conditional ensemble quantiles are invalid")
    intervals = np.quantile(samples, quantiles, axis=0)
    for key, expected in (("lower", intervals[0]), ("upper", intervals[1]),
                          ("mean", np.mean(samples, axis=0)), ("std", np.std(samples, axis=0, ddof=1))):
        values = uncertainty.get(key)
        if (not isinstance(values, list) or len(values) != len(model)
                or any(not _close(a, float(b), 1e-7) for a, b in zip(values, expected))):
            raise ValueError("M06 conditional interval summary differs from ensemble")
