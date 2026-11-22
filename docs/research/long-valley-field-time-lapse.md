# Long Valley repeated-station gravity: field-data processing case

**Status:** source-bound local data workflow and browser view implemented. This
is an observed time-lapse processing case. It is not a density inversion and
does not infer a magma body from the raw difference.

## Source and rights

The source is the USGS Long Valley Caldera GIS Database, Digital Data Series
DDS-81 (2003), `MonitoringData/Gravity/SpreadsheetFormatData/GravitySurveys.txt`
and its FGDC record. The official format page describes occupations from 1980
through 1999, gives gravity and standard deviations in mGal, and reports UTM,
NAD27 coordinates in metres. The network page describes the USGS 1980–1985
occupations and Stanford University's 1998–1999 reoccupations. The FGDC metadata
lists no access or use constraints and requests USGS acknowledgement. The app
retains the full DDS-81 attribution and direct links. USGS-produced data are
public domain under the agency's published policy; this mixed-contributor
dataset remains attributed to DDS-81 and its credited authors.

- [USGS DDS-81 archive](https://pubs.usgs.gov/dds/dds-81/intro.html)
- [Gravity table format, units and coordinate frame](https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/DataFormat.html)
- [Network field and correction history](https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/gravity.html)
- [FGDC gravity metadata](https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/gravitymetadata.htm)
- [USGS data and copyright policy](https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted)
- [Battaglia, Roberts & Segall (1999)](https://doi.org/10.1126/science.285.5436.2119)
- [Battaglia et al. (2003), geodetic and microgravity constraints](https://doi.org/10.1016/S0377-0273(03)00171-9)

## Download, process, reproduce

Raw downloads live under
`$env:GEOPHYSICS_LOCAL_DATA_ROOT/data/downloads/long-valley/`, outside the
repository. Set `GEOPHYSICS_LOCAL_DATA_ROOT` to an absolute device data root
(for example `E:\_Datos\CAOS_Geophysics`) or pass `--data-root` explicitly.
The downloader allows only the two pinned USGS URLs, enforces a 1 MiB response ceiling, checks
the gravity table byte count and SHA-256, and checks a canonical metadata hash.
The HTML metadata includes rotating Cloudflare email tokens and a transient
script; canonicalization removes only that injected wrapper and those contact
tokens. All other source-authored metadata remains in the fingerprint.

```powershell
$env:GEOPHYSICS_LOCAL_DATA_ROOT = 'E:\_Datos\CAOS_Geophysics'
.\.venv-pipeline\Scripts\python.exe scripts/download_long_valley.py
.\.venv-pipeline\Scripts\python.exe data-pipeline/long_valley_timelapse.py
.\.venv-pipeline\Scripts\python.exe data-pipeline/long_valley_timelapse.py --check
.\.venv-pipeline\Scripts\python.exe -m pytest -q tests/data/test_long_valley_timelapse.py
```

The compact prepared observation artifact is committed at
`data/derived/field/long-valley/1982-06_to_1999-07.json`; the production build
copies only that file after checking its byte count and SHA-256 against
`frontend/src/data/field-study-index.json`. The raw source table is not copied
to the web bundle.

## What is computed

The source table contains 37 station rows, eight occupation epochs and 212
non-missing station-epoch measurements. For each station present at both chosen
epochs, the processor calculates

\[
\Delta g_i = g_{i,B}-g_{i,A},\qquad
\sigma_{\Delta,i}^{(\mathrm{ind})}=\sqrt{\sigma_{i,A}^2+\sigma_{i,B}^2}.
\]

The superscript marks the independent-error assumption. The source gives
occupation-level 1-SD values, not inter-epoch covariance. The default pair,
June 1982 to July 1999, has 37 paired stations; its raw observed differences
range from approximately −0.123 to +0.002 mGal. These are not corrected
residuals. The app recomputes the pair and its uncertainties in the browser from
the source-bound observation arrays; it does not grid or interpolate the
station values. Selecting a station reveals its occupation history relative to
its first available measurement, with propagated uncertainty bars.

## Scientific limits

The source's station table has no elevation coordinate. The format page says
UTM/NAD27 but does not name the UTM zone in that table; the view therefore keeps
source-reported easting/northing and does not reproject them. Its metadata and
network description state that solid Earth tide and daily gravimeter drift
were removed and that repeat readings were averaged by least squares. The
browser's raw epoch differences receive no additional correction for vertical
deformation, water-table changes, or covariance across occupations. Those
effects matter: the published Long Valley interpretation explicitly corrected
gravity change for deformation and hydrologic effects before estimating a
source. Consequently, the display makes no source-depth, density, magma, or
uniqueness claim. It supports archive inspection, temporal pairing, uncertainty
propagation, and data-quality teaching only.

### Source quality flag: 1JD1952, September 1982

The retrieved table reports 979255.21 mGal (σ=0.005 mGal) for 1JD1952 in
September 1982. The same value appears for station 1JCM1952 in this archive;
the other available 1JD1952 occupations are near 979279.9 mGal. USGS Open-File
Report 87-77, [Table 3](https://pubs.usgs.gov/of/1987/0077/report.pdf), lists
979279.87 mGal for station “1 JDI 952” and 979255.21 mGal for “1 JCM”. This is evidence of a possible cross-copy or
transcription issue, not proof that the 1982 observation is erroneous: station
names, epochs, and source versions must be checked with the data owner.

Accordingly the pipeline pins this review flag to the exact downloaded table
SHA-256 and exact station/epoch/value/uncertainty tuple. It preserves the raw
value, marks it unresolved, excludes it from default pairwise differences, and
offers an explicit include-flagged control. No replacement value or automatic
outlier threshold is used. The pair 1982-09 to 1999-07 therefore has 23 default
pairs and 24 when the flagged record is explicitly included; that inclusion
produces the visible +24.605 mGal difference and should be interpreted as a
source-QC investigation, not a plausible corrected signal.

The two bilingual lessons
[`04-long-valley-time-lapse-processing`](../../notebooks/en/02-gravity/03-long-valley-time-lapse-processing.ipynb)
and [Spanish counterpart](../../notebooks/es/02-gravity/03-long-valley-time-lapse-processing.ipynb)
replay the downloaded source, quantify epoch coverage, inspect the station
network, plot temporal differences, and test sensitivity to unknown
cross-epoch correlation. They execute no inversion and preserve the above
limits.
