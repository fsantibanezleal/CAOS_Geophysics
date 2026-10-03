# Read physical gravity JSON and calculate explicit corrections locally

The local parser accepts original `gravity-stations-1` bytes, not arbitrary CSV,
an API envelope, a file path or a previously decoded dictionary. It preserves
native numbers, Unicode, station order and supplied history. It does not acquire
data, correct measurements, authenticate a citation or make a field dataset
eligible. The [exact root contract](../design/features/physical-json-boundary/contracts.md)
defines every required field and the structural rejection rules.

Run the examples from `data-pipeline` using the existing reviewed interpreter.
Parsing needs only Python's standard library. The separate correction adapter
requires the pinned Boule0.5.0/Harmonica0.7.0/NumPy2.2.6/SciPy1.15.2 runtime and
unchanged scientific core; no example installs dependencies or changes engines.

## Read an explicitly selected local file with a byte ceiling

Replace the literal path below with your own rights-cleared physical root file.
The caller reads at most16777217 bytes: the inclusive16-MiB limit plus one byte
to detect excess. The parser never opens the path or creates a file. Reading the
whole file first with `read_bytes()` would defeat this caller-side allocation
bound, even though the parser subsequently rejects its oversized argument.

```python
from hashlib import sha256
from pathlib import Path
from gravity_station_json import (
    MAX_RAW_BYTES, GravityStationsJsonError, load_gravity_stations_json,
)
from gravity_processing import digest

try:
    with Path("my-survey.gravity-stations.json").open("rb") as source:
        raw = source.read(MAX_RAW_BYTES + 1)
except OSError:
    print("Selected local source could not be read.")
else:
    try:
        dataset = load_gravity_stations_json(raw)
    except GravityStationsJsonError as error:
        print({"code": error.code, "field": error.field,
               "message": error.message})
    else:
        print({"raw_sha256": sha256(raw).hexdigest(),
               "scientific_dataset_sha256": digest(dataset),
               "station_count": len(dataset["stations"]),
               "declared_state": dataset["state"]})
```

This is an explicit local-file recipe, not an authenticated upload endpoint or
a safe arbitrary-path service. No supplied file was assumed present to validate
this recipe. Filesystem errors print a fixed message; parser errors expose only
their fixed code/known field/message. Never serialize traceback frames, locals,
decoder exceptions or private station values into a web error.

The raw hash identifies exact supplied bytes, including whitespace and numeric
spelling. The scientific digest is the unchanged core's sorted compact ASCII
object identity. The supplied `metadata.source_sha256` is a third declaration,
not an automatically verified copy of either hash. Do not overwrite it to make
identities match. A matching self-supplied hash is not provider authentication.

## Execute the parser-to-correction analytical control

The following reads the existing trusted committed control wrapper, encodes its
complete parent as raw JSON, invokes the actual strict parser, and runs the real
ordinary correction adapter with its explicitly saved configuration. The first
`json.loads` is only for that trusted repository fixture; never substitute an
untrusted wrapper there. It writes no dataset, result, provider or receipt file.

```python
import json
from pathlib import Path
from gravity_station_json import load_gravity_stations_json
from gravity_processing import digest
from gravity_station_adapter import run_station_corrections

control = json.loads(Path(
    "../docs/methods/gravity-processing/examples/station-control.json"
).read_text(encoding="utf-8"))
raw = json.dumps(control["dataset"], ensure_ascii=False,
                 allow_nan=False).encode("utf-8")
dataset = load_gravity_stations_json(raw)
request = {
    "schema_version": "gravity-station-adapter-request-1",
    "method": "gravity.station-corrections/v1",
    "dataset": dataset,
    "config": control["config"],
    "input_dataset_sha256": digest(dataset),
    "submitted_config_sha256": digest(control["config"]),
}
result = run_station_corrections(request)
print(result["correction_result"]["qc"]["derived_mgal"])
print(result["receipt"]["acceptance"])
```

The mathematical control has latitude45 degrees, ellipsoidal receiver/surface
height1000 m, plate density2670 kg/m3 and prescribed residual12 mGal. These are
its authored inputs, not recommended defaults or measured geology. The actual
calculation applies WGS84 normal/elevation terms and the infinite land plate;
the [method chapter](../methods/gravity-processing/01_station-corrections.md)
gives equations, signs, units, uncertainty assumptions and independent oracles.
Adapter failures use its separate safe record as shown in the
[adapter guide](13_local_station_adapter.md); parser success does not suppress
those scientific failures. Complete output retains original values, actual
history, propagation and the unchanged false host/method/field authority flags.

MAIN executed both exact Markdown code blocks on2026-10-03 in the reviewed
runtime. The real parser/adapter control returned12.000000000024315 mGal and
all three authority flags false. The first block's absent-user-file branch
printed its fixed message. No user file was fabricated, and that absent-path
check is not a claim that an external measured dataset was processed.

For your own calculation, supply the complete physical parent and explicit
configuration, not this fixture's density or uncertainties. A later correction
uses the actual complete prior output dataset and its scientific digest, not
rounded displayed values. Equivalent-source fitting/continuation is a
[different operation](../methods/gravity-processing/02_equivalent-source-transforms.md);
its coefficients are not a recovered3D density model.

## Bounds and scientific limitations

The root lane admits1..400 stations,16 MiB actual raw bytes,8 MiB canonical root,
depth16,200000 nodes,128 UTF-8 bytes/key,8192 bytes/string,128 source characters
per numeric token and integer-token magnitude at most2^53-1. Every bound is
inclusive; overflow, malformed UTF-8, decoded duplicates, unpaired surrogates
and nonfinite numbers reject before native materialization. Nothing is trimmed,
normalized, guessed, thinned or silently repaired. Existing adapter limits apply
again to its whole request, not to a shifted root presumed equivalent.

Structural acceptance does not prove numerical history, calibration/tide work,
height/reference consistency, uncertainty validity, source rights or3D modelling
eligibility. The retained Bartlett author rows remain physically ineligible;
do not manufacture their datum/errors or thin them to meet a size limit. The
[independent parser review](../validation/physical-json-independent-review-2026-10-03.md)
records actual179-pass/no-skip integration and allocation controls. A16-MiB
astral/whitespace input peaked near111 MB in its measured Windows process;
16 MiB is not a general memory ceiling. These are local observations, not
browser/server admission or an activated online physical-child workflow.
