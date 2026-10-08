# Native field norm and certified steps / Norma nativa y pasos certificados

[Physical objective](03_physical-objective.md) defines whitening and physical
regularization. This chapter explains the actual quantity/Jacobian and directed
objective-displacement implementation. It does not report a completed inverse,
IRLS, field study, resource admission or accepted nonlinear optimizer.

## English: actual quantities and operand identity

The public SimPEG scalar induced operator, with Geoana RAM float64, yields
receiver-major ENU columns Gchi in nT per unit SI susceptibility. Production
susceptibility stays inside the supplied bounds, at most.1 SI. The mathematical
Choclo unit-susceptibility oracle is outside that production input domain: it
uses magnetization B0(T)/mu0 to independently check derivative columns.

The inverse coordinate is q=chi/.01. Store the binary64 product A_b=.01Gchi
once, then form b=A_b q. Its exact stored bytes, B0 components, retained F and
the quantity define the kernel identity. Recomputing an unrounded product in a
certificate would describe a different function. The three quantities are:

- Secondary vector: b, components E,N,U, Jacobian A_b.
- Linear TMI: f dot b, Jacobian f dot A_b.
- Exact scalar: norm(B0+b)-F, Jacobian (B0+b)/norm(B0+b) dot A_b.

Inclination is positive down and declination clockwise from north. All
coordinates are resolved ENU metres, vertical positive up. No field direction,
remanent magnetization, epoch, height, datum or measurement uncertainty is
estimated. A metadata-only builder seals original-order geometry before engine
construction; it never decodes observation or uncertainty lists. Predicting an
outer receiver coordinate is not access to its held-out measurement.

Binary64 trigonometric B0 does not generally satisfy dot(B0,B0)=F squared in
exact real arithmetic. Define delta0=dot(B0,B0)-F squared. The stable identity is

H=(delta0+2 B0 dot b+b dot b)/(norm(B0+b)+F).

Both delta0 and retained F matter. At zero secondary field H may be a tiny
nonzero rounded-field intercept; the derivative uses B0/norm(B0), not an
asserted exactly unit rounded f. Do not normalize B0, replace F, subtract this
intercept as noise or omit delta0. The original forward-only expression remains
historical; this continuation explicitly evaluates native norm-minus-F.

Point evaluation converts each retained component with Decimal.from_float in
an isolated80-digit context. It uses the full rational identity; the independent
portable scalar oracle uses a direct square-root difference at160 digits in
the tests. Neither depends on Windows longdouble. Physical component checks
remain independently Choclo-based, not the scalar algebra oracle.

## English: what a directed certificate proves

The certificate fixes the actual rounded A_b, B0, F, observations, reference,
beta and each vendor regularization derivative/weight separately. It does not
substitute a rounded normal matrix. SD residuals are divided by declared SD.
Covariance residuals are solved through the actual retained native Cholesky L,
using the principal covariance for that fitting/scoring row set. The certificate
does not form an inverse, symmetrize covariance or add a noise nugget.

At each actual projected trial, it encloses real objective difference
Phi(q_trial)-Phi(q), slope g_native dot(q_trial-q) and Armijo margin
deltaPhi-binary64(1e-4)*slope. A hypothetical unprojected direction is not that
chord. A rounded native objective difference is not a proof of its sign.

All arithmetic uses explicit34,50,80-digit FLOOR/CEILING contexts. Squared
intervals that cross zero have lower bound zero. A checked positive radicand is
required before square root. Decimal.sqrt rounds HALF_EVEN irrespective of
context rounding, so each endpoint root is enlarged by next_minus/next_plus.
The inverse restriction T/F>1e-8 must hold for the lower norm enclosure, not only
the nominal floating value. Both direct and full rational enclosures describe
the same real native operands; their sound intersection can tighten the result.

Accept only if slope upper<0 AND Armijo-margin upper<0. Certified non-descent
or positive margin rejects. A sign still straddling after80 digits is unresolved,
not convergence. Timeout/domain failures clear partial intervals, precision and
pass counters. The caller's decimal precision, rounding, exponent range, traps
and flags are unaffected. Null displacement never produces acceptance.

The nonlinear arithmetic tag is fixed_native_operand_magnetic_norm. It cannot
be relabelled fixed_native_operand_quadratic to enter a linear-only optimizer.
This certificate establishes one actual-displacement predicate, not KKT,
unique geology, a global nonlinear optimum or final true-p1 IRLS stationarity.
Owned, C-order write-protected snapshots are not tamperproof: an owner can
reenable writes on its returned array. New evaluations never reuse that returned
storage; durable immutability requires persisted hashes and validated contracts.

## English: bounded equivalent scalar reuse

Within one frozen fixed-surrogate certificate, a completed scalar objective
enclosure may be reused at the bit-identical native model and the same explicit
34/50/80-digit precision. The model key is an owned readonly vector; signed
zero bits remain distinct. At most two model keys and twelve scalar Decimal
endpoints survive, never a Decimal kernel/matrix or cross-surrogate cache.
The conservative16*a+24576byte charge is included before snapshots, without
increasing the original768MiB limit or subtracting presumed execution savings.

