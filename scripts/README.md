# Scripts

These scripts make the complete local workflow reproducible on Windows PowerShell and POSIX shells.

| Script | Purpose |
|---|---|
| `setup.ps1` / `setup.sh` | Create ignored runtime and offline environments. Add `-Gpu` or `--gpu` for the CUDA lane. |
| `fetch-data.ps1` / `fetch-data.sh` | Download public SimPEG comparison archives into ignored `data/downloads/` and print their checksums. |
| `precompute.ps1` / `precompute.sh` | Run all nine named stages and bake every registered case into `data/derived/`. |
| `dev.ps1` / `dev.sh` | Copy canonical replay artifacts into the frontend and run Vite. |
| `local.ps1` / `local.sh` | Build, test, lint, validate artifacts, and stop the local server. |
| `check_artifacts.py` | Enforce the processing to web manifest and byte-size contract. |
| `check_template_residue.py` | Ensure the instantiated repository has no archetype example cases or placeholder sources. |
| `check_content_standards.py` | Reject em-dashes and pictographic emoji in tracked repository content. |

The frontend and VPS never run the scientific bake. They serve the validated replay artifacts produced locally by the offline environment.
