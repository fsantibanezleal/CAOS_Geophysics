import { useId, useState } from "react";
import { Figure, useShellLang, useThemeStore } from "@fasl-work/caos-app-shell";
import reference from "../../../docs/methods/gravity-processing/scientific-course/assets/reference-surfaces.svg?raw";
import plate from "../../../docs/methods/gravity-processing/scientific-course/assets/plate-and-relief.svg?raw";
import errors from "../../../docs/methods/gravity-processing/scientific-course/assets/shared-errors.svg?raw";
import layer from "../../../docs/methods/gravity-processing/scientific-course/assets/mathematical-layer.svg?raw";
import blocks from "../../../docs/methods/gravity-processing/scientific-course/assets/blocked-support.svg?raw";
import continuation from "../../../docs/methods/gravity-processing/scientific-course/assets/continuation-spectrum.svg?raw";
import type { CourseResult } from "../data/m01-scientific-course";

const diagrams = [reference, plate, errors, layer, blocks, continuation];
const diagramLabels = [
  ["Receiver, land, geoid and ellipsoid heights", "Alturas de receptor, tierra, geoide y elipsoide"],
  ["Infinite plate and signed attraction of relief", "Placa infinita y atracción con signo del relieve"],
  ["Shared primitive errors and dependent height derivatives", "Errores primitivos comunes y derivadas de alturas dependientes"],
  ["Buried control prism separate from a mathematical source layer", "Prisma de control enterrado separado de capa de fuentes matemáticas"],
  ["Outer blocks, inner folds, masked rows and null support", "Bloques externos, pliegues internos, máscaras y soporte null"],
  ["Source-free Fourier attenuation by height and wavelength", "Atenuación de Fourier sin fuentes según altura y longitud de onda"],
];
/** Standalone image document: never inject its root/text CSS into the app.
 * Frozen physical geometry and bilingual labels stay unchanged; explicit
 * shell theme overrides the image's system preference, without global CSS.
 */