The same explicit-context computation at unchanged operands/model/precision
encloses the same real objective. Reuse changes neither endpoint nor decision.
Slope, actual projected chord, margin, native diagnostics and all strict sign
predicates are computed fresh. Hits check the original deadline; expired or
partial construction is not published. Cached intervals are not accepted steps
or convergence evidence. Independent uncached-record and Decimal160 physical
objective controls remain required; full original matrix and native lifetime
gates must be measured again for the changed source inventory.

## Espanol: cantidades y campo nativo

El operador inducido escalar real de SimPEG/Geoana produce Gchi, en nT por
susceptibilidad SI, con orden receptor y componentes E,N,U. El modelo fisico
respeta los limites declarados, como maximo.1 SI. La columna matematica de
susceptibilidad unitaria de Choclo usa B0(T)/mu0 solo como oraculo independiente,
no como entrada de produccion. La coordenada numerica q=chi/.01 no cambia la
unidad fisica. A_b=.01Gchi se redondea y almacena una sola vez.

El vector secundario es b=A_b q. TMI lineal es f dot b. La anomalia escalar
exacta es norm(B0+b)-F; su Jacobiano depende de la direccion total actual, no
de una proyeccion constante. Inclinacion positiva hacia abajo, declinacion
horaria desde el norte, ENU en metros y vertical positiva hacia arriba son
convenciones explicitas. No se infieren remanencia, datum, altura, fecha ni
incertidumbre. Leer la geometria sellada no abre observaciones retenidas.

Los componentes binarios de B0 no tienen necesariamente norma exacta F.
Por eso la identidad estable conserva delta0=dot(B0,B0)-F squared junto con
2 B0 dot b+b dot b, dividido por norm(B0+b)+F. Incluso con b=0 puede existir
un pequeno intercepto nativo. Normalizar B0, sustituir F o borrar delta0 cambia
la funcion. Decimal80 evalua el punto y Decimal160 verifica independientemente
la diferencia directa de normas; Choclo verifica los componentes fisicos.

## Espanol: alcance del certificado

El certificado fija operandos binarios reales, desviaciones o factor Cholesky
de la covarianza principal, beta, referencia y derivados/pesos del regularizador.
No construye una inversa ni estima ruido. Certifica la diferencia del objetivo
completo entre dos modelos realmente proyectados y el producto del gradiente
nativo con su desplazamiento. No certifica un modelo cuadratico aproximado
como si fuera la verosimilitud de norma no lineal.

Los contextos explicitos de34,50,80 digitos propagan cotas dirigidas. sqrt de
Decimal siempre usa HALF_EVEN; next_minus/next_plus amplian cada raiz de un
radicando positivo comprobado. La cota inferior debe verificar T/F>1e-8. Solo
se acepta cuando las cotas superiores de pendiente y margen Armijo son
estrictamente negativas. Una cota ambigua sigue sin resolver; un tiempo agotado
o dominio invalido no publica un certificado parcial. El contexto del usuario
no cambia. El dominio magnetic_norm no puede hacerse pasar por quadratic.

Un paso certificado no demuestra convergencia KKT, estacionariedad final IRLS,
geologia unica, validez de campo ni admision en linea. Las matrices devueltas
son copias propias con escritura desactivada, no memoria inviolable; hashes y
contratos persistidos son necesarios para reproducibilidad durable.

## Espanol: reutilizacion escalar acotada

Un certificado con operandos fijos puede reutilizar solo los extremos escalares
completos del mismo modelo binario y precision explicita. Dos copias propias
del modelo y como maximo doce extremos Decimal quedan retenidos; no hay matriz
Decimal ni memoria compartida entre sustitutos IRLS. Los bits de cero positivo
y negativo son claves distintas. El coste16*a+24576bytes se admite antes de
las copias sin aumentar el limite768MiB. El plazo original se verifica tambien
al reutilizar. Una construccion parcial o vencida no se publica. Pendiente,
desplazamiento proyectado y margen se calculan de nuevo; un intervalo reutilizado
no demuestra convergencia ni admision de campo o del servicio.

## Sources and executable reading

[SimPEG magnetic simulation0.25.2](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/simulation.py)
defines the real induced kernel and units.
[Choclo0.3.2 magnetic functions](https://raw.githubusercontent.com/fatiando/choclo/v0.3.2/choclo/prism/_magnetic.py)
provide the independent physical oracle.
[CPython3.12.10 decimal implementation](https://raw.githubusercontent.com/python/cpython/v3.12.10/Modules/_decimal/libmpdec/mpdecimal.c)
defines square-root finalization; [Decimal neighbor methods](https://docs.python.org/3.12/library/decimal.html)
define explicit-context predecessor/successor enlargement.

Source: magnetic_inverse.py and magnetic_inverse_precision.py. Test:
tests/numerics/test_magnetic_inverse.py and test_magnetic_inverse_precision.py.
The tests distinguish physical finite-difference/adjoint checks, tiny scalar
algebra, full-covariance objective enclosures, projected chords, strict rejection,
exhausted precision, deadlines, invalid protocols and snapshot independence.
See the [full validation matrix](../../design/features/m04-survey-inversion/validation.md)
for still-required inverse, acquisition, IRLS, durability and linked-view gates.
