"""Rebuild original synthetic EDI fixtures; no external measurements or licences.

The oracle deliberately does not import the inversion forward operator. Half-space
uses the closed form; the two-layer fixture uses a reflection-coefficient formula.
Run with the repository venv from any working directory. Output stays beside script.
"""
from pathlib import Path
import hashlib
import json

import numpy as np

ROOT = Path(__file__).resolve().parent
MU0 = 4*np.pi*1e-7


def block(name, values, rotation=True):
    header = f">{name}"+(" ROT=ZROT" if rotation else "")+f" // {len(values)}"
    rows = [" ".join(f"{v:.16e}" for v in values[i:i+5]) for i in range(0, len(values), 5)]
    return "\n".join([header, *rows])


def create(name, model, thickness, units, angle, sign, noise, seed):
    frequency = np.geomspace(100., .01, 24)
    omega = 2*np.pi*frequency
    halfspace = (1+1j)*np.sqrt(omega*MU0*model[-1]/2)
    z = halfspace
    if len(model) == 2:
        characteristic = (1+1j)*np.sqrt(omega*MU0*model[0]/2)
        propagation = (1+1j)*np.sqrt(omega*MU0/(2*model[0]))
        reflection = (halfspace-characteristic)/(halfspace+characteristic)
        r = reflection*np.exp(-2*propagation*thickness[0])
        z = characteristic*(1+r)/(1-r)
    sigma = .025*abs(z)
    tensor = np.zeros((len(frequency), 2, 2), dtype=complex)
    tensor[:, 0, 1], tensor[:, 1, 0] = z, -z
    if noise:
        rng = np.random.default_rng(seed)
        tensor += sigma[:, None, None]*(rng.normal(size=tensor.shape)+1j*rng.normal(size=tensor.shape))
    if sign == "-":
        tensor = tensor.conj()
    factor = MU0*1000 if units == "mt" else 1.
    tensor /= factor
    variance = 2*(sigma/factor)**2
    station = name.upper().replace("-", "_")
    text = f""">HEAD
 DATAID={station}
 ACQBY=CAOS_SYNTHETIC
 FILEBY=CAOS
 FILEDATE=2026-09-24
 LAT=0
 LON=0
 ELEV=0
 EMPTY=1.000000E+32
 UNITS={"millivolts_per_kilometer_per_nanotesla" if units == "mt" else "ohm"}
 STDVERS="SEG 1.0"
>INFO
 DATA_KIND=original-synthetic-transfer-functions
 SIGN_CONVENTION={sign}
 VARIANCE_CONVENTION=complex
 FREQUENCY_UNITS=Hz
 CAOS.PROVENANCE="Independent analytic half-space or two-layer reflection formula; no field acquisition"
 CAOS.LICENSE=CC0-1.0
 CAOS.COORDINATES=unspecified-synthetic-not-a-field-site
 CAOS.NOISE_SEED={seed}
>=DEFINEMEAS
 MAXCHAN=4
 MAXRUN=1
 MAXMEAS=4
 UNITS=M
 REFTYPE=CART
 REFLAT=0
 REFLONG=0
 REFELEV=0
>HMEAS ID=1 CHTYPE=HX X=0 Y=0 AZM=0
>HMEAS ID=2 CHTYPE=HY X=0 Y=0 AZM=90
>EMEAS ID=3 CHTYPE=EX X=0 Y=0 X2=100 Y2=0
>EMEAS ID=4 CHTYPE=EY X=0 Y=0 X2=0 Y2=100
>=MTSECT
 SECTID={station}
 NFREQ={len(frequency)}
 NCHAN=4
 HX=1
 HY=2
 EX=3
 EY=4
"""
    text += block("FREQ", frequency, False)+"\n"
    text += block("ZROT", np.full(len(frequency), angle), False)+"\n"
    for component, i, j in (("XX", 0, 0), ("XY", 0, 1), ("YX", 1, 0), ("YY", 1, 1)):
        for suffix, values in (("R", tensor[:, i, j].real), ("I", tensor[:, i, j].imag), (".VAR", variance)):
            text += block("Z"+component+suffix, values)+"\n"
    text += ">END\n"
    path = ROOT/(name+".edi")
    path.write_text(text, encoding="utf-8", newline="\n")
    return dict(
        id=station, path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size,
        data_kind="original synthetic transfer functions; not field measurements",
        target=dict(quantity="electrical resistivity", units="ohm m", dimensionality="1D fixed-thickness layers",
                    provenance="independent analytic synthetic oracle"),
        truth_ohm_m=model, thickness_m=thickness, noise_seed=seed, noise_added=noise,
        noise_law="independent real and imaginary Gaussian parts, SD=0.025*abs(clean off-diagonal Z)" if noise else "none; positive 2.5% declared test errors",
        units=units, sign_convention=sign, rotation_deg=angle, variance_convention="complex",
        expected_artifact=f"data/experiments/edi/{name}.json",
        command=f".venv-pipeline/Scripts/python data-pipeline/edi.py data/fixtures/edi/{name}.edi"
                + (f" --thickness {' '.join(map(str, thickness))}" if thickness else "")
                + f" --bootstrap-samples 128 --output data/experiments/edi/{name}.json",
    )


def main():
    items = [
        create("halfspace-100-native", [100.], [], "mt", 0., "+", False, 67101),
        create("halfspace-500-ohm-negative", [500.], [], "ohm", 90., "-", False, 67102),
        create("two-layer-noisy-rotated", [120., 12.], [350.], "mt", 27., "+", True, 67201),
    ]
    manifest = dict(
        schema="inverse-earth/edi-fixtures/v1", created="2026-09-24", license="CC0-1.0",
        generator="data/fixtures/edi/generate_fixtures.py",
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        fixtures=items, parser_dependency="mt-metadata==1.0.10",
        target_policy="Fixture truth is for independent evaluation only; the EDI inversion does not read this manifest.",
        public_artifacts="Integration owner promotes validated output; these commands never write canonical data/derived/v2.",
    )
    (ROOT/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
