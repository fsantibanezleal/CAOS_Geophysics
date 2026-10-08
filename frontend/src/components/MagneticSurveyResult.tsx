import { useMemo, useState } from "react";
import { Tabs, SubTabs, useShellLang } from "@fasl-work/caos-app-shell";
import { magneticCells, magneticSpectrum, type MagneticView } from "../api/magnetic-result";
import "./MagneticSurveyResult.css";

/** Mounted only for a receipt-bound immutable result. This is a replay viewer. */
export function MagneticSurveyResult({ value, onExport }: { value: MagneticView; onExport?: () => void }) {
  const es = useShellLang() === "es", t = (en: string, sp: string) => es ? sp : en;
  const format = useMemo(()=>new Intl.NumberFormat(es?"es":"en",{maximumSignificantDigits:6}),[es]);
  const f = (x: number) => format.format(x);
  const [component, setComponent] = useState(0), [selectedRow, setSelectedRow] = useState(0);
  const [group, setGroup] = useState(value.rows[0].group_id), [layer, setLayer] = useState(0);
  const [cellIndex, setCellIndex] = useState(0), [angle, setAngle] = useState(35), [historyIndex, setHistoryIndex] = useState(0);
  const [sourceIndex, setSourceIndex] = useState(0);
  const rows = value.rows.filter(r=>r.group_id===group), row=value.rows[selectedRow];
  const cells = useMemo(()=>magneticCells(value),[value]), cell=cells[cellIndex];
  const psf=value.diagnostics.resolution_arrays, spectrum=magneticSpectrum(rows,component);
  const limits = (v:number[])=>{ const a=Math.min(...v), b=Math.max(...v); return [a,b===a?a+1:b]; };
  const [xmin,xmax]=limits(value.rows.map(r=>r.xyz_m[0])), [ymin,ymax]=limits(value.rows.map(r=>r.xyz_m[1]));
  const sx=(x:number)=>45+610*(x-xmin)/(xmax-xmin), sy=(y:number)=>395-350*(y-ymin)/(ymax-ymin);
  const frame=(title:string, body:React.ReactNode)=> <svg viewBox="0 0 700 450" className="magnetic-drawing" role="img" aria-label={title}>
    <title>{title}</title>{body}</svg>;
  const rowReadout=<output className="magnetic-readout" aria-live="polite" data-row-id={row.row_id}>
    {row.row_id} · {row.role=== "outer"?t("Held out", "Reservada"):t("Development","Desarrollo")} · E {f(row.xyz_m[0])} m · N {f(row.xyz_m[1])} m · U {f(row.xyz_m[2])} m ·
    {t(" Observed", " Observado")} {f(row.observed_nT[component])} nT · {t("Predicted", "Predicho")} {row.predicted_nT===null?t("Unavailable", "No disponible"):f(row.predicted_nT[component])+" nT"} ·
    {t(" Residual", " Residuo")} {row.residual_nT===null?t("Unavailable", "No disponible"):f(row.residual_nT[component])+" nT"}
  </output>;
  const map=<>{rowReadout}<p>{t("Accent: held-out original flights. Muted: development flights. Picking a row links map and line; it does not alter QC or fitting.", "Acento: vuelos originales reservados. Atenuado: vuelos de desarrollo. Seleccionar una fila vincula mapa y línea; no modifica QC ni ajuste.")}</p>{frame(t("Original acquisition map", "Mapa de adquisición original"),<>
    <text x="320" y="440">E (m)</text><text x="8" y="30">N (m)</text>
    {value.rows.map(r=><circle key={r.row_id} cx={sx(r.xyz_m[0])} cy={sy(r.xyz_m[1])} r={selectedRow===r.row?7:4}
      className={r.role==="outer"?"magnetic-outer":"magnetic-development"} opacity={r.usable?1:.4} role="button" tabIndex={0}
      aria-label={`${r.row_id}: ${f(r.observed_nT[component])} nT`} onPointerEnter={()=>setSelectedRow(r.row)}
      onClick={()=>{setSelectedRow(r.row);setGroup(r.group_id);}} onKeyDown={e=>{if(e.key==="Enter"){setSelectedRow(r.row);setGroup(r.group_id);}}} />)}
  </>)}</>;
  const distances=rows.map(r=>Math.hypot(r.xyz_m[0]-rows[0].xyz_m[0],r.xyz_m[1]-rows[0].xyz_m[1]));
  const line=(residual:boolean)=>{
    const values=rows.flatMap(r=>residual?(r.residual_nT?[r.residual_nT[component]]:[]):[r.observed_nT[component],...(r.predicted_nT?[r.predicted_nT[component]]:[])]);
    const [lo,hi]=limits(values.length?values:[0]), distance=Math.max(1,...distances), x=(i:number)=>45+610*distances[i]/distance, y=(n:number)=>395-350*(n-lo)/(hi-lo);
    return <>{rowReadout}<p>{residual?t("Residual is observed minus predicted, in nT.", "El residuo es observado menos predicho, en nT."):t("Circles: observed. Squares: predicted. Original line order and gaps are retained.", "Círculos: observado. Cuadrados: predicho. Se conserva el orden y las brechas de la línea original.")}</p>{frame(residual?t("Signed residual by original flight", "Residuo con signo por vuelo original"):t("Observed and predicted flight", "Vuelo observado y predicho"),<>
      <text x="260" y="440">{t("Horizontal distance (m)", "Distancia horizontal (m)")}</text><text x="8" y="25">nT</text>
      {rows.map((r,i)=><g key={r.row_id} onPointerEnter={()=>setSelectedRow(r.row)} onClick={()=>setSelectedRow(r.row)}>
        {(residual?r.residual_nT:r.observed_nT)!==null && <circle cx={x(i)} cy={y((residual?r.residual_nT:r.observed_nT)![component])} r={selectedRow===r.row?6:3} className="magnetic-observed" />}
        {!residual && r.predicted_nT!==null && <rect x={x(i)-3} y={y(r.predicted_nT[component])-3} width="6" height="6" className="magnetic-predicted" />}
      </g>)}
    </>)}</>;
  };
  const rad=angle*Math.PI/180, [cxlo,cxhi]=limits(cells.map(c=>c.xyz_m[0])), [cylo,cyhi]=limits(cells.map(c=>c.xyz_m[1])), [czlo,czhi]=limits(cells.map(c=>c.xyz_m[2]));
  const projected=(xyz:number[])=>{const x=(xyz[0]-cxlo)/(cxhi-cxlo)-.5,y=(xyz[1]-cylo)/(cyhi-cylo)-.5,z=(xyz[2]-czlo)/(czhi-czlo)-.5;return [350+240*(Math.cos(rad)*x-Math.sin(rad)*y),230+120*(Math.sin(rad)*x+Math.cos(rad)*y)-200*z];};
  const maxChi=Math.max(0,...cells.map(c=>c.chi_si));
  const cellReadout=<output className="magnetic-readout" data-cell-index={cell.index}>{t("Cell", "Celda")} {cell.index} · E {f(cell.xyz_m[0])} m · N {f(cell.xyz_m[1])} m · U {f(cell.xyz_m[2])} m · χ {f(cell.chi_si)} SI · {f(cell.volume_m3)} m³</output>;
  const model=(slice:boolean)=> <>
    {slice?<label>{t("Depth layer", "Capa en profundidad")}<select value={layer} onChange={e=>setLayer(Number(e.target.value))}>{(value.mesh.widths_z_m.data as number[]).map((_,i)=><option key={i} value={i}>{i+1}</option>)}</select></label>:
      <label>{t("View rotation (degrees; does not refit)", "Rotación de vista (grados; no reajusta)")}<input type="range" min="0" max="360" step="1" value={angle} onChange={e=>setAngle(Number(e.target.value))}/></label>}
    {cellReadout}
    {frame(slice?t("Susceptibility depth slice", "Corte de susceptibilidad en profundidad"):t("Susceptibility physical cells in 3D projection", "Celdas físicas de susceptibilidad en proyección 3D"),
      cells.filter(c=>!slice||c.layer===layer).map(c=>{const opacity=maxChi===0?.3:.15+.65*c.chi_si/maxChi;
        const corners=Array.from({length:8},(_,i)=>projected(c.xyz_m.map((x,axis)=>x+((i>>axis)&1?1:-1)*c.widths_m[axis]/2)));
        return <g key={c.index} opacity={opacity} className="magnetic-cell" tabIndex={0} role="button" aria-label={`${c.index}: ${f(c.chi_si)} SI`} onPointerEnter={()=>setCellIndex(c.k)} onClick={()=>setCellIndex(c.k)} onKeyDown={e=>{if(e.key==="Enter")setCellIndex(c.k);}}>
          {slice?<rect x={45+610*(c.xyz_m[0]-c.widths_m[0]/2-cxlo)/(cxhi-cxlo)} y={395-350*(c.xyz_m[1]+c.widths_m[1]/2-cylo)/(cyhi-cylo)} width={610*c.widths_m[0]/(cxhi-cxlo)} height={350*c.widths_m[1]/(cyhi-cylo)} stroke="currentColor" strokeWidth={cellIndex===c.k?2:.3}/>: [[4,5,7,6],[0,1,5,4],[0,2,6,4]].map((face,i)=><polygon key={i} points={face.map(j=>corners[j].join(",")).join(" ")} stroke="currentColor" strokeWidth={cellIndex===c.k?2:.3}/>)}
        </g>;}))}
    <p>{t("Opacity encodes susceptibility, not certainty. Physical cell faces retain the nonuniform mesh; no interpolated geology.", "La opacidad codifica susceptibilidad, no certeza. Las caras físicas conservan la malla no uniforme; no se interpola geología.")}</p>
  </>;
  const resolution=<>{psf?<><label>{t("Point-spread source cell", "Celda fuente de dispersión puntual")}<select value={sourceIndex} onChange={e=>setSourceIndex(Number(e.target.value))}>{psf.selected_indices.data.map((i,k)=><option key={k} value={k}>{Number(i)}</option>)}</select></label>
    {frame(t("Local point spread", "Dispersión puntual local"),cells.map(c=>{const p=projected(c.xyz_m),n=Number(psf.point_spread.data[c.k*psf.selected_indices.data.length+sourceIndex]); return <circle key={c.index} cx={p[0]} cy={p[1]} r={cellIndex===c.k?7:4} className={n<0?"magnetic-outer":"magnetic-development"} onPointerEnter={()=>setCellIndex(c.k)}><title>{c.index}: {f(n)}</title></circle>;}))}
    {cellReadout}<output>{t("Response", "Respuesta")}: {f(Number(psf.point_spread.data[cellIndex*psf.selected_indices.data.length+sourceIndex]))}</output></>:<p>{t("Local resolution unavailable; not replaced by zero.", "Resolución local no disponible; no se reemplaza por cero.")}</p>}
    <p>{t("Fixed-objective free-face resolution is conditional on this mesh, field, regularizer and active bounds. It is not posterior geological uncertainty. Physical sensitivity was not exported and is unavailable.", "La resolución local depende de esta malla, campo, regularizador y límites activos. No es incertidumbre geológica posterior. La sensibilidad física no se exportó y no está disponible.")}</p></>;
  const h=value.history[Math.min(historyIndex,Math.max(0,value.history.length-1))];
  const history=<>{h?<><label>{t("Accepted objective state (replay only)", "Estado de objetivo aceptado (solo reproducción)")}<input type="range" min="0" max={value.history.length-1} value={historyIndex} onChange={e=>setHistoryIndex(Number(e.target.value))}/></label>
    <dl><dt>{t("Candidate / fold", "Candidato / partición")}</dt><dd>{h.candidate} / {h.fold}</dd><dt>{t("Phase / iteration", "Fase / iteración")}</dt><dd>{h.phase} / {h.inner_iteration}</dd><dt>β</dt><dd>{f(h.beta)}</dd><dt>φd / φm / F</dt><dd>{f(h.phi_d)} / {f(h.phi_regularizer)} / {f(h.objective)}</dd><dt>{t("Projected gradient", "Gradiente proyectado")}</dt><dd>{f(h.kkt_inf)}</dd></dl>
    {frame(t("Recorded objective history", "Historial de objetivo registrado"),value.history.map((state,i)=>{const max=Math.max(1,...value.history.map(s=>s.objective));return <circle key={i} cx={45+610*i/Math.max(1,value.history.length-1)} cy={395-350*state.objective/max} r={historyIndex===i?5:2} className="magnetic-development" onPointerEnter={()=>setHistoryIndex(i)}/>;}))}
  </>:<p>{t("No iteration history.", "Sin historial de iteración.")}</p>}<p>{t("Different candidates and epsilon stages are distinct objectives; a joined history is not one monotone solve. No model states are invented between saved records.", "Candidatos y etapas epsilon son objetivos distintos; el historial no es una única resolución monótona. No se inventan estados entre registros guardados.")}</p></>;
  const spectral=<>{spectrum?frame(t("Uniform-flight residual power spectrum", "Espectro de potencia del residuo de vuelo uniforme"),<>
    <text x="240" y="440">{t("Frequency (cycles/m)", "Frecuencia (ciclos/m)")}</text><text x="8" y="25">nT² m</text>
    {spectrum.map((s,i)=>{const max=Math.max(1,...spectrum.map(p=>p.power_nT2_m));return <rect key={i} x={45+610*i/spectrum.length} y={395-350*s.power_nT2_m/max} width={Math.max(1,610/spectrum.length-2)} height={350*s.power_nT2_m/max} className="magnetic-development"><title>{f(s.frequency_cycles_per_m)} cycles/m · {f(s.power_nT2_m)} nT² m</title></rect>;})}
  </>):<p>{t("Unavailable: the complete selected line is irregular, has gaps or lacks residuals. No interpolation or subset spectrum.", "No disponible: la línea completa seleccionada es irregular, tiene brechas o carece de residuos. No se interpola ni usa un subconjunto.")}</p>}
    <p>{t("Demeaned Hann-window one-sided spectrum on original horizontal spacing. This display diagnostic does not change masks, fitting, noise estimates or held-out selection.", "Espectro unilateral con ventana Hann y media retirada sobre el espaciamiento horizontal original. Este diagnóstico visual no cambia máscaras, ajuste, estimación de ruido ni selección reservada.")}</p></>;
  return <section className="magnetic-result" data-generation={value.binding.generation_sha256} data-lane="local_replay">
    <p role="status">{t("Immutable local result replay. Not field acceptance, unique geology or admitted online execution.", "Reproducción de resultado local inmutable. No acredita campo, geología única ni ejecución en línea admitida.")}</p>
    <div className="magnetic-controls"><label>{t("Component", "Componente")}<select value={component} onChange={e=>setComponent(Number(e.target.value))}>{value.components.map((c,i)=><option key={c} value={i}>{c}</option>)}</select></label>
      <label>{t("Original acquisition group", "Grupo de adquisición original")}<select value={group} onChange={e=>{setGroup(e.target.value);setSelectedRow(value.rows.find(r=>r.group_id===e.target.value)!.row);}}>{[...new Set(value.rows.map(r=>r.group_id))].map(g=><option key={g}>{g}</option>)}</select></label>
      {onExport && <button type="button" onClick={onExport}>{t("Export verified numeric bundle", "Exportar bundle numérico verificado")}</button>}</div>
    <Tabs ariaLabel={t("Magnetic scientific views", "Vistas científicas magnéticas")} tabs={[
      {id:"observations",label:t("Observations", "Observaciones"),content:<SubTabs tabs={[{id:"map",label:t("Map","Mapa"),content:map},{id:"flight",label:t("Flight", "Vuelo"),content:line(false)},{id:"residual",label:t("Residual", "Residuo"),content:line(true)}]}/>},
      {id:"model",label:t("Susceptibility", "Susceptibilidad"),content:<SubTabs tabs={[{id:"volume",label:t("3D cells", "Celdas 3D"),content:model(false)},{id:"slice",label:t("Depth slice", "Corte en profundidad"),content:model(true)}]}/>},
      {id:"resolution",label:t("Resolution", "Resolución"),content:resolution},
      {id:"history",label:t("Iteration", "Iteración"),content:history},
      {id:"spectrum",label:t("Residual spectrum", "Espectro residual"),content:spectral}
    ]}/>
  </section>;
}
