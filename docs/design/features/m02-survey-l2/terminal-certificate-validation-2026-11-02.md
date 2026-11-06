# CPU2 terminal certificate validation ledger — 2026-11-02

**Current verdict: validation in progress; no scientific acceptance.** This is
candidate-source evidence under the approved design amendment. It is not a
deployment or release record.

## Completed local evidence

- `tests/numerics/test_gravity_irls_corrected.py` exited 0 when run with all
  three native-workspace thread pins set to `1` (`OPENBLAS_NUM_THREADS`,
  `OMP_NUM_THREADS`, `MKL_NUM_THREADS`). This includes a native solve through
  the new certificate path, exact certificate replay, weight and KKT rejection,
  inner-solve/state/curvature negatives, tied and active-bound rejection, and
  unchanged null/legacy controls.
- The exact current-source rerun passed all 36 tests, including seven additional
  tamper controls for beta, request-derived background, bounds, epsilon, operator
  hash, source inventory, and a one-ULP final native model change.
- The first invocation without the required pins is invalid as solver evidence:
  it rejected initialization with `metric: reviewed single-thread native
  workspace required` before entering IRLS. No solver acceptance was inferred
  from it.
- The frontend production build passed after the Long Valley citation update;
  all four EN/ES, light/dark, desktop/phone browser contexts passed with no
  horizontal overflow or browser errors. These feature checks are independent
  of M02 terminal certification.

## Completed candidate matrix; remaining acceptance gates open

The first matrix launcher had a node-ID ordering mismatch: pytest IDs are
`[family-condition]`, but the launcher initially supplied `[condition-family]`.
Its 16 valid unique test nodes covered families 0–3 across conditions 0–3. The
eight trailing non-existent selectors were harness errors and are excluded
from solver evidence. The corrected follow-on completed the eight missing
actual nodes (families 4–5 × conditions 0–3). All valid cases wrote new,
source-bound archives and logs under
`E:\_Datos\CAOS_Geophysics\validation\m02-terminal-cert-20261102` and
`D:\_Temp\gravity-playback-qa\m02-terminal-cert-matrix`; existing evidence is
not overwritten. Every actual case retains its selection/failure and
per-fit/aggregate timing.

All 24 valid parameterized nodes have now exited. Each case selected a beta
candidate. Calibration wall times ranged from 988.859 to 1670.359 seconds,
below the 1,800-second aggregate limit. Twenty-two nodes exited 0 and completed
their independent held-out evaluation checks. Two nodes exited 1 on the
existing 120-second per-fit cap; the archived fits measured 122.656 seconds
(family 1, condition 1) and 120.047 seconds (family 3, condition 1). Their
full calibration archives remain available, and no limit was changed. The
eight invalid selectors from the first launcher are harness errors and are
excluded; the corrected follow-on supplied all eight actual family-4/5 nodes.

The 20 cap-bound and 20 nominal resource children now all pass locally, with
complete process-tree sampling and source-bound receipts. Aggregate p95 values
are 130.582 seconds wrapper wall / 285,356,032 bytes peak RSS for cap runs and
799.863 seconds / 308,989,952 bytes for nominal runs. These local runs do not
prove an upper bound or host admission: both `resource_upper_proof` and
`host_accepted` remain false in the aggregate receipt. The per-run archive is
`E:\_Datos\CAOS_Geophysics\validation\m02-terminal-cert-resource-20261102`.

Both isolated fresh-root timing replays now pass. Family 1 / condition 1
selected beta index 6 with a 347.531-second calibration, 107.984-second maximum
fit, and held-out WRMS 1.198917. Family 3 / condition 1 selected beta index 5
with a 301.000-second calibration, 49.000-second maximum fit, and held-out
WRMS 1.085903. Both are below their unchanged limits and include independently
evaluated held-out archives. An initial family-1 replay used D: scratch and E:
data; the solver finished, but atomic hard-link archive publication correctly
failed across volumes. That infrastructure attempt produced no evidence and was
not counted; the passing replay uses fresh E: data and scratch roots.

