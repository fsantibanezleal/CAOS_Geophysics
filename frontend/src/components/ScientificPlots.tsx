import { useEffect, useRef, useState } from "react";
import { PlotCard, useShellLang, useWorkbenchState } from "@fasl-work/caos-app-shell";
import { UPlotChart } from "@fasl-work/caos-app-shell/chart";
import { color, extent, format, type Palette } from "../science";
import plotStyles from "./ScientificPlots.module.css";

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
  aspectRatio,
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
  aspectRatio?: number;
}) {
  const es = useShellLang() === "es";
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<{ x: number; y: number } | null>(null);
  const rows = data.length,
    cols = data[0]?.length ?? 0;
  const isResidual = /residual|residuo/i.test(title);
  const residualLimit = Math.max(1e-20, ...data.flat().filter(Number.isFinite).map(Math.abs));
  const bounds = isResidual ? [-residualLimit, residualLimit] as [number, number] : range ?? extent(data.flat());
  useEffect(() => {
    const c = canvas.current;
    if (!c || !rows || !cols) return;
    const ctx = c.getContext("2d")!;
    const source = document.createElement("canvas");
    source.width = cols;
    source.height = rows;
    const pixels = source.getContext("2d")!;
    // Nearest-neighbour backing pixels keep coarse grids crisp without
    // inventing intermediate values. Bound the allocation for user arrays.
    const rasterScale = Math.max(
      1,
      Math.min(8, Math.floor(Math.sqrt(1_500_000 / (rows * cols)))),
    );
    c.width = cols * rasterScale;
    c.height = rows * rasterScale;
    for (let y = 0; y < rows; y++)
      for (let x = 0; x < cols; x++) {
        pixels.fillStyle = color(data[y][x], bounds, palette);
        pixels.fillRect(x, y, 1, 1);
      }
    // Each raster pixel is an exported sample; do not interpolate fake resolution.
    ctx.imageSmoothingEnabled = false;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(source, 0, 0, c.width, c.height);
    // A restrained quarter grid is a spatial reference overlay, not extra
    // samples. It keeps near-background and uniform sections spatially
    // locatable without altering any raster values.
    if (rows > 4 && cols > 4) {
      const area = c.parentElement;
      const pixelScale = c.width / Math.max(1, area?.clientWidth ?? c.width);
      const lineWidth = Math.max(1, pixelScale * 0.8);
      ctx.save();
      ctx.strokeStyle = getComputedStyle(c).getPropertyValue("--color-fg-subtle").trim() || "#59616b";
      ctx.globalAlpha = 0.32;
      ctx.lineWidth = lineWidth;
      for (let i = 1; i < 5; i++) {
        const x = Math.round((i * cols * rasterScale) / 5) + 0.5;
        const y = Math.round((i * rows * rasterScale) / 5) + 0.5;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, rows * rasterScale);
        ctx.moveTo(0, y);
        ctx.lineTo(cols * rasterScale, y);
        ctx.stroke();
      }
      ctx.restore();
    }
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
    <figure className={`${plotStyles.heatmap} science-plot heatmap`}>
      <figcaption>
        <span>{title}</span>
        <output>
          {hover ? `${format(data[hover.y]?.[hover.x])} ${unit}` : unit}
        </output>
      </figcaption>
      <div className={`${plotStyles.heatmapAxes} heatmap-axes`}>
        <span className="axis-y">{yLabel}</span>
        <div
          className={`${plotStyles.heatmapArea} heatmap-area`}
          style={aspectRatio ? { aspectRatio } : undefined}
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
          <canvas ref={canvas} aria-label={title} style={{ position: "absolute", inset: 0, imageRendering: "pixelated" }} />
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
  x, series, title, xLabel, yLabel, logX = false, logY = false, band,
  interactive = false, selectedIndex, onSelect, viewport,
  zeroCentered = false, fixedYRange, pointLabels,
}: {
  x: number[]; series: Series[]; title: string; xLabel: string; yLabel: string;
  logX?: boolean; logY?: boolean; band?: Band; interactive?: boolean;
  selectedIndex?: number; onSelect?: (index: number) => void;
  /** Domain in transformed x coordinates (log10 where logX). */
  viewport?: [number, number] | null; onViewport?: (range: [number, number] | null) => void;
  zeroCentered?: boolean; fixedYRange?: [number, number]; pointLabels?: string[];
}) {
  const workbench = useWorkbenchState();
  const pick = selectedIndex ?? null;
  const activeViewport = viewport && logX
    ? [10 ** viewport[0], 10 ** viewport[1]] as [number, number]
    : viewport;
  const chartSeries = series.flatMap((s, i) => {
    const base = {
      id: `series-${i}`, label: s.name,
      values: s.values.map(v => Number.isFinite(v) ? v : null),
      mode: s.points ? "points" as const : "line" as const,
      dash: s.dashed ? [6, 4] : undefined, dots: s.points,
    };
    const uncertainty = s.errors?.length === x.length ? [
      { id: `series-${i}-lower`, label: `${s.name} − σ`, values: s.values.map((v, j) => Number.isFinite(v) && Number.isFinite(s.errors![j]) ? v - s.errors![j] : null), dash: [2, 3] },
      { id: `series-${i}-upper`, label: `${s.name} + σ`, values: s.values.map((v, j) => Number.isFinite(v) && Number.isFinite(s.errors![j]) ? v + s.errors![j] : null), dash: [2, 3] },
    ] : [];
    return [base, ...uncertainty];
  });
  const bandSeries = band ? [
    { id: "interval-lower", label: `${band.name} lower`, values: band.lower.map(v => Number.isFinite(v) ? v : null), dash: [2, 3] },
    { id: "interval-upper", label: `${band.name} upper`, values: band.upper.map(v => Number.isFinite(v) ? v : null), dash: [2, 3] },
  ] : [];
  const choose = (index: number) => onSelect?.(index);
  const yRange = fixedYRange ?? (zeroCentered ? (() => {
    const vals = [...series.flatMap(s => s.values), ...(band ? [...band.lower, ...band.upper] : [])].filter(Number.isFinite);
    const m = Math.max(1e-20, ...vals.map(Math.abs));
    return [-m * 1.08, m * 1.08] as [number, number];
  })() : undefined);
  const chart = <UPlotChart
    title={title}
    x={{ label: xLabel, values: x, log: logX, range: activeViewport ?? undefined }}
    y={{ label: yLabel, log: logY, range: yRange }}
    series={[...chartSeries, ...bandSeries]}
    height="fill"
    onPick={interactive ? choose : undefined}
    readout={index => `${pointLabels?.[index] ?? `sample ${index + 1}`} · ${series.map(s => `${s.name}: ${Number.isFinite(s.values[index]) ? format(s.values[index]) : "not available"}${s.errors ? ` ± ${format(s.errors[index])}` : ""}`).join(" · ")}${band ? ` · ${band.name}: ${format(band.lower[index])}–${format(band.upper[index])}` : ""}`}
    hint={pick === null ? `${yLabel} by ${xLabel}` : `${pointLabels?.[pick] ?? `sample ${pick + 1}`} · ${format(x[pick])} ${xLabel}`}
  />;
  const content = workbench ? <PlotCard
    title={title} lane="replay"
    provenance={workbench.source === "real" ? "real" : "synthetic"}
    dataKey={workbench.stateKey} fill
  >{chart}</PlotCard> : chart;
  return <div className={`${plotStyles.plotShell} science-plot-shell`}>{content}</div>;
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
  const es = useShellLang() === "es";
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
      <svg
        className="layer-stack layer-stack-svg"
        viewBox="0 0 250 600"
        preserveAspectRatio="none"
        role="group"
        aria-label={title}
        data-plot="Layered resistivity model"
      >
        {rho.map((v, i) => {
          const top = z;
          z += full[i];
          const y = (top / total) * 600;
          const height = (full[i] / total) * 600;
          const end = i < thickness.length ? `${Math.round(top + full[i])} m` : "∞";
          const label = `${i + 1}: ${format(v)} Ω m; ${Math.round(top)} m to ${end}`;
          const selected = onSelect && selectedLayer === i;
          return (
            <g
              key={i}
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              aria-pressed={onSelect ? selectedLayer === i : undefined}
              aria-label={label}
              onClick={() => onSelect?.(i)}
              onKeyDown={e => {
                if (onSelect && ["Enter", " "].includes(e.key)) {
                  e.preventDefault();
                  onSelect(i);
                }
              }}
            >
              <rect
                x="0"
                y={y}
                width="250"
                height={Math.max(1, height)}
                fill={color(Math.log10(v), range, "velocity")}
                stroke="var(--color-surface)"
                strokeWidth="3"
                vectorEffect="non-scaling-stroke"
              />
              {selected && <rect x="2" y={y + 2} width="246" height={Math.max(1, height - 4)} fill="none" stroke="var(--color-fg)" strokeWidth="3" vectorEffect="non-scaling-stroke" />}
              {height >= 48 ? <>
                <rect x="6" y={y + height / 2 - 19} width="238" height="19" rx="3" className="layer-label-plate" />
                <text x="12" y={y + height / 2 - 5} className="layer-depth-label">{Math.round(top)} m – {end}</text>
                <rect x="6" y={y + height / 2 + 3} width="238" height="20" rx="3" className="layer-label-plate" />
                <text x="12" y={y + height / 2 + 18} className="layer-value-label">{format(v)} Ω m{comparison ? ` · ${format(comparison[i])} Ω m` : ""}</text>
              </> : height >= 30 ? <>
                <rect x="6" y={y + height / 2 - 11} width="238" height="20" rx="3" className="layer-label-plate" />
                <text x="12" y={y + height / 2 + 4} className="layer-value-label">{Math.round(top)} m · {format(v)} Ω m</text>
              </> : null}
            </g>
          );
        })}
      </svg>
      <div className="layer-base">∞ · {es ? "semiespacio" : "half-space"}</div>
    </figure>
  );
}
