# 2. Plate and terrain / Placa y terreno

[Previous / Anterior](01_quantity-and-reference.md) · [Course / Curso](README.md) · [Next / Siguiente](03_uncertainty-and-covariance.md)

![Plate and finite relief attractions with signed residual / Atracciones de placa y relieve finito con residual firmado](assets/plate-and-relief.svg)

Figure / Figura: two different mass models evaluated at the same receiver; the plate is horizontally infinite. Arrows identify positive downward attraction, not arrow-length measurements. / Dos modelos de masa evaluados en el mismo receptor; la placa es horizontalmente infinita. Las flechas indican signo descendente positivo, no medidas de magnitud.

## English: which mass contribution are we subtracting?

The land plate approximation replaces relief by a horizontally infinite layer of density $\rho$ and thickness $h_s\ge0$, measured above the declared ellipsoid. The receiver sits at $h_r\ge h_s$. Density is a **supplied reduction assumption**, not a density inferred from station observations. Receiver height controls the normal reference; surface height controls plate thickness. Interchanging them changes the physical model.

Derive the downward attraction using a cylindrical shell at radius $R$, depth-coordinate $z\in[0,h_s]$, and receiver clearance $u=h_r-z\ge0$. Shell mass is $2\pi R\rho\,dR\,dz$. Its downward Newton component has the factor $u/(R^2+u^2)^{3/2}$, giving

\[
B=G\rho\int_0^{h_s}\int_0^\infty
\frac{2\pi R(h_r-z)}{[R^2+(h_r-z)^2]^{3/2}}\,dR\,dz.
\]

For $u>0$, integrate the radial factor: $\int_0^\infty Ru(R^2+u^2)^{-3/2}\,dR=1$. The $u=0$ top boundary is treated as the limiting exterior field and has zero measure in the thickness integral. Therefore

\[
B=2\pi G\rho h_s,\qquad B_{\rm mGal}=C\rho h_s,
\quad C=2\pi G\,10^5,\quad G=6.67430\,10^{-11}\ {\rm m^3\,kg^{-1}\,s^{-2}}.
\]

