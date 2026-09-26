import { useState } from "react";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { evaluationLabel, evaluationReason, targetProvenance, targetDescription } from "../data/evidence";
import { metricInfo } from "../data/metrics";
import { flatten, format, sliceVolume, type DetectionValidation, type Method, type ModelArray, type Run } from "../science";
import { membershipField, propertyScale, sharedScale, uncertaintyProblem } from "../recovery";
import { PotentialCalibration } from "./PotentialCalibration";
import { Heatmap, Plot } from "./ScientificPlots";

export function EvaluationStatus({ method }: { method: Pick<Method, "evaluation"> }) {
  const es = useShellLang() === "es";
  const evaluation = method.evaluation;
  return <div className="evaluation-status" data-evaluation={evaluation?.status ?? "unassessed"}>
    <strong>{evaluationLabel(evaluation?.status, es)}</strong>
    {!!evaluation?.reason_codes?.length && <details>
      <summary>{es ? "Criterios de evaluación" : "Evaluation criteria"}</summary>
      <ul>{evaluation.reason_codes.map(code => <li key={code}>{evaluationReason(code, es)}</li>)}</ul>
    </details>}
    {!evaluation && <p className="plot-note">{es ? "Este artefacto no contiene un veredicto de recuperación. Ajustar datos o ejecutar sin errores no lo sustituye." : "This artifact has no recovery verdict. Data fit or successful execution does not supply one."}</p>}
  </div>;
}

export function EvidenceMetrics({ run, methodId }: { run: Run; methodId: string }) {
  const es = useShellLang() === "es";
  const method = run.methods[methodId];
  return <div className="table-scroll"><table className="cmp-table">
    <caption>{es ? "Evidencia de la solución final seleccionada" : "Evidence for the final selected solution"}</caption>
    <thead><tr><th>{es ? "Métrica" : "Metric"}</th><th>{es ? "Valor" : "Value"}</th><th>{es ? "Población y significado" : "Population and meaning"}</th></tr></thead>
    <tbody>{Object.entries(method.metrics).map(([key, value]) => {
      const info = metricInfo(key, run.family, methodId, es);
      return <tr key={key}><th scope="row">{info.label}</th><td>{typeof value === "boolean" ? value ? es ? "Sí" : "Yes" : "No" : value == null || !Number.isFinite(value) ? es ? "No disponible" : "Unavailable" : format(value)} {info.unit}</td><td>{info.description}</td></tr>;
    })}</tbody>
  </table></div>;
}

export function TargetEvidence({ run, methodId }: { run: Run; methodId: string }) {
  const es = useShellLang() === "es";
  return <div className="target-evidence">
    <p><strong>{es ? "Objetivo estimado: " : "Estimated target: "}</strong>{targetDescription(run, methodId, es)}</p>
    <p className="plot-note">{targetProvenance(run, methodId, es)}</p>
    <ApplicabilityWarning method={run.methods[methodId]} />
    <EvaluationStatus method={run.methods[methodId]} />
  </div>;
}

export function ApplicabilityWarning({ method }: { method: Pick<Method, "applicability"> }) {
  const es = useShellLang() === "es";
  if (method.applicability?.varied_parameter !== false) return null;
  return <p role="note" className="plot-note"><strong>{es ? "No es una intervención sobre esta red: " : "Not an intervention on this network: "}</strong>{es ? "El checkpoint está congelado. Esta condición cambia la regularización del comparador clásico, no entrena ni regulariza de nuevo la CNN o el autoencoder." : "The checkpoint is frozen. This condition changes the classical comparator’s regularization; it does not retrain or re-regularize the CNN or autoencoder."}</p>;
}

