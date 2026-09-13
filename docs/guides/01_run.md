# Run setup and release bake

On Windows, run scripts/setup.ps1 from the repository root. This creates the ignored root .venv and the offline .venv-pipeline. Run scripts/fetch-data.ps1 for the optional SimPEG comparison archives, then scripts/precompute.ps1. The all command produces 20 result artifacts, one manifest per case, an index, a release record, and a validation result.

Run the Python tests in .venv-pipeline. Build the SPA from frontend with npm install and npm run build. The build copies data/derived into a public overlay and does not regenerate canonical science.

The Bash commands have the same subcommands and are intended for Git Bash, Linux, or CI.
