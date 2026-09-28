"""Independent, fail-closed admission QC for the measured AusLAMP C15 EDI.

This script never runs a layered inverse. It checks original numeric blocks
against mt_metadata, source-frame geometry and a necessary 1D tensor null.
The output is a local ignored scientific receipt, not a released model.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

import numpy as np

from sources import LEDGER, ROOT, SourceError, acquire_source

SOURCE_ID = "auslamp-nsw-c15"
WRMS_LIMIT = 3.0
PHASE_CONDITION_LIMIT = 1e8
COMPONENTS = ("XX", "XY", "YX", "YY")


class MTFieldQCError(ValueError):
    """The EDI cannot be screened without discarding or guessing evidence."""


def _sections(raw: bytes) -> tuple[dict, list]:
    if len(raw) > 10_000_000:
        raise MTFieldQCError("EDI exceeds the 10 MB sounding limit")
    try:
        lines = raw.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as error:
        raise MTFieldQCError("EDI is not UTF-8/ASCII") from error
    blocks, measures, current = {}, [], None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("!") or line.startswith(">!"):
            continue
        if "END" in blocks:
            raise MTFieldQCError("Content follows terminal END")
        if line.startswith(">"):
            match = re.fullmatch(r">\s*=?\s*([A-Za-z][A-Za-z0-9_.]*)(.*)", line)
            if not match:
                raise MTFieldQCError(f"Malformed block header: {line[:80]}")
            current = {"name": match[1].upper(), "header": match[2].strip(), "lines": []}
            if current["name"] in {"EMEAS", "HMEAS"}:
                measures.append(current)
            elif current["name"] in blocks:
                raise MTFieldQCError(f"Duplicate block {current['name']}")
            else:
                blocks[current["name"]] = current
        elif current is None:
            raise MTFieldQCError("Data outside EDI sections")
        else:
            content = line.split("!", 1)[0].strip()
            if content:
                current["lines"].append(content)
    if "HEAD" not in blocks or "END" not in blocks or blocks["END"]["lines"]:
        raise MTFieldQCError("Require HEAD and terminal END")
    return blocks, measures


def _line_value(block: dict, key: str) -> str:
    matches = [
        m[1].strip().strip("\"'")
        for line in block["lines"]
        if (m := re.fullmatch(rf"{re.escape(key)}\s*=\s*(.*?)\s*", line, re.I))
    ]
    if len(matches) != 1 or not matches[0]:
        raise MTFieldQCError(f"Require one {key} in {block['name']}")
    return matches[0]


def _attributes(header: str) -> dict[str, str]:
    before_count = header.split("//", 1)[0]
    attrs = {}
    for match in re.finditer(r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*(\"[^\"]*\"|[^\s]+)", before_count):
        key = match[1].upper()
        if key in attrs:
            raise MTFieldQCError(f"Duplicate header attribute {key}")
        attrs[key] = match[2].strip('"')
    return attrs


def _numeric(block: dict, count: int, empty: float, *, missing_ok: bool = False):
    declaration = re.search(r"//\s*(\d+)\s*$", block["header"])
    if declaration is None or int(declaration[1]) != count:
        raise MTFieldQCError(f"{block['name']} count declaration disagrees with NFREQ")
    try:
        values = np.asarray(" ".join(block["lines"]).split(), dtype=float)
    except ValueError as error:
        raise MTFieldQCError(f"{block['name']} contains a nonnumeric token") from error
    if len(values) != count or not np.isfinite(values).all():
        raise MTFieldQCError(f"{block['name']} has wrong length or nonfinite values")
    missing = np.abs(values) == abs(empty)
    if (missing.any() and not missing_ok) or np.any((np.abs(values) >= 1e30) & ~missing):
        raise MTFieldQCError(f"{block['name']} has missing or overflow values")
    return values, missing


def _layout(blocks: dict, measures: list) -> dict:
    fields = {key: _line_value(blocks["MTSECT"], key) for key in ("EX", "EY", "HX", "HY")}
    remote = [
        key
        for key in ("RX", "RY")
        if any(re.fullmatch(rf"{key}\s*=\s*.*", line, re.I) for line in blocks["MTSECT"]["lines"])
    ]
    if len(remote) == 1:
        raise MTFieldQCError("Remote-reference RX and RY must be declared together")
    if remote:
        fields.update({key: _line_value(blocks["MTSECT"], key) for key in remote})
    entries = {}
    for measure in measures:
        attrs = _attributes(measure["header"])
        identifier = attrs.get("ID")
        if not identifier or identifier in entries:
            raise MTFieldQCError("Measurement IDs must be present and unique")
        entries[identifier] = (measure["name"], attrs)

    def direction(channel: str) -> tuple[float, float | None]:
        try:
            kind, attrs = entries[fields[channel]]
            if attrs["CHTYPE"].upper() != ("HX" if channel == "RX" else "HY" if channel == "RY" else channel):
                raise MTFieldQCError(f"{channel} measurement type disagrees with MTSECT")
            if channel in ("EX", "EY"):
                if kind != "EMEAS":
                    raise MTFieldQCError(f"{channel} must be an electric dipole")
                dx = float(attrs["X2"]) - float(attrs["X"])
                dy = float(attrs["Y2"]) - float(attrs["Y"])
                length = float(np.hypot(dx, dy))
                if not np.isfinite(length) or length <= 0:
                    raise MTFieldQCError(f"{channel} dipole length is invalid")
                return float(np.degrees(np.arctan2(dy, dx))), length
            if kind != "HMEAS":
                raise MTFieldQCError(f"{channel} must be magnetic")
            return float(attrs["AZM"]), None
        except (KeyError, ValueError) as error:
            raise MTFieldQCError(f"{channel} lacks explicit orientation or geometry") from error

    angles = {channel: direction(channel) for channel in fields}
    if any(not np.isfinite(angle) for angle, _ in angles.values()):
        raise MTFieldQCError("Nonfinite channel azimuth")

    def aligned(a: str, b: str, offset: float = 0) -> bool:
        return abs((angles[a][0] - angles[b][0] - offset + 180) % 360 - 180) < 1e-5

    if not (aligned("EX", "HX") and aligned("EY", "HY") and aligned("EY", "EX", 90) and aligned("HY", "HX", 90)):
        raise MTFieldQCError("Electric, magnetic and remote-reference axes are not aligned orthogonal pairs")
    if remote and not (aligned("RX", "HX") and aligned("RY", "HY")):
        raise MTFieldQCError("Remote-reference axes disagree with local magnetic axes")
    return {name: {"azimuth_deg": angle, "dipole_length_m": length} for name, (angle, length) in angles.items()}


def _raw_tensor(blocks: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    try:
        count = int(_line_value(blocks["MTSECT"], "NFREQ"))
        empty = float(_line_value(blocks["HEAD"], "EMPTY"))
    except ValueError as error:
        raise MTFieldQCError("Invalid NFREQ or EMPTY") from error
    if not 4 <= count <= 512 or not np.isfinite(empty) or empty == 0:
        raise MTFieldQCError("Unsupported frequency count or sentinel")
    if _line_value(blocks["HEAD"], "DATAID") != _line_value(blocks["MTSECT"], "SECTID"):
        raise MTFieldQCError("DATAID and SECTID disagree")
    frequency, _ = _numeric(blocks["FREQ"], count, empty)
    if np.any(frequency <= 0) or len(np.unique(frequency)) != count:
        raise MTFieldQCError("Frequency must be finite, positive and unique")
    angle, _ = _numeric(blocks["ZROT"], count, empty)
    if not np.allclose(angle, 0, atol=1e-12, rtol=0):
        raise MTFieldQCError("This candidate requires declared zero ZROT; no covariance-free rerotation")
    tensor = np.zeros((count, 2, 2), dtype=complex)
    variance = np.zeros((count, 2, 2), dtype=float)
    for component in COMPONENTS:
        i, j = ("XY".index(component[0]), "XY".index(component[1]))
        values = []
        for suffix in ("R", "I", ".VAR"):
            block = blocks[f"Z{component}{suffix}"]
            if _attributes(block["header"]) != {"ROT": "ZROT"}:
                raise MTFieldQCError(f"{block['name']} must refer to common ZROT")
            value, _ = _numeric(block, count, empty)
            values.append(value)
        real, imag, var = values
        if np.any(var <= 0):
            raise MTFieldQCError(f"Z{component}.VAR must be strictly positive")
        tensor[:, i, j] = real + 1j * imag
        variance[:, i, j] = var
    tipper = {"present": False}
    tipper_names = {name for name in blocks if name.startswith(("TX", "TY", "TROT"))}
    if tipper_names and "TROT.EXP" not in tipper_names:
        raise MTFieldQCError("Incomplete ancillary tipper blocks")
    if "TROT.EXP" in blocks:
        trot, _ = _numeric(blocks["TROT.EXP"], count, empty)
        if not np.allclose(trot, 0, atol=1e-12, rtol=0):
            raise MTFieldQCError("Tipper rotation differs from the zero impedance frame")
        masks, components = [], []
        for axis in ("X", "Y"):
            values = []
            for suffix in ("R.EXP", "I.EXP", "VAR.EXP"):
                block = blocks[f"T{axis}{suffix}"]
                if _attributes(block["header"]) != {"ROT": "TROT"}:
                    raise MTFieldQCError(f"{block['name']} tipper rotation reference is inconsistent")
                value, missing = _numeric(block, count, empty, missing_ok=True)
                values.append(value)
                masks.append(missing)
            if np.any(values[2][~masks[-1]] <= 0):
                raise MTFieldQCError(f"T{axis} tipper variance must be positive where present")
            components.append(values[0] + 1j * values[1])
        if any(not np.array_equal(masks[0], mask) for mask in masks[1:]):
            raise MTFieldQCError("Tipper missing masks disagree")
        valid = ~masks[0]
        magnitude = np.sqrt(np.abs(components[0][valid]) ** 2 + np.abs(components[1][valid]) ** 2)
        tipper = {
            "present": True,
            "valid_periods": int(valid.sum()),
            "missing_periods": int((~valid).sum()),
            "median_vector_magnitude": float(np.median(magnitude)) if len(magnitude) else None,
        }
    return frequency, tensor, variance, angle, tipper


def tensor_gate(tensor: np.ndarray, variance: np.ndarray) -> dict:
    """Necessary 1D complex-tensor null with deliberately generous SDs."""
    z = np.asarray(tensor, dtype=complex)
    v = np.asarray(variance, dtype=float)
    if z.ndim != 3 or z.shape[1:] != (2, 2) or v.shape != z.shape or not len(z):
        raise MTFieldQCError("Require a nonempty 2x2 impedance and variance per frequency")
    if not np.isfinite(z).all() or not np.isfinite(v).all() or np.any(v <= 0):
        raise MTFieldQCError("Tensor and variances must be finite with positive variance")
    if np.any(np.linalg.norm(z, axis=(1, 2)) == 0):
        raise MTFieldQCError("Zero impedance tensor cannot support a dimensionality screen")
    sigma = np.sqrt(v)
    per_period = {
        "xx": np.abs(z[:, 0, 0]) / (np.sqrt(2) * sigma[:, 0, 0]),
        "yy": np.abs(z[:, 1, 1]) / (np.sqrt(2) * sigma[:, 1, 1]),
        "antisymmetry": np.abs(z[:, 0, 1] + z[:, 1, 0]) / (np.sqrt(2) * (sigma[:, 0, 1] + sigma[:, 1, 0])),
    }
    wrms = {key: float(np.sqrt(np.mean(score**2))) for key, score in per_period.items()}
    j = np.array([[0, 1], [-1, 0]])
    amplitude = (z[:, 0, 1] - z[:, 1, 0]) / 2
    departure = np.linalg.norm(z - amplitude[:, None, None] * j, axis=(1, 2)) / np.linalg.norm(z, axis=(1, 2))
    quarter_turn = np.array([[0.0, -1.0], [1.0, 0.0]])
    turned = quarter_turn @ z @ quarter_turn.T
    turned_amplitude = (turned[:, 0, 1] - turned[:, 1, 0]) / 2
    turned_departure = np.linalg.norm(turned - turned_amplitude[:, None, None] * j, axis=(1, 2)) / np.linalg.norm(
        turned, axis=(1, 2)
    )
    rotation_error = float(np.max(np.abs(departure - turned_departure)))
    if rotation_error > 1e-12:
        raise MTFieldQCError("1D tensor-distance rotation invariant check failed")
    return {
        "threshold": WRMS_LIMIT,
        "passes": all(value <= WRMS_LIMIT for value in wrms.values()),
        "wrms": wrms,
        "per_period_normalized": {k: v.tolist() for k, v in per_period.items()},
        "median_relative_distance_to_1d": float(np.median(departure)),
        "relative_distance_to_1d": departure.tolist(),
        "quarter_turn_invariance_max_abs_error": rotation_error,
        "sigma_policy": "sqrt(original Z.VAR) per real/imaginary component; generous if Z.VAR is complex variance",
        "antisymmetry_sigma_policy": "sum of two marginal SDs; no cross-component covariance inferred",
        "all_supplied_periods_used": True,
    }


def phase_tensor_diagnostic(tensor: np.ndarray) -> dict:
    """Rotation-invariant scalar-departure diagnostic, not a geology verdict."""
    z = np.asarray(tensor, dtype=complex)
    rows, skipped = [], []
    for i, item in enumerate(z):
        condition = float(np.linalg.cond(item.real))
        if not np.isfinite(condition) or condition > PHASE_CONDITION_LIMIT:
            skipped.append(i)
            continue
        phi = np.linalg.solve(item.real, item.imag)
        scale = float(np.linalg.norm(phi))
        if scale == 0 or not np.isfinite(scale):
            skipped.append(i)
            continue
        scalar = np.trace(phi) / 2
        departure = float(np.linalg.norm(phi - scalar * np.eye(2)) / scale)
        beta = float(np.degrees(np.arctan2(phi[0, 1] - phi[1, 0], np.trace(phi))) / 2)
        rows.append((i, departure, beta, condition))
    if len(rows) < len(z) / 2:
        raise MTFieldQCError("Fewer than half of phase tensors are numerically usable")
    return {
        "definition": "Phi = Re(Z)^(-1) Im(Z); scalar departure = ||Phi-tr(Phi)I/2||F / ||Phi||F",
        "usable_periods": len(rows),
        "skipped_indices": skipped,
        "condition_limit": PHASE_CONDITION_LIMIT,
        "median_scalar_departure": float(np.median([row[1] for row in rows])),
        "p90_scalar_departure": float(np.percentile([row[1] for row in rows], 90)),
        "median_abs_skew_beta_deg": float(np.median([abs(row[2]) for row in rows])),
        "per_period": [
            {"source_index": i, "scalar_departure": d, "skew_beta_deg": b, "real_tensor_condition": c}
            for i, d, b, c in rows
        ],
        "caveat": "Indicative phase-tensor dimensionality only; static distortion, missing covariance and structure remain.",
    }


def inspect_edi(path: Path) -> dict:
    """Inspect original bytes; the result contains no physical-unit assumption."""
    path = Path(path)
    raw = path.read_bytes()
    blocks, measures = _sections(raw)
    try:
        layout = _layout(blocks, measures)
        frequency, tensor, variance, angle, tipper = _raw_tensor(blocks)
    except KeyError as error:
        raise MTFieldQCError(f"Required source block is missing: {error}") from error
    try:
        from mt_metadata.transfer_functions.io.edi import EDI

        parsed = EDI(fn=path)
        official_order = np.argsort(np.asarray(parsed.frequency))
        source_order = np.argsort(frequency)
        np.testing.assert_allclose(np.asarray(parsed.frequency)[official_order], frequency[source_order], rtol=1e-12)
        np.testing.assert_allclose(np.asarray(parsed.z)[official_order], tensor[source_order], rtol=1e-12, atol=1e-15)
        np.testing.assert_allclose(
            np.asarray(parsed.z_err)[official_order] ** 2, variance[source_order], rtol=1e-12, atol=1e-25
        )
    except (AssertionError, ValueError, OSError, ImportError) as error:
        raise MTFieldQCError(f"Official parser disagrees with original EDI blocks: {error}") from error
    gate = tensor_gate(tensor, variance)
    phase = phase_tensor_diagnostic(tensor)
    return {
        "source_bytes": len(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "id": _line_value(blocks["HEAD"], "DATAID"),
        "frequency_count": len(frequency),
        "frequency_min_hz": float(np.min(frequency)),
        "frequency_max_hz": float(np.max(frequency)),
        "original_frequency_hz": frequency.tolist(),
        "parser_agreement": "all original FREQ, Z real/imag and Z.VAR values agree with mt_metadata",
        "parser_version": importlib.metadata.version("mt-metadata"),
        "rotation": {
            "zrot_unique_deg": np.unique(angle).tolist(),
            "action": "preserved; no rerotation",
            "channel_layout": layout,
        },
        "variance": {
            "all_positive": True,
            "min_native": float(np.min(variance)),
            "max_native": float(np.max(variance)),
            "original_convention": "not stated in source EDI; QC uses generous SD bound",
        },
        "tensor_1d": gate,
        "phase_tensor": phase,
        "tipper": tipper,
        "unresolved_for_absolute_inverse": [
            "impedance_units_not_declared_by_edi",
            "time_sign_convention_not_declared_by_edi",
            "variance_convention_not_declared_by_edi",
        ],
    }


def _provider_screen(record: dict, root: Path, raw_sha256: str, frequency_count: int) -> dict:
    """Verify ignored snapshots before attributing the upstream screening label."""
    rows = {}
    for name, filename, digest_key in (
        ("station", "auslamp-nsw-c15-station.json", "station_record_sha256"),
        ("dimensionality", "auslamp-nsw-c15-dimensionality.json", "dimensionality_record_sha256"),
    ):
        path = root / "data/raw/mt" / filename
        try:
            original = path.read_bytes()
            if hashlib.sha256(original).hexdigest() != record[digest_key]:
                raise MTFieldQCError(f"Pinned provider {name} snapshot hash differs: {path}")
            rows[name] = json.loads(original)
        except (OSError, json.JSONDecodeError) as error:
            raise MTFieldQCError(f"Missing or invalid pinned provider {name} snapshot: {path}") from error
    station, dimension = rows["station"], rows["dimensionality"]
    if (
        station.get("ausmt_id") != "au.auslamp-nsw-2016-21.C15"
        or station.get("provenance", {}).get("input_sha256") != raw_sha256
        or station.get("distribution", {}).get("license") != "CC-BY-4.0"
        or station.get("data", {}).get("n_periods") != frequency_count
        or dimension.get("classification") != "1-D"
        or not dimension.get("screening_diagnostic")
    ):
        raise MTFieldQCError("Provider snapshots disagree with pinned C15 identity, rights or screening class")
    return {
        "classification": dimension["classification"],
        "kind": "attributed phase-tensor screening diagnostic",
        "skew_beta_median_deg": dimension.get("skew_beta_median_deg"),
        "pct_periods_3d": dimension.get("pct_periods_3d"),
        "url": record["dimensionality_record"],
        "station_record_sha256": record["station_record_sha256"],
        "dimensionality_record_sha256": record["dimensionality_record_sha256"],
        "not_an_inverse_admission": True,
    }


def run(*, local_file: Path | None = None, root: Path = ROOT, ledger_path: Path = LEDGER) -> dict:
    record, path, acquisition = acquire_source(SOURCE_ID, local_file=local_file, root=root, ledger_path=ledger_path)
    inspected = inspect_edi(path)
    if inspected["id"] != "C15" or inspected["source_sha256"] != record["sha256"]:
        raise MTFieldQCError("C15 identity differs from pinned ledger")
    upstream = _provider_screen(record, Path(root), inspected["source_sha256"], inspected["frequency_count"])
    reasons = []
    if not inspected["tensor_1d"]["passes"]:
        reasons.append("complex_tensor_inconsistent_with_isotropic_1d_at_declared_variance")
    reasons.extend(inspected["unresolved_for_absolute_inverse"])
    result = {
        "schema": "inverse-earth/m06-field-admission/v1",
        "source_id": SOURCE_ID,
        "source_url": record["object_url"],
        "source_sha256": inspected["source_sha256"],
        "source_bytes": inspected["source_bytes"],
        "rights_decision": record["rights_decision"],
        "citation": record["citation"],
        "raw_receipt": acquisition,
        "source_kind": "measured EDI transfer function, not raw time series",
        "provider_screen": upstream,
        "qc": inspected,
        "status": "ineligible" if reasons else "unresolved",
        "one_d_inversion_eligible": False,
        "reason_codes": reasons if reasons else ["requires_separate_inverse_review"],
        "inversion_performed": False,
        "methods": {},
        "predicted": None,
        "heldout_metrics": None,
        "truth": None,
        "interpretation": "No layered field inverse or geological truth claim",
    }
    target = Path(root) / "data/raw/mt/auslamp-nsw-c15-m06-admission.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    target.write_text(payload, encoding="utf-8", newline="\n")
    target.with_suffix(target.suffix + ".sha256").write_text(
        hashlib.sha256(payload.encode("utf-8")).hexdigest() + "  " + target.name + "\n", encoding="ascii", newline="\n"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Exact locally downloaded C15 EDI for pinned manual import")
    args = parser.parse_args()
    try:
        result = run(local_file=args.file)
    except (MTFieldQCError, SourceError, OSError) as error:
        parser.exit(2, f"M06 field admission rejected: {error}\n")
    print(
        json.dumps(
            {
                "source_id": result["source_id"],
                "source_sha256": result["source_sha256"],
                "frequency_count": result["qc"]["frequency_count"],
                "tensor_wrms": result["qc"]["tensor_1d"]["wrms"],
                "status": result["status"],
                "inversion_performed": result["inversion_performed"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
