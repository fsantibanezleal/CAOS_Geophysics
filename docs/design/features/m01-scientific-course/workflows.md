# Real local Python workflows for explicitly eligible user files

Status: proposed lesson recipes using existing ordinary code, NOT executed for this course milestone. All example files are selected or authored by the user; absent paths are errors, not invitations to fabricate field inputs. Full MAIN approval precedes recipe execution and publication as authored wiki content. No dependency install, environment creation, new source module, authenticated job or provider reinterpretation is included.

## 1. Preconditions and interpreter selection

Work from the repository root for paired commands, or data-pipeline for Python blocks. Use an already reviewed CPython3.12 environment matching [requirements-m01.txt](../../../../data-pipeline/requirements-m01.txt) and [requirements-m01-transforms.txt](../../../../data-pipeline/requirements-m01-transforms.txt); do not silently extend another agent's environment or upgrade pins. Paired scripts select this checkout's existing .venv-m01. A trusted alternate existing interpreter may be selected explicitly, never guessed from a system PATH or a claimed newly created environment.

```powershell
$ExistingM01Python = Join-Path (Get-Location) '.venv-m01/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $ExistingM01Python)) {
    throw 'Select an existing reviewed M01 interpreter before running this recipe.'
}
& $ExistingM01Python --version
```

POSIX selection, also without creating an environment:

```sh
M01_PYTHON='./.venv-m01/bin/python'
test -x "$M01_PYTHON" || { printf '%s\n' 'Select an existing reviewed M01 interpreter.' >&2; exit 2; }
"$M01_PYTHON" --version
```

Interpreter version alone is not the full pin gate. The actual modules enforce their stated engines; the ordinary adapter also enforces source/__file__/runtime integrity. The notebook/CLI below needs the full existing transform environment because its bounded JSON reader resides in gravity_transforms, which imports the installed engines. That is not a claim that raw structural parsing inherently needs scientific dependencies.

Before calling science, audit quantity/state/history, original units/signs, datum/frame/tide conventions, processing lineage and known primitive SDs. Prepare exact [contract](contracts.md) objects, not a CSV header mapping. Do not take a processed CBA/ISO, declare it absolute observed gravity, copy another fixture's uncertainties/density or replace missing elevation with1200. If metadata is insufficient, retain an ineligible/QC-only diagnosis. The separate newly reviewed raw JSON guide is [owned by MAIN](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/231ca4291b129251e0a80bec120f8a1fc6b02576/docs/guides/15_local_physical_json.md); it is not a new course parser or a retrofit to the existing core CLI.

## 2. User-file corrections with existing paired scripts

`my-corrections.json` must contain exactly dataset and config. Its dataset is the complete actual gravity-stations-1 parent; its config is the user's explicit target/error/plate/terrain declaration. Do not use an API or adapter envelope for this CLI. Pick a fresh run directory for each invocation; no overwriting, canonical paths or private receipt publication.

```powershell
./scripts/run_m01_gravity.ps1 --input ./my-corrections.json --output-dir ./data/raw/gravity-m01/my-run-001
```

```sh
bash ./scripts/run_m01_gravity.sh --input ./my-corrections.json --output-dir ./data/raw/gravity-m01/my-run-001
```

The real output is gravity-result.json (dataset/processing/qc) plus receipt.json. Receipt file hashes refer to actual file bytes; processing input/output hashes refer to scientific objects. Keep the original selected request bytes, full output and receipt; do not reconstruct source bytes from pretty JSON or update old receipts in place. An initial integer-bearing parent may be scientifically valid yet fail the bounded transform input-identity reconstruction; retaining it does not guarantee later admission.

Core CLI has a32-MiB stat and post-read actual-byte check with duplicate-key rejection. It reads bytes before the post-read check; it is not a streaming untrusted-upload allocation guarantee, and its errors are local diagnostics, not web-safe records. Use a suitable separately approved bounded caller for genuinely untrusted acquisition. Do not advertise this local command as a general arbitrary-path service.

## 3. Ordinary adapter using actual local user-file objects

The following complete Python block runs from data-pipeline in the existing matched environment. It uses the existing transform reader's MAX+1/depth/UTF-8/duplicate/nonfinite checks for a local file, then the ordinary adapter validates its actual native request. This is a local recipe, not HTTP admission; it supplies no source authenticity or geometry guesses. Select my-corrections.json yourself. Missing file/unsafe JSON fails before the adapter and is intentionally not converted into a publishable web response.

```python
from pathlib import Path
from gravity_transforms import read_request
from gravity_processing import digest
from gravity_station_adapter import (
    GravityStationAdapterError, run_station_corrections,
)

selected = read_request(Path('../my-corrections.json'))
if type(selected) is not dict or set(selected) != {'dataset', 'config'}:
    raise ValueError('Expected the selected local dataset/config document.')
request = {
    'schema_version': 'gravity-station-adapter-request-1',
    'method': 'gravity.station-corrections/v1',
    'dataset': selected['dataset'],
    'config': selected['config'],
    'input_dataset_sha256': digest(selected['dataset']),
    'submitted_config_sha256': digest(selected['config']),
}
try:
    corrected = run_station_corrections(request)
except GravityStationAdapterError as error:
    print(error.to_record())
else:
    print(corrected['correction_result']['dataset']['state'])
    print(corrected['receipt']['acceptance'])
```

