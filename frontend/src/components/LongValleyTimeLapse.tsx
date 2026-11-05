import { useEffect, useMemo, useState } from "react";
import { PlotCard, useShellLang } from "@fasl-work/caos-app-shell";
import { appBase, color, format } from "../science";
import { differenceEpochs, parseLongValleyCase, type LongValleyCase, type LVStation } from "../api/long-valley";

const ARTIFACT = "data/field/long-valley/1982-06_to_1999-07.json";
const t = (es: boolean, en: string, sp: string) => es ? sp : en;

function MapPlot({ earlier, later, rows, selected, onSelect, es }: { earlier: string; later: string; rows: ReturnType<typeof differenceEpochs>; selected: string; onSelect: (id: string) => void; es: boolean }) {
  const W = 860, H = 500, pad = { l: 84, r: 24, t: 26, b: 68 };
  const xs = rows.map((r) => r.easting_m), ys = rows.map((r) => r.northing_m);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)], [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const scale = Math.min((W - pad.l - pad.r) / Math.max(x1 - x0, 1), (H - pad.t - pad.b) / Math.max(y1 - y0, 1));
  const mapW = (x1 - x0) * scale, mapH = (y1 - y0) * scale;
  const left = pad.l + ((W - pad.l - pad.r) - mapW) / 2, top = pad.t + ((H - pad.t - pad.b) - mapH) / 2;
  const X = (v: number) => left + (v - x0) * scale;
  const Y = (v: number) => top + (y1 - v) * scale;
  const limit = Math.max(...rows.map((r) => Math.abs(r.delta_gravity_mgal)), 0.001);
  return <PlotCard title={t(es, "Station network · observed epoch difference", "Red de estaciones · diferencia observada entre épocas")} lane="replay" provenance="real" note={`${earlier} → ${later} · ${rows.length} ${t(es,"paired stations","estaciones emparejadas")}`}>
    <svg className="lv-network-map" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t(es, "Map of actual Long Valley gravity stations coloured by observed change", "Mapa de estaciones gravimétricas reales de Long Valley coloreadas por cambio observado")}>
      {[0, 1, 2, 3, 4].map((i) => <g key={`g${i}`} className="chart-grid"><line x1={left + mapW * i / 4} x2={left + mapW * i / 4} y1={top} y2={top + mapH}/><line x1={left} x2={left + mapW} y1={top + mapH * i / 4} y2={top + mapH * i / 4}/></g>)}
      <rect x={left} y={top} width={mapW} height={mapH} fill="none" stroke="var(--color-border)"/>
      {rows.map((row) => <circle key={row.station_id} cx={X(row.easting_m)} cy={Y(row.northing_m)} r={row.station_id === selected ? 8 : 6.2} fill={color(row.delta_gravity_mgal, [-limit, limit], "field")} stroke={row.station_id === selected ? "var(--color-fg)" : "var(--color-surface)"} strokeWidth={row.station_id === selected ? 2.5 : 1.4} tabIndex={0} role="button" aria-label={`${row.station_id}: ${format(row.delta_gravity_mgal)} mGal`} onClick={() => onSelect(row.station_id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(row.station_id); } }}><title>{`${row.station_id} · Δg ${format(row.delta_gravity_mgal)} ± ${format(row.delta_sigma_independent_mgal)} mGal (independent-error assumption)`}</title></circle>)}
      {[0,1,2,3,4].map((i) => <g key={`tick${i}`}><text x={left + mapW * i / 4} y={top + mapH + 25} textAnchor="middle">{format(x0 + (x1-x0)*i/4)}</text><text x={left - 10} y={top + mapH - mapH*i/4 + 4} textAnchor="end">{format(y0 + (y1-y0)*i/4)}</text></g>)}
      <text x={left + mapW / 2} y={H - 15} textAnchor="middle">{t(es, "Easting (source UTM), m", "Este (UTM de origen), m")}</text>
      <text x={20} y={top + mapH/2} textAnchor="middle" transform={`rotate(-90 20 ${top + mapH/2})`}>{t(es, "Northing (source UTM), m", "Norte (UTM de origen), m")}</text>
      <path d={`M ${W-56} 88 L ${W-56} 50 M ${W-63} 60 L ${W-56} 50 L ${W-49} 60`} fill="none" stroke="var(--color-fg)" strokeWidth="2"/><text x={W-56} y={42} textAnchor="middle">N</text>
    </svg>
    <div className="scale-legend"><span>{format(-limit)} mGal</span><i style={{background:"linear-gradient(90deg,#234c74,#80abc4,#f4f2ed,#d79a6b,#923f28)"}}/><span>{format(limit)} mGal</span></div>
  </PlotCard>;
}