Still open: independent reproduction from the original requests; owner review;
and all other product/release gates. The research-only 12-fold archived
weight/KKT audit remains diagnostic and does not exercise this terminal route.
Candidate results do not establish field eligibility, method acceptance,
product convergence, or VPS promotion.

## Matrix outcomes

Two completed nodes failed only the existing per-fit wall cap:

| Case | Observed fit wall time | Outcome |
| --- | ---: | --- |
| family 1, condition 1 | 122.656 s | failed the 120 s per-fit cap |
| family 3, condition 1 | 120.047 s | failed the 120 s per-fit cap |

Both original failed outcomes and exact-request archives are retained as
resource-gate failures; they are not erased by the later replays. The fresh-root
isolated replays passed the unchanged 120-second cap, so neither overrun
reproduced. No limit was changed and no scientific acceptance is inferred.

## Exact-checkout focused rerun — 2026-11-02 12:19 CLST

A fresh focused replay of `tests/numerics/test_gravity_irls_corrected.py` on the
current direct checkout passed 36/36 tests with the required one-thread BLAS,
OpenMP and MKL pins. Runtime was 77.555 s; the native positive control completed
as `converged/irls_fixed_point` in 69 combined steps. Ruff and scoped
`git diff --check` also passed. This reconfirms the local candidate controls;
it is not the independent certificate reproduction or full product acceptance.

JUnit SHA-256: `7b81ae0beb7475f42152ca450e7e95caebb4bb3cda421c61eb3abee334e526af`

Exact-checkout SHA-256:
- `data-pipeline/gravity_irls_corrected.py`: `d5a6a80c75b22d3fd9b01f251d40443585b4c9cd24e5b27fa1d72a037bdc4b01`
- `tests/numerics/test_gravity_irls_corrected.py`: `8e185a8009b1eb3228cfc59c814d3a79335b8fa35af470c2d0dd35da126f7b53`

## Current-source family-0 / condition-0 replay — 2026-11-02

The prior CPU2 archive failed current-source identity because its recorded
`gravity_l2.py` digest differed from the working tree. It remains historical;
no certificate audit was run against it. The full source-matched matrix node
`test_original24_corrected_science[0-0]` was therefore executed against the
current source inventory. It passed in 611.311 s (calibration wall 561.531 s),
selected candidate index 5, completed its frozen outer evaluation with WRMS
1.2211798943, and retained the new calibration and outer archives outside the
repository. JUnit reports one pass, no failures/skips. JUnit SHA-256:
`cfde926b063ebe72c91c49542d53328809e064b4430a7b98d265e0b22e7ed6ee`.

The new independent audit script
`scripts/research/audit_cpu2_terminal_certificate.py` does not call the
producer's terminal-certificate decision function. It loads the exact current
source-bound archive, reconstructs each problem from its archived request,
creates a fresh SimPEG Sparse stage, and independently compares the final
smallness weights, stage weight hashes, projected KKT infinity norm, smallness
Hessian diagonal minimum, and beta-scaled strict-convexity lower bound against
the stored certificate. It audited 10 certificate-bearing fits. Recomputed KKT
ranged from `2.5579538487e-13` to `8.5292883867e-13`; minimum smallness curvature
was `2000000`, and strict-convexity lower bounds ranged from `1440000` to
`14400000000`. Every archived value matched exactly. This is research evidence
for this one family/condition only; it is not full 24-cell acceptance or a
peer review.

Archive SHA-256: `9f6d5bf881e8a027b8b62629685d42eb57982010148edb2fd2031b3dc7ad87da`
Audit receipt SHA-256: `f967337c41138746ec31dd8d986468133445f0e2f8145f17c13a77fafeaca226`
Audit receipt digest: `b09108640691c8804398b98d6900fa6ac0991bbc3af0f482e0c777db40df9c8f`
Auditor source SHA-256: `d50772893a11699bc017e9075154086723a36e2adcb4202e73528926e4178884`
Current `gravity_l2.py` SHA-256: `fc6fd9216edd43c02b83fddedca007a782bc627073a9d08da069d29f75d4d016`

