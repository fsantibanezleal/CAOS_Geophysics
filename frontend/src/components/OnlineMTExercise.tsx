import { useId, useState } from "react";
import { Cite, useShellLang } from "@fasl-work/caos-app-shell";
import type { Bilingual, MTMethod } from "../data/online-mt-course";
import worked from "../data/online-mt-worked.json";
import { Plot } from "./ScientificPlots";
import styles from "./OnlineMTCourse.module.css";

export const mtQuestions: { id: string; method: MTMethod; prompt: Bilingual; answer: Bilingual }[] = [
  { id: "variance", method: "m05", prompt: ["If complex VAR=8 in SI units, what SD belongs to each real/imaginary part?", "Si VAR compleja=8 en unidades SI, ¿qué DE corresponde a cada parte real/imaginaria?"], answer: ["2 Ω: sqrt(8/2), not sqrt(8). VAR has Ω² units. Native inputs also need the μ₀×1000 unit multiplier on sigma. The inverse weights impedance components, not apparent-resistivity errors.", "2 Ω: sqrt(8/2), no sqrt(8). VAR está en Ω². Entradas nativas también necesitan multiplicador μ₀×1000 sobre sigma. La inversión pondera componentes de impedancia, no errores de resistividad aparente."] },
  { id: "cl061", method: "m05", prompt: ["Can cl061 run M06 if xy looks smooth and offending diagonal frequencies are omitted?", "¿Puede cl061 ejecutar M06 si xy parece suave y se omiten frecuencias diagonales incómodas?"], answer: ["No. All three all-original-frequency scores exceed3. Preserve QC-only, methods={}, truth=null. A subsequent training mask cannot change the complete-source eligibility verdict; no true layer model is available from this record.", "No. Los tres scores con todas las frecuencias originales superan3. Conservar sólo QC, methods={}, truth=null. Una máscara posterior de entrenamiento no cambia elegibilidad de fuente completa; el registro no aporta modelo verdadero de capas."] },
  { id: "phase", method: "m06", prompt: ["What phase should a positive-time homogeneous halfspace have, and why?", "¿Qué fase tiene un semiespacio homogéneo con signo temporal positivo y por qué?"], answer: ["45° because Z=(1+i)sqrt(πfμ₀rho) has equal positive real/imaginary parts. Apparent resistivity is rho at every frequency. Negative-time source values must be conjugated before comparison with this oracle.", "45° porque Z=(1+i)sqrt(πfμ₀rho) tiene partes real/imaginaria positivas iguales. Resistividad aparente es rho en toda frecuencia. Valores fuente de tiempo negativo se conjugan antes de comparar con este oráculo."] },
  { id: "holdout", method: "m06", prompt: ["The280-m control has smaller held-out WRMS than350m. Does it establish the true cover thickness?", "El control280m tiene menor WRMS reservado que350m. ¿Establece el espesor verdadero?"], answer: ["No. This synthetic target is350m, disclosed only for evaluation. Four withheld frequencies in one noisy sounding do not identify geometry or validate a new station. Do not tune h or select starts on holdout; retain the wrong-h result as a negative control.", "No. El objetivo sintético es350m, revelado sólo para evaluar. Cuatro frecuencias reservadas de un sondeo ruidoso no identifican geometría ni validan estación nueva. No ajustar h ni elegir inicios por holdout; conservar h incorrecto como control negativo."] },
  { id: "interval", method: "m06", prompt: ["Which physical assumptions does a narrow20–40-member bootstrap interval leave untested?", "¿Qué supuestos físicos quedan sin probar con un intervalo bootstrap estrecho de20–40 miembros?"], answer: ["Unknown h, alternative structure/dimensionality, correlated errors, static shift and forward-model discrepancy. It measures pointwise repeatability of this fixed estimator under independent Gaussian real/imaginary errors, not geological posterior probability or calibrated field coverage.", "h desconocido, estructura/dimensionalidad alternativa, errores correlacionados, desplazamiento estático y discrepancia del modelo directo. Mide repetibilidad puntual del estimador fijo bajo errores gaussianos independientes, no probabilidad posterior geológica ni cobertura de campo calibrada."] },
];
const caseLabels: Record<string, Bilingual> = {
  fixed: ["Fixed h350m", "h fijo350m"], thin: ["Wrong h280m", "h incorrecto280m"],
  thick: ["Wrong h420m", "h incorrecto420m"], halfspace: ["Halfspace baseline", "Referencia semiespacio"], beta: ["Beta0.01, h350m", "Beta0,01, h350m"],
};

