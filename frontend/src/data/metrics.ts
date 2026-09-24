import type { Family } from "../science";
import { algorithmFor, type Text } from "./methods";
export function methodName(id: string, es: boolean, fallback = id) {
  return algorithmFor(id)?.title[es ? 1 : 0] ?? fallback;
}
export function metricInfo(
  key: string,
  family: Family,
  method = "",
  es = false,
) {
  const property = family === "magnetics" ? "SI" : "g/cm³";
  const entries: Record<string, { name: Text; unit: string; meaning: Text }> = {
    wrms: {
      name: ["Noise-normalized data RMS", "RMS de datos normalizado por ruido"],
      unit: "1",
      meaning:
        family === "mt"
          ? [
              "√mean(|Zpred−Zobs|²/σ²), over all frequencies. Noise is independent in real and imaginary parts, so the true-response expectation is approximately √2. Coverage-excluded frequencies remain in this reported metric.",
              "√media(|Zpred−Zobs|²/σ²), sobre todas las frecuencias. El ruido real e imaginario es independiente; en la verdad se espera aproximadamente √2. Incluye frecuencias excluidas del ajuste.",
            ]
          : method === "joint"
            ? [
                "√mean((Gρ−d)²/σ²) over all gravity stations, including excluded coverage stations. It measures data agreement, not density accuracy.",
                "√media((Gρ−d)²/σ²) en todas las estaciones gravimétricas, incluidas las excluidas del ajuste. Mide acuerdo de datos, no precisión de densidad.",
              ]
            : [
                "√mean((Gm−d)²/σ²), evaluated over active stations only. σ is used in this metric, not as a weight in the potential-field solve.",
                "√media((Gm−d)²/σ²), sólo en estaciones activas. σ se usa en esta métrica, no como peso en la inversión potencial.",
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
      name: ["Cell-property RMSE", "RMSE de propiedad por celda"],
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
        "Noise-normalized magnetic residual RMS over all stations. It is a separate data-fit diagnostic for the joint model.",
        "RMS magnético normalizado por ruido en todas las estaciones. Diagnóstico independiente del ajuste del modelo conjunto.",
      ],
    },
    cross_gradient: {
      name: [
        "Mean cross-gradient magnitude",
        "Magnitud media de gradiente cruzado",
      ],
      unit: "cell-index",
      meaning: [
        "Mean norm of the cross-gradient of normalized properties in cell-index coordinates. Not the mean squared component penalty optimized by the solver; not a probability.",
        "Media de la norma del gradiente cruzado de propiedades normalizadas por índices. No es la penalización de componentes cuadrados optimizada ni una probabilidad.",
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
        "Validation 99th-percentile threshold",
        "Umbral percentil 99 de validación",
      ],
      unit: "1",
      meaning: [
        "An empirical validation reconstruction-error quantile, frozen before test evaluation. Not a confidence level or a geological detection probability.",
        "Cuantil empírico de error de reconstrucción, fijado antes de prueba. No es nivel de confianza ni probabilidad de detección geológica.",
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
  const item = entries[key];
  return item
    ? {
        label: item.name[es ? 1 : 0],
        unit: item.unit,
        description: item.meaning[es ? 1 : 0],
      }
    : { label: key, unit: "", description: "" };
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
      : method === "mt-lm"
        ? ["Residual evaluation", "Evaluación de residuo"]
        : ["Optimizer step", "Paso del optimizador"];
  return {
    label: label[es ? 1 : 0],
    axis: axis[es ? 1 : 0],
    stride: learned
      ? 5
      : method === "joint"
        ? 6
        : method.startsWith("mt-") && method !== "mt-lm"
          ? 10
          : 1,
    description: algorithmFor(method)?.history[es ? 1 : 0] ?? "",
  };
}
