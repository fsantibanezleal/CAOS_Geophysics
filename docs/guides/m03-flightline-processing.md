# Process a mapped airborne magnetic line survey (M03)

This local workflow performs source-aware line and sensor-height QC, reserves a contiguous block of complete flight lines, evaluates spatial interpolation on that holdout, and writes a masked grid. It does not upload the source file, solve a subsurface inverse problem, or apply magnetic corrections.

## 1. Prepare the source and mapping

Keep the original CSV unchanged. Record its citation, usage rights, provider-declared processing state, magnetic quantity and unit. The code does not infer whether a value is total field, anomaly, a horizontal derivative, or already levelled. Use projected coordinates in metres with a named projected CRS; angular longitude/latitude is rejected. Declare whether sensor height is above-ground or referenced to a vertical datum.

Create a JSON config using the exact headers in the CSV:

```json
{
  "source": {
    "source_id": "your-survey-id",
    "citation": "Replace with the full source citation",
    "rights_decision": "Replace with a reviewed rights decision",
    "processing_state": "State the provider corrections and unknowns",
    "value_quantity": "total-field anomaly",
    "value_unit": "nT",
    "sensor_height_reference": "above-ground"
  },
  "frame": {
    "crs": "Replace with the verified projected CRS",
    "coordinates_are_projected": true,
    "linear_unit": "m"
  },
  "mapping": {
    "easting": "EASTING",
    "northing": "NORTHING",
    "value": "MAGNETIC_VALUE",
    "line_id": "LINE_ID",
    "line_role": "LINE_TYPE",
    "sensor_height_m": "SENSOR_HEIGHT_M"
  },
  "settings": {
    "grid_spacing_m": 100,
    "holdout_fraction": 0.2,
    "seed": "survey-name-and-version"
  }
}
```

Replace every example header and CRS with values verified from the actual survey documentation. The example is a schema illustration, not a claim about any particular survey.

## 2. Run locally

```powershell
.venv-pipeline\Scripts\python.exe data-pipeline\magnetic_processing.py `
  --csv path\to\original-flight-lines.csv `
  --config path\to\mapping.json `
  --output path\to\new-result.json
```

The CLI refuses to overwrite an existing result. It prints the output byte count and SHA-256. It accepts CSVs up to 256 MiB and 250,000 rows; a grid is limited to 250,000 cells. It requires NumPy and SciPy from the pinned offline environment.

## 3. Read the result correctly

`geometry_qc.lines` contains line counts, extents and sensor-height minimum/median/maximum/MAD plus outlier row indices. The outlier rule is six scaled MAD; it is a screening flag, not calibrated instrument uncertainty. No row is removed. Exact coincident samples from different lines are counted and their value differences summarized; this does not estimate near-crossing tie residuals.

`split` lists complete fit and held-out flight-line IDs. A contiguous interior line block is selected deterministically along the estimated line-normal direction. Tie lines are excluded from fitting. `heldout_interpolation` reports supported sample count, coverage, MAE and RMSE. `grid` stores axes in metres, values, a `[northing, easting]` array shape, and a support mask. Values outside the training convex hull are encoded as zero only where the mask is false.

These values interpolate observations at their recorded sensor heights. They are not upward-continued to a common plane. A small held-out error only shows that this interpolation predicted those measured samples; it is not evidence of a uniquely recovered subsurface model.

## 4. Not yet provided by this workflow

It does not estimate geometric line intersections, tie-line levelling, diurnal/IGRF/lag/height corrections, regional fields or upward continuation. It does not compare against a provider grid or prove the source processing history. Do not feed a provider-processed dataset into a raw correction chain. Charleston-specific validation remains pending until its provider CSV, dictionary, contractor report and comparison grid are retrieved and hashed; see [the source research record](../research/m03-charleston-flightline-research-2026-10-25.md).
