# Explicit representation and fixed-policy grid controls

## Epochs and units

Representation is distinct from the fit policy. A new metre axis is
`grid_axis:float64[L]`, not the historical `grid_coordinate:float64[P,3]`.
The original reader refuses the new role; the finite representation reader
verifies original manifest/1 with its unchanged parser or manifest/2 with the
new closed parser. It never guesses the epoch from a filename. New result/2
must identify fixed_basis_v1 or resolution_v2 explicitly; this does not upgrade
an old receipt, change a basis, or turn historical predictive FAIL into PASS.

For the east axis, $e_i=e_0+i\Delta e$; for north, $n_j=n_0+j\Delta n$.
Both are strictly increasing, finite, and use the unchanged64-epsilon relative
spacing check. Axis ordered hashes bind separate padded `easting.i` and
`northing.j` identities. Grid cell identities remain original `g.j.i` order.
Masks retain geometric holes, gaps and sampling-unresolved information. The
latter is informational, not a license to fill an excluded cell or to declare
sampling resolved. Supported predictions use every selected source:

$$t(\mathbf{x})=\sum_{k=1}^{M}q_k/\|\mathbf{x}-\mathbf{s}_k\|_2.$$

Here coordinates are metres, $q_k$ is nT*m, and $t$ is nT. Chunks bound the
query/kernel storage, not the physical domain or number of sources. Sources are
below the maximum-training-height eligible plane. Higher-plane direct
equivalent-source prediction is not silently replaced by FFT continuation.
Source-free, known-datum, complete-plane FFT eligibility is checked separately.

## Boundary and spectrum contract

The new representation freezes the unchanged ordinary formula
$2p_e\le n_x$, $2p_n\le n_y$. Earlier full-schema prose allowed wider padding;
that discrepancy is not resolved by weakening the original transform negative.
Periodic boundaries require no padding, taper or detrend. Internal FFT cells
remain at most4194304, while **all exported grid/power cells together** remain
at most1048576. Requested spectra cannot silently disappear or borrow an
unreserved exported-cell allowance.

Upward FFT continuation multiplies each coefficient by
$\exp(-\sqrt{k_e^2+k_n^2}\,\Delta h)$ for strictly positive $\Delta h$.
A finite periodic extension generally differs from the direct infinite-domain
equivalent-source prediction: an eligibility receipt and a reported difference
are not a parity PASS. Two-sided bin power is
$|\mathcal F(w(t-\bar t))|^2/(N^2\langle w^2\rangle)$; its sum is checked
against $\langle[w(t-\bar t)]^2\rangle/\langle w^2\rangle$ at the unchanged
Parseval criterion. The approved `microlevel_transfer` is dimensionless in the
declared FFT shape, never an nT array relabel. Removed/retained channels remain
diagnostic, without a geological-preservation claim.

These formulas follow the already reviewed
[Harmonica0.7.0 equivalent-source model](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html)
and [Harmonica upward-continuation filter](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.filters.upward_continuation_kernel.html).
They identify a harmonic representation, not inferred susceptibility, source
depth, geology, provider authentication or field measurement accuracy.

## Pre-value v2 refusal proof

The approved four resolutions/two depths/four lambdas/three folds yield96
inner solves and one mandatory final solve. Before measurements the winner is
unknown. The integer-only planner sums eight solves for each of twelve actual
geometry/inner-fold shapes, reserves the maximum final shape, every inner score,
worst final outer/grid prediction and optional named comparator. Each solve
reserves four scaling/independent-gradient pair passes plus two per declared2000
iterations. It never substitutes the old25-fit estimate.

Sixteen retained maps bind each final/inner partition at each resolution. Their
uint64 two-column member arrays and float64 three-column sources enter scratch
planning, with shared training indexes, all retained member/index byte bounds,
and the original independent phase allowance. The proof refuses over128 arrays,
16 dictionaries,192 logical members,10^15 pairs or the unchanged RSS/commit,
raw/auxiliary bytes, FFT, cells and scratch caps before native allocation.
`resource_state=unmeasured` is intentional: integer planning is not a native
zero/cancel proof, measured host admission, fresh scientific seal or value access.

## Español: identidad y límites

El eje métrico nuevo es un vector1D explícito bajo manifiesto/2; no se renombra
el papel histórico3D. La política científica fija-v1 conserva sus24 candidatos
y25 ajustes. La selección de resolución-v2 exige96 candidatos completos y97
ajustes, o98 sólo con comparador identificado. Los FAIL S1 y100/50 permanecen.

Cada celda admitida usa todas las fuentes del modelo global. Los bloques limitan
memoria, no recortan el dominio. Se conservan máscaras y originales; una bandera
de muestreo no resuelto no equivale a hueco geométrico ni a muestreo resuelto.
Continuación directa y FFT tienen condiciones de borde distintas: elegibilidad
no es paridad ni validez geológica. Potencia tiene nT^2; transferencia es
adimensional; remoción y retención siguen diagnósticas.

Antes de valores se suma el costo de los96 ajustes internos y se reserva el peor
modelo final todavía desconocido. Se incluyen mapas, índices, originales,
canales y artefactos bajo los mismos topes. El cálculo entero no inventa
mediciones de RSS/CPU ni admisión del host. Fuente original8201, referencia de
campo, workflow propietario, montaje y activación conservan gates separados.
