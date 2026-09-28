# Data and contracts

The public release is built from original seeded synthetic subsurface models. Every case is labelled `synthetic` in its manifest. This gives the pipeline a known truth for numerical validation without implying that a synthetic response is a field interpretation.

Contract 1 accepts station observations with `station_id`, `x_m`, `y_m`, `frequency_hz`, `value`, and `unit`. Supported units are `gravity_mgal`, `magnetic_nT`, `ohm_m`, `phase_deg`, and `trace_amplitude`. Missing fields, non-numeric values, NaN, non-positive frequency, and unknown units are rejected. Extreme finite values are retained and flagged for review.

Contract 2 binds the compact JSON replay artifact to a manifest. The manifest records case, category, method, parameters, seed, artifact path, schema, byte size, measured lane verdict, engine inventory, metrics, and provenance. `scripts/check_artifacts.py` verifies the byte contract before release.

## External sources

The [source ledger](source-ledger.json) is the reviewed allowlist for acquisition. `scripts/fetch-data.ps1` and `scripts/fetch-data.sh` call the same hash/size-verified local downloader for the two SimPEG tutorial archives. A raw asset is immutable under ignored `data/downloads/`, with a write-once receipt under ignored `data/raw/acquisition/`. The pyGIMLi field examples are provider-link-only: no raw file is copied to the public repository while rights remain unresolved. The measured Clear Lake EDI is fetched from its exact provider object or imported locally and screened as a transfer function, not as raw time series or an inverse solution. STEAD metadata is only a provider link with a user-reported, unverified checksum; no waveform or asset is acquired here. Exact commands and rights are in [the source guide](../docs/guides/05_sources.md).

## Formats

Declared source formats in the current ledger are tutorial tar observations, EDI transfer functions, pyGIMLi ERT `.ohm` and refraction `.sgt` files, STEAD metadata CSV (provider link only), plus generated synthetic cases. Only the tar and EDI adapters are active in this foundation. Other modalities require their own metadata and scientific validation before modelling. Browser artifacts use compact JSON arrays with explicit coordinates and units. Heavy raw arrays and virtual environments are ignored; derived release artifacts are small, deterministic, and manifest-backed.
