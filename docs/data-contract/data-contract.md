# Scientific data contracts · v2

Start with [From a source file to a geophysical result](01_source-to-result.md) for the full provenance graph, physical eligibility gates and a reproducible example of the **currently implemented authenticated API**. This page also documents older local CLI and static-catalogue contracts. Those lanes have different inputs and must not be treated as interchangeable online capabilities.

## Source ledger and immutable raw assets

`data/source-ledger.json` (`inverse-earth.sources/v2`) is the local reviewed source allowlist. Each acquirable external SourceRecord has a stable `source_id`, provider and exact provider/object link, acquisition mode, format, expected byte count, lowercase SHA-256, ignored storage key, rights decision and statement, citation and scientific use. `provider-link-only` is a rights verdict that forbids a product-hosted raw mirror; local retrieval for comparison can still be allowed by a separately reviewed `fetch` or `manual` acquisition mode. A distinct `provider-link` acquisition mode denotes catalogue metadata only: reported bytes/hash must be labelled unverified, no raw key exists and the acquisition command rejects it. `derivative-only` permits only the specifically attributed derivative selected for release. Generated original cases have no external raw asset.

`data-pipeline/acquire.py --source-id <id>` selects a reviewed object; `--file <local-file>` imports a manually obtained one. It verifies byte count and hash before installation under ignored `data/downloads/` and refuses to overwrite an existing raw asset. The ignored `data/raw/acquisition/<id>.json` receipt (`inverse-earth.raw-asset/v1`) records `asset_id=sha256:<digest>`, local owner scope, source/provider, original filename, MIME/detected format, bytes, SHA-256, storage key, rights, acquisition method, retrieval time and `hash-verified` status. A changed source or receipt fails. The local owner scope is not an API user/project ownership claim; the authenticated service has a separate owner/project binding. See the [source acquisition guide](../guides/05_sources.md) for the eight entries and exact commands. The STEAD metadata index is only a provider link with user-reported bytes/hash, not a receipt or a waveform asset; the separately owned M13 phase must verify its own data and rights before processing or publication.

## Legacy local CLI observations (not authenticated API input)

The following five-column CSV and `ingest.py` workflow belong to the local potential-field CLI. The authenticated API currently accepts a different, six-column gravity station contract with an explicit sigma declaration and only a flag-only QC method; see [the processing-job guide](../guides/07_processing_jobs.md). Passing the CLI contract does not create an API observation dataset.

UTF-8 CSV headers must be exactly `east_m,north_m,up_m,value,sigma`. At least four unique stations are required. Every value must be finite; sigma must be strictly positive. Duplicate coordinates reject the table; no silent averaging, clipping or outlier deletion occurs. Stations are sorted northing then easting. Coordinates are Cartesian ENU in metres. Gravity is gz, positive upward, in mGal. Magnetics is TMI in nT.

`ingest.py --csv survey.csv --family gravity --output data/raw/result.json` performs noise-weighted spatial L2 and L1/L2 IRLS. The inverse scales operator rows by uncertainty and selects the tradeoff by discrepancy. A 14×12×8 mesh is derived from station extent, below the lowest station. Magnetic direction is fixed to 60° inclination / 12° declination, amplitude 50,000 nT; users must explicitly modify this configuration for another field. Terrain masks, regional removal and source separation are not automatic. This path does not claim known truth or field accuracy.

`ingest.py --external` selects only reviewed fetchable SimPEG tar archives. It does not try EDI or provider-link-only manual sources. Archive metadata is checked for traversal, links, member count, size and expansion before one `_data.obs` member is read in memory. The synthetic tutorial member has four XYZ/value columns in a local Cartesian metre frame, with no declared geographic CRS or instrument error. The adapter requires finite unique stations and assigns `max(3% × observation SD, 1e-12)` as an explicitly assumed sigma for local experimentation. Values beyond six scaled MAD are flagged, never dropped or silently reweighted. Ignored `data/raw/processed/<source_id>/<raw-sha>.npz` and its `inverse-earth.local-preprocessing/v2` receipt retain source/member hash, units, row count, uncertainty/outlier rule and derivative hash. `data/external-preprocessing.json` is a historical release comparison receipt and is not rewritten. Neither raw nor local preprocessing values are committed while redistribution terms are unresolved.

Selected EDI is dispatched to the strict transfer-function screen, with explicit units, variance and rotation arguments. The pinned measured Clear Lake `cl061` source has 42 frequencies and fails the necessary isotropic-1D eligibility check; this path emits QC metadata only, not an inverse or new public artifact. EDI is not a raw EM time series. The pyGIMLi Slagdump `.ohm` and Koenigsee `.sgt` entries are SHA-256-pinned provider links with local-only raw imports and no validated observation adapter in this unit. Their ERT electrodes/resistances and refraction picks require distinct modality contracts before modelling; neither is a waveform. Unknown formats receive an explicit unsupported verdict, not a guessed interpretation.

