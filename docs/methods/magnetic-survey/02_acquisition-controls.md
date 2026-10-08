# Independent acquisition controls / Controles de adquisición independientes

These are original authored scientific controls, not provider acquisitions or
field observations. The executable generator is
`tests/fixtures/magnetic_survey/generate.py`; independent checks are in
`tests/numerics/test_magnetic_survey_truth.py`. This chapter defines real inputs
and oracles, not fitted predictive success or accepted magnetic inversion.

## English: geometry precedes measurements

S2 has twelve flights with twenty-four samples each. For flight `l=0..11` and
sample `s=0..23`, local ENU coordinates in metres are

$$E=-200+80s,\qquad N=600l,\qquad U=120+10(s\bmod3).$$

IDs preserve original flight/sample order. Heights are explicitly authored and
heterogeneous; timestamps are unavailable, never fabricated. The inversion mesh
has origin `(-400,-300,-1800)m`, horizontal widths `11×200m`, `12×600m` and
vertical widths `[150,250,400,1000]m`, with528 active cells. Magnetic truth does
not use these inversion-cell coefficients.

Before amplitudes, the generator verifies complete geometry metadata, coordinate
payload and independently ranked membership hashes. Block widths250/500m,
buffer200m and seed104729 are fixed:12 units,72 outer rows on flights01/04/11,
216 development rows, three144-fit/72-validation folds and216 final-refit rows.
Changes to coordinates, groups, mesh, QC, timestamps or buffer fail before
physical truth. No amplitude-dependent mask, decimation or relaxed partition.

## Actual independent physics and native scalar algebra

The authored uniform truth field is `F=50000nT`, downward inclination37° and
clockwise-from-north declination−73°. In ENU,

$$\mathbf f=(\cos I\sin D,\cos I\cos D,-\sin I),\quad\mathbf B_0=F\mathbf f.$$

For independent rectangular bodies,

$$\mathbf M=\chi\mathbf B_0\,10^{-9}/\mu_0+\mathbf M_r\quad[\mathrm{A/m}].$$