The auditor passes Ruff and Python compilation. No source archive was overwritten.
Independent review of the other 23 family/condition cells, complete resource
upper-bound/host admission, remaining scientific/product gates, and VPS cutover
remain open.

## Current-source certificate matrix and independent replay — 2026-11-02

After detecting that the earlier archived CPU2 calibration used a different
`gravity_l2.py` source hash, the complete frozen matrix was rerun in a fresh
external root against the exact current source inventory. Command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
$env:GEOPHYSICS_M02_IRLS_CORRECTED_DATA_ROOT='E:\_Datos\CAOS_Geophysics\validation\m02-terminal-cert-current-matrix-20261102\data'
$env:GEOPHYSICS_M02_IRLS_CORRECTED_TEMP_ROOT='E:\_Datos\CAOS_Geophysics\validation\m02-terminal-cert-current-matrix-20261102\scratch'
.venv-pipeline\Scripts\python.exe -m pytest tests/numerics/test_gravity_irls_corrected_matrix.py::test_original24_corrected_science -q --junitxml=E:\_Datos\CAOS_Geophysics\validation\m02-terminal-cert-current-matrix-20261102\original24.xml
```

Result: 24/24 passed; zero failures/errors/skips. Every family/condition cell
selected a candidate and completed held-out outer evaluation. Calibration wall
times were 243.922–867.844 s (sum 10,599.704 s); maximum individual fit wall was
118.234 s, below the unchanged 120 s cap. Every calibration remained below the
unchanged 1,800 s aggregate cap. Outer WRMS ranged 0.8133–2.9621; these synthetic
controls establish the recorded behavior only, not field transfer or general
geological recovery. The 600 fit records include retained failed alternatives
(163 line-search failures, 40 IRLS caps, and 12 starts unavailable at the wall
cap); selected candidates still had all required converged folds. JUnit suite
wall time was 12,155.221 s. JUnit SHA-256:
`7c9735857861cd45a86395b2bf920c98b470330feec847a6622154f92cc1af5a`.

All 24 source-bound calibration archives were then audited by
`scripts/research/audit_cpu2_terminal_certificate_matrix.py`. It rebuilt each
problem from the archived request, independently instantiated the SimPEG Sparse
stage, recomputed terminal weights/hashes, projected KKT, smallness curvature,
and beta-scaled strict-convexity bound; it does not call the producer's terminal
certificate decision function. The 24 archives contained 208 certificates; all
208 recomputed values matched. KKT ranged `7.6383344094e-14`–`9.7044594582e-13`;
minimum smallness curvature was `2000000`, and the minimum strict-convexity bound
was `1220000`. This is an independent computational replay authored in this
checkout, not external peer/owner review or overall product acceptance.

Archive root: `E:\_Datos\CAOS_Geophysics\validation\m02-terminal-cert-current-matrix-20261102\data`
Audit receipt file SHA-256: `0e102cbf3d9fde13e17f387234ee10f975fc66f3678b17b1fea227af53f45d01`
Audit receipt digest: `35d6d3570bbdd3a8308686e53aae6f3ca26ab19de70a1cd2dba3e4ba17190004`
Matrix auditor SHA-256: `e1043e0cd81245c2ed18b3b6e3dd76aef95c42024aaaa71a34b28e530cf2742f`
Single-archive auditor SHA-256: `d50772893a11699bc017e9075154086723a36e2adcb4202e73528926e4178884`

Exact source SHA-256:
- `data-pipeline/gravity_l2.py`: `fc6fd9216edd43c02b83fddedca007a782bc627073a9d08da069d29f75d4d016`
- `data-pipeline/gravity_irls_corrected.py`: `d5a6a80c75b22d3fd9b01f251d40443585b4c9cd24e5b27fa1d72a037bdc4b01`
- `data-pipeline/gravity_irls_corrected_workflow.py`: `c9538fdf7aad5153c29cc319a65398489bd0c9b20b85b6598ce0bdf40927c6ba`

Both audit scripts pass Ruff and `py_compile`. The separate 20+20 resource
receipt is not current-source evidence: its archived `gravity_l2.py` hash is
`e3ce4f56c0b8e1c9f993f756e83dee9e8a3f0e79df4335e4519b7f0f5fe87fdb`, while the
current source hash is
`fc6fd9216edd43c02b83fddedca007a782bc627073a9d08da069d29f75d4d016`. Its pass
counts and sampled resource values remain historical diagnostics only. A new
exact-source resource replay and justified upper-bound/host admission are open.
External peer/owner review, the other M02 workflows, and all broader
product/release gates also remain open.

## Exact-current-source resource replay — 2026-11-02

The frozen 20-cap/20-nominal resource harness was rerun into a new external
directory after the previous receipt was found to contain a stale
`gravity_l2.py` hash. All 108 inventoried Python sources, the harness and matrix
test matched the exact current working-tree bytes at replay completion. Each of
the 40 child science records also matched that same complete inventory; all 40
children passed and all 40 process-tree samplers completed without errors or
hard timeouts.

| Group | Trials | Child wall range | p95 child wall | Peak RSS range | p95 peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Capped fit | 20/20 passed | 126.875–141.547 s | 136.544 s | 283,004,928–286,429,184 B | 286,331,904 B |
| Full nominal calibration | 20/20 passed | 695.000–917.688 s | 886.901 s | 307,834,880–309,084,160 B | 309,045,248 B |

The nominal case performs a fresh full calibration for every child. The cap case
replays the frozen family-0/condition-1 deadline-bound fit. No cache result or
previous-source receipt was reused. The exact-source runtime epoch is
`m02-survey-irls-cpu-2-terminal-certificate-exact-q-replay-legacy-init-1`.
The normalized SHA-256 of the complete 108-file source inventory is
`5315723ce0abfe9e061b783ced88f4a290cff8cba9c80b9a6db336fc38781c70`; the
aggregate receipt SHA-256 is
`2d5a2a7743f7a26b16478acbcb22758aecd7bcf3d38fb4bf6e1adf7b1176621b`.

External archive:
`E:\_Datos\CAOS_Geophysics\validation\m02-terminal-cert-resource-current-source-20261102`.
The aggregate receipt deliberately still records `resource_upper_proof=false`
and `host_accepted=false`. Sampled process RSS is not an allocation upper bound;
these Windows measurements do not establish an ML VPS limit, cgroup/container
charge, or hosted job admission. The numerical resource repeatability gate is
now source-current and locally measured; proof from the bounded allocation
contract and actual-host admission remain separate required work.

## Current-checkout independent replay — 2026-11-06

The matrix auditor was rerun from checkout revision
`88ea5958e78593bff0df766041a0b32aa06f51d8` against the retained 24 current-source
calibration archives in the external `m02-terminal-cert-current-matrix` evidence
set. It independently replayed all 208 CPU2 terminal certificates across all 24
archives. The projected-KKT infinity norms ranged from
`7.638334409421077e-14` to `9.704459458248493e-13`; minimum smallness curvature
was `2,000,000`, and the minimum recorded strict-convexity lower bound was
`1,220,000`.

The new matrix receipt SHA-256 is
`0e102cbf3d9fde13e17f387234ee10f975fc66f3678b17b1fea227af53f45d01`; its
internal receipt identity is
`35d6d3570bbdd3a8308686e53aae6f3ca26ab19de70a1cd2dba3e4ba17190004`. Both the
matrix receipt and auditor explicitly retain `research_only=true` and
`acceptance=false`. This replay confirms certificate arithmetic and archive
identity only. The allocation upper-bound proof, actual-host admission, and
independent peer/owner review remain open; M02 and product acceptance remain
unaccepted.
