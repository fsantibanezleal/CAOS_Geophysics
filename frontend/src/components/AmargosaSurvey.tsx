import { useEffect, useMemo, useState } from "react";
import { Callout, PlotCard, useShellLang } from "@fasl-work/caos-app-shell";
import { appBase, color, format } from "../science";
import { parseAmargosaBytes, type AmargosaResult } from "../api/amargosa";
import { Legend } from "./ScientificPlots";
import fieldStudyIndex from "../data/field-study-index.json";

const ARTIFACT = "data/field/amargosa/amargosa-m03-20261111.json";
const t = (es: boolean, en: string, sp: string) => es ? sp : en;

function AmargosaMap({ data, display, es }: { data: AmargosaResult; display: "anomaly" | "support"; es: boolean }) {
  const width = 900, height = 560, pad = { left: 88, right: 28, top: 28, bottom: 72 };
  const x = data.grid.x_easting_m, y = data.grid.y_northing_m;
  const x0 = x[0], x1 = x[x.length - 1], y0 = y[0], y1 = y[y.length - 1];
  const scale = Math.min((width - pad.left - pad.right) / (x1 - x0), (height - pad.top - pad.bottom) / (y1 - y0));
  const mapWidth = (x1 - x0) * scale, mapHeight = (y1 - y0) * scale;
  const left = pad.left + ((width - pad.left - pad.right) - mapWidth) / 2;
  const top = pad.top + ((height - pad.top - pad.bottom) - mapHeight) / 2;
  const X = (value: number) => left + (value - x0) * scale;
  const Y = (value: number) => top + (y1 - value) * scale;
  const dx = x.length > 1 ? (x[1] - x[0]) * scale : 0;
  const dy = y.length > 1 ? (y[1] - y[0]) * scale : 0;
  const supportedValues = data.grid.values.flatMap((row, rowIndex) => row.filter((_, columnIndex) => data.grid.support_mask[rowIndex][columnIndex]));
  const minimum = Math.min(...supportedValues), maximum = Math.max(...supportedValues);
  const range: [number, number] = minimum === maximum ? [minimum - .5, maximum + .5] : [minimum, maximum];
  const lines = useMemo(() => data.source_selection.tracks.map((track) => ({
    track,
    geometry: data.geometry_qc.lines.find((line) => line.line_id === track.track_id)!,
  })), [data]);

  return <PlotCard title={t(es, display === "anomaly" ? "Levelled magnetic anomaly · 100 m grid" : "Supported interpolation cells · flight lines only", display === "anomaly" ? "Anomalía magnética nivelada · grilla de 100 m" : "Celdas soportadas · solo líneas de vuelo")} lane="replay" provenance="real" note={t(es, "USGS measured survey · NAD27 / UTM 11N · projected metres", "Levantamiento medido USGS · NAD27 / UTM 11N · metros proyectados")}>
    <svg className="amargosa-map" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t(es, display === "anomaly" ? "Measured Amargosa levelled magnetic anomaly grid and flight lines" : "Amargosa interpolation support and survey lines", display === "anomaly" ? "Grilla medida de anomalía magnética nivelada de Amargosa y líneas de vuelo" : "Soporte de interpolación de Amargosa y líneas de levantamiento")}>
      {[0, 1, 2, 3, 4].map((step) => <g key={`grid-${step}`} className="chart-grid"><line x1={left + mapWidth * step / 4} x2={left + mapWidth * step / 4} y1={top} y2={top + mapHeight}/><line x1={left} x2={left + mapWidth} y1={top + mapHeight * step / 4} y2={top + mapHeight * step / 4}/></g>)}
      {display === "anomaly" && data.grid.values.flatMap((row, rowIndex) => row.map((value, columnIndex) => {
        if (!data.grid.support_mask[rowIndex][columnIndex]) return null;
        return <rect key={`cell-${rowIndex}-${columnIndex}`} x={X(x[columnIndex]) - dx / 2} y={Y(y[rowIndex]) - dy / 2} width={dx + .2} height={dy + .2} fill={color(value, range, "field")}><title>{`${format(x[columnIndex])} E, ${format(y[rowIndex])} N · ${format(value)} nT`}</title></rect>;
      }))}
      {display === "support" && data.grid.support_mask.flatMap((row, rowIndex) => row.map((supported, columnIndex) => supported
        ? <rect key={`support-${rowIndex}-${columnIndex}`} x={X(x[columnIndex]) - dx / 2} y={Y(y[rowIndex]) - dy / 2} width={dx + .2} height={dy + .2} fill="var(--color-accent)" opacity=".62"/>
        : null))}
      <rect x={left} y={top} width={mapWidth} height={mapHeight} fill="none" stroke="var(--color-border)"/>
      {lines.map(({ track, geometry }) => {
        const east = geometry.coordinate_extent_m.easting, north = geometry.coordinate_extent_m.northing;
        const flight = track.role === "flight";
        return <g key={track.track_id} className={flight ? "amargosa-flight" : "amargosa-tie"}><line x1={X(east[0])} x2={X(east[1])} y1={Y(north[0])} y2={Y(north[1])} strokeWidth={flight ? 2.4 : 2.2} strokeDasharray={flight ? undefined : "6 4"}><title>{`${track.track_id} · ${track.role} · ${track.representative_source_line_id} · ${track.representative_sample_count} ${t(es,"samples","muestras")}`}</title></line></g>;
      })}
      {[0,1,2,3,4].map((step) => <g key={`tick-${step}`} fill="var(--color-fg-subtle)"><text x={left + mapWidth * step / 4} y={top + mapHeight + 25} textAnchor="middle">{format(x0 + (x1-x0)*step/4)}</text><text x={left - 10} y={top + mapHeight - mapHeight*step/4 + 4} textAnchor="end">{format(y0 + (y1-y0)*step/4)}</text></g>)}
      <text x={left + mapWidth / 2} y={height - 18} textAnchor="middle" fill="var(--color-fg)">{t(es, "Easting, m", "Este, m")}</text>
      <text x={18} y={top + mapHeight / 2} textAnchor="middle" transform={`rotate(-90 18 ${top + mapHeight / 2})`} fill="var(--color-fg)">{t(es, "Northing, m", "Norte, m")}</text>
    </svg>
    {display === "anomaly" && <><Legend range={range} unit="nT" palette="field"/><p className="amargosa-range-note">{t(es, "Full supported-cell range; no color clipping.", "Rango completo de celdas soportadas; sin recorte de color.")}</p></>}
    <div className="amargosa-line-legend"><span><i className="amargosa-flight-key"/> {t(es,"Flight tracks","Líneas de vuelo")} · {data.source_selection.track_count.flight}</span><span><i className="amargosa-tie-key"/> {t(es,"Tie tracks (QC only)","Líneas de amarre (solo QC)")} · {data.source_selection.track_count.tie}</span></div>
  </PlotCard>;
}

