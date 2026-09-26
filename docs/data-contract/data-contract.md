# Scientific data contracts · v2

## User observations

UTF-8 CSV headers must be exactly `east_m,north_m,up_m,value,sigma`. At least four unique stations are required. Every value must be finite; sigma must be strictly positive. Duplicate coordinates reject the table; no silent averaging, clipping or outlier deletion occurs. Stations are sorted northing then easting. Coordinates are Cartesian ENU in metres. Gravity is gz, positive upward, in mGal. Magnetics is TMI in nT.

`ingest.py --csv survey.csv --family gravity --output data/raw/result.json` performs noise-weighted spatial L2 and L1/L2 IRLS. The inverse scales operator rows by uncertainty and selects the tradeoff by discrepancy. A 14×12×8 mesh is derived from station extent, below the lowest station. Magnetic direction is fixed to 60° inclination / 12° declination, amplitude 50,000 nT; users must explicitly modify this configuration for another field. Terrain masks, regional removal and source separation are not automatic. This path does not claim known truth or field accuracy.

External archives are read member-by-member in memory, never extracted blindly. Checksums must match `data/source-ledger.json`. The source tutorial has four columns; an explicitly assumed 3%-SD uncertainty is added for local experiments. `data/external-preprocessing.json` records row counts, units, source members, hashes and licensing boundaries. Raw values and NPZ derivatives remain ignored.

## Live MT input

EDI ingestion and inversion are a separate local path in `edi.py`. Units, signs,
tensor axes and uncertainty conventions are validated before inversion. Generic
`inverse-earth/edi-1d/v1` retains `truth:null`; original fixture truths are labelled
separately at `data/derived/v2/edi/manifest.json`. See [the EDI contract](../problem-types/mt-recovery.md).

The browser accepts JSON `{rho:[...], thickness:[...]}`: 2–8 resistivity values in [1,10000] Ω m; one fewer finite thickness values in [10,2000] m. Invalid shape, range, type or >100 kB files are rejected with a visible error. The last layer is a half-space. Frequencies are positive and logarithmically sampled. No input is uploaded to a server. Export includes model, frequencies, real/imaginary impedance, apparent resistivity and phase.

## Computed experiment

Schema `inverse-earth/v2` includes case identity, family, variant, seed, engine, truth, methods, parameters, runtime and original-synthetic provenance. Potential fields add mesh origin/spacing/centres and a survey with clean/observed values, sigma and active mask. MT adds known thicknesses, frequencies, complex responses and active-frequency mask. Seismics adds initial velocity, shot locations, receiver positions, dt, actual pressure snapshots and shot arrays.

Array order is contractual: volumes flatten x-fast from `[z,northing,easting]`, with z increasing upward; plotted sections reverse z to depth-down. Seismic velocity and pressure are `[depth,distance]`. Gathers are `[shot,receiver,time]`. Column density is `[northing,easting]`. Predictions and residuals refer to final selected models; replay frames are separately labelled.

Each method carries named parameters, model, prediction, residual, recorded objective and states, and metrics. CNN predicts a 2D column, not a 3D model. Autoencoder `model` is normalized squared observation error. Vector magnetic `model` is the component norm, accompanied by vectors.

Recovery adds `target`, `evaluation.status/reason_codes`, `state_identity`, `solver`,
optional conditional `uncertainty`, and optional `applicability`. The final replay
frame equals the selected model. Predictions refer to that final model even during
earlier-state replay. Joint outputs add `magnetic_model`; PGI adds cell-by-class
`prior_membership` and fitted `petrophysical_prior`. Frozen neural checkpoints mark
the classical regularization condition as not an intervention on the network.

## Release

`catalog.json` contains 20 cases × 6 variants, relative artifact paths, byte sizes, SHA-256, names and metric summaries. `release.json` counts actual experiments and method results. The guard rejects nonfinite values, duplicate reference truth hashes, missing variants, drifted identities/hashes/sizes, metric mismatches and checkpoint drift. It does not certify scientific adequacy by itself; the numerical and rendered tests are separate gates.

Both manifests require `complete:true` for promotion. Family-specific source/settings
fingerprints reject stale resumed runs. Catalogue verdicts exactly match per-run
evaluations. The EDI bundle has separate hashes; it is not counted as another
known-truth canonical geophysical case.

Floats are exported to seven significant digits. Residual closure tests therefore use a scale-aware absolute rounding floor. CNN and autoencoder weights are JSON tensors with explicit shape; the ledger records source seeds, split counts, normalization, best validation loss and every held-out error.
