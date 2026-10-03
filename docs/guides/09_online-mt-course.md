# Use and reproduce the M05/M06 course

## In the application

From App, use the shared header to open Introduction for the current source/processing/inverse and execution boundaries. Open Methodology, Fields, Magnetotellurics, M05/M06 for the mathematical chapters. Implementation uses the same family and method path for strict parsing, source/admission, field negatives, actual TRF algorithm, function/array shapes and worked exercises. Replay comparators preserves the existing synthetic TRF/Adam/neural content, explicitly separate from online EDI. All copy, equations, figure labels and answers are EN/ES. Shared theme/language controls remain unchanged. [Scientific chapter](../problem-types/05_online-mt-course.md).

Read the explicit assumptions before interpreting a curve. EDI is not raw MT time-series estimation; M06 fixes thickness and only fits eligible full-tensor observations. cl061 is a QC-only field negative. A course case control loads an actual recorded synthetic solve with a source hash, not a new API job. Its plot lets the reader compare observed/predicted real impedance and inspect a frequency value, while model and data/prior/holdout readouts update with each control. [Exercise implementation](../../frontend/src/components/OnlineMTExercise.tsx).

## Worked lesson sequence

1. Derive the45-degree halfspace phase from exp(+i omega t), and native-to-SI conversion from E/B versus E/H.
2. Before revealing M05's variance answer, compute marginal SD for complex VAR8Ω²:2Ω. Explain why treating VAR as per-real-component changes weighting.
3. Select fixed h350m and inspect the original noisy fixture's20/4 train/holdout partition and120/12ohm m evaluation target. Truth is never a solver argument.
4. Predict how imposed h280/420 changes resistivity, then load both actual control records. Observe that h280 holdout improves even though the known synthetic thickness is350. Do not retune on holdout.
5. Compare the one-layer baseline and beta0.01 control, keeping observations/sigma/mask unchanged. Separate data and prior terms rather than only total cost.
6. Reveal the conditional interval explanation: unknown structure/h, static shift and correlated errors are outside its sampling law.
7. Read cl061's original receipt and failed all-frequency tensor scores. Reject a proposal to mask offending frequencies or fit only a smooth xy to manufacture M06 admission.

These exercises address physical/numerical interpretation, not globally unique geology. [SciPy1.15.2 TRF](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.least_squares.html), [source-bound walkthrough](../problem-types/05_online-mt-course.md).

## Local numerical reproduction

Use a repository-local precompute/ingestion environment with NumPy2.2.6, SciPy1.15.2, mt-metadata1.0.10 and the existing pipeline dependencies. On Windows the preserved `.venv-ingestion` satisfies this. Course reproduction reads the existing original EDI fixture and computes into memory; it never writes canonical experiments. It applies the actual online frozen mask/three-start rule via the existing core solver, then reuses the selected main start for sensitivity controls and100 for the halfspace. The fixture target is outside solver inputs.

```powershell
.venv-ingestion/Scripts/python -m pytest -o addopts='' tests/test_online_mt_course.py tests/test_mt_recovery.py tests/test_edi.py -q
.venv-ingestion/Scripts/python tests/test_online_mt_course.py
```

The second command prints `COURSE_WORKED_JSON=` followed by the actual execution record; it does not overwrite the committed course record. Independent reflection algebra checks the tanh recurrence at relative1e-11, and displayed model/objective/response replay uses relative1e-7/absolute1e-9. Byte counts/hashes are exact. Two-layer boundary controls include rho1/6000 and h2/4000. Bootstrap test executes20 actual refits and independently replays one generated observation. Full-tensor malformed/unit/sign/frame tests are the existing strict EDI suite, not a source-label test. [Numerical gate source](../../tests/test_online_mt_course.py), [record](../../frontend/src/data/online-mt-worked.json).

For measured cl061, acquire the original under its reviewed rights receipt into the ignored `data/downloads/clear-lake/USGS-GMEG.2022.cl061.edi`, then rerun the gate. It must be16411bytes and the stated SHA; absence produces an explicit skip. Never substitute synthetic bytes or update a source digest to call an old result fresh. The inversion rejection should execute before any layered solve. [Measured acquisition and screen record](../problem-types/mt-recovery.md), [USGS release](https://doi.org/10.5066/P14KAQ3M).

## Local course/render verification

```powershell
cd frontend
npm ci
npm test
npm run build
npx playwright test --config playwright.mt-course.config.ts
```

The scoped Playwright harness serves only loopback4337; it creates no public origin and runs no API worker.32tests cover the16 EN/ES×light/dark×desktop/phone×normal/reduced-motion combinations, separately checking Introduction and the two-page course. Pointer navigation begins at App, activates every M05/M06 topic, checks actual translated headings, KaTeX/citations, SVG rendered label bounds and document horizontal fit, reveals all answers, changes all five worked results and revisits replay comparators. Screenshots/report/traces stay ignored under `frontend/node_modules/.mt-course-qa/`; prior private outputs are not staged. Manual rendered inspection supplements the numeric bounds gate. [Validation receipt](../validation/online-mt-course-review.md).

## Your eligible EDI and the worker boundary

The course branch does not import or modify the backend from PR100. Its mathematical implementation reference is7b69404; current owned CSV processing is developafac8ab. Follow the reviewed [online EDI guide](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/0970a09/docs/guides/08_online_edi_mt.md) and [exact contract](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/0970a09/docs/data-contract/02_online-edi-mt.md) only in an admitted private runtime. Do not enable the host flag or submit to an assumed public API based on this course.

An owner uploads exact bytes/rights/physical declarations, creates an awaiting-QC envelope, runs full-tensor M05 and submits M06 only with the same owned dataset's passing M05 job. Original5MiB and method-specific counts/ceilings are strict, not suggestions. Missing/conflicting metadata, malformed tensor, unsupported rotation, foreign owner and ineligible source reject. A512-frequency passing M05 cannot enter M06; cl061 never can. Result truth is null for supplied data. [Contract boundary statuses](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/0970a09/docs/data-contract/02_online-edi-mt.md).

Export/re-import verifies exact members, source/code identity, arrays, forward prediction and serialized residual identity. It does not bundle raw bytes or confer redistribution permission. Keep permitted original source separately for reprocessing. Full offline GPU/FWI/learning results use their own artifact contracts and cannot be relabelled online MT. Actual Linux admission and disk/headroom, canonical full assembly and integrated frontend acceptance remain separate live gates; no merge/deploy/activation occurs here. [Approved product SDD](../design/SDD.md).