Only the adapter's to_record is its fixed safe serialized failure surface. Do not print traceback context/locals/other exceptions into public logs. A compatible engine is not authenticated origin; all three acceptance flags remain false. Caller-known file errors and transform/core errors need a separately designed safe boundary in an actual web caller, which is not authorized here.

The notebook variable corrected is the four-key adapter result. For a transform use corrected['correction_result'], not corrected itself. For a later correction use corrected['correction_result']['dataset'] as the exact complete next parent and its actual scientific digest, with a strictly later target and unchanged earlier reduction parameters. Preserve integer/float distinctions, original_values, full history and supplied source identity. A valid resume in the core/adapter is not universal transform replay eligibility. Do not round displayed values or create a synthetic earlier input.

## 4. Build a transform request without guessing geometry/errors

First obtain the real correction result from step2, or use the whole correction_result variable from step3. Independently prepare my-metric-geometry.json with all sixteen geometry keys and my-transform-config.json with the actual bounded config/covariance. User-owned metric conversion and source-free/geometry-error justification are prerequisites, not generated by this block. Upward values must match the existing core QC; error scale/covariance cannot be inferred from fit residuals or missing metadata.

Run from data-pipeline; the controlled output location is ignored and the input file is created exclusively. There is no existing file to overwrite. Paths below are user-selected local workspace paths, not a service accepting arbitrary remote path names.

```python
import json
from pathlib import Path
from gravity_transforms import read_request

correction_result = read_request(Path(
    '../data/raw/gravity-m01/my-run-001/gravity-result.json'
))
geometry = read_request(Path('../my-metric-geometry.json'))
config = read_request(Path('../my-transform-config.json'))
request = {
    'schema_version': 'gravity-transform-request-1',
    'correction_result': correction_result,
    'geometry': geometry,
    'config': config,
}
target = Path('../data/raw/gravity-m01-transforms/my-transform-001.json')
target.parent.mkdir(parents=True, exist_ok=True)
with target.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(request, stream, sort_keys=True, indent=2, allow_nan=False)
    stream.write('\n')
```

JSON serialization preserves native numeric types; it does not recover original raw bytes or fix an unreconstructable parent. No untrusted whole-archive extraction, pickle, dynamic operator or array loading is used. Admission of this composed document occurs when the real transform executes, not merely when json.dump succeeds.

From repository root, run exactly one platform's command:

```powershell
./scripts/run_m01_transforms.ps1 --input ./data/raw/gravity-m01-transforms/my-transform-001.json --output-dir ./data/raw/gravity-m01-transforms/my-transform-run-001
```

```sh
bash ./scripts/run_m01_transforms.sh --input ./data/raw/gravity-m01-transforms/my-transform-001.json --output-dir ./data/raw/gravity-m01-transforms/my-transform-run-001
```

Expect request.json, result.json, actual theme-aware SVG/PNG map/diagnostic exports and receipt.json as completion marker, not a separate model.json. A missing completion receipt is not a complete publication; leave an interrupted directory for inspection and choose a new run path. Inspect selection.status and CLI exit: unmet_height_precision exits3 with preserved diagnostics, contract failure rejects, and a successful local export still leaves field_gate open/full_method_accepted false. Never substitute synthetic controls for a missing user file or field gate.

## 5. Direct Python transform and numeric replay

This alternative block also runs from data-pipeline with an actual already prepared user request. It calls the existing ordinary functions, not an inverse API. Choose a different fresh export path than step4.

```python
from pathlib import Path
from gravity_transforms import read_request, transform_survey, export_bundle

request = read_request(Path(
    '../data/raw/gravity-m01-transforms/my-transform-001.json'
))
result = transform_survey(request)
receipt = export_bundle(request, result, Path(
    '../data/raw/gravity-m01-transforms/my-transform-python-001'
))
print(result['selection']['status'])
print(result['evaluation']['holdout'])
print(result['provenance']['full_method_accepted'])
```

Export identity check binds this result to this request but is not a general malicious-result validator or authenticated source receipt. See exact parent/height/covariance/support constraints in contracts.md. Replaying a locally verified bound numeric result with replay_grid is possible without pickle, but that function does not validate arbitrary uploaded checkpoints. Public course records require separate full artifact/index verification before they are displayed.

## 6. Expected evidence, not assumed execution

After explicit approval validate exact blocks in a fresh local scratch with an actual eligible authored-control input plus absent-file and scientific negatives; retain command, runtime, actual source/config/input/output/artifact hashes and safe output. Re-run frozen independent formulas/blocked oracles without changing tolerances. Field-like metadata declarations in a control remain labelled authored controls. Course recipe execution is currently NOT_RUN; older M01 and MAIN JSON-guide receipts are not adopted as execution of these new blocks.
