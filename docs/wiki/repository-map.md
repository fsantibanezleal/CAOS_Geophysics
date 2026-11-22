# Repository map

This repository contains the Inverse Earth Studio research application, its numerical workflows, source and derived data records, bilingual lessons, and the evidence used to judge each method. The map below describes current responsibilities; it does not imply that every method or release has passed scientific acceptance.

## Application and numerical code

- `frontend/` is the React application. It composes the published CAOS App Shell and reads committed, hash-identified result arrays. Browser calculations are enabled only where their runtime and numerical boundary are documented.
- `data-pipeline/` contains source intake, validation, preprocessing, forward operators, inverse solvers, evaluation, and export. The scripts run in the repository's local pipeline environment; GPU execution is selected by the relevant workflow and installed engine.
- `scripts/` contains reproducible orchestration and repository guards. It is not an internal Python package; numerical modules are invoked through the documented local commands.
- `tests/` holds numerical controls, data-contract checks, adversarial cases, and browser-facing checks. A passing focused suite supports only the behavior it exercises.

## Data, models, and lessons

- `data/source-ledger.json` records provenance for included source assets. `data/derived/` contains explicitly identified computed artifacts and their catalogue; authored synthetic truth is never presented as field truth.
- Raw downloads and other large working inputs are kept outside Git in the configured data root. Provider links, rights, units, coordinates, and uncertainty metadata determine whether an input is eligible for a particular method.
- `models/` records checkpoints, training splits, and evaluation receipts. Model training and full FWI remain local workflows; a saved artifact or browser replay is not represented as online retraining.
- `notebooks/en/` and `notebooks/es/` contain the parallel English and Spanish course. The `docs/methods/` chapters describe the method assumptions, equations, limits, implementation paths, and reproducible commands.
- `manuscripts/` contains the technical report and separate research manuscripts. Each document's measured content gate, scientific conclusion, and publication status are distinct.

## Contracts and release boundary

`docs/contracts/` defines the catalogue, readiness, API, payload, and browser-model asset contracts. The versioned catalogue binds each artifact to its byte count, checksum, methods, and metrics. It does not certify that a method is scientifically accepted.

The only application origin is `https://geophysics.ml.fasl-work.com/`, served by the ML VPS. GitHub Actions validate source and build outputs; they do not publish a second application. The live origin currently serves the legacy `0.04.001` release. The `0.04.003` replacement remains a candidate until scientific, content, application, and host gates pass.
