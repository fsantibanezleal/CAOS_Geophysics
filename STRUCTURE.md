# Inverse Earth Studio structure

The repository has three deliberate lanes:

- `data-pipeline/geophysicslab/` is the offline scientific engine and staged pipeline.
- `frontend/` is the browser workbench. Its compact analytic engine is intentionally low latency and never imports the heavy offline packages.
- `data/derived/` is the replay lane. It contains immutable, seeded artifacts and manifests that the browser and static deployments serve.

## Scientific stages

`pipeline.py` executes the ordered contract: ingest, preprocess, dataset, features, train, infer, evaluate, export, validate. Every case writes a replay artifact, a manifest, and a stage summary. `training.json` records the grouped learning split and held-out losses. `release.json` records the engine inventory and the full stage contract.

## Frontend routes

The shared CAOS shell exposes the Workbench, Introduction, Methodology, Implementation, Experiments, and Benchmark routes. The architecture modal documents the relationship between the browser lane, offline GPU lane, replay artifacts, and two data contracts.

## Data and provenance

Raw downloaded archives remain in ignored `data/downloads/`. The public repository contains compact original synthetic artifacts, checksums in `data/source-ledger.json`, framework cards, and a manuscript source. External course material is cited and not redistributed.

## Deployment

GitHub Actions publishes `frontend/dist` to GitHub Pages. `deploy/deploy.ps1` promotes the same build to the ML VPS with an immutable release directory and an atomic Nginx symlink. No request-time backend or runtime secret is required.