export function DetectionEvidence({ data }: { data?: DetectionValidation }) {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => es ? b : a;
  if (!data) return null;
  return <section className="evidence-layout">
    <h3>{t("Held-out novelty detection", "Detección de novedad independiente")}</h3>
    <p className="evaluation-status" data-evaluation={data.true_positive === 0 ? "failed" : "unresolved"}><strong>{data.true_positive} / {data.ood_count} {t("withheld-family cases detected", "casos de familias omitidas detectados")}.</strong> {data.true_positive === 0 ? t("The detector missed every tested OOD case. High specificity does not compensate for zero sensitivity.", "El detector omitió todos los casos OOD de prueba. Una especificidad alta no compensa sensibilidad cero.") : t("This count is not a field-detection guarantee.", "Este conteo no garantiza detección de campo.")}</p>
    <p className="plot-note">{t("Ground truth is whether a realization belongs to a withheld geometric family, not whether its subsurface has been recovered. Threshold calibration is separate from checkpoint validation and this test set. Misses and false alarms remain in the denominators.", "La verdad indica si una realización pertenece a una familia geométrica omitida, no si se recuperó el subsuelo. La calibración del umbral es separada de validación de pesos y de esta prueba. Fallos y falsas alarmas permanecen en los denominadores.")}</p>
    <div className="table-scroll"><table className="cmp-table"><caption>{t("Frozen-threshold confusion counts", "Conteos de confusión con umbral fijo")}</caption><thead><tr><th>{t("True family", "Familia verdadera")}</th><th>{t("Flagged unfamiliar", "Marcada desconocida")}</th><th>{t("Not flagged", "No marcada")}</th></tr></thead><tbody><tr><th scope="row">{t("Withheld family", "Familia omitida")}</th><td>{data.true_positive}</td><td>{data.false_negative} · {t("misses", "fallos")}</td></tr><tr><th scope="row">{t("Generator-distribution test", "Prueba de distribución generadora")}</th><td>{data.false_positive} · {t("false alarms", "falsas alarmas")}</td><td>{data.true_negative}</td></tr></tbody></table></div>
    <dl className="parameter-ledger">
      <div><dt>{t("Sensitivity: detected / withheld", "Sensibilidad: detectados / omitidos")}</dt><dd>{format(data.sensitivity)}</dd></div>
      <div><dt>{t("Specificity: unflagged / in-distribution", "Especificidad: no marcados / en distribución")}</dt><dd>{format(data.specificity)}</dd></div>
      <div><dt>{t("ROC AUC: pairwise ranking", "ROC AUC: ordenamiento por pares")}</dt><dd>{format(data.roc_auc)}</dd></div>
      <div><dt>{t("Independent calibration realizations", "Realizaciones de calibración independientes")}</dt><dd>{data.calibration_count}</dd></div>
      <div><dt>{t("Calibration seed", "Semilla de calibración")}</dt><dd>{data.calibration_seed}</dd></div>
      <div><dt>{t("Withheld-family seed", "Semilla de familia omitida")}</dt><dd>{data.ood_seed}</dd></div>
    </dl>
    <p className="plot-note">{t("AUC is the probability that a withheld-family score exceeds an independent in-distribution score, with half credit for ties. None of these results establishes a universal out-of-distribution detector or field-data reliability.", "AUC es la probabilidad de que un puntaje omitido supere otro independiente en distribución, con medio crédito en empates. No establece un detector universal fuera de distribución ni fiabilidad de campo.")}</p>
  </section>;
}

function spatialMap(run: Run, array: ModelArray, section: number): number[][] {
  if (Array.isArray(array[0])) return array as number[][];
  if (run.grid?.shape.length === 3) return sliceVolume(array as number[], run.grid.shape, section);
  return [array as number[]];
}

