# BAS SPARC Northern Palmer Land magnetic line case

## Source and rights

The source is the British Antarctic Survey / UK Polar Data Centre record
[GB/NERC/BAS/PDC/01358](https://data.bas.ac.uk/full-record.php?id=GB/NERC/BAS/PDC/01358),
dataset DOI [10.5285/5c87409e-fdfd-4732-ad19-9d319a0e5a2b](https://doi.org/10.5285/5c87409e-fdfd-4732-ad19-9d319a0e5a2b).
Ferraccioli and Jones (2020) distribute one ASCII XYZ archive under the UK Open
Government Licence v3. The required dataset citation and the provider's
no-warranty notice are retained in the source ledger and local acquisition
receipt. The exact archive used here is 69,305,816 bytes with SHA-256
`db63cf49dada843676429376f1991f2531c37eab8007f1da2feeb22b3b7943f8`.

The provider describes more than 20,000 line-km, E-W profiles, N-S ties, nominal
5 km profile spacing, 25 km tie spacing and nominal 2,800 m flight altitude.
The archive spans 26 December 2002 through 20 January 2003. The channels include
raw `MagR`, compensated/corrected intermediates, statistically levelled `MagL`
and microlevelled `MagML`. The published lineage already includes magnetic
compensation, IGRF removal, diurnal correction and levelling. Crucially,
`MagML` contains no tie-line observations. This product does not repeat those
provider corrections or infer missing channel values.

The provider's coordinate metadata calls the frame Polar stereographic and
lists latitude of natural origin -71, longitude 0, a field labelled scale
factor `-75.33333333333`, false easting 0 m, and false northing 2,082,760.109 m.
The scale-factor entry is ambiguous as published. The adapter preserves the
values verbatim, uses the provided planar x/y metres for local geometry, assigns
no EPSG code and performs no reprojection.

## Parser, inventory and geometry

`data-pipeline/sparc_magnetic.py` recognizes the provider's `Line`, `Tie`,
`Random` and `Special` markers, verifies each numeric record belongs to the
active marker, parses all 21 columns and rejects malformed/nonfinite values.
The pinned source is streamed into a row inventory with source-line and
numeric-record indices, marker type, raw token record and missing-value
channels. The source bytes remain external and immutable. Processing tables
preserve their source record indices and are new, hash-recorded derivatives.

The archive contains 209,370 numeric records; the generated inventory retains
all of them. It classifies 42 empty marker headers and 289 coordinate-incomplete
records rather than silently dropping them. Of the coordinate-bearing line
groups, geometry-only orientation clustering finds 69 profile-axis groups and
18 near-orthogonal tie-axis groups (axis separation 89.927 degrees; largest
within-axis deviation 5.694 degrees). This agrees with the explicit `Line`
(67 profiles) and `Tie` (12 ties) markers; four `Random` markers fall on the tie
axis, and four `Special` lines split two per axis. No magnetic values enter this
classification. The 2-axis partition is a source-specific inference supported
by the official survey design and the provider markers; it is retained in the
manifest for review.

The parser writes separate M03 inputs:

- `magl-flight-and-tie.csv`: 201,749 complete MagL rows, with flight/tie roles.
- `magml-flight-profiles.csv`: 162,098 complete MagML profile rows; zero ties.
- `magl-common-profile-rows.csv`: the same 162,098 source rows as MagML, carrying
  MagL values so the two channels can be compared on identical line blocks.

No data are uploaded or copied into the repository. See the [source-acquisition
guide](../guides/05_sources.md#bas-sparc-northern-palmer-land-line-data) and
[`data/source-ledger.json`](../../data/source-ledger.json).

## M03 processing evidence

The M03 crossover checker uses an x-sorted sweep over line-segment bounding
boxes, then applies the exact segment-intersection predicate. It counts only
opposite-role XY-envelope overlaps against the unchanged two-million candidate
cap; disjoint envelopes cannot intersect. On the full MagL flight/tie table,
the run checks 1,236 candidate pairs and finds 648 geometric intersections.
Linear interpolation at those points yields mean signed difference -0.824 nT,
MAE 3.311 nT and RMSE 36.780 nT. The relatively large RMSE indicates a
heavy-tailed crossing residual distribution. The interpolated sensor-height
difference has median absolute magnitude 36.63 m, 90th percentile 787.73 m,
and maximum 1,464.10 m; the absolute field-difference median is 0.00716 nT,
the 95th percentile is 1.516 nT, and the maximum is 784.798 nT. The paired
quantities are retained per intersection and shown together in the M03 result
view. The wide height variation makes it unsafe to interpret the uncorrected
field mismatch as a leveling error: the pipeline does not apply an altitude
correction or model a magnetic gradient. The 98% central view is explicitly
zoomed and reports how many points fall outside its axes; point tooltips retain
the original values. This table is MagL, before the
provider's microlevelled channel. It is not comparable to the provider's
reported mean crossover error below 1 nT after microlevelling; the MagML channel
contains no tie samples, so that reported statistic cannot be reproduced from
this file using MagML.

For the paired channel experiment, both M03 runs use the exact same 66 profile
lines, 162,098 source record IDs, 14 preselected held-out lines and grid
geometry. Each withholds 32,895 rows; 32,872 have supported predictions
(99.930% coverage). At 1 km spacing, both support 103,896 of 181,395 grid
cells. MagL gives held-out MAE 126.984 nT and RMSE 223.900 nT; MagML gives MAE
126.498 nT and RMSE 223.979 nT. The RMSE difference is +0.079 nT for MagML
relative to MagL. This single-block comparison does not establish a
microlevelling benefit or harm: there is no independent error model, repeat
survey, cross-region evaluation or known subsurface target. The errors measure
spatial interpolation between profiles, not field accuracy or source recovery.

Both results explicitly retain `inverse_model=false`,
`provider_grid_comparison=false` and `scientific_release_accepted=false`. The
case is measured-data M03 QC and a negative/limited interpolation result. It is
not an M04 susceptibility inversion, geological interpretation, reproduction
of the provider's 1 km grid or independent validation of BAS processing.

## Reproduction and receipts

Use the external root configured by `GEOPHYSICS_LOCAL_DATA_ROOT` and the exact
source ID in the ledger. The acquisition receipt binds the original bytes to
the OGL citation. The parser manifest and M03 JSON receipts are stored under
`data/raw/magnetic/sparc-northern-palmer-m03-v006/` in that external root.
The local `case-receipt-v001.json` binds source, parser, processor, CSV and
result bytes. The three result hashes are `fd35c80b87238baf509a7d0b5ee85ffedea664b5cbe9376e4aec56dcf8e0448b`
(full MagL crossover), `eebd2c2836e6ff3848193718b2186017157b15b23c25551705592209397865e8`
(paired MagL), and `e0505943047e474ad62c6e3637fb843402232922773c3c59146044cc8412a2c9`
(paired MagML). Reproduce using the commands
in the source-acquisition guide and a Python 3.12 `.venv-pipeline`.
