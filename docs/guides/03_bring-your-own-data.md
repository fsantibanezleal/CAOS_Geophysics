# Bring another dataset

1. Preserve the source URL, fetch date, license, and SHA-256 hash.
2. Convert the table to station_id, x_m, y_m, frequency_hz, value, and unit.
3. Run the Contract 1 validator and inspect rejected and flagged rows.
4. Fit preprocessing state on the training group only.
5. Keep stations or physical cases grouped when creating train, validation, and held-out sets.
6. Export a replay artifact only after its manifest and byte size validate.

For EDI, MTpy-v2 is the recommended parsing boundary. For large arrays, keep the raw file local and publish only a compact derived artifact when terms allow it.
