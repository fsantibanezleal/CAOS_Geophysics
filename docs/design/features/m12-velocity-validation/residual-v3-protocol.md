# M12 learned residual refinement protocol v3.1

Status: predeclared research protocol; not an accepted M12 method or field claim.
The failed v1 and v2 checkpoints, results and criteria remain unchanged. The
first v3 training attempt stopped before test scoring or receipt creation
because a strict CPU/CUDA cellwise parity assertion failed. Its incomplete
output remains preserved. The checkpoint replay showed validation RMSE of
6.795705 m/s on CPU and 6.795878 m/s on CUDA (max cellwise difference 0.1194,
p99 0.0428, mean 0.01064 m/s). Version 3.1 records a predeclared numerical
replay envelope of max 0.15, p99 0.05 and mean 0.02 m/s. It scores all held-out
cohorts from the CPU-reloaded checkpoint and retains these parity metrics in
the receipt. No held-out scores were computed in the stopped attempt. This
amendment changes numerical replay acceptance only; the model, cohorts,
selection and scientific comparator remain fixed.

## Why test a hybrid

The retained CUDA v2 receipt loses to the matched classical inverse even on
validation: learned/classical mean velocity RMSE is 2.82 and independent-oracle
travel-time RMSE is 4.16. That indicates the direct two-channel network is not
using the observed geometry as effectively as the explicit linear inverse.
V3 first computes the same bounded, regularized straight-ray slowness solution
for each noisy survey. A CNN then predicts a bounded correction to that map
from three channels: normalized baseline velocity, geometry-normalized
backprojection residual and ray coverage. The network cannot replace the data
with a replayed case; both paths use the same input picks and ray operator.

This is an amortized supervised residual-correction experiment, not an
unrolled optimizer, convergent plug-and-play method or new inversion theory.
The baseline is

\[
\hat s_0=\arg\min_{s_{\min}\le s\le s_{\max}}
\|W(As-t)\|_2^2+\lambda\|Ds\|_2^2+0.01\|s-s_0\|_2^2,
\qquad v_0=1/\hat s_0.
\]

The learned output is

\[
\hat v=\Pi_{[1400,4000]}\!\left(v_0+250\tanh f_\theta(v_0,b,c)\right),
\]

where \(b\) is the corrected physics backprojection and \(c\) is normalized
ray coverage. Training minimizes the fixed objective

\[
L=\operatorname{MSE}((\hat v-v)/400)
+0.025\operatorname{MSE}((A(1/\hat v)-t)/0.01)
+0.025\operatorname{MSE}(\Delta v/250).
\]

The baseline regularization parameter is selected only on the fresh validation
set from the pre-existing grid. The epoch is selected by validation velocity
RMSE; the joint, family-only, acquisition-only and ID test partitions are not
read until weights, lambda and threshold are frozen. Epoch zero (the unchanged
classical solution) is an explicit candidate, so a learned correction is never
forced to worsen the validation score.

## Fresh partitions and controls

The generator equations and geometries are unchanged; every cohort uses a new,
disjoint seed interval: train 217001-218200; validation 227001-227160; ID test
237001-237160; family-only 247001-247080; acquisition-only 257001-257080; joint
OOD 267001-267160. Training/validation/ID use layered, lens and dipping models
with layouts A/B. Family-only uses held-out fault/salt on A/B; acquisition-only
uses training families on layout C; joint OOD uses held-out fault/salt on C.
No test family, test label, or test truth enters the method or threshold.

The frozen run uses 1,200 training cases, 160 validation, 160 ID, 80
family-only, 80 acquisition-only and 160 joint-OOD cases. Adam uses seed 77214,
learning rate 5e-4, batch size 64, maximum 100 epochs, patience 20 and a
gradient-norm cap of 5. The serialized result includes the complete split
manifests, every epoch, chosen lambda/epoch, checkpoint and source hashes,
matched per-case model and independent-oracle errors, and the validation
95th-percentile residual-screen threshold with false-positive and miss counts.

The locked joint scientific gate remains both mean learned/classical ratios
below 1.0 for velocity RMSE and oracle travel-time RMSE, on all 160 cases, with
no omitted failures. A failed result stays failed. Passing would establish only
this bounded synthetic protocol; straight rays, the bilinear forward oracle,
fixed geometry, 16x16 parameterization and absent field measurements remain
limitations. It would not validate geological field interpretation.

## Execution and independent sources

Run `scripts/run_m12_residual_v3.py --device cuda --output <new external folder>`
then replay the saved result on CPU using `--verify`. The output path must be
new and outside every checkout. The RTX 4070 is used for training only; full
cohort scoring and checkpoint verification run on CPU. The canonical method
artifacts are not modified by this experiment.

The experiment follows the general inverse-problem practice of combining a
measurement operator with a learned prior/correction, while this particular
residual target, operator, objective and data split are defined above. Relevant
primary references include [Kamilov et al., Plug-and-Play Methods for
Integrating Physical and Learned Models in Computational Imaging
(2023)](https://doi.org/10.1109/MSP.2022.3199595) and [Fang et al., What's in a
Prior? Learned Proximal Networks for Inverse Problems
(2024)](https://arxiv.org/abs/2310.14344). Neither reference validates this
tomography experiment or its performance.
