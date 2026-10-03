import { useEffect, useId, useRef, useState } from "react";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { color, extent, format, type Palette } from "../science";
import { curvePath, intervalPath } from "../recovery";

export function Legend({
  range,
  unit,
  palette = "earth",
}: {
  range: [number, number];
  unit: string;
  palette?: Palette;
}) {
  return (
    <div className="scale-legend">
      <span>{format(range[0])}</span>
      <i
        style={{
          background: `linear-gradient(90deg,${Array.from({ length: 9 }, (_, i) => color(range[0] + (i * (range[1] - range[0])) / 8, range, palette)).join(",")})`,
        }}
      />
      <span>
        {format(range[1])} {unit}
      </span>
    </div>
  );
}

export function Heatmap({
  data,
  title,
  unit,
  xLabel,
  yLabel,
  palette = "field",
  range,
  xRange,
  yRange,
  xCoordinates,
  yCoordinates,
  onPick,
  markers = [],
  boundaries,
  cursorY,
}: {
  data: number[][];
  title: string;
  unit: string;
  xLabel: string;
  yLabel: string;
  palette?: Palette;
  range?: [number, number];
  xRange?: [number, number];
  yRange?: [number, number];
  xCoordinates?: number[];
  yCoordinates?: number[];
  onPick?: (x: number, y: number) => void;
  markers?: { x: number; y: number; label: string }[];
  boundaries?: number[][];
  cursorY?: number;
}) {
  const es = useShellLang() === "es";
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<{ x: number; y: number } | null>(null);
  const rows = data.length,
    cols = data[0]?.length ?? 0;
  const bounds = range ?? extent(data.flat());
  useEffect(() => {
    const c = canvas.current;
    if (!c || !rows || !cols) return;
    const ctx = c.getContext("2d")!;
    const source = document.createElement("canvas");
    source.width = cols;
    source.height = rows;
    const pixels = source.getContext("2d")!;
    c.width = cols * 8;
    c.height = rows * 8;
    for (let y = 0; y < rows; y++)
      for (let x = 0; x < cols; x++) {
        pixels.fillStyle = color(data[y][x], bounds, palette);
        pixels.fillRect(x, y, 1, 1);
      }
    // Each raster pixel is an exported sample; do not interpolate fake resolution.
    ctx.imageSmoothingEnabled = false;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(source, 0, 0, c.width, c.height);
  }, [data, palette, bounds[0], bounds[1], rows, cols]);
  const xv = hover
    ? (xCoordinates?.[hover.x] ??
      (xRange?.[0] ?? 0) +
        ((hover.x + 0.5) / cols) * ((xRange?.[1] ?? cols) - (xRange?.[0] ?? 0)))
    : 0;
  const yv = hover
    ? (yCoordinates?.[hover.y] ??
      (yRange?.[0] ?? 0) +
        ((hover.y + 0.5) / rows) * ((yRange?.[1] ?? rows) - (yRange?.[0] ?? 0)))
    : 0;
  return (
    <figure className="science-plot heatmap">
      <figcaption>
        <span>{title}</span>
        <output>
          {hover ? `${format(data[hover.y]?.[hover.x])} ${unit}` : unit}
        </output>
      </figcaption>
      <div className="heatmap-axes">
        <span className="axis-y">{yLabel}</span>
        <div
          className="heatmap-area"
          onPointerMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            setHover({
              x: Math.min(
                cols - 1,
                Math.max(
                  0,
                  Math.floor(((e.clientX - r.left) / r.width) * cols),
                ),
              ),
              y: Math.min(
                rows - 1,
                Math.max(
                  0,
                  Math.floor(((e.clientY - r.top) / r.height) * rows),
                ),
              ),
            });
          }}
          onPointerLeave={() => setHover(null)}
          onClick={() => {
            if (hover) onPick?.(hover.x, hover.y);
          }}
        >
          <canvas ref={canvas} aria-label={title} />
          {boundaries && (
            <svg
              className="geology-overlay"
              viewBox={`0 0 ${cols} ${rows}`}
              preserveAspectRatio="none"
              aria-label={
                es
                  ? "Interfaces geológicas conocidas"
                  : "Known geological interfaces"
              }
            >
              {boundaries.flatMap((row, y) =>
                row.flatMap((v, x) => {
                  const lines = [];
                  if (y && Math.abs(v - boundaries[y - 1][x]) > 200)
                    lines.push(
                      <line
                        key={`h${y}-${x}`}
                        x1={x}
                        x2={x + 1}
                        y1={y}
                        y2={y}
                      />,
                    );
                  if (x && Math.abs(v - row[x - 1]) > 200)
                    lines.push(
                      <line
                        key={`v${y}-${x}`}
                        x1={x}
                        x2={x}
                        y1={y}
                        y2={y + 1}
                      />,
                    );
                  return lines;
                }),
              )}
            </svg>
          )}
          {cursorY !== undefined && (
            <i
              className="time-cursor"
              style={{ top: `${Math.min(1, cursorY) * 100}%` }}
            />
          )}
          {hover && (
            <>
              <i
                className="crosshair-v"
                style={{ left: `${((hover.x + 0.5) / cols) * 100}%` }}
              />
              <i
                className="crosshair-h"
                style={{ top: `${((hover.y + 0.5) / rows) * 100}%` }}
              />
              <span className="plot-readout">
                {format(xv)}, {format(yv)}
              </span>
            </>
          )}
          {markers.map((m, i) => (
            <span
              className="map-marker"
              key={i}
              style={{ left: `${m.x * 100}%`, top: `${m.y * 100}%` }}
            >
              {m.label}
            </span>
          ))}
        </div>
      </div>
      <div className="axis-x">
        <span>{format(xRange?.[0] ?? 0)}</span>
        {xLabel}
        <span>{format(xRange?.[1] ?? cols)}</span>
      </div>
      <Legend range={bounds} unit={unit} palette={palette} />
    </figure>
  );
}

