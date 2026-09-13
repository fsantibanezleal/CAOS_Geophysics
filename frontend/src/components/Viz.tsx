import { useState } from 'react';
import type { LiveResult } from '../engine';

function color(value: number, min: number, max: number, hue = 190) { const t = Math.max(0, Math.min(1, (value - min) / (max - min || 1))); return `hsl(${hue + 55 * t} ${55 + 35 * t}% ${18 + 40 * t}%)`; }

export function FieldMap({ result, values, label, units, opacity = 1, hue = 190 }: { result: LiveResult; values: number[]; label: string; units: string; opacity?: number; hue?: number }) {
  const [readout, setReadout] = useState(`${label} | move pointer across the field`); const w = 720, h = 340, nx = result.x.length, nz = result.z.length; const min = Math.min(...values), max = Math.max(...values);
  return <div className="viz-card"><div className="viz-title"><span>{label}</span><span className="mono">{readout}</span></div><svg className="field-map" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} onMouseMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); const ix = Math.min(nx - 1, Math.max(0, Math.floor((e.clientX - r.left) / r.width * nx))); const iz = Math.min(nz - 1, Math.max(0, Math.floor((e.clientY - r.top) / r.height * nz))); setReadout(`x ${result.x[ix].toFixed(0)} m | z ${result.z[iz].toFixed(0)} m | ${values[iz * nx + ix].toFixed(4)} ${units}`); }}>
    {Array.from({ length: nz }, (_, iz) => Array.from({ length: nx }, (_, ix) => <rect key={`${iz}-${ix}`} x={ix * w / nx} y={iz * h / nz} width={w / nx + .4} height={h / nz + .4} fill={color(values[iz * nx + ix], min, max, hue)} opacity={opacity} />))}
    <g className="map-grid"><line x1="0" x2={w} y1="0" y2="0" /><line x1="0" x2={w} y1={h - 1} y2={h - 1} /><text x="12" y="22">surface</text><text x="12" y={h - 12}>{result.z.at(-1)?.toFixed(0)} m depth</text></g>
  </svg></div>;
}

export function LinePlot({ values, label, units, accent = '#f5b942', comparison }: { values: number[]; label: string; units: string; accent?: string; comparison?: number[] }) {
  const [readout, setReadout] = useState(`${label} | move pointer across the trace`); const w = 720, h = 250; const all = values.concat(comparison ?? []); const min = Math.min(...all), max = Math.max(...all); const path = (data: number[]) => data.map((v, i) => `${(i / Math.max(1, data.length - 1)) * w},${h - 20 - ((v - min) / (max - min || 1)) * (h - 38)}`).join(' ');
  return <div className="viz-card"><div className="viz-title"><span>{label}</span><span className="mono">{readout}</span></div><svg className="line-plot" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label} onMouseMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); const i = Math.min(values.length - 1, Math.max(0, Math.round((e.clientX - r.left) / r.width * (values.length - 1)))); setReadout(`sample ${i + 1}/${values.length} | ${values[i].toFixed(4)} ${units}`); }}><line x1="0" x2={w} y1={h - 20} y2={h - 20} className="axis" /><polyline points={path(values)} fill="none" stroke={accent} strokeWidth="3" />{comparison && <polyline points={path(comparison)} fill="none" stroke="#6ae3de" strokeWidth="2" strokeDasharray="7 6" />}<text x="12" y="18">{max.toPrecision(4)} {units}</text><text x="12" y={h - 28}>{min.toPrecision(4)} {units}</text></svg></div>;
}

export function Section({ result, mode, opacity }: { result: LiveResult; mode: string; opacity: number }) {
  if (mode === 'gravity') return <><FieldMap result={result} values={result.density} label="Density model | depth slice" units="g/cm³" opacity={opacity} hue={30} /><LinePlot values={result.gravity} label="Gravity response | surface profile" units="mGal" /></>;
  if (mode === 'magnetics') return <><FieldMap result={result} values={result.susceptibility} label="Susceptibility model | inducing field" units="SI" opacity={opacity} hue={205} /><LinePlot values={result.magnetic} label="Magnetic anomaly | total field" units="nT" accent="#8bf0c2" /></>;
  if (mode === 'mt') return <><LinePlot values={result.resistivity} label="Apparent resistivity | log frequency" units="ohm m" accent="#c59cff" /><LinePlot values={result.phase} label="Phase | impedance response" units="deg" accent="#6ae3de" /></>;
  if (mode === 'fwi') return <><FieldMap result={result} values={result.density.map((v, i) => 1800 + 900 * v + (i % result.x.length) * 1.8)} label="Acoustic update | velocity proxy" units="m/s" opacity={opacity} hue={260} /><LinePlot values={result.wave} comparison={result.residual} label="Shot gather | observed and residual" units="amplitude" accent="#f5b942" /></>;
  if (mode === 'joint') return <><FieldMap result={result} values={result.cross} label="Cross-gradient | structural agreement" units="relative" opacity={opacity} hue={280} /><LinePlot values={result.gravity} comparison={result.magnetic.map((v) => v / 1000)} label="Linked evidence | normalized profiles" units="scaled" accent="#f5b942" /></>;
  if (mode === 'learned') return <><FieldMap result={result} values={result.uncertainty} label="Novelty / uncertainty | learned guard" units="relative" opacity={opacity} hue={320} /><LinePlot values={result.uncertainty} label="Latent reconstruction error" units="relative" accent="#ff8cb8" /></>;
  return <><FieldMap result={result} values={result.density} label="Subsurface evidence field" units="g/cm³" opacity={opacity} /><LinePlot values={result.gravity} label="Primary observation" units="mGal" /></>;
}
