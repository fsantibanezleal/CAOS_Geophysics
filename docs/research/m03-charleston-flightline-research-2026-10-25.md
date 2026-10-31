# M03 Charleston airborne magnetic lines: verified intake record

Date checked: 2026-10-25. Scope: primary-source facts and accessible metadata for the approved M03 flight-line processing case. This is not an implementation or acceptance receipt.

## Candidate and rights

The USGS 2019 Charleston airborne magnetic and radiometric release is the selected candidate (Shah, DOI [10.5066/P9EWQ08L](https://doi.org/10.5066/P9EWQ08L)). USGS identifies CC0 1.0 for the release. Its stated purpose includes imaging crystalline basement structures in the Charleston seismic zone and critical-mineral placer deposits. USGS reports a 134 km by 90 km survey area, NW–SE flight lines at nominal 400 m spacing, NE–SW tie lines at 4,000 m spacing, mean terrain clearance of 127 m, May–July 2019 acquisition, and 32,447 line-km. These are metadata statements, not measured coverage or instrument-QC results.

The USGS magnetic child record describes the published CSV as **processed horizontal magnetic gradiometry flight-line data** and a GeoTIFF, not unprocessed magnetometer samples. The child FGDC metadata names `Charleston_MagneticFlightLineData.csv` and `DataDictionary_CharlestonMagnetic.csv`; it identifies `USGS-South Carolina-Geophysical Airborne Survey Report.pdf` as the contractor-report reference. It says the parent ScienceBase item holds downloadable files. Thus the CSV may support flight/tie-line organization, height/QC, gridding and comparison with the provider product, but it must not be presented as a raw-to-corrected processing demonstration until the data dictionary/report and processing lineage confirm which corrections are already applied.

## Retrieved and retained evidence

The official USGS metadata XML files are stored in the device data root under `CAOS_Geophysics/data/downloads/usgs-charleston-2019/` (outside Git):

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `magnetic-flight-line-metadata.xml` | 17,806 | `badd712ff0e169bd62ed70b34ce273ef9bea4b4ec7a206627b09eac55a98a1c2` |
| `parent-release-metadata.xml` | 16,902 | `dd9aa31c9c3635bf715bd98aad1bb72aebde903ec05ff334b622e3c406036c71` |

The child metadata was retrieved from `https://data.usgs.gov/datacatalog/metadata/USGS.5f4da2c182ce4c3d1231922e.xml`; the parent metadata was retrieved from `https://data.usgs.gov/datacatalog/metadata/USGS.5f247e3082cef313ed972534.xml`. Both requests returned HTTP 200. The catalog's child and parent HTML records also return HTTP 200 (499,324 and 499,586 bytes respectively), but the child page only exposes a “Get Data and Metadata” link to the DOI. The official USGS identifier API paths `https://www1.usgs.gov/pir/api/identifiers/USGS:5f4da2c182ce4c3d1231922e` and `https://www1.usgs.gov/pir/api/identifiers/USGS:5f247e3082cef313ed972534` return the same child and parent XML metadata, not attachment payloads. On 2026-10-25, direct requests to the DOI, ScienceBase parent and child item pages, documented `?format=json` forms, item search, and parent/child catalog file endpoints returned HTTP 403. Official USGS ScienceBase documentation confirms item JSON and REST access are supported, but these routes are not reachable from this environment. The large CSV, data dictionary, contractor report, and full-resolution magnetic grid have therefore **not** been retrieved, hashed, or independently parsed. The prior SDD's approximately 2.58 GB estimate is metadata-scale planning only; it is not a measured downloaded size.

The USGS landing page and the Science Data Catalog child record are the authority for the facts above: [USGS release page](https://www.usgs.gov/data/airborne-magnetic-and-radiometric-survey-charleston-south-carolina-and-surrounds-2019), [USGS child record](https://data.usgs.gov/datacatalog/data/USGS%3A5f4da2c182ce4c3d1231922e), and [Shah et al., 2021, *GSA Today*, DOI 10.1130/GSATG512A.1](https://doi.org/10.1130/GSATG512A.1). The official USGS description confirms acquisition geometry and the published deliverable types; it does not, by itself, establish tie-line residuals, height correction, gridding error, or equivalence with the provider grid.

## Scientific acceptance still required

1. Retrieve the exact CSV, dictionary, contractor report and provider grid from the parent data release; save original bytes outside Git and record URL, byte count and SHA-256 before parsing.
2. Map the data dictionary's field IDs, line IDs, coordinates, sensor/terrain heights, total field/anomaly, horizontal gradients, units, CRS/datum and sentinel values. Reject missing or ambiguous quantities; never infer correction state from a column name alone.
3. Reconcile the report's acquisition and correction sequence. Preserve original values and all producer-supplied processed values; do not reapply diurnal/IGRF/leveling/corrections already included.
4. Measure flight/tie geometry, spacing, altitude distribution, repeated IDs, gaps, duplicate coordinates, crossovers and line-wise residuals. Report anomalies as diagnostics, not silently corrected observations.
5. Freeze a spatially blocked line holdout before any levelling/gridding choice. Fit any tie-line leveling only on training intersections; score withheld flight-line samples and separately compare to the provider grid with declared interpolation/support masks.
6. Grid irregular line samples with a documented operator and uncertainty/support layer; show line-only versus grid results and upward continuation only where the sampled-grid geometry and boundary/aliasing checks support it. Do not manufacture between-line resolution.
7. Record the exact CLI, settings, source/rights receipt, split hash, outputs, independent numerical checks and limitations in a full M03 feature SDD and acceptance record before publishing the case.

No M03 parser, correction, gridding, continuation, holdout or user-data acceptance is claimed by this intake record.

## Access refresh: 2026-10-27

The two official ISO metadata records were fetched again from the USGS Science Data Catalog and saved outside Git under the configured CAOS working-data root at `data/downloads/usgs-charleston-2019/`. Their bytes and SHA-256 values match the prior recorded XML: child metadata 17,806 bytes (`badd712ff0e169bd62ed70b34ce273ef9bea4b4ec7a206627b09eac55a98a1c2`), parent metadata 16,902 bytes (`dd9aa31c9c3635bf715bd98aad1bb72aebde903ec05ff334b622e3c406036c71`). The metadata names the CSV and data dictionary, and describes the CSV as processed horizontal magnetic gradiometry line data.

The live ScienceBase JSON item (`https://www.sciencebase.gov/catalog/item/5f4da2c182ce4c3d1231922e?format=json`) still returns HTTP 403 from this environment. The official DOI landing page confirms that flight-line CSVs, GeoTIFFs, and the contractor report are release products, but its accessible page does not expose direct asset URLs. The CSV, dictionary, report, and magnetic grid therefore remain unacquired and unhashed; the M03 processing component and synthetic continuation control are not provider-data validation. The source remains an external-data dependency, not permission to substitute the provider grid or authored controls for flight-line evidence.
