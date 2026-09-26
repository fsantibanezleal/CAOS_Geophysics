import type { Evaluation, Run } from "../science";

export function evaluationLabel(status: Evaluation["status"] | undefined, es: boolean): string {
  const labels = {
    recovered: ["Recovery criteria met", "Criterios de recuperación cumplidos"],
    unresolved: ["Recovery unresolved", "Recuperación no resuelta"],
    failed: ["Recovery criteria failed", "Criterios de recuperación incumplidos"],
    "negative-control": ["Declared negative control", "Control negativo declarado"],
  };
  return status && labels[status] ? labels[status][es ? 1 : 0] : es ? "Recuperación no evaluada" : "Recovery not evaluated";
}

const reasons: Record<string, [string, string]> = {
  whole_model_not_improved: ["Whole-model error does not improve on the independent starting model.", "El error total no mejora el modelo inicial independiente."],
  waveform_not_improved: ["Active waveform error does not improve on the starting model.", "El error de onda activo no mejora el modelo inicial."],
  withheld_data_not_improved: ["Withheld waveform error does not improve on the starting model.", "El error de onda omitido no mejora el modelo inicial."],
  salt_cycle_skipping_challenge: ["Salt is a declared cycle-skipping challenge; apparent fit is not accepted as verified recovery.", "La sal es un desafío declarado de salto de ciclos; el ajuste aparente no se acepta como recuperación verificada."],
  solver_failure: ["The optimizer did not report successful convergence.", "El optimizador no informó convergencia satisfactoria."],
  data_misfit_exceeds_threshold: ["Data error exceeds the evaluator's declared acceptance threshold.", "El error de datos supera el umbral de aceptación declarado."],
  model_not_better_than_initial: ["Model error does not improve on the independent initial model.", "El error del modelo no mejora el modelo inicial independiente."],
  conditional_synthetic_recovery_over_initial: ["Conditional synthetic recovery improves on the initial model under the declared fit and local-identifiability criteria; uniqueness is not established.", "La recuperación sintética condicional mejora el modelo inicial bajo los criterios declarados de ajuste e identificabilidad local; no se establece unicidad."],
  local_identifiability_weak: ["Local data sensitivity is insufficient to resolve every parameter independently.", "La sensibilidad local es insuficiente para resolver independientemente cada parámetro."],
  no_independent_geological_truth: ["No independent geological target is supplied; data fit cannot verify recovery.", "No se aporta un objetivo geológico independiente; el ajuste no verifica recuperación."],
  "withheld-data-not-predicted": ["Withheld-station WRMS exceeds 2.", "WRMS de estaciones omitidas supera 2."],
  "no-improvement-over-initial-model": ["Whole-model RMSE is no better than the zero/initial baseline.", "El RMSE total no mejora la referencia cero/inicial."],
  "low-model-correlation": ["Target–estimate correlation is below 0.5.", "Correlación objetivo–estimación menor que 0,5."],
  "active-data-misfit-above-noise": ["Active-station WRMS exceeds 2.", "WRMS de estaciones activas supera 2."],
  "deliberately-misspecified-physical-model": ["The physical or petrophysical prior is deliberately misspecified.", "El modelo físico o prior petrofísico es deliberadamente incorrecto."],
  "coupling-does-not-improve-independent-density-recovery": ["Coupling does not improve independent density recovery.", "El acoplamiento no mejora recuperación independiente de densidad."],
  "held-out-geological-family": ["This geometric family was excluded from training.", "Esta familia geométrica se excluyó del entrenamiento."],
  "column-target-not-three-dimensional-recovery": ["Only depth-integrated columns are evaluated, not 3D recovery.", "Se evalúan columnas integradas, no recuperación 3D."],
  "does-not-improve-classical-baseline": ["CNN column error does not improve the matched classical baseline.", "El error de columna CNN no mejora la referencia clásica comparable."],
  "withheld-geometric-family-detected": ["The withheld geometry exceeds the calibrated novelty threshold.", "La geometría omitida supera el umbral calibrado de novedad."],
  "withheld-geometric-family-missed": ["The withheld geometry is missed by the novelty detector.", "El detector de novedad no detecta la geometría omitida."],
  baseline_improved: ["Model error improves on the declared baseline.", "El error del modelo mejora la referencia declarada."],
  baseline_not_improved: ["Model error does not improve on the declared baseline.", "El error del modelo no mejora la referencia declarada."],
  worse_than_baseline: ["Model error exceeds the baseline error.", "El error del modelo supera el error de referencia."],
  heldout_misfit: ["Omitted observations are not predicted within the declared tolerance.", "Las observaciones omitidas no se predicen dentro de la tolerancia declarada."],
  data_fit_only: ["Observation agreement does not establish model recovery.", "El acuerdo con observaciones no establece recuperación del modelo."],
  bound_hit: ["A recovered parameter reaches a solver bound.", "Un parámetro recuperado alcanza un límite del optimizador."],
  negative_control: ["This experiment deliberately violates an inverse-model assumption.", "Este experimento viola deliberadamente un supuesto del modelo inverso."],
  prior_mismatch: ["The petrophysical prior is intentionally mismatched.", "El prior petrofísico es deliberadamente incompatible."],
  model_mismatch: ["Forward and inverse assumptions are mismatched.", "Los supuestos directo e inverso son incompatibles."],
  nonfinite: ["Nonfinite output invalidates this result.", "Una salida no finita invalida este resultado."],
  no_ground_truth: ["The subsurface target is unknown; model recovery cannot be scored.", "El subsuelo objetivo es desconocido; no se puede evaluar su recuperación."],
};
export function evaluationReason(code: string, es: boolean): string {
  return reasons[code]?.[es ? 1 : 0] ?? (es
    ? "El evaluador exportó una condición adicional; consulte el registro de evaluación descargable."
    : "The evaluator exported an additional condition; consult the downloadable evaluation record.");
}

