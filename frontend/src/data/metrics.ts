import type { Family, Metric } from "../science";
import { algorithmFor, type Text } from "./methods";
export function metricValue(value: Metric | undefined): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}
export function methodName(id: string, es: boolean, fallback = id) {
  const added: Record<string, Text> = {
    "joint-uncoupled": ["Uncoupled joint baseline", "Referencia conjunta sin acoplamiento"],
    pgi: ["Petrophysically guided inversion", "Inversión guiada por petrofísica"],
    "pgi-mismatch": ["PGI · mismatched prior", "PGI · prior incompatible"],
  };
  return added[id]?.[es ? 1 : 0] ?? algorithmFor(id)?.title[es ? 1 : 0] ?? fallback;
}
export function metricInfo(
  key: string,
  family: Family,
  method = "",
  es = false,
) {
  const property = family === "magnetics" ? "SI" : family === "seismic" ? "m/s" : family === "mt" ? "ln(Ω m)" : method === "cnn" ? "g/cm³ m" : "g/cm³";
  const entries: Record<string, { name: Text; unit: string; meaning: Text }> = {
    classical_column_rmse: {
      name: ["Matched classical column-density RMSE", "RMSE clásico comparable de densidad integrada"], unit: "g/cm³ m",
      meaning: ["The spatial L2 model projected onto the same column-density target, from the same observed data as the CNN. Not a 3D cell-property comparison.", "Modelo L2 espacial proyectado al mismo objetivo de densidad integrada, con los mismos datos observados que la CNN. No compara propiedades 3D por celda."],
    },
    classical_baseline_ratio: {
      name: ["CNN / matched classical column error", "Error de columna CNN / clásico comparable"], unit: "1",
      meaning: ["CNN column RMSE divided by the matched spatial L2 column RMSE. Above one means the CNN is worse for this case.", "RMSE de columna CNN dividido por RMSE de columna L2 espacial comparable. Mayor que uno significa peor CNN en este caso."],
    },
    independent_model_rmse: {
      name: ["Independent density-inversion RMSE", "RMSE de inversión de densidad independiente"], unit: "g/cm³",
      meaning: ["Density RMSE of the independent spatial L2 initialization used by all joint methods.", "RMSE de densidad de la inicialización L2 espacial independiente usada en todos los métodos conjuntos."],
    },
    independent_baseline_ratio: {
      name: ["Joint / independent density error", "Error de densidad conjunto / independiente"], unit: "1",
      meaning: ["Joint density RMSE divided by independent-inversion density RMSE. Below one is improvement; structural simplicity alone is not improvement.", "RMSE de densidad conjunta dividido por RMSE independiente. Menor que uno mejora; simplificar estructura no basta."],
    },
    magnetic_model_rmse: {
      name: ["Susceptibility model RMSE", "RMSE del modelo de susceptibilidad"], unit: "SI",
      meaning: ["RMSE between final recovered and target susceptibility across all cells, separately from density recovery.", "RMSE entre susceptibilidad final recuperada y objetivo en todas las celdas, separado de recuperación de densidad."],
    },
    magnetic_heldout_wrms: {
      name: ["Withheld magnetic normalized RMS", "RMS magnético omitido normalizado"], unit: "1",
      meaning: ["Noise-normalized magnetic residual on stations excluded from the joint inverse.", "Residuo magnético normalizado por ruido en estaciones excluidas de la inversión conjunta."],
    },
    vector_rmse: {
      name: ["Vector-component RMSE", "RMSE de componentes vectoriales"], unit: "SI",
      meaning: ["RMSE over all three effective magnetization components and model cells, including amplitude and direction effects.", "RMSE de las tres componentes efectivas y todas las celdas, incluyendo efectos de amplitud y dirección."],
    },
    recovered_centroid_depth_m: {
      name: ["Recovered property-centroid depth", "Profundidad del centroide recuperado"], unit: "m",
      meaning: ["Depth of the absolute-property-weighted recovered centroid, not a recovered top or bottom boundary.", "Profundidad del centroide recuperado ponderado por propiedad absoluta; no es interfaz superior ni inferior."],
    },
    true_centroid_depth_m: {
      name: ["Target property-centroid depth", "Profundidad del centroide objetivo"], unit: "m",
      meaning: ["Depth of the absolute-property-weighted known synthetic target centroid, used only for evaluation.", "Profundidad del centroide sintético conocido ponderado por propiedad absoluta, usado sólo para evaluar."],
    },
    other_component_wrms: {
      name: ["Opposite tensor component WRMS", "WRMS de componente tensorial opuesto"], unit: "1",
      meaning: ["Real-component normalized residual of the selected 1D model against the other off-diagonal impedance component, with its sign corrected for 1D antisymmetry. It was not fitted.", "Residuo normalizado por componente real del modelo 1D frente al otro componente fuera de diagonal, con signo corregido por antisimetría 1D. No se usó para ajustar."],
    },
    active_wrms: {
      name: ["Active-observation normalized RMS", "RMS normalizado de observaciones activas"], unit: "1",
      meaning: ["Noise-normalized prediction residual on observations used in the solve. Compare withheld error separately; low fitting error is not a recovery verdict.", "Residuo de predicción normalizado por ruido en observaciones utilizadas en el ajuste. Compare aparte el error omitido; ajustar datos no es un veredicto de recuperación."],
    },
    heldout_wrms: {
      name: ["Withheld-observation normalized RMS", "RMS normalizado de observaciones omitidas"], unit: "1",
      meaning: ["Noise-normalized residual on observations excluded from inversion. No omitted observations means this metric is unavailable, not zero.", "Residuo normalizado por ruido en observaciones excluidas de la inversión. Sin observaciones omitidas, la métrica no está disponible, no es cero."],
    },
    initial_model_rmse: {
      name: ["Initial-model RMSE", "RMSE del modelo inicial"], unit: property,
      meaning: ["Model error of the prescribed starting model against the synthetic target, on the same parameters as final-model error.", "Error del modelo inicial prescrito frente al objetivo sintético, en los mismos parámetros que el error final."],
    },
    zero_model_rmse: {
      name: ["Zero-model RMSE", "RMSE del modelo cero"], unit: property,
      meaning: ["Error from predicting zero property contrast everywhere. A diagnostic baseline, not a geological solution.", "Error al predecir contraste cero en todas las celdas. Referencia diagnóstica, no solución geológica."],
    },
    baseline_rmse: {
      name: ["Baseline-model RMSE", "RMSE del modelo de referencia"], unit: property,
      meaning: ["Error of the evaluator's declared zero or starting-model baseline, on the same target and support as the reported comparison.", "Error de la referencia cero o inicial declarada por el evaluador, en el mismo objetivo y soporte que la comparación."],
    },
    baseline_ratio: {
      name: ["Final / baseline model error", "Error final / error de referencia"], unit: "1",
      meaning: ["Final-model RMSE divided by baseline RMSE. Below one improves that baseline; above one worsens it. This ratio alone does not establish identifiability.", "RMSE final dividido por RMSE de referencia. Menor que uno mejora esa referencia; mayor que uno la empeora. No establece por sí solo identificabilidad."],
    },
    correlation: {
      name: ["Target–estimate correlation", "Correlación objetivo–estimación"], unit: "1",
      meaning: ["Signed spatial correlation between target and estimate. It does not assess absolute amplitude; the evaluator records zero for a constant field instead of assigning recovery.", "Correlación espacial con signo entre objetivo y estimación. No evalúa amplitud absoluta; el evaluador registra cero para campos constantes sin asignar recuperación."],
    },
    support_rmse: {
      name: ["Target-support RMSE", "RMSE en soporte del objetivo"], unit: property,
      meaning: ["Model error on the target's declared non-background support, excluding background dilution. For potential/column fields the support is |truth| > 5% of its maximum absolute value.", "Error del modelo en el soporte declarado del objetivo, sin dilución del fondo. En campos potenciales/columnas, el soporte es |verdad| > 5% de su máximo absoluto."],
    },
    background_rmse: {
      name: ["Background RMSE", "RMSE del fondo"], unit: property,
      meaning: ["Model error outside the declared target support; complements support error without merging the two populations.", "Error fuera del soporte declarado del objetivo; complementa el error del soporte sin mezclar ambas poblaciones."],
    },
    centroid_error_m: {
      name: ["Property-centroid displacement", "Desplazamiento del centroide de propiedad"], unit: "m",
      meaning: ["Distance between target and recovered absolute-property-weighted centroids. A small centroid error does not imply a correct shape.", "Distancia entre centroides ponderados por propiedad absoluta del objetivo y la recuperación. Un error pequeño no implica forma correcta."],
    },
    direction_error_deg: {
      name: ["Magnetization direction error", "Error de dirección de magnetización"], unit: "°",
      meaning: ["Angular discrepancy between recovered and target magnetization on the evaluator's stated support. Amplitude errors are evaluated separately.", "Discrepancia angular entre magnetización recuperada y objetivo en el soporte del evaluador. Los errores de amplitud se evalúan aparte."],
    },
    wrms: {
      name: ["Noise-normalized data RMS", "RMS de datos normalizado por ruido"],
      unit: "1",
      meaning:
        family === "mt"
          ? [
              "√mean(|Zpred−Zobs|²/σ²), over all frequencies. Noise is independent in real and imaginary parts, so the true-response expectation is approximately √2. Coverage-excluded frequencies remain in this reported metric.",
              "√media(|Zpred−Zobs|²/σ²), sobre todas las frecuencias. El ruido real e imaginario es independiente; en la verdad se espera aproximadamente √2. Incluye frecuencias excluidas del ajuste.",
            ]
          : ["joint", "joint-uncoupled", "pgi"].includes(method)
            ? [
                "√mean((Gρ−d)²/σ²) over active gravity stations only. Withheld stations have a separate error metric. It measures data agreement, not density accuracy.",
                "√media((Gρ−d)²/σ²) sólo en estaciones gravimétricas activas. Las omitidas tienen una métrica separada. Mide acuerdo de datos, no precisión de densidad.",
              ]
            : [
                "√mean((Gm−d)²/σ²), evaluated over active stations only. This score measures observation agreement, not model recovery.",
                "√media((Gm−d)²/σ²), sólo en estaciones activas. Esta métrica mide acuerdo con observaciones, no recuperación del modelo.",
              ],
    },
    rmse: {
      name: ["Data RMSE", "RMSE de datos"],
      unit: family === "magnetics" ? "nT" : "mGal",
      meaning: [
        "Root mean squared prediction residual over active stations. The exported residual map also includes inactive stations.",
        "Raíz del residuo cuadrático medio en estaciones activas. El mapa exportado incluye también estaciones inactivas.",
      ],
    },
    model_rmse: {
      name: method === "cnn" ? ["Column-target RMSE", "RMSE del objetivo de columnas"] : ["Cell-property RMSE", "RMSE de propiedad por celda"],
      unit: property,
      meaning: [
        "√mean((m̂−mtrue)²) over every model cell, including zero-background cells. Background volume affects this metric; it is not a boundary-position error.",
        "√media((m̂−mreal)²) sobre todas las celdas, incluidas las de fondo cero. El volumen de fondo afecta la métrica; no mide posición de interfaces.",
      ],
    },
    model_norm: {
      name: ["Model L2 norm", "Norma L2 del modelo"],
      unit: property,
      meaning: [
        "Euclidean norm of the property coefficients. It measures model magnitude, not error; smaller is not inherently better. Vector inversion uses all three component blocks.",
        "Norma euclídea de coeficientes. Mide magnitud, no error; menor no implica mejor. En inversión vectorial usa los tres bloques de componentes.",
      ],
    },
    log_model_rmse: {
      name: ["Log-resistivity RMSE", "RMSE de log resistividad"],
      unit: "1",
      meaning: [
        "√mean(ln(ρ̂/ρtrue)²) over layers. This measures multiplicative model error; it is not an Ω m error or an uncertainty interval.",
        "√media(ln(ρ̂/ρreal)²) sobre capas. Mide error multiplicativo, no error en Ω m ni intervalo de incertidumbre.",
      ],
    },
    velocity_rmse: {
      name: ["Velocity RMSE", "RMSE de velocidad"],
      unit: "m/s",
      meaning: [
        "√mean((v̂−vtrue)²) over all velocity nodes. This can remain high after waveform misfit is reduced.",
        "√media((v̂−vreal)²) sobre todos los nodos. Puede seguir alto después de reducir el desajuste de onda.",
      ],
    },
    initial_relative_mse: {
      name: ["Initial relative waveform MSE", "MSE relativo inicial de onda"],
      unit: "1",
      meaning: [
        "Mean squared initial waveform residual divided by observed mean-square amplitude, using full internal traces. The initial velocity is a prescribed depth trend.",
        "Media del residuo inicial cuadrado dividida por amplitud observada cuadrática media, con trazas internas completas. La velocidad inicial es una tendencia prescrita.",
      ],
    },
    relative_mse: {
      name: ["Relative waveform MSE", "MSE relativo de onda"],
      unit: "1",
      meaning: [
        "Mean squared unfiltered receiver residual divided by observed mean-square amplitude. Evaluated before export downsampling; neither regularization nor continuation filtering is included.",
        "Media del residuo de receptores sin filtrar al cuadrado dividida por amplitud observada cuadrática media. Se evalúa antes de reducir muestreo; excluye regularización y filtrado de continuación.",
      ],
    },
    magnetic_wrms: {
      name: ["Magnetic normalized RMS", "RMS magnético normalizado"],
      unit: "1",
      meaning: [
        "Noise-normalized magnetic residual RMS over active stations. It is a separate data-fit diagnostic for the joint model.",
        "RMS magnético normalizado por ruido en estaciones activas. Diagnóstico independiente del ajuste del modelo conjunto.",
      ],
    },
    cross_gradient: {
      name: [
        "Mean cross-gradient magnitude",
        "Magnitud media de gradiente cruzado",
      ],
      unit: "g/cm³ · SI / m²",
      meaning: [
        "Mean magnitude of the cross-gradient of physical density and susceptibility, using derivatives per metre. The optimizer instead penalizes normalized properties with a 240⁴ factor and fixed initial-penalty normalization; this diagnostic is not a probability.",
        "Magnitud media del gradiente cruzado de densidad y susceptibilidad físicas, con derivadas por metro. El optimizador penaliza propiedades normalizadas con factor 240⁴ y normalización por penalización inicial fija; este diagnóstico no es probabilidad.",
      ],
    },
    column_rmse: {
      name: ["Column-density RMSE", "RMSE de densidad integrada"],
      unit: "g/cm³ m",
      meaning: [
        "√mean((ĉ−ctrue)²) over horizontal columns. The CNN predicts integrated density, not depth-resolved cells.",
        "√media((ĉ−creal)²) sobre columnas horizontales. La CNN predice densidad integrada, no celdas resueltas en profundidad.",
      ],
    },
    reconstruction_mse: {
      name: [
        "Observation reconstruction MSE",
        "MSE de reconstrucción de observaciones",
      ],
      unit: "1",
      meaning: [
        "Mean squared autoencoder reconstruction residual divided by training-observation variance. A high score can reflect noise or acquisition shift; a low score does not prove familiar geology.",
        "Residuo cuadrático medio del autoencoder dividido por varianza de entrenamiento. Un valor alto puede reflejar ruido o adquisición; uno bajo no prueba geología conocida.",
      ],
    },
    threshold: {
      name: [
        "Independent-calibration 99th-percentile threshold",
        "Umbral percentil 99 de calibración independiente",
      ],
      unit: "1",
      meaning: [
        "An empirical independent-calibration reconstruction-error quantile, frozen before test evaluation. Not a confidence level or a geological detection probability.",
        "Cuantil empírico independiente de error de reconstrucción, fijado antes de prueba. No es nivel de confianza ni probabilidad de detección geológica.",
      ],
    },
    above_threshold: {
      name: [
        "Reconstruction score exceeds threshold",
        "Error de reconstrucción supera umbral",
      ],
      unit: "",
      meaning: [
        "True only when mean reconstruction error exceeds the fixed validation threshold. False may be a missed unfamiliar geometry.",
        "Verdadero sólo si el error medio supera el umbral fijo. Falso puede corresponder a una geometría desconocida no detectada.",
      ],
    },
  };
  const aliases: Record<string, string> = { withheld_wrms: "heldout_wrms", model_correlation: "correlation", initial_rmse: "initial_model_rmse", zero_rmse: "zero_model_rmse", active_rmse: "rmse", model_baseline_ratio: "baseline_ratio" };
  Object.assign(aliases, { initial_velocity_rmse: "initial_model_rmse", initial_log_model_rmse: "initial_model_rmse", model_rmse_ratio: "baseline_ratio", model_error_ratio: "baseline_ratio" });
  const componentEntries: Record<string, { name: Text; unit: string; meaning: Text }> = {
    active_component_wrms: { name: ["Active real-component WRMS", "WRMS activo por componente real"], unit: "1", meaning: ["√mean of the squared, noise-normalized real and imaginary residual components at active frequencies. The true-response noise expectation is approximately one, unlike complex WRMS (√2).", "Raíz de la media de residuos reales e imaginarios normalizados al cuadrado en frecuencias activas. Con ruido se espera aproximadamente uno, a diferencia del WRMS complejo (√2)."] },
    withheld_component_wrms: { name: ["Withheld real-component WRMS", "WRMS omitido por componente real"], unit: "1", meaning: ["Same real-component normalization, evaluated only at frequencies excluded from inversion. Undefined when no frequencies are withheld.", "La misma normalización por componente, sólo en frecuencias excluidas de inversión. Indefinido si no hay frecuencias omitidas."] },
    initial_component_wrms: { name: ["Initial real-component WRMS", "WRMS inicial por componente real"], unit: "1", meaning: ["Active-frequency real-component WRMS of the common prescribed starting resistivities.", "WRMS por componente en frecuencias activas de las resistividades iniciales comunes."] },
    objective: { name: ["Complete selected objective", "Objetivo completo seleccionado"], unit: "1", meaning: ["The exported objective evaluated on the selected model, including its data and regularization terms.", "Objetivo exportado evaluado en el modelo seleccionado, incluidos datos y regularización."] },
    data_objective: { name: ["Data-objective contribution", "Contribución de datos al objetivo"], unit: "1", meaning: ["Observation residual contribution to the complete objective under the declared normalization.", "Contribución del residuo de observaciones al objetivo completo con la normalización declarada."] },
    regularization_objective: { name: ["Regularization contribution", "Contribución de regularización"], unit: "1", meaning: ["Regularization contribution including its exported tradeoff weight; not a data-fit or geological accuracy score.", "Contribución de regularización con su peso exportado; no mide ajuste de datos ni precisión geológica."] },
    velocity_bias: { name: ["Mean velocity bias", "Sesgo medio de velocidad"], unit: "m/s", meaning: ["Mean signed velocity difference from the target over the entire model.", "Diferencia de velocidad media con signo respecto al objetivo en todo el modelo."] },
    velocity_min: { name: ["Minimum recovered velocity", "Velocidad recuperada mínima"], unit: "m/s", meaning: ["Smallest velocity in the final selected model.", "Menor velocidad del modelo final seleccionado."] },
    velocity_max: { name: ["Maximum recovered velocity", "Velocidad recuperada máxima"], unit: "m/s", meaning: ["Largest velocity in the final selected model.", "Mayor velocidad del modelo final seleccionado."] },
    bound_fraction: { name: ["Fraction near velocity bounds", "Fracción próxima a cotas de velocidad"], unit: "1", meaning: ["Fraction of nodes within the solver's declared tolerance of a velocity bound.", "Fracción de nodos dentro de la tolerancia declarada respecto a una cota de velocidad."] },
  };
  const seismicParts: Record<string, Text> = { shallow: ["Shallow region", "Región superficial"], middle: ["Middle-depth region", "Región intermedia"], deep: ["Deep region", "Región profunda"], departure: ["Target departure from initial model", "Desviación del objetivo respecto al inicial"], background: ["Background region", "Región de fondo"] };
  const depth = key.match(/^(shallow|middle|deep|departure|background)_(initial_)?rmse$/);
  if (family === "seismic" && depth) {
    const part = seismicParts[depth[1]][es ? 1 : 0];
    return { label: part + (depth[2] ? es ? " · RMSE inicial" : " · initial RMSE" : " · RMSE"), unit: "m/s", description: es ? "Error de velocidad en la región declarada por el evaluador, sin promediar otras profundidades o poblaciones." : "Velocity error on the evaluator's declared region, without averaging other depths or populations." };
  }
  const waveform = key.match(/^(initial_)?(active|withheld)_relative_mse$/);
  if (waveform) return {
    label: (waveform[1] ? es ? "MSE relativo inicial" : "Initial relative MSE" : es ? "MSE relativo final" : "Final relative MSE") + " · " + (waveform[2] === "active" ? es ? "receptores activos" : "active receivers" : es ? "receptores omitidos" : "withheld receivers"),
    unit: "1", description: es ? "Residuo de onda cuadrático medio dividido por amplitud observada cuadrática media, sólo para la población de receptores indicada." : "Mean squared waveform residual divided by observed mean-square amplitude, only for the named receiver population."
  };
  const item = componentEntries[key] ?? entries[aliases[key] ?? key];
  return item
    ? {
        label: item.name[es ? 1 : 0],
        unit: item.unit,
        description: item.meaning[es ? 1 : 0],
      }
    : { label: es ? "Diagnóstico adicional del evaluador" : "Additional evaluator diagnostic", unit: "", description: es ? "Definición pendiente de sincronización con el contrato del evaluador; consulte la exportación." : "Definition pending synchronization with the evaluator contract; consult the exported result." };
}
export function historyInfo(method: string, es: boolean) {
  const learned = ["cnn", "autoencoder"].includes(method);
  const label = ["l2", "irls", "vector"].includes(method)
    ? ["Noise-normalized residual MSE", "MSE del residuo normalizado"]
    : learned
      ? ["Validation MSE", "MSE de validación"]
      : method.startsWith("fwi")
        ? ["Relative waveform MSE", "MSE relativo de onda"]
        : ["Recorded loss", "Pérdida registrada"];
  const axis = ["l2", "irls", "vector"].includes(method)
    ? ["Linear solve index", "Índice de solución lineal"]
    : learned
      ? ["Training epoch", "Época de entrenamiento"]
      : ["joint", "joint-uncoupled", "pgi"].includes(method)
        ? ["Recorded optimizer state", "Estado registrado del optimizador"]
      : method === "mt-lm"
        ? ["Residual evaluation", "Evaluación de residuo"]
        : ["Optimizer step", "Paso del optimizador"];
  return {
    label: label[es ? 1 : 0],
    axis: axis[es ? 1 : 0],
    stride: learned
      ? 5
      : method === "joint"
        ? 1
        : method.startsWith("mt-") && method !== "mt-lm"
          ? 1
          : 1,
    description: algorithmFor(method)?.history[es ? 1 : 0] ?? "",
  };
}