The separate M06 `auslamp-nsw-c15` EDI is a measured 35-frequency transfer function with source and two provider-JSON SHA-256 pins. Its `manual` acquisition is immutable and ignored. `mt_field_qc.py`, not the general EDI ingestion adapter, checks AusMT's remote-reference dialect against `mt-metadata`, verifies frame and original errors, and writes local `inverse-earth/m06-field-admission/v1` JSON plus a SHA-256 sidecar under ignored `data/raw/mt/`. That schema carries full-period complex-tensor and phase-tensor diagnostics, upstream screening attribution, `status=ineligible`, `one_d_inversion_eligible=false`, `inversion_performed=false`, `methods={}`, `predicted:null`, `heldout_metrics:null` and `truth:null`. This receipt is **not** a public `inverse-earth/edi-screen/v1` artifact or a layered inverse. Its [method chapter](../problem-types/mt-field-admission.md) documents the source search, error convention, 1D gate, measured scores and reproduction.

## Browser layered-MT calculator and local EDI input

EDI ingestion and inversion are a separate local path in `edi.py`. Units, signs,
tensor axes and uncertainty conventions are validated before inversion. Generic
`inverse-earth/edi-1d/v1` retains `truth:null`; original fixture truths are labelled
separately at `data/derived/v2/edi/manifest.json`. See [the EDI contract](../problem-types/mt-recovery.md).
The separate `inverse-earth/edi-screen/v1` measured-station artifact contains
observed full-tensor curves, uncertainties, parser provenance and the necessary
1D-consistency screen. It has `truth:null`, `methods:{}` and
`inversion_performed:false`; a failed screen is never converted into a layered
model. The manifest's `field_screens` entry carries its hash and source citation.

The static browser calculator accepts JSON `{rho:[...], thickness:[...]}`: 2–8 resistivity values in [1,10000] Ω m; one fewer finite thickness values in [10,2000] m. Invalid shape, range, type or >100 kB files are rejected with a visible error. The last layer is a half-space. Frequencies are positive and logarithmically sampled. No input is uploaded to a server. Export includes model, frequencies, real/imaginary impedance, apparent resistivity and phase. This forward calculator does **not** parse uploaded EDI or invert a field station.

## Computed experiment

Schema `inverse-earth/v2` includes case identity, family, variant, seed, engine, truth, methods, parameters, runtime and original-synthetic provenance. Potential fields add mesh origin/spacing/centres and a survey with clean/observed values, sigma and active mask. MT adds known thicknesses, frequencies, complex responses and active-frequency mask. Seismics adds initial velocity, shot locations, receiver positions, dt, actual pressure snapshots and shot arrays.

Array order is contractual: volumes flatten x-fast from `[z,northing,easting]`, with z increasing upward; plotted sections reverse z to depth-down. Seismic velocity and pressure are `[depth,distance]`. Gathers are `[shot,receiver,time]`. Column density is `[northing,easting]`. Predictions and residuals refer to final selected models; replay frames are separately labelled.

Each method carries named parameters, model, prediction, residual, recorded objective and states, and metrics. CNN predicts a 2D column, not a 3D model. Autoencoder `model` is normalized squared error against its actual network input; on the coverage variant that input is an interpolated station map, and a separate `raw_observation_mse` is supplied. The case threshold flag is not a calibrated geological verdict. Vector magnetic `model` is the component norm, accompanied by vectors.

Recovery adds `target`, `evaluation.status/reason_codes`, `state_identity`, `solver`,
optional conditional `uncertainty`, and optional `applicability`. The final replay
frame equals the selected model. Predictions refer to that final model even during
earlier-state replay. Joint outputs add `magnetic_model`; PGI adds cell-by-class
`prior_membership` and fitted `petrophysical_prior`. Frozen neural checkpoints mark
the classical regularization condition as not an intervention on the network.

## Release

`catalog.json` contains 20 cases × 6 variants, relative artifact paths, byte sizes, SHA-256, names and metric summaries. `release.json` counts actual experiments and method results. The guard rejects nonfinite values, duplicate reference truth hashes, missing variants, drifted identities/hashes/sizes, metric mismatches and checkpoint drift. It does not certify scientific adequacy by itself; the numerical and rendered tests are separate gates.

Both manifests require `complete:true` for promotion. Family-specific source/settings
fingerprints reject stale resumed runs. A release may reuse an unchanged earlier
run only when its original version and scientific-source fingerprint still match;
the run retains its generation version rather than claiming a new solve.
Catalogue verdicts exactly match per-run
evaluations. The EDI bundle has separate hashes; it is not counted as another
known-truth canonical geophysical case.

Floats are exported to seven significant digits. Residual closure tests therefore use a scale-aware absolute rounding floor. CNN and autoencoder weights are JSON tensors with explicit shape; the ledger records source seeds, split counts, normalization, best validation loss and every held-out error.
