import { PlotCard, Stage } from "@fasl-work/caos-app-shell";
import type { ProfileAdmission, ProfileModel } from "../api/profile-local-contracts";
import { Plot } from "./ScientificPlots";
import { ertSurveyPoints } from "./ert-view-data";
import { formatNumber } from "../lib/number-format";
import styles from "./ScientificPlots.module.css";

type QC = Record<string, unknown>;
const fmt = (value: number, es: boolean) => formatNumber(value, es ? "es-CL" : "en-US");

/** M07 supplied-data view: surveyed topography and four-electrode acquisition. */
export function ERTResultView({ admitted, model, row, onRow, es }: {
  admitted: ProfileAdmission; model: ProfileModel; row: number; onRow: (row: number) => void; es: boolean;
}) {
  const t = (en: string, sp: string) => es ? sp : en;
  const qc = (admitted.result.engine_report as Record<string, unknown>).qc as QC;
  const x = admitted.rows.map((_, i) => i + 1);
  const labels = admitted.rows.map((quad, i) => `${i + 1} · A${quad[0] + 1} B${quad[1] + 1} M${quad[2] + 1} N${quad[3] + 1}`);
  const selected = admitted.rows[row];
  const sensorX = admitted.sensors.map(point => point[0]);
  const sensorZ = admitted.sensors.map(point => point[1]);
  const xMin = Math.min(...sensorX), xMax = Math.max(...sensorX);
  const zMin = Math.min(...sensorZ), zMax = Math.max(...sensorZ);
  const xSpan = Math.max(xMax - xMin, 1), zSpan = Math.max(zMax - zMin, 1);
  const survey = ertSurveyPoints(admitted.sensors, selected);
  const source = (admitted.result.metadata as Record<string, unknown>).source as Record<string, unknown>;
  const provenance = source.kind === "synthetic_control" ? "synthetic" : "real";
  const errors = model.sigma;
  const relief = typeof qc.topographic_relief_m === "number" ? qc.topographic_relief_m : null;
  const reciprocalCount = Array.isArray(qc.reciprocal_pairs) ? qc.reciprocal_pairs.length : null;
  const flagged = Array.isArray(qc.flagged_rows) ? qc.flagged_rows.length : null;

  return <section data-testid="ert-result-view" className="processing-instrument">
    <div className={`${styles.plotShell} ${styles.surveyPlotShell}`}>
    <PlotCard title={t("Surveyed ERT electrode profile", "Perfil de electrodos ERT medido")} lane="replay" provenance={provenance} fill
      note={t("Electrode positions are the supplied x/elevation coordinates. A, B, M and N identify the selected original quadrupole; no current paths or apparent-resistivity pseudosection are inferred.", "Las posiciones son las coordenadas x/elevación suministradas. A, B, M y N identifican el cuadripolo original seleccionado; no se infieren trayectorias de corriente ni una seudosección de resistividad aparente.")}>
      <Stage label={t("Surveyed electrode profile", "Perfil de electrodos medido")}>{({ width, height }) => {
        const pad = { left: 62, right: 22, top: 34, bottom: 48 };
        const availableX = Math.max(1, width - pad.left - pad.right);
        const availableY = Math.max(1, height - pad.top - pad.bottom);
        const scale = Math.min(availableX / xSpan, availableY / zSpan);
        const drawingWidth = xSpan * scale, drawingHeight = zSpan * scale;
        const left = pad.left + (availableX - drawingWidth) / 2;
        const bottom = pad.top + (availableY - drawingHeight) / 2 + drawingHeight;
        const px = (v: number) => left + (v - xMin) * scale;
        const py = (v: number) => bottom - (v - zMin) * scale;
        const xs = [xMin, (xMin + xMax) / 2, xMax];
        const zs = zSpan === 1 && zMin === zMax ? [zMin] : [zMin, (zMin + zMax) / 2, zMax];
        return <svg role="img" aria-label={t("Topographic ERT electrode geometry", "Geometría topográfica de electrodos ERT")} viewBox={`0 0 ${width} ${height}`} width={width} height={height} data-testid="ert-topographic-profile">
          <g stroke="var(--color-border)" strokeWidth="1">
            {xs.map((value, i) => <line key={`gx${i}`} x1={px(value)} x2={px(value)} y1={pad.top} y2={bottom} />)}
            {zs.map((value, i) => <line key={`gz${i}`} x1={left} x2={left + drawingWidth} y1={py(value)} y2={py(value)} />)}
          </g>
          <polyline points={survey.map(p => `${px(p.x_m)},${py(p.elevation_m)}`).join(" ")} fill="none" stroke="var(--color-fg)" strokeWidth="2" />
          {survey.map(point => <circle key={point.electrode} cx={px(point.x_m)} cy={py(point.elevation_m)} r={point.label ? 7 : 3.5} fill={point.label ? "var(--color-accent)" : "var(--color-surface)"} stroke={point.label ? "var(--color-bg)" : "var(--color-fg)"} strokeWidth={point.label ? 2 : 1.5} data-electrode={point.label ?? undefined}><title>{t("Electrode", "Electrodo")} {point.electrode + 1}: x {fmt(point.x_m, es)} m, z {fmt(point.elevation_m, es)} m{point.label ? ` · ${point.label}` : ""}</title></circle>)}
          {survey.filter(point => point.label).map(point => {
            return <g key={point.label!} data-electrode={point.label!}>
              <text x={px(point.x_m)} y={py(point.elevation_m) - 12} textAnchor="middle" fill="var(--color-fg)" fontFamily="var(--font-mono)" fontSize="12" fontWeight="700">{point.label}</text>
            </g>;
          })}
          {xs.map((value, i) => <text key={`xt${i}`} x={px(value)} y={bottom + 20} textAnchor="middle" fill="var(--color-fg-subtle)" fontFamily="var(--font-mono)" fontSize="11">{fmt(value, es)}</text>)}
          {zs.map((value, i) => <text key={`zt${i}`} x={left - 8} y={py(value) + 4} textAnchor="end" fill="var(--color-fg-subtle)" fontFamily="var(--font-mono)" fontSize="11">{fmt(value, es)}</text>)}
          <text x={left + drawingWidth / 2} y={height - 5} textAnchor="middle" fill="var(--color-fg)" fontFamily="var(--font-mono)" fontSize="12">{t("Profile distance [m]", "Distancia del perfil [m]")}</text>
          <text x="14" y={pad.top + drawingHeight / 2} transform={`rotate(-90 14 ${pad.top + drawingHeight / 2})`} textAnchor="middle" fill="var(--color-fg)" fontFamily="var(--font-mono)" fontSize="12">{t("Elevation [m], positive up", "Elevación [m], positiva hacia arriba")}</text>
        </svg>;
      }}</Stage>
    </PlotCard>
    </div>

    <div className="processing-status" data-testid="ert-qc-summary">
      <span>{t("Electrodes", "Electrodos")}: {String(qc.sensor_count ?? admitted.sensors.length)}</span>
      <span>{t("Quadrupoles", "Cuadripolos")}: {String(qc.measurement_count ?? admitted.rows.length)}</span>
      {relief !== null && <span>{t("Surveyed relief", "Relieve medido")}: {fmt(relief, es)} m</span>}
      {reciprocalCount !== null && <span>{t("Reciprocal pairs", "Pares recíprocos")}: {reciprocalCount}</span>}
      {flagged !== null && <span>{t("QC flags (retained)", "Alertas QC (retenidas)")}: {flagged}</span>}
      <span>{t("Instrument errors", "Errores instrumentales")}: {t("not supplied", "no suministrados")}</span>
    </div>
    <p className="plot-note">{t("The admitted result contains transfer resistance (Ω), not per-quadrupole geometric factors or apparent resistivity. Error bars below use the declared assumed weighting, not measured instrument uncertainty.", "El resultado admitido contiene resistencia de transferencia (Ω), no factores geométricos por cuadripolo ni resistividad aparente. Las barras de error usan la ponderación supuesta declarada, no incertidumbre instrumental medida.")}</p>
    <Plot interactive x={x} selectedIndex={row} onSelect={onRow} pointLabels={labels}
      title={t("Measured and frozen predicted transfer resistance", "Resistencia de transferencia medida y predicción congelada")}
      xLabel={t("Original quadrupole row [1]", "Fila del cuadripolo original [1]")} yLabel="Transfer resistance [Ω]"
      series={[
        { name: t("Observed ± assumed σ", "Observado ± σ supuesta"), values: model.observed, errors, points: true },
        { name: t("Forward prediction", "Predicción directa"), values: model.predicted },
        { name: t("Held-out observations", "Observaciones reservadas"), values: model.observed.map((v, i) => model.held.includes(i) ? v : Number.NaN), points: true },
      ]} />
    <Plot interactive x={x} selectedIndex={row} onSelect={onRow} pointLabels={labels}
      title={t("Signed prediction residual", "Residual de predicción con signo")}
      xLabel={t("Original quadrupole row [1]", "Fila del cuadripolo original [1]")} yLabel="Predicted − observed [Ω]" zeroCentered
      series={[{ name: t("Residual (Δ = prediction − observation)", "Residual (Δ = predicción − observación)"), values: model.residual, points: true }]} />
  </section>;
}
