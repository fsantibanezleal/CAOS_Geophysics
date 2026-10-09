import { useId, useState } from "react";
import { Callout, Equation, Refs, useShellLang } from "@fasl-work/caos-app-shell";
import { jointChapters } from "../data/m11-scientific-course";

/** MAIN owns mounting and the single root citation provider. No solve or bake. */
export function M11ScientificCourse() {
  const language = useShellLang() === "es" ? 1 : 0, id = useId();
  const [selected, setSelected] = useState(0), [revealed, setRevealed] = useState(false);
  const chapter = jointChapters[selected];
  const t = (en: string, es: string) => language === 1 ? es : en;
  return <section className="method-article" data-m11-course aria-labelledby={id+"-title"}>
    <h2 id={id+"-title"}>{t("Supplied gravity–magnetic structural inversion", "Inversión estructural gravedad–magnetismo suministrada")}</h2>
    <p className="measure">{t("Scientific quantities, real physical operators, independent baselines, marginal errors and constrained stopping. This course describes the supplied-survey local methodology; it is separate from the cached synthetic joint replay. No interaction fits data, reads originals or creates a processing job.", "Magnitudes científicas, operadores físicos reales, bases independientes, errores marginales y parada restringida. Este curso describe metodología local para levantamientos suministrados; es independiente del replay sintético conjunto. No ajusta datos, lee originales ni crea una tarea.")}</p>
    <label htmlFor={id+"-chapter"}>{t("Scientific question", "Pregunta científica")}</label>
    <select className="select" id={id+"-chapter"} value={selected} onChange={e => { setSelected(Number(e.target.value)); setRevealed(false); }}>
      {jointChapters.map((item, index) => <option key={item.id} value={index}>{index+1}. {item.title[language]}</option>)}
    </select>
    <article key={chapter.id} data-m11-chapter={chapter.id}>
      <h3>{chapter.title[language]}</h3>
      {chapter.paragraphs.map((text, index) => <p key={index}>{text[language]}</p>)}
      <Equation tex={chapter.tex} caption={chapter.caption[language]} />
      <h3>{t("Predict and explain", "Prediga y explique")}</h3><p>{chapter.question[language]}</p>
      <button className="btn" type="button" aria-expanded={revealed} aria-controls={id+"-answer"} onClick={() => setRevealed(value => !value)}>
        {revealed ? t("Hide reasoning", "Ocultar razonamiento") : t("Reveal reasoning", "Revelar razonamiento")}
      </button>
      {revealed && <p id={id+"-answer"} role="status">{chapter.answer[language]}</p>}
      <Callout variant="honest">{chapter.limitation[language]}</Callout>
      <Refs ids={chapter.refs} label={t("Inspected primary sources", "Fuentes primarias inspeccionadas")} />
    </article>
  </section>;
}
