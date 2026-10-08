import { useEffect, useMemo, useRef, useState } from "react";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { browserJointFiles, exportJointOriginals, importJointOutput, jointPhysicalRange, jointResponse, jointSidecar, jointState, obj,
  type JointInspection, type Modality, type NativeRecord, type Partition } from "../api/joint-result";
import { color } from "../science";
import { Legend, Plot } from "./ScientificPlots";
import { downloadInspection } from "./result-view-data";

/** Local original-output inspection only. Never starts scientific computation. */
export function JointResultWorkbench({ initial }: { initial?: JointInspection }) {
  const es = useShellLang() === "es", t = (en: string, sp: string) => es ? sp : en;
  const [inspection, setInspection] = useState<JointInspection | null>(initial ?? null), [busy, setBusy] = useState(false), [error, setError] = useState(false);
  const controller = useRef<AbortController | null>(null), generation = useRef(0);
  const [view, setView] = useState("response"), [modality, setModality] = useState<Modality>("gravity"), [partition, setPartition] = useState<Partition>("sealed");
  const [row, setRow] = useState(0), [cell, setCell] = useState(0), [attempt, setAttempt] = useState(0), [state, setState] = useState(0);
  const [plane, setPlane] = useState<"xy" | "xz" | "yz">("xy"), [slice, setSlice] = useState(0), [exportBusy, setExportBusy] = useState(false);
  const [exportError, setExportError] = useState(false), [normalized, setNormalized] = useState(false);
  useEffect(() => () => { controller.current?.abort(); generation.current++; }, []);
  const clear = () => { controller.current?.abort(); generation.current++; setInspection(null); setBusy(false); setError(false); setExportError(false); setExportBusy(false); };
  async function load(files: FileList | null) {
    if (!files?.length) return;
    clear(); const id = generation.current, abort = new AbortController(); controller.current = abort; setBusy(true);
    try { const result = await importJointOutput(browserJointFiles(files), abort.signal);
      if (id !== generation.current) return; setInspection(result); setView(result.outcome === "failed" ? "optimization" : "response");
      setRow(0); setCell(0); setAttempt(0); setState(0); setSlice(0); setPlane("xy");
    } catch { if (id === generation.current && !abort.signal.aborted) setError(true); }
    finally { if (id === generation.current) setBusy(false); }
  }
  async function exportOriginals() {
    if (!inspection || busy || exportBusy) return; const id = generation.current; setExportBusy(true); setExportError(false);
    try { const bytes = await exportJointOriginals(inspection); if (id !== generation.current) return;
      const url = URL.createObjectURL(new Blob([bytes.slice().buffer], { type: "application/zip" })), a = document.createElement("a");
      a.href = url; a.download = "joint-private-original-output.zip"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch { if (id === generation.current) setExportError(true); } finally { if (id === generation.current) setExportBusy(false); }
  }
  const response = useMemo(() => inspection?.outcome === "completed" ? jointResponse(inspection, modality, partition) : null, [inspection, modality, partition]);
  const responsePlot = useMemo(() => response ? { x: Array.from(response.rows), observed: Array.from(response.observed), predicted: Array.from(response.predicted), residual: Array.from(response.residual), whitened: Array.from(response.whitened) } : null, [response]);
  const selected = inspection?.candidates[attempt], recorded = selected?.trace.models_q.shape[0] ? jointState(selected, state) : null;
  const model = inspection?.model, axes = plane === "xy" ? [0, 1, 2] : plane === "xz" ? [0, 2, 1] : [1, 2, 0];
  const sliceCount = model ? model.arrays[["mesh_hx_m", "mesh_hy_m", "mesh_hz_m"][axes[2]]].shape[0] : 0;
  function cellSlice(index: number, orientation = plane) {
    if (!model) return 0; const id = model.arrays.active_full_indices.values[index], nx = model.arrays.mesh_hx_m.shape[0], ny = model.arrays.mesh_hy_m.shape[0];
    return orientation === "xy" ? Math.floor(id / (nx * ny)) : orientation === "xz" ? Math.floor(id / nx) % ny : id % nx;
  }
  function chooseCell(index: number) { setCell(index); setSlice(cellSlice(index)); }
  function chooseSlice(value: number) {
    setSlice(value); if (!model) return;
    const index = Array.from(model.arrays.active_full_indices.values).findIndex((_, i) => cellSlice(i) === value);
    if (index >= 0) setCell(index);
  }
  function select(label: string, value: string | number, change: (value: string) => void, entries: [string | number, string][]) {
    return <label className="select-control"><span>{label}</span><select className="select" aria-label={label} value={value} onChange={e => change(e.target.value)}>{entries.map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>;
  }
  function table(heads: string[], rows: (string | number | boolean | null)[][], caption: string) {
    return <div className="processing-station-table"><table className="cmp-table"><caption>{caption}</caption><thead><tr>{heads.map(h => <th key={h} scope="col">{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j}>{v === null ? t("unavailable", "no disponible") : String(v)}</td>)}</tr>)}</tbody></table></div>;
  }
  return <section className="processing-instrument mt-instrument" data-testid="joint-result-workbench" aria-label={t("Supplied joint result instrument", "Instrumento de resultados conjuntos suministrados")}>
    <div className="processing-status"><strong>{t("Offline scientific processing; local browser inspection", "Procesamiento científico fuera de línea; inspección local en navegador")}</strong></div>
    <details className="processing-provenance"><summary>{t("Inspection scope and private custody", "Alcance de inspección y custodia privada")}</summary>
      <p>{t("Import the complete output directory from a local gravity–magnetic workflow. This browser reads exported physical values and checks transport consistency; it does not fit, refit, run physical kernels or certify scientific acceptance. No files are uploaded or stored by this tool.", "Importe el directorio completo de salida de un flujo local gravedad–magnetismo. El navegador lee valores físicos exportados y comprueba consistencia de transporte; no ajusta, reajusta, ejecuta kernels físicos ni certifica aceptación científica. Esta herramienta no sube ni almacena archivos.")}</p></details>
    <div className="processing-station-toolbar">
      <label className="select-control"><span>{t("Import local workflow output directory", "Importar directorio local de resultados")}</span>
        <input type="file" aria-label={t("Import local workflow output directory", "Importar directorio local de resultados")} multiple ref={el => { if (el) el.setAttribute("webkitdirectory", ""); }} onChange={e => { void load(e.target.files); e.target.value = ""; }}/></label>
      <button className="btn" disabled={!inspection && !busy && !error} onClick={clear}>{busy ? t("Cancel import", "Cancelar importación") : t("Clear private result", "Borrar resultado privado")}</button>
      <button className="btn" disabled={!inspection || busy || exportBusy} onClick={() => void exportOriginals()}>{exportBusy ? t("Preparing private archive", "Preparando archivo privado") : t("Export original private archive (includes observations)", "Exportar archivo privado original (incluye observaciones)")}</button>
      <button className="btn" disabled={!inspection || busy} onClick={() => { if (inspection) downloadInspection(jointSidecar(inspection, modality, partition, row, cell, attempt, state), "joint-inspection.json"); }}>{t("Export selected exact inspection JSON", "Exportar inspección exacta seleccionada JSON")}</button>
    </div>
    {busy && <p role="status">{t("Admitting full original inventory, headers and hashes. No scientific execution.", "Admitiendo inventario completo, cabeceras y hashes originales. Sin ejecución científica.")}</p>}
    {(error || exportError) && <p role="alert">{t("The private output could not be admitted or exported. Use the complete native workflow directory and validate it offline; unsupported, incomplete or altered files are not displayed. No scientific result was replaced by a fallback.", "No se pudo admitir o exportar la salida privada. Use el directorio nativo completo y valídelo fuera de línea; no se muestran archivos incompatibles, incompletos o alterados. Ningún resultado científico se reemplazó por alternativa.")}</p>}
    {!inspection && !busy && <p>{t("Run and validate the supplied-survey workflow locally with its original development and sealed inputs, then select its new output directory. A supplied-model evaluation remains an evaluation, not an inverse. This instrument does not turn the cached synthetic course into supplied-data processing.", "Ejecute y valide localmente el flujo de levantamientos suministrados con entradas originales de desarrollo y reserva, y seleccione su nuevo directorio de salida. Evaluar un modelo suministrado no es invertir. Este instrumento no convierte el curso sintético almacenado en procesamiento de datos suministrados.")}</p>}
    {inspection && <>
      <div className="evaluation-status" data-evaluation={inspection.outcome === "failed" ? "failed" : "unresolved"} data-testid="joint-workflow-boundary"><strong>{inspection.outcome === "failed" ? t("Offline workflow failed; retained accepted states are not a completed inverse", "Flujo fuera de línea fallido; estados aceptados conservados no son inversión completa") : inspection.mode === "evaluate" ? t("Supplied-model evaluation; inverse execution false", "Evaluación de modelo suministrado; ejecución inversa falsa") : t("Offline solve receipt completed; candidate failures and scientific gates remain separate", "Recibo de inversión fuera de línea completo; fallos de candidatos y criterios científicos permanecen separados")}</strong>
        <details className="processing-provenance"><summary>{t("Integrity is not scientific acceptance or a rights grant", "Integridad no es aceptación científica ni permiso")}</summary><p>{t("Archive hashes are integrity, not authenticity. Field eligibility, geological recovery, global optimality and redistribution rights are not established. Independent scientific replay still requires original inputs and the pinned offline runtime.", "Hashes son integridad, no autenticidad. No se establece elegibilidad de campo, recuperación geológica, óptimo global ni derechos de redistribución. Replay científico independiente requiere entradas originales y runtime fijado fuera de línea.")}</p></details></div>
      <div className="processing-station-toolbar">{select(t("Joint scientific view", "Vista científica conjunta"), view, setView,
        [...(inspection.outcome === "completed" ? [["response", t("Observed, predicted and residual response", "Respuesta observada, predicha y residual")], ["model", t("Native physical property sections", "Secciones nativas de propiedades físicas")]] as [string, string][] : []),
          ...(inspection.candidates.length ? [["optimization", t("Constrained optimization states", "Estados de optimización restringida")], ["comparison", t("Independent baselines and validation selection", "Bases independientes y selección por validación")]] as [string, string][] : [])])}</div>
      {view === "response" && response && responsePlot && <>
        <div className="processing-station-toolbar">
          {select(t("Survey response", "Respuesta de levantamiento"), modality, v => { setModality(v as Modality); setRow(0); }, [["gravity", t("Upward gravity [mGal]", "Gravedad hacia arriba [mGal]")], ["magnetic", t("Linear induced TMI [nT]", "TMI inducida lineal [nT]")]])}
          {select(t("Frozen partition", "Partición congelada"), partition, v => { setPartition(v as Partition); setRow(0); }, [["training", t("Training", "Entrenamiento")], ["validation", t("Validation selection", "Selección por validación")], ["sealed", t("Sealed evaluation", "Evaluación reservada")]])}
          {select(t("Original receiver row", "Fila receptora original"), row, v => setRow(Number(v)), Array.from(response.rows, (v, i) => [i, String(v)]))}
          {select(t("Signed residual coordinates", "Coordenadas residuales con signo"), normalized ? "white" : "physical", v => setNormalized(v === "white"), [["physical", response.unit], ["white", t("Principal-marginal whitened [1]", "Blanqueado marginal principal [1]")]])}
        </div>
        <output className="processing-station-readout" data-testid="joint-response-readout">{t("Original row", "Fila original")} {response.rows[row]} · {t("observed", "observado")} {response.observed[row]} {response.unit} · {t("predicted", "predicho")} {response.predicted[row]} {response.unit} · {t("predicted minus observed", "predicho menos observado")} {response.residual[row]} {response.unit} · {t("whitened coordinate", "coordenada blanqueada")} {response.whitened[row]} [1]</output>
        <div className="mt-plot-grid">
          <Plot interactive title={t("Observed and frozen-model predicted response", "Respuesta observada y predicha de modelo congelado")} x={responsePlot.x} series={[{ name: t("Observed", "Observado"), values: responsePlot.observed, points: true }, { name: t("Predicted", "Predicho"), values: responsePlot.predicted, points: true }]} xLabel={t("original receiver row [1]", "fila receptora original [1]")} yLabel={response.unit} selectedIndex={row} onSelect={setRow}/>
          <Plot interactive title={t("Signed residual, prediction minus observation", "Residuo con signo, predicción menos observación")} x={responsePlot.x} series={[{ name: normalized ? t("Marginal whitened", "Blanqueado marginal") : t("Physical residual", "Residuo físico"), values: normalized ? responsePlot.whitened : responsePlot.residual, points: true }]} xLabel={t("original receiver row [1]", "fila receptora original [1]")} yLabel={normalized ? "[1]" : response.unit} zeroCentered selectedIndex={row} onSelect={setRow}/>
        </div>
        <p className="plot-note">{t("Receiver row is not a distance or coordinate. Curves connect no inferred spatial trajectory. Whitened values use the principal marginal partition covariance; with correlated errors they are not individual receiver residuals divided by an SD. No fitted historical responses or uncertainty bars are supplied.", "La fila receptora no es distancia ni coordenada. Las curvas no infieren trayectoria espacial. Valores blanqueados usan covarianza marginal principal de la partición; con errores correlacionados no son residuos individuales divididos por DE. No se proporcionan respuestas históricas ajustadas ni barras de incertidumbre.")}</p>
        {table([t("Modality / partition", "Modalidad / partición"), "N", "RMSE", "WRMS [1]", "χ² [1]"], (["gravity", "magnetic"] as const).flatMap(m => (["training", "validation", "sealed"] as const).map(p => { const v = obj(obj(inspection.result!.payload.metrics)[m])[p], metric = obj(v); return [`${m} / ${p}`, metric.count as number, `${metric.rmse_physical} ${metric.unit}`, metric.wrms as number, metric.chi_square as number]; })), t("Independent marginal metrics; no combined science score", "Métricas marginales independientes; sin puntaje científico combinado"))}
      </>}
      {view === "model" && model && <>
        <div className="processing-station-toolbar">
          {select(t("Physical section plane", "Plano de sección física"), plane, v => { setPlane(v as typeof plane); setSlice(cellSlice(cell, v as typeof plane)); }, [["xy", "E / N"], ["xz", "E / U"], ["yz", "N / U"]])}
          {select(t("Fixed mesh slice", "Corte fijo de malla"), slice, v => chooseSlice(Number(v)), Array.from({ length: sliceCount }, (_, i) => [i, String(i)]))}
          {select(t("Active physical cell", "Celda física activa"), cell, v => chooseCell(Number(v)), Array.from(model.arrays.active_full_indices.values, (v, i) => [i, String(v)]))}
        </div>
        <output className="processing-station-readout" data-testid="joint-cell-readout">{cellSlice(cell) !== slice && t("Selected cell outside empty active slice · ", "Celda seleccionada fuera de corte activo vacío · ")}{t("Full cell", "Celda completa")} {model.arrays.active_full_indices.values[cell]} · ENU [{Array.from(model.arrays.active_cell_centres_m.values.slice(cell * 3, cell * 3 + 3)).join(", ")}] m · ρ {model.arrays.density_kg_m3.values[cell]} kg/m³ · χ {model.arrays.susceptibility_si.values[cell]} SI · V {model.arrays.active_cell_volumes_m3.values[cell]} m³</output>
        <div className="mt-plot-grid"><JointPhysicalSection model={model} property="density_kg_m3" axes={axes} slice={slice} cell={cell} onCell={chooseCell} title={t("Signed density contrast", "Contraste de densidad con signo")}/><JointPhysicalSection model={model} property="susceptibility_si" axes={axes} slice={slice} cell={cell} onCell={chooseCell} title={t("Induced SI susceptibility", "Susceptibilidad SI inducida")}/></div>
        <p className="plot-note">{t("Native nonuniform active prisms, x-fast indexing, ENU metres and upward height. Blank cells are inactive, not zero property. Slice controls only inspect the frozen model; no interpolation, terrain conversion, inferred rock labels or approximate coupling field is drawn.", "Prismas activos no uniformes nativos, índice x-rápido, metros ENU y altura positiva arriba. Celdas vacías son inactivas, no propiedad cero. Los cortes solo inspeccionan modelo congelado; sin interpolación, conversión de terreno, litología inferida ni campo de acoplamiento aproximado.")}</p>
        {table([t("Physical value", "Valor físico"), t("Exact value", "Valor exacto")], [["ρ [kg/m³]", model.arrays.density_kg_m3.values[cell]], ["χ [SI]", model.arrays.susceptibility_si.values[cell]], ["ENU centre [m]", Array.from(model.arrays.active_cell_centres_m.values.slice(cell * 3, cell * 3 + 3)).join(", ")], ["Emin, Emax, Nmin, Nmax, Umin, Umax [m]", Array.from(model.arrays.active_cell_bounds_m.values.slice(cell * 6, cell * 6 + 6)).join(", ")], ["V [m³]", model.arrays.active_cell_volumes_m3.values[cell]]], t("Selected actual active prism; not geological truth", "Prisma activo real seleccionado; no verdad geológica"))}
      </>}
      {view === "optimization" && <>
        <div className="processing-station-toolbar">{select(t("Actual optimization attempt", "Intento de optimización real"), attempt, v => { setAttempt(Number(v)); setState(0); }, inspection.candidates.map((c, i) => [i, `${c.stage}: ${c.modality ?? t("joint", "conjunto")} · λ ${c.weights.coupling} · ${c.start} · ${c.status}`]))}
          {recorded && select(t("Recorded accepted state", "Estado aceptado registrado"), state, v => setState(Number(v)), Array.from({ length: selected!.trace.models_q.shape[0] }, (_, i) => [i, `${i === 0 ? t("Initial", "Inicial") : t("Accepted", "Aceptado")} ${i}`]))}</div>
        {selected && <p data-testid="joint-attempt-status">{t("Terminal receipt (verbatim)", "Recibo terminal (literal)")}: {selected.status} / {selected.reason} · {selected.iterations} {t("accepted steps", "pasos aceptados")} · {selected.writerReplayed ? t("Offline writer declares replay-verified attempt; browser does not establish physics", "Escritor fuera de línea declara intento verificado; navegador no establece física") : t("Last attempt retained before scientific replay; not replay-verified", "Último intento conservado antes de replay científico; no verificado")}</p>}
        {recorded && selected && <>
          <output className="processing-station-readout" data-testid="joint-state-readout">{t("State", "Estado")} {state} · F {recorded.objective} · {t("recorded normalized exact-bound KKT", "KKT normalizado de límite exacto registrado")} {recorded.kkt_normalized} · βρ {String(selected.weights.beta_gravity)} · βχ {String(selected.weights.beta_magnetic)} · λ {String(selected.weights.coupling)}</output>
          <div className="mt-plot-grid"><Plot interactive title={t("Actual accepted objective history", "Historia de objetivo aceptado real")} x={Array.from({ length: selected.trace.phi_engine.values.length }, (_, i) => i)} series={[{ name: "F", values: Array.from(selected.trace.phi_engine.values) }]} xLabel={t("accepted state [1]", "estado aceptado [1]")} yLabel="[1]" selectedIndex={state} onSelect={setState}/>
            <Plot interactive title={t("Actual recorded property block", "Bloque de propiedades registrado real")} x={recorded.q.map((_, i) => i)} series={[{ name: t("Normalized model q", "Modelo normalizado q"), values: recorded.q, points: true }]} xLabel={t("property-block entry [1]", "entrada de bloque de propiedad [1]")} yLabel="q [1]"/></div>
          {recorded.terms ? table([t("Exported unweighted term", "Término no ponderado exportado"), t("Exact scalar [1]", "Escalar exacto [1]")], Object.entries(recorded.terms), t("Exact exported scalar terms; coupling is not a vector-factor map", "Términos escalares exactos exportados; acoplamiento no es mapa de factores vectoriales")) : <p>{t("No scientifically replayed five-term or physical-property trace was exported for this interrupted attempt. Only the original normalized states are shown.", "No se exportó traza de cinco términos ni propiedades físicas con replay científico para este intento interrumpido. Solo se muestran estados normalizados originales.")}</p>}
          {recorded.physical && <details className="processing-provenance"><summary>{t("Exact accepted physical property block", "Bloque físico exacto del estado aceptado")}</summary>{table([t("Block entry", "Entrada de bloque"), t("Physical value", "Valor físico"), t("Unit", "Unidad")], recorded.physical.map((v, i) => [i, v, selected.modality === "gravity" || selected.modality === null && i < recorded.physical!.length / 2 ? "kg/m³" : "SI"]), t("Values from this accepted state, not the terminal selection", "Valores de este estado aceptado, no de selección terminal"))}</details>}
          {recorded.preceding_step && <details className="processing-provenance"><summary>{t("Actual preceding search step", "Paso de búsqueda precedente real")}</summary>{table([t("Recorded quantity", "Magnitud registrada"), t("Exact value", "Valor exacto")], Object.entries(recorded.preceding_step), t("Null CG quantities were not measured on the projected branch", "Magnitudes CG null no fueron medidas en rama proyectada"))}</details>}
          <p>{t("Terminal validation and stop status apply to the last state only. Earlier accepted states have no historical prediction or sealed metric arrays. Selecting a frame never reruns optimization or upgrades a failed attempt.", "Validación y estado de parada terminal aplican solo al último estado. Estados aceptados anteriores no tienen arrays de predicción histórica ni métricas reservadas. Seleccionar estado nunca reejecuta optimización ni mejora un intento fallido.")}</p>
        </>}
        {selected && !recorded && <p>{t("This failed attempt has no accepted model state; no model or response is manufactured.", "Este intento fallido no tiene estado de modelo aceptado; no se fabrica modelo ni respuesta.")}</p>}
      </>}
      {view === "comparison" && <>
        <p>{t("Sixteen actual independent training fits (eight fixed beta values per property), then ten fixed positive-lambda fits from submitted and baseline starts. Lambda zero is the selected independently optimized pair, not a refit. Each positive candidate needs both validation WRMS values within 1.05 of its own baseline; selection is not scientific improvement or recovery.", "Dieciséis ajustes reales independientes de entrenamiento (ocho betas fijos por propiedad), luego diez ajustes de lambda positivo fijo desde inicios suministrado y base. Lambda cero es la pareja optimizada independientemente seleccionada, no reajuste. Cada candidato positivo requiere ambos WRMS de validación dentro de 1,05 de su base; seleccionar no es mejora científica ni recuperación.")}</p>
        {table([t("Attempt", "Intento"), t("Property / start", "Propiedad / inicio"), "βρ / βχ / λ", t("Terminal status / reason", "Estado / razón terminal"), t("Eligible", "Elegible"), "WRMS ρ / χ"], inspection.candidates.map(c => [c.stage, `${c.modality ?? "joint"} / ${c.start}`, `${c.weights.beta_gravity} / ${c.weights.beta_magnetic} / ${c.weights.coupling}`, `${c.status} / ${c.reason}`, c.metadata.eligible === undefined ? null : c.metadata.eligible as boolean, c.metadata.validation_wrms ? Object.entries(obj(c.metadata.validation_wrms)).map(([m, v]) => `${m}: ${v}`).join(" / ") : null]), t("Every actual attempt retained; no failed-candidate exclusion", "Todos los intentos reales conservados; sin excluir candidatos fallidos"))}
        {inspection.calibration && <p data-testid="joint-selection-reason">{t("Frozen selection reason (verbatim)", "Razón de selección congelada (literal)")}: {String(inspection.calibration.payload.reason)}</p>}
      </>}
      <details className="processing-provenance"><summary>{t("Original identities, source declarations and resource receipt", "Identidades originales, declaraciones de fuente y recibo de recursos")}</summary>
        <p>{inspection.importedBytes} {t("original bytes admitted; memory/RSS is not inferred from this byte count", "bytes originales admitidos; memoria/RSS no se infiere de este conteo")}</p>
        {table([t("Receipt field", "Campo de recibo"), t("Original declaration", "Declaración original")], Object.entries(inspection.receipt).map(([k, v]) => [k, typeof v === "object" ? JSON.stringify(v) : String(v)]), t("Offline workflow declaration; no browser science certificate", "Declaración de flujo fuera de línea; sin certificado científico del navegador"))}
        {table([t("Original member", "Miembro original"), "SHA-256"], [...inspection.hashes], t("Original file-byte identities", "Identidades de bytes originales"))}
      </details>
    </>}
  </section>;
}