export function UncertaintyView({ run, method, section }: { run: Run; method: Method; section: number }) {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => es ? b : a;
  const [quantity, setQuantity] = useState<"mean" | "std" | "width">("width");
  const u = method.uncertainty;
  if (!u) return null;
  const invalid = uncertaintyProblem(u, method.model);
  if (invalid) return <p role="alert">{t("Uncertainty artifact is incompatible with this model; intervals cannot be displayed.", "El artefacto de incertidumbre es incompatible con el modelo; no se pueden mostrar intervalos.")}</p>;
  const lo = flatten(u.lower), hi = flatten(u.upper), mean = flatten(u.mean);
  const unit = u.units ?? method.target?.units ?? method.units ?? run.units;
  const bandName = `${format(u.quantiles[0] * 100)}–${format(u.quantiles[1] * 100)}% ` + t("empirical quantiles", "cuantiles empíricos");
  const intervalWidth = hi.map((v, i) => v - lo[i]);
  const matrixWidth = Array.isArray(method.model[0])
    ? (method.model as number[][]).map((row, i) => intervalWidth.slice(i * row.length, (i + 1) * row.length)) : intervalWidth;
  const array = quantity === "width" ? matrixWidth : u[quantity];
  const titles = { mean: t("Ensemble mean", "Media del conjunto"), std: t("Ensemble standard deviation", "Desviación estándar del conjunto"), width: t("Empirical interval width", "Ancho del intervalo empírico") };
  const spatialRange = sharedScale([array], quantity === "mean" && flatten(array).some(v => v < 0)).range;
  return <section className="evidence-layout">
    <h3>{t("Conditional uncertainty", "Incertidumbre condicional")}</h3>
    {["gravity", "learned"].includes(run.family) && <PotentialCalibration />}
    <p className="plot-note">{u.kind === "conditional-parametric-bootstrap" ? t("Parametric noise bootstrap: repeated inversions conditional on the stated model, acquisition, noise law and solver. These intervals are not posterior geological probabilities.", "Bootstrap paramétrico de ruido: inversiones repetidas condicionadas al modelo, adquisición, ley de ruido y optimizador declarados. No son probabilidades geológicas posteriores.") : t("Exported ensemble intervals; their meaning is limited to the sampling procedure below. Posterior validity is not established.", "Intervalos del conjunto exportado; su significado se limita al muestreo indicado. No se establece validez posterior.")}</p>
    <p>{es ? u.conditioning_es ?? u.conditioning : u.conditioning}</p>
    <dl className="parameter-ledger">
      <div><dt>{t("Ensemble members", "Miembros del conjunto")}</dt><dd>{u.members}</dd></div>
      <div><dt>{t("Random seed", "Semilla aleatoria")}</dt><dd>{u.seed}</dd></div>
      <div><dt>{t("Synthetic pointwise coverage", "Cobertura puntual sintética")}</dt><dd>{u.coverage == null ? t("Unknown target / not measured", "Objetivo desconocido / no medida") : `${format(100 * u.coverage)}%`}</dd></div>
      {u.support_coverage != null && <div><dt>{t("Target-support coverage", "Cobertura en soporte del objetivo")}</dt><dd>{format(100 * u.support_coverage)}%</dd></div>}
      {u.background_coverage != null && <div><dt>{t("Background coverage", "Cobertura del fondo")}</dt><dd>{format(100 * u.background_coverage)}%</dd></div>}
    </dl>
    <p className="plot-note">{t("Coverage is the fraction of known synthetic target values inside the exported bounds. It is not the nominal quantile span and does not guarantee coverage for field data.", "La cobertura es la fracción de valores sintéticos conocidos dentro de los límites exportados. No es el ancho nominal de cuantiles ni garantiza cobertura en datos de campo.")}</p>
    {u.coverage != null && u.coverage < u.quantiles[1] - u.quantiles[0] && <p className="evaluation-status" data-evaluation="failed"><strong>{t("Synthetic undercoverage: ", "Subcobertura sintética: ")}{format(100 * u.coverage)}% {t("observed versus", "observada frente a")} {format(100 * (u.quantiles[1] - u.quantiles[0]))}% {t("nominal interval span.", "amplitud nominal del intervalo.")}</strong> {t("Conditional noise spread excludes regularization bias and geological ambiguity. These bounds are not calibrated geological uncertainty.", "La dispersión condicional de ruido excluye sesgo de regularización y ambigüedad geológica. Estos límites no son incertidumbre geológica calibrada.")}</p>}
    {run.family === "mt" ? <Plot
      title={t("Layer resistivity intervals", "Intervalos de resistividad por capa")}
      x={mean.map((_, i) => i + 1)}
      series={[{ name: t("Ensemble mean", "Media del conjunto"), values: mean }, { name: t("Selected final model", "Modelo final seleccionado"), values: flatten(method.model), dashed: true }, ...(run.provenance.target_known !== false && run.provenance.synthetic ? [{ name: t("Synthetic target", "Objetivo sintético"), values: flatten(run.truth), points: true }] : [])]}
      band={{ name: bandName, lower: lo, upper: hi }} xLabel={t("Layer index", "Índice de capa")} yLabel={unit} logY={lo.every(v => v > 0)}
    /> : <>
      <label className="select-control"><span>{t("Uncertainty quantity", "Magnitud de incertidumbre")}</span><select className="select" value={quantity} onChange={e => setQuantity(e.target.value as typeof quantity)}>{Object.entries(titles).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <Heatmap data={spatialMap(run, array, section)} title={`${titles[quantity]} · ${bandName}`} unit={unit} range={spatialRange} palette={quantity === "mean" ? "field" : "error"} xLabel={t("Easting / distance · m", "Este / distancia · m")} yLabel={t("Depth · m", "Profundidad · m")} xRange={run.grid?.shape.length === 3 ? [-1120, 1120] : undefined} yRange={run.grid?.shape.length === 3 ? [0, 1120] : undefined} />
    </>}
  </section>;
}

export function PetrophysicalView({ run, methodId, section }: { run: Run; methodId: string; section: number }) {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => es ? b : a;
  const [component, setComponent] = useState(0);
  const method = run.methods[methodId];
  const secondary = method.magnetic_model ?? method.secondary_model;
  if (!run.grid || !secondary) return null;
  const classes = method.prior_membership?.[0]?.length ?? method.responsibilities?.[0]?.length ?? 0;
  const chosen = Math.min(component, classes - 1);
  const membership = membershipField(method, chosen, secondary.length);
  const range = propertyScale(run, methodId, true).range;
  const map = (values: number[], title: string, unit: string, bounds?: [number, number]) => <Heatmap data={sliceVolume(values, run.grid!.shape, section)} title={title} unit={unit} range={bounds} xLabel={t("Easting · m", "Este · m")} yLabel={t("Depth · m", "Profundidad · m")} xRange={[-1120, 1120]} yRange={[0, 1120]} />;
  return <section className="evidence-layout">
    <h3>{t("Secondary property and petrophysical prior", "Propiedad secundaria y prior petrofísico")}</h3>
    <div className="two-plots">
      {run.secondary_truth && map(run.secondary_truth, t("Synthetic susceptibility target", "Objetivo sintético de susceptibilidad"), "SI", range)}
      {map(secondary, t("Final recovered susceptibility", "Susceptibilidad final recuperada"), "SI", range)}
    </div>
    {method.cross_gradient && map(method.cross_gradient, t("Structural disagreement", "Desacuerdo estructural"), t("exported cross-gradient magnitude", "magnitud exportada del gradiente cruzado"))}
    {classes > 0 && <>
      <label className="select-control"><span>{t("Petrophysical component", "Componente petrofísico")}</span><select className="select" value={chosen} onChange={e => setComponent(+e.target.value)}>{Array.from({ length: classes }, (_, i) => <option key={i} value={i}>{t("Component", "Componente")} {i + 1}</option>)}</select></label>
      {membership ? map(membership, t("Mixture responsibility at the final model", "Responsabilidad de mezcla en el modelo final"), "1", [0, 1]) : <p role="alert">{t("Invalid membership array; no lithology probabilities are inferred.", "Matriz de pertenencia inválida; no se infieren probabilidades litológicas.")}</p>}
      <p className="plot-note">{t("Responsibilities express compatibility of recovered density and susceptibility with the fitted mixture. They are not verified rock labels or posterior probabilities of the true geology.", "Las responsabilidades expresan compatibilidad de densidad y susceptibilidad recuperadas con la mezcla ajustada. No son etiquetas de roca verificadas ni probabilidades posteriores de la geología real.")}</p>
    </>}
    {method.petrophysical_prior && <>
      <p className="plot-note">{t("Independent prior source: ", "Fuente independiente del prior: ")}{method.petrophysical_prior.source}</p>
      <div className="table-scroll"><table className="cmp-table"><caption>{t("Fitted petrophysical mixture", "Mezcla petrofísica ajustada")}</caption><thead><tr><th>{t("Component", "Componente")}</th><th>{t("Density mean · g/cm³", "Densidad media · g/cm³")}</th><th>{t("Susceptibility mean · SI", "Susceptibilidad media · SI")}</th><th>{t("Mixture weight", "Peso de mezcla")}</th></tr></thead><tbody>{method.petrophysical_prior.means.map((m, i) => <tr key={i}><td>{i + 1}</td><td>{format(m[0])}</td><td>{format(m[1])}</td><td>{format(method.petrophysical_prior!.weights[i])}</td></tr>)}</tbody></table></div>
    </>}
  </section>;
}
