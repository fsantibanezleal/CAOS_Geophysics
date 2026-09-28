# M06 measured magnetotelluric sounding: source, tensor admission, and stop verdict

This chapter records a *measured* long-period MT transfer function, not a raw electric/magnetic time series or a known-resistivity target. It is the bounded M06 scientific lane specified by the [feature requirements](../design/features/m06-field-mt/requirements.md), separate from the [synthetic 1D inversion and Clear Lake M05 screen](mt-recovery.md). The result on 2026-09-28 is **ineligible for isotropic layered 1D inversion**. No C15 model, predicted curve, holdout score, posterior, or geological interpretation has been produced. This is a candidate-specific scientific stop, not a claim that 1D MT is impossible elsewhere.

## Evidence and rights boundary

The [AusMT AusLAMP New South Wales survey](https://ausmt.auscope.org.au/surveys/auslamp-nsw-2016-21) and [C15 station record](https://ausmt.auscope.org.au/data/products/auslamp-nsw-2016-21/C15/station.json) attribute the EDI to Geoscience Australia, license its distribution CC BY 4.0, and cite Kyi, Jiang, Hitchman and Stolz, *AusLAMP New South Wales*, Geoscience Australia Record 2020/011, [DOI 10.11636/Record.2020.011](https://doi.org/10.11636/Record.2020.011). The exact [C15 EDI object](https://ausmt.auscope.org.au/data/edi/auslamp-nsw-2016-21/C15.edi) is 23,021 bytes, SHA-256 `353953564964015c59eaaa0ce8f808ebec48af0d51c11759a14c21be00b20a8f`. Its original bytes and acquisition receipt are ignored local assets at `data/downloads/auslamp-nsw/C15.edi` and `data/raw/acquisition/auslamp-nsw-c15.json`. The source ledger records a `mirror` rights decision because the survey license permits attributed redistribution; this branch **does not** publish a mirror or field-derived arrays.

Two provider JSON snapshots are independently hash-pinned and kept ignored: the [station record](https://ausmt.auscope.org.au/data/products/auslamp-nsw-2016-21/C15/station.json), SHA-256 `50b82ab1c9326414e1dabc418470fc1cb956b4ed039d63864c44571760560444`, and the [dimensionality screen](https://ausmt.auscope.org.au/data/products/auslamp-nsw-2016-21/C15/dimensionality.json), SHA-256 `412b267270b8f86f52233025fa0b4ccdba3f92b40d172a5d53697689c621e590`. The station record claims 35 periods, remote-reference processing, tipper, and a phase-tensor `1-D` class. Its 3D-period fraction is 37%, close to the upstream 40% screening threshold; its median skew beta is 2.5°. [AusMT's station-product reference](https://ausmt.readthedocs.io/en/latest/reference/station-products/) explicitly treats this automated classification as a *screening diagnostic*, not an interpretation product. The provider's label is therefore a useful candidate-selection clue, never an inverse admission verdict.

Candidate search was bounded, not a systematic census of every public MT station. The [USGS Clear Lake release](https://www.usgs.gov/data/magnetotelluric-data-clear-lake-region-northern-california) is CC0 and its `cl061` station is already an M05 negative control; it was **not** recycled for M06. Additional downloaded, ignored Clear Lake EDI files `cl059` and `cl060` and AusMT candidates from NSW, Capricorn and Cloncurry were **pre-screened with the community parser**. The table uses the same deliberately generous error normalization defined below; columns are full-period component WRMS `xx / yy / xy+yx`. A score above 3 fails the necessary 1D gate. Those pre-screen scores are not full independent raw/frame admissions; only C15 received that work. SHA values identify the *locally checked* candidate bytes, not new source-ledger entries.

| Candidate | Local EDI SHA-256 | Preliminary tensor score or rejection |
| --- | --- | --- |
| Clear Lake `cl059` | `69c758d290263c0ad06701810cdbdaba351b50a06f3f64099539f6d0673cb5d5` | 131.77 / 199.83 / 61.71 |
| Clear Lake `cl060` | `b9de390deb74d7711c27867798091af88be9479a05bac8a1ea5ac2a6ff2d91e2` | 95.67 / 25.06 / 57.41 |
| NSW `C15` | `353953564964015c59eaaa0ce8f808ebec48af0d51c11759a14c21be00b20a8f` | 43.00 / 14.22 / 6.73; provider class `1-D`, independent admission fails |
| NSW `J15` | `c0d5bef0ced46606d247eefe45133d742c8bfae1132d54a60b6eddb1c3e2781c` | 12.32 / 30.11 / 46.85 |
| NSW `M16` | `b87fa62d861900a18c80941fc5df7c8fdfa68f0ca9e8192e47406054d65b9523` | 18.60 / 4.10 / 13.33 |
| NSW `O16` | `a63c668bae6a16f0cbae3ca577d86ed6ed87491b272c5fe826c016b56fc20f0c` | 28.90 / 15.89 / 10.50 |
| NSW `P16` | `916caf96fc0efc7cb7e97e59edbcbf04d7f9a470a3ead764d524d1e37325537c` | 47.24 / 27.72 / 34.47 |
| Capricorn `CP2B06` | `04897ebc939fbc152bbe5cd8a932434a909d268a2e693d3a69753709c34e30eb` | 92.09 / 144.21 / 57.25, despite upstream `1-D` screen |
| Cloncurry `L14S19` | `37f4905e07710c36373f735e9ff9fc0c3b1e074ca66186a716b31fc836c76d62` | Incomplete electric-dipole geometry for this lane; community reader returns 69 zero error entries despite positive raw `Z.VAR` blocks. Parser/frame reconciliation is required before dimension testing. |

The table is a reproducible *search log* for locally sampled files, not a survey-wide no-solution theorem. Only C15 is registered as the reviewed M06 source; other files remain ignored and are not offered as product assets.

## Independent EDI and frame checks

`data-pipeline/mt_field_qc.py` reads original UTF-8/ASCII EDI blocks before invoking `mt-metadata==1.0.10`. It requires one terminal END, matching DATAID/SECTID, 4–512 distinct positive Hz frequencies, every real/imaginary/variance tensor block with the declared count, finite non-sentinel values, and strictly positive `Z.VAR` at **every** period. It compares every original frequency, complex impedance and variance with the community reader, allowing numerical rounding but not dropped or zero-filled values. The `C15` comparison agrees at all 35 periods. This independent raw check matters because an EDI reader may normalize missing values.

The EX/EY endpoint coordinates define *declared* electric azimuths and positive endpoint directions; physical instrument wiring polarity cannot be verified from EDI alone. HX/HY and remote RX/RY azimuths are independently checked for co-alignment and right angles. Every impedance block must reference the same ZROT. All original C15 ZROT entries and ancillary TROT entries are zero, so no rerotation or component-error covariance is guessed. A common exact 90° signed-permutation check leaves the normalized nearest-1D tensor distance invariant to `5.55×10⁻¹⁷`; arbitrary rerotation is refused. Tipper is checked for complete component/variance blocks, common missing mask and strictly positive variance where present, but never used to fit a 1D model. C15 has 35/35 tipper periods, median vector magnitude 0.1167. These checks establish parse and frame coherence, not instrument calibration or 1D structure.

The EDI does not itself settle native impedance units, time-harmonic sign, or whether `Z.VAR` is complex variance or per-real-component variance. The admission test does not need to convert units: zeros of the diagonal and `Zxy + Zyx` are invariant to a common nonzero scale and conjugation. An absolute Ω m inverse *would* need these conventions and any relevant full covariance established and recorded. The tiny native variances span `3.580339×10⁻⁶` to `0.05150069`; these are source values, not verified measurement coverage probabilities. No post-hoc error floor, frequency deletion, or covariance model was introduced to rescue C15.

## Dimension and error test

For a horizontally layered isotropic earth in a common horizontal frame, the necessary impedance form at each frequency is

```text
Z_1D(f) = [  0   z(f) ]
          [ -z(f)  0  ] .
```

Set `s_ij(f) = sqrt(Zij.VAR(f))` as a *generous upper standard deviation for each real and imaginary part*. If the native number is a complex variance, the actual per-part SD under the usual circular assumption would be `sqrt(VAR/2)`, increasing the rejection scores by `sqrt(2)`. No cross-component covariance is asserted: the standard deviation of `Zxy+Zyx` is bounded above by `s_xy+s_yx` by Cauchy–Schwarz. For `N` supplied frequencies, the three equal-weight, two-real-component statistics are

```text
WRMS_xx   = sqrt( mean_f( |Zxx|² / (2 s_xx²) ) )
WRMS_yy   = sqrt( mean_f( |Zyy|² / (2 s_yy²) ) )
WRMS_anti = sqrt( mean_f( |Zxy+Zyx|² / (2 (s_xy+s_yx)²) ) ).
```

All three must be at most 3 on **all** supplied frequencies. That necessary threshold predates this C15 selection: it is the existing M05 tensor-consistency criterion, applied with even more generous marginal errors. This is a diagnostic gate, not a calibrated hypothesis-test p-value: period correlations, systematic distortion, error-floor convention and full covariance are unknown. A failed gate means the given full measured tensor is incompatible with the isotropic 1D approximation at the supplied error scale. It does **not** identify a unique 2D/3D geometry or prove an instrument fault.

For a variance-independent diagnostic, `Phi = Re(Z)⁻¹ Im(Z)` is computed only when the real tensor condition number is at most `10⁸`. We report `||Phi - tr(Phi)I/2||F / ||Phi||F` and the [Caldwell phase-tensor](https://doi.org/10.1111/j.1365-246X.2004.02281.x) skew beta. A scalar phase tensor is compatible with 1D phase behaviour, but galvanic distortion/static shift can affect complex amplitude and a small skew alone does not validate the full tensor. The closest 1D antisymmetric complex tensor has `z=(Zxy-Zyx)/2`; its Frobenius relative departure is reported independently of the variance weights. These complementary diagnostics prevent an upstream phase label from silently superseding the complex-data residual gate.

| C15 result (all 35 original frequencies) | Value |
| --- | ---: |
| Frequency span | `3.968249×10⁻⁵`–`0.1` Hz (25,200.03–10 s) |
| `WRMS_xx / WRMS_yy / WRMS_anti`; gate ≤3 each | `43.0041 / 14.2159 / 6.7270` — **fail/fail/fail** |
| Median relative complex distance to nearest 1D tensor | `0.17985` |
| Phase-tensor usable periods; median/p90 scalar departure | `35`; `0.20233 / 0.26323` |
| Median absolute phase-tensor skew beta | `2.4663°` (provider rounds to `2.5°`) |
| Rotation invariance numerical error | `5.55×10⁻¹⁷` |
| Verdict | `ineligible`; `one_d_inversion_eligible=false`; `inversion_performed=false`; `methods={}`; `truth=null` |

The negative result is not repaired by fitting only the best-looking off-diagonal component: the unfitted diagonal and opposite off-diagonal are still measured constraints on the isotropic 1D assumption. It also cannot be repaired by reporting phase-tensor class `1-D` as geological truth.

## Inverse gate that remains unresolved

The product's pre-existing [1D recurrence](mt-recovery.md) has synthetic halfspace/two-layer controls, but no such control turns an ineligible field tensor into an admissible sounding. If another rights-cleared source passes source, geometry, covariance/error, units/sign and all-frequency dimensionality checks, its feature amendment must predeclare a frequency split before model tuning. Training-only bounded log-resistivity TRF with multiple fixed starts would minimize normalized real/imaginary complex residuals plus a declared adjacent-layer penalty; thickness count/range and beta would be fixed or swept on *training data only*. A one-layer halfspace fitted on precisely the same training frequencies is the baseline. The untouched held-out frequencies would be scored with both component WRMS and complex residual plots, against that baseline; there is no honest held-out metric for C15 because no inverse was run. Solver stop condition, bound contacts, Jacobian weak directions, alternate thickness and error assumptions, and all starts must be retained even if inconvenient. Conditional parametric intervals, if computed under a stated independent-error model and fixed parameterization, describe algorithmic repeatability—not geologic truth, uniqueness, or coverage under correlated field errors. Shared-station frequency holdout is weaker than independent-station generalization. A new source also requires its own pinned bytes, source citation, method review and tests; it must not inherit C15's provider label as permission.

## Exact offline reproduction (PowerShell, repository root)

Use Python 3.12. The new environment is ignored and intentionally separate from the main pipeline and M07. Download only the reviewed HTTPS objects, verify their hashes, and import the EDI through the immutable source-acquisition boundary:

```powershell
py -3.12 -m venv .venv-m06
.\.venv-m06\Scripts\python.exe -m pip install -r data-pipeline/requirements-m06.txt
New-Item -ItemType Directory -Force data/downloads/ausmt-candidates,data/raw/mt | Out-Null
Invoke-WebRequest -Uri 'https://ausmt.auscope.org.au/data/edi/auslamp-nsw-2016-21/C15.edi' -OutFile 'data/downloads/ausmt-candidates/C15.edi'
Invoke-WebRequest -Uri 'https://ausmt.auscope.org.au/data/products/auslamp-nsw-2016-21/C15/station.json' -OutFile 'data/raw/mt/auslamp-nsw-c15-station.json'
Invoke-WebRequest -Uri 'https://ausmt.auscope.org.au/data/products/auslamp-nsw-2016-21/C15/dimensionality.json' -OutFile 'data/raw/mt/auslamp-nsw-c15-dimensionality.json'
Get-FileHash data/downloads/ausmt-candidates/C15.edi,data/raw/mt/auslamp-nsw-c15-station.json,data/raw/mt/auslamp-nsw-c15-dimensionality.json -Algorithm SHA256
.\.venv-m06\Scripts\python.exe data-pipeline/acquire.py --source-id auslamp-nsw-c15 --file data/downloads/ausmt-candidates/C15.edi
.\.venv-m06\Scripts\python.exe data-pipeline/mt_field_qc.py
.\.venv-m06\Scripts\python.exe -m pytest -o addopts= tests/data/test_sources.py tests/numerics/test_mt_field_qc.py
.\.venv-m06\Scripts\python.exe -m ruff check data-pipeline/mt_field_qc.py tests/numerics/test_mt_field_qc.py tests/data/test_sources.py
git ls-files data/downloads data/raw
```

The hash output must match all three pins above *before* trusting the snapshots. The first acquisition creates ignored `data/raw/acquisition/auslamp-nsw-c15.json` and installs the immutable source under `data/downloads/auslamp-nsw/C15.edi`; the QC command verifies it again and writes ignored `data/raw/mt/auslamp-nsw-c15-m06-admission.json` and `.json.sha256`. The command prints the source hash, 35-frequency count, three WRMS values, `status=ineligible` and `inversion_performed=false`. `git ls-files` must print nothing. No script in this workflow modifies `data/derived`, frontend/API, a deployment, or the prior `cl061` screen. The [source guide](../guides/05_sources.md) and [data contract](../data-contract/data-contract.md) explain storage and release boundaries.
