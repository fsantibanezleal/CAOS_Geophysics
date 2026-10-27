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
    <M11WorkflowDiagram t={t} titleId={id+"-workflow-title"} />
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

function M11WorkflowDiagram({ t, titleId }: { t: (en: string, es: string) => string; titleId: string }) {
  return <figure className="m11-workflow">
    <svg className="m11-flow-wide" viewBox="0 0 1120 300" role="img" aria-labelledby={titleId}>
      <title id={titleId}>{t("Gravity and magnetic joint inversion workflow", "Flujo de inversión conjunta gravimétrica y magnética")}</title>
      <defs><marker id={`${titleId}-arrow`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" /></marker></defs>
      <g className="m11-flow-node">
        <rect x="12" y="28" width="228" height="220" rx="6" />
        <text x="28" y="57" className="m11-flow-heading">{t("Measured surveys", "Levantamientos medidos")}</text>
        <text x="28" y="91">gᵢ ± σg · (xᵢ, yᵢ, zᵢ)</text>
        <text x="28" y="119">Bzⱼ ± σB · (xⱼ, yⱼ, zⱼ)</text>
        <path d="M28 138 H222" className="m11-flow-rule" />
        <text x="28" y="167">{t("Independent stations,", "Estaciones independientes,")}</text>
        <text x="28" y="192">{t("coordinates and errors", "coordenadas y errores")}</text>
        <text x="28" y="221" className="m11-flow-muted">Wg, WB from declared uncertainty</text>
      </g>
      <path d="M246 138 H278" className="m11-flow-arrow" markerEnd={`url(#${titleId}-arrow)`} />
      <g className="m11-flow-node">
        <rect x="286" y="28" width="236" height="220" rx="6" />
        <text x="302" y="57" className="m11-flow-heading">{t("Physical forward maps", "Operadores físicos")}</text>
        <text x="302" y="100">dg = Gg ρ</text>
        <text x="302" y="131">dBz = Gm κ</text>
        <path d="M302 150 H506" className="m11-flow-rule" />
        <text x="302" y="180">Gg: prism gravity kernel</text>
        <text x="302" y="207">Gm: magnetic dipole kernel</text>
        <text x="302" y="232" className="m11-flow-muted">same mesh · separate physics</text>
      </g>
      <path d="M528 138 H560" className="m11-flow-arrow" markerEnd={`url(#${titleId}-arrow)`} />
      <g className="m11-flow-node m11-flow-objective">
        <rect x="568" y="28" width="300" height="220" rx="6" />
        <text x="584" y="57" className="m11-flow-heading">{t("Joint objective", "Objetivo conjunto")}</text>
        <text x="584" y="91">½‖Wg(Ggρ − dg)‖²</text>
        <text x="584" y="119">+ ½‖WB(Gmκ − dB)‖²</text>
        <text x="584" y="151">+ βg Rg(ρ) + βm Rm(κ)</text>
        <path d="M584 168 H852" className="m11-flow-rule" />
        <text x="584" y="190">+ λc Rc(∇ρ, ∇κ) / Rc,0</text>
        <text x="584" y="215">+ μ Pmix(ρ, κ) · PGI only</text>
        <text x="584" y="239" className="m11-flow-muted">{t("cross-gradient couples boundaries, not amplitudes", "gradiente cruzado acopla bordes, no amplitudes")}</text>
      </g>
      <path d="M874 138 H906" className="m11-flow-arrow" markerEnd={`url(#${titleId}-arrow)`} />
      <g className="m11-flow-node">
        <rect x="914" y="28" width="194" height="220" rx="6" />
        <text x="930" y="57" className="m11-flow-heading">{t("Recovered models", "Modelos recuperados")}</text>
        <text x="930" y="105">ρ · g/cm³</text>
        <text x="930" y="136">κ · dimensionless</text>
        <path d="M930 155 H1092" className="m11-flow-rule" />
        <text x="930" y="184">{t("shared structure", "estructura compartida")}</text>
        <text x="930" y="209">{t("distinct amplitudes", "amplitudes distintas")}</text>
        <text x="930" y="233" className="m11-flow-muted">{t("compare to independent fits", "comparar con ajustes separados")}</text>
      </g>
      <text x="12" y="278" className="m11-flow-footnote">{t("The coupling term is an assumption to test: report both independent baselines and the objective terms before interpreting a shared boundary.", "El acoplamiento es una hipótesis que se debe probar: reporte ambas bases independientes y los términos del objetivo antes de interpretar un borde compartido.")}</text>
    </svg>
    <svg className="m11-flow-compact" viewBox="0 0 360 700" role="img" aria-labelledby={titleId+"-compact"}>
      <title id={titleId+"-compact"}>{t("Gravity and magnetic joint inversion workflow", "Flujo de inversión conjunta gravimétrica y magnética")}</title>
      <defs><marker id={`${titleId}-compact-arrow`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" /></marker></defs>
      <g className="m11-flow-node"><rect x="12" y="12" width="336" height="128" rx="6"/><text x="28" y="40" className="m11-flow-heading">{t("Measured surveys", "Levantamientos medidos")}</text><text x="28" y="70">gᵢ ± σg · (xᵢ,yᵢ,zᵢ)</text><text x="28" y="96">Bzⱼ ± σB · (xⱼ,yⱼ,zⱼ)</text><text x="28" y="121" className="m11-flow-muted">{t("independent stations and errors", "estaciones y errores independientes")}</text></g>
      <path d="M180 143 V165" className="m11-flow-arrow" markerEnd={`url(#${titleId}-compact-arrow)`}/>
      <g className="m11-flow-node"><rect x="12" y="172" width="336" height="128" rx="6"/><text x="28" y="200" className="m11-flow-heading">{t("Physical forward maps", "Operadores físicos")}</text><text x="28" y="234">dg = Gg ρ · prism gravity</text><text x="28" y="263">dBz = Gm κ · magnetic dipole</text><text x="28" y="286" className="m11-flow-muted">{t("same mesh · separate physics", "misma malla · física separada")}</text></g>
      <path d="M180 303 V325" className="m11-flow-arrow" markerEnd={`url(#${titleId}-compact-arrow)`}/>
      <g className="m11-flow-node m11-flow-objective"><rect x="12" y="332" width="336" height="202" rx="6"/><text x="28" y="360" className="m11-flow-heading">{t("Joint objective", "Objetivo conjunto")}</text><text x="28" y="393">½‖Wg(Ggρ − dg)‖²</text><text x="28" y="420">+ ½‖WB(Gmκ − dB)‖²</text><text x="28" y="447">+ βg Rg(ρ) + βm Rm(κ)</text><text x="28" y="474">+ λc Rc / Rc,0</text><text x="28" y="500">+ μ Pmix(ρ, κ) · PGI</text><text x="28" y="524" className="m11-flow-muted">{t("structure term and mixture prior are alternatives", "acoplamiento y mezcla son alternativas")}</text></g>
      <path d="M180 537 V559" className="m11-flow-arrow" markerEnd={`url(#${titleId}-compact-arrow)`}/>
      <g className="m11-flow-node"><rect x="12" y="566" width="336" height="122" rx="6"/><text x="28" y="594" className="m11-flow-heading">{t("Recovered models", "Modelos recuperados")}</text><text x="28" y="627">ρ · g/cm³</text><text x="28" y="654">κ · dimensionless</text><text x="28" y="680" className="m11-flow-muted">{t("shared structure · distinct amplitudes", "estructura compartida · amplitudes distintas")}</text></g>
    </svg>
    <figcaption>{t("Operator-to-model path for the supplied-survey method. The current panel teaches the equations; it does not launch this solve.", "Trayecto desde los operadores hasta los modelos del método para datos suministrados. Este panel enseña las ecuaciones; no ejecuta la inversión.")}</figcaption>
  </figure>;
}