export function OnlineMTExercise({ method }: { method: MTMethod }) {
  const id = useId(), es = useShellLang() === "es", i = es ? 1 : 0;
  const [caseId, setCaseId] = useState("fixed"), [questionId, setQuestionId] = useState("");
  const [revealed, setRevealed] = useState(false);
  const questions = mtQuestions.filter(q => q.method === method);
  const question = questions.find(q => q.id === questionId) ?? questions[0];
  const result = worked.cases.find(c => c.id === caseId)!;
  const fmt = (n: number) => n.toLocaleString(es ? "es-CL" : "en-US", { maximumFractionDigits: 6 });
  return <section className={styles.exercise} data-mt-exercise={method} aria-labelledby={`${id}-heading`}>
    <h3 id={`${id}-heading`}>{es ? "Ejercicio: prediga, compare y explique" : "Exercise: predict, compare and explain"}</h3>
    {method === "m06" && <>
      <p>{es ? "Replay de cálculo real sintético: 24 frecuencias, 20 entrenamiento y 4 reservadas; fuente8987bytes, semilla ruido67201, marco27°. Objetivo120/12Ωm y350m sólo para evaluación. Sin solver navegador ni envío API." : "Actual synthetic solve replay:24 frequencies,20 training and4 withheld; source8987bytes, noise seed67201, frame27°. Target120/12Ωm and350m is evaluation-only. No browser solver or API submission."} <Cite id="mtcode" paren /></p>
      <label htmlFor={`${id}-case`}>{es ? "Control resuelto" : "Worked control"}</label>
      <select className="select" id={`${id}-case`} value={caseId} onChange={event => setCaseId(event.target.value)}>{worked.cases.map(c => <option value={c.id} key={c.id}>{caseLabels[c.id][i]}</option>)}</select>
      <output data-testid="mt-worked-model" aria-live="polite">{es ? "Modelo" : "Model"}: [{result.model_ohm_m.map(fmt).join(", ")}] Ω m; h=[{result.thickness_m.map(fmt).join(", ")}] m; β={fmt(result.beta)}</output>
      <div className={styles.table}><table><caption>{es ? "Mismo d, sigma y máscara; métricas recalculadas" : "Same d, sigma and mask; recomputed metrics"}</caption><tbody>
        <tr><th scope="row">{es ? "WRMS entrenamiento" : "Training WRMS"}</th><td>{fmt(result.training_wrms)}</td></tr>
        <tr><th scope="row">{es ? "WRMS reservado" : "Held-out WRMS"}</th><td>{fmt(result.heldout_wrms)}</td></tr>
        <tr><th scope="row">J</th><td>{fmt(result.training_objective)}</td></tr>
        <tr><th scope="row">{es ? "Datos / prior" : "Data / prior"}</th><td>{fmt(result.data_objective)} / {fmt(result.prior_objective)}</td></tr>
        <tr><th scope="row">{es ? "Inicio elegido (Ω m)" : "Selected start (Ω m)"}</th><td>[{result.selected_start.map(fmt).join(", ")}]</td></tr>
      </tbody></table></div>
      <Plot title={es ? "Respuesta real de impedancia: observado y predicho" : "Real impedance response: observed and predicted"} x={worked.frequency_hz} xLabel={es ? "Frecuencia (Hz)" : "Frequency (Hz)"} yLabel="Re Z (Ω)" logX
        series={[{ name: es ? "Observado sintético" : "Synthetic observed", values: worked.observed_real_ohm, points: true }, { name: es ? "Predicho" : "Predicted", values: result.predicted_real_ohm, dashed: true }]} />
      <p>{es ? "Procedencia del ejemplo" : "Example provenance"}: SHA-256 <code>{worked.source_sha256}</code>; NumPy{worked.environment.numpy}, SciPy{worked.environment.scipy}; {es ? "regla online revisada" : "reviewed online rule"} {worked.backend_reference}.</p>
    </>}
    <label htmlFor={`${id}-question`}>{es ? "Pregunta de control" : "Control question"}</label>
    <select className="select" id={`${id}-question`} value={question.id} onChange={event => { setQuestionId(event.target.value); setRevealed(false); }}>{questions.map((q, index) => <option key={q.id} value={q.id}>{es ? "Pregunta" : "Question"} {index + 1}</option>)}</select>
    <p data-testid="mt-question">{question.prompt[i]}</p>
    <button className="btn" type="button" onClick={() => setRevealed(v => !v)} aria-expanded={revealed} aria-controls={`${id}-answer`}>{revealed ? (es ? "Ocultar respuesta" : "Hide answer") : (es ? "Revelar explicación" : "Reveal explanation")}</button>
    {revealed && <p id={`${id}-answer`} data-testid="mt-answer" role="status">{question.answer[i]} <Cite id={question.id === "cl061" ? "clearlake" : "mtcode"} paren /></p>}
  </section>;
}