export type Series = {
  name: string;
  values: number[];
  color?: string;
  dashed?: boolean;
  points?: boolean;
  errors?: number[];
};
export type Band = { name: string; lower: number[]; upper: number[] };

/** Prevent floating-point differences in near-constant curves from filling the plot. */
export function plotYRange(values: number[], logY: boolean): [number, number] {
  const finite = values.filter(Number.isFinite).map(v => logY ? Math.log10(Math.max(v, 1e-20)) : v);
  if (!finite.length) return [0, 1];
  const low = Math.min(...finite), high = Math.max(...finite);
  const centre = (low + high) / 2;
  const minimumSpan = logY ? 2 * Math.log10(1.05) : 0.1 * (Math.max(Math.abs(low), Math.abs(high)) || 1);
  const span = Math.max(high - low, minimumSpan);
  const padding = span * 0.08;
  return [centre - span / 2 - padding, centre + span / 2 + padding];
}

export function Plot({
  x,
  series,
  title,
  xLabel,
  yLabel,
  logX = false,
  logY = false,
  band,
  interactive = false,
  selectedIndex,
  onSelect,
  viewport,
  onViewport,
  zeroCentered = false,
  fixedYRange,
  pointLabels,
}: {
  x: number[];
  series: Series[];
  title: string;
  xLabel: string;
  yLabel: string;
  logX?: boolean;
  logY?: boolean;
  band?: Band;
  interactive?: boolean;
  selectedIndex?: number;
  onSelect?: (index: number) => void;
  /** Domain in transformed x coordinates (log10 where logX). */
  viewport?: [number, number] | null;
  onViewport?: (range: [number, number] | null) => void;
  zeroCentered?: boolean;
  fixedYRange?: [number, number];
  pointLabels?: string[];
}) {
  const es = useShellLang() === "es", t=(en:string,sp:string)=>es?sp:en;
  const [localPick, setPick] = useState<number | null>(null), pick=selectedIndex??localPick;
  const [localViewport,setViewport]=useState<[number,number]|null>(null), [mode,setMode]=useState("brush");
  const [drag,setDrag]=useState<{start:number;end:number;range:[number,number]}|null>(null);
  const pointers=useRef(new Map<number,number>()), pinch=useRef<{distance:number;range:[number,number]}|null>(null);
  const clipId=useId().replace(/:/g,""), choose=(i:number)=>{setPick(i);onSelect?.(i);};
  const change=(range:[number,number]|null)=>{if(onViewport)onViewport(range);else setViewport(range);};
  const svgRef = useRef<SVGSVGElement>(null);
  const [w, setWidth] = useState(640);
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const update = () => {
      const next = Math.max(280, Math.round(svg.getBoundingClientRect().width));
      setWidth(current => current === next ? current : next);
    };
    const observer = new ResizeObserver(update);
    observer.observe(svg);
    update();
    return () => observer.disconnect();
  }, []);
  const h = 300,
    p = { l: 78, r: 22, t: 26, b: 46 };
  const ticks = w < 480 ? 4 : 5;
  const tx = (v: number) => (logX ? Math.log10(Math.max(v, 1e-20)) : v),
    ty = (v: number) => (logY ? Math.log10(Math.max(v, 1e-20)) : v);
  const full=extent(x.map(tx)), xr=viewport??localViewport??full;
  const values=[...series.flatMap(s=>s.errors?s.values.flatMap((v,i)=>[v-s.errors![i],v+s.errors![i]]):s.values),...(band?[...band.lower,...band.upper]:[])];
  const magnitude=Math.max(1e-20,...values.filter(Number.isFinite).map(Math.abs));
  const yr=fixedYRange??(zeroCentered?[-magnitude*1.08,magnitude*1.08] as [number,number]:plotYRange(values,logY));
  const X = (v: number) =>
      p.l + ((tx(v) - xr[0]) / (xr[1] - xr[0])) * (w - p.l - p.r),
    Y = (v: number) =>
      h - p.b - ((ty(v) - yr[0]) / (yr[1] - yr[0])) * (h - p.b - p.t);
  const hues = [
    "var(--color-accent)",
    "var(--color-accent-2)",
    "var(--color-magenta)",
  ];
  const px=(client:number)=>{const r=svgRef.current!.getBoundingClientRect();return Math.max(p.l,Math.min(w-p.r,(client-r.left)/r.width*w));};
  const coordinate=(u:number)=>xr[0]+(u-p.l)/(w-p.l-p.r)*(xr[1]-xr[0]);
  const nearest=(u:number)=>{let near=0; for(let i=1;i<x.length;i++)if(Math.abs(X(x[i])-u)<Math.abs(X(x[near])-u))near=i;return near;};
  const zoom=(factor:number,centre=(xr[0]+xr[1])/2)=>change([centre+(xr[0]-centre)*factor,centre+(xr[1]-centre)*factor]);
  useEffect(()=>{
    if(!interactive||!svgRef.current)return; const svg=svgRef.current;
    const wheel=(event:WheelEvent)=>{event.preventDefault();zoom(event.deltaY>0?1.25:.8,coordinate(px(event.clientX)));};
    svg.addEventListener("wheel",wheel,{passive:false});return()=>svg.removeEventListener("wheel",wheel);
  },[interactive,xr[0],xr[1],w,onViewport]);
  return (
    <figure className={`science-plot curve ${interactive ? "analytical-curve" : ""}`}>
      <figcaption>
        {title}
        <output>
          {pick === null
            ? yLabel
            : series
                .map((s) => `${s.name}: ${Number.isFinite(s.values[pick]) ? `${format(s.values[pick])}${s.errors ? ` ± ${format(s.errors[pick])}` : ""} ${yLabel}` : t("not in partition", "fuera de partición")}`)
                .join(" · ")}
        </output>
      </figcaption>
      {interactive && <div className="processing-view-controls">
        <button className="btn" onClick={()=>zoom(.8)} aria-label={`${title}: ${t("zoom in","acercar")}`}>+</button><button className="btn" onClick={()=>zoom(1.25)} aria-label={`${title}: ${t("zoom out","alejar")}`}>−</button>
        <button className="btn" onClick={()=>change([xr[0]-(xr[1]-xr[0])*.2,xr[1]-(xr[1]-xr[0])*.2])} aria-label={`${title}: ${t("pan left","desplazar izquierda")}`}>←</button><button className="btn" onClick={()=>change([xr[0]+(xr[1]-xr[0])*.2,xr[1]+(xr[1]-xr[0])*.2])} aria-label={`${title}: ${t("pan right","desplazar derecha")}`}>→</button>
        <button className="btn" onClick={()=>change(null)}>{t("Reset zoom","Restablecer zoom")}</button>
        <label>{t("Drag","Arrastrar")}<select className="select" aria-label={`${title}: ${t("drag mode","modo de arrastre")}`} value={mode} onChange={e=>setMode(e.target.value)}><option value="brush">{t("Brush","Selección")}</option><option value="pan">{t("Pan","Desplazar")}</option></select></label>
      </div>}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${w} ${h}`}
        role={interactive?"group":"img"}
        aria-label={title}
        tabIndex={interactive?0:undefined}
        data-x-min={xr[0]} data-x-max={xr[1]} data-y-min={yr[0]} data-y-max={yr[1]} data-selected-index={pick}
        onDoubleClick={()=>{if(interactive)change(null);}}
        onKeyDown={e=>{if(!interactive)return;if(["ArrowLeft","ArrowRight","Home","End","Escape","+","-"].includes(e.key))e.preventDefault();if(e.key==="Escape")change(null);if(e.key==="+")zoom(.8);if(e.key==="-")zoom(1.25);if(e.key==="Home")choose(0);if(e.key==="End")choose(x.length-1);if(e.key==="ArrowLeft")choose(Math.max(0,(pick??0)-1));if(e.key==="ArrowRight")choose(Math.min(x.length-1,(pick??0)+1));}}
        onPointerLeave={() => {if(!interactive && selectedIndex===undefined)setPick(null);}}
        onPointerDown={e=>{if(!interactive)return;e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);const u=px(e.clientX);pointers.current.set(e.pointerId,u);if(pointers.current.size===2){const a=[...pointers.current.values()];pinch.current={distance:Math.max(1,Math.abs(a[1]-a[0])),range:[...xr]};setDrag(null);}else setDrag({start:u,end:u,range:[...xr]});choose(nearest(u));}}
        onPointerUp={e=>{if(!interactive)return;pointers.current.delete(e.pointerId);if(pinch.current){pinch.current=null;setDrag(null);return;}if(drag&&mode==="brush"&&Math.abs(drag.end-drag.start)>8){const a=coordinate(drag.start),b=coordinate(drag.end);change([Math.min(a,b),Math.max(a,b)]);}setDrag(null);}}
        onPointerCancel={e=>{pointers.current.delete(e.pointerId);pinch.current=null;setDrag(null);}}
        onPointerMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const u = ((e.clientX - r.left) / r.width) * w;
          let near = 0;
          for (let i = 1; i < x.length; i++)
            if (Math.abs(X(x[i]) - u) < Math.abs(X(x[near]) - u)) near = i;
          choose(near);
          if(interactive && pointers.current.has(e.pointerId)){
            const u=px(e.clientX);pointers.current.set(e.pointerId,u);
            if(pinch.current&&pointers.current.size===2){const a=[...pointers.current.values()], v=pinch.current, factor=v.distance/Math.max(1,Math.abs(a[1]-a[0])),centre=(v.range[0]+v.range[1])/2;change([centre+(v.range[0]-centre)*factor,centre+(v.range[1]-centre)*factor]);}
            else if(drag){setDrag({...drag,end:u});if(mode==="pan"){const shift=(drag.start-u)/(w-p.l-p.r)*(drag.range[1]-drag.range[0]);change([drag.range[0]+shift,drag.range[1]+shift]);}}
          }
        }}
      >
        <defs><clipPath id={clipId}><rect x={p.l} y={p.t} width={w-p.l-p.r} height={h-p.t-p.b}/></clipPath></defs>
        {Array.from({ length: ticks }, (_, i) => {
          const a = i / (ticks - 1),
            yv = yr[0] + a * (yr[1] - yr[0]),
            xv = xr[0] + a * (xr[1] - xr[0]);
          return (
            <g key={i}>
              <line
                className="chart-grid"
                x1={p.l}
                x2={w - p.r}
                y1={h - p.b - a * (h - p.b - p.t)}
                y2={h - p.b - a * (h - p.b - p.t)}
              />
              <text
                x={p.l - 10}
                y={h - p.b - a * (h - p.b - p.t) + 4}
                textAnchor="end"
              >
                {format(logY ? 10 ** yv : yv)}
              </text>
              <text
                x={p.l + a * (w - p.l - p.r)}
                y={h - 16}
                textAnchor="middle"
              >
                {format(logX ? 10 ** xv : xv)}
              </text>
            </g>
          );
        })}
        {zeroCentered && <line className="chart-grid" x1={p.l} x2={w-p.r} y1={Y(0)} y2={Y(0)} />}
        <g clipPath={`url(#${clipId})`}>
        {band && <path
          aria-label={band.name}
          d={intervalPath(x, band.lower, band.upper, X, Y)}
          fill="var(--color-accent)" fillOpacity="0.16" stroke="var(--color-accent)" strokeWidth="0.8"
        />}
        {series.map((s, j) => (
          <g key={s.name}>
            {!s.points && (
              <path
                d={curvePath(x, s.values, X, Y)}
                fill="none"
                stroke={s.color ?? hues[j % 3]}
                strokeWidth="2.3"
                strokeDasharray={s.dashed ? "6 4" : undefined}
              />
            )}{" "}
            {(s.points || s.values.length === 1 || pick !== null) &&
              s.values.map((v, i) =>
                Number.isFinite(v) && Number.isFinite(x[i]) && (s.points || s.values.length === 1 || i === pick) ? (
                  <circle
                    key={i}
                    cx={X(x[i])}
                    cy={Y(v)}
                    r={i === pick ? 4.5 : 2.3}
                    fill={s.dashed ? "var(--color-surface)" : s.color ?? hues[j % 3]}
                    stroke={s.color ?? hues[j % 3]}
                    data-index={i} data-x={x[i]} data-value={v}
                  />
                ) : null,
              )}
          </g>
        ))}
        {series.flatMap((s,j)=>s.errors?s.values.map((v,i)=>Number.isFinite(v)?<g key={`${j}-${i}`} stroke={s.color??hues[j%3]} data-error={s.errors![i]}><line x1={X(x[i])} x2={X(x[i])} y1={Y(v-s.errors![i])} y2={Y(v+s.errors![i])}/><line x1={X(x[i])-3} x2={X(x[i])+3} y1={Y(v-s.errors![i])} y2={Y(v-s.errors![i])}/><line x1={X(x[i])-3} x2={X(x[i])+3} y1={Y(v+s.errors![i])} y2={Y(v+s.errors![i])}/></g>:null):[])}
        {pick !== null && (
          <line
            className="cursor-line"
            x1={X(x[pick])}
            x2={X(x[pick])}
            y1={p.t}
            y2={h - p.b}
          />
        )}
        {drag&&mode==="brush"&&<rect className="processing-brush" x={Math.min(drag.start,drag.end)} y={p.t} width={Math.abs(drag.start-drag.end)} height={h-p.t-p.b}/>}
        </g>
        <text className="axis-unit" x={p.l} y={17}>
          {yLabel}
        </text>
      </svg>
      {interactive && <output className="plot-note">{pick===null ? t("Point at a sample or use arrow keys.","Señale una muestra o use las flechas.") : `${format(x[pick])} ${xLabel} · ${pointLabels?.[pick]??`${t("sample","muestra")} ${pick+1}`}`}</output>}
      <div className="curve-legend">
        <span>
          {xLabel}
          {logX ? " · log₁₀" : ""}
        </span>
        {series.map((s, i) => (
          <span key={s.name}>
            <i style={{ background: s.color ?? hues[i % 3] }} />
            {s.name}
          </span>
        ))}
        {band && <span>{band.name}{pick !== null ? `: ${format(band.lower[pick])} – ${format(band.upper[pick])}` : ""}</span>}
      </div>
      {interactive && <details className="mt-exact-table"><summary>{t("Exact curve values","Valores exactos de curvas")}</summary><div className="processing-station-table"><table><thead><tr><th>{xLabel}</th>{series.map(s=><th key={s.name}>{s.name} [{yLabel}]</th>)}</tr></thead><tbody>{x.map((v,i)=><tr key={i} aria-selected={pick===i} onClick={()=>choose(i)}><td><button className="btn" onClick={()=>choose(i)}>{v} · {pointLabels?.[i]}</button></td>{series.map(s=><td key={s.name}>{Number.isFinite(s.values[i])?s.values[i]:t("not in this partition","no pertenece a esta partición")}{s.errors?` ± ${s.errors[i]}`:""}</td>)}</tr>)}</tbody></table></div></details>}
    </figure>
  );
}

