import { useEffect, useRef, useState, type ChangeEvent, type PointerEvent } from "react";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { appBase } from "../science";
import {
  PHASE_RATE_HZ, PHASE_SAMPLES, PHASE_THRESHOLD, parseLocalTrace, parseNormalizedF32,
  parsePhaseBenchmark, parsePhaseManifest, sha256, verifiedFetch, type PhaseBenchmark,
  type PhaseManifest, type PhaseManifestEntry,
  type PhaseScores, type PhaseTrace,
} from "../phase-picker";
import { createPhaseSession, type PhaseSession } from "../phase-runtime";

const ASSET_BASE = `${appBase}data/phase/stead/`;
const COLORS = ["var(--color-accent)", "var(--color-accent-2)", "var(--color-magenta)"];
const formatTime = (sample: number) => `${(sample / PHASE_RATE_HZ).toFixed(2)} s`;

function envelope(values: Float32Array, start: number, end: number, plotWidth: number,
                  top: number, height: number, low: number, high: number): string {
  const count = end - start;
  const left = 44, inner = plotWidth - 60;
  const columns = Math.min(Math.round(inner), count);
  const points: string[] = [];
  for (let x = 0; x < columns; x++) {
    const a = start + Math.floor((x * count) / columns);
    const b = start + Math.max(1, Math.floor(((x + 1) * count) / columns));
    let min = Infinity, max = -Infinity;
    for (let i = a; i < Math.min(b, end); i++) {
      min = Math.min(min, values[i]); max = Math.max(max, values[i]);
    }
    const px = left + (x / Math.max(1, columns - 1)) * inner;
    const y = (value: number) => top + (1 - (value - low) / (high - low)) * height;
    points.push(`${x ? "L" : "M"}${px.toFixed(1)},${y(min).toFixed(1)}L${px.toFixed(1)},${y(max).toFixed(1)}`);
  }
  return points.join("");
}