export function targetDescription(run: Run, methodId: string, es: boolean): string {
  const t = (en: string, sp: string) => es ? sp : en;
  const method = run.methods[methodId];
  if (method?.target) {
    const names: Record<string, [string, string]> = {
      "depth-integrated_density_contrast": ["Depth-integrated density contrast (column, not 3D recovery)", "Contraste de densidad integrado en profundidad (columna, no recuperación 3D)"],
      "effective_magnetization_/_inducing-field_amplitude": ["Effective magnetization / inducing-field amplitude (not induced susceptibility)", "Magnetización efectiva / amplitud del campo inductor (no susceptibilidad inducida)"],
      density_contrast_with_jointly_estimated_susceptibility: ["Density contrast with jointly estimated susceptibility", "Contraste de densidad con susceptibilidad estimada conjuntamente"],
      normalized_observation_reconstruction_error: ["Normalized observation reconstruction error (not subsurface recovery)", "Error normalizado de reconstrucción de observaciones (no recuperación del subsuelo)"],
      effective_magnetization: ["Effective magnetization", "Magnetización efectiva"],
      magnetic_susceptibility: ["Magnetic susceptibility", "Susceptibilidad magnética"],
      density_contrast: ["Density contrast", "Contraste de densidad"],
      density: ["Density contrast", "Contraste de densidad"],
      susceptibility: ["Magnetic susceptibility", "Susceptibilidad magnética"],
      magnetization_amplitude: ["Magnetization amplitude", "Amplitud de magnetización"],
      magnetization: ["Magnetization", "Magnetización"],
      resistivity: ["Layer resistivity", "Resistividad por capa"],
      velocity: ["Acoustic velocity", "Velocidad acústica"],
      acoustic_velocity: ["Acoustic velocity", "Velocidad acústica"],
      column_density: ["Depth-integrated density", "Densidad integrada en profundidad"],
      reconstruction_error: ["Observation reconstruction error", "Error de reconstrucción de observaciones"],
    };
    const quantity = method.target.quantity.toLowerCase().replaceAll(" ", "_");
    if (quantity === "electrical_resistivity") return t("Layer resistivity", "Resistividad por capa") + " · " + method.target.units;
    const title = names[quantity]?.[es ? 1 : 0];
    if (title) return title + " · " + (method.target.units === "normalized squared error" ? t("normalized squared error", "error cuadrático normalizado") : method.target.units) + " · " + method.target.dimensionality + (typeof method.target.dimensionality === "number" ? "D" : "");
  }
  if (methodId === "cnn") return t("Depth-integrated density · g/cm³ m; not a depth-resolved 3D body.", "Densidad integrada en profundidad · g/cm³ m; no un cuerpo 3D resuelto en profundidad.");
  if (methodId === "autoencoder") return t("Observed gravity map reconstruction and normalized squared error; not subsurface geology.", "Reconstrucción del mapa de gravedad observado y error cuadrático normalizado; no geología del subsuelo.");
  if (methodId === "vector") return t("Three magnetization components; the volume displays their amplitude · SI. Amplitude alone does not validate direction.", "Tres componentes de magnetización; el volumen muestra su amplitud · SI. La amplitud no valida la dirección.");
  const targets = {
    gravity: t("Cell density contrast · g/cm³", "Contraste de densidad por celda · g/cm³"),
    magnetics: t("Cell magnetic susceptibility · SI", "Susceptibilidad magnética por celda · SI"),
    joint: t("Cell density contrast · g/cm³ and susceptibility · SI", "Contraste de densidad por celda · g/cm³ y susceptibilidad · SI"),
    mt: t("Layer resistivity · Ω m; thicknesses are prescribed", "Resistividad por capa · Ω m; espesores prescritos"),
    seismic: t("Acoustic velocity · m/s", "Velocidad acústica · m/s"),
    learned: t("Cell density contrast · g/cm³", "Contraste de densidad por celda · g/cm³"),
  };
  return targets[run.family];
}

