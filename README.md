# Inverse Earth Studio

Public release: [GitHub Pages](https://fsantibanezleal.github.io/CAOS_Geophysics/) · [ML mirror](https://geophysics.ml.fasl-work.com)

Inverse Earth Studio is a research-grade interactive workbench for visual and didactic geophysics. It keeps a selected subsurface case, the physical observation, the inferred model, the residual, and identifiability evidence in one linked surface. The initial release covers potential fields, layered magnetotellurics, acoustic full-waveform inversion, learned spatial priors, joint cross-gradient diagnostics, and reproducible uncertainty views.

## Why it exists

Geophysical inversion is underdetermined. Different density, susceptibility, conductivity, or velocity models can produce similar observations. This project makes that relationship inspectable: move contrast, depth, noise, field angle, frequency, and regularization context; then read the changed field, profile, residual, and uncertainty at the pointer. Every canonical case is synthetic and labelled, so a result is auditable rather than presented as field truth.

## Impact and value

- Researchers can compare physics families with the same case and explicit assumptions.
- Students can connect equations to observations and failure modes through animated, value-reading views.
- Method developers can reproduce the staged bake, inspect metrics, and bring a new CSV or EDI table through the input contract.
- Reviewers can trace public numbers to a seed, manifest, artifact, engine inventory, and source ledger.

## What is included

- 20 configurable cases across potential fields, electromagnetics, seismic, joint inversion, and learned methods.
- Gravity and magnetics forward maps with density or susceptibility fields, field direction, profiles, residual context, and compact regularization evidence.
- Layered-earth MT impedance recursion with apparent resistivity, phase, thickness, and differentiable physics-guided loss context.
- Finite-difference acoustic shot and update artifacts with frequency and cycle-skipping explanations.
- Learned CNN-prior and autoencoder-novelty tools with held-out split language and no fabricated headline accuracy.
- Joint cross-gradient structure comparison and an uncertainty layer that grows with depth and noise.
- Nine named stages: ingest, preprocess, grouped split, features, train, infer, evaluate, export, validate.
- Two enforced data contracts, deterministic manifests, source ledger, GPU capability record, docs wiki, manuscript source, and CI guards.

## Quick start on Windows

Run scripts/setup.ps1, scripts/fetch-data.ps1, and scripts/precompute.ps1 from PowerShell. Then run .venv-pipeline/Scripts/python.exe -m pytest, change to frontend, run npm install, and run npm run build or npm run dev.

Use scripts/setup.ps1 -Gpu to add the official CUDA PyTorch wheel on the local RTX workstation. The ML VPS is CPU-only and serves the checked static build. Git Bash equivalents are available as scripts/setup.sh, scripts/fetch-data.sh, scripts/precompute.sh, and scripts/local.sh.

## Scientific boundary

The web lane is a compact analytic mirror designed for low-latency interaction. The offline lane is the canonical numerical bake and is where solver-backed SimPEG, Choclo, MTpy, PyTorch, Devito, and Deepwave integrations are checked when installed. The app does not claim that a synthetic result is a field interpretation, that a scalar magnetic inversion resolves remanence, or that a compact acoustic example is a production elastic FWI survey.

## Repository map

data-pipeline/geophysicslab/ contains typed contracts, models, and the staged bake. data/derived/ contains compact public replay artifacts and manifests. frontend/ contains the shared-shell SPA and linked visualizations. docs/ contains theory, framework, contract, case, and run guides. manuscripts/ contains research manuscript source and evidence notes. scripts/ contains PowerShell and Bash reproducibility commands. tests/ contains contracts, physics, determinism, and lane gates.

## Documentation and citations

Start with [the docs wiki](docs/README.md), [architecture](docs/architecture/architecture.md), [theory](docs/problem-types/problem-types.md), [framework cards](docs/frameworks/frameworks.md), and [the data contract](docs/data-contract/data-contract.md). The research review that motivated the implementation is persisted in the private coordination workspace; this public repository contains only public-safe technical documentation and source links.

Key references include SimPEG ([Cockett et al.](https://doi.org/10.1016/j.cageo.2015.09.015)), the electromagnetic framework ([Heagy et al.](https://doi.org/10.1016/j.cageo.2017.06.018)), FWI ([Virieux and Operto](https://doi.org/10.1190/1.3238367)), and the OpenFWI benchmark ([repository](https://github.com/lanl/OpenFWI)).

## License

Code is Apache-2.0. Original explanatory content and synthetic replay data are CC-BY-4.0. External archives are downloaded only to ignored local storage pending license review and are not silently redistributed.
