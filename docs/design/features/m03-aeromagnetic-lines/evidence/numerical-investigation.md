# Frozen original dipoles: actual failure evidence

The [intake-bound investigation](s1-intake-bound-investigation.json) is actual
execution of the frozen geometry, original S1 dipoles, inner candidate fits
and one outer evaluation using the verified pinned Harmonica/Verde engines.
It is not a complete processing run, Result schema, field case or admitted job.
Correction operators, a translated intersection and relative-gauge QR are
implemented separately; the full correction DAG/crossover inventory/export/
replay/spectrum/continuation and allS1..S6 workflows remain incomplete.

Original authored CSV SHA256 is
`ac28e5f7c8344b94ebe0c408484eede8ade5a4074c8ef44661bcfe774ff0bfae`.
The sidecar identifies original_synthetic_acquisition, actual nT weak projection,
synthetic2001 clock and engineering datum, with unknown uncertainty kept null.
Dataset/request/channel/geometry identities are independently bound in the
receipt. Geometry is sealed before any dipole calculation. No field bytes
were acquired or relabelled, and no sigma was guessed.

Selected depth500m/damping0.0001 is determined by the three inner folds only.
Inner mean RMSE is15.246552104811881nT; all eight candidates retain their actual
fold results. Outer33-row geometry coverage is1.0, with25 actual harmonic fits
and one outer opening. The geometric comparator is not implemented in this
investigation; the approved total ceiling26 is unchanged.

Held-out observed-minus-predicted RMSE is18.799740861734186nT, signal RMS
5.1932793077546116nT, and the fixed5%/1e-6nT-floor limit is
0.25966396538773057nT. The predictive target FAILS. Final augmented-system
condition is1822.2899686716455, below the unchanged1e12 numerical condition
refusal. Neither condition nor geometric support proves predictive fidelity.
This failure is not xfailed, skipped, hidden by an average or weakened.

Independent augmented-QR coefficient/new-coordinate prediction checks pass
at the frozen tolerances. Independently coded direct SI dipoles agree with
the official Harmonica vector engine at noncentral coordinates/heights.
Perturbing only outer observations by+10000nT in a separately byte-bound
authored input leaves inner scores, training SHA and selected candidate
unchanged. That checks value isolation, not successful physical prediction.
Sources are training-only blocks, not the actual generating dipoles.

[The earlier operator-only receipt](s1-frozen-investigation.json) is retained
unchanged. It used the geometry scaffold's dataset/channel fields and a separate
actual S1 sealed-value identity, not a complete raw-byte intake. Its metrics
remain a valid operator experiment, but it does not establish original CSV
custody. The later intake-bound receipt validates actual raw/sidecar/request
identity before the same calculation; the original failed metric is reproduced.
Neither receipt has an internal self hash.

The [current-source repetition](s1-current-source-investigation.json) follows
fixed-error native-array hardening and reproduces the same frozen selection,
outer metric and failed limit using current source bytes. Its source pins and
one-process timing are independent of the two historical receipts. The first
receipt wrapper addressed a nonexistent intake key, dataset_version_sha256,
and raised KeyError after calculation; it wrote no receipt. The corrected
wrapper uses the actual dataset_sha256 field without changing science.

The initial correction/intersection/offset tests had five genuine missing-module
failures. Their first implemented combined run retained35passes/one failure:
the test expected a2m segment at1e8m origin to pass, whereas its parameter
tolerance exceeds the fixed1e-6 limit. The test now expects this actual refusal
and uses resolvable1000m geometry for the positive translated control. No
tolerance changed. The next run had36passes. Original T05 controls then had
two missing-generator failures. Subsequent combined runs retain the S1
predictive failure while dipole/QR/seal controls pass. XML pins and exact
source/test hashes are recorded separately; historical failures remain.

The native-shape negative control first failed with a raw TypeError for a
zero-dimensional NumPy array. Explicit dimension/scalar checks now reject
malformed arrays with the fixed contract envelope before conversion, and
finite float64 range is checked after casting. The original RED XML is
retained. The final focused run has40passes, one genuine S1 quality failure,
zero errors and zero skips; it is not a successful method suite. Exact test
names and raw XML identities are in [the test receipt](numerical-test-checks.json).

The IGRF test is only a negative unreviewed-receipt refusal plus independent
rereference-sign arithmetic. It cannot satisfy the evaluated IGRF/datum gate.
Unknown reference/clock/source hashes cannot authenticate an evaluator.
The local numerical functions do not run an API child or complete the original
approved full-survey/user-file/field workflow. No native CPU/RSS/stop profile,
graphical product acceptance, provider comparison or parent acceptance is
asserted. The two single-process wall/CPU observations are not a30-run cold
profile; peak RSS remains explicitly unmeasured.

No frozen geometry, source blocks, candidate depths/damping, direction,
5% quality target or numerical tolerance was revised using the outer result.
Independent solver/physics agreement narrows the investigation, but a review
must distinguish inadequate approximation/sampling from implementation defects
before any method-design change. Further calculations cannot regain an
untouched outer-test label by reusing this observed control.
