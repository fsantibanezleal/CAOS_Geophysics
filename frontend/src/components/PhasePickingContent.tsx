import { Callout, Cite, Equation, Refs, useShellLang } from "@fasl-work/caos-app-shell";
import { phasePickers, type PickerId, type PickerSection } from "../data/phase-picking";
import { PhasePickingDiagram } from "./PhasePickingDiagram";
import { Link } from "react-router";

export function PhasePickingContent({ method, view }: { method: PickerId; view: "theory" | "implementation" }) {
  const es = useShellLang() === "es";
  const i = es ? 1 : 0;
  const picker = phasePickers.find(item => item.id === method);
  if (!picker) throw new Error(`Unknown phase-picking method: ${method}`);
  const section: PickerSection = picker[view];
  return (
    <article className="method-article" data-picker={method} data-view={view}>
      <h2>{section.title[i]}</h2>
      {section.paragraphs.map(({ text, cite }, index) => (
        <p key={`${method}-${view}-${index}`}>
          {text[i]} <Cite id={cite} paren />
        </p>
      ))}
      {section.equations.map(({ tex, caption }, index) => (
        <Equation key={`${method}-${view}-eq-${index}`} tex={tex} caption={caption[i]} />
      ))}
      <h3>{es ? "Símbolos y unidades" : "Symbols and units"}</h3>
      <ul className="method-symbols">
        {section.symbols.map((pair, index) => <li key={`${method}-${view}-symbol-${index}`}>{pair[i]}</li>)}
      </ul>
      {section.steps && (
        <>
          <h3>{es ? "Secuencia propuesta y prueba pendiente" : "Proposed sequence and pending gate"}</h3>
          <ol>{section.steps.map((pair, index) => <li key={`${method}-step-${index}`}>{pair[i]}</li>)}</ol>
        </>
      )}
      <PhasePickingDiagram method={method} />
      {method === "m13" && view === "implementation" && <p>
        <Link to="/benchmark#phase-picker">{es ? "Abrir inferencia P/S en Benchmark" : "Open P/S inference in Benchmark"}</Link>
      </p>}
      <Callout variant="honest" title={section.calloutTitle[i]}>{section.callout[i]}</Callout>
      <Refs ids={section.refs} label={es ? "Referencias" : "References"} />
    </article>
  );
}
