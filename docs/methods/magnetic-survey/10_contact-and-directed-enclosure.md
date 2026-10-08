# Public contact initialization and equivalent directed enclosure

## What changes and what does not

An optional local linear source binds
`physical_feasible_optimizer.solve_bounded_linear`, epoch
`physical-gncg-linear-joseph-contact-candidate-4`. This is separate from the
older conditioned linear epoch, not an upgrade of its results. The complete
inventory contains the original24 sources, four conditioned sources and the
feasible source. The receipt binds all29 actual loaded hashes. This source has
no nonlinear contact export; exact total-field anomaly retains its separately
reviewed nonlinear GN source and original norm certificate.

The public owner constructs one initial ray from a successful native CG
direction. For each free coordinate moving toward its original box boundary,
it computes the positive quotient using exact stored binary64 values. The
smallest quotient below1 is converted upward to the smallest enclosing
binary64 alpha. The native projected Armijo loop receives alpha times the
original direction once and retains its original20 trials. Its actual projected
chord, strict native descent and directed physical certificate decide adoption.
This is not a retry after a failed line search, manual bound snapping, a
near-bound heuristic or a new CG method. The original projected-gradient branch
uses its original full diagonal proposal, without contact scaling.

## Directed dot algebra

The physical certificate evaluates the same stored-real affine kernel,
background, noise chain and fixed regularization at both projected endpoints.
For exact coefficient a and interval X=[l,u], define

```text
(x_lower,x_upper) = (l,u) if a >= 0, otherwise (u,l)
L_next = floor_context.fma(a,x_lower,L)
U_next = ceiling_context.fma(a,x_upper,U)
```

Suppose the partial exact sum lies in[L,U]. Multiplication by the fixed signed
coefficient is monotone in the selected direction, and addition is monotone in
the accumulator. Rounding the combined expression downward/upward therefore
encloses the next exact partial sum. Induction from[0,0] encloses the complete
dot product. Fused multiply-add avoids intermediate product rounding and may
tighten the interval; it does not alter operands or remove their rounding proof.
Every coefficient is still `Decimal.from_float` of the actual binary64 source.
No rounded decimal matrix, float estimate or residual-based error heuristic is
substituted. Only two accumulators and one exact coefficient are retained.

The explicit34/50/80 contexts, exponent/range traps, positive norm/domain guard,
strict negative projected slope and Armijo upper endpoint remain unchanged.
Deadline checks also occur inside a long dot every128 terms; expiration still
clears partial proof fields and refuses adoption. Principal covariance still
uses its original native Cholesky triangular chain, not an explicit inverse.

## Verification and claims

Independent rational enumeration of all interval corners covers mixed signs,
zero, subnormal coefficients, cancellation and large exponent differences.
It verifies the new endpoints contain the exact real dot product and lie inside
the former multiplication/add enclosure. Independent Decimal160 full-objective
controls still verify vector, projected scalar and exact norm quantities with
diagonal and principal covariance. Unresolved symmetric/tiny Armijo controls
must remain unresolved; caller context and time/range refusals remain binding.

Actual full288-row/528-cell calibration, complete L2/eight-threshold IRLS,
heldout evaluation and finite resource/lifetime controls are separate gates.
Original200 combined steps, linearCG200/20LS, nonlinearCG512/30LS,120seconds
per fit and768MiB envelope do not change. Contact initialization can still fail
or exhaust that budget. Source correctness and tiny-control precision are not
full-matrix, field, native Linux or authenticated service acceptance.

## Espanol

La opcion lineal enlaza un export publico distinto y los29 hashes reales.
No añade una variante no lineal ni cambia los limites originales. El propietario
publico elige una sola escala inicial hacia el primer contacto; la proyeccion
nativa y el certificado fisico deciden el desplazamiento realmente adoptado.
No hay CG privado, reintento, ajuste de cotas ni tolerancia mas debil.

Para el producto escalar certificado, el signo del coeficiente exacto selecciona
el extremo inferior/superior. Cada acumulacion usa multiplicacion y suma
fusionadas con redondeos dirigidos separados. Por induccion, ambos extremos
encierran la misma suma real de operandos binary64 originales. No se conserva
una matriz Decimal ni se cambia el operador fisico. Se mantienen34/50/80
digitos, restricciones de dominio y rechazo al vencer el plazo. Los controles
racionales independientes no sustituyen la evaluacion completa S2 o de campo.

References: [Python3.12 Decimal fused multiply-add and explicit Context](https://docs.python.org/3.12/library/decimal.html#decimal.Decimal.fma),
[original physical algorithms](../../design/features/m04-survey-inversion/algorithms.md),
[native norm certificate](04_native-norm-certificate.md), and
[composition design](../../design/features/m04-survey-inversion/contact-and-enclosure.md).

## Separate reduced-native linear composition

`magnetic_reduced_adapter` consumes only the public
`physical_reduced_optimizer.solve_bounded_linear`. The original current
physical gradient and exact bounds define the initial native free face. The
public owner disables the vendor active-gradient add-on, solves the actual
principal physical Hessian with native CG and the closed Joseph metric, and
freezes outward-at-exact-bound coordinates only after a successful original
true-residual check. The actual CG count is summed across these phases, never
reset to grant another200 iterations. Original20 Armijo trials,200 combined
accepted states,120seconds and768MiB remain binding. Outside the direction
construction, original full physical KKT and same-run terminal remain authority.
The magnetic wrapper does not provide masks, factors, CG or failed-solve retries.

Before a full kernel, its new source-bound allocation dictionary reserves
the complete bounded phase history and public8MiB workspace. At most512 phases
charge8*a+8192 each; at most200 directions charge16*a model/gradient and8*a
total frozen indices each, plus one prospective8*a delta. This conservative
reserve is added to the larger original source/metric envelope and must fit
the unchanged768MiB cap. Old allocation hashes cannot acquire this reserve
retroactively. The dictionary is not proof of native RSS, Linux custody or
scientific validity.

The [prerequisite design](../../design/features/m04-survey-inversion/reduced-public-seam.md)
requires original independent Choclo/BVLS model/objective/prediction precision,
then one original full firstfold before any dependent complete matrix. Exact
total magnitude has no reduced-linear admission. Sparse continuation, heldout
evaluation, actual lifetime/resource controls, field lineage and mounted owner
integration remain their separate original requirements.

### Espanol: composicion lineal de espacio activo reducido

El adaptador magnetico consume solamente el export publico lineal. El nucleo
publico construye las caras libres desde el gradiente fisico y los limites
exactos; no recibe una mascara ni un factor elegido por el cliente. Despues
de cada CG nativo exitoso se comprueba el residuo verdadero y se congelan
solo coordenadas que apuntan hacia afuera en un limite exacto. Los200 pasos
CG se comparten entre fases; no son200 adicionales por fase. Se conservan
20 ensayos Armijo,200 estados aceptados,120segundos y768MiB originales.

La admision previa al kernel reserva el historial completo acotado, no una
estimacion optimista de fases. El nuevo diccionario y su hash enlazan fuente,
conteos y reserva; no actualizan recibos antiguos. La convergencia de una
particion y el oraculo independiente son prerrequisitos, no aceptacion de
campo, magnitud no lineal, API autenticada o matriz completa.
