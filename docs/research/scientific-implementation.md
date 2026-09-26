# Scientific implementation: recovery revision 0.04.000

Primary sources motivate the methods; actual objectives and settings are defined
by the executable scripts and exported solver records. The [0.03 audit](audits/implementation-0.03.md)
is preserved to distinguish corrections from retrospective relabelling.

## Integral gravity and magnetic inverses

`potential.py` uses SimPEG rectangular-prism gz and linearized TMI operators on
28×24×16 cells. Coordinates are east/north/up in metres, flattening x-fast.
Density contrast is g/cm³, gz mGal positive upward, susceptibility SI and TMI nT.
The inducing field is 50,000 nT at inclination 60°, declination 12°.
The 16×16 receiver grid is at 60 m or 180 m height.

`spatial_inverse.py` minimizes `||Wd(Gm-d)||² + beta m'Qm`, with `Wd=diag(1/sigma)`
and physical spatial derivatives of length 240/240/140 m. Independent calibration
selects depth exponent 0.375. Discrepancy selects beta before the declared strength
multiplier. Four IRLS updates modify smoothed L1 smallness and retain spatial L2
derivatives. No positivity, terrain correction or regional removal is implied.
Vector inversion estimates three normalized-magnetization components. Amplitude
and direction errors are separate. Choclo independently checks gravity/magnetic
signs, scales and vector conventions. See [objective and calibration](../problem-types/03_potential-recovery.md).

## Layered magnetotellurics and EDI

`electromagnetics.py` propagates E/H impedance upward from a half-space, with
exp(+iωt), known thicknesses and isotropic layers. Bounded TRF, projected Adam
and the per-sounding neural parameterization share a mean-of-real-component-squares
objective, adjacent log-resistivity penalty, 1–6000 Ω m bounds and 100 Ω m start.
The legacy `mt-lm` key is TRF, not LM. Saved states are copied and reevaluated
after updates; rejected TRF residual evaluations are identified explicitly.

`edi.py` wraps the official mt-metadata parser with strict units, time-convention,
frequency, error, component and rotation validation. Native E/B units convert
to E/H ohms. Arbitrary rotation cannot fabricate independent component errors
when covariance is absent. Original analytic fixtures test native units,
negative-time SI data, axis rotation and a noisy rotated two-layer sounding.
Generic inputs retain unknown truth; fixture targets remain separate labelled data.
See [full contract](../problem-types/mt-recovery.md) and [executed evidence](../problem-types/mt-recovery-validation.md).

## Acoustic full-waveform inversion

`seismic.py` uses Deepwave finite differences and automatic derivatives on 128×96
samples at 12.5 m, 0.5 ms integration, 1.6 s records, three known Ricker sources
and 300 m absorbing layers. The independent start is `1800+0.88z` m/s. Every
fifth receiver is withheld from objectives and selection.

A data-only 1D background precedes control grids 9×12, 17×24 and 33×48, bounded
to 1400–4400 m/s. Matched full-band and continuation inverses share background,
spatial budget and regularization. The sixth-order Butterworth-amplitude filter
has explicit 3/5/8/14 Hz cutoffs, not a short moving average. Each stage has 28
strong-Wolfe L-BFGS calls. Terminal updates, final prediction, model, last frame
and objective records describe the same selected state. Raw waveform MSE,
filtered stage objective and regional model errors are distinct quantities.
See [calibration, nominal recovery and remaining bias](../problem-types/02_fwi-recovery.md).

## Joint priors, learned inference and uncertainty

`joint.py` compares uncoupled, physical cross-gradient and Gaussian-mixture priors
using matched observations, initialization and 80-call budgets. The physical cross
penalty is normalized by its independent initial value; L-BFGS has a diagonal
Hessian preconditioner. `petrophysics.py` fits 640 separate synthetic laboratory-like
pairs by EM. This explicit mixture prior is not a reproduction of SimPEG's PGI
optimizer. Samples, parameters and conditional responsibilities are exported.
The decoupled case violates the paired-property prior. Coupling can worsen recovery.

`learning.py` trains a column-density CNN and a 12-dimensional observation
autoencoder with 800/160/160 disjoint training/validation/test realizations.
The spatial L2 and CNN test receive identical noisy observations and the same
physical target. Another 160 realizations calibrate the novelty threshold.
Eighty withheld ring/crossed geometries test detection. Confusion counts and AUC
are exported: the executed detector misses all 80 withheld examples. The CNN also
fails to beat the classical column inverse on the two displayed withheld references.
Classical regularization is explicitly not an intervention on frozen checkpoints.

Potential-field ensembles perturb observations at fixed prior and selected beta;
MT ensembles re-invert complex-Gaussian resamples around the selected TRF model.
These are conditional repeatability intervals, not posterior geology. Independent
calibration measures coverage, including regularization bias and noncoverage;
coverage is not assumed to equal the nominal 95% quantile span.

## Release gates

`evaluation.py` separates active/held-out data error, baseline-relative model
error, correlation, support/background error and centroid/direction error.
`validate_recovery.py` recomputes physical predictions and state identities and
requires three nominal reference FWI cases to improve independent starts.
Failed variants remain visible. `catalog.py` rejects stale or missing runs.
Static guards verify the full matrix, EDI hashes, checkpoints and verdicts.
Numerical tests, rendered inspection, Git promotion and host verification are
separate stages. A successful build alone is not scientific validation.
