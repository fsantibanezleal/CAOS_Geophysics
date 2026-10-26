import { Fragment, useEffect, useId, useState, type ReactNode } from "react";
import { Callout, Cite, Equation, InlineMath, Refs, useShellLang } from "@fasl-work/caos-app-shell";
import { M01_COURSE_CITATIONS, lessons, lessonBody, loadCourseRecord, scenarioIds, type VerifiedCourseRecord } from "../data/m01-scientific-course";
import { M01CourseDiagram, type MapField } from "./M01CourseDiagram";
import { M01CourseExercise } from "./M01CourseExercise";

/** Small trusted-course markup view, not an untrusted Markdown/HTML importer.
 * React escapes prose/code; links are only frozen HTTPS citations/repo paths.
 * All actual scientific arrays enter through the separate bound loader.
 */
function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const tokens = /(\$[^$\n]+\$|\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let at = 0, match: RegExpExecArray|null;
  while ((match = tokens.exec(text))) {
    parts.push(text.slice(at, match.index));
    const token = match[0], key = match.index;
    if (token.startsWith("$")) parts.push(<InlineMath key={key} tex={token.slice(1, -1)} />);
    else if (token.startsWith("**")) parts.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    else if (token.startsWith("`")) parts.push(<code key={key}>{token.slice(1, -1)}</code>);
    else {
      const link = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token)!;
      const base = "https://github.com/fsantibanezleal/CAOS_Geophysics/blob/96b583eefad4e8c8c4281800df219432c3b5a45e/docs/methods/gravity-processing/scientific-course/";
      const url = new URL(link[2], base);
      const alias = url.href === "https://geored2.sgc.gov.co/Articulos%20y%20documentacion/Li_G_Tut.pdf" ? "m01li"
        : url.href === "https://nsojournals.onlinelibrary.wiley.com/doi/full/10.1111/ecog.02881" ? "m01roberts" : null;
      const reference = M01_COURSE_CITATIONS.find(c => c.id === alias || c.url === url.href || (c.doi && url.href === "https://doi.org/" + c.doi));
      parts.push(reference ? <Cite key={key} id={reference.id} />
        : url.protocol === "https:" ? <a key={key} href={url.href} target="_blank" rel="noreferrer">{link[1]}</a> : link[1]);
    }
    at = match.index + token.length;
  }
  parts.push(text.slice(at));
  return parts;
}
export function PhysicsText({ text, es }: { text: string; es: boolean }) {
  const chunks = text.split(/(```[\s\S]*?```|\\\[[\s\S]*?\\\])/);
  return <>{chunks.map((chunk, index) => {
    if (chunk.startsWith("```")) return <pre className="codeblock" key={index}><code>{chunk.replace(/^```[^\n]*\n/, "").replace(/```$/, "").trimEnd()}</code></pre>;
    if (chunk.startsWith("\\[")) return <Equation key={index} tex={chunk.slice(2, -2).trim()}
      caption={es ? "Relación física: símbolos y unidades definidos en los párrafos contiguos; mGal para gravedad, m para alturas, kg/m³ para densidad, DE y covarianza explícitas. No es ejecución de una tarea." : "Physical relation: symbols and units are defined in the adjacent paragraphs; gravity in mGal, heights in m, density in kg/m³, explicit SD/covariance. Not a job execution."} />;
    return <Fragment key={index}>{chunk.trim().split(/\n\s*\n/).filter(Boolean).map((block, j) => {
      if (/^## /.test(block)) return <h2 key={j}>{inline(block.replace(/^## /, ""))}</h2>;
      if (/^### /.test(block)) return <h3 key={j}>{inline(block.replace(/^### /, ""))}</h3>;
      if (/^\d+\.\s/.test(block)) return <ol key={j}>{block.split("\n").map((line, k) => <li key={k}>{inline(line.replace(/^\d+\.\s/, ""))}</li>)}</ol>;
      return <p key={j}>{inline(block.replace(/\n/g, " "))}</p>;
    })}</Fragment>;
  })}</>;
}

function RecordedControl() {
  const es = useShellLang() === "es", id = useId();
  const [scenario, setScenario] = useState<typeof scenarioIds[number]>("prism-case-0");
  const [record, setRecord] = useState<VerifiedCourseRecord|null>(null), [state, setState] = useState("loading");
  const [height, setHeight] = useState(0), [field, setField] = useState<MapField>("field");
  const [coverage, setCoverage] = useState(true), [alternative, setAlternative] = useState(0);
  const t = (en: string, sp: string) => es ? sp : en;
  const format = (v: number|null|undefined) => v == null ? "null" : v.toLocaleString(es ? "es-CL" : "en-US", { maximumSignificantDigits: 8 });
  useEffect(() => {
    const controller = new AbortController();
    setRecord(null); setState("loading"); setHeight(0); setAlternative(0);
    loadCourseRecord(scenario, controller.signal).then(value => {
      if (!controller.signal.aborted) { setRecord(value); setState("ready"); }
    }).catch(() => { if (!controller.signal.aborted) { setRecord(null); setState("rejected"); } });
    return () => controller.abort();
  }, [scenario]);
  const result = record?.result;
  return <section data-m01-recorded>
    <h2>{t("Recorded analytical control, not a live job", "Control analítico registrado, no tarea activa")}</h2>
    <p>{t("Three actually executed, source-pinned irregular/rotated/translated prism controls:196 retained stations, four declared masks and authored0.02-mGal SD. Buried Newton volume physics generated the control, not the fitted scalar1/r kernel. Known density is control input, not recovered output. The browser verifies original bytes and declared bindings, not Python scientific replay or provider authenticity.", "Tres controles de prismas realmente ejecutados, fijados a código, irregulares/rotados/trasladados:196 estaciones conservadas, cuatro máscaras y DE creada0,02mGal. Física newtoniana volumétrica produjo el control, no el núcleo ajustado1/r. Densidad conocida es entrada del control, no salida recuperada. El navegador verifica bytes y vínculos declarados, no replay científico Python ni autenticidad de proveedor.")} <Cite id="m01equivalent" paren /></p>
    <label htmlFor={id+"-scenario"}>{t("Actual record", "Registro real")}</label>
    <select className="select" id={id+"-scenario"} value={scenario}
      onChange={e => { setRecord(null); setScenario(e.target.value as typeof scenario); }}>
      {scenarioIds.map((value, i) => <option key={value} value={value}>{t("Prism survey", "Levantamiento de prismas")} {i+1}</option>)}
    </select>
    {state === "loading" && <p role="status">{t("Loading and verifying this record only.", "Cargando y verificando solo este registro.")}</p>}
    {state === "rejected" && <p role="alert">{t("Record unavailable or integrity mismatch. No metrics or map admitted.", "Registro no disponible o integridad discordante. No se admiten métricas ni mapa.")}</p>}
    {record && result && <>
      <p data-testid="m01-selected-model">{t("Selected mathematical depth / damping / absolute ellipsoidal height", "Profundidad matemática / penalización / altura elipsoidal absoluta seleccionadas")}: {format(result.selection.depth_m)} m / {format(result.selection.damping)} mGal⁻² / {format(result.selection.height_m)} m. {result.selection.status}</p>
      <div style={{ overflowX: "auto" }}><table className="cmp-table">
        <caption>{t("Covered rows only; unsupported rows remain reported", "Solo filas con soporte; se informan las no soportadas")}</caption>
        <thead><tr>{[t("Partition", "Partición"), "RMSE (mGal)", t("Normalized RMSE", "RMSE normalizado"), t("Covered", "Con soporte"), t("Unsupported", "Sin soporte")].map(x => <th scope="col" key={x}>{x}</th>)}</tr></thead>
        <tbody>{(["train", "holdout"] as const).map(key => <tr key={key}><th scope="row">{key === "train" ? t("Training", "Entrenamiento") : t("Outer holdout", "Reserva externa")}</th>
          <td>{format(result.evaluation[key].rmse_mgal)}</td><td>{format(result.evaluation[key].normalized_rmse)}</td>
          <td>{result.evaluation[key].covered_count}</td><td>{result.evaluation[key].unsupported_count}</td></tr>)}</tbody>
      </table></div>
      <div className="def-grid">
        <label htmlFor={id+"-height"}>{t("Recorded absolute height (m), display only", "Altura absoluta registrada (m), solo vista")}
          <select className="select" id={id+"-height"} value={height} disabled={field === "residual"} onChange={e => setHeight(Number(e.target.value))}>
            {result.grids.map((g, i) => <option value={i} key={g.height_m}>{format(g.height_m)} m · {g.height_precision_passed ? t("precision passed", "precisión cumplida") : t("precision failed", "precisión fallida")}</option>)}
          </select></label>
        <label htmlFor={id+"-field"}>{t("Quantity", "Magnitud")}
          <select className="select" id={id+"-field"} value={field} onChange={e => setField(e.target.value as MapField)}>
            <option value="field">{t("Continued field (mGal)", "Campo continuado (mGal)")}</option>
            <option value="sigma">{t("Conditional noise SD (mGal)", "DE condicional de ruido (mGal)")}</option>
            <option value="residual">{t("Prediction − observation (mGal), receiver heights", "Predicción − observación (mGal), alturas originales")}</option>
          </select></label>
        <label><input type="checkbox" checked={coverage} onChange={e => setCoverage(e.target.checked)} />{t("Coverage outlines and station partitions", "Contornos de soporte y particiones")}</label>
      </div>
      <M01CourseDiagram key={scenario+field} result={result} heightIndex={height} field={field} coverage={coverage} />
      <p>{t("Grid noise ceiling and covered nodes", "Cota de ruido de malla y nodos con soporte")}: {format(result.grids[height].max_conditional_sigma_mgal)} mGal · {result.grids[height].covered.filter(Boolean).length}/{result.grids[height].covered.length}.
        {" "}{t("Adjacent-easting difference RMS, not a gradient or resolution", "RMS de diferencias vecinas al este, no gradiente ni resolución")}: {format(result.grids[height].adjacent_easting_difference_rms_mgal)} mGal.</p>
      <label htmlFor={id+"-layer"}>{t("Training-only layer comparison, no model switch", "Comparación de capas solo de entrenamiento, sin cambiar modelo")}</label>
      <select className="select" id={id+"-layer"} value={alternative} onChange={e => setAlternative(Number(e.target.value))}>
        {result.nonuniqueness.training_only_alternatives.map((a, i) => <option key={i} value={i}>{a.depth_m} m · λ={a.damping} mGal⁻² · {a.status === "passed" ? t("passed", "cumplido") : t("failed", "fallido")}</option>)}
      </select>
      {(() => {
        const a = result.nonuniqueness.training_only_alternatives[alternative];
        return a.status === "passed" ? <p>{t("Training RMSE / coefficient norm / damped condition", "RMSE de entrenamiento / norma de coeficientes / condición amortiguada")}: {format(a.training_rmse_mgal)} mGal / {format(a.coefficient_l2_mgal_m)} mGal m / {format(a.damped_condition)}.</p>
          : <p>{t("Recorded failed candidate", "Candidato fallido registrado")}: {a.reason}</p>;
      })()}
      <details><summary>{t("All inner candidate outcomes and frozen parameters", "Resultados de candidatos internos y parámetros fijos")}</summary>
        <ul>{result.selection.candidates.map((a, i) => <li key={i}>{String(a.depth_m)} m · λ={String(a.damping)} mGal⁻² · {String(a.status)} · {t("inner normalized RMSE", "RMSE interno normalizado")} {typeof a.cv_normalized_rmse === "number" ? format(a.cv_normalized_rmse) : "null"}{a.reason ? " · " + String(a.reason) : ""}</li>)}</ul>
        <ul>{Object.entries(result.config).map(([k,v]) => <li key={k}><code>{k}</code>: {Array.isArray(v) ? v.join(", ") : String(v)}</li>)}</ul>
      </details>
      <p style={{ overflowWrap: "anywhere" }}>{t("Exact request / result identities", "Identidades exactas de petición / resultado")}: <code>{record.index.request_sha256}</code> / <code>{record.index.result_sha256}</code>.</p>
      <p>{t("Recorded runtime, not authenticated origin", "Runtime registrado, no origen autenticado")}: {record.index.runtime.python_implementation} {record.index.runtime.python}; {Object.entries(record.index.runtime.engines).map(([k,v]) => k+" "+v).join(", ")}.
        {" "}{t("Original export UTC", "UTC de exportación original")}: {String(record.receipt.executed_utc)}.</p>
      <p>{t("Load measured in this view: bytes / elapsed / parsed objects", "Carga medida en esta vista: bytes / tiempo / objetos analizados")}: {record.load.fetched_bytes} / {format(record.load.elapsed_ms)} ms / {record.load.parsed_objects}.
        {" "}{t("No all-scenario preload or persistent record cache. These are acquisition/parse counters, not a browser peak-memory guarantee.", "Sin precarga de todos los escenarios ni caché persistente. Son contadores de adquisición/análisis, no garantía de pico de memoria del navegador.")}</p>
      <Callout variant="honest">{t("Conditional noise propagation excludes geometry, parameter selection, bias and geology. Coverage is not resolution; coefficients are not density. Original corrections are not reapplied. Field datum/errors/lineage eligibility remains unresolved; no field, host or full-M01 acceptance.", "La propagación condicional excluye geometría, selección, sesgo y geología. Soporte no es resolución; coeficientes no son densidad. No se reaplican correcciones originales. Elegibilidad de datum/errores/historia de campo sigue sin resolver; no hay aceptación de campo, host ni M01 completo.")}</Callout>
    </>}
    <Refs ids={["m01equivalent", "m01verde", "m01blocks", "m01gum"]} label={t("References", "Referencias")} />
  </section>;
}

/** MAIN mounts this component and extends the SINGLE root citation provider.
 * No route/root/registry/copy-data side effect and no physical upload/job.
 */
export function M01ScientificCourse() {
  const es = useShellLang() === "es", language = es ? 1 : 0, id = useId();
  const [section, setSection] = useState("1"), [revealed, setRevealed] = useState(false);
  const lesson = lessons[Number(section) - 1];
  return <div className="method-article" data-m01-course>
    <p className="measure">{es ? "Referencia de gravedad, contribuciones de masa, errores dependientes, capa equivalente, validación espacial y continuación sin fuentes. Magnitudes y unidades antes del cálculo. Cuatro modelos escalares explicativos y tres controles analíticos realmente registrados son vías distintas; ninguna crea una tarea física ni resuelve metadatos de campo ausentes." : "Gravity reference, mass contributions, dependent errors, equivalent layer, spatial validation and source-free continuation. Quantities and units precede calculation. Four explanatory scalar models and three actually recorded analytical controls are separate lanes; neither creates a physical job or resolves missing field metadata."} <InlineMath tex={String.raw`D=g_\downarrow-\gamma(\phi,h_r)`} /></p>
    <label htmlFor={id+"-section"}>{es ? "Pregunta científica o control registrado" : "Scientific question or recorded control"}</label>
    <select className="select" id={id+"-section"} value={section} onChange={e => { setSection(e.target.value); setRevealed(false); }}>
      <optgroup label={es ? "Preguntas científicas" : "Scientific questions"}>
        {lessons.map(l => <option value={l.id} key={l.id}>{l.id}. {l.title[language]}</option>)}
      </optgroup>
      <option value="records">{es ? "Controles analíticos registrados" : "Recorded analytical controls"}</option>
    </select>
    {section === "records" ? <RecordedControl /> : <article>
      <PhysicsText text={lessonBody(lesson, language)} es={es} />
      <M01CourseDiagram chapter={lesson.id} />
      <h3>{es ? "Prediga y explique" : "Predict and explain"}</h3><p>{lesson.question[language]}</p>
      <button className="btn" type="button" aria-expanded={revealed} aria-controls={id+"-answer"} onClick={() => setRevealed(v => !v)}>
        {revealed ? (es ? "Ocultar explicación" : "Hide explanation") : (es ? "Revelar explicación" : "Reveal explanation")}
      </button>
      {revealed && <p id={id+"-answer"} role="status">{lesson.answer[language]}</p>}
      {lesson.calculator && <M01CourseExercise key={lesson.calculator} exercise={lesson.calculator} />}
      <Callout variant="honest">{es ? "Los archivos del usuario necesitan referencias, errores, derechos e historia explícitos. No se adivinan elevación, covarianza o estado por nombres de columnas. Conservar padre entero/flotante e historia completos; algunos padres válidos no son reconstruibles por el transformador acotado. Una cota marginal no es DE independiente y una capa matemática no es densidad." : "User files need explicit references, errors, rights and history. Elevation, covariance or correction state are not guessed from columns. Preserve the complete integer/float parent and history; some valid parents cannot be reconstructed by the bounded transformer. A marginal bound is not independent SD and a mathematical layer is not density."}</Callout>
      <Refs ids={lesson.refs} label={es ? "Referencias" : "References"} />
    </article>}
  </div>;
}
