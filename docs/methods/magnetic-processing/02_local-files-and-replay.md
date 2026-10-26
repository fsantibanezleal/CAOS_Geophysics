# Local files, exact Results and replay / Archivos locales y reproducción

## What an output means / Qué significa una salida

An observed-minus-predicted residual is (r_i=y_i-\hat y_i\), in nT.
Its RMSE is (\sqrt{\sum r_i^2/N}\); a positive bias means the observations
are larger than predictions. Crossover difference has a different ordering:
flight minus tie. A grid at120m is not a measurement at120m, and its50m pixel
does not establish50m resolving power. Missing sigma stays null: numerical
uniform weights are not one-nT measurement errors. Unknown/reference-applied
states do not authorize another subtraction.

El residuo observado menos predicho es (r_i=y_i-\hat y_i\), en nT.
Un sesgo positivo significa observaciones mayores que las predicciones.
En cruces, la diferencia es línea de vuelo menos línea de amarre. Una predicción
a120m no es una medición a120m; píxeles de50m no prueban resolución de50m.
Una incertidumbre desconocida permanece nula. Pesos numéricos uniformes no
son errores instrumentales de1nT. Un estado desconocido o ya aplicado no
autoriza repetir una corrección.

The [exact contract](../../design/features/m03-aeromagnetic-lines/contracts.md)
separates finite typed structure, physical eligibility and successful computation.
The [Result/custody extension](../../design/features/m03-aeromagnetic-lines/local-result-and-source-profile.md)
specifies original versus canonical hashes and the distinct local source study.
Hashes bind bytes, not provider authenticity, rights or geological truth.

## Inspect real user files / Inspeccionar archivos reales del usuario

Use a pre-existing compatible pinned CPython interpreter, not a package
installation guessed by this recipe. Supply your actual files, exact14-column
CSV and full sidecar/request. Never rename a raster/grid into flight lines.

Use un intérprete CPython compatible ya existente. Suministre los archivos
reales, el CSV exacto de14 columnas y sus metadatos/solicitud completos. No
convierta una imagen o grilla en líneas de vuelo mediante un cambio de nombre.

```powershell
# Assign the actual existing pinned interpreter yourself; no environment is created.
& $ExistingPipelinePython data-pipeline/magnetic_lines.py validate `
    --csv survey.csv --metadata survey.metadata.json --request survey.request.json
```

Structural inspection prints actual original-byte identity and eligibility
reasons; numerical_success remains false. Missing datum, reference, time,
correction history, uncertainty or source rights is not silently filled.
The current ordinary numerical implementation requires reviewed applicable
control/auxiliary semantics; an actual provider file does not become accepted
because this inspection succeeds. The400-row bounded lane does not process
the full Charleston survey.

La inspección imprime la identidad de los bytes originales y los motivos de
elegibilidad; numerical_success permanece falso. No rellena datum, referencia,
tiempo, historial, incertidumbre ni derechos faltantes. Un archivo real no queda
aceptado por superar la inspección. El límite de400 filas no cubre Charleston
completo; no se permite un subconjunto conveniente como sustituto.

## Compute/export when eligible / Calcular y exportar cuando sea elegible

```powershell
& $ExistingPipelinePython data-pipeline/magnetic_lines.py run `
    --csv survey.csv --metadata survey.metadata.json --request survey.request.json `
    --output-directory new-local-result

# Same producer via the paired PowerShell wrapper.
pwsh -File scripts/magnetic-lines.ps1 -Python $ExistingPipelinePython -Mode run `
    -Csv survey.csv -Metadata survey.metadata.json -Request survey.request.json `
    -OutputDirectory another-new-local-result
```

```sh
# ExistingPipelinePython must identify the actual pre-existing compatible runtime.
sh scripts/magnetic-lines.sh --python "$ExistingPipelinePython" run \
    --csv survey.csv --metadata survey.metadata.json --request survey.request.json \
    --output-directory new-local-result
```

Destinations must be absent. No overwrite, ZIP/pickle execution, installation,
network retrieval or job dispatch occurs. All source-order rows survive the
inventory, with masks/exclusion reasons. Arrays bind their physical unit,
shape, ordered identity, values and mask SHA-256. Invalid cells are null, not
zeros. A complete Result requires typed reference vectors; the untyped original
S1 diagnostic is not patched into a complete Result by guessing direction zero.

Los destinos deben estar ausentes. No hay sobrescritura, ejecución de ZIP/pickle,
instalación, descarga de red ni despacho de trabajos. El inventario conserva
todas las filas en orden original. Cada arreglo vincula unidades, dimensiones,
identidades, valores y máscaras. Celdas inválidas son nulas, no ceros. Los vectores
de referencia deben estar tipados; no se inventa una dirección para completar S1.

Raw, private-processing and derivative-publication permissions are separate.
Raw originals embedded in navigation/base/calibration records also require
appropriate export permission. Denied raw members remain excluded and replay
ineligible; an allowed derivative does not override that restriction.

Los permisos para datos originales, procesamiento privado y publicación de
derivados son distintos. Los registros originales embebidos también requieren
permiso. Excluir originales puede dejar la reproducción inelegible; permitir
un derivado no elimina esa restricción.

## Replay and inspect / Reproducir e inspeccionar

```powershell
& $ExistingPipelinePython data-pipeline/magnetic_lines.py replay `
    --bundle new-local-result --output-directory new-replay-result
```

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("data-pipeline").resolve()))
from magnetic_line_contract import read_bounded
from magnetic_lines import parse_result

result = parse_result(read_bounded("new-local-result/result.json", 8 * 1024**2))
print(result["evaluation"]["outer"]["rmse_nT"])
print(result["evaluation"]["field_acceptance"])
print(result["verdict"])
```

Replay checks every allowlisted member before computation and independently
reconstructs the recorded pipeline from exact originals, request and compatible
runtime/source identity. Rehashing an altered request or array is not scientific
replay. A different source revision refuses rather than inventing the current
origin of an older receipt. Structural parsing alone is not replay verification.

La reproducción comprueba cada miembro antes de calcular y reconstruye el
proceso desde los originales exactos. Recalcular el hash de datos modificados
no verifica la física. Una revisión de fuente distinta causa rechazo, no una
atribución falsa del comprobante anterior. Analizar JSON no equivale a reproducir.

## Why finer source blocks are not a waiver / Por qué bloques menores no eximen

The fixed fresh100m/50m study has independently sealed geometry and new SI
dipole truth, separate from opened original S1. Both requests keep the original
depths, damping, tie rule and5% target. Neither width is chosen from outer error.
Finer representation can reduce some approximation error but cannot promise
prediction between widely separated flight lines. The inverse-distance basis
and depth/regularization assumptions still matter. A covered location is not
a validated prediction; source coefficients are not geological magnetization.

El estudio independiente de100m/50m conserva profundidades, amortiguamientos,
regla de desempate y meta del5%. No se elige el ancho a partir del error externo.
Una representación más fina no garantiza predicción entre líneas separadas.
Cobertura geométrica no es validación predictiva, y los coeficientes no son
magnetización geológica. El fracaso original de S1 permanece como control negativo.

Primary physics: [Harmonica inverse-distance sources](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html),
[SI dipole forward operator](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.dipole_magnetic.html),
[weak total-field projection](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.total_field_anomaly.html),
[Verde's actual scaled Ridge objective](https://www.fatiando.org/verde/v1.9.0/_modules/verde/base/least_squares.html).
Native measurement semantics: [Windows Job queries](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject)
and [committed-memory versus resident-memory limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).