export function LayerColumn({
  rho,
  comparison,
  thickness,
  title,
  range = [0, 4],
  selectedLayer,
  onSelect,
}: {
  rho: number[];
  comparison?: number[];
  thickness: number[];
  title: string;
  range?: [number, number];
  selectedLayer?: number;
  onSelect?: (layer: number) => void;
}) {
  const full = [
      ...thickness,
      Math.max(400, thickness.reduce((a, b) => a + b, 0) * 0.45),
    ],
    total = full.reduce((a, b) => a + b, 0);
  let z = 0;
  return (
    <figure className="science-plot layer-column">
      <figcaption>
        {title}
        <output>Ω m</output>
      </figcaption>
      <div className="layer-stack">
        {rho.map((v, i) => {
          const top = z;
          z += full[i];
          return (
            <div
              key={i}
              className="earth-layer"
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              aria-pressed={onSelect ? selectedLayer === i : undefined}
              aria-label={`${i + 1}: ${v} Ω m; ${top} m — ${i < thickness.length ? top + full[i] : "∞"} m`}
              onClick={() => onSelect?.(i)}
              onKeyDown={e => { if (onSelect && ["Enter", " "].includes(e.key)) { e.preventDefault(); onSelect(i); } }}
              style={{
                flexGrow: full[i] / total,
                background: color(Math.log10(v), range, "velocity"),
              }}
            >
              <span>{Math.round(top)} m</span>
              <strong>{format(v)} Ω m</strong>
              {comparison && <small>{format(comparison[i])} Ω m</small>}
            </div>
          );
        })}
      </div>
      <div className="layer-base">∞</div>
    </figure>
  );
}
