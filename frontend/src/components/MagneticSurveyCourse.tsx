import { useState } from "react";
import { Callout, Cite, CitationsProvider, Equation, Figure, Refs, useShellLang } from "@fasl-work/caos-app-shell";
import { magneticLessons } from "../data/magnetic-survey-course";
import { magneticDerivations, type MagneticDerivation } from "../data/magnetic-course-derivations";
import { MAGNETIC_CITATIONS } from "../data/magnetic-course-citations";
import type { MagneticView } from "../api/magnetic-result";

/** Additive source-linked course. Parent supplies an already verified replay. */
export function MagneticSurveyCourse({value}:{value:MagneticView}) {
  const i=useShellLang()==="es"?1:0, [chapter,setChapter]=useState(0);
  const originalLesson=magneticLessons[chapter], originalDerivation=magneticDerivations[originalLesson.id];
  // Preserve canonical theory data; this result consumer explains scientific
  // reproduction, not the hosted owner's integration/activation backlog.
  const lesson=originalLesson.id!=="custody"?originalLesson:{...originalLesson,
    title:["Reproducible numerical generations", "Generaciones numéricas reproducibles"],
    body:["A reproducible result retains the original observations and the exact inducing field, covariance, physical mesh, prior and selected configuration. Array hashes, shapes, units and original row inventory must read back consistently before numerical exchange. A replay changes presentation, never the quantity or physical operands of an old fit. Changing those operands requires a new immutable request and a new inference. Byte identity establishes reproduction, not the accuracy of acquisition metadata or uniqueness of geological interpretation.","Un resultado reproducible conserva observaciones originales y campo inductor, covarianza, malla física, prior y configuración seleccionada exactos. Hashes, formas, unidades e inventario de filas se releen consistentemente antes del intercambio numérico. Reproducción cambia presentación, nunca cantidad ni operandos físicos de un ajuste previo. Cambiar operandos exige solicitud inmutable e inferencia nueva. Identidad de bytes acredita reproducción, no exactitud de metadatos ni interpretación geológica única."],
    symbols:["The selected binding identifies original bytes, physical configuration and numerical generation. Matching hashes do not establish datum, inducing field, remanence or geological truth.","El vínculo seleccionado identifica bytes originales, configuración física y generación numérica. Hashes iguales no prueban datum, campo inductor, remanencia ni verdad geológica."],
    limit:["Reproducible bytes cannot upgrade a failed fit or a null control into nontrivial recovery. Objective records are not intermediate susceptibility arrays; no missing model state is interpolated.","Bytes reproducibles no convierten fallo ni control nulo en recuperación no trivial. Registros de objetivo no son arrays intermedios de susceptibilidad; no se interpola un estado ausente."]};
  const derivation:MagneticDerivation=originalLesson.id!=="custody"?originalDerivation:{...originalDerivation,
    paragraphs:[originalDerivation.paragraphs[0],
      ["A numerical manifest closes one generation only when every declared array hash, shape, unit and frozen binding agrees with the retained original inventory. Export exchanges bounded declared numeric members, not an untracked substitute original. Readback therefore checks reproduction of the fitted expression, not whether the supplied field or noise model describes nature. Process termination does not supply missing stationarity, predictive or publication evidence. Re-evaluating an already examined acquisition remains reused evaluation, never a newly independent held-out survey.","Un manifiesto cierra una generación sólo si hashes, formas, unidades y vínculo congelado concuerdan con inventario original. Exportación intercambia miembros numéricos declarados y acotados, no original sustituto sin seguimiento. Relectura comprueba reproducción de expresión ajustada, no si campo o ruido describen naturaleza. Terminación de proceso no aporta estacionariedad, predicción ni publicación faltantes. Reevaluar adquisición examinada sigue siendo evaluación reutilizada, nunca levantamiento independiente nuevo."]],
    implementation:["The supplied-data CLI performs calibration; the numerical importer independently verifies the complete manifest and arrays. A verified replay keeps the selected original, configuration and generation fixed while exposing their physical units and limitations.","CLI de datos suministrados ejecuta calibración; importador verifica manifiesto completo y arrays independientemente. Reproducción verificada mantiene original, configuración y generación fijos y expone unidades físicas y límites."]};
  const outer=value.rows.filter(r=>r.role==="outer" && r.usable && r.residual_nT!==null), residual=outer.flatMap(r=>r.residual_nT!);
  const rms=residual.length?Math.sqrt(residual.reduce((s,x)=>s+x*x,0)/residual.length):null;
  return <CitationsProvider items={MAGNETIC_CITATIONS}><section className="magnetic-course method-article" data-generation={value.binding.generation_sha256} data-lesson={lesson.id}>
    <h1>{i?"Curso de inversión de levantamientos magnéticos":"Magnetic survey inversion course"}</h1>
    <p>{i?"Inversión de susceptibilidad inducida y lectura de una generación reproducible. La predicción y la resolución son condicionales al campo, la malla, los errores y el prior declarados; no prueban una geología única ni sustituyen metadatos de campo ausentes.":"Induced-susceptibility inversion and interpretation of a reproducible generation. Prediction and resolution are conditional on the declared field, mesh, errors and prior; they do not prove unique geology or replace missing field metadata."}</p>
    <label>{i?"Capítulo":"Chapter"} <select value={chapter} onChange={e=>setChapter(Number(e.target.value))}>{magneticLessons.map((l,k)=><option key={l.id} value={k}>{k+1}. {l.label[i]}</option>)}</select></label>
    <article><h2>{lesson.title[i]}</h2><p>{lesson.body[i]} {lesson.references.map(r=><Cite key={r.id} id={r.id}/>)}</p>
      {derivation.paragraphs.map((p,k)=><p key={k}>{p[i]}</p>)}
      <Equation tex={lesson.equation} caption={lesson.symbols[i]}/>
      <Equation tex={derivation.equation} caption={derivation.symbols[i]}/>
      <Figure caption={i?"Relaciones del método; esquema conceptual, no datos ni resultado ajustado.":"Method relationships; conceptual schematic, not data or a fitted result."}>
        <MagneticMethodDiagram value={derivation} language={i}/>
      </Figure>
      <h3>{i?"Algoritmo y expresión física":"Algorithm and physical expression"}</h3><p>{derivation.implementation[i]}</p>
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
  </section></CitationsProvider>;
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
