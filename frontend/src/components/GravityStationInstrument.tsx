import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import type { FlagResult, GravityDataset } from "../api/processing-contracts";
import { downloadInspection, gravityInspection } from "./result-view-data";

type Bounds = { x0: number; x1: number; y0: number; y1: number };
type Kind = "plan" | "observations" | "scores";
const value = (number: number) => number.toLocaleString("en-US", { maximumSignificantDigits: 7, useGrouping: false });
const range = (values: number[]) => {
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min;
  const pad = span > 0 ? Math.max(span * 0.06, Math.max(Math.abs(min), Math.abs(max)) * Number.EPSILON * 16) : Math.max(Math.abs(min) * 1e-6, 1);
  return [min - pad, max + pad];
};

function StationPlot({ kind, dataset, result, selected, onSelect, es }: {
  kind: Kind; dataset: GravityDataset; result: FlagResult | null;
  selected: number; onSelect: (index: number) => void; es: boolean;
}) {
  const t = (en: string, sp: string) => es ? sp : en;
  const figure = useRef<HTMLElement>(null), svg = useRef<SVGSVGElement>(null);
  const [size, setSize] = useState({ width: 640, height: 420 });
  const [bounds, setBounds] = useState<Bounds | null>(null);
  const [gesture, setGesture] = useState<"brush" | "pan">("brush");
  const drag = useRef<{ x: number; y: number; bounds: Bounds } | null>(null);
  const [brush, setBrush] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const left = 72, right = size.width - 18, top = 28, bottom = size.height - 50;
  const width = right - left, height = bottom - top;
  useEffect(() => {
    const element = figure.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setSize({ width: Math.max(300, element.clientWidth - 16), height: Math.max(270, element.clientHeight - 94) }));
    observer.observe(element); return () => observer.disconnect();
  }, []);
  const points = useMemo(() => dataset.station_ids.map((_, i) => ({
    x: kind === "plan" ? dataset.xyz_m[i][0] : i + 1,
    y: kind === "plan" ? dataset.xyz_m[i][1] : kind === "scores" ? result?.robust_score[i] ?? 0 : dataset.observed_mgal[i],
    sigma: kind === "observations" ? dataset.sigma_mgal[i] : 0,
  })), [kind, dataset, result]);
  const initial = useMemo(() => {
    let [x0, x1] = range(points.map(point => point.x));
    let [y0, y1] = range(points.flatMap(point => [point.y - point.sigma, point.y + point.sigma]));
    if (kind === "scores" && result) { y0 = Math.min(0, y0); y1 = Math.max(y1, result.parameters.threshold * 1.1); }
    if (kind === "plan") {
      const scale = Math.max((x1 - x0) / width, (y1 - y0) / height);
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      x0 = cx - width * scale / 2; x1 = cx + width * scale / 2;
      y0 = cy - height * scale / 2; y1 = cy + height * scale / 2;
    }
    return { x0, x1, y0, y1 };
  }, [points, kind, result, width, height]);
  let view = bounds ?? initial;
  if (kind === "plan" && bounds) {
    const scale = Math.max((bounds.x1 - bounds.x0) / width, (bounds.y1 - bounds.y0) / height);
    const cx = (bounds.x0 + bounds.x1) / 2, cy = (bounds.y0 + bounds.y1) / 2;
    view = {x0: cx - width * scale / 2, x1: cx + width * scale / 2, y0: cy - height * scale / 2, y1: cy + height * scale / 2};
  }
  const px = (x: number) => left + (x - view.x0) / (view.x1 - view.x0) * width;
  const py = (y: number) => bottom - (y - view.y0) / (view.y1 - view.y0) * height;
  const zoom = (factor: number, cx = (view.x0 + view.x1) / 2, cy = (view.y0 + view.y1) / 2) => {
    const next = { x0: cx + (view.x0 - cx) * factor, x1: cx + (view.x1 - cx) * factor, y0: cy + (view.y0 - cy) * factor, y1: cy + (view.y1 - cy) * factor };
    if (Object.values(next).every(Number.isFinite) && next.x1 - next.x0 > 1e-10 && next.y1 - next.y0 > 1e-10) setBounds(next);
  };
  useEffect(() => { setBounds(null); setBrush(null); drag.current = null; }, [dataset.dataset_id, result?.job_id, kind]);
  useEffect(() => {
    const node = svg.current;
    if (!node) return;
    const wheel = (event: WheelEvent) => { event.preventDefault(); zoom(event.deltaY > 0 ? 1.2 : 1 / 1.2); };
    node.addEventListener("wheel", wheel, { passive: false });
    return () => node.removeEventListener("wheel", wheel);
  });
  const location = (event: PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return { x: Math.max(left, Math.min(right, (event.clientX - rect.left) / rect.width * size.width)), y: Math.max(top, Math.min(bottom, (event.clientY - rect.top) / rect.height * size.height)) };
  };
  const nearest = (x: number, y: number) => {
    let best = selected, distance = Infinity;
    points.forEach((point, i) => {
      const dx = px(point.x) - x, dy = kind === "plan" ? py(point.y) - y : 0;
      if (point.x < view.x0 || point.x > view.x1 || point.y < view.y0 || point.y > view.y1) return;
      const candidate = dx * dx + dy * dy;
      if (candidate < distance) { distance = candidate; best = i; }
    });
    onSelect(best);
  };
  const move = (event: PointerEvent<SVGSVGElement>) => {
    const pointer = location(event), start = drag.current;
    if (!start) { nearest(pointer.x, pointer.y); return; }
    if (gesture === "brush") setBrush({ x: Math.min(start.x, pointer.x), y: Math.min(start.y, pointer.y), width: Math.abs(pointer.x - start.x), height: Math.abs(pointer.y - start.y) });
    else {
      const dx = (start.x - pointer.x) / width * (start.bounds.x1 - start.bounds.x0), dy = (pointer.y - start.y) / height * (start.bounds.y1 - start.bounds.y0);
      setBounds({ x0: start.bounds.x0 + dx, x1: start.bounds.x1 + dx, y0: start.bounds.y0 + dy, y1: start.bounds.y1 + dy });
    }
  };
  const finish = (event: PointerEvent<SVGSVGElement>) => {
    const pointer = location(event), start = drag.current;
    if (start && gesture === "brush" && Math.abs(pointer.x - start.x) > 6 && Math.abs(pointer.y - start.y) > 6) {
      const dx = (pixel: number) => start.bounds.x0 + (pixel - left) / width * (start.bounds.x1 - start.bounds.x0);
      const dy = (pixel: number) => start.bounds.y1 - (pixel - top) / height * (start.bounds.y1 - start.bounds.y0);
      const next = { x0: dx(Math.min(start.x, pointer.x)), x1: dx(Math.max(start.x, pointer.x)), y0: dy(Math.max(start.y, pointer.y)), y1: dy(Math.min(start.y, pointer.y)) };
      if (kind === "plan") {
        const scale = Math.max((next.x1 - next.x0) / width, (next.y1 - next.y0) / height);
        const cx = (next.x0 + next.x1) / 2, cy = (next.y0 + next.y1) / 2;
        next.x0 = cx - width * scale / 2; next.x1 = cx + width * scale / 2;
        next.y0 = cy - height * scale / 2; next.y1 = cy + height * scale / 2;
      }
      setBounds(next);
    } else if (start && Math.hypot(pointer.x - start.x, pointer.y - start.y) < 6) nearest(pointer.x, pointer.y);
    drag.current = null; setBrush(null);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };
  const title = kind === "plan" ? t("Station geometry", "Geometría de estaciones") : kind === "scores" ? t("Robust QC scores", "Puntajes robustos QC") : t("Observed gravity and σ", "Gravedad observada y σ");
  const unit = kind === "plan" ? "m" : kind === "scores" ? "1" : "mGal";
  const clip = `station-clip-${kind}`;
  const visible = points.map((point, i) => ({ point, i })).filter(({point}) => point.x >= view.x0 && point.x <= view.x1 && point.y >= view.y0 && point.y <= view.y1);
  return <figure ref={figure} className="processing-plot">
    <figcaption><strong>{title}</strong><output>{dataset.station_ids[selected]} · {kind === "plan" ? `XY ${value(points[selected].x)}, ${value(points[selected].y)}` : value(points[selected].y)} {unit}</output></figcaption>
    <svg ref={svg} viewBox={`0 0 ${size.width} ${size.height}`} role="img" tabIndex={0} aria-label={title}
      onKeyDown={event => {
        if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "=", "-", "Home", "Escape"].includes(event.key)) event.preventDefault();
        if (["ArrowLeft", "ArrowDown"].includes(event.key)) onSelect(Math.max(0, selected - 1));
        if (["ArrowRight", "ArrowUp"].includes(event.key)) onSelect(Math.min(points.length - 1, selected + 1));
        if (["+", "="].includes(event.key)) zoom(1 / 1.5);
        if (event.key === "-") zoom(1.5);
        if (["Home", "Escape"].includes(event.key)) setBounds(null);
      }}
      onPointerDown={event => { if (event.button !== 0) return; const point = location(event); drag.current = { ...point, bounds: view }; event.currentTarget.setPointerCapture(event.pointerId); event.currentTarget.focus(); }}
      onPointerMove={move} onPointerUp={finish} onPointerCancel={() => { drag.current = null; setBrush(null); }} onDoubleClick={() => setBounds(null)}>
      <defs><clipPath id={clip}><rect x={left} y={top} width={width} height={height} /></clipPath></defs>
      {[0, 0.5, 1].map(fraction => <g key={fraction}>
        <line x1={left} x2={right} y1={top + fraction * height} y2={top + fraction * height} className="chart-grid" />
        <text x={left - 8} y={top + fraction * height + 4} textAnchor="end">{value(view.y1 - fraction * (view.y1 - view.y0))}</text>
        <text x={left + fraction * width} y={bottom + 20} textAnchor={fraction === 0 ? "start" : fraction === 1 ? "end" : "middle"}>{value(view.x0 + fraction * (view.x1 - view.x0))}</text>
      </g>)}
      <text x={(left + right) / 2} y={size.height - 7} textAnchor="middle">{kind === "plan" ? `X [m] · EPSG:${dataset.physical_metadata.epsg}` : t("Station order [1]", "Orden de estación [1]")}</text>
      <text transform={`translate(14 ${(top + bottom) / 2}) rotate(-90)`} textAnchor="middle">{kind === "plan" ? "Y [m]" : kind === "scores" ? t("Robust score [1]", "Puntaje robusto [1]") : "g ± σ [mGal]"}</text>
      <g clipPath={`url(#${clip})`}>
        {kind === "scores" && result && <line x1={left} x2={right} y1={py(result.parameters.threshold)} y2={py(result.parameters.threshold)} className="processing-threshold" />}
        {visible.map(({point, i}) => <g key={i} className={result?.outlier_flag[i] ? "processing-flagged" : "processing-station"}>
          {!!point.sigma && <line x1={px(point.x)} x2={px(point.x)} y1={py(point.y - point.sigma)} y2={py(point.y + point.sigma)} stroke="currentColor" />}
          {result?.outlier_flag[i] ? <path d={`M${px(point.x)},${py(point.y) - 5}l5,9h-10Z`} fill="currentColor" /> : <circle cx={px(point.x)} cy={py(point.y)} r={visible.length > 500 ? 2 : 3.5} fill="currentColor" />}
        </g>)}
        <line x1={px(points[selected].x)} x2={px(points[selected].x)} y1={top} y2={bottom} className="cursor-line" />
        <circle cx={px(points[selected].x)} cy={py(points[selected].y)} r="8" className="processing-selection" />
      </g>
      {brush && <rect {...brush} className="processing-brush" />}
    </svg>
    <div className="processing-view-controls">
      <button className="btn" aria-label={`${t("Zoom in", "Acercar")} · ${title}`} onClick={() => zoom(1 / 1.5)}>+</button>
      <button className="btn" aria-label={`${t("Zoom out", "Alejar")} · ${title}`} onClick={() => zoom(1.5)}>−</button>
      <button className="btn" onClick={() => setBounds(null)}>{t("Reset view", "Restablecer vista")}</button>
      <label><span>{t("Drag", "Arrastrar")}</span><select className="select" aria-label={`${t("Drag action", "Acción de arrastre")} · ${title}`} value={gesture} onChange={event => setGesture(event.target.value as "brush" | "pan")}>
        <option value="brush">{t("Zoom region", "Acercar región")}</option><option value="pan">{t("Pan", "Desplazar")}</option></select></label>
    </div>
  </figure>;
}

