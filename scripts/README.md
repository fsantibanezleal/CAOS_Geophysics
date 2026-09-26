# Scripts

These scripts make the complete local workflow reproducible on Windows PowerShell and POSIX shells.

| Script | Purpose |
|---|---|
| `setup.ps1` / `setup.sh` | Create ignored runtime and offline environments. Add `-Gpu` or `--gpu` for the CUDA lane. |
| `fetch-data.ps1` / `fetch-data.sh` | Download public SimPEG comparison archives into ignored `data/downloads/` and print their checksums. |
| `precompute.ps1` / `precompute.sh` | Bake numerical experiments into an ignored candidate directory; this does not assemble EDI evidence or promote canonical data. |
| `rebuild-release.ps1` | On Windows, bake or resume all 120 conditions, assemble synthetic EDI fixtures and the pinned measured screen, build the catalogue, and run artifact/recovery gates in ignored `data/experiments/`. Requires the cited local station EDI before the bake. `-SkipNumerical` validates an existing numerical candidate. |
| `dev.ps1` / `dev.sh` | Copy canonical replay artifacts into the frontend and run Vite. |
| `local.ps1` / `local.sh` | Build, test, lint, validate artifacts, and stop the local server. |
| `check_artifacts.py` | Enforce the processing to web manifest and byte-size contract. |
| `check_template_residue.py` | Ensure the instantiated repository has no archetype example cases or placeholder sources. |
| `check_content_standards.py` | Reject em-dashes and pictographic emoji in tracked repository content. |

The frontend and VPS never run the scientific bake. They serve the validated replay artifacts produced locally by the offline environment.
The release script refuses `data/derived/v2` as output. Canonical artifacts are copied from a fully validated candidate only as a separate reviewed promotion step.
