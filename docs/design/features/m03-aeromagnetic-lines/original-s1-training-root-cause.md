# Original S1 training-basis diagnosis / Diagnóstico de base original S1

## English

`magnetic_line_survey_diagnosis.diagnose_retained_s1` consumes the already
executed, immutable original streamed S1 artifacts, not newly generated truth.
Its separate closed worker plan requires an actual Job before any decoding or
scientific import. It verifies the original 45,539 bytes/SHA256, retained
diagnostic and GeometrySeal hashes, every member closure, exact 294 original
training indexes/row-ID hash, the selected 500m/0.0001 policy, and all 66 original
400m half-open source blocks independently against the protected geometry
oracle. Source/scales/coefficients retain their exact roles, units and identities.
It cannot process a substitute field file or select a changed model.

The dense oracles are deliberately restricted to this small original 294×66
control. They are never the global large-survey operator. Reconstruct direct
G_ij=1/|x_i-p_j| and unweighted population scales s_j, then A=G/s. Independently
solve [A;sqrt(0.0001)I]c=[y;0] with SVD least squares and reconstruct the full
sum-of-squares plus penalty objective. Separately take the numerical column-space
projection U_r U_r^T y from SVD(A), with cutoff eps*max(N,M)*sigma_max. No mean
removal, intercept, normalized weights, changed source height, damping or outer
observations enter either oracle. Custody hashes outer bytes but does not decode
them into an oracle or evaluate a new outer prediction. Production fits=0,
independent training oracles=2, new outer evaluations=0.

Current retained streamed artifacts reproduce:

| Training-only quantity | Observation |
|---|---:|
| Numerical rank / original sources | 66 / 66 |
| Numerical singular-value cutoff | 1.737488427721417e-11 |
| Best numerical training projection RMSE | 3.560874605601467 nT |
| Fixed damped SVD oracle training RMSE | 3.560876112655139 nT |
| Retained matrix-free fit training RMSE | 3.560876112655113 nT |
| Maximum retained/oracle prediction difference | 1.3451785796370075e-7 nT |
| Original frozen prediction tolerance | 1.1960891514020586e-6 nT |
| Relative full-objective disagreement | 6.095961820535938e-16 |
| Relative column-scale disagreement | 7.342847947156929e-16 |
| Augmented condition number | 1822.2899686716619 |

The selected basis already leaves about 3.56nT training representation error
without damping. The selected penalty adds only about 1.51e-6nT to training
RMSE. At the preserved control precision, the current iterative fit agrees with
independent SVD objective/predictions/scales; replacing its solver with another
solver of the same objective is not a demonstrated predictive repair. The
original 400m blocks are coarse relative to the 50m output spacing, but output
pixels do not increase the basis's resolving power.

This numerical projection is NOT a rigorous interval-certified lower bound,
NOT an outer-error bound, NOT proof that all 1/r representations fail, and NOT
permission to select finer blocks, changed depths, damping or thresholds from
already opened controls. The [opened refinement diagnosis](representation-refinement-diagnosis.md)
shows much smaller unpenalized training residuals on finer separately defined
bases but both original refinement predictive decisions remain FAIL. Geometry
support and good condition alone do not establish predictive fidelity.

Original S1 remains 18.799740861734186nT versus 0.25966396538773057nT FAIL;
the current streamed repetition is 18.799740863534nT at the same limit. The
training diagnosis explains a specific selected-basis deficiency, not every
contribution to that outer error. No unchanged positive control is declared
repaired. A legitimate new predictive claim requires independently reviewed
physics/representation and untouched validation, while the original failure
and frozen control remain permanent evidence. Field source/reference/datum,
complete corrected SurveyResult/export/replay, GUI and host acceptance remain
separate requirements; CLOSED capability is not online implementation.

