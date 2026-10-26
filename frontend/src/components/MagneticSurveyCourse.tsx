import { useState } from "react";
import { Callout, Cite, Equation, Figure, Refs, useShellLang } from "@fasl-work/caos-app-shell";
import { magneticLessons } from "../data/magnetic-survey-course";
import { magneticDerivations, type MagneticDerivation } from "../data/magnetic-course-derivations";
import type { MagneticView } from "../api/magnetic-result";

/** Additive source-linked course. Parent supplies an already verified replay. */
export function MagneticSurveyCourse({value}:{value:MagneticView}) {
  const i=useShellLang()==="es"?1:0, [chapter,setChapter]=useState(0), lesson=magneticLessons[chapter];
  const derivation=magneticDerivations[lesson.id];
  const outer=value.rows.filter(r=>r.role==="outer" && r.usable && r.residual_nT!==null), residual=outer.flatMap(r=>r.residual_nT!);
  const rms=residual.length?Math.sqrt(residual.reduce((s,x)=>s+x*x,0)/residual.length):null;
  return <section className="magnetic-course method-article" data-generation={value.binding.generation_sha256} data-lesson={lesson.id}>
    <h1>{i?"Curso de inversión de levantamientos magnéticos":"Magnetic survey inversion course"}</h1>
    <p>{i?"Método y reproducción local verificada; no cálculo en navegador, admisión de campo ni montaje API autenticado.":"Method and verified local replay; not browser computation, field admission or authenticated API mounting."}</p>
    <label>{i?"Capítulo":"Chapter"} <select value={chapter} onChange={e=>setChapter(Number(e.target.value))}>{magneticLessons.map((l,k)=><option key={l.id} value={k}>{k+1}. {l.label[i]}</option>)}</select></label>
    <article><h2>{lesson.title[i]}</h2><p>{lesson.body[i]} {lesson.references.map(r=><Cite key={r.id} id={r.id}/>)}</p>
      {derivation.paragraphs.map((p,k)=><p key={k}>{p[i]}</p>)}
      <Equation tex={lesson.equation} caption={lesson.symbols[i]}/>
      <Equation tex={derivation.equation} caption={derivation.symbols[i]}/>
      <Figure caption={i?"Relaciones del método; esquema conceptual, no datos ni resultado ajustado.":"Method relationships; conceptual schematic, not data or a fitted result."}>
        <MagneticMethodDiagram value={derivation} language={i}/>
      </Figure>
      <h3>{i?"Frontera de implementación":"Implementation boundary"}</h3><p>{derivation.implementation[i]}</p>
      <Callout variant="honest" title={i?"Supuestos y límites":"Assumptions and limits"}>{lesson.limit[i]}</Callout>
      <h3>{i?"Ejercicio razonado":"Worked question"}</h3><p>{derivation.exercise[i]}</p><p>{derivation.answer[i]}</p>
      <Refs ids={lesson.references.map(r=>r.id)} label={i?"Referencias primarias":"Primary references"}/>
    </article>
    <aside><h3>{i?"Lectura del resultado realmente seleccionado":"Read the actual selected result"}</h3>
      <p>{i?"Estas cifras se calculan de la generación suministrada y verificada, no de un modelo de demostración independiente. Un control nulo no demuestra recuperación no trivial.":"These numbers come from the supplied verified generation, not an independent demonstration model. A null control does not demonstrate nontrivial recovery."}</p>
      <dl><dt>{i?"Fuente / cantidad":"Source / quantity"}</dt><dd>{value.binding.source_id} / {value.quantity}</dd>
        <dt>{i?"Filas originales / celdas activas":"Original rows / active cells"}</dt><dd>{value.rows.length} / {value.model.chi_si.data.length}</dd>
        <dt>{i?"Candidato congelado":"Frozen candidate"}</dt><dd>{value.selected}</dd>
        <dt>{i?"Componentes externos / RMS crudo":"Outer components / raw RMS"}</dt><dd>{residual.length} / {rms===null?(i?"No disponible":"Unavailable"):rms+" nT"}</dd>
        <dt>{i?"Generación SHA256":"Generation SHA256"}</dt><dd style={{overflowWrap:"anywhere"}}>{value.binding.generation_sha256}</dd></dl>
    </aside>
  </section>;
}

function MagneticMethodDiagram({value,language}:{value:MagneticDerivation;language:0|1}) {
  return <svg className="fig-svg" viewBox="0 0 500 330" role="img" aria-label={value.steps.map(s=>s[language]).join(" → ")} data-magnetic-method-diagram>
    {value.steps.map((step,k)=><g key={k}>
      <rect x="20" y={12+k*110} width="460" height="70" rx="8" fill="none" stroke="currentColor"/>
      <text x="250" y={53+k*110} textAnchor="middle" fill="currentColor" fontSize="18">{step[language]}</text>
      {k<2&&<path d={`M250 ${82+k*110}v36m-7-8 7 8 7-8`} fill="none" stroke="var(--color-accent)" strokeWidth="2"/>}
    </g>)}
  </svg>;
}
