# Data contract

## Contract 1: ingestion

The accepted record has station_id, x_m, y_m, frequency_hz, value, and unit. Coordinates are metres, frequency is hertz, and value uses an explicit unit. The unit must be one of gravity_mgal, magnetic_nT, ohm_m, phase_deg, or trace_amplitude. Rows with missing keys, non-numeric values, NaN, non-positive frequency, or unknown units are rejected. Extreme finite values are accepted with a review flag rather than silently clipped.

## Contract 2: replay

The replay artifact has schema inverse-earth.replay/v1, case identity, category, method, seed, coordinates, fields, observations, residuals, metrics, and uncertainty. The manifest binds the artifact path and exact byte size. A release is invalid if the index, manifest, or artifact disagree.

## Bringing other data

Convert a CSV or EDI-derived table to the six required fields, preserve the original file hash and source license in a ledger, then run the contract validator before preprocessing. Keep source data outside the public repository when redistribution is not explicit. A new case should be grouped as held-out at the model level, not split by neighbouring samples.

References: [MTpy-v2](https://mtpy-v2.readthedocs.io/en/stable/index.html), [MTH5](https://doi.org/10.1016/j.cageo.2022.105102).
