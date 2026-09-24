# Inverse Earth Studio structure

The repository has three deliberate lanes:

- `data-pipeline/` contains plain numerical scripts, invoked by path.
- `frontend/` renders the canonical arrays and provides an independently parity-tested live MT calculator.
- `data/derived/v2/` contains original experiments, the hashed catalogue and learned checkpoints.

## Scientific stages

`rebuild.py` constructs geology, configures acquisition, solves physics, perturbs and masks observations, inverts, evaluates and exports. The learned branch additionally generates disjoint training/validation/test realizations. `ingest.py` handles external and user observations separately. `models/training.json` records learned splits, checkpoints and evaluation; `release.json` records actual counts and engines.

## Frontend routes

The shared CAOS shell exposes the Workbench, Introduction, Methodology, Implementation, Experiments, and Benchmark routes. The architecture modal documents the relationship between the browser lane, offline GPU lane, replay artifacts, and two data contracts.

## Data and provenance

Raw downloaded archives remain in ignored `data/downloads/`. The public repository contains compact original synthetic artifacts, checksums in `data/source-ledger.json`, framework cards, and a manuscript source. External course material is cited and not redistributed.

## Deployment

GitHub Actions publishes `frontend/dist` to GitHub Pages. `deploy/deploy.ps1` promotes the same build to the ML VPS with an immutable release directory and an atomic Nginx symlink. No request-time backend or runtime secret is required.
