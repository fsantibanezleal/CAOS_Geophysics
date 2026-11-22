# Fixed revised experiment

Keep the original800 m/16x16 cell and independent A/Q ray construction. Original
source/checkpoint/receipt is untouched. All new identities use m12-physics-v2.
Cohorts have800 train,160 validation,160 ID,80 family-only,80 acquisition-only,
160 joint; seed bases117001,127001,137001,147001,157001,167001 respectively.
Families and A/B training versus C test geometry follow the original definitions.
These are fresh realizations but the synthetic family definitions and geometry
were already known; no claim of independently discovered unseen geology is made.
Noise stays independent Gaussian1 ms per ray. Fixed scales/no test normalization.

Let L=A1 in metres and c=A.T1 in metres. Feature slowness perturbation is
h=A.T((t-As0)/L)/c, units s/m; unsupported cells get0 via explicit masked division.
The first channel is -h*v0^2/400, dimensionless first-order velocity perturbation.
The second is c/max(c), dimensionless coverage. Every supplied ray has positive
length; invalid length/shape/nonfinite input rejects. This is a smoothed linear
feature, not the exact inverse for heterogeneous structure.

CNN: existing24-channel, three residual-block3x3 architecture, zero-initialized
last1x1 layer; v=1400+2600 sigmoid(logit((v0-1400)/2600)+network(features)).
Unlike the old600 m/s perturbation bound, this can represent the full declared
velocity interval. Bounds are chosen from the already fixed physical generator,
not a held-out optimum. Initial output exactly v0 to float32 precision.

Adam0.001, batch64, exactly40 full epochs, seed77213; normalized model MSE in
400 m/s plus0.1 normalized cell-ray data MSE in10 ms. The minimum validation
velocity RMSE selects weights, ties earliest. Same classical lambda candidates
1,10,100,1000 selected on validation only. After weight/lambda selection, compute
validation95th-percentile learned Q residual then evaluate the four locked test
cohorts once. No grid/candidate/threshold changes after seeing them.

Emit new exclusive NPZ checkpoint and JSON receipt with source/legacy-operator
hashes, device/versions, full split/model/noisy-data hashes,40-epoch curve,
checkpoint hash, all per-record/group metrics, residual flags and unchanged
both-ratios-below1 advantage predicate. A mechanical fixture may use1 epoch and
12 records/cohort but is labelled fixture-only. Verification recreates cohorts,
reloads weights on CPU and checks every record, counts and flags, using the
original1e-5 relative/1e-4 absolute cross-device metric tolerance. No canonical
rebake/public artifact replacement is authorized by a training run.
