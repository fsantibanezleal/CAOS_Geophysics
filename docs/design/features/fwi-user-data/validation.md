# Supplied FWI validation, 2026-10-08

This records local controlled calculations and import checks, not field
validation, VPS FWI admission or a complete product release.

## Actual original-input execution

The final source-bound CUDA matrix passed 23 tests, zero failures/errors/skips.
JUnit suite time 225.107 s; command wall 226.37 s. A later original-input preparation
test passed separately 1/1 in 2.775 s; it is not retroactively part of that matrix.
The observed arrays and independent initial velocity remained unchanged.

The full-budget case has three shots, 20 receivers and 3,200 samples per trace.
Both methods ran 112 L-BFGS calls with 28 calls per stage, identical fitting masks,
independent starting model and regularization. Every terminal prediction was
recomputed by a fresh scalar forward call: unchanged prediction rtol/atol
2e-5/2e-5 and residual2e-4/2e-5. Export reopening checks full array identities,
axis order, exact float32 observed-minus-predicted residuals and final-model/frame
equality. A separate actual CUDA test changed beta and measured a model change.
Neither a serialized fixture nor a cached canonical case replaces these runs.

| Quantity | Full-band | Multiscale |
| --- | ---: | ---: |
| Initial fitting relative MSE | 0.0005335343032842526 | same |
| Final fitting relative MSE | 0.00003331503186881423 | 0.000005841915072936148 |
| Initial withheld relative MSE | 0.0011972806771578606 | same |
| Final withheld relative MSE | 0.0002475339669992302 | 0.000018009454878952193 |
| External control-only final velocity RMSE [m/s] | 466.7247009277344 | 457.569580078125 |

External control-only initial model RMSE 508.2166442871094 m/s. Known control truth
was inspected only after both fits/exports were fixed; it is not an inverse input
or emitted user-result field. Waveform agreement improved more than velocity
recovery. Stop remains a finite budget, not a convergence certificate or unique
geological interpretation. These positive numerical checks do not erase the
unchanged cycle-skip and other original failure controls.

Actual inverse wall 177.0247156000696 s, CUDA allocated peak 2,073,827,840 bytes,
20 ms-sampled peak RSS 1,414,254,592 bytes. RSS is sampled, not an OS maximum.
Torch 2.14.0+cu126, Deepwave 0.0.27, NumPy 2.2.6, RTX 4070 Laptop GPU.
One local experiment is not a latency percentile or universal resource guarantee.

An additional unchanged-solver CUDA acquisition matrix passed 2/2, with no skips,
in 39.787 s: both 20 and 40 receivers, 768 samples, two actual inverse methods,
export/reopening, exact final frames/residuals, original-byte preservation and
changed-beta model effect. This short matrix does not establish the full-budget
40-receiver resource ceiling. Its JUnit SHA-256 is
`6c6f2923281ab129ebf250d440f9a3a1fa66a2293747171f2b54e861ff5bd51d`.

## Identity and retained failures

- Actual FWI module SHA256:
  `628881441fe0d5c5c47aef49742069fe3766d24409d8a519c8d3b95469f7c80f`.
- Unchanged seismic module:
  `e0d475c946edd07c906874511d4c53170db8180dcf0c74887da73bba35b55c85`.
- Complete controlled generation manifest:
  `1e19d31bdee7afec2bc86e1a9b65a0c754e100bd3945e754dc07cbdd449f1e13`.
- Final CUDA JUnit, 2,879 bytes:
  `8b271666c7832a920f8fd6418f6938fea459e8053d382698480fc19d149ff6ec`.
- Separate preparation JUnit, 380 bytes:
  `74eb9aebdb14a329b06ba7eebb6f1f4f431ea84cda9c4c59e61a485f521ddc17`.

An earlier hardened matrix reported 20 PASS/3 FAIL: final-frame validation was
unreachable after an indentation mistake; TorchVersion is a string subclass but
the metadata validator requires exact strings. Both implementation errors were
corrected, then the full matrix reran without weakening assertions or tolerances.
The failed receipts and partial generations remain retained externally.

## Browser and build scope

The v4 integrated browser run passed both tests in 4.5 min: eight EN/ES/theme/
desktop/phone FWI contexts, exact sample export versus original binary offsets,
three native 3200x20 gather rasters, physical 128/96 velocity aspect, full traces,
recorded-state play/pause/scrub and schedule switching; plus all six supplied-joint
course chapters in eight contexts. It used actual completed local CUDA arrays,
no intercepted API, upload, fallback solve or synthetic UI response. Source file
digests before/after import matched. All 197 frontend contracts passed without
skips using actual protected ERT/TT and local FWI/profile generations.

Earlier browser timeouts were retained. Trace evidence showed exact accessible
label lookup never resolved for the nested scientific-view select; explicit
accessible names fixed that fault. A separate native-pixel canvas/layout change
removes the old 8-fold raster allocation; it was not the demonstrated timeout
cause. The browser verifies bytes/contracts, not independent acoustic physics.

Screenshot review then prompted an additional shared-token layout revision:
initial/result comparison on existing responsive two-plot layout, three gathers
together on existing three-plot layout, literal receiver-metre/time extents,
view-only shared returned-state versus full-bound velocity scales, and linked
trace scale from its actual three arrays. Scientific arrays are unchanged.
The later v7 run passed 2/2 in 5.8 min, with the same eight FWI contexts and
eight six-chapter course contexts. The selected original trace sample was 962,
not a visually convenient pre-arrival sample; exported observation, prediction
and residual equalled the exact original binary offsets. All 197 frontend
tests passed with zero skips after the layout revision; report SHA-256:
`7cf868f20e66e4bb639f7d83063370aec9384ec6cd6d539a56ec01ceabf3ae82`.
Actual desktop gather/model and Spanish phone trace screenshots were inspected.
A subsequent time-label formatting change rounds displayed time to four decimal
places only; physical coordinates and exported values are unchanged. The final
v8 strict TypeScript/build and single-origin source/build guard passed. Its real
browser matrix passed 2/2 in 2.8 min: FWI 1.0 min and course 1.6 min, with all
eight contexts per instrument. This is local rendering, not a public cutover.

All raw controls, binary generations, failed/accepted XML and browser evidence
are under external `E:/_Temp/geophysics-resume-20261008`, not a repository cache.
No private account information or raw field dataset is included in this record.
Ruff and single-origin source/build gates pass; build warnings about the existing
large main chunk remain explicit, not a measured performance acceptance.
