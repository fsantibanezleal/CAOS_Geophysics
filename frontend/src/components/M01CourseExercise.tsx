import { useId, useState } from "react";
import { Callout, useShellLang } from "@fasl-work/caos-app-shell";
import { calculateExplanation, explanationFields, explanationAssumptions, type ExplanationId } from "../data/m01-scientific-course";

const resultLabels: Record<string, readonly [string,string]> = {
  surface_reference_mgal: ["Surface reference (mGal)", "Referencia superficial (mGal)"],
  plate_mgal: ["Plate attraction (mGal)", "Atracción de placa (mGal)"],
  subtractive_mgal: ["Subtractive contribution (mGal)", "Contribución sustractiva (mGal)"],
  linear_sd_mgal: ["Linear SD (mGal)", "DE lineal (mGal)"],
  marginal_sd_upper_bound_mgal: ["Marginal SD upper bound (mGal)", "Cota superior de DE marginal (mGal)"],
  attenuation: ["Attenuation (dimensionless)", "Atenuación (adimensional)"],
  continued_amplitude_mgal: ["Continued amplitude (mGal)", "Amplitud continuada (mGal)"],
};
export function M01CourseExercise({ exercise }: { exercise: ExplanationId }) {
  const es = useShellLang() === "es", i = es ? 1 : 0, id = useId();
  const fields = explanationFields[exercise];
  const defaults = () => Object.fromEntries(fields.map(f => [f.key, String(f.initial)]));
  const [values, setValues] = useState(defaults), [output, setOutput] = useState<Record<string,number>|null>(null);
  const [invalid, setInvalid] = useState(false);
  function apply() {
    try {
      if (fields.some(f => values[f.key].trim() === "")) throw new Error("Empty explanatory input.");
      const result = calculateExplanation(exercise, Object.fromEntries(fields.map(f => [f.key, Number(values[f.key])])));
      setOutput(result); setInvalid(false);
    } catch { setOutput(null); setInvalid(true); }
  }
  return <section aria-labelledby={id+"-heading"} data-m01-explanation={exercise}>
    <h3 id={id+"-heading"}>{es ? "Cálculo explicativo" : "Explanatory calculation"} · {exercise}</h3>
    <p>{explanationAssumptions[exercise][i]}</p>
    <div className="def-grid">{fields.map(f => <label key={f.key} htmlFor={id+"-"+f.key}>
      {f.label[i]} [{f.min}, {f.max}]
      <input className="select" id={id+"-"+f.key} type="number" step="any" min={f.min} max={f.max}
        value={values[f.key]} onChange={e => { setValues(v => ({ ...v, [f.key]: e.target.value })); setOutput(null); setInvalid(false); }} />
    </label>)}</div>
    <button className="btn" type="button" onClick={apply}>{es ? "Aplicar" : "Apply"}</button>{" "}
    <button className="btn" type="button" onClick={() => { setValues(defaults()); setOutput(null); setInvalid(false); }}>{es ? "Restablecer" : "Reset"}</button>
    {invalid && <p role="alert">{es ? "Cada entrada debe ser finita, no vacía y estar en su intervalo declarado." : "Each input must be finite, nonempty and within its declared range."}</p>}
    {output && <div role="status" aria-live="polite" data-testid="m01-explanatory-output">
      <dl>{Object.entries(output).map(([key, value]) => <div key={key}><dt>{resultLabels[key][i]}</dt><dd>{value.toLocaleString(es ? "es-CL" : "en-US", { maximumSignificantDigits: 10 })}</dd></div>)}</dl>
    </div>}
    <Callout variant="honest">{es ? "Ejemplos numéricos elegidos, no parámetros de campo recomendados. No produce estación corregida, tarea, recibo ni aprobación de fuente." : "Chosen numerical examples, not recommended field parameters. No corrected station, job, receipt or source approval is produced."}</Callout>
  </section>;
}