function StationHistory({ station, es, includeSuspect }: { station: LVStation | undefined; es: boolean; includeSuspect: boolean }) {
  const measurements=station?.measurements.filter((m)=>includeSuspect||m.qc?.status!=="suspect")??[];
  if (!station || measurements.length < 2) return <PlotCard title={t(es,"Selected-station record","Registro de estación seleccionada")} lane="replay" provenance="real"><p>{t(es,"Select a station with repeated occupations.","Seleccione una estación con ocupaciones repetidas.")}</p></PlotCard>;
  const W=760,H=340,pad={l:75,r:24,t:25,b:58};
  const base=measurements[0], values=measurements.map((m)=>m.gravity_mgal-base.gravity_mgal);
  const errors=measurements.map((m,i)=>i===0?0:Math.hypot(m.sigma_mgal,base.sigma_mgal));
  const lo=Math.min(...values.map((v,i)=>v-errors[i])), hi=Math.max(...values.map((v,i)=>v+errors[i]));
  const span=Math.max(hi-lo,1e-6), X=(i:number)=>pad.l+(W-pad.l-pad.r)*i/Math.max(1,values.length-1),Y=(v:number)=>pad.t+(H-pad.t-pad.b)*(hi-v)/span;
  const path=values.map((v,i)=>`${i?"L":"M"} ${X(i)} ${Y(v)}`).join(" ");
  return <PlotCard title={t(es,`Station ${station.station_id} · change from first occupation`,`Estación ${station.station_id} · cambio desde la primera ocupación`)} lane="replay" provenance="real" note={t(es,`Reference ${base.epoch} · gravity change and propagated 1σ`,`Referencia ${base.epoch} · cambio de gravedad y 1σ propagada`)}>
    <svg className="lv-history-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t(es,"Observed gravity time series relative to the first station occupation","Serie temporal de gravedad observada relativa a la primera ocupación de estación")}>
      {[0,1,2,3,4].map(i=>{const v=lo+(hi-lo)*i/4;return <g key={i} className="chart-grid"><line x1={pad.l} x2={W-pad.r} y1={Y(v)} y2={Y(v)}/><text x={pad.l-10} y={Y(v)+4} textAnchor="end">{format(v)}</text></g>})}
      <path d={path} fill="none" stroke="var(--color-accent)" strokeWidth="2.5"/>
      {values.map((v,i)=><g key={measurements[i].epoch}><line x1={X(i)} x2={X(i)} y1={Y(v-errors[i])} y2={Y(v+errors[i])} stroke="var(--color-fg)" strokeWidth="1.5"/><line x1={X(i)-4} x2={X(i)+4} y1={Y(v-errors[i])} y2={Y(v-errors[i])} stroke="var(--color-fg)"/><line x1={X(i)-4} x2={X(i)+4} y1={Y(v+errors[i])} y2={Y(v+errors[i])} stroke="var(--color-fg)"/><circle cx={X(i)} cy={Y(v)} r="4.5" fill="var(--color-accent)"><title>{`${measurements[i].epoch} · Δg ${format(v)} ± ${format(errors[i])} mGal${measurements[i].qc?.status==="suspect"?" · suspect source observation":""}`}</title></circle><text x={X(i)} y={H-25} textAnchor="middle">{measurements[i].epoch.slice(0,7)}</text></g>)}
      <text x={W/2} y={H-5} textAnchor="middle">{t(es,"Occupation epoch","Época de ocupación")}</text><text x={20} y={H/2} textAnchor="middle" transform={`rotate(-90 20 ${H/2})`}>Δg (mGal)</text>
    </svg>
  </PlotCard>;
}