export function AmargosaSurvey() {
  const es = useShellLang() === "es";
  const [data, setData] = useState<AmargosaResult>();
  const [error, setError] = useState("");
  const [display, setDisplay] = useState<"anomaly" | "support">("anomaly");
  useEffect(() => {
    const controller = new AbortController();
    const pin = fieldStudyIndex.artifacts.find((artifact) => artifact.path === "amargosa/amargosa-m03-20261111.json");
    if (!pin) { setError("Amargosa artifact is absent from the reviewed field-study index."); return () => controller.abort(); }
    fetch(`${appBase}${ARTIFACT}`, { signal: controller.signal, cache: "force-cache" })
      .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.arrayBuffer(); })
      .then((bytes) => parseAmargosaBytes(bytes, pin.sha256))
      .then(setData)
      .catch((cause: unknown) => { if (!(cause instanceof Error && cause.name === "AbortError")) setError(String(cause)); });
    return () => controller.abort();
  }, []);
  if (error) return <p role="alert">{t(es, "Amargosa source-bound result could not be loaded: ", "No se pudo cargar el resultado de Amargosa con procedencia: ")}{error}</p>;
  if (!data) return <p role="status">{t(es, "Loading the verified USGS survey result…", "Cargando el resultado verificado del levantamiento USGS…")}</p>;
  const supported = data.grid.support_mask.flat().filter(Boolean).length;
  const score = data.heldout_interpolation;
  return <section className="amargosa-study" aria-labelledby="amargosa-title">
    <header><h2 id="amargosa-title">{t(es, "Amargosa Desert · measured aeromagnetic survey", "Desierto de Amargosa · levantamiento aeromagnético medido")}</h2><p>{t(es, "A pinned USGS field archive processed through the M03 flight-line contract. The view shows the provider-levelled anomaly and the footprint used for a whole-line spatial holdout.", "Un archivo de campo USGS fijado y procesado con el contrato M03 de líneas de vuelo. La vista muestra la anomalía nivelada por el proveedor y la cobertura usada en una reserva espacial de líneas completas.")}</p></header>
    <div className="amargosa-controls" role="group" aria-label={t(es, "Displayed quantity", "Magnitud mostrada")}>
      <button className="btn btn-small" type="button" aria-pressed={display === "anomaly"} onClick={() => setDisplay("anomaly")}>{t(es, "Levelled anomaly", "Anomalía nivelada")}</button>
      <button className="btn btn-small" type="button" aria-pressed={display === "support"} onClick={() => setDisplay("support")}>{t(es, "Interpolation support", "Soporte de interpolación")}</button>
    </div>
    <div className="amargosa-metrics"><div><span>{t(es,"Selected measurements","Mediciones seleccionadas")}</span><strong>{data.source_selection.tracks.reduce((sum, track) => sum + track.representative_sample_count, 0).toLocaleString()}</strong></div><div><span>{t(es,"Supported 100 m cells","Celdas soportadas a 100 m")}</span><strong>{supported.toLocaleString()}</strong></div><div><span>{t(es,"Whole flight lines held out","Líneas de vuelo reservadas")}</span><strong>{score.heldout_line_ids.length} · {score.heldout_row_count} {t(es,"samples","muestras")}</strong></div><div><span>{t(es,"Held-line RMSE","RMSE en líneas reservadas")}</span><strong>{format(score.rmse)} nT</strong></div></div>
    <div className="amargosa-plots"><AmargosaMap data={data} display={display} es={es}/><PlotCard title={t(es,"Held-out interpolation evidence","Evidencia de interpolación en líneas reservadas")} lane="replay" provenance="real" note={t(es,"Deterministic split by complete flight track", "Partición determinista por trayectoria de vuelo completa")}><dl className="amargosa-score"><dt>MAE</dt><dd>{format(score.mae)} nT</dd><dt>RMSE</dt><dd>{format(score.rmse)} nT</dd><dt>{t(es,"Coverage","Cobertura")}</dt><dd>{format(score.coverage_fraction * 100)}%</dd><dt>{t(es,"Held-out tracks","Trayectorias reservadas")}</dt><dd>{score.heldout_line_ids.join(", ")}</dd></dl><p>{t(es,"Scores measure spatial interpolation of this provider-processed survey patch. They do not measure subsurface recovery.","Las métricas evalúan interpolación espacial en este sector del levantamiento ya procesado por el proveedor. No miden recuperación del subsuelo.")}</p></PlotCard></div>
    <Callout variant="honest" title={t(es,"Processing boundary","Límite del procesamiento")}>{t(es,"The USGS levelled-anomaly channel is used as published. No diurnal or IGRF correction, crossover levelling, extrapolation outside the support hull, magnetic inversion or geological interpretation is applied here.","Se usa el canal de anomalía nivelada del USGS tal como fue publicado. Aquí no se aplican correcciones diurnas o IGRF, nivelación de cruces, extrapolación fuera del soporte, inversión magnética ni interpretación geológica.")}</Callout>
    <p className="amargosa-source"><a href="https://pubs.usgs.gov/of/2000/of00-188/" target="_blank" rel="noreferrer">USGS Open-File Report 00-188</a> · <a href={`${appBase}${ARTIFACT}`} download>{t(es,"Download processed result","Descargar resultado procesado")}</a> · <a href="https://pubs.usgs.gov/of/2000/of00-188/data/amargosa.xyz.gz" target="_blank" rel="noreferrer">{t(es,"Original 374,490-record archive","Archivo original de 374.490 registros")}</a></p>
    <p className="amargosa-hash">SHA-256 {data.source.sha256} · {data.source.citation}</p>
  </section>;
}
