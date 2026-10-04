# Process and inspect supplied ERT and first-arrival profiles

This workflow executes the existing topography-aware pyGIMLi DC inverse or
Dijkstra first-arrival inverse on an explicit local original. It is not a
browser inverse, a provider-file substitution, or a claim of uniquely recovered
field geology. Originals remain local. Result and manifest files can be opened
in the public profile instrument without an account or upload.

## Physical problem and input contract

For ERT the observations are transfer resistances
\(R_i=(u_{M_i}-u_{N_i})/I_i\), in ohms. Conductivity satisfies the DC potential
equation \(\nabla\cdot(\sigma\nabla u)=-I(\delta_A-\delta_B)\).
Topographic geometric factors convert resistance to apparent resistivity, but
apparent resistivity is not a directly measured subsurface cell resistivity.
The `.ohm` parser accepts its explicit sensor count, metre coordinates,
measurement count and one-based ABMN/resistance records. Invalid geometry,
counts, duplicate quadrupoles and unsupported columns are rejected.

For first arrivals, \(T=\int_\Gamma v^{-1}\,ds\) and the isotropic eikonal
relation is \(|\nabla T|=v^{-1}\) away from sources. The `.sgt` original contains
sensor positions and one-based source/geophone indices with times in seconds.
The computed inverse uses Dijkstra paths on the engine's discretization, not
straight rays drawn to imitate a recovered model. Sensor geometry and exact
row order survive export. Both formats require an explicit local horizontal
reference and elevation datum, metre coordinates and elevation positive up.
No datum, foot/metre conversion, measured uncertainty or rights are guessed.

The physical implementation and limitations follow the
[pyGIMLi inversion guide](https://www.pygimli.org/user-guide/inversion/),
[topographic ERT example](https://www.pygimli.org/_examples_auto/3_ert/plot_02_ert_field_data/)
and [field traveltime example](https://www.pygimli.org/_examples_auto/2_seismics/plot_04_koenigsee/).
Provider examples illustrate the engines, not permission to redistribute an
arbitrary original.

## Explicit metadata

Create a JSON object with exactly `schema`, `method`, `source`, `frame`, and
`weights`. The [feature contract](../design/features/supplied-profile-workflow/design.md)
defines every field and byte bound. Required declarations are:

- `schema`: `geophysics.supplied-profile/v1`.
- `method`: `ert.topographic-profile/v1` or `traveltime.first-arrival-profile/v1`.
- `source`: nonempty `source_id`, `kind` (`user_upload`, `field`, or
  `synthetic_control`), `citation`, exact original `sha256` and `bytes`.
- `source.rights`: `holder`, `processing_allowed: true`, and an explicit Boolean
  `redistribution_allowed`. These are operator declarations, not independent
  permission verification. Export does not copy raw bytes.
- `frame`: `horizontal_reference`, `vertical_datum`, `coordinate_unit: "m"`,
  `vertical_positive: "up"`, `profile_axes: ["distance", "elevation"]`.
- `weights.policy`: `provider-example-conditional/v1`.

For an original file, obtain its exact SHA-256 with `Get-FileHash` on PowerShell
or `sha256sum` on a Unix shell. Use the byte count of that same original. Do not
hash a reformatted table, replace missing metadata with an arbitrary label, or
declare redistribution permission merely because a file is downloadable.

The conditional weighting policy is explicit:
\(\sigma_R=\max(0.03|R|,0.001\ \Omega)\) for ERT and
\(\sigma_t=\max(0.03t,10^{-4}\ \mathrm{s})\) for traveltime.
These assumed errors are not instrument-calibrated covariance. An apparent
chi-square target therefore cannot establish geological validity.

## Execute, retain failures, and reproduce

Use the pinned `requirements-ert.txt` or `requirements-traveltime.txt` environment.
The invocation is by script path; no editable internal package installation is
needed. For example, with the original and its metadata already prepared:

```powershell
.venv-traveltime/Scripts/python.exe -B scripts/process_supplied_profile.py `
  --input survey.sgt --metadata survey.metadata.json --output results/survey-run-01
```

```bash
.venv-traveltime/bin/python -B scripts/process_supplied_profile.py \
  --input survey.sgt --metadata survey.metadata.json --output results/survey-run-01
```

Use the ERT environment and `.ohm` original for ERT. The output directory must
be new; reruns never overwrite an earlier result. `result.json` and
`manifest.json` are exclusive, hashed outputs. The single stdout JSON receipt
uses exit zero only for a passed numerical report; exit three retains an
ineligible, nonconverged or unverified scientific artifact; exit two means
admission/publication was rejected. Python and native-engine diagnostics use
stderr. Keep that stream private when it contains local paths.

The wrapper binds original hash/count/file identity before parsing and checks
it again after calculation. Engine, wrapper and mesh-serializer bytes are also
bound. Implementation or original drift prevents completed publication.
Independent reproduction requires the same original, declarations and pinned
environment, not merely a screenshot or matching exported array hashes.

## Held-out prediction is separate from geological recovery

The traveltime supplied policy requires at least ten distinct shots and sets
\(K=\lceil N/5\rceil\). The interleaved whole-shot fold holds ordered indices
\(\lfloor(j+1)N/K\rfloor-1\), while the central fold starts at
\(\lfloor(N-K)/2\rfloor\). Neither uses observed times to select the fold.
Each retains at least 100 training and 30 held picks. Accepted prediction needs
at least ten percent held-RMSE improvement over the training-only homogeneous
baseline, improvement on at least \(\lceil2K/3\rceil\) held shots, and a normal
stop before the original iteration ceiling. The analytic homogeneous,
reciprocity and speed-scaling forward checks remain required. The original
15-shot provider path retains its exact older fold records and digests.

ERT retains its original homogeneous-factor oracle and both independent
prediction challenges. Exported passed verdicts are checked against those
reported numerical conditions before the browser displays a passed model.
That structural check is not independent solver replay. Negative controls,
failed held-out tests and insufficient geometry remain visible rather than
being replaced with an attractive model.

## Inspect native geometry and linked measurements

From App choose **Local ERT / traveltime results**, then select the matching
original `result.json` and `manifest.json`. The browser verifies their byte,
content, source, method and configuration bindings before displaying arrays.
An unsuccessful import leaves the previous admitted result visibly identified.

The model view draws actual returned triangular cells with equal metre scale
on both axes, elevation upward and original acquisition locations. It does not
interpolate centres into invented geology or imply resolution below the mesh.
Choose a cell by pointer or keyboard, and a measurement by its original index;
linked readouts show observed/predicted values, signed prediction-minus-
observation residual, assumed error and coverage. Pan, zoom and colour limits
change the display only. Coverage is not posterior uncertainty. Whole-shot
fits are independently selectable. Acquisition-row playback moves selection,
not waves or an optimizer history that was never recorded.

An inspection export includes the exact admitted result, producer-file hashes
and selected cell/row/fold. It is an inspection sidecar, not a new signed
producer manifest. Raw originals are not uploaded, copied or exposed by this
local route. Protected VPS job integration and actual host admission are
separate capabilities and must not be inferred from this local calculation.
