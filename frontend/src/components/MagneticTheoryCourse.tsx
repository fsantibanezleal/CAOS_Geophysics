import { useState } from "react";
import { Callout, Cite, Equation, Refs, useShellLang } from "@fasl-work/caos-app-shell";
import { magneticLessons } from "../data/magnetic-survey-course";
import { magneticDerivations } from "../data/magnetic-course-derivations";

/** Authored theory: deliberately independent of a fitted MagneticView. */
export function MagneticTheoryCourse({ implementation = false }: { implementation?: boolean }) {
  const i = useShellLang() === "es" ? 1 : 0;
  const [chapter, setChapter] = useState(0);
  const lesson = magneticLessons[chapter], derivation = magneticDerivations[lesson.id];
  return <section className="method-article" data-magnetic-theory data-lesson={lesson.id}>
    <h2>{i ? "Inversión de levantamientos magnéticos" : "Magnetic survey inversion"}</h2>
    <p>{i ? "Cantidades, formulación y algoritmos locales. Las preguntas razonadas son ejemplos didácticos, no resultados ajustados ni aceptación de campo. Este curso no ejecuta una inversión." : "Quantities, formulation and local algorithms. Worked questions are teaching examples, not fitted results or field acceptance. This course does not execute an inversion."}</p>
    <label>{i ? "Capítulo magnético" : "Magnetic chapter"} <select value={chapter} onChange={event => {
      const selected = Number(event.target.value);
      if (Number.isInteger(selected) && selected >= 0 && selected < magneticLessons.length) setChapter(selected);
    }}>{magneticLessons.map((item, index) => <option key={item.id} value={index}>{index + 1}. {item.label[i]}</option>)}</select></label>
    <article key={lesson.id}>
      <h3>{lesson.title[i]}</h3>
      <p>{lesson.body[i]} {lesson.references.map((reference, index) => <span key={reference.id}><Cite id={reference.id} />{index + 1 < lesson.references.length ? " · " : ""}</span>)}</p>
      <Equation tex={lesson.equation} caption={lesson.symbols[i]} />
      {derivation.paragraphs.map((text, index) => <p key={index}>{text[i]}</p>)}
      <Equation tex={derivation.equation} caption={derivation.symbols[i]} />
      <h3>{i ? "Algoritmo e implementación" : "Algorithm and implementation"}</h3>
      <p>{derivation.implementation[i]}</p>
      {implementation && <p>{i ? "Ubicación del algoritmo local" : "Local algorithm location"}: <code>{lesson.code}</code></p>}
      <Callout variant="honest" title={i ? "Supuestos y límites" : "Assumptions and limits"}>{lesson.limit[i]}</Callout>
      <h3>{i ? "Pregunta razonada" : "Worked question"}</h3>
      <p>{derivation.exercise[i]}</p>
      <details><summary>{i ? "Explicación" : "Explanation"}</summary><p>{derivation.answer[i]}</p></details>
      <Refs ids={lesson.references.map(reference => reference.id)} label={i ? "Referencias primarias" : "Primary references"} />
    </article>
  </section>;
}
