import { useEffect, useRef, useState } from "react";
import { runMagneticLocal, type MagneticLocalMapping, type MagneticLocalOptions, type MagneticLocalProgress, type MagneticLocalRun } from "../api/magnetic-local";
import { color } from "../science";

const MAPPING: (keyof MagneticLocalMapping)[] = ["easting", "northing", "value", "line_id", "line_role", "sensor_height_m", "sample_order"];
const DEFAULT_MAPPING: MagneticLocalMapping = { easting: "easting", northing: "northing", value: "value", line_id: "line_id", line_role: "line_role", sensor_height_m: "sensor_height_m", sample_order: "sample_order" };
type LineSummary = { line_id: string; role: string; sample_count: number; coordinate_extent_m: { easting: number[]; northing: number[] }; sensor_height_m: { minimum: number; median: number; maximum: number; mad: number; qc_outlier_rows: number[] } };
type Crossing = { line_a: string; role_a: string; line_b: string; role_b: string; easting_m: number; northing_m: number; difference_a_minus_b: number };

function download(run: MagneticLocalRun) {
  const blob = new Blob([JSON.stringify({ schema: "magnetic-flightline-browser-local-bundle-1", ...run }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob), anchor = document.createElement("a");
  anchor.href = url; anchor.download = `${run.execution.original_csv_filename.replace(/\.csv$/i, "")}-m03-local-result.json`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

function MaskedGrid({ run, es }: { run: MagneticLocalRun; es: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null), grid = run.result.grid;
  useEffect(() => {
    const canvas = ref.current; if (!canvas) return;
    const ny = grid.values.length, nx = grid.x_easting_m.length;
    canvas.width = nx; canvas.height = ny;
    const context = canvas.getContext("2d"); if (!context) return;
    const image = context.createImageData(nx, ny), mask = grid.support_mask;
    let low = Infinity, high = -Infinity;
    for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) if (mask[y][x]) { low = Math.min(low, grid.values[y][x]); high = Math.max(high, grid.values[y][x]); }
    const fallback = getComputedStyle(canvas).backgroundColor.match(/[\d.]+/g)?.slice(0, 3).map(Number) ?? [90, 95, 100];
    for (let y = 0; y < ny; y++) for (let x = 0; x < nx; x++) {
      const sourceY = ny - 1 - y; // northing increases upward; canvas row zero is the north edge.
      const offset = (y * nx + x) * 4;
      const rgb = mask[sourceY][x] ? color(grid.values[sourceY][x], [low, high], "field").match(/[\d.]+/g)?.slice(0, 3).map(Number) : fallback;
      if (!rgb) continue;
      image.data[offset] = rgb[0]; image.data[offset + 1] = rgb[1]; image.data[offset + 2] = rgb[2]; image.data[offset + 3] = 255;
    }
    context.putImageData(image, 0, 0);
  }, [grid]);
  return <canvas ref={ref} role="img" aria-label={es ? "Grilla de interpolación con celdas sin soporte enmascaradas" : "Interpolation grid with unsupported cells masked"} style={{ display: "block", width: "100%", maxWidth: 820, maxHeight: 560, objectFit: "contain", imageRendering: "pixelated", backgroundColor: "var(--color-surface-2)" }} />;
}

export function MagneticLocalWorkbench({ es, onCurated }: { es: boolean; onCurated: () => void }) {
  const t = (en: string, sp: string) => es ? sp : en;
  const [file, setFile] = useState<File | null>(null);
  const [mapping, setMapping] = useState<MagneticLocalMapping>(DEFAULT_MAPPING);
  const [source, setSource] = useState({ source_id: "local:user-provided-csv", citation: "", rights_decision: "", processing_state: "", value_unit: "nT", value_quantity: "", sensor_height_reference: "" });
  const [crs, setCrs] = useState("");
  const [projected, setProjected] = useState(false);
  const [spacing, setSpacing] = useState("100");
  const [holdout, setHoldout] = useState("0.2");
  const [seed, setSeed] = useState("m03-local-v1");
  const [progress, setProgress] = useState<MagneticLocalProgress | null>(null);
  const [run, setRun] = useState<MagneticLocalRun | null>(null);
  const [problem, setProblem] = useState("");
  const [controlsOpen, setControlsOpen] = useState(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);
  const updateSource = (key: keyof typeof source, value: string) => setSource(previous => ({ ...previous, [key]: value }));
  const execute = async () => {
    if (!file || !projected) return;
    const options: MagneticLocalOptions = {
      source, frame: { crs: crs.trim(), coordinates_are_projected: true, linear_unit: "m" }, mapping,
      settings: { grid_spacing_m: Number(spacing), holdout_fraction: Number(holdout), seed: seed.trim() },
    };
    controller.current?.abort();
    const next = new AbortController(); controller.current = next;
    setProblem(""); setRun(null); setProgress({ stage: "starting" });
    try {
      const completed = await runMagneticLocal(file, options, { signal: next.signal, onProgress: setProgress });
      setRun(completed); setProgress(null);
    } catch (error) {
      if (!next.signal.aborted) setProblem(error instanceof Error ? error.message : String(error));
      setProgress(null);
    } finally { if (controller.current === next) controller.current = null; }
  };
  const busy = progress !== null;
  const lineQc = run?.result.geometry_qc as { lines?: LineSummary[]; crossover_interpolation_qc?: { intersection_count: number; mean_signed_difference: number | null; mae: number | null; rmse: number | null; crossings: Crossing[]; interpretation: string } } | undefined;
  const lines = lineQc?.lines ?? [], crossings = lineQc?.crossover_interpolation_qc?.crossings ?? [];
  const extents = lines.map(line => line.coordinate_extent_m).filter(extent => Array.isArray(extent.easting) && Array.isArray(extent.northing));
  const bounds = extents.length ? { xmin: Math.min(...extents.map(e => e.easting[0])), xmax: Math.max(...extents.map(e => e.easting[1])), ymin: Math.min(...extents.map(e => e.northing[0])), ymax: Math.max(...extents.map(e => e.northing[1])) } : null;
  const stageLabel = progress?.stage === "loading-runtime" ? t("Loading browser runtime…", "Cargando el entorno del navegador…") : progress?.stage === "loading-scientific-packages" ? t("Loading NumPy and SciPy…", "Cargando NumPy y SciPy…") : progress?.stage === "processing" ? t("Processing the local CSV…", "Procesando el CSV local…") : t("Starting…", "Iniciando…");

  return <div className="page-body wide workbench processing-workbench m03-flightline-workbench">
    <aside className={`instrument-sidebar processing-sidebar ${controlsOpen ? "expanded" : ""}`}>
      <nav className="processing-actions" aria-label={t("Processing tools", "Herramientas de procesamiento")}><button className="btn" onClick={onCurated}>{t("Return to experiments", "Volver a experimentos")}</button></nav>
      <div className="instrument-brand"><span className="instrument-kicker">M03 · MAGNETIC SURVEY · BROWSER LOCAL</span><h1>{t("Flight-line QC and gridding", "QC de líneas de vuelo y grilla")}</h1><p>{t("Select a CSV, declare its physical columns and coordinate frame, then run the shared Python/SciPy processor in a Web Worker.", "Seleccione un CSV, declare sus columnas físicas y marco de coordenadas; luego ejecute el procesador Python/SciPy compartido en un Web Worker.")}</p></div>
      <button className="btn mobile-controls-toggle" aria-expanded={controlsOpen} onClick={() => setControlsOpen(value => !value)}>{controlsOpen ? t("Close local controls", "Cerrar controles locales") : t("Local magnetic controls", "Controles magnéticos locales")}</button>
      <div className="processing-controls">
        <label className="select-control"><span>{t("Local CSV file", "Archivo CSV local")}</span><input className="select" type="file" accept=".csv,text/csv" onChange={event => { setFile(event.currentTarget.files?.[0] ?? null); setRun(null); setProblem(""); }}/></label>
        <p className="project-note">{t("Survey bytes stay in this browser tab and are never uploaded. The pinned WebAssembly runtime and NumPy/SciPy load lazily from jsDelivr; the first run downloads about 54 MiB. Bounds: 16 MiB source, 25,000 rows, 100,000 grid cells, 2,000,000 crossover segment pairs and 180 seconds.", "Los bytes del levantamiento permanecen en esta pestaña y nunca se cargan al servidor. El entorno WebAssembly fijado y NumPy/SciPy se cargan bajo demanda desde jsDelivr; la primera ejecución descarga cerca de 54 MiB. Límites: archivo de 16 MiB, 25.000 filas, 100.000 celdas de grilla, 2.000.000 pares de segmentos y 180 segundos.")}</p>
        <h2>{t("Explicit CSV column map", "Mapa explícito de columnas CSV")}</h2>
        {MAPPING.map(key => <label className="select-control" key={key}><span>{t(({easting:"Easting",northing:"Northing",value:"Field value",line_id:"Flight/tie line ID",line_role:"Line role",sensor_height_m:"Sensor height [m]",sample_order:"Acquisition order"} as const)[key], ({easting:"Este",northing:"Norte",value:"Valor del campo",line_id:"ID de línea vuelo/amarre",line_role:"Rol de línea",sensor_height_m:"Altura del sensor [m]",sample_order:"Orden de adquisición"} as const)[key])}</span><input className="select" value={mapping[key]} onChange={event => setMapping(previous => ({ ...previous, [key]: event.target.value }))}/></label>)}
        <h2>{t("Source and physical declarations", "Declaraciones de fuente y físicas")}</h2>
        <label className="select-control"><span>{t("Source identifier", "Identificador de fuente")}</span><input className="select" value={source.source_id} onChange={e => updateSource("source_id", e.target.value)}/></label>
        <label className="select-control"><span>{t("Citation / provider", "Cita / proveedor")}</span><input className="select" value={source.citation} onChange={e => updateSource("citation", e.target.value)} /></label>
        <label className="select-control"><span>{t("Rights decision", "Decisión de derechos")}</span><input className="select" value={source.rights_decision} onChange={e => updateSource("rights_decision", e.target.value)} /></label>
        <label className="select-control"><span>{t("Known processing and unknowns", "Procesamiento conocido e incógnitas")}</span><textarea className="select" value={source.processing_state} onChange={e => updateSource("processing_state", e.target.value)} /></label>
        <label className="select-control"><span>{t("Measured quantity", "Magnitud medida")}</span><input className="select" value={source.value_quantity} onChange={e => updateSource("value_quantity", e.target.value)} placeholder="total-field anomaly" /></label>
        <label className="select-control"><span>{t("Value unit", "Unidad del valor")}</span><input className="select" value={source.value_unit} onChange={e => updateSource("value_unit", e.target.value)} /></label>
        <label className="select-control"><span>{t("Sensor-height reference", "Referencia de altura del sensor")}</span><input className="select" value={source.sensor_height_reference} onChange={e => updateSource("sensor_height_reference", e.target.value)} placeholder={t("above ground or named vertical datum", "sobre terreno o datum vertical indicado")}/></label>
        <label className="select-control"><span>{t("Projected coordinate reference system", "Sistema de referencia de coordenadas proyectadas")}</span><input className="select" value={crs} onChange={e => setCrs(e.target.value)} placeholder="EPSG:32719"/></label>
        <label className="select-control"><span><input type="checkbox" checked={projected} onChange={e => setProjected(e.target.checked)}/> {t("Coordinates are projected metres", "Las coordenadas son metros proyectados")}</span></label>
        <h2>{t("Processing controls", "Controles de procesamiento")}</h2>
        <label className="select-control"><span>{t("Grid spacing [m]", "Espaciamiento de grilla [m]")}</span><input className="select" type="number" min="1" max="100000" step="any" value={spacing} onChange={e => setSpacing(e.target.value)}/></label>
        <label className="select-control"><span>{t("Whole-line holdout fraction", "Fracción retenida por líneas completas")}</span><input className="select" type="number" min="0.05" max="0.5" step="0.01" value={holdout} onChange={e => setHoldout(e.target.value)}/></label>
        <label className="select-control"><span>{t("Deterministic split seed", "Semilla determinista de partición")}</span><input className="select" maxLength={128} value={seed} onChange={e => setSeed(e.target.value)}/></label>
        <button className="btn primary" disabled={!file || !projected || !crs.trim() || busy || MAPPING.some(key => !mapping[key].trim()) || Object.values(source).some(value => !value.trim())} onClick={() => void execute()}>{t("Run locally in this browser", "Ejecutar localmente en este navegador")}</button>
        {busy && <><p role="status" aria-live="polite" className="project-note">{stageLabel}</p><button className="btn" onClick={() => controller.current?.abort()}>{t("Cancel local run", "Cancelar ejecución local")}</button></>}
        {problem && <p role="alert" className="project-error">{problem}</p>}
      </div>
    </aside>
    <main className="instrument-main processing-main">
      <header className="processing-status"><strong>{t("M03 local execution", "Ejecución local M03")}</strong><span>{file?.name ?? t("No file selected", "Sin archivo seleccionado")}</span></header>
      {!run && <section className="project-note"><h2>{t("What this calculation does", "Qué calcula este método")}</h2><p>{t("The processor reports flight/tie geometry, robust sensor-height flags, segment-interpolated crossover differences, deterministic complete-line holdout scores, and a piecewise-linear Delaunay grid. Tie lines do not fit the grid. Unsupported grid cells remain masked.", "El procesador informa geometría de vuelo/amarre, marcas robustas de altura, diferencias interpoladas en cruces, puntajes deterministas con líneas completas retenidas y una grilla Delaunay lineal por tramos. Las líneas de amarre no ajustan la grilla. Las celdas sin soporte permanecen enmascaradas.")}</p><p>{t("It applies no diurnal, IGRF, lag, terrain, height continuation, leveling, or subsurface inversion. The holdout measures spatial interpolation, not geological-model accuracy.", "No aplica corrección diurna, IGRF, retardo, terreno, continuación de altura, nivelación ni inversión del subsuelo. La reserva evalúa interpolación espacial, no precisión de un modelo geológico.")}</p></section>}
      {run && <>
        <section className="processing-summary"><span>{t("Held-out rows", "Filas retenidas")} {run.result.heldout_interpolation.supported_heldout_row_count}/{run.result.heldout_interpolation.heldout_row_count}</span><span>{t("Coverage", "Cobertura")} {(100*run.result.heldout_interpolation.coverage_fraction).toFixed(1)}%</span><span>MAE {run.result.heldout_interpolation.mae === null ? "—" : `${run.result.heldout_interpolation.mae.toPrecision(5)} ${run.result.configuration.value_unit ?? run.result.source.value_unit}`}</span><span>RMSE {run.result.heldout_interpolation.rmse === null ? "—" : `${run.result.heldout_interpolation.rmse.toPrecision(5)} ${run.result.configuration.value_unit ?? run.result.source.value_unit}`}</span><button className="btn" onClick={() => download(run)}>{t("Export result and provenance JSON", "Exportar JSON de resultados y procedencia")}</button></section>
        <section className="project-note"><h2>{t("Survey line extents and height QC", "Extensión de líneas y QC de altura")}</h2><p>{t("Extent boxes use only the per-line minimum/maximum coordinates returned by the processor; they do not reconstruct acquisition paths.", "Las cajas muestran solo coordenadas mínimas/máximas por línea; no reconstruyen trayectorias de adquisición.")}</p>{bounds && <svg viewBox="0 0 760 320" role="img" aria-label={t("Flight and tie line coordinate extents", "Extensiones de coordenadas de vuelo y amarre")} style={{ width:"100%", maxHeight:360, background:"var(--color-surface-2)" }}>{lines.map(line => { const e=line.coordinate_extent_m; const x0=90+(e.easting[0]-bounds.xmin)/Math.max(1,bounds.xmax-bounds.xmin)*600, x1=90+(e.easting[1]-bounds.xmin)/Math.max(1,bounds.xmax-bounds.xmin)*600; const y0=270-(e.northing[0]-bounds.ymin)/Math.max(1,bounds.ymax-bounds.ymin)*230, y1=270-(e.northing[1]-bounds.ymin)/Math.max(1,bounds.ymax-bounds.ymin)*230; return <g key={`${line.role}-${line.line_id}`}><rect x={Math.min(x0,x1)} y={Math.min(y0,y1)} width={Math.max(3,Math.abs(x1-x0))} height={Math.max(3,Math.abs(y1-y0))} fill={line.role === "tie" ? "var(--color-fg-subtle)" : "var(--color-accent)"} opacity=".72"/><title>{line.line_id} · {line.role} · {line.sample_count} rows · height median {line.sensor_height_m.median} m · {line.sensor_height_m.qc_outlier_rows.length} flags</title></g>; })}<text x="390" y="306" textAnchor="middle">{t("Easting [m]","Este [m]")}</text><text x="18" y="160" transform="rotate(-90 18 160)" textAnchor="middle">{t("Northing [m]","Norte [m]")}</text></svg>}
          <div className="processing-summary">{lines.map(line => <span key={`${line.role}-${line.line_id}`}>{line.line_id} · {line.role} · n={line.sample_count} · z median {line.sensor_height_m.median.toPrecision(5)} m · {line.sensor_height_m.qc_outlier_rows.length} {t("height flags","marcas de altura")}</span>)}</div>
        </section>
        <section className="project-note"><h2>{t("Interpolated crossover QC", "QC interpolado de cruces")}</h2><p>{lineQc?.crossover_interpolation_qc?.interpretation} · {t("intersections","intersecciones")} {lineQc?.crossover_interpolation_qc?.intersection_count}; MAE {lineQc?.crossover_interpolation_qc?.mae?.toPrecision(5) ?? "—"} {run.result.source.value_unit}; RMSE {lineQc?.crossover_interpolation_qc?.rmse?.toPrecision(5) ?? "—"} {run.result.source.value_unit}</p>{crossings.length>0&&<svg viewBox="0 0 760 280" role="img" aria-label={t("Flight minus tie residual at geometric crossovers", "Residuo vuelo menos amarre en cruces geométricos")} style={{width:"100%",maxHeight:320,background:"var(--color-surface-2)"}}>{crossings.map((crossing,i)=>{const min=Math.min(...crossings.map(c=>c.difference_a_minus_b)),max=Math.max(...crossings.map(c=>c.difference_a_minus_b));const x=80+i/Math.max(1,crossings.length-1)*640,y=240-(crossing.difference_a_minus_b-min)/Math.max(1e-12,max-min)*180;return <g key={`${crossing.line_a}-${crossing.line_b}-${i}`}><circle cx={x} cy={y} r="4" fill="var(--color-accent)"/><title>{crossing.line_a} − {crossing.line_b}: {crossing.difference_a_minus_b.toPrecision(6)} {run.result.source.value_unit}</title></g>})}<text x="380" y="270" textAnchor="middle">{t("Crossover index","Índice de cruce")}</text><text x="18" y="140" transform="rotate(-90 18 140)" textAnchor="middle">{t("Flight − tie [source unit]","Vuelo − amarre [unidad fuente]")}</text></svg>}<p>{t("These differences are diagnostics only. No tie-line leveling or value correction is applied.", "Estas diferencias son solo diagnósticos. No se aplica nivelación ni corrección de valores.")}</p></section>
        <section className="project-note"><h2>{t("Supported Delaunay interpolation grid", "Grilla de interpolación Delaunay soportada")}</h2><MaskedGrid run={run} es={es}/><p>{t("Grey cells fall outside the fitted convex hull. The separate support mask, not the encoded zeros, determines which cells contain predictions.", "Las celdas grises quedan fuera de la envolvente convexa de ajuste. La máscara de soporte, no los ceros de codificación, determina qué celdas tienen predicción.")}</p><p>{t("Easting [m]","Este [m]")}: {run.result.grid.x_easting_m[0]}–{run.result.grid.x_easting_m.at(-1)} · {t("Northing [m]","Norte [m]")}: {run.result.grid.y_northing_m[0]}–{run.result.grid.y_northing_m.at(-1)} · {t("Spacing","Espaciamiento")}: {String(run.result.configuration.grid_spacing_m)} m · {t("Supported cells","Celdas soportadas")}: {run.result.grid.support_mask.flat().filter(Boolean).length}/{run.result.grid.support_mask.flat().length}</p></section>
        <section className="project-note"><h2>{t("Blocked-line evaluation", "Evaluación con líneas retenidas")}</h2><p>{t("Fit lines","Líneas de ajuste")}: {run.result.split.fit_line_ids.join(", ")} · {t("held-out lines","líneas retenidas")}: {run.result.split.holdout_line_ids.join(", ")}</p><p>{run.result.heldout_interpolation.interpretation}</p><details className="processing-provenance"><summary>{t("Source, runtime and limitations", "Fuente, entorno y límites")}</summary><p>{run.result.source.citation} · {run.result.source.rights_decision} · {run.result.source.processing_state}</p><p>SHA-256 CSV <code>{run.execution.original_csv_sha256}</code></p><p>SHA-256 pipeline <code>{run.execution.python_pipeline_sha256}</code></p><p>{run.execution.lane} · Pyodide {run.execution.pyodide_version} · NumPy {run.execution.numpy_version} · SciPy {run.execution.scipy_version} · {run.execution.original_csv_bytes.toLocaleString()} B</p><p>{run.execution.runtime_reused ? t("Warm worker", "Worker reutilizado") : t("Worker initialized", "Worker inicializado")} · {t("startup", "inicio")}: {run.execution.runtime_load_ms.toFixed(0)} ms · {t("processing", "procesamiento")}: {run.execution.processing_ms.toFixed(0)} ms · {t("worker total", "total del worker")}: {run.execution.total_worker_ms.toFixed(0)} ms · {t("WASM heap capacity", "capacidad de memoria WASM")}: {run.execution.wasm_heap_capacity_bytes === null ? t("unavailable", "no disponible") : `${run.execution.wasm_heap_capacity_bytes.toLocaleString()} B`}</p><ul>{run.result.limitations.map((item,i)=><li key={i}>{item}</li>)}</ul><p>{t("Synthetic or user-supplied data have provenance and scientific status only as declared by their owner. A browser calculation does not establish independent validation.", "Los datos sintéticos o aportados por el usuario tienen la procedencia y estatus científico que declara su propietario. Un cálculo en navegador no constituye validación independiente.")}</p></details></section>
      </>}
      <p className="processing-scope">{t("Execution lane: browser-local WebAssembly. The original survey bytes are not uploaded. Runtime/package downloads do not contain survey data. Full local Python pipelines remain available for files or operations outside these browser bounds.", "Ejecución: WebAssembly local en navegador. Los bytes originales no se cargan al servidor. Las descargas del entorno/paquetes no contienen datos del levantamiento. Las tuberías completas de Python local siguen disponibles para archivos u operaciones fuera de estos límites.")}</p>
    </main>
  </div>;
}
