# Procesamiento local de líneas aeromagnéticas (M03)

Este flujo local inspecciona la geometría de las líneas y la altura del sensor, reserva un bloque contiguo de líneas completas para validación, mide la interpolación espacial sobre ese bloque y genera una grilla con máscara de soporte. No sube el archivo, no invierte un modelo del subsuelo y no aplica correcciones magnéticas.

## 1. Preparar los datos y el mapeo

Conserve intacto el CSV original. Registre la cita, los derechos de uso, el estado de procesamiento declarado por el proveedor, la magnitud magnética y su unidad. El código no deduce si el valor es campo total, anomalía, derivada horizontal o si ya fue nivelado. Use coordenadas proyectadas en metros y un CRS proyectado identificado; el código rechaza longitud/latitud angular. Declare si la altura del sensor es sobre el terreno o está referida a un datum vertical.

Prepare un JSON con los encabezados exactos del CSV. El ejemplo completo está en la versión en inglés de esta guía: [mapeo y parámetros](m03-flightline-processing.md#1-prepare-the-source-and-mapping). Sustituya todos los encabezados, unidades, CRS y afirmaciones de procesamiento por valores comprobados en la documentación de su levantamiento. El ejemplo no describe un levantamiento real específico.

## 2. Ejecutar localmente

```powershell
.venv-pipeline\Scripts\python.exe data-pipeline\magnetic_processing.py `
  --csv ruta\al\original-lineas.csv `
  --config ruta\al\mapeo.json `
  --output ruta\al\nuevo-resultado.json
```

El programa no sobrescribe resultados existentes. Informa tamaño y SHA-256 del archivo generado. Acepta CSV de hasta 256 MiB y 250.000 filas; la grilla admite hasta 250.000 celdas. Requiere NumPy y SciPy del entorno offline fijado.

## 3. Interpretar la salida

`geometry_qc.lines` informa cantidad de muestras, extensión y estadísticos de altura (mínimo, mediana, máximo, MAD e índices señalados). El umbral de seis MAD escaladas sirve como alerta de revisión, no como incertidumbre calibrada del instrumento. Ninguna observación se elimina. Las coincidencias exactas entre líneas se cuentan y se resume su diferencia de valor; esto no reemplaza el cálculo de cruces geométricos cercanos.

`split` muestra los identificadores de líneas completas de ajuste y validación. El bloque interior contiguo se selecciona de forma determinista respecto del eje normal estimado. Las líneas de amarre no entran al ajuste. `heldout_interpolation` informa cantidad y cobertura de muestras soportadas, MAE y RMSE. `grid` guarda ejes en metros, valores con forma `[northing, easting]` y máscara de soporte. Fuera del casco convexo de los datos de ajuste, el valor cero siempre va acompañado de máscara falsa.

La grilla interpola mediciones a sus alturas registradas; no las continúa a un plano común. Un error pequeño de validación solo indica que la interpolación predijo esas muestras medidas. No demuestra un modelo único del subsuelo.

## 4. Límites actuales

Este flujo aún no calcula intersecciones geométricas de líneas, nivelación por líneas de amarre, correcciones diurna/IGRF/retardo/altura, campo regional ni continuación ascendente. Tampoco compara con una grilla del proveedor ni verifica el historial de procesamiento de la fuente. No aplique una cadena de corrección de datos crudos a datos que el proveedor ya procesó. La validación específica de Charleston sigue pendiente hasta obtener y calcular hashes del CSV, diccionario, informe contractual y grilla de comparación oficiales; consulte el [registro de investigación de la fuente](../research/m03-charleston-flightline-research-2026-10-25.md).