/** Orthographic projection of exact prism bounds, not a coupling diagnostic. */
function JointPhysicalSection({ model, property, axes, slice, cell, onCell, title }: {
  model: NativeRecord; property: "density_kg_m3" | "susceptibility_si"; axes: number[]; slice: number; cell: number; onCell: (value: number) => void; title: string;
}) {
  const es = useShellLang() === "es", a = model.arrays, [u, v, fixed] = axes, values = a[property].values;
  const widths = [a.mesh_hx_m.values, a.mesh_hy_m.values, a.mesh_hz_m.values], origin = a.mesh_origin_m.values;
  const span = widths.map(w => Array.from(w).reduce((x, y) => x + y, 0)), end = Array.from(origin, (o, i) => o + span[i]);
  const nx = widths[0].length, ny = widths[1].length, unit = property === "density_kg_m3" ? "kg/m³" : "SI";
  const range = jointPhysicalRange(values, property === "density_kg_m3");
  const boxes = Array.from(a.active_full_indices.values).flatMap((id, i) => { const xyz = [id % nx, Math.floor(id / nx) % ny, Math.floor(id / (nx * ny))]; if (xyz[fixed] !== slice) return [];
    const b = a.active_cell_bounds_m.values, loU = b[6 * i + 2 * u], hiU = b[6 * i + 2 * u + 1], loV = b[6 * i + 2 * v], hiV = b[6 * i + 2 * v + 1];
    return [{ i, id, x: 72 + (loU - origin[u]) / span[u] * 530, y: 24 + (end[v] - hiV) / span[v] * 260, w: (hiU - loU) / span[u] * 530, h: (hiV - loV) / span[v] * 260 }]; });
  return <figure className="science-plot"><figcaption><span>{title}</span><output>{values[cell]} {unit}</output></figcaption>
    <svg viewBox="0 0 640 330" role="group" aria-label={title}>
      {boxes.map(b => <rect key={b.id} x={b.x} y={b.y} width={b.w} height={b.h} fill={color(values[b.i], range, "field")} stroke={cell === b.i ? "var(--color-fg)" : "var(--color-border)"} strokeWidth={cell === b.i ? 3 : .6} role="button" tabIndex={0} aria-pressed={cell === b.i} aria-label={`${es ? "Celda" : "Cell"} ${b.id}: ${values[b.i]} ${unit}`} data-cell={b.id} data-value={values[b.i]} onPointerMove={() => onCell(b.i)} onClick={() => onCell(b.i)} onKeyDown={e => { if (["Enter", " "].includes(e.key)) { e.preventDefault(); onCell(b.i); } }}><title>{b.id}: {values[b.i]} {unit}</title></rect>)}
      <text x="72" y="304" fill="var(--color-fg)">{origin[u]}</text><text x="602" y="304" textAnchor="end" fill="var(--color-fg)">{end[u]}</text><text x="335" y="324" textAnchor="middle" fill="var(--color-fg)">{["E", "N", "U"][u]} [m]</text>
      <text x="65" y="30" textAnchor="end" fill="var(--color-fg)">{end[v]}</text><text x="65" y="284" textAnchor="end" fill="var(--color-fg)">{origin[v]}</text><text x="30" y="160" textAnchor="middle" transform="rotate(-90 30 160)" fill="var(--color-fg)">{["E", "N", "U"][v]} [m]</text>
    </svg><Legend range={range} unit={unit} palette="field"/>
    {!boxes.length && <p>{es ? "No hay prismas activos en este corte; no se rellenan." : "No active prisms in this slice; none are filled in."}</p>}
  </figure>;
}
