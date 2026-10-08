import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ApiClient, ApiHttpError } from "../api/client";
import { LifecycleApi, type ProjectView } from "../api/lifecycle";
import type { RawAsset } from "../api/contracts";
import { ProcessingApi } from "../api/processing";
import { FLAG_METHOD, M05_METHOD, isFlagJob, isGravityReceipt, isEdiReceipt, isMtJob, type ProjectDatasetReceipt, type ProjectProcessingJob, type FlagResult, type GravityDataset, type MethodEligibility, type ProcessingState } from "../api/processing-contracts";
import { GravityStationInstrument } from "./GravityStationInstrument";
import { MtProjectWorkbench } from "./MtProjectWorkbench";
import { ProfileProjectWorkbench } from "./ProfileProjectWorkbench";
import { ResultBundleInput } from "./ResultBundleInput";
import { readSavedResult } from "./result-view-data";

export function processingProblem(error: unknown, es: boolean): string {
  const t = (en: string, sp: string) => es ? sp : en;
  const guidance: Record<string, [string, string]> = {
    dataset_value_invalid: ["Correct the nonnumeric or nonfinite CSV value.", "Corrija el valor CSV no numérico o no finito."],
    dataset_uncertainty_invalid: ["Every station needs positive sigma in mGal.", "Cada estación necesita sigma positiva en mGal."],
    dataset_station_invalid: ["Station IDs must be nonblank and unique.", "Los ID de estación deben existir y ser únicos."],
    dataset_geometry_invalid: ["Check six distinct column declarations and unique XYZ station coordinates.", "Revise seis columnas distintas y coordenadas XYZ únicas."],
    dataset_columns_invalid: ["The CSV must contain exactly the six declared columns in every row.", "El CSV debe contener exactamente las seis columnas declaradas en cada fila."],
    dataset_physics_ineligible: ["This adapter requires projected xy metres, vertical metres, mGal and an explicit sigma column. Re-upload with corrected declarations; original metadata is immutable.", "Este adaptador requiere xy proyectadas en metros, vertical en metros, mGal y columna sigma explícita. Cargue de nuevo con declaraciones corregidas; los metadatos originales son inmutables."],
    dataset_format_ineligible: ["This frontend supports the gravity station CSV processing adapter.", "Esta interfaz admite el adaptador de procesamiento CSV gravimétrico."],
    dataset_row_limit: ["Supply 4–4096 stations.", "Proporcione 4–4096 estaciones."],
    dataset_too_large: ["This adapter accepts at most 2 MiB.", "Este adaptador acepta hasta 2 MiB."],
    dataset_csv_invalid: ["Check UTF-8 CSV syntax and column values.", "Revise la sintaxis CSV UTF-8 y los valores."],
    dataset_exists: ["This original already has a dataset. Refresh the dataset list.", "Este original ya tiene un conjunto. Actualice la lista."],
    active_job_limit: ["An account already has queued/running work. Wait or cancel it before a new submission.", "La cuenta ya tiene trabajo en cola o ejecutándose. Espere o cancélelo antes de enviar otro."],
    job_queue_full: ["The queue is full. Retry later.", "La cola está llena. Reintente más tarde."],
    job_resource_ineligible: ["The dataset exceeds the processing method resource limits.", "El conjunto excede los límites de recursos del método."],
    account_quota_exceeded: ["The account private-byte quota is exhausted.", "Se agotó la cuota de bytes privados de la cuenta."],
    method_ineligible: ["The API rejected this method for the selected dataset. Refresh eligibility.", "La API rechazó el método para este conjunto. Actualice la elegibilidad."],
    derived_integrity_failed: ["Stored derivative integrity failed. Operator review is required.", "Falló la integridad del derivado almacenado. Se requiere revisión del operador."],
    raw_integrity_failed: ["The original differs from its receipt. Operator review is required.", "El original difiere de su recibo. Se requiere revisión del operador."],
    result_not_ready: ["The job has no successful result yet. Refresh status.", "El trabajo aún no tiene resultado exitoso. Actualice el estado."],
    job_terminal: ["This job is already terminal. Refresh its status.", "El trabajo ya terminó. Actualice su estado."],
    csrf_invalid: ["The security token expired. Retry the action.", "El código de seguridad expiró. Reintente la acción."],
  };
  if (error instanceof ApiHttpError) {
    const base = error.status === 401 ? t("Session expired. Sign in to reload private data.", "La sesión expiró. Inicie sesión para volver a cargar datos privados.") : guidance[error.code] ? t(...guidance[error.code]) : error.status === 404 ? t("Project or item not found for this account.", "Proyecto o elemento no encontrado para esta cuenta.") : t("The service rejected the request.", "El servicio rechazó la solicitud.");
    return `${base} (${error.code})${error.fields.length ? ` · ${t("Fields", "Campos")}: ${error.fields.join(", ")}` : ""}`;
  }
  return `${t("Request or response unavailable", "Solicitud o respuesta no disponible")}: ${error instanceof Error ? error.message : String(error)}`;
}
const active = (job: {state: ProcessingState}) => job.state === "queued" || job.state === "running";
function save(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob), link = document.createElement("a");
  link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export function ProjectProcessingWorkbench({ projectId, es, onManage, onCurated }: {
  projectId: string; es: boolean; onManage: () => void; onCurated: () => void;
}) {
  const [mode, setMode] = useState(() => new URLSearchParams(window.location.search).get("instrument") ?? "gravity");
  const select = (value: string) => { const url = new URL(window.location.href); if (value !== "gravity") url.searchParams.set("instrument", value); else url.searchParams.delete("instrument"); window.history.replaceState(null, "", url); setMode(value); };
  if (mode === "profiles") return <ProfileProjectWorkbench key={projectId} projectId={projectId} es={es} onManage={onManage} onCurated={onCurated} onGravity={() => select("gravity")} onMt={() => select("mt")} />;
  return mode === "mt" ? <MtProjectWorkbench key={projectId} projectId={projectId} es={es} onManage={onManage} onCurated={onCurated} onGravity={() => select("gravity")} onProfiles={() => select("profiles")} /> : <GravityProjectWorkbench key={projectId} projectId={projectId} es={es} onManage={onManage} onCurated={onCurated} onMt={() => select("mt")} onProfiles={() => select("profiles")} />;
}
function GravityProjectWorkbench({ projectId, es, onManage, onCurated, onMt, onProfiles }: {
  projectId: string; es: boolean; onManage: () => void; onCurated: () => void; onMt: () => void; onProfiles: () => void;
}) {
  const t = (en: string, sp: string) => es ? sp : en;
  const clients = useMemo(() => { const client = new ApiClient(window.location.origin); return { lifecycle: new LifecycleApi(client), processing: new ProcessingApi(client) }; }, []);
  const [session, setSession] = useState<"checking" | "ready" | "signedout" | "expired" | "unavailable">("checking");
  const [project, setProject] = useState<ProjectView | null>(null), [assets, setAssets] = useState<RawAsset[]>([]);
  const [datasets, setDatasets] = useState<ProjectDatasetReceipt[]>([]), [jobs, setJobs] = useState<ProjectProcessingJob[]>([]);
  const [assetId, setAssetId] = useState(""), [datasetId, setDatasetId] = useState(""), [jobId, setJobId] = useState("");
  const [dataset, setDataset] = useState<GravityDataset | null>(null), [eligibility, setEligibility] = useState<MethodEligibility | null>(null), [result, setResult] = useState<FlagResult | null>(null);
  const [methodId, setMethodId] = useState<string>(FLAG_METHOD), [threshold, setThreshold] = useState("6");
  const [section, setSection] = useState("data"), [controlsOpen, setControlsOpen] = useState(false);
  const [problem, setProblem] = useState<unknown>(null), [pollProblem, setPollProblem] = useState<unknown>(null);
  const [busy, setBusy] = useState(false), [reading, setReading] = useState(false), [revision, setRevision] = useState(0), [pollRetry, setPollRetry] = useState(0);
  const [notice, setNotice] = useState<"validated" | "submitted" | "exported" | null>(null);
  const lifetime = useRef(new AbortController());
  const ownerId = useRef("");
  const clearPrivate = () => { setProject(null); setAssets([]); setDatasets([]); setJobs([]); setDataset(null); setEligibility(null); setResult(null); };
  const failure = (error: unknown) => {
    if (error instanceof ApiHttpError && error.status === 401) { lifetime.current.abort(); clearPrivate(); setSession("expired"); }
    setProblem(error);
  };
  useEffect(() => {
    lifetime.current = new AbortController(); const {signal} = lifetime.current;
    setSession("checking"); clearPrivate(); setProblem(null); setPollProblem(null); setBusy(false);
    void (async () => {
      try {
        const account = await clients.lifecycle.probe(signal);
        if (signal.aborted) return;
        if (!account) { setSession("signedout"); return; }
        ownerId.current = account.id;
        const projects = await clients.lifecycle.projects(signal), selected = projects.find(item => item.id === projectId);
        if (!selected) throw new ApiHttpError(404, "not_found", "Project not found for this account");
        const [originals, receipts, history] = await Promise.all([clients.lifecycle.assets(projectId, signal), clients.processing.datasets(projectId, signal), clients.processing.jobs(projectId, signal)]);
        if (originals.some(asset => asset.project_id !== projectId || asset.owner_id !== account.id)) throw new Error("Original receipt disagrees with requested owner/project");
        if (signal.aborted) return;
        setProject(selected); setAssets(originals); setDatasets(receipts); setJobs(history);
        setAssetId(current => originals.some(item => item.asset_id === current) ? current : originals[0]?.asset_id ?? "");
        const gravity = receipts.filter(isGravityReceipt);
        setDatasetId(current => gravity.some(item => item.dataset_id === current) ? current : gravity.at(-1)?.dataset_id ?? "");
        setSession("ready");
      } catch (error) { if (!signal.aborted) { failure(error); if (!(error instanceof ApiHttpError && error.status === 401)) setSession("unavailable"); } }
    })();
    return () => { lifetime.current.abort(); ownerId.current = ""; };
  }, [projectId, clients, revision]);
  const gravityDatasets = datasets.filter(isGravityReceipt);
  const receipt = gravityDatasets.find(item => item.dataset_id === datasetId);
  const selectedAsset = assets.find(item => item.asset_id === assetId);
  const history = jobs.filter(isFlagJob).filter(item => item.dataset_id === datasetId);
  const job = history.find(item => item.job_id === jobId);
  const hasActive = jobs.some(active);
  useEffect(() => {
    if (session !== "ready" || !hasActive) return;
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    setPollProblem(null);
    const poll = async () => {
      try {
        const rows = await clients.processing.jobs(projectId, controller.signal);
        if (controller.signal.aborted) return;
        setJobs(rows);
        if (rows.some(active)) timer = setTimeout(poll, 1000);
      } catch (error) { if (!controller.signal.aborted) { if (error instanceof ApiHttpError && error.status === 401) failure(error); else setPollProblem(error); } }
    };
    timer = setTimeout(poll, 1000);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [session, hasActive, clients, projectId, pollRetry]);
  useEffect(() => {
    setDataset(null); setEligibility(null); setResult(null); setProblem(null); setReading(false);
    if (session !== "ready" || !receipt) return;
    const controller = new AbortController(); setReading(true);
    void Promise.all([clients.processing.dataset(projectId, receipt, controller.signal), clients.processing.methods(projectId, receipt.dataset_id, controller.signal)]).then(([data, methods]) => {
      if (controller.signal.aborted) return;
      if (data.owner_id !== ownerId.current) throw new Error("Dataset disagrees with authenticated owner");
      setDataset(data); setEligibility(methods); setMethodId(FLAG_METHOD);
    }).catch(error => { if (!controller.signal.aborted) failure(error); }).finally(() => { if (!controller.signal.aborted) setReading(false); });
    return () => controller.abort();
  }, [clients, projectId, receipt, session]);
  useEffect(() => {
    setJobId(current => history.some(item => item.job_id === current) ? current : history.at(-1)?.job_id ?? "");
  }, [datasetId, jobs]);
  useEffect(() => {
    setResult(null);
    if (!job || job.state !== "succeeded" || !dataset || !receipt || session !== "ready") return;
    const controller = new AbortController();
    void clients.processing.result(projectId, job, dataset, receipt, controller.signal).then(output => { if (!controller.signal.aborted) setResult(output); }).catch(error => { if (!controller.signal.aborted) failure(error); });
    return () => controller.abort();
  }, [job?.job_id, job?.state, job?.request_sha256, job?.result_sha256, dataset, clients, projectId, session]);
  const act = async (operation: (signal: AbortSignal) => Promise<void>) => {
    const signal = lifetime.current.signal;
    if (signal.aborted || session !== "ready") return;
    setBusy(true); setProblem(null); setNotice(null);
    try { await operation(signal); }
    catch (error) { if (!signal.aborted) failure(error); }
    finally { if (!signal.aborted) setBusy(false); }
  };
  const validate = () => void act(async signal => {
    const created = await clients.processing.validateAsset(projectId, assetId, signal);
    if (signal.aborted) return;
    setDatasets(rows => [...rows, created]); setDatasetId(created.dataset_id); setNotice("validated"); setSection("run");
  });
  const submit = (event: FormEvent) => { event.preventDefault(); if (!receipt) return;
    void act(async signal => {
      const admitted = await clients.processing.submit(projectId, receipt, Number(threshold), signal);
      if (signal.aborted) return;
      setResult(null); setJobs(rows => [...rows, admitted]); setJobId(admitted.job_id); setNotice("submitted"); setSection("history");
    });
  };
  const cancel = () => { if (!job) return; void act(async signal => {
    const updated = await clients.processing.cancel(projectId, job.job_id, signal);
    if (!signal.aborted) setJobs(rows => rows.map(item => item.job_id === updated.job_id ? updated : item));
  }); };
  const download = () => { if (!job || !dataset || !receipt) return; void act(async signal => {
    const blob = await clients.processing.export(projectId, job, dataset, receipt, signal);
    if (!signal.aborted) { save(blob, `processing-${job.job_id}.zip`); setNotice("exported"); }
  }); };
  const labels: Record<ProcessingState, string> = { queued: t("Queued", "En cola"), running: t("Running", "En ejecución"), succeeded: t("Succeeded", "Finalizado"), failed: t("Failed", "Fallido"), cancelled: t("Cancelled", "Cancelado") };
  const eligible = eligibility?.methods.find(item => item.method_id === methodId);
  const unavailable = eligibility?.unavailable.find(item => item.method_id === methodId);
  const thresholdValid = threshold.trim() !== "" && Number.isFinite(Number(threshold)) && Number(threshold) >= 1 && Number(threshold) <= 10;
  const rawGuidance = !selectedAsset ? t("Select a stored original.", "Seleccione un original almacenado.") : selectedAsset.detected_format !== "gravity_csv" ? t("This adapter accepts gravity station CSV; this original remains available in Projects.", "Este adaptador admite CSV gravimétrico; este original sigue disponible en Proyectos.") : !selectedAsset.physical_metadata.geometry.sigma_column ? t("No sigma column declared. Re-upload with explicit per-station uncertainty to use this adapter.", "No se declaró columna sigma. Cargue de nuevo con incertidumbre por estación para usar este adaptador.") : t("The API checks every row, geometry, units and positive sigma. A raw receipt alone is not eligible.", "La API revisa cada fila, geometría, unidades y sigma positiva. El recibo original por sí solo no es elegible.");
  return <div className="page-body wide workbench processing-workbench">
    <aside className={`instrument-sidebar processing-sidebar ${controlsOpen ? "expanded" : ""}`}>
      <div className="instrument-brand"><span className="small-caps">{t("PRIVATE PROJECT · PROCESSING", "PROYECTO PRIVADO · PROCESAMIENTO")}</span><h1>{project?.name ?? t("Project processing", "Procesamiento de proyecto")}</h1></div>
      <div className="processing-actions"><button className="btn" onClick={onMt}>{t("MT transfer functions", "Funciones de transferencia MT")}</button><button className="btn" onClick={onCurated}>{t("Curated cases", "Casos curados")}</button><button className="btn" onClick={onManage}>{t("Projects & raw data", "Proyectos y datos originales")}</button></div>
      <button className="btn" onClick={onProfiles}>{t("ERT / first-arrival profiles", "Perfiles ERT / primeras llegadas")}</button>
      <button className="btn mobile-controls-toggle" aria-expanded={controlsOpen} onClick={() => setControlsOpen(!controlsOpen)}>{t("Processing controls", "Controles de procesamiento")}</button>
      {session === "ready" && <div className="processing-controls">
        <label className="select-control"><span>{t("Control section", "Sección de controles")}</span><select className="select" value={section} onChange={event => setSection(event.target.value)}>
          <option value="data">{t("Data validation", "Validación de datos")}</option><option value="run">{t("Flag QC parameters", "Parámetros de QC de marcas")}</option><option value="history">{t("Job history", "Historial de trabajos")}</option><option value="open">{t("Open saved result", "Abrir resultado guardado")}</option></select></label>
        <label className="select-control"><span>{t("Validated dataset", "Conjunto validado")}</span><select className="select" disabled={busy || !gravityDatasets.length} value={datasetId} onChange={event => { if (event.target.value !== datasetId) { setResult(null); setDataset(null); setDatasetId(event.target.value); setNotice(null); } }}>
          {!gravityDatasets.length && <option value="">{t("No gravity dataset yet", "Aún sin conjunto gravimétrico")}</option>}{gravityDatasets.map((item, i) => <option key={item.dataset_id} value={item.dataset_id}>{i + 1} · {assets.find(asset => asset.asset_id === item.raw_asset_id)?.original_filename ?? item.dataset_id} · {item.row_count} {t("stations", "estaciones")}</option>)}</select></label>
        {section === "data" && <>
          <label className="select-control"><span>{t("Stored original", "Original almacenado")}</span><select className="select" value={assetId} disabled={busy || !assets.length} onChange={event => setAssetId(event.target.value)}>
            {!assets.length && <option value="">{t("No originals", "Sin originales")}</option>}{assets.map(item => <option key={item.asset_id} value={item.asset_id}>{item.original_filename} · {item.detected_format}</option>)}</select></label>
          <p className="project-note">{rawGuidance}</p>
          <button className="btn primary" disabled={busy || !selectedAsset || selectedAsset.detected_format !== "gravity_csv" || datasets.some(item => item.raw_asset_id === assetId)} onClick={validate}>{t("Validate station table", "Validar tabla de estaciones")}</button>
          <p className="project-note">{t("4–4096 stations · six explicit columns · projected xy metres · mGal with positive σ · ≤2 MiB. Original values are retained.", "4–4096 estaciones · seis columnas explícitas · xy proyectadas en metros · mGal con σ positiva · ≤2 MiB. Se conservan valores originales.")}</p>
          {datasets.filter(isEdiReceipt).map(item => <p className="project-note" key={item.dataset_id}>{assets.find(asset => asset.asset_id === item.raw_asset_id)?.original_filename ?? item.dataset_id} · {item.row_count} {t("declared frequencies", "frecuencias declaradas")} · awaiting_full_tensor_qc. {t("Immutable EDI envelope, not parsed gravity or an inverse. MT execution/result/export require a separate reviewed frontend adapter and host admission.", "Envoltura EDI inmutable, no gravedad analizada ni inversión. Ejecución/resultado/exportación MT requieren otro adaptador revisado y admisión del servidor.")}</p>)}
          <button className="btn" disabled={busy} onClick={() => setRevision(n => n + 1)}>{t("Refresh project data", "Actualizar datos del proyecto")}</button>
        </>}
        {section === "run" && <form className="processing-run-form" onSubmit={submit}>
          <label className="select-control"><span>{t("API method verdict", "Veredicto de método de la API")}</span><select className="select" value={methodId} disabled={!eligibility || busy} onChange={event => setMethodId(event.target.value)}>
            {!eligibility && <option value={FLAG_METHOD}>{t("Read dataset first", "Lea primero el conjunto")}</option>}
            {eligibility?.methods.map(item => <option key={item.method_id} value={item.method_id}>{item.method_id === FLAG_METHOD ? t("Gravity station outlier flags", "Marcas atípicas gravimétricas") : item.method_id}</option>)}
            {eligibility && <optgroup label={t("Unavailable methods", "Métodos no disponibles")}>{eligibility.unavailable.map(item => <option key={item.method_id} value={item.method_id}>{item.method_id} · {t("unavailable", "no disponible")}</option>)}</optgroup>}
          </select></label>
          <p className="project-note" role="status">{methodId === FLAG_METHOD && eligible ? t("Eligible: flag-only statistical QC. No gravity correction or inversion.", "Elegible: QC estadístico solo de marcas. Sin corrección gravimétrica ni inversión.") : unavailable ? `${t("API reason", "Motivo de la API")}: ${unavailable.reason}` : eligible ? t("The API lists this method, but this frontend has no reviewed parameter/result adapter for it.", "La API incluye este método, pero esta interfaz no tiene adaptador revisado de parámetros/resultados.") : t("Waiting for dataset eligibility.", "Esperando elegibilidad del conjunto.")}</p>
          <label className="select-control"><span>{t("Robust-score threshold [1]", "Umbral del puntaje robusto [1]")}</span><input className="select" type="number" min="1" max="10" step="any" required value={threshold} onChange={event => setThreshold(event.target.value)} /></label>
          <p className="project-note">{t("Flag when |g − median(g)| / (1.4826 × MAD) exceeds this threshold. The worker retains all observations and σ. Zero MAD fails explicitly.", "Marca si |g − mediana(g)| / (1,4826 × MAD) excede el umbral. El proceso conserva todas las observaciones y σ. MAD cero produce fallo explícito.")}</p>
          <button className="btn primary" disabled={busy || !dataset || !receipt || !thresholdValid || !eligible || methodId !== FLAG_METHOD || hasActive}>{t("Submit flag QC job", "Enviar trabajo QC de marcas")}</button>
          <p className="project-note">{t("The API checks resource admission on submission; one active job per account. Its receipt records actual limits.", "La API comprueba recursos al enviar; un trabajo activo por cuenta. El recibo registra los límites reales.")}</p>
        </form>}
        {section === "history" && <>
          {jobs.filter(isMtJob).map(item => <div className="project-note" key={item.job_id}><p>{item.method_id} · {labels[item.state]} · {item.job_id}. {item.method_id === M05_METHOD ? t("M05 success is full-tensor QC only; not an inverse.", "M05 exitoso es solo QC tensorial; no inversión.") : t("M06 candidate is conditional on imposed thickness; not geological truth.", "El candidato M06 depende del espesor impuesto; no es verdad geológica.")} {t("This gravity view does not interpret or export that result.", "Esta vista gravimétrica no interpreta ni exporta ese resultado.")}</p>{item.error && <p role="alert">{item.error.code}: {item.error.message}</p>}{active(item) && <button className="btn" disabled={busy || item.cancel_requested} onClick={() => void act(async signal => { const updated = await clients.processing.cancel(projectId,item.job_id,signal); if (!signal.aborted) setJobs(rows => rows.map(row => row.job_id === updated.job_id ? updated : row)); })}>{item.cancel_requested ? t("Cancellation requested", "Cancelación solicitada") : t("Cancel job", "Cancelar trabajo")} · {item.method_id}</button>}</div>)}
          <label className="select-control"><span>{t("Processing job", "Trabajo de procesamiento")}</span><select className="select" value={jobId} disabled={busy || !history.length} onChange={event => { if (event.target.value !== jobId) { setResult(null); setJobId(event.target.value); } }}>
            {!history.length && <option value="">{t("No job yet", "Aún sin trabajo")}</option>}{history.map((item, i) => <option key={item.job_id} value={item.job_id}>{i + 1} · {labels[item.state]} · {t("threshold", "umbral")} {item.request.parameters.threshold}</option>)}</select></label>
          {job && <><p className="project-note">{t("Submitted threshold", "Umbral enviado")}: {job.request.parameters.threshold} [1]</p>
            <button className="btn" disabled={busy || !active(job) || job.cancel_requested} onClick={cancel}>{job.cancel_requested ? t("Cancellation requested", "Cancelación solicitada") : t("Cancel job", "Cancelar trabajo")}</button>
            <dl className="processing-limits"><dt>{t("Estimated memory / limit", "Memoria estimada / límite")}</dt><dd>{(job.preflight.estimated_memory_bytes / 1048576).toFixed(1)} / {(job.preflight.memory_limit_bytes / 1048576).toFixed(1)} MiB</dd><dt>{t("Scratch / wall limits", "Límites temporales / duración")}</dt><dd>{(job.preflight.scratch_limit_bytes / 1048576).toFixed(1)} MiB / {job.preflight.wall_limit_seconds} s</dd><dt>{t("Measured wall / peak RSS", "Duración / RSS máximo medidos")}</dt><dd>{job.wall_ms === null ? t("not measured", "sin medición") : `${job.wall_ms} ms`} / {job.peak_rss_bytes === null ? t("not measured", "sin medición") : `${(job.peak_rss_bytes / 1048576).toFixed(1)} MiB`}</dd><dt>{t("Measured scratch", "Temporales medidos")}</dt><dd>{job.scratch_bytes === null ? t("not measured", "sin medición") : `${job.scratch_bytes} bytes`}</dd></dl>
            <button className="btn" disabled={busy || job.state !== "succeeded" || !result} onClick={download}>{t("Verify & export processing ZIP", "Verificar y exportar ZIP de procesamiento")}</button>
            </>}
          <button className="btn" disabled={busy} onClick={() => setRevision(n => n + 1)}>{t("Refresh history", "Actualizar historial")}</button>
        </>}
        {section === "open" && (job?.state === "succeeded" && dataset ? <><p className="project-note">{t("Selected job", "Trabajo seleccionado")}: {job.job_id} · {t("Select another job in History before opening its ZIP.", "Seleccione otro trabajo en Historial antes de abrir su ZIP.")}</p><ResultBundleInput key={`${dataset.dataset_id}:${job.job_id}:${job.result_sha256}`} es={es} verify={file => readSavedResult(file, { kind: "gravity", job, dataset })} onOpened={setResult}/></> : <p className="project-note">{t("Select a successful job in History first. Saved files do not admit or execute jobs.", "Seleccione primero un trabajo exitoso en Historial. Los archivos no admiten ni ejecutan trabajos.")}</p>)}
      </div>}
    </aside>
    <section className="instrument-main processing-main" aria-label={t("Selected project processing", "Procesamiento del proyecto seleccionado")}>
      {session !== "ready" ? <div className="load-state" role="status"><p>{session === "checking" ? t("Checking project ownership…", "Comprobando titular del proyecto…") : session === "signedout" || session === "expired" ? t("Sign in through Projects to load this private project.", "Inicie sesión en Proyectos para cargar este proyecto privado.") : t("Project service or data unavailable.", "Servicio o datos del proyecto no disponibles.")}</p>{session !== "checking" && <button className="btn" onClick={() => setRevision(n => n + 1)}>{t("Retry project load", "Reintentar carga del proyecto")}</button>}</div> : <>
        <div className="processing-status"><strong>{t("Gravity station flag QC", "QC de marcas gravimétricas")}</strong><span role="status" data-testid="job-status">{job ? `${labels[job.state]}${job.cancel_requested && active(job) ? ` · ${t("cancellation requested", "cancelación solicitada")}` : ""}` : t("Observations · no job selected", "Observaciones · sin trabajo seleccionado")}</span></div>
        {job?.error && <p className="project-error" role="alert">{labels[job.state]} · {job.error.code}: {job.error.message}</p>}
        {reading && <p role="status">{t("Reading validated dataset and eligibility…", "Leyendo conjunto y elegibilidad…")}</p>}
        {result && <div className="processing-summary" data-testid="qc-summary"><span>{t("Median", "Mediana")} {result.statistics.median_mgal.toPrecision(6)} mGal</span><span>MAD {result.statistics.mad_mgal.toPrecision(6)} mGal</span><span>{t("Flagged", "Marcadas")} {result.statistics.flagged_count}/{dataset?.dimensions.station}</span><span>{t("Submitted threshold", "Umbral enviado")} {result.parameters.threshold} [1]</span></div>}
        {dataset ? <GravityStationInstrument key={dataset.dataset_id} dataset={dataset} result={result} es={es} /> : !reading && <div className="load-state">{t("Validate a stored gravity station table to inspect observations. Use Projects to upload an original with explicit uncertainty.", "Valide una tabla gravimétrica almacenada para inspeccionar observaciones. Use Proyectos para cargar un original con incertidumbre explícita.")}</div>}
        <p className="processing-scope">{t("Statistical flags preserve g and σ. This processing contract returns no inverse model, predicted data or residuals; full M01 correction/inversion remains a separate method.", "Las marcas estadísticas conservan g y σ. Este contrato no devuelve modelo inverso, predicciones ni residuos; corrección/inversión M01 completa sigue siendo un método separado.")}</p>
        {dataset && <details className="processing-provenance"><summary>{t("Dataset, job and source provenance", "Procedencia de conjunto, trabajo y fuente")}</summary><p>{dataset.attribution} · {dataset.rights_decision} · {dataset.rights_statement}</p><p>{dataset.physical_metadata.horizontal_datum} · {dataset.physical_metadata.vertical_datum} · Z {dataset.physical_metadata.vertical_positive} [m] · {dataset.physical_metadata.component_frame}</p><p>{t("Dataset SHA-256", "SHA-256 del conjunto")}: <code>{receipt?.sha256}</code></p><p>{t("Raw parent SHA-256", "SHA-256 original")}: <code>{dataset.parent_raw_sha256}</code></p>{job && <p>{t("Job", "Trabajo")}: {job.job_id} · {t("Request SHA-256", "SHA-256 de solicitud")}: <code>{job.request_sha256}</code></p>}{result && <p>{t("Engine SHA-256", "SHA-256 del motor")}: <code>{result.engine_sha256}</code> · {t("Result SHA-256", "SHA-256 del resultado")}: <code>{job?.result_sha256}</code></p>}</details>}
      </>}
      {problem != null && <p role="alert" className="project-error">{processingProblem(problem, es)}</p>}
      {pollProblem != null && <p role="alert" className="project-error">{processingProblem(pollProblem, es)} <button className="btn" onClick={() => setPollRetry(n => n + 1)}>{t("Resume status check", "Reanudar revisión de estado")}</button></p>}
      {notice && <p role="status" className="project-notice">{notice === "validated" ? t("Immutable dataset created for flag QC only.", "Conjunto inmutable creado solo para QC de marcas.") : notice === "submitted" ? t("Request admitted. The separate worker determines its outcome.", "Solicitud admitida. El proceso separado determina el resultado.") : t("Export member hashes and dataset/result identity verified before download.", "Hashes e identidad de conjunto/resultado verificados antes de descargar.")}</p>}
    </section>
  </div>;
}