Actual [Choclo0.3.2](https://github.com/fatiando/choclo/tree/v0.3.2) evaluates
components in tesla, explicitly converted to nT. Off-grid body bounds are not
the inversion mesh. The installed magnetic source is compared to its retrieved
versioned hash before physical calls. The generator uses `magnetic_field`;
separate `magnetic_e/n/u` callables check selected results. They share low-level
Choclo kernels: this is component-call consistency, not three independent
engines. The intrinsic forward unit has its separate quadrature oracle. No
SimPEG/Geoana inverse kernel or production solver generates acquisition truth.

Each declared quantity has a separate record: secondary vector `E,N,U` in
receiver-major order; scalar linear TMI `f·b`; or exact anomaly `|B0+b|−F`.
Secondary amplitude `|b|` is not any of these quantities. Exact scalar truth
uses Decimal80 direct positive-radicand square root minusF, converting EACH
retained binary64 operand with `Decimal.from_float` before addition. Neither
Windows longdouble nor the candidate rational expression is the tiny oracle.

Rounded trigonometric components need not obey `B0·B0=F²`. With
`δ0=B0·B0−F²`, the frozen-operand identity is

$$|\mathbf B_0+\mathbf b|-F=
\frac{\delta_0+2\mathbf B_0\cdot\mathbf b+\mathbf b\cdot\mathbf b}
{|\mathbf B_0+\mathbf b|+F}.$$

Omittingδ0 changes the function. At zero secondary field the tiny native
baseline is retained and derivative direction is `B0/|B0|`. No mean subtraction,
field normalization, alteredF or tolerance waiver forces it to zero. Original
P04 source is unchanged; this continuation does not relabel its older expression.

The Decimal point oracle is not an interval certificate. A sound positive
radicand interval needs `sqrt(lo).next_minus(context)` and
`sqrt(hi).next_plus(context)` to enclose endpoint rounding: a FLOOR context does
not direct Decimal.sqrt. Separate algebra tests check the retainedδ0 and
outward-root bounds. No nonlinear inverse certificate is implemented here.

## Frozen regimes, conditional noise and honest negatives

Ordinary body1 bounds: E[310,770],N[1700,2570],U[−510,−130]m;
body2: E[960,1430],N[3980,4830],U[−980,−420]m.

| Regime | Authored physical hypothesis | Evaluation question, not an achieved verdict |
| --- | --- | --- |
| A | χ1=.012,χ2=.021, induced only | Disjoint-flight prediction and ambiguity |
| B | Same bounds,χ1=.025,χ2=.003 | Sparse/L2 fit and compactness comparison |
| C | Body1 U[−1050,−470]m,χ1=.021 | Depth/extent nonuniqueness |
| D | A plus body1 remanence `(8,−5.5,2.3)A/m` | Induced-only mismatch, not a classifier |
| E | Exactly A measurements; declared inverse I−35°,D−100° | Wrong-field negative, no direction estimation |
| F | No bodies; zero observations with SD.5nT | Null optimization and separate coverage rejection |

A–E add conditional Gaussian SD.5nT per component using NumPy2.2.6
`Generator(PCG64(20261004))` with exact shape `(288,C)`. Raw RNG states,
generator/source hashes and byte records are retained. Scalar lanes use a paired
realization; no statistical independence across controls/regimes is claimed.
D/E cannot quietly receive new noise, altered masks or favourable partitions.

F is an explicit zero-observation control under the declared SD, not an assertion
that rounded `|B0|=F`. Its separate exact clean scalar baseline remains nonzero
where arithmetic dictates. The four-flight coverage negative is a declared
subset, not a full acquisition, and must reject insufficient indivisible units.
Every control verdict starts `not_evaluated`; generating an input does not
prove fitted success, remanence discrimination or unique susceptibility.

## Original bytes, truth separation and execution

`original_bytes` is the actual canonical acquisition: IDs/groups, frame, declared
field, geometry, observations and SD. Evaluator bodies, remanence and noiseless
signals are absent from this record and the modelling request. SHA and byte
count come from real record bytes, not protocol placeholders. Observations have
little-endian binary64 payload hashes. The ordinary parser/planner preserves
deferred likelihood spans; regimes cannot seed or alter geometry memberships.

Numerical results are independently owned, C-contiguous write-protected
snapshots. Owners can re-enable writes; they are not tamperproof. Retained bytes
and hashes establish identity. Mutating a clean-signal snapshot does not change
its observations or a later independently generated record.

Run in the existing pinned pipeline environment, without installing another
engine or changing a runtime to make the gate pass:

```powershell
$env:PYTHONPATH='data-pipeline;tests/data'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
.venv-pipeline/Scripts/python.exe -B -m pytest --noconftest -p no:cacheprovider -o addopts= -q tests/numerics/test_magnetic_survey_truth.py
```

These commands verify generated measurements and recorded bytes. They do NOT
calibrate/evaluate a supplied inverse. Accepted optimizer/source composition,
L2/IRLS fits and fixed-objective stationarity, one-time sealed predictive
evaluation, resolution, measured full-cap resources, durable fitted bundles,
actual supplied-user-data tools and field gates remain required. No synthetic
truth volume is assigned to a real field survey.

## Español: geometría, física y cantidades

S2 es una adquisición original sintética, no datos de terreno. Sus doce líneas y
288 filas conservan IDs, grupos y coordenadas ENU originales. Las alturas son
heterogéneas y explícitamente construidas; no se inventan fechas. Geometría,
malla, QC, grupos y búfer se sellan antes de generar amplitudes. Cambiar valores
o errores no cambia las72 filas externas ni las tres particiones144/72. La
cobertura de cuatro líneas se rechaza sin relajar el búfer ni llamar completo
al subconjunto. Se verifica toda la metadata geométrica antes del motor físico.

Prismas independientes de Choclo producen componentes ENU en tesla, convertidos
a nT con magnetización `M=χ B0(T)/μ0+Mr`. No son coeficientes de la malla inversa.
Vector secundario, proyección lineal `f·b` y anomalía exacta `|B0+b|−F` son
mediciones distintas; `|b|` no sustituye ninguna. La anomalía usa Decimal80
directo con cada operando binary64 convertido antes de sumar. El defecto
`δ0=B0·B0−F²` se conserva en la identidad racional, sin normalizar el vector
ni forzar respuesta cero. Los intervalos de raíz requieren vecinos hacia fuera:
Decimal.sqrt no obedece un redondeo FLOOR. P04 no cambia y estos tests no
implementan un inversor no lineal ni su certificado.

## Español: controles, ruido, bytes y límites

A/B/C estudian heterogeneidad, contraste y ambigüedad de profundidad; D añade
remanencia `(8,−5.5,2.3)A/m`; E mantiene exactamente datos de A pero declara
otro campo. F registra observaciones cero con SD.5nT, conservando por separado
la pequeña línea base escalar nativa. D/E no son clasificadores: sin ajuste y
evaluación retenida no se afirma discriminación ni geología recuperada.

El ruido condicional usa PCG64, semilla20261004 y forma288×C. Se registran estado
inicial/final, versión, hashes del generador, fuente física y bytes reales. Los
controles escalares son apareados; no se afirma independencia entre controles.
El registro original incluye mediciones, geometría, campo declarado y SD, pero
excluye cuerpos verdaderos, señal limpia y remanencia. La verdad del evaluador
no entra al contrato de modelado ni modifica sus particiones.

Las matrices son copias propias con escritura inicialmente protegida, no memoria
inviolable. La identidad durable depende de bytes y hashes. Los tests verifican
componentes, álgebra escalar, reproducibilidad y separación de verdad. No prueban
éxito predictivo, ajuste L2/IRLS, recursos al máximo, durabilidad, cálculo online
o validez de terreno. Los dictámenes permanecen `not_evaluated` hasta la
evaluación científica real. El flujo completo de datos suministrados, incluidos
negativos y fallos persistidos, sigue siendo obligatorio.
