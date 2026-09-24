# Source-to-content dossier: 2026-09-24

The audit began at baseline 9b8f47e and was updated after the authorized spatial refinement.
All canonical results and neural checkpoints were regenerated for 0.03.000. The public site explains these algorithms,
not more sophisticated algorithms from related literature.

## Potential fields

`potential.py`: SimPEG 0.25.2 `Simulation3DIntegral`, geoana engine, gz and linearized TMI.
28×24×16 prisms, 80×80×70 m. Receivers 16×16 at 60/180 m. Gravity g/cm³→mGal;
susceptibility SI→nT. Inducing field 50,000 nT, inclination 60°, declination 12°.
Let s_j=||G_:j||₂, W_jj=1/max(s_j,0.06 max s). Set a=||GW||F/sqrt(N), A=GW/a,
b=d/a. For diagonal H, minimize ||Aq-b||²+β qᵀHq; C=H⁻¹ and
q=C Aᵀ(ACAᵀ+βI)⁻¹b, m=Wq. L2: H=I, one solve. IRLS: eight solves,
ε=max(0.12 max|q|,1e-10), H_jj=(q_j²+ε²)^(-1/2), divided by median(H).
β=.018/.25. No derivative smoothness, bounds, positivity, β cooling, noise-whitening or stopping
test. Sigma is used for WRMS reporting only. Vector magnetization concatenates three component
blocks; displayed magnitude is effective susceptibility, not A/m. Scalar reference truth is not a
direction-error oracle. Remanent direction is normalized [0.80,-0.55,0.23].

Primary context verified: [SimPEG gravity tutorial](https://simpeg.xyz/user-tutorials/inv-gravity-anomaly-3d/).
The custom data-space solve is derived from the local source; the tutorial's directive-driven
optimization must not be attributed to this implementation.

## Magnetotellurics

`electromagnetics.py`: μ=4π10⁻⁷ H/m, ω=2πf; halfspace Z=√(iωμρ). Upward recursion with
k=√(iωμ/ρ), w=√(iωμρ), t=tanh(kh), Z_j=w_j(Z_(j+1)+w_j t)/(w_j+Z_(j+1)t).
ρa=|Z|²/(μω), phase=arg Z. Known thicknesses, only resistivities inverted. 36 log frequencies
0.01–100 Hz, acquisition .001–100, coverage alternate18. Noise independent real/imag components
with σ=.025|Z| or .10|Z|. Complex WRMS expectation at truth is √2, not1.

SciPy `least_squares` default is TRF, two-point Jacobian, linear loss; NOT LM despite legacy key.
Residual concatenates real/sigma, imag/sigma and √β diff(logρ), bounds1–6000Ωm,
initial100Ωm, max_nfev160, default ftol/xtol/gtol1e-8. Saved residual evaluations include finite
difference probes and are not accepted iterations. Adam direct logρ:250steps/.06, no bounds;
neural:1→24→24→1 tanh, logρ=1+7 sigmoid(net(index)),420steps/.025, no pretrained inverse.
These minimize mean|r|²+β mean(diff(logρ)²), not the same relative penalty as TRF's sums.
Every10steps stored, minimum recorded objective selected. The direct-Adam tensor is modified in place
before a frame is copied; do not claim exact frame/history equality. MT result metrics include ALL
frequencies, including omitted coverage frequencies.

Primary references verified: [SciPy 1.15.2 TRF API](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.least_squares.html),
[physics-guided MT paper](https://arxiv.org/abs/2410.15274). The latter motivates per-sounding
optimization, not a reproduction claim.

## Seismic

`seismic.py`: constant-density acoustic Deepwave, grid128x×96z,12.5m,dt0.5ms,nt2200,
fourth-order spatial accuracy,PML24,max_vel4600. Sources at(300,75),(800,75),(1275,75)m;
40receivers at integer grid indices from linspace(6,120). Ricker8Hz (salt9Hz), acquisition5Hz.
v0=1800+11iz; v=1400+3000 sigmoid(p). Objective mean|Lw(pred)-Lw(obs)|²/mean|obs|²
+4β[mean((Dxv)²)+mean((Dzv)²)]/1e6. D are cell differences, not derivatives per metre.
Adam28steps,lr.045, gradient norm clip10, β.002/.06. Moving average widths41steps0–8,
17steps9–17,1steps18–27, replicate padding. Direct variant always1. Source frequency does not
change during continuation. Selected model minimizes raw unfiltered normalized waveform MSE
among pre-update predictions. History is that raw MSE; pressure snapshots every24ms, gathers4ms.
No elastic modes, attenuation, density inversion, free surface or posterior uncertainty.

Primary reference: [Deepwave FWI example](https://ausargeo.com/deepwave/example_fwi).
The local moving average differs from the example's frequency-filter implementation.

## Joint

`joint.py`: a=ρ/.5,b=χ/.03; loss=mean((Gg*.5a-dg)/σg)²+mean((Gm*.03b-dm)/σm)²
+λ mean((∇a×∇b)²)+.015(mean a²+mean b²). `torch.gradient` in [z,north,east] cell indices,
central interior/one-sided boundary; no spacing argument. λ4/25,180Adamsteps,lr.008.
Starts density from case L2 and susceptibility from independent solve β.04. Final model returned,
history every6steps,total objective; frames post-update but loss pre-update.
Cross-gradient metric is mean vector norm, while penalty is mean squared components.
Both data sets masked for optimization; final joint WRMS includes all stations.

Reference: [SimPEG cross-gradient tutorial](https://docs.simpeg.xyz/latest/content/user-guide/tutorials/13-joint_inversion/plot_inv_3_cross_gradient_pf.html).
This app's normalized cell-index penalty is not the tutorial's mesh-weighted objective or PGI.

## Learning

`learning.py`: train/validation/test800/160/160; seeds18001/29001/39001, model seed7721,
noise seed5001. Four generator families, whole-realization split; oblique/ring excluded. Scale
s_d=SD(clean training observations), noisy input=(d+N(0,.02s_d))/s_d, targetsΣ_zρ*70/400.
CNN conv1→16→24,kernel3,padding1,GELU,adaptivepool4×4,flatten384,linear96,GELU,linear672.
AE flatten256→64→12→64→256,GELU between hidden layers. Adam lr.001,batch64,180epochs,
best validation MSE checkpoint, no test selection. Training history stores last minibatch loss,
not epoch-average; validation history sampled every5epochs. AE threshold validation99th percentile.
The scores and frozen threshold are recorded separately for the withheld oblique and ring cases.
A below-threshold score on either is a missed unfamiliar geometry, not proof of in-distribution geology. CNN target is a column, not a3D reconstruction.
Classical held-out baseline uses CLEAN observations while CNN uses noisy inputs, with fixed untuned
regularization. Show numbers but explicitly disallow a controlled superiority claim.

Algorithm reference: [Adam original paper](https://arxiv.org/abs/1412.6980). Architectures and all
training constants are original local implementation details, not InversionNet/OpenFWI reproductions.

## Editorial rule

Every result explanation identifies observable, units, comparison population and an inference limit.
Remove slogans, competitive claims about visual quality, and assurances about being a real instrument.
Keep setup/hosting in the architecture dialog and reproduction documentation; scientific implementation
must explain equations, discrete updates, stopping criteria and saved-state semantics first.
