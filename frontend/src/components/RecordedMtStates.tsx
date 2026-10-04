import { useEffect, useState } from "react";
import type { MtResult } from "../api/mt-contracts";
import { LayerColumn, Plot } from "./ScientificPlots";
import { downloadInspection, recordedMtState } from "./result-view-data";

export function RecordedMtStates({ result, es }: {
  result: MtResult; es: boolean;
}) {
  const t = (en: string, sp: string) => es ? sp : en;
  const [playing, setPlaying] = useState(false), [reduced, setReduced] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [layer, setLayer] = useState(0), [frame, setFrame] = useState(0);
  const m = result.inverse!.methods["mt-lm"], last = m.frames.length - 1;
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => { setReduced(media.matches); if (media.matches) setPlaying(false); };
    const visibility = () => { if (document.hidden) setPlaying(false); };
    media.addEventListener("change", change); document.addEventListener("visibilitychange", visibility);
    return () => { media.removeEventListener("change", change); document.removeEventListener("visibilitychange", visibility); };
  }, []);
  useEffect(() => {
    if (!playing || reduced || document.hidden || frame >= last) return;
    const timer = setTimeout(() => { setFrame(frame + 1); if (frame + 1 === last) setPlaying(false); }, 500);
    return () => clearTimeout(timer);
  }, [playing, reduced, frame, last]);
  const select = (index: number) => { setPlaying(false); setFrame(index); };
  const state = recordedMtState(result, frame);
  return <section aria-label={t("Recorded residual evaluations", "Evaluaciones residuales registradas")}>
    <Plot interactive x={m.history.map((_, i) => i)} series={[{ name: "J [1]", values: m.history }]} title={t("Objective per recorded residual evaluation", "Objetivo por evaluación residual registrada")} xLabel={t("recorded frame [1]", "marco registrado [1]")} yLabel="J [1]" selectedIndex={frame} onSelect={select}/>
    <div className="processing-view-controls">
      <button className="btn" disabled={frame === 0} onClick={() => select(frame - 1)}>{t("Previous recorded state", "Estado registrado anterior")}</button>
      <button className="btn" disabled={frame === last} onClick={() => select(frame + 1)}>{t("Next recorded state", "Estado registrado siguiente")}</button>
      <button className="btn" disabled={!playing && (reduced || frame === last || document.hidden)} aria-pressed={playing} onClick={() => setPlaying(!playing)}>{playing ? t("Pause recorded states", "Pausar estados registrados") : t("Play recorded states", "Reproducir estados registrados")}</button>
      <button className="btn" onClick={() => select(0)}>{t("Reset recorded state", "Restablecer estado registrado")}</button>
    </div>
    <label className="select-control"><span>{t("Recorded evaluation index [1]", "Índice de evaluación registrada [1]")}</span><input type="range" min={0} max={last} step={1} value={frame} onChange={event => select(Number(event.target.value))}/></label>
    <output data-testid="mt-recorded-state">{frame}/{last} · {state.state.kind} · step {state.state.step} · ρ {state.model_ohm_m.join(" / ")} Ω m · J {state.objective} · Jdata {state.state.objective.data} · Jreg {state.state.objective.regularization}</output>
    <LayerColumn rho={state.model_ohm_m} thickness={state.thickness_m} selectedLayer={layer} onSelect={setLayer} title={t("Recorded evaluation model; not the selected final response", "Modelo de evaluación registrada; no la respuesta final seleccionada")}/>
    <p className="plot-note">{t("500 ms per stored record, no interpolation or loop. Records are residual evaluations, not accepted iterations or physical time. Response panels always use the selected final model; historical predictions are not supplied.", "500 ms por registro almacenado, sin interpolación ni ciclo. Son evaluaciones residuales, no iteraciones aceptadas ni tiempo físico. Los paneles de respuesta usan el modelo final seleccionado; no se proporcionan predicciones históricas.")}</p>
    {reduced && <p>{t("Reduced motion: use manual step/scrub; automatic playback is disabled.", "Movimiento reducido: use pasos/manual; reproducción automática desactivada.")}</p>}
    <button className="btn" onClick={() => downloadInspection(state, `recorded-mt-${result.job_id}-${frame}.json`)}>{t("Export recorded state JSON", "Exportar estado registrado JSON")}</button>
  </section>;
}
