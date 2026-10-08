# Objective-preserving HP component epoch / Epoca HP

Parent approval: 2026-10-08, after full private precode review and primary
Stanford SOL / SciPy review. This authorizes this scoped component implementation,
not field eligibility, host admission, route mounting or activation. Frozen v1/v2
and their opened adverse controls remain unchanged. No source body or tolerance
is changed. A separately named strict full Result/CLI/export/replay epoch remains
necessary before any97-fit result can be published as implemented.

The objective is J(c)=||Ac-b||²+lambda||c||², A=W^(1/2) G S^(-1),
G=1/d metres^-1, S=the existing UNWEIGHTED population standard deviations.
Physical coefficients are q=c/S. P_j=1/sqrt(sum_training A_ij²+lambda).
LSMR sees B=[A;sqrt(lambda)I]P, d=[b;0], scalar damp=0 and c=Pz.
Both blocks MUST be scaled. P uses geometry, training sigma and lambda only.
No intercept, clipping, centering, source filtering, response-selected scaling,
outer tuning, warm start or tolerance relaxation is permitted.

The B recurrence condition estimate is explicitly labelled B, not an A condition
estimate or a rigorous bound. Unchanged atol/btol1e-12, conlim1e8, maxiter2000,
successful codes0/1/2/4/5 and original-coordinate relative gradient1e-9 all apply.
The direct-kernel gradient is independently calculated even after code7, but
does not turn code7 into success. Actual stop, coefficients/hashes, recurrence,
original objective/gradient and action counts survive refusal.

## Gates and fail-first execution

`tests/data/test_magnetic_line_survey_hp.py` independently constructs bounded
dense G, STD, A, H and B, checks both actions/adjoint/objective/P reconstruction
and dense least-squares reconstruction, weighted/unweighted, zero response,
invalid lambda and retained stop7. Its AP-only regularizer is an actual negative
control, not a modified production objective.

`scripts/run_m03_hp_prerequisite.py` executes these oracles, binds their source
hashes/XML, then launches ONE actual cold Job worker. A new output path must not
exist. The worker binds the actual historical S3 plan/correction/failure bytes,
computes the full prospective proof BEFORE native imports/geometry allocation,
independently rebuilds all16 maps and writes a NEW HP pre-value seal BEFORE
training response decoding. It unpacks ONLY249 declared foldC corrected values;
encoded chunk custody hashes are not full-channel numerical decoding. No sigma
is opened for this unweighted candidate. No outer score/value is decoded.
Candidate39 is200m,500m depth,lambda0.0001,249rows/127sources. It executes once;
failure blocks the dependent matrix. This script cannot run97 fits or outer.

## Pinned allocation audit BEFORE allocation

SciPy1.15.2 LSMR source SHA256
`f1e60be3f5216f602bf33535acc72474aa80fbe0149d5929145d0432bc29e0ce`.
Its x,v,h,hbar are M vectors; rhs/u and a temporary normalized u/action are
virtual N+M vectors. x/h/hbar/v updates are in-place with at most one scaled
M temporary. Our actions additionally hold Pv, A(Pv), sqrt(lambda)Pv and an
N+M concatenation, or A^T u plus the scaled identity tail and output. P's pass
holds two M compensated sums and bounded kernel/weighted-square blocks. The
original diagnostic holds six M accumulators and bounded row blocks; returned
z,c,q,P/scales/source maps are counted concurrently, not assumed freed.

The ADDITIONAL8*(24*N+32*M) allowance conservatively exceeds these additional
live vectors, and is added to EVERY old phase bound, including scratch. Original
8*R*C kernel temporaries, existing16 maps and original vectors remain in the old
bound, never discounted. Augmented rows N+M are explicitly reported.

4006*n*m per fit includes2000 forward+2001 adjoint+2 STD+2 original-gradient+1
weighted-P passes. Independent P reconstruction is EXTRA:3*n*m (2 STD+1 weighted)
for every mandatory identity and optional comparator, not just the winner.
The old final native objective/gradient/prediction allowance remains additional,
conservatively including duplicate scales. Exact inner shapes each occur8 times.
Worst-final geometry is used, not the selected winner. Prediction/grid/outer
costs remain separately counted. Logical192, physical1million,4GiB memory,
32GiB scratch, CPU21600s, wall43200s, parent300s and one process remain unchanged.

Actual retained corrected S3 closure is125logical/104arrays/5dictionaries,
NOT the precode example119/98. HP reserves126logical/104arrays, adding ONE
97-row identity table (no97 P arrays). Each row<=4096B:397312B page+2097152B
manifest=2494464B retained, plus4096B index reservation,2 physical members.
Comparator98 would reserve2498560B. The actual native closure must still be
verified; these are arithmetic bounds, not measured host acceptance.

For363rows/max292sources: additional vectors144448B;
all mandatory fit pairs10939745040; independent P reconstruction8192520pairs.
The prospective proof records all unchanged auxiliary/member/index/prediction
terms too; it does not echo the old25-fit bound or fabricate actual97 counts.

## Actual first prerequisite, 2026-10-08

`E:/_Temp/geophysics-m03-resume-20261008/hp-prerequisite2` retains seven PASS
small oracles and ONE actual candidate39 solve. The fresh16-map HP seal and
full proof preceded training-value decoding. Solve FAIL: istop7,2000iterations,
2000forward/2001adjoint, relative original gradient1.0764842455268023e-8>
unchanged1e-9. Absolute gradient1.0125350297346836e-5;
denominator940.5943783591337; objective106.19072799896819. Independent native P
and direct original-gradient reconstruction PASS, not convergence. B recurrence
conda1612.7787210718166 is explicitly NOT A's estimate.

Full failure JSON SHA256
`c4a4b9ac1f095f9296cc8ff3d627055c6251a9cce789d5df4d483891cb9b5b91`.
Physical coefficients SHA256
`b62f3e61e8156e1648d1f07cbfa3ec8c793e8419e62eb1a3b56099c9c4cc08d5`;
P SHA256 `17a1f0c3468dbd7578f4c56ccc5ea1a78da842044015dde1935ad4f7a4e4520c`.
Actual child CPU11.234375s,RSS245391360B,commit218017792B,wall84.27582079998683s,
scratch395044B,one total process/zero active at drain. Generic controller's
exit2 receipt labels resource_refused; the retained scientific receipt states
the actual nonconverged cause. Do not relabel that controller receipt PASS.

The earlier hp-prerequisite1 launch stopped during geometry traversal on a
producer-file deletion race: no HP pre-value seal, training-value record or
candidate solve was reached. Its evidence remains retained. The monitor fix
permits ONLY independently confirmed absence in active traversal, never a
present unsafe entry or terminal missing bytes; its negative guard passed.
The second launch is the FIRST and ONLY HP candidate execution, not a solver
retry. Full97 and outer remain BLOCKED by that first failed prerequisite.

## Espanol: limites y evidencia

Se transforma tambien sqrt(lambda)I; penalizar z cambiaria el objetivo y esta
prohibido. El gradiente independiente permanece en coordenadas originales.
Codigo7 sigue siendo FAIL aunque su gradiente se conserve. La condicion es una
estimacion de B, no de A. Los fallos S1 y100/50 siguen siendo historicos adversos.
La prueba cuenta126miembros logicos reales, no el ejemplo120. Solo se decodifica
el entrenamiento declarado del candidato39. Un PASS de este componente no es
PASS97, aceptacion predictiva, verificacion del proveedor8201 ni despliegue.