export function LongValleyTimeLapse() {
  const es=useShellLang()==="es";
  const [data,setData]=useState<LongValleyCase>(); const [error,setError]=useState("");
  const [earlier,setEarlier]=useState("1982-06"); const [later,setLater]=useState("1999-07"); const [selected,setSelected]=useState("12DOR75"); const [includeSuspect,setIncludeSuspect]=useState(false);
  useEffect(()=>{const c=new AbortController();fetch(`${appBase}${ARTIFACT}`,{signal:c.signal,cache:"force-cache"}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json() as Promise<unknown>}).then(v=>setData(parseLongValleyCase(v))).catch(e=>{if(e.name!=="AbortError")setError(String(e))});return()=>c.abort()},[]);
  const rows=useMemo(()=>data?differenceEpochs(data,earlier,later,includeSuspect):[],[data,earlier,later,includeSuspect]);
  useEffect(()=>{if(rows.length&&!rows.some(r=>r.station_id===selected))setSelected(rows[0].station_id)},[rows,selected]);
  if(error)return <p role="alert">{t(es,"Field archive could not be loaded: ","No se pudo cargar el archivo de campo: ")}{error}</p>;
  if(!data)return <p role="status">{t(es,"Loading the source-bound station archive…","Cargando el archivo de estaciones con identidad de origen…")}</p>;
  const flaggedGravity = new Intl.NumberFormat(es ? "es-CL" : "en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(979255.21);
  const station=data.stations.find(s=>s.station_id===selected);
  const min=Math.min(...rows.map(r=>r.delta_gravity_mgal)),max=Math.max(...rows.map(r=>r.delta_gravity_mgal));
  return <section className="lv-study" aria-labelledby="long-valley-title">
    <header><h2 id="long-valley-title">{t(es,"Long Valley · repeated-station gravity observations","Long Valley · observaciones gravimétricas repetidas por estación")}</h2><p>{t(es,"A real monitoring network with 37 stations and eight occupations from 1980–1999. Select the epoch pair; the station map and uncertainty-weighted differences update from the archived measurements.","Red real de monitoreo con 37 estaciones y ocho ocupaciones entre 1980–1999. Elija el par de épocas; el mapa y las diferencias con incertidumbre se actualizan desde las mediciones archivadas.")}</p></header>
    <div className="lv-controls">
      <label className="select-control"><span>{t(es,"Earlier occupation A","Ocupación anterior A")}</span><select className="select" value={earlier} onChange={e=>setEarlier(e.target.value)}>{data.epochs.filter(e=>e!==later).map(e=><option key={e}>{e}</option>)}</select></label>
      <label className="select-control"><span>{t(es,"Later occupation B","Ocupación posterior B")}</span><select className="select" value={later} onChange={e=>setLater(e.target.value)}>{data.epochs.filter(e=>e!==earlier).map(e=><option key={e}>{e}</option>)}</select></label>
      <label className="select-control lv-qc-toggle"><span>{t(es,"Quality control","Control de calidad")}</span><span><input type="checkbox" checked={includeSuspect} onChange={e=>setIncludeSuspect(e.target.checked)}/> {t(es,"Include flagged observations","Incluir mediciones marcadas")}</span></label>
      <div className="lv-stat"><span>{t(es,"Paired stations","Estaciones emparejadas")}</span><strong>{rows.length} / {data.station_count}</strong></div><div className="lv-stat"><span>{t(es,"Observed Δg range","Rango observado de Δg")}</span><strong>{format(min)} to {format(max)} mGal</strong></div>
    </div>
    <aside className="lv-qc-notice" role="note"><strong>{t(es,"Source quality flag · unresolved","Alerta de calidad de fuente · sin resolver")}</strong><p>{t(es,`The archived 1JD1952 reading (1982-09: ${flaggedGravity} mGal) exactly matches 1JCM1952 in this table and conflicts with adjacent 1JD1952 occupations. It is preserved unchanged and omitted from the default pair calculation. Turn on the checkbox to inspect the flagged value.`,`La lectura archivada de 1JD1952 (1982-09: ${flaggedGravity} mGal) coincide exactamente con 1JCM1952 en esta tabla y difiere de las ocupaciones adyacentes de 1JD1952. Se conserva sin cambios y se excluye del cálculo predeterminado. Active la casilla para inspeccionar el dato marcado.`)}</p><a href="https://pubs.usgs.gov/of/1987/0077/report.pdf" target="_blank" rel="noreferrer">USGS Open-File Report 87-77 (station values, Table 3)</a></aside>
    {rows.length ? <div className="lv-chart-grid"><MapPlot earlier={earlier} later={later} rows={rows} selected={selected} onSelect={setSelected} es={es}/><StationHistory station={station} es={es} includeSuspect={includeSuspect}/></div> : <p role="status">{t(es,"These occupations have no stations with both measurements and uncertainties. Choose another pair.","Estas ocupaciones no comparten estaciones con mediciones e incertidumbres. Elija otro par.")}</p>}
    <details className="lv-record"><summary>{t(es,"Inspect paired station values and propagated uncertainty","Inspeccionar valores emparejados e incertidumbre propagada")}</summary><div className="table-scroll"><table className="cmp-table"><thead><tr><th>{t(es,"Station","Estación")}</th><th>A (mGal)</th><th>σA (mGal)</th><th>B (mGal)</th><th>σB (mGal)</th><th>Δg B−A (mGal)</th><th>σΔ independent (mGal)</th><th>Δg / σΔ</th><th>{t(es,"Source QC","CC fuente")}</th></tr></thead><tbody>{rows.map(r=>{const flagged=data.stations.find(s=>s.station_id===r.station_id)?.measurements.some(m=>(m.epoch===earlier||m.epoch===later)&&m.qc?.status==="suspect");return <tr key={r.station_id}><td><button className="btn btn-small" type="button" onClick={()=>setSelected(r.station_id)}>{r.station_id}</button></td><td>{format(r.earlier_gravity_mgal)}</td><td>{format(r.earlier_sigma_mgal)}</td><td>{format(r.later_gravity_mgal)}</td><td>{format(r.later_sigma_mgal)}</td><td>{format(r.delta_gravity_mgal)}</td><td>{format(r.delta_sigma_independent_mgal)}</td><td>{format(r.standardized_delta_independent)}</td><td>{flagged?t(es,"Suspect · unresolved","Sospechoso · sin resolver"):t(es,"No flag","Sin alerta")}</td></tr>})}</tbody></table></div></details>
    <div className="lv-notes"><p><strong>{t(es,"Processing boundary","Límite del procesamiento")}:</strong> {data.observation_contract.processing_history}. {t(es,"The plotted epoch differences are not corrected for elevation change, hydrologic effects, or covariance between occupations. UTM coordinates and the datum are source-reported; the display does not reproject or interpolate the station data.","Las diferencias entre épocas no corrigen cambios de elevación, efectos hidrológicos ni covarianza entre ocupaciones. Coordenadas UTM y datum se informan según la fuente; la vista no reproyecta ni interpola estaciones.")}</p><p><a href={data.source.data_url} target="_blank" rel="noreferrer">{t(es,"USGS source table","Tabla fuente USGS")}</a> · <a href={data.source.format_metadata_url} target="_blank" rel="noreferrer">{t(es,"Format, units and frame","Formato, unidades y marco")}</a> · <a href={data.source.fgdc_metadata_url} target="_blank" rel="noreferrer">FGDC</a> · <a href={`${appBase}${ARTIFACT}`} download>{t(es,"Download prepared source-bound data","Descargar datos preparados con origen vinculado")}</a></p><p className="lv-hash">SHA-256 {data.source.source_sha256} · {data.source.attribution}</p></div>
  </section>;
}