function PhasePlot({ kind, trace, scores, start, duration, cursor, onCursor, record, es }: {
  kind: "waveform" | "scores"; trace: PhaseTrace; scores: PhaseScores | null;
  start: number; duration: number; cursor: number | null; onCursor: (sample: number | null) => void;
  record: PhaseManifestEntry | null; es: boolean;
}) {
  const figure = useRef<HTMLElement>(null);
  const [plotWidth, setPlotWidth] = useState(600);
  useEffect(() => {
    const element = figure.current;
    if (!element) return;
    const observer = new ResizeObserver(() => setPlotWidth(Math.max(280, Math.round(element.clientWidth - 16))));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const left = 44, right = plotWidth - 16, inner = right - left;
  const beginning = Math.round(start * PHASE_RATE_HZ);
  const end = Math.min(PHASE_SAMPLES, beginning + Math.round(duration * PHASE_RATE_HZ));
  const values = kind === "waveform" ? trace.channels : scores ? [
    scores.probabilities.subarray(0, PHASE_SAMPLES),
    scores.probabilities.subarray(PHASE_SAMPLES, 2 * PHASE_SAMPLES),
    scores.probabilities.subarray(2 * PHASE_SAMPLES),
  ] : null;
  const names = kind === "waveform" ? ["E", "N", "Z"] : ["N", "P", "S"];
  const visible = (sample: number | null) => sample !== null && sample >= beginning && sample < end;
  const x = (sample: number) => left + ((sample - beginning) / Math.max(1, end - beginning - 1)) * inner;
  const markers = scores && kind === "scores" ? [
    { label: "P", sample: scores.picks.P, color: COLORS[1], dashed: false },
    { label: "S", sample: scores.picks.S, color: COLORS[2], dashed: false },
    { label: es ? "P analista" : "analyst P", sample: record?.analyst_p_s == null ? null : Math.round(record.analyst_p_s * 100), color: COLORS[1], dashed: true },
    { label: es ? "S analista" : "analyst S", sample: record?.analyst_s_s == null ? null : Math.round(record.analyst_s_s * 100), color: COLORS[2], dashed: true },
  ] : [];
  const height = kind === "waveform" ? 320 : 250;
  const pointer = (event: PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const pixel = ((event.clientX - rect.left) / rect.width) * plotWidth;
    onCursor(Math.max(beginning, Math.min(end - 1, beginning + Math.round(((pixel - left) / inner) * (end - beginning - 1)))));
  };
  return <figure ref={figure} className="phase-plot">
    <figcaption>
      <strong>{kind === "waveform" ? (es ? "Forma de onda E/N/Z" : "E/N/Z waveform") : (es ? "Puntajes N/P/S" : "N/P/S scores")}</strong>
      <output>{cursor !== null && values
        ? `${formatTime(cursor)} · ${names.map((name, i) => `${name} ${values[i][cursor].toFixed(3)}`).join(" · ")}`
        : kind === "waveform" ? (es ? "Amplitud normalizada, sin dimensión" : "Normalized amplitude, dimensionless")
          : (es ? "Puntaje softmax, sin calibrar" : "Softmax score, uncalibrated")}</output>
    </figcaption>
    <svg viewBox={`0 0 ${plotWidth} ${height}`} role="img"
      aria-label={kind === "waveform" ? (es ? "Tres componentes medidas E N Z" : "Three measured E N Z components") : (es ? "Puntajes N P S calculados en navegador" : "Browser-computed N P S scores")}
      onPointerMove={pointer} onPointerLeave={() => onCursor(null)}>
      {kind === "waveform" ? names.map((name, i) => {
        const top = 19 + i * 99;
        return <g key={name}>
          <line x1={left} x2={right} y1={top + 47} y2={top + 47} className="chart-grid" />
          <text x="10" y={top + 51} className="phase-axis-label">{name}</text>
          {values && <path d={envelope(values[i], beginning, end, plotWidth, top, 94, -1.05, 1.05)} fill="none" stroke={COLORS[i]} strokeWidth="1.3" />}
        </g>;
      }) : <>
        {[0, 0.5, 0.8, 1].map(level => <g key={level}>
          <line x1={left} x2={right} y1={215 - level * 185} y2={215 - level * 185} className="chart-grid" />
          <text x={left - 6} y={219 - level * 185} textAnchor="end">{level.toFixed(1)}</text>
        </g>)}
        <line x1={left} x2={right} y1={215 - PHASE_THRESHOLD * 185} y2={215 - PHASE_THRESHOLD * 185} className="phase-threshold" />
        {values?.map((series, i) => <path key={names[i]}
          d={envelope(series, beginning, end, plotWidth, 30, 185, 0, 1)} fill="none" stroke={COLORS[i]} strokeWidth="1.5" />)}
        {markers.filter(marker => visible(marker.sample)).map(marker => <g key={marker.label}>
          <line x1={x(marker.sample!)} x2={x(marker.sample!)} y1="25" y2="215" stroke={marker.color}
            strokeWidth="1.5" strokeDasharray={marker.dashed ? "4 4" : undefined} />
          {!marker.dashed && <text x={x(marker.sample!) + 3} y="38" fill={marker.color} className="phase-marker-label">{marker.label}</text>}
        </g>)}
      </>}
      {[0, 0.5, 1].map(fraction => <text key={fraction} x={left + fraction * inner} y={height - 6}
        textAnchor={fraction === 0 ? "start" : fraction === 1 ? "end" : "middle"}>
        {(start + fraction * duration).toFixed(1)} s
      </text>)}
      {visible(cursor) && <line x1={x(cursor!)} x2={x(cursor!)} y1="15" y2={height - 27} className="cursor-line" />}
    </svg>
    <div className="phase-legend">{names.map((name, i) => <span key={name}><i style={{ background: COLORS[i] }} />{name}</span>)}
      {kind === "scores" && <span>{es ? "Línea punteada: analista · línea horizontal: 0,8" : "Dashed: analyst · horizontal line: 0.8"}</span>}
      <span>{es ? "Eje horizontal: tiempo desde inicio [s]" : "Horizontal axis: seconds from window start [s]"}</span>
    </div>
  </figure>;
}

function message(error: unknown): string { return error instanceof Error ? error.message : String(error); }

export function PhasePickerPanel() {
  const es = useShellLang() === "es";
  const t = (en: string, sp: string) => es ? sp : en;
  const session = useRef<PhaseSession | null>(null);
  const operation = useRef(0);
  const [manifest, setManifest] = useState<PhaseManifest | null>(null);
  const [benchmark, setBenchmark] = useState<PhaseBenchmark | null>(null);
  const [modelHash, setModelHash] = useState("");
  const [modelSource, setModelSource] = useState<"curated" | "local" | null>(null);
  const [traceChoice, setTraceChoice] = useState("local");
  const [localTrace, setLocalTrace] = useState<PhaseTrace | null>(null);
  const [trace, setTrace] = useState<PhaseTrace | null>(null);
  const [scores, setScores] = useState<PhaseScores | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [windowSeconds, setWindowSeconds] = useState(60);
  const [windowStart, setWindowStart] = useState(0);
  const [cursor, setCursor] = useState<number | null>(null);
  const record = manifest && traceChoice !== "local" ? manifest.records[Number(traceChoice)] ?? null : null;
  useEffect(() => () => { operation.current++; void session.current?.release(); }, []);

  async function installModel(bytes: ArrayBuffer, source: "curated" | "local", expectedHash?: string) {
    const digest = await sha256(bytes);
    if (expectedHash && digest !== expectedHash) throw new Error("ONNX SHA-256 differs from the asset manifest");
    const next = await createPhaseSession(bytes);
    const old = session.current;
    session.current = next;
    void old?.release();
    setModelHash(digest);
    setModelSource(source);
    setScores(null); setTrace(null); setElapsedMs(null);
  }

  async function loadCurated() {
    const ticket = ++operation.current;
    setBusy(true); setError(""); setScores(null); setTrace(null);
    try {
      const response = await fetch(`${ASSET_BASE}manifest.json`, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error(`Curated M13 assets are unavailable (HTTP ${response.status})`);
      const parsed = parsePhaseManifest(await response.json());
      const bytes = await verifiedFetch(`${ASSET_BASE}${parsed.model.file}`, parsed.model.sha256);
      if (bytes.byteLength !== parsed.model.bytes) throw new Error("ONNX model byte count differs from the manifest");
      const benchmarkBytes = await verifiedFetch(`${ASSET_BASE}${parsed.benchmark.file}`, parsed.benchmark.sha256);
      const heldout = parsePhaseBenchmark(JSON.parse(new TextDecoder().decode(benchmarkBytes)), parsed);
      if (ticket !== operation.current) return;
      await installModel(bytes, "curated", parsed.model.sha256);
      if (ticket !== operation.current) return;
      setManifest(parsed); setBenchmark(heldout); setTraceChoice("0");
    } catch (cause) { if (ticket === operation.current) setError(message(cause)); }
    finally { if (ticket === operation.current) setBusy(false); }
  }

  async function localModelChanged(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const ticket = ++operation.current;
    setBusy(true); setError(""); setScores(null);
    try {
      if (!file.name.toLowerCase().endsWith(".onnx") || file.size === 0 || file.size > 100_000_000)
        throw new Error("Supply a nonempty .onnx model no larger than 100 MB");
      await installModel(await file.arrayBuffer(), "local");
      setBenchmark(null);
    } catch (cause) { if (ticket === operation.current) setError(message(cause)); }
    finally { if (ticket === operation.current) setBusy(false); }
  }

  async function localTraceChanged(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(""); setScores(null); setTrace(null); setTraceChoice("local");
    try {
      if (!file.name.toLowerCase().endsWith(".json") || file.size === 0 || file.size > 2_000_000)
        throw new Error("Supply a trace JSON file no larger than 2 MB");
      const parsed = parseLocalTrace(JSON.parse(await file.text()));
      setLocalTrace(parsed);
    } catch (cause) { setLocalTrace(null); setError(message(cause)); }
  }

  async function run() {
    if (!session.current || (traceChoice === "local" && !localTrace) || record?.status === "qc-rejected") return;
    const ticket = ++operation.current;
    setBusy(true); setError(""); setScores(null); setTrace(null); setElapsedMs(null);
    try {
      let selected = localTrace;
      if (record) {
        const bytes = await verifiedFetch(`${ASSET_BASE}${record.waveform_file}`, record.waveform_sha256!);
        selected = parseNormalizedF32(bytes, record);
      }
      if (!selected) throw new Error("Select a valid trace before inference");
      const started = performance.now();
      const result = await session.current.run(selected);
      if (ticket !== operation.current) return;
      setTrace(selected); setScores(result); setElapsedMs(performance.now() - started);
      setWindowStart(0); setWindowSeconds(60);
    } catch (cause) { if (ticket === operation.current) setError(message(cause)); }
    finally { if (ticket === operation.current) setBusy(false); }
  }

  function exportScores() {
    if (!scores || !trace) return;
    const bytes = new ArrayBuffer(scores.probabilities.length * 4);
    const view = new DataView(bytes);
    scores.probabilities.forEach((value, i) => view.setFloat32(i * 4, value, true));
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([bytes], { type: "application/octet-stream" }));
    link.download = `${trace.traceId.replace(/[^a-zA-Z0-9._-]/g, "_")}-browser-probabilities.f32`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 30_000);
  }

  const labelPick = (phase: "P" | "S") => scores?.picks[phase] === null
    ? scores.reasons[phase] === "ps-separation"
      ? t("abstained: S−P < 0.4 s", "abstención: S−P < 0,4 s")
      : t("abstained: peak < 0.8", "abstención: máximo < 0,8")
    : scores ? `${formatTime(scores.picks[phase]!)} · ${scores.peaks[phase].toFixed(4)}` : "—";

  return <section id="phase-picker" className="phase-picker" aria-label={t("M13 browser phase picker", "Detector de fases M13 en navegador")}>
    <div className="phase-heading">
      <div><span className="small-caps">M13 · ONNX Runtime Web · 100 Hz</span>
        <h2>{t("P/S arrivals from three-component waveforms", "Llegadas P/S desde ondas de tres componentes")}</h2>
        <p>{t("The browser runs the selected ONNX model on a 60 s E/N/Z window. P/S times are candidate arrivals relative to window start. Scores are uncalibrated; a pick is not an event location or ground-velocity measurement.",
          "El navegador ejecuta el modelo ONNX sobre una ventana E/N/Z de 60 s. Los tiempos P/S son llegadas candidatas relativas al inicio. Los puntajes no están calibrados; una marca no localiza el evento ni mide velocidad del suelo.")}</p>
      </div>
      <button className="btn" onClick={loadCurated} disabled={busy}>{t("Load reviewed STEAD assets", "Cargar archivos STEAD revisados")}</button>
    </div>
    <div className="phase-controls">
      <details className="phase-local-files"><summary>{t("Use local model or trace files", "Usar archivos locales de modelo o traza")}</summary>
        <div><label className="select-control"><span>{t("Local ONNX model", "Modelo ONNX local")}</span><input type="file" accept=".onnx" onChange={localModelChanged} disabled={busy} /></label>
        <label className="select-control"><span>{t("Local E/N/Z trace JSON", "Traza JSON E/N/Z local")}</span><input type="file" accept=".json,application/json" onChange={localTraceChanged} disabled={busy} /></label></div>
      </details>
      {manifest && <label className="select-control"><span>{t("Predeclared browser selection (24)", "Selección web predeclarada (24)")}</span>
        <select className="select" aria-label={t("STEAD trace", "Traza STEAD")} value={traceChoice} onChange={event => {
          operation.current++; setTraceChoice(event.target.value); setScores(null); setTrace(null); setError("");
        }}>
          {localTrace && <option value="local">{t("Local trace", "Traza local")}</option>}
          {manifest.records.map((item, index) => <option key={item.trace_id} value={index}>
            {String(index + 1).padStart(2, "0")} · {item.station_id} · {item.category === "noise" ? t("noise", "ruido") : t("earthquake", "sismo")}{item.status === "qc-rejected" ? ` · ${t("QC rejected", "QC rechazada")}` : ""}
          </option>)}
        </select>
      </label>}
      <button className="btn" onClick={run} disabled={busy || !modelHash || (traceChoice === "local" ? !localTrace : record?.status !== "qc-valid")}>{busy ? t("Processing…", "Procesando…") : t("Run browser inference", "Ejecutar inferencia web")}</button>
      <button className="btn" onClick={exportScores} disabled={!scores}>{t("Export N/P/S scores (.f32)", "Exportar puntajes N/P/S (.f32)")}</button>
    </div>
    {error && <p role="alert" className="phase-error">{error}</p>}
    {record?.status === "qc-rejected" && <p role="status" className="phase-error">{t("QC rejected; no waveform asset and no browser inference for this preselected trace:", "QC rechazada; esta traza preseleccionada no tiene archivo de onda ni inferencia web:")} {record.qc_reason}</p>}
    <div className="phase-ledger">
      <p><strong>{t("Model", "Modelo")}:</strong> {modelSource === "curated" ? t("manifest-linked ONNX", "ONNX vinculado al manifiesto") : modelSource === "local" ? t("local file, provenance unverified", "archivo local, procedencia sin verificar") : t("none loaded", "ninguno cargado")}
        {modelHash && <><br /><code>SHA-256 {modelHash}</code></>}</p>
      <p><strong>{t("Trace", "Traza")}:</strong> {record ? `${record.trace_id} · ${record.network}/${record.channel} · ${record.status}` : localTrace ? `${localTrace.traceId} · ${t("local metadata only", "sólo metadatos locales")}` : t("none selected", "ninguna seleccionada")}
        <br />{t("Input: unrestituted counts or normalized counts; no response correction, gap filling or resampling.", "Entrada: conteos sin corregir o normalizados; sin corrección instrumental, relleno de huecos ni remuestreo.")}</p>
      <p><strong>{t("Population", "Población")}:</strong> {manifest ? t("Browser display: 23 QC-valid / 24 selected; one retained QC failure. Full held-out benchmark: 6,000 selected, separate from this display.",
        "Vista web: 23 válidas de 24 seleccionadas; se conserva una falla QC. Benchmark reservado completo: 6.000, separado de esta vista.") : t("No curated held-out population loaded.", "Sin población reservada curada cargada.")}</p>
    </div>
    {manifest && <p className="phase-source">{manifest.source.authors} · {manifest.source.dataset} · <a href={`https://doi.org/${manifest.source.doi}`}>{manifest.source.citation}</a> · <a href={manifest.source.license_url}>{manifest.source.license}</a>.
      {" "}{manifest.source.modification}</p>}
    {scores && trace && <>
      <div className="phase-arrivals">
        <div><span>P · {t("candidate", "candidata")}</span><strong>{labelPick("P")}</strong></div>
        <div><span>S · {t("candidate", "candidata")}</span><strong>{labelPick("S")}</strong></div>
        <div><span>{t("Browser inference", "Inferencia web")}</span><strong>{elapsedMs?.toFixed(0)} ms</strong></div>
      </div>
      <div className="phase-window-controls">
        <label className="select-control"><span>{t("Display span", "Duración visible")}</span><select className="select" value={windowSeconds} onChange={e => { setWindowSeconds(Number(e.target.value)); setWindowStart(0); }}>
          {[60, 20, 10, 5].map(seconds => <option key={seconds} value={seconds}>{seconds} s</option>)}</select></label>
        <label className="select-control"><span>{t("Display start", "Inicio visible")} · {windowStart.toFixed(1)} s</span>
          <input type="range" min="0" max={60 - windowSeconds} step="0.1" value={windowStart} disabled={windowSeconds === 60} onChange={e => setWindowStart(Number(e.target.value))} /></label>
      </div>
      <div className="phase-plots">
        <PhasePlot kind="waveform" trace={trace} scores={scores} start={windowStart} duration={windowSeconds} cursor={cursor} onCursor={setCursor} record={record} es={es} />
        <PhasePlot kind="scores" trace={trace} scores={scores} start={windowStart} duration={windowSeconds} cursor={cursor} onCursor={setCursor} record={record} es={es} />
      </div>
      <p className="plot-note">{t("Arrival selection used all 6,000 raw ONNX output samples before display reduction. Solid markers are accepted model picks; dashed markers are STEAD analyst references, not ground truth. A missing marker is an abstention or a missing reference.",
        "Las llegadas se eligieron con las 6.000 muestras originales de ONNX antes de reducir la visualización. Marcas continuas: predicciones aceptadas; discontinuas: referencias de analista STEAD, no verdad física. Marca ausente: abstención o referencia inexistente.")}</p>
      {record && <p className="plot-note">{t("STEAD analyst reference", "Referencia de analista STEAD")}: P {record.analyst_p_s == null ? "—" : `${record.analyst_p_s.toFixed(2)} s`} · S {record.analyst_s_s == null ? "—" : `${record.analyst_s_s.toFixed(2)} s`}.</p>}
    </>}
    {benchmark && modelSource === "curated" && <div className="phase-benchmark">
      <h3>{t("Offline held-out P/S benchmark", "Benchmark P/S reservado offline")}</h3>
      <p>{t(`All ${benchmark.selected.toLocaleString("en-US")} selected STEAD test traces, including ${benchmark.qc_rejected} QC rejections counted as unpicked; ${benchmark.valid} QC-valid. F1 uses ±0.5 s agreement with manual picks. This is not the 24-trace browser display or a browser accuracy score.`,
        `Las ${benchmark.selected.toLocaleString("es-CL")} trazas de prueba STEAD, incluidas ${benchmark.qc_rejected} rechazadas por QC contadas sin marca; ${benchmark.valid} válidas. F1 usa acuerdo ±0,5 s con marcas manuales. No es la vista web de 24 ni una cifra de precisión web.`)}</p>
      <div className="table-scroll"><table className="cmp-table"><thead><tr>
        <th>{t("Method", "Método")}</th><th>{t("Phase", "Fase")}</th><th>F1 @ ±0.5 s</th>
        <th>{t("Within tolerance / reference", "Dentro de tolerancia / referencia")}</th>
        <th>{t("Median |timing error|", "Mediana |error temporal|")}</th>
      </tr></thead><tbody>
        {(["M08", "M13"] as const).flatMap(method => (["P", "S"] as const).map(phase => {
          const row = benchmark.nominal[method][phase];
          return <tr key={`${method}-${phase}`}><td>{method}</td><td>{phase}</td>
            <td>{row.f1_at_0p5s.toFixed(4)}</td><td>{row.correct_within_0p5s} / {row.reference_count}</td>
            <td>{row.timing_absolute_median_s === null ? "—" : `${row.timing_absolute_median_s.toFixed(2)} s`}</td></tr>;
        }))}
      </tbody></table></div>
    </div>}
  </section>;
}
