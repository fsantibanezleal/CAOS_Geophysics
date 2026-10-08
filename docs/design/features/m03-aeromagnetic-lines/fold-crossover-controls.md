# Fold-scoped crossover values / Valores de cruces por partición

## English

`magnetic_line_survey_crossover_values` reconstructs values on every original
geometric pair after the value-free seal. All four endpoints must belong to
the actual training partition. Original adjacent acquisition ordinals remain
adjacent; filtering cannot reconnect separated rows into new segments. Every
rejected pair is retained with its actual reason. Missing values never become
zero measurements; typed payload zeros are interpreted only through masks.

For intersection fractions a,b, the admitted difference is
((1-a)F0+aF1)-((1-b)T0+bT1), accumulated as the protected original oracle.
Independent one-sigma errors imply variance
(1-a)^2 sigmaF0^2+a^2 sigmaF1^2+(1-b)^2 sigmaT0^2+b^2 sigmaT1^2.
Unknown, missing, nonpositive or overflowing error declarations refuse the
weighted lane, never invent variances. Units are nT and nT squared.

Shared-endpoint representatives are rebuilt AFTER this fold's eligibility,
not inherited from a value-free whole-survey group. This prevents a rejected
pair from stealing the fold's representative. `incidence_constraints` verifies
the stored receipt, table closure, original line roles and representative count
and streams only admitted actual representatives to the global sparse solver.
An actually empty inner calibration remains empty and ineligible. A successful
outer graph cannot supply held-out inner calibration.

Custody binds original geometry, geometry policy, training row-ID hash and
measurement pass. All SQLite spill and member storage use explicit external
roots. Tests compare every actual original S2 record exactly with the protected
oracle and all global offsets within the unchanged 1e-9 nT tolerance. They
also retain the original empty-inner-A refusal. This component does not establish
a complete correction DAG, field reference, SurveyResult or online admission.

## Español

Se reconstruyen valores de todos los pares geométricos originales después del
sellado sin valores. Los cuatro extremos deben pertenecer al entrenamiento
real. No se reconectan filas separadas al filtrar; se conserva cada rechazo y
su razón. Valores faltantes no son mediciones cero: la máscara gobierna el
payload tipado.

Las ecuaciones anteriores conservan interpolación y propagación de varianza
originales, con unidades nT y nT cuadrado. Sigma desconocida, ausente, no positiva
o aritmética no finita rechaza ponderación; no se inventan errores. Los
representantes de extremos compartidos se reconstruyen DESPUÉS de elegibilidad
por partición. Se verifican recibo, cierre de tabla, roles originales y cantidad
de representantes antes de resolver incidencia global. La calibración interna
realmente vacía permanece inelegible; no se reutiliza la calibración externa.

La custodia vincula geometría original, política, hash ordenado de IDs de
entrenamiento y mediciones. SQLite y miembros permanecen en raíces externas
explícitas. Las pruebas comparan exactamente cada registro S2 original y
offsets globales dentro de 1e-9 nT, conservando el rechazo interno A. No prueba
DAG completo, referencia física de campo, SurveyResult ni admisión online.