The objective/scaling follows [Verde's pinned source](https://raw.githubusercontent.com/fatiando/verde/v1.9.0/verde/base/least_squares.py);
the harmonic scalar representation and source-block guidance follow
[Harmonica's pinned model documentation](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html).
The independent oracle uses [SciPy's SVD least-squares API](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.linalg.lstsq.html).

### Actual metric/constant discrimination, 2026-10-08

The separate `training-basis-forensics.json` from the same actual contained
training-only run reconstructs direct Python hypot distances and the pinned
Harmonica Jacobian on all294x66 original pairs. Relative disagreements are
3.10e-16; common XYZ translation2.88e-16, axis permutation3.12e-16, and normalized
operator after common metric rescaling1.31e-15, all below unchanged1e-12 controls.
G and population scales have units m^-1, c has nT, q has nT*m. A common units
factor cancels from G/s; no metres/kilometres multiplier repairs this basis error.
Training-source distances are502.44788944824734..4351.557926366724m; all sources
lie at -444.84239409854206m, exactly minimum training height55.157605901457934
minus the frozen500m. Original half-open membership/representatives were already
independently reconstructed. This is not validation of an unknown field datum.

Residualizing a constant column against the selected basis gives norm-squared
0.013374725844610547. A diagnostic training-only constant coefficient
5.0864251368563895nT changes projection RMSE only from3.560874605601467 to
3.560709338551843nT, about0.00464% improvement. Independent augmented SVD has
rank67/condition2419.7890932066366 and prediction discrepancy5.00e-13nT.
Therefore an absent constant alone does not explain the large training
representation error. This does NOT add an intercept, center values, change
main-field subtraction, choose a correction or predict on outer data.

The original S1 diagnostic is explicitly uncorrected: zero correction requests
and zero leveling fits. No crossover/gauge offset was applied, so changing a
non-applied leveling offset cannot explain its numeric failure. Real empty
inner-A calibration stays ineligible. Additional training oracles1, new outer
evaluations0, production fits0; original predictive FAIL and field unresolved.
These checks narrow the observed cause to the selected spatial representation,
not a demonstrated global units/distance/constant/leveling implementation error.
They do not prove which untested basis will predict well. Prospective resolution
selection is separately specified in the pre-code corrective workflow packet.

## Español

El diagnóstico consume artefactos streamed originales S1 ya ejecutados y
verifica bytes/hash originales, diagnóstico y GeometrySeal, cierre de todos los
miembros, 294 índices/IDs originales y las 66 fuentes originales de bloques
400m, con selección congelada 500m/0.0001. Exige Job real antes de decodificar o
importar motores. Roles, unidades e identidades no se infieren. No sustituye
campo ni selecciona otro modelo.

Los oráculos densos se restringen al control pequeño 294×66, nunca representan
el operador global grande. Reconstruyen G=1/r, desviaciones poblacionales sin
ponderar y A=G/s. SVD resuelve el sistema aumentado con sqrt(lambda), y otra
SVD calcula proyección sobre el espacio columna con corte numérico explícito.
No se cambia media, intercepto, pesos, alturas, lambda ni observaciones externas.
Se verifican bytes externos sólo por custodia, sin incorporarlos al oráculo:
cero ajustes de producción, dos oráculos internos, cero evaluaciones externas.

La tabla reproduce error de representación interno de aproximadamente 3,56nT
sin penalización. La lambda seleccionada añade apenas 1,51e-6nT a RMSE interno;
objetivo, escalas y predicciones streamed concuerdan con SVD independiente a
tolerancias originales. Cambiar solamente el solver del mismo objetivo no es
una reparación predictiva demostrada. Píxeles 50m no agregan resolución a la
base de bloques 400m.

La proyección numérica no es una cota rigurosa por intervalos ni cota externa,
ni prueba de imposibilidad de toda representación 1/r. No autoriza ajustar
bloques/profundidades/lambda/umbrales a controles ya abiertos. Los refinamientos
separados poseen menor residuo interno sin penalización pero ambos siguen FAIL.
Soporte geométrico y buena condición no equivalen a fidelidad predictiva.

S1 conserva RMSE externo original 18,799740861734186nT frente a
0,25966396538773057nT, y repetición streamed 18,799740863534nT: FAIL. Se explica
una deficiencia de la base seleccionada, no todas las causas del error externo.
No se declara reparado el control positivo. Una nueva afirmación exige física/
representación revisadas independientemente y validación no abierta; se conserva
permanentemente el fallo original. Campo/referencia/datum, flujo corregido de
SurveyResult/exportación/replay, GUI y host siguen requisitos separados; la
capacidad CLOSED no cuenta como implementación online. Las fuentes científicas
y numéricas primarias son las enlazadas en la sección inglesa.

La discriminación métrica real adicional compara todos los294x66 pares con
hypot independiente y Harmonica; las discrepancias de distancia, traslación,
permutación y escala normalizada son menores que1e-12. Fuentes a altura mínima
de entrenamiento menos500m, unidades G/s m^-1 y coeficientes nT*m: un factor
métrico común no repara el error. Una constante diagnóstica interna de5,0864nT
reduce RMSE de3,5608746 a3,5607093nT apenas0,00464%; no explica el error grande,
no agrega intercepto ni cambia referencia. S1 tenía cero correcciones y cero
nivelaciones; una compensación de cruces no aplicada no causa su diferencia.
Se conserva la calibración A vacía, FAIL original, cero evaluaciones externas y
cero ajustes de producción nuevos. Aún no se prueba una base predictiva válida.