export function GravityStationInstrument({ dataset, result, es }: { dataset: GravityDataset; result: FlagResult | null; es: boolean }) {
  const t = (en: string, sp: string) => es ? sp : en;
  const [selected, setSelected] = useState(0), [showScores, setShowScores] = useState(false), [table, setTable] = useState(false);
  useEffect(() => { setSelected(0); setShowScores(false); }, [dataset.dataset_id]);
  const page = Math.floor(selected / 50), count = dataset.station_ids.length;
  return <div className="processing-instrument" data-testid="processing-instrument">
    <div className="processing-station-toolbar">
      <label className="select-control"><span>{t("Selected station", "Estación seleccionada")}</span><select className="select" value={selected} onChange={event => setSelected(Number(event.target.value))}>
        {dataset.station_ids.map((id, i) => <option key={id} value={i}>{id}{result?.outlier_flag[i] ? ` · ${t("flagged", "marcada")}` : ""}</option>)}</select></label>
      <label className="select-control"><span>{t("Measurement view", "Vista de medición")}</span><select className="select" value={showScores && result ? "scores" : "observations"} onChange={event => setShowScores(event.target.value === "scores")}>
        <option value="observations">{t("Observed gravity ± σ", "Gravedad observada ± σ")}</option><option value="scores" disabled={!result}>{t("Returned robust scores", "Puntajes robustos recibidos")}</option></select></label>
      <button className="btn" aria-pressed={table} onClick={() => setTable(!table)}>{table ? t("Show plots", "Mostrar gráficos") : t("Station table", "Tabla de estaciones")}</button>
      <button className="btn" onClick={() => downloadInspection(gravityInspection(dataset, result, selected), `gravity-inspection-${dataset.dataset_id}.json`)}>{t("Export exact inspection JSON", "Exportar inspección exacta JSON")}</button>
    </div>
    <output className="processing-station-readout" aria-live="polite" data-testid="station-readout">
      {dataset.station_ids[selected]} · XYZ {dataset.xyz_m[selected].map(String).join(", ")} m · g {String(dataset.observed_mgal[selected])} ± {String(dataset.sigma_mgal[selected])} mGal
      {result && ` · ${t("score", "puntaje")} ${String(result.robust_score[selected])} [1] · ${result.outlier_flag[selected] ? t("flagged", "marcada") : t("not flagged", "sin marca")}`}
    </output>
    {table ? <div className="processing-station-table">
      <div className="processing-view-controls"><button className="btn" disabled={page === 0} onClick={() => setSelected((page - 1) * 50)}>{t("Previous rows", "Filas anteriores")}</button><span>{page * 50 + 1}–{Math.min(count, (page + 1) * 50)} / {count}</span><button className="btn" disabled={(page + 1) * 50 >= count} onClick={() => setSelected((page + 1) * 50)}>{t("Next rows", "Filas siguientes")}</button></div>
      <table className="cmp-table"><caption>{t("Original observations and returned QC; no stations excluded", "Observaciones originales y QC recibido; sin excluir estaciones")}</caption>
        <thead><tr><th>{t("Station", "Estación")}</th><th>X [m]</th><th>Y [m]</th><th>Z [m]</th><th>g [mGal]</th><th>σ [mGal]</th><th>{t("Score [1]", "Puntaje [1]")}</th><th>{t("Flag", "Marca")}</th></tr></thead>
        <tbody>{dataset.station_ids.slice(page * 50, (page + 1) * 50).map((id, offset) => { const i = page * 50 + offset; return <tr key={id} aria-selected={selected === i}>
          <th><button className="btn" aria-pressed={selected === i} onClick={() => setSelected(i)}>{id}</button></th>{[...dataset.xyz_m[i], dataset.observed_mgal[i], dataset.sigma_mgal[i]].map((v, c) => <td key={c}>{String(v)}</td>)}<td>{result ? String(result.robust_score[i]) : t("n/a", "n/d")}</td><td>{result ? result.outlier_flag[i] ? t("Yes", "Sí") : t("No", "No") : t("n/a", "n/d")}</td></tr>; })}</tbody></table>
    </div> : <div className="processing-charts"><StationPlot kind="plan" dataset={dataset} result={result} selected={selected} onSelect={setSelected} es={es} /><StationPlot kind={showScores && result ? "scores" : "observations"} dataset={dataset} result={result} selected={selected} onSelect={setSelected} es={es} /></div>}
    <p className="plot-note">{t("Circles: stations. Triangles: returned statistical flags. Bars: declared ±1σ, not a model interval. Arrows select stations; +/− zoom; Home resets. Coordinates and observations are unchanged.", "Círculos: estaciones. Triángulos: marcas estadísticas recibidas. Barras: ±1σ declarada, no intervalo de modelo. Flechas seleccionan; +/− acercan; Inicio restablece. Coordenadas y observaciones sin cambios.")}</p>
  </div>;
}
