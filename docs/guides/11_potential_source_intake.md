# Local potential-field source intake

This guide admits **source bytes for inspection**, not a gravity correction chain, inversion, field benchmark or hydrogen interpretation. `modelling_eligible` and `inversion_performed` remain false. Do not promote this profile to canonical cases, solver arrays or public modelling observations. The [research dossier](../research/bartlett-source-review-2026-10-03.md) and [feature contract](../design/features/potential-source-intake/requirements.md) record the reviewed evidence and boundaries; [guide 05](05_sources.md) covers the other reviewed sources.

## Two different source objects

`bartlett-fgdc` is the original USGS FGDC **metadata**, not original observation bytes: [USGS DOI 10.5066/P90F5TGH](https://doi.org/10.5066/P90F5TGH), [retrieved XML](https://data.usgs.gov/datacatalog/metadata/USGS.64188a2ed34eb496d1d1d359.xml). The USGS release is CC0 1.0. ScienceBase attachment requests returned a challenge/403 in the recorded inspection; original `bsf_gravity_data.csv` has not been byte-verified here.

`clear-lake-author-potentials-v2` is Su, Wu, Sun, Wei and Chen (2025), *Joint inversion and integrated geological interpretation for natural hydrogen exploration: code and results*, [Zenodo version 2, DOI 10.5281/zenodo.16975696](https://doi.org/10.5281/zenodo.16975696). Its data rights are **CC BY 4.0**, not USGS CC0 or the repository code's MIT licence. Retain author attribution, version DOI, underlying USGS citations and modification notices. Extraction leaves selected bytes unmodified; profiling is a labelled inspection derivative. Author compilation, coordinate transforms and station-level original-source lineage are not proven equivalent to the original USGS attachments.

The ledger pins the ZIP to 121295137 bytes / SHA-256 `337a2d9070493773af06aee11a19d591e6468ecf0f062dd75c194a04476c0cdf`. The recorded MD5 `7ef5beb984425bf0edabd829cf880187` is supplementary, not the integrity gate. FGDC: 37384 bytes / SHA-256 `84d3d512f9deba53ae0251c74354c389b8723d056375390d2bfebd28c24b8295`.

## Local commands and isolated interpreter

No package is created and no scientific engine is needed: `sources.py` and `potential_sources.py` use Python's standard library. Use Python 3.12 in a local virtualenv. An existing suitable virtualenv may be used **read-only**; intake neither installs dependencies nor modifies that environment. For a new test environment:

```powershell
py -3.12 -m venv .venv-intake
& .venv-intake/Scripts/python.exe -m pip install -r requirements-dev.txt
$env:GEOPHYSICS_INTAKE_PYTHON = (Resolve-Path .venv-intake/Scripts/python.exe).Path
& $env:GEOPHYSICS_INTAKE_PYTHON data-pipeline/acquire.py --source-id clear-lake-author-potentials-v2 --file data/raw/source-research/natural-hydrogen-16975696.zip
./scripts/intake-potential-sources.ps1 -File data/raw/source-research/natural-hydrogen-16975696.zip -Output data/raw/potential-source-intake/gravity-inspection.json
# Optional metadata import is a separate object, not measurement acquisition:
& $env:GEOPHYSICS_INTAKE_PYTHON data-pipeline/acquire.py --source-id bartlett-fgdc --file data/raw/source-research/bartlett-fgdc-20261003.xml
```

```bash
python3.12 -m venv .venv-intake
.venv-intake/bin/python -m pip install -r requirements-dev.txt
export GEOPHYSICS_INTAKE_PYTHON="$PWD/.venv-intake/bin/python"
"$GEOPHYSICS_INTAKE_PYTHON" data-pipeline/acquire.py --source-id clear-lake-author-potentials-v2 --file data/raw/source-research/natural-hydrogen-16975696.zip
bash scripts/intake-potential-sources.sh --file data/raw/source-research/natural-hydrogen-16975696.zip --output data/raw/potential-source-intake/gravity-inspection.json
```

Run from the repository root. Paths may contain spaces; quote them. The paired scripts require a local `--file`/`-File`, a new ignored output path and an isolated interpreter (`--python`/`-PythonPath` overrides the environment). The direct CLI also permits reuse of previously acquired immutable bytes without `--file`; if absent, its ledger-approved fetch path is explicit acquisition, not a CI/test operation. Neither entrypoint accepts arbitrary URLs. The same output path is never overwritten: select a different profile filename on repeated runs. Selected objects and receipts may be reused only when identical.

## Archive safety and local receipts

`archive_contract` is mandatory for research ZIPs and forbidden on other formats. It contains exactly positive bounded `max_entries`, `max_expanded_bytes`, `max_member_bytes`, `max_expansion_ratio` and a nonempty selection mapping. Integer bounds reject booleans, fractional values and excessive limits; ratios reject NaN/infinity. Global ceilings are 512 entries, 500000000 expanded bytes, 200000000 per member and a ratio of 1000. This source's narrower reviewed limits are 64 / 350000000 / 200000000 / 1000.

Every inventory path must be canonical portable ASCII, relative, without traversal, drive syntax, controls, Windows devices, trailing dot/space aliases, case collisions or file/parent collisions. Symlinks, reparse points in storage, special files, encryption, unsupported compression and nonempty directory records fail. The complete inventory is bounded before reading selected content. Only these exact names and their ledger byte/SHA-256 pins are read:

- `data/ground_gravity_data.csv` — 335377 bytes.
- `data/aeromagnetic_data.csv` — 28531313 bytes.
- `data/topography_data.csv` — 193035546 bytes.
- `README.pdf` — 96913 bytes (stored only, not executed or rendered).

Unselected source code, notebooks, saved model text, `.npy` and HDF5 files are inventoried by ZIP headers only, never opened, loaded or executed. No `extractall`, pickle loading, array deserialization or provider code execution occurs. All selected bytes are staged and verified before exclusive hard-link installation. Existing member/receipt disagreements fail before intentional publication; no overwrite occurs. Multi-file publication is not a transactional filesystem operation: an OS failure or competing writer during installation can leave an incomplete set of **verified** members, recoverable by identical retry. Use one intake writer per worktree.

Local paths:

- Archive: `data/downloads/clear-lake-author-potentials-v2.zip`.
- Acquisition receipt: `data/raw/acquisition/clear-lake-author-potentials-v2.json`.
- Four selected members: `data/downloads/extracted/clear-lake-author-potentials-v2/`.
- Member receipt: `data/raw/acquisition/clear-lake-author-potentials-v2-members.json` (complete inventory fingerprint, exact selected hashes, rights and citation).
- Full inspection JSON: your new `data/raw/potential-source-intake/` path.

Both `data/downloads/` and `data/raw/` are ignored; do not force-add them. Only the compact [inspection evidence](../research/potential-source-intake-evidence-2026-10-03.json) is suitable for this scoped commit. Receipt-file SHA-256 means actual on-disk bytes, not a reserialized JSON assumption.

## Principal facts: channel/state contract

The strict header is:

```text
,Station_ID,lonWGS84,latWGS84,xWGS84_UTM10N,yWGS84_UTM10N,zWGS84,OG,FAA,SBA,TTC,CBA,ISO
```

Original index tokens, station IDs, CSV line ends and every numeric channel are retained. Header differences, ragged/empty rows, unknown nonnumeric tokens or excessive size/count fail rather than trigger schema guesses. Blank, `NA`, `N/A`, NaN and infinite numeric values become explicit JSON nulls with row/field/original-token flags, never zero. Duplicate station IDs/finite XYZ are reported, not removed. Range diagnostics flag invalid longitude/latitude, broad UTM easting/northing bounds, terrestrial observed-gravity magnitudes and negative TTC, without asserting these diagnostics establish datum or modelling suitability. Bounds exclude nulls only; no outlier rows are excluded.

| Author field | Preserved meaning in mGal | Intake action |
| --- | --- | --- |
| OG | Observed absolute gravity, provider processing attribution: tide/drift corrections and IGSN1971 base ties already applied | Preserve; never treat as raw instrument readings |
| FAA | Free-air anomaly | Preserve; no new reference/elevation correction |
| SBA | Simple Bouguer anomaly | Preserve; no repeated Bouguer correction |
| TTC | Total terrain correction | Preserve separately; do not add again to CBA |
| CBA | Complete Bouguer anomaly | Preserve; includes provider curvature/terrain processing |
| ISO | Isostatic anomaly | Preserve separately; not an uncorrected observation |

The correction attribution comes from original FGDC processing, **not** independent verification of each author station. USGS metadata describes IGSN1971 bases 980094.15 and 980119.04 mGal, Bouguer/curvature/terrain to 166.7 km at 2670 kg/m³, and Airy compensation with 25 km crust and 400 kg/m³ contrast. No corrections are applied by this intake.

The original metadata labels latitude/longitude **NAD27** and elevation literally `elevation_ft_NVD29`, without a formal `spref` section in the inspected XML. Do not silently repair this label to NGVD29 or infer a vertical datum. The author labels horizontal WGS84 and UTM10N in metres; `zWGS84` does **not** establish ellipsoidal versus orthometric height, source datum or transformation. Therefore reference/elevation reprocessing is ineligible. There is no station-error column: do not fabricate sigma, weights, precision or field uncertainty. Original grain-density metadata requires independent physical review and is not used.

Worked channel distinction, using the actual first author row: OG 979999.22, FAA 22.99, SBA 4.16, TTC 2.76, CBA 6.67, ISO -1.73 mGal; zWGS84 137.03739 m remains datum-unresolved. `CBA - SBA - TTC = -0.25 mGal` is an arithmetic **difference**, not a model residual, uncertainty estimate, correctness proof or full physical closure. It can include provider curvature/rounding/other lineage differences; no decomposition is asserted.

Aeromagnetic/topography CSVs are byte-verified selected objects only in this unit: no grid parser, transform or magnetic modelling claim. The author script's +1000 ft magnetic terrain clearance and replacement of missing interpolated elevations with 1200 m are recorded in research, not adopted as measurement truth or a safe preprocessing policy.

## Named tests and remaining gates

```powershell
& $env:GEOPHYSICS_INTAKE_PYTHON -m pytest tests/data/test_sources.py tests/data/test_potential_sources.py
# Opt-in real gate requires the pinned local archive already imported; it never downloads:
$env:GEOPHYSICS_REAL_POTENTIAL_SOURCE = '1'
& $env:GEOPHYSICS_INTAKE_PYTHON -m pytest tests/data/test_sources.py tests/data/test_potential_sources.py
Remove-Item Env:GEOPHYSICS_REAL_POTENTIAL_SOURCE
```

The named PFI gates cover identity/rights, immutable selected objects, malicious ZIP controls, profile semantics and guide parity; `test_real_local_source_intake` separately checks the genuine archive. Small controls are original test fixtures, not substitute field observations. CI validates metadata/fixtures without external downloads.

Still open: byte-verified original USGS attachments and station-level author transformation lineage; adjudicated vertical datum/height transforms; measured error model; magnetic acquisition-height/grid semantics; scientifically applicable correction-chain admission; independent field forward/inverse controls and the full M01/M02 method acceptance gates. No merge, deployment or full field acceptance follows from intake.
