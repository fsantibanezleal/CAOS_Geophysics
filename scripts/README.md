# Scripts

These scripts make the complete local workflow reproducible on Windows PowerShell and POSIX shells.

| Script | Purpose |
|---|---|
| `setup.ps1` / `setup.sh` | Create ignored runtime and offline environments. Add `-Gpu` or `--gpu` for the CUDA lane. |
| `fetch-data.ps1` / `fetch-data.sh` | Acquire the two reviewed SimPEG comparison archives through the source allowlist, verify exact bytes/SHA-256, and write ignored immutable raw receipts. |
| `precompute.ps1` / `precompute.sh` | Bake numerical experiments into an ignored candidate directory; this does not assemble EDI evidence or promote canonical data. |
| `rebuild-release.ps1` | On Windows, bake or resume all 120 conditions, assemble synthetic EDI fixtures and the pinned measured screen, build the catalogue, and run artifact, recovery and full CUDA FWI-replay gates in ignored `data/experiments/`. Requires the cited local station EDI before the bake. `-SkipNumerical` validates an existing numerical candidate. |
| `dev.ps1` / `dev.sh` | Copy canonical replay artifacts into the frontend and run Vite. |
| `local.ps1` / `local.sh` | Build, test, lint, validate artifacts, and stop the local server. |
| `check_artifacts.py` | Enforce the processing to web manifest and byte-size contract. |
| `check_phase_assets.py` | Check the committed M13 ONNX, real-trace, QC and benchmark byte/hash contract without training or source downloads. |
| `validate_fwi_exports.py` | On local CUDA, replay all 24 seismic conditions and independently check 48 saved final models, receiver predictions, residuals, metrics and verdicts. Not run by CPU-only CI. |
| `validate_mt_replays.py` | Local-only replay of all 24 current-source MT conditions / 72 results, original seeded observations, final predictions/residuals, objective states, metrics and 3,072 actual bootstrap refits, plus the pinned cl061 QC-only screen. Writes a source-bound receipt inside the ignored candidate; does not promote canonical artifacts or enable host admission. |
| `check_template_residue.py` | Ensure the instantiated repository has no archetype example cases or placeholder sources. |
| `check_content_standards.py` | Reject em-dashes and pictographic emoji in tracked repository content. |

The frontend and VPS never run the scientific bake. They serve the validated replay artifacts produced locally by the offline environment.
The release script refuses `data/derived/v2` as output. Canonical artifacts are copied from a fully validated candidate only as a separate reviewed promotion step.