export function provenanceDescription(run: Run, es: boolean): string {
  const p = run.provenance;
  const custom = es ? p.description_es : p.description;
  if (custom) return custom;
  if (!p.synthetic) return es
    ? "Observaciones externas. No se presume conocida la geología; el ajuste de datos no demuestra recuperación del subsuelo."
    : "External observations. Geological truth is not presumed known; data agreement is not proof of subsurface recovery.";
  return es
    ? "Objetivo sintético construido, no geología medida. Los datos se calculan con un operador físico y ruido prescrito. La verdad sólo evalúa la recuperación."
    : "Constructed synthetic target, not measured geology. Data are calculated with a physical operator and prescribed noise. Truth is used to evaluate recovery.";
}

export function targetProvenance(run: Run, methodId: string, es: boolean): string {
  const source = run.methods[methodId]?.target?.provenance;
  if (!source) return provenanceDescription(run, es);
  const translations: Record<string, string> = {
    "Original seeded synthetic geological reference": "Referencia geológica sintética original con semilla declarada",
    "Independent original synthetic geological reference": "Referencia geológica sintética original independiente",
    "Three-component model; scalar amplitude is not induced susceptibility under remanence": "Modelo de tres componentes; con remanencia, la amplitud escalar no es susceptibilidad inducida",
    "original synthetic transfer functions; target truth used only for generation and evaluation": "Funciones de transferencia sintéticas originales; verdad utilizada sólo para generación y evaluación",
    "synthetic known velocity; not measured field truth": "Velocidad sintética conocida; no es verdad medida en campo",
    "Depth integral of original synthetic volume; not a reconstructed depth profile": "Integral en profundidad del volumen sintético original; no es un perfil de profundidad reconstruido",
    "Known withheld geometry; no subsurface recovery claim": "Geometría omitida conocida; no afirma recuperación del subsuelo",
  };
  return es ? translations[source] ?? source : source;
}
