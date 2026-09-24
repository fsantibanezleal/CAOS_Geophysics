import { useEffect, useRef, useState } from "react";
import { color, extent, format, type Palette } from "../science";

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
  onPick?: (x: number, y: number) => void;
  markers?: { x: number; y: number; label: string }[];
  boundaries?: number[][];
  cursorY?: number;
}) {
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
    ctx.imageSmoothingEnabled = palette !== "velocity";
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(source, 0, 0, c.width, c.height);
  }, [data, palette, bounds[0], bounds[1], rows, cols]);
  const xv = hover
    ? (xRange?.[0] ?? 0) +
      ((hover.x + 0.5) / cols) * ((xRange?.[1] ?? cols) - (xRange?.[0] ?? 0))
    : 0;
  const yv = hover
    ? (yRange?.[0] ?? 0) +
      ((hover.y + 0.5) / rows) * ((yRange?.[1] ?? rows) - (yRange?.[0] ?? 0))
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
              aria-label="Known geological interfaces"
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

type Series = {
  name: string;
  values: number[];
  color?: string;
  dashed?: boolean;
  points?: boolean;
};
export function Plot({
  x,
  series,
  title,
  xLabel,
  yLabel,
  logX = false,
  logY = false,
}: {
  x: number[];
  series: Series[];
  title: string;
  xLabel: string;
  yLabel: string;
  logX?: boolean;
  logY?: boolean;
}) {
  const [pick, setPick] = useState<number | null>(null);
  const w = 640,
    h = 270,
    p = { l: 64, r: 22, t: 20, b: 42 };
  const tx = (v: number) => (logX ? Math.log10(Math.max(v, 1e-20)) : v),
    ty = (v: number) => (logY ? Math.log10(Math.max(v, 1e-20)) : v);
  const xr = extent(x.map(tx)),
    yr = extent(series.flatMap((s) => s.values.map(ty)));
  const pad = (yr[1] - yr[0]) * 0.08;
  yr[0] -= pad;
  yr[1] += pad;
  const X = (v: number) =>
      p.l + ((tx(v) - xr[0]) / (xr[1] - xr[0])) * (w - p.l - p.r),
    Y = (v: number) =>
      h - p.b - ((ty(v) - yr[0]) / (yr[1] - yr[0])) * (h - p.b - p.t);
  const hues = [
    "var(--plot-observed)",
    "var(--plot-predicted)",
    "var(--plot-third)",
  ];
  return (
    <figure className="science-plot curve">
      <figcaption>
        {title}
        <output>
          {pick === null
            ? yLabel
            : series
                .map((s) => `${s.name}: ${format(s.values[pick] ?? 0)}`)
                .join(" · ")}
        </output>
      </figcaption>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={title}
        onPointerLeave={() => setPick(null)}
        onPointerMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const u = ((e.clientX - r.left) / r.width) * w;
          let near = 0;
          for (let i = 1; i < x.length; i++)
            if (Math.abs(X(x[i]) - u) < Math.abs(X(x[near]) - u)) near = i;
          setPick(near);
        }}
      >
        {Array.from({ length: 5 }, (_, i) => {
          const a = i / 4,
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
        {series.map((s, j) => (
          <g key={s.name}>
            {!s.points && (
              <path
                d={s.values
                  .map((v, i) => `${i ? "L" : "M"}${X(x[i])},${Y(v)}`)
                  .join(" ")}
                fill="none"
                stroke={s.color ?? hues[j % 3]}
                strokeWidth="2.3"
                strokeDasharray={s.dashed ? "6 4" : undefined}
              />
            )}{" "}
            {(s.points || pick !== null) &&
              s.values.map((v, i) =>
                s.points || i === pick ? (
                  <circle
                    key={i}
                    cx={X(x[i])}
                    cy={Y(v)}
                    r={i === pick ? 4.5 : 2.3}
                    fill={s.color ?? hues[j % 3]}
                  />
                ) : null,
              )}
          </g>
        ))}
        {pick !== null && (
          <line
            className="cursor-line"
            x1={X(x[pick])}
            x2={X(x[pick])}
            y1={p.t}
            y2={h - p.b}
          />
        )}
        <text className="axis-unit" x={p.l} y={12}>
          {yLabel}
        </text>
      </svg>
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
      </div>
    </figure>
  );
}

export function LayerColumn({
  rho,
  comparison,
  thickness,
  title,
}: {
  rho: number[];
  comparison?: number[];
  thickness: number[];
  title: string;
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
              style={{
                flexGrow: full[i] / total,
                background: color(Math.log10(v), [0, 4], "velocity"),
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