Units reduce to m/s² before conversion. The infinite horizontal extent explains why raising the receiver **above** the same plate does not change $B$. Real finite relief does not have that property. The existing engine is [Harmonica's Bouguer plate correction](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.bouguer_correction.html); its general ocean options are not an implemented lane in this core.

### Sign and terrain definition

Start with disturbance $D$. Remove positive plate attraction to obtain $D_B=D-B$. Let $A_{\rm topo}$ be attraction of an independently modelled actual topography, positive downward. Define the signed supplied residual

\[
T=B-A_{\rm topo},\qquad D_T=D_B+T=D-A_{\rm topo}.
\]

This is an algebraic **addition** after plate subtraction. Its sign is not inferred from the label “terrain correction”: if actual attraction exceeds the plate, $T<0$. A supplied TTC column, unsigned relief height or already curvature-corrected CBA is not automatically this residual. The exact nine-key terrain declaration is `kind`, `unit`, `height_reference`, `density_kg_m3`, `source_sha256`, `method`, `station_ids`, `additions_mgal`, `sigma_mgal`. It requires `additive_residual_to_plate`, mGal, WGS84 ellipsoid, matching density, exact station order, values and declared errors.

The core does not query a DEM or recalculate those supplied values. A DEM model would additionally need its horizontal/vertical reference, cell/receiver geometry, resolution, finite extent, density and boundary assumptions. [Harmonica's topographic modelling guide](https://www.fatiando.org/harmonica/v0.7.0/user_guide/topographic_correction.html) describes a separate modelling operation. Curvature, isostasy, ocean, network adjustment and raw calibration/drift/tides are not quietly performed here. In configs not targeting terrain, `terrain: null` is valid; supplying terrain for a non-terrain target rejects. A terrain target needs the exact non-null declaration and conservative marginal error mode.

### Worked reasoning and negative controls

Assume a teaching plate with $\rho=2670$ kg/m³, $h_s=1000$ m. Its attraction is the expression $2\pi(6.67430\,10^{-11})(2670)(1000)10^5$, approximately 111.97 mGal. Define $D=B+12$ for this hand exercise. Then $D_B=12$ exactly by definition; this is **not** an executed station control or actual field reading. If the upstream documented residual is $T=+2$, then $D_T=14$ mGal and $A_{\rm topo}=B-2$. Reversing $T$ produces 10, a different mass model.

Doubling thickness doubles $B$; raising only the receiver leaves $B$ unchanged but changes normal gravity and usually the observed attraction of real finite terrain. A supplied residual calculated for another density or reference cannot simply be reused. If an actual provider CBA already includes plate, curvature and terrain, subtracting this plate again is double application; changing its state flag does not restore the original observation. A repeated state transition must reject rather than infer hidden missing corrections.

### Python: create the exact ordinary request from your file

From `data-pipeline`, the following uses the existing bounded local reader and ordinary adapter, not an authenticated API. It neither derives terrain nor fills metadata. The actual source/datum/error contract and matched runtime must already hold. The recipe was syntax-checked only, not executed in this wiki milestone.

```python
from pathlib import Path
from gravity_transforms import read_request
from gravity_processing import digest
from gravity_station_adapter import (
    GravityStationAdapterError, run_station_corrections,
)

selected = read_request(Path('../my-corrections.json'))
if type(selected) is not dict or set(selected) != {'dataset', 'config'}:
    raise ValueError('Expected the selected dataset/config document.')
request = {
    'schema_version': 'gravity-station-adapter-request-1',
    'method': 'gravity.station-corrections/v1',
    'dataset': selected['dataset'],
    'config': selected['config'],
    'input_dataset_sha256': digest(selected['dataset']),
    'submitted_config_sha256': digest(selected['config']),
}
try:
    corrected = run_station_corrections(request)
except GravityStationAdapterError as error:
    print(error.to_record())
else:
    print(corrected['correction_result']['dataset']['state'])
    print(corrected['receipt']['acceptance'])
```

Only the adapter's four-key `to_record()` is its fixed safe failure surface; other local errors are not safe public tracebacks. All three acceptance flags remain false. Preserve the exact complete resulting parent for a strictly later correction, including integer types and history. The [workflow](../../../design/features/m01-scientific-course/workflows.md) specifies real paired scripts and fresh ignored outputs; the [adapter](../../../../data-pipeline/gravity_station_adapter.py) verifies fixed sibling identity and engine/runtime pins, not authenticated origin.

## Español: ¿qué contribución de masa estamos restando?

La aproximación terrestre reemplaza el relieve por una capa horizontal infinita de densidad $\rho$ y espesor $h_s\ge0$, sobre el elipsoide declarado. El receptor debe estar en $h_r\ge h_s$. La densidad es una **hipótesis de reducción suministrada**, no inferida de las estaciones. La altura del receptor determina la referencia normal; la de superficie determina el espesor. Intercambiarlas modifica el modelo físico.

La derivación integra un anillo cilíndrico de radio $R$, coordenada $z\in[0,h_s]$ y separación $u=h_r-z\ge0$. La masa es $2\pi R\rho\,dR\,dz$; su componente newtoniana descendente contiene $u/(R^2+u^2)^{3/2}$. La integral radial escrita arriba vale uno para $u>0$. La frontera superior $u=0$ se interpreta como límite exterior y tiene medida cero en la integral de espesor. Así se obtiene $B=2\pi G\rho h_s$; al convertir SI a mGal, $B=C\rho h_s$, con el mismo $G$ declarado.

La independencia respecto de la separación del receptor procede de la extensión horizontal infinita, no de una propiedad general del terreno. Elevarse **sobre** la misma placa no cambia $B$; el relieve real finito sí puede cambiar su atracción. La [API de placa de Harmonica](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.bouguer_correction.html) es el motor existente; sus opciones oceánicas generales no constituyen una vía implementada en este núcleo.

### Signo y definición del terreno

Desde $D$, se resta la atracción positiva: $D_B=D-B$. Para atracción topográfica real $A_{\rm topo}$ positiva descendente, se define $T=B-A_{\rm topo}$. Por tanto $D_T=D_B+T=D-A_{\rm topo}$. El residual se **suma** después de restar la placa; puede ser negativo cuando la atracción real supera la aproximación. El nombre “corrección de terreno”, una columna TTC, una altura de relieve sin signo o un CBA con curvatura no garantizan esta definición.

El objeto de nueve claves enumerado en inglés exige `additive_residual_to_plate`, mGal, elipsoide WGS84, densidad coincidente, orden exacto de estaciones, valores, DE, método y hash de fuente. No consulta DEM ni vuelve a calcular valores. El [modelo topográfico de Harmonica](https://www.fatiando.org/harmonica/v0.7.0/user_guide/topographic_correction.html) es una operación distinta que necesita referencias, geometría, resolución, extensión y bordes. Aquí no se añaden curvatura, isostasia, océano, ajuste de red ni deriva/mareas/calibración. Para destinos sin terreno, `terrain: null` es válido y un objeto no nulo rechaza. El destino terreno exige el objeto completo y el modo conservador de errores marginales.

### Ejercicio resuelto, negativos y Python

La placa docente $\rho=2670$ kg/m³, $h_s=1000$ m tiene $B\approx111.97$ mGal. Definir $D=B+12$ implica algebraicamente $D_B=12$, no una estación ejecutada ni dato de campo. Con $T=+2$, $D_T=14$ y $A_{\rm topo}=B-2$. Invertir el signo daría 10, otro modelo de masa. Duplicar espesor duplica $B$; elevar solo el receptor deja la placa igual pero modifica referencia y, generalmente, atracción finita real.

Un residual de otra densidad o referencia no se reutiliza sin justificación física. Si CBA ya incluye placa, curvatura y terreno, restar otra placa duplica la reducción. Cambiar una bandera no recupera la observación. Un destino repetido debe rechazar, no inferir operaciones ocultas. La compilación real no se vuelve elegible mediante este ejercicio.

El bloque Python anterior crea la petición ordinaria exacta desde su archivo real, sin inventar terreno/metadatos y sin autenticación. Solo fue comprobado sintácticamente. `to_record()` del adaptador es la superficie de error segura de cuatro claves; otras excepciones locales no se publican como trazas. Las tres banderas de aceptación permanecen falsas. Conserve el padre completo, tipos enteros e historia al reanudar hacia un destino estrictamente posterior. Los enlaces de flujo/adaptador describen rutas nuevas ignoradas, versiones y verificaciones de identidad del código; no prueban origen autenticado.