export function theoryDiagramUrl(chapter: number, dark: boolean): string {
  const palette = dark
    ? "--bg:#0d1117;--surface:#161b22;--fg:#c9d1d9;--muted:#9aa6b2;--border:#30363d;--blue:#58a6ff;--cyan:#3fb1c8;--pink:#f778ba;--warn:#d29922"
    : "--bg:#f6f8fa;--surface:#fff;--fg:#1f2328;--muted:#57606a;--border:#d0d7de;--blue:#0969da;--cyan:#0a7c8a;--pink:#bf3989;--warn:#9a6700";
  const raw = diagrams[chapter - 1];
  if (!raw) throw new Error("Unknown physical diagram.");
  const image = raw.replace(/@media\(prefers-color-scheme:dark\)\{:root\{[^}]*\}\}/, "")
    .replace(/:root\{[^}]*\}/, ":root{" + palette + "}");
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(image);
}
export type MapField = "field" | "sigma" | "residual";
export const mapScales: Record<MapField, readonly [number,number]> = {
  field: [-.2, .8], sigma: [0, .03], residual: [-.1, .1],
};
export function M01CourseDiagram({ chapter = 1, result, heightIndex = 0, field = "field", coverage = true }: {
  chapter?: number; result?: CourseResult; heightIndex?: number; field?: MapField; coverage?: boolean;
}) {
  const es = useShellLang() === "es", dark = useThemeStore(s => s.theme) === "dark", id = useId();
  const [point, setPoint] = useState(0);
  const t = (en: string, sp: string) => es ? sp : en;
  if (!result) return <Figure caption={t(
    "Physical assumption schematic, not a measured survey or recovered density. Geometry is explanatory; arrow lengths are not amplitudes. Labels are bilingual.",
    "Esquema de supuestos físicos, no levantamiento medido ni densidad recuperada. Geometría explicativa; flechas no son amplitudes. Etiquetas bilingües.")}>
    <img className="fig-svg" style={{ height: "auto" }} src={theoryDiagramUrl(chapter, dark)}
      alt={t(diagramLabels[chapter-1][0], diagramLabels[chapter-1][1])} />
  </Figure>;
  const grid = result.grids[heightIndex], x = result.axes.easting_m, y = result.axes.northing_m;
  const dx = x[1] - x[0], dy = y[1] - y[0], xmin = x[0] - dx/2, xmax = x.at(-1)! + dx/2;
  const ymin = y[0] - dy/2, ymax = y.at(-1)! + dy/2;
  const scale = 510 / (xmax - xmin), plotHeight = (ymax - ymin) * scale;
  const px = (v: number) => 65 + (v - xmin) * scale, py = (v: number) => 35 + (ymax - v) * scale;
  const [low, high] = mapScales[field], mid = (low + high) / 2;
  const values = field === "sigma" ? grid.conditional_sigma_mgal : grid.predicted_mgal;
  const color = (v: number) => v < mid ? "var(--color-fg-subtle)" : "var(--color-accent)";
  const opacity = (v: number) => .12 + .88 * Math.min(1, Math.abs(v - mid) / ((high - low) / 2));
  const label = field === "sigma" ? t("Conditional noise SD", "DE condicional de ruido")
    : field === "residual" ? t("Prediction minus observation", "Predicción menos observación")
      : t("Continued downward component", "Componente descendente continuada");
  const selected = Math.min(point, field === "residual" ? 195 : values.length - 1);
  const selectedValue = field === "residual" ? result.stations.signed_predicted_minus_observed_mgal[selected] : values[selected];
  const selectedX = field === "residual" ? result.geometry.easting_m[selected] : x[selected % x.length];
  const selectedY = field === "residual" ? result.geometry.northing_m[selected] : y[Math.floor(selected / x.length)];
  const reason = field === "residual"
    ? result.geometry.mask[selected] ? t("original mask", "máscara original") : t("unsupported", "sin soporte")
    : grid.outside_hull[selected] ? t("outside training hull", "fuera de envolvente")
      : t("outside coverage radius", "fuera del radio");
  const maxIndex = field === "residual" ? 195 : values.length - 1;
  return <Figure caption={t(
    "Actual recorded arrays, mGal; equal-aspect metric axes. Rectangles depict sampled grid nodes, not extra interpolation or geological resolution. Shared fixed colour limits across all three scenarios/heights; saturated colour does not clip the value.",
    "Arrays realmente registrados, mGal; ejes métricos con igual escala. Rectángulos representan nodos muestreados, no interpolación adicional ni resolución geológica. Límites de color fijos entre tres escenarios/alturas; saturación no recorta valores.")}>
    <svg className="method-diagram" viewBox={"0 0 640 " + (plotHeight + 170)} role="img" aria-labelledby={id+"-title"}>
      <title id={id+"-title"}>{label + " (mGal)"}</title>
      <rect x="65" y="35" width="510" height={plotHeight} fill="var(--color-surface)" stroke="var(--color-border)" />
      {field !== "residual" && values.map((v, i) => v === null ? coverage ? <rect key={i}
        x={px(x[i % x.length]) - dx*scale/2} y={py(y[Math.floor(i/x.length)]) - dy*scale/2}
        width={dx*scale} height={dy*scale} fill="none" stroke="var(--color-border)" strokeWidth=".5" onPointerEnter={() => setPoint(i)}>
        <title>{grid.outside_hull[i] ? t("Outside hull: null", "Fuera de envolvente: null") : t("Outside radius: null", "Fuera de radio: null")}</title>
      </rect> : null : <rect key={i} x={px(x[i % x.length]) - dx*scale/2}
        y={py(y[Math.floor(i/x.length)]) - dy*scale/2} width={dx*scale} height={dy*scale}
        fill={color(v)} fillOpacity={opacity(v)} onPointerEnter={() => setPoint(i)}>
        <title>{x[i%x.length].toFixed(2) + ", " + y[Math.floor(i/x.length)].toFixed(2) + " m: " + v.toPrecision(7) + " mGal"}</title>
      </rect>)}
      {result.geometry.easting_m.map((east, i) => {
        const north = result.geometry.northing_m[i], masked = result.geometry.mask[i];
        const residual = result.stations.signed_predicted_minus_observed_mgal[i];
        const unsupported = !result.stations.prediction_covered[i], cx = px(east), cy = py(north);
        if (masked || (field === "residual" && unsupported)) return <path key={i}
          d={"M"+(cx-3)+","+(cy-3)+"l6,6m-6,0l6,-6"} stroke="var(--color-fg)" onPointerEnter={() => field === "residual" && setPoint(i)}>
          <title>{result.geometry.station_ids[i] + ": " + (masked ? result.geometry.mask_reasons[i] : t("unsupported residual: null", "residual sin soporte: null"))}</title>
        </path>;
        if (field === "residual" && residual !== null) return <circle key={i} cx={cx} cy={cy} r="3.8"
          fill={color(residual)} fillOpacity={opacity(residual)} onPointerEnter={() => setPoint(i)}>
          <title>{residual.toPrecision(7) + " mGal; " + result.split.partition[i]}</title>
        </circle>;
        return coverage ? <circle key={i} cx={cx} cy={cy} r={result.split.partition[i] === "holdout" ? 3.5 : 1.8}
          fill="none" stroke="var(--color-fg)" strokeWidth=".8">
          <title>{result.geometry.station_ids[i] + ": " + result.split.partition[i]}</title>
        </circle> : null;
      })}
      <text x="65" y={plotHeight + 61}>{xmin.toFixed(0)} m</text>
      <text x="575" y={plotHeight + 61} textAnchor="end">{xmax.toFixed(0)} m</text>
      <text x="310" y={plotHeight + 86} textAnchor="middle">{t("Easting (m)", "Este (m)")}</text>
      <text x="60" y="30" textAnchor="end">{ymax.toFixed(0)} m</text>
      <text x="60" y={plotHeight + 35} textAnchor="end">{ymin.toFixed(0)} m</text>
      <text transform={"translate(16 "+(35+plotHeight/2)+") rotate(-90)"} textAnchor="middle">{t("Northing (m)", "Norte (m)")}</text>
      {Array.from({length: 40}, (_, i) => {
        const v = low + (high-low) * i/39;
        return <rect key={"scale-"+i} x={65+i*12.75} y={plotHeight+99} width="12.75" height="12" fill={color(v)} fillOpacity={opacity(v)} />;
      })}
      <text x="65" y={plotHeight+130}>{low} mGal</text><text x="320" y={plotHeight+130} textAnchor="middle">{mid} mGal</text>
      <text x="575" y={plotHeight+130} textAnchor="end">{high} mGal</text>
      <text x="65" y={plotHeight+150}>{t("X = masked/unsupported; blank = null", "X = máscara/sin soporte; blanco = null")}</text>
    </svg>
    <label htmlFor={id+"-node"}>{t("Inspect sample (keyboard arrows or pointer)", "Inspeccionar muestra (flechas o puntero)")}</label>
    <input className="select" id={id+"-node"} type="number" min="0" max={maxIndex} value={selected}
      onChange={e => { const v = Number(e.target.value); if (Number.isInteger(v) && v >= 0 && v <= maxIndex) setPoint(v); }} />
    <output aria-live="polite" data-testid="m01-map-value"> {selectedX.toFixed(2)}, {selectedY.toFixed(2)} m:
      {selectedValue === null ? " null (" + reason + ")" : " " + selectedValue.toPrecision(8) + " mGal"}</output>
  </Figure>;
}
