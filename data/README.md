# Data and contracts

The public release is built from original seeded synthetic subsurface models. Every case is labelled `synthetic` in its manifest. This gives the pipeline a known truth for numerical validation without implying that a synthetic response is a field interpretation.

Contract 1 accepts station observations with `station_id`, `x_m`, `y_m`, `frequency_hz`, `value`, and `unit`. Supported units are `gravity_mgal`, `magnetic_nT`, `ohm_m`, `phase_deg`, and `trace_amplitude`. Missing fields, non-numeric values, NaN, non-positive frequency, and unknown units are rejected. Extreme finite values are retained and flagged for review.

Contract 2 binds the compact JSON replay artifact to a manifest. The manifest records case, category, method, parameters, seed, artifact path, schema, byte size, measured lane verdict, engine inventory, metrics, and provenance. `scripts/check_artifacts.py` verifies the byte contract before release.

## External sources

`scripts/fetch-data.ps1` and `scripts/fetch-data.sh` download public SimPEG tutorial archives into ignored `data/downloads/` for local comparison and parser development. They are not copied into the public artifact tree until their redistribution terms are confirmed. The source ledger records the URLs and SHA-256 hashes generated locally. The committed replay suite remains original synthetic content.

## Formats

Raw source formats may include CSV, EDI, NumPy, VTK, and HDF5 in the offline lane. Browser artifacts use compact JSON arrays with explicit coordinates and units. Heavy raw arrays and virtual environments are ignored; derived release artifacts are small, deterministic, and manifest-backed.
