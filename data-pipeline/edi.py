"""Strict, provenance-preserving EDI transfer functions -> CPU isotropic 1D MT.

mt_metadata performs the official EDI read AFTER a strict raw-block preflight.
The preflight prevents its permissive replacement of bad/missing numbers by zero.
Only complete impedance tensors with explicit conventions are accepted. See
docs/problem-types/mt-recovery.md for supported inputs and rejected ambiguities.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

import numpy as np

from electromagnetics import MU, MT_BOUNDS, bootstrap_mt, calibrate_mt_bootstrap, curves, impedance, invert_mt

COMPONENTS = ("xx", "xy", "yx", "yy")
MT_TO_OHM = MU*1000  # (mV/km)/nT = 1000 (V/m)/T; H = B/mu0.
PARSER_PIN = "mt-metadata==1.0.10"


class EDIError(ValueError):
    """An EDI cannot be interpreted safely by this deliberately bounded workflow."""


@dataclass
class EDISounding:
    frequencies: np.ndarray
    tensor: np.ndarray                  # canonical E/H ohm, positive-time convention
    sigma: np.ndarray                   # SD of each real/imag part, in ohm
    rotation_deg: np.ndarray            # clockwise from geographic North
    provenance: dict
    metadata: dict
    compatibility: dict

    def select(self, component="xy"):
        if component not in ("xy", "yx"):
            raise EDIError("Isotropic 1D inversion supports xy or sign-corrected yx, never a diagonal component")
        i, j = (0, 1) if component == "xy" else (1, 0)
        sign = 1 if component == "xy" else -1
        return self.tensor[:, i, j]*sign, self.sigma[:, i, j]


def _assignments(text):
    pattern = r'([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*("[^"]*"|\'[^\']*\'|[^\s]+)'
    result = {}
    for match in re.finditer(pattern, text):
        key, value = match.group(1).upper(), match.group(2).strip("\"'")
        if key in result:
            raise EDIError(f"Duplicate metadata key {key}")
        result[key] = value
    return result


def _sections(text):
    entries, current = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith((">!", "!")):
            continue
        if line.startswith(">"):
            match = re.match(r"^>\s*=?\s*([A-Za-z][A-Za-z0-9_.]*)\b(.*)$", line)
            if not match:
                raise EDIError(f"Invalid EDI block header: {line[:80]}")
            current = dict(name=match[1].upper(), header=match[2].strip(), lines=[])
            entries.append(current)
        elif current is None:
            raise EDIError("Content appears before >HEAD")
        else:
            current["lines"].append(line.split("!")[0].strip())
    if not entries or entries[0]["name"] != "HEAD" or entries[-1]["name"] != "END":
        raise EDIError("Require >HEAD first and >END last")
    if entries[-1]["lines"] or entries[-1]["header"]:
        raise EDIError("Content after >END is unsupported")
    singleton = {}
    repeated = []
    for entry in entries:
        if entry["name"] in ("HMEAS", "EMEAS"):
            repeated.append(entry)
        elif entry["name"] in singleton:
            raise EDIError(f"Duplicate block {entry['name']}")
        else:
            singleton[entry["name"]] = entry
    return singleton, repeated


def _numeric(entry, count, empty):
    declaration = re.search(r"//\s*(\d+)\s*$", entry["header"])
    if not declaration or int(declaration[1]) != count:
        raise EDIError(f"{entry['name']} must declare exactly // {count} entries")
    try:
        values = np.asarray(" ".join(entry["lines"]).split(), dtype=float)
    except ValueError as error:
        raise EDIError(f"Invalid numeric token in {entry['name']}") from error
    if len(values) != count or not np.isfinite(values).all():
        raise EDIError(f"Wrong length or nonfinite values in {entry['name']}")
    if np.any(abs(values) == abs(empty)) or np.any(abs(values) >= 1e30):
        raise EDIError(f"Missing-value sentinel in {entry['name']}; no silent zero replacement")
    return values


def _normalize_units(value):
    normalized = value.lower().replace(" ", "")
    if normalized in ("mt", "(mv/km)/nt", "mv/km/nt", "millivolts_per_kilometer_per_nanotesla"):
        return "mt"
    if normalized in ("ohm", "ohms", "v/m/(a/m)"):
        return "ohm"
    raise EDIError(f"Unsupported or ambiguous impedance units {value!r}")


def _normalize_sign(value):
    normalized = value.lower().replace(" ", "")
    if normalized in ("+", "exp(+iwt)", "exp(+iomegat)"):
        return "+"
    if normalized in ("-", "exp(-iwt)", "exp(-iomegat)"):
        return "-"
    raise EDIError(f"Unsupported time/sign convention {value!r}")


def _normalize_variance(value):
    normalized = value.lower().replace("_", "-")
    if normalized in ("complex", "complex-variance"):
        return "complex"
    if normalized in ("per-real-component", "real-component"):
        return "per-real-component"
    raise EDIError(f"Unsupported variance convention {value!r}")


def _resolve(values, supplied, name, normalize):
    values = [v for v in values if v is not None]
    if supplied is not None:
        values.append(supplied)
    if not values:
        raise EDIError(f"Missing explicit {name}; provide documented metadata or a provenance-recorded argument")
    canonical = [normalize(v) for v in values]
    if len(set(canonical)) != 1:
        raise EDIError(f"Conflicting {name} declarations")
    return canonical[0]


def _layout(measurements):
    channels = {}
    for entry in measurements:
        item = _assignments(entry["header"]+" "+" ".join(entry["lines"]))
        channel = item.get("CHTYPE", "").upper()
        if channel not in ("EX", "EY", "HX", "HY") or channel in channels:
            raise EDIError("Require exactly one EX, EY, HX, HY measurement; additional channels unsupported")
        try:
            if entry["name"] == "HMEAS":
                if channel not in ("HX", "HY"):
                    raise EDIError("Magnetic measurement has electric channel identifier")
                angle = float(item["AZM"])
            else:
                if channel not in ("EX", "EY"):
                    raise EDIError("Electric measurement has magnetic channel identifier")
                # EDI dipole x=north, y=east. Both endpoints specify polarity.
                dx = float(item["X2"])-float(item["X"])
                dy = float(item["Y2"])-float(item["Y"])
                if np.hypot(dx, dy) <= 0:
                    raise EDIError("Electric dipole length must be positive")
                angle = np.degrees(np.arctan2(dy, dx))
            if not np.isfinite(angle):
                raise EDIError("Nonfinite channel orientation")
            channels[channel] = dict(id=item["ID"], azimuth_deg=float(angle))
        except (KeyError, ValueError) as error:
            raise EDIError("Missing or malformed measurement orientation/identifier") from error
    if set(channels) != {"EX", "EY", "HX", "HY"}:
        raise EDIError("Four horizontal channel orientations must be documented")
    def close(a, b):
        return abs((a-b+180) % 360-180) < 1e-5
    if not (close(channels["HY"]["azimuth_deg"], channels["HX"]["azimuth_deg"]+90)
            and close(channels["EY"]["azimuth_deg"], channels["EX"]["azimuth_deg"]+90)
            and close(channels["EX"]["azimuth_deg"], channels["HX"]["azimuth_deg"])):
        raise EDIError("Nonorthogonal or unmatched electric/magnetic layout requires covariance-aware preprocessing")
    return channels


def _compatibility(tensor, sigma):
    # Conservative antisymmetry scale needs no cross-component covariance:
    # SD(X+Y) <= SD(X)+SD(Y). This is a screening test, not dimensionality proof.
    scores = {}
    for component, i in (("xx", 0), ("yy", 1)):
        r = tensor[:, i, i]/sigma[:, i, i]
        scores[component+"_component_wrms"] = float(np.sqrt(np.mean(abs(r)**2)/2))
    r = (tensor[:, 0, 1]+tensor[:, 1, 0])/(sigma[:, 0, 1]+sigma[:, 1, 0])
    scores["antisymmetry_conservative_wrms"] = float(np.sqrt(np.mean(abs(r)**2)/2))
    accepted = all(value <= 3 for value in scores.values())
    return dict(
        **scores, threshold=3., passes_screen=accepted,
        criteria="diagonal component WRMS <=3 and conservative antisymmetry WRMS <=3",
        caveat="Necessary 1D consistency screen only, not proof of isotropy; static shift and 2D/3D ambiguity remain.",
    )


def read_edi(path, *, units=None, sign_convention=None, variance_convention=None, rotation="preserve"):
    """Read full tensor strictly, convert units/errors, keep or exactly permute axes.

    Arbitrary re-rotation is rejected because Z.VAR has no covariance. Preservation
    is safe: a 1D antisymmetric tensor is rotation invariant and no errors are mixed.
    The caller may explicitly supply missing conventions, never silently override
    conflicting metadata. Those supplied interpretations are retained in provenance.
    """
    source = Path(path)
    raw = source.read_bytes()
    if len(raw) > 10_000_000:
        raise EDIError("EDI exceeds the 10 MB offline sounding limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise EDIError("EDI must be UTF-8 or ASCII, not silently repaired text") from error
    blocks, measurements = _sections(text)
    required = {"HEAD", "INFO", "DEFINEMEAS", "MTSECT", "FREQ", "END"}
    required |= {f"Z{c.upper()}{suffix}" for c in COMPONENTS for suffix in ("R", "I", ".VAR")}
    if required-set(blocks):
        raise EDIError(f"Missing required blocks: {sorted(required-set(blocks))}")
    if set(blocks)-(required | {"ZROT"}):
        raise EDIError(f"Unsupported EDI blocks: {sorted(set(blocks)-(required | {'ZROT'}))}; only impedance transfer functions supported")
    header = _assignments(" ".join(blocks["HEAD"]["lines"]))
    info = _assignments(" ".join(blocks["INFO"]["lines"]))
    mtsect = _assignments(" ".join(blocks["MTSECT"]["lines"]))
    if not header.get("DATAID") or header.get("DATAID") != mtsect.get("SECTID"):
        raise EDIError("DATAID and SECTID must be present and agree")
    try:
        count = int(mtsect["NFREQ"])
        empty = float(header.get("EMPTY", "1e32"))
    except (KeyError, ValueError) as error:
        raise EDIError("Invalid NFREQ or EMPTY metadata") from error
    if not 2 <= count <= 512 or not np.isfinite(empty) or empty == 0:
        raise EDIError("Require 2..512 frequencies and a finite nonzero missing sentinel")
    layout = _layout(measurements)
    if len({v["id"] for v in layout.values()}) != 4:
        raise EDIError("Channel identifiers must be unique")
    if any(mtsect.get(c) != value["id"] for c, value in layout.items()):
        raise EDIError("MTSECT channel identifiers do not match measurement definitions")
    input_units = _resolve([header.get("UNITS"), info.get("TRANSFER_FUNCTION.UNITS"), info.get("IMPEDANCE_UNITS")],
                           units, "impedance units", _normalize_units)
    input_sign = _resolve([info.get("TRANSFER_FUNCTION.SIGN_CONVENTION"), info.get("SIGN_CONVENTION")],
                          sign_convention, "time/sign convention", _normalize_sign)
    variance_kind = _resolve([info.get("VARIANCE_CONVENTION"), info.get("CAOS.VARIANCE_CONVENTION")],
                             variance_convention, "variance convention", _normalize_variance)
    freq_units = info.get("FREQUENCY_UNITS", "HZ").upper()
    if freq_units != "HZ":
        raise EDIError("Only FREQ in Hz is supported")
    freq_attributes = _assignments(blocks["FREQ"]["header"].split("//")[0])
    if set(freq_attributes)-{"UNITS", "ORDER"} or freq_attributes.get("UNITS", "HZ").upper() != "HZ":
        raise EDIError("Unsupported FREQ header or frequency units; require Hz")
    if "ORDER" in freq_attributes and freq_attributes["ORDER"].upper() not in ("INC", "DEC"):
        raise EDIError("Unsupported FREQ ordering declaration")
    frequency = _numeric(blocks["FREQ"], count, empty)
    if np.any(frequency <= 0) or len(np.unique(frequency)) != count:
        raise EDIError("Frequencies must be positive and unique")
    zrot = _numeric(blocks["ZROT"], count, empty) if "ZROT" in blocks else None
    tensor = np.zeros((count, 2, 2), dtype=complex)
    variance = np.zeros((count, 2, 2), dtype=float)
    angle = None
    for component in COMPONENTS:
        i, j = ("xy".index(component[0]), "xy".index(component[1]))
        for suffix in ("R", "I", ".VAR"):
            block = blocks[f"Z{component.upper()}{suffix}"]
            attrs = _assignments(block["header"].split("//")[0])
            if set(attrs) != {"ROT"}:
                raise EDIError("Every impedance/error block must declare only ROT=ZROT or a numeric angle")
            try:
                rotation_value = attrs["ROT"]
                block_angle = zrot if rotation_value.upper() == "ZROT" else np.full(count, float(rotation_value))
            except ValueError as error:
                raise EDIError("Unsupported rotation reference") from error
            if block_angle is None or not np.isfinite(block_angle).all():
                raise EDIError("ROT=ZROT requires a finite >ZROT block")
            if angle is None:
                angle = block_angle.copy()
            elif not np.allclose((block_angle-angle+180) % 360-180, 0, atol=1e-7, rtol=0):
                raise EDIError("All tensor components and their variances must share a common frame at each frequency")
            values = _numeric(block, count, empty)
            if suffix == ".VAR":
                if np.any(values <= 0):
                    raise EDIError("All component variances must be strictly positive")
                variance[:, i, j] = values
            elif suffix == "R":
                tensor[:, i, j] += values
            else:
                tensor[:, i, j] += 1j*values
    # Official parser agreement is mandatory, not an optional fallback.
    try:
        from mt_metadata.transfer_functions.io.edi import EDI
    except ImportError as error:
        raise EDIError(f"Install {PARSER_PIN} in the repository venv; no internal package install is required") from error
    try:
        parsed = EDI(fn=source)
        official_order = np.argsort(np.asarray(parsed.frequency))
        order = np.argsort(frequency)
        np.testing.assert_allclose(np.asarray(parsed.frequency)[official_order], frequency[order], rtol=1e-12)
        np.testing.assert_allclose(np.asarray(parsed.z)[official_order], tensor[order], rtol=1e-12, atol=1e-15)
        np.testing.assert_allclose(np.asarray(parsed.z_err)[official_order]**2, variance[order], rtol=1e-12, atol=1e-25)
    except Exception as error:
        raise EDIError(f"Official EDI parser disagrees with validated raw blocks: {error}") from error
    factor = MT_TO_OHM if input_units == "mt" else 1.
    tensor *= factor
    variance *= factor**2
    if input_sign == "-":
        tensor = tensor.conj()
    variance /= 2 if variance_kind == "complex" else 1
    transformation = "none; tensor and marginal errors remain in supplied common frame"
    if rotation == "geographic":
        turns = np.rint(angle/90)
        if not np.allclose(angle, turns*90, atol=1e-7, rtol=0):
            raise EDIError("Arbitrary rotation needs full error covariance; use preserve for isotropic 1D")
        # Exact signed permutation; no cross-component covariance assumption.
        for k, turn in enumerate(turns.astype(int)):
            theta = np.deg2rad(-90*turn)
            rotation_matrix = np.rint([[np.cos(theta), np.sin(theta)], [-np.sin(theta), np.cos(theta)]])
            tensor[k] = rotation_matrix @ tensor[k] @ rotation_matrix.T
            variance[k] = rotation_matrix**2 @ variance[k] @ (rotation_matrix.T**2)
        angle = np.zeros(count)
        transformation = "exact multiple-of-90-degree signed permutation to geographic axes"
    elif rotation != "preserve":
        raise EDIError("Rotation must be preserve or geographic")
    order = np.argsort(frequency)
    frequency, tensor, sigma, angle = frequency[order], tensor[order], np.sqrt(variance[order]), angle[order]
    metadata = dict(header=header, info=info, mtsect=mtsect, measurement_layout=layout)
    provenance = dict(
        source_file=source.name, source_sha256=hashlib.sha256(raw).hexdigest(), source_bytes=len(raw),
        parser="mt_metadata.transfer_functions.io.edi.EDI", parser_version=importlib.metadata.version("mt-metadata"),
        preflight="strict impedance-only EDI v1", original_units=input_units, output_units="ohm",
        units_multiplier_to_ohm=factor, original_sign_convention=input_sign, output_sign_convention="+",
        variance_convention=variance_kind, sigma_definition="SD per real or imaginary component",
        error_assumption="equal real/imag variance and zero real-imag covariance; no component covariance invented",
        interpretation_arguments=dict(units=units, sign_convention=sign_convention, variance_convention=variance_convention),
        rotation_action=transformation, original_rotation_deg=block_angle.tolist(),
        frequency_permutation=order.tolist(), original_frequency_hz=_numeric(blocks["FREQ"], count, empty).tolist(),
        data_kind=info.get("DATA_KIND", "unclassified supplied transfer functions; no geological truth"),
        synthetic=info.get("DATA_KIND") == "original-synthetic-transfer-functions",
        target_known=False,
    )
    return EDISounding(frequency, tensor, sigma, angle, provenance, metadata, _compatibility(tensor, sigma))


def invert_edi(path, thickness, *, component="xy", output=None, beta=.001, initial=None,
               methods=("mt-lm",), seed=61001, bootstrap_samples=128, **read_options):
    """Validate full tensor and execute an actual bounded, fixed-thickness 1D inverse."""
    sounding = read_edi(path, **read_options)
    if not sounding.compatibility["passes_screen"]:
        raise EDIError("Tensor fails the necessary 1D consistency screen; use a dimensionality-appropriate inverse")
    observed, sigma = sounding.select(component)
    f, h = sounding.frequencies, np.asarray(thickness, dtype=float)
    fitted = invert_mt(h, f, observed, sigma, beta=beta, initial=initial, methods=methods, seed=seed)
    for method in fitted.values():
        pred = impedance(method["model"], h, f)
        other = "yx" if component == "xy" else "xy"
        held, held_sig = sounding.select(other)
        method["metrics"]["other_component_wrms"] = float(np.sqrt(np.mean(abs((pred-held)/held_sig)**2)/2))
        method["target"]["provenance"] = "inverted supplied EDI; layer thickness imposed by operator, no measured geology target"
    if bootstrap_samples:
        if "mt-lm" not in fitted:
            raise EDIError("Conditional bootstrap currently supports the TRF estimator only; select mt-lm")
        fitted["mt-lm"]["uncertainty"] = bootstrap_mt(
            fitted["mt-lm"]["model"], h, f, sigma, initial=initial, beta=beta,
            samples=bootstrap_samples, seed=seed+1)
    run = dict(
        schema="inverse-earth/edi-1d/v1", id=sounding.metadata["header"]["DATAID"],
        family="mt", source_kind="EDI transfer functions", component=component,
        geometry="operator-supplied fixed-thickness 1D model", units="ohm m", data_units="ohm",
        frequencies=f.tolist(), thickness=h.tolist(), observed=curves(observed, f),
        sigma=sigma.tolist(), active=np.ones(len(f), dtype=bool).tolist(), methods=fitted,
        tensor=dict(real=sounding.tensor.real.tolist(), imag=sounding.tensor.imag.tolist(),
                    sigma=sounding.sigma.tolist(), rotation_deg=sounding.rotation_deg.tolist()),
        compatibility=sounding.compatibility, provenance=sounding.provenance, metadata=sounding.metadata,
        parameters=dict(regularization=beta, bounds_ohm_m=list(MT_BOUNDS), component=component),
        truth=None, clean=None,  # never invent geological truth for supplied transfer functions
    )
    if output is not None:
        destination = Path(output)
        if destination.resolve() == Path(path).resolve():
            raise EDIError("Output must not overwrite the source EDI")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(run, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return run


def build_fixture_bundle(output_directory, *, bootstrap_samples=128, seed=61001, calibration_realizations=0):
    """Export review-ready original fixtures and inversions, never canonical v2 data.

    manifest.json contains relative source/artifact filenames for static hosting.
    truth_ohm_m in that manifest is a labelled independent synthetic oracle; generic
    EDI artifacts retain truth=null and never feed fixture truth to the estimator.
    """
    fixture_root = Path(__file__).resolve().parents[1]/"data/fixtures/edi"
    definitions = json.loads((fixture_root/"manifest.json").read_text(encoding="utf-8"))
    output_root = Path(output_directory)
    if output_root.resolve() == fixture_root.resolve() or fixture_root.resolve() in output_root.resolve().parents:
        raise EDIError("Bundle output must not overwrite original fixture files")
    output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, fixture in enumerate(definitions["fixtures"]):
        source = fixture_root/fixture["path"]
        artifact_name = source.stem+".json"
        source_name = source.name
        if hashlib.sha256(source.read_bytes()).hexdigest() != fixture["sha256"]:
            raise EDIError("Fixture bytes differ from original manifest")
        run = invert_edi(source, fixture["thickness_m"], output=output_root/artifact_name,
                         bootstrap_samples=bootstrap_samples, seed=seed+i*1000)
        (output_root/source_name).write_bytes(source.read_bytes())
        rows.append(dict(
            id=fixture["id"], label=source.stem, synthetic=True,
            target=fixture["target"], truth_ohm_m=fixture["truth_ohm_m"], thickness_m=fixture["thickness_m"],
            source=source_name, source_sha256=fixture["sha256"], artifact=artifact_name,
            artifact_sha256=hashlib.sha256((output_root/artifact_name).read_bytes()).hexdigest(),
            noise_added=fixture["noise_added"], noise_seed=fixture["noise_seed"],
            input_units=fixture["units"], rotation_deg=fixture["rotation_deg"],
            sign_convention=fixture["sign_convention"], selected_component=run["component"],
            metrics=run["methods"]["mt-lm"]["metrics"],
        ))
    calibration = []
    if calibration_realizations:
        if calibration_realizations < 2 or bootstrap_samples < 20:
            raise EDIError("Calibration requires >=2 independent realizations and >=20 ensemble members")
        f = np.geomspace(.01, 100, 24)
        # Designated calibration models are distinct from the distributed EDI fixtures.
        for model, h, label, calibration_seed in (
            ([230.], [], "halfspace", 95317), ([180., 20.], [450.], "two-layer", 95318)
        ):
            sigma = .04*abs(impedance(model, h, f))
            evidence = calibrate_mt_bootstrap(
                model, h, f, sigma, realizations=calibration_realizations, samples=bootstrap_samples,
                seed=calibration_seed, beta=.001)
            filename = f"calibration-{label}.json"
            path = output_root/filename
            path.write_text(json.dumps(evidence, indent=2, allow_nan=False)+"\n", encoding="utf-8")
            calibration.append(dict(
                id=label, artifact=filename, artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                synthetic=True, realizations=calibration_realizations,
                coverage_per_layer=evidence["coverage_per_layer"],
                failures=evidence["failures"], seed=calibration_seed,
                applicability="These independently seeded synthetic calibration models only; not field coverage.",
            ))
    bundle = dict(
        schema="inverse-earth/edi-bundle/v1", fixtures=rows, license=definitions["license"],
        calibration=calibration,
        parser_dependency=PARSER_PIN,
        artifact_schema="inverse-earth/edi-1d/v1",
        provenance="Original analytic synthetic transfer functions; not downloaded field data",
        uncertainty="Per-artifact TRF conditional parametric bootstrap, no empirical coverage inferred here",
    )
    (output_root/"manifest.json").write_text(json.dumps(bundle, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("--fixture-bundle", action="store_true", help="Export all original fixtures; --output is a directory")
    parser.add_argument("--thickness", nargs="*", type=float, default=[], help="Finite-layer thicknesses in metres; omit for half-space")
    parser.add_argument("--component", choices=("xy", "yx"), default="xy")
    parser.add_argument("--units", choices=("mt", "ohm"), help="Explicit missing-unit interpretation, recorded in provenance")
    parser.add_argument("--sign-convention", choices=("+", "-"))
    parser.add_argument("--variance-convention", choices=("complex", "per-real-component"))
    parser.add_argument("--rotation", choices=("preserve", "geographic"), default="preserve")
    parser.add_argument("--beta", type=float, default=.001)
    parser.add_argument("--seed", type=int, default=61001)
    parser.add_argument("--bootstrap-samples", type=int, default=128, help="0 disables; otherwise >=20")
    parser.add_argument("--calibration-realizations", type=int, default=0,
                        help="Fixture bundle only: independently seeded synthetic coverage experiments; 0 disables")
    parser.add_argument("--all-methods", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.fixture_bundle:
        if args.source is not None:
            parser.error("Do not supply source together with --fixture-bundle")
        try:
            result = build_fixture_bundle(args.output, bootstrap_samples=args.bootstrap_samples, seed=args.seed,
                                          calibration_realizations=args.calibration_realizations)
        except (EDIError, ValueError, OSError) as error:
            parser.exit(2, f"EDI rejected: {error}\n")
        print(json.dumps(dict(output=str(args.output/"manifest.json"), fixtures=len(result["fixtures"]))))
        return
    if args.source is None:
        parser.error("Supply an EDI source or --fixture-bundle")
    if args.calibration_realizations:
        parser.error("--calibration-realizations is only supported with --fixture-bundle")
    methods = ("mt-lm", "mt-adam", "mt-neural") if args.all_methods else ("mt-lm",)
    try:
        result = invert_edi(args.source, args.thickness, component=args.component, output=args.output,
                            units=args.units, sign_convention=args.sign_convention,
                            variance_convention=args.variance_convention, rotation=args.rotation,
                            beta=args.beta, seed=args.seed, bootstrap_samples=args.bootstrap_samples, methods=methods)
    except (EDIError, ValueError, OSError) as error:
        parser.exit(2, f"EDI rejected: {error}\n")
    print(json.dumps(dict(output=str(args.output), source_sha256=result["provenance"]["source_sha256"],
                          methods={k: v["metrics"] for k, v in result["methods"].items()}), allow_nan=False))


if __name__ == "__main__":
    main()
