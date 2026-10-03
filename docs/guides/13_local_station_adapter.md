# Run the ordinary physical station adapter locally

This callable performs the reviewed M01 physical reduction, not CSV outlier flags. Its six-key request contains an exact `gravity-stations-1` parent, explicit correction configuration and separate parent/configuration digests. The real scientific core runs once. Normal gravity, height, Bouguer plate, supplied terrain residual and propagated uncertainty follow the [method contract](../methods/gravity-processing/01_station-corrections.md); [transforms](../methods/gravity-processing/02_equivalent-source-transforms.md) are a different operation.

Use the existing reviewed CPython 3.12 environment with Boule 0.5.0, Harmonica 0.7.0, NumPy 2.2.6 and SciPy 1.15.2. The adapter checks these versions, the exact scientific-core hash and the imported sibling's actual file location. A changed/missing runtime fails; it does not install dependencies or fall back to another engine.

## Reproduce the analytical control

From a Python process launched in this repository's `data-pipeline` directory, the following reads the existing **trusted committed analytical fixture**, not an arbitrary upload. It prints the resulting values and safe acceptance record; it writes no dataset or result files.

```python
import json
from pathlib import Path
from gravity_processing import digest
from gravity_station_adapter import run_station_corrections, GravityStationAdapterError

control = json.loads(Path(
    "../docs/methods/gravity-processing/examples/station-control.json"
).read_text(encoding="utf-8"))
request = {
    "schema_version": "gravity-station-adapter-request-1",
    "method": "gravity.station-corrections/v1",
    "dataset": control["dataset"],
    "config": control["config"],
    "input_dataset_sha256": digest(control["dataset"]),
    "submitted_config_sha256": digest(control["config"]),
}
try:
    result = run_station_corrections(request)
except GravityStationAdapterError as error:
    print(json.dumps(error.to_record(), allow_nan=False))
else:
    print(result["correction_result"]["qc"]["derived_mgal"])
    print(result["receipt"]["acceptance"])
```

The independently executed analytical result is approximately 12 mGal. It is a formula/replay control, not measured field geology. The receipt's `host_approved`, `full_method_accepted` and `field_source_verified` declarations remain false. Their meaning is that this function does not certify those independent authorities, not that a failed scientific correction is disguised as success.

## Supply a different scientific object

Construct the complete parent using the [exact physical contract](../design/features/m01-gravity-station-adapter/design.md). All source, instrument, tide, height/reference, unit/sign and primitive-error metadata must be supplied and consistent. A source citation or matching self-supplied hash is not source authentication. In particular, the attributed Bartlett principal facts remain ineligible; no automatic OG/FAA/CBA conversion, guessed height datum, guessed uncertainty or row thinning exists.

The ordinary adapter admits 1..400 stations, exact native JSON-compatible built-ins, finite numbers, bounded structure/strings and at most 16 MiB canonical encoding. Preserve original values and order. For a later correction stage, pass the **actual complete previous output dataset** with its exact digest; do not reconstruct it from rounded plots or reapply earlier corrections. Both submitted and normalized configurations receive separate identities. Outliers are flagged, not removed.

The snippet's `json.loads` is suitable only for the reviewed trusted fixture. It is **not** an untrusted-upload parser: duplicate keys can already have been discarded before the callable receives a decoded object. Authenticated raw transport must separately enforce byte/depth limits, duplicate-key/nonfinite rejection, immutable raw hashes, ownership and the exact admitted parent version. That online correction-child integration is not implemented by this guide or callable. Do not run provider code, pickle, arbitrary import paths or source scripts.

Only `GravityStationAdapterError.to_record()` is a safe serialized failure surface. Do not return arbitrary exception arguments, contexts, tracebacks, locals or source values. The full successful result is private caller data until its rights/ownership/publication policy is independently established. No CLI filesystem publication, worker/API lifecycle, quota, cancellation, restore or measured host gate is asserted here.

## Verification

Run the new adapter tests alongside the unchanged correction/transform/source tests in the reviewed environment. [Independent review](../validation/station-adapter-independent-review-2026-10-03.md) records 223 passing controls without skips, including the actual author archive's negative admission. It does not close full M01 or product acceptance.
