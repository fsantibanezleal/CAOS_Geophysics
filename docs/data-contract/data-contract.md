# Scientific data contracts · v2

## User observations

UTF-8 CSV headers must be exactly `east_m,north_m,up_m,value,sigma`. At least four unique stations are required. Every value must be finite; sigma must be strictly positive. Duplicate coordinates reject the table; no silent averaging, clipping or outlier deletion occurs. Stations are sorted northing then easting. Coordinates are Cartesian ENU in metres. Gravity is gz, positive upward, in mGal. Magnetics is TMI in nT.

`ingest.py --csv survey.csv --family gravity --output data/raw/result.json` performs sensitivity-weighted L2 and IRLS. Heteroscedastic uncertainty is applied by scaling operator rows and observations before solving. A 14×12×8 mesh is derived from station extent, below the lowest station. Magnetic direction is fixed to 60° inclination / 12° declination, amplitude 50,000 nT; users must explicitly modify this configuration for another field. Terrain masks, regional removal and source separation are not automatic. This path does not claim known truth or field accuracy.

External archives are read member-by-member in memory, never extracted blindly. Checksums must match `data/source-ledger.json`. The source tutorial has four columns; an explicitly assumed 3%-SD uncertainty is added for local experiments. `data/external-preprocessing.json` records row counts, units, source members, hashes and licensing boundaries. Raw values and NPZ derivatives remain ignored.

## Live MT input

The browser accepts JSON `{rho:[...], thickness:[...]}`: 2–8 resistivity values in [1,10000] Ω m; one fewer finite thickness values in [10,2000] m. Invalid shape, range, type or >100 kB files are rejected with a visible error. The last layer is a half-space. Frequencies are positive and logarithmically sampled. No input is uploaded to a server. Export includes model, frequencies, real/imaginary impedance, apparent resistivity and phase.

## Computed experiment

Schema `inverse-earth/v2` includes case identity, family, variant, seed, engine, truth, methods, parameters, runtime and original-synthetic provenance. Potential fields add mesh origin/spacing/centres and a survey with clean/observed values, sigma and active mask. MT adds known thicknesses, frequencies, complex responses and active-frequency mask. Seismics adds initial velocity, shot locations, receiver positions, dt, actual pressure snapshots and shot arrays.

Array order is contractual: volumes flatten x-fast from `[z,northing,easting]`, with z increasing upward; plotted sections reverse z to depth-down. Seismic velocity and pressure are `[depth,distance]`. Gathers are `[shot,receiver,time]`. Column density is `[northing,easting]`. Predictions and residuals refer to final selected models; replay frames are separately labelled.

Each method carries named parameters, model, prediction, residual, recorded objective and states, and metrics. CNN predicts a 2D column, not a 3D model. Autoencoder `model` is normalized squared observation error. Vector magnetic `model` is the component norm, accompanied by vectors.

## Release

`catalog.json` contains 20 cases × 6 variants, relative artifact paths, byte sizes, SHA-256, names and metric summaries. `release.json` counts actual experiments and method results. The guard rejects nonfinite values, duplicate reference truth hashes, missing variants, drifted identities/hashes/sizes, metric mismatches and checkpoint drift. It does not certify scientific adequacy by itself; the numerical and rendered tests are separate gates.

Floats are exported to seven significant digits. Residual closure tests therefore use a scale-aware absolute rounding floor. CNN and autoencoder weights are JSON tensors with explicit shape; the ledger records source seeds, split counts, normalization, best validation loss and every held-out error.
