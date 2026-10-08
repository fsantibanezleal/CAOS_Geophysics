import { useState } from "react";
import { Callout, Equation, useShellLang } from "@fasl-work/caos-app-shell";
import { magneticLessons } from "../data/magnetic-survey-course";
import type { MagneticView } from "../api/magnetic-result";

/** Additive source-linked course. Parent supplies an already verified replay. */
export function MagneticSurveyCourse({value}:{value:MagneticView}) {
  const i=useShellLang()==="es"?1:0, [chapter,setChapter]=useState(0), lesson=magneticLessons[chapter];
  const outer=value.rows.filter(r=>r.role==="outer" && r.usable && r.residual_nT!==null), residual=outer.flatMap(r=>r.residual_nT!);
  const rms=residual.length?Math.sqrt(residual.reduce((s,x)=>s+x*x,0)/residual.length):null;
  return <section className="magnetic-course method-article" data-generation={value.binding.generation_sha256} data-lesson={lesson.id}>
    <h1>{i?"M04 · Curso de inversión de levantamientos magnéticos":"M04 · Magnetic survey inversion course"}</h1>
    <p>{i?"Método y reproducción local verificada; no cálculo en navegador, admisión de campo ni montaje API autenticado.":"Method and verified local replay; not browser computation, field admission or authenticated API mounting."}</p>
    <label>{i?"Capítulo":"Chapter"} <select value={chapter} onChange={e=>setChapter(Number(e.target.value))}>{magneticLessons.map((l,k)=><option key={l.id} value={k}>{k+1}. {l.label[i]}</option>)}</select></label>
    <article><h2>{lesson.title[i]}</h2><p>{lesson.body[i]}</p><Equation tex={lesson.equation} caption={lesson.symbols[i]}/>
      <h3>{i?"Implementación real":"Actual implementation"}</h3><code>{lesson.code}</code>
      <Callout variant="honest" title={i?"Supuestos y límites":"Assumptions and limits"}>{lesson.limit[i]}</Callout>
      <h3>{i?"Referencias primarias":"Primary references"}</h3><ul>{lesson.references.map(r=><li key={r.url}><a href={r.url} target="_blank" rel="noreferrer">{r.title}</a></li>)}</ul>
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
