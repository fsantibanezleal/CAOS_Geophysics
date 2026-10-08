import { useEffect, useMemo, useRef, useState } from "react";
import { ApiClient, ApiHttpError } from "../api/client";
import { LifecycleApi, type ProjectView } from "../api/lifecycle";
import type { RawAsset } from "../api/contracts";
import { ProfileProcessingApi, verifyProfileBundle } from "../api/profile-processing";
import { M07_METHOD, M09_METHOD, isProfileReceipt, isProfileJob, type ProfileDatasetReceipt, type ProjectProcessingJob, type MethodEligibility } from "../api/processing-contracts";
import type { ProfileAdmission } from "../api/profile-local-contracts";
import { ProfileLocalInstrument } from "./ProfileLocalInstrument";
import { ResultBundleInput } from "./ResultBundleInput";

const active = (job: ProjectProcessingJob) => job.state === "queued" || job.state === "running";
export function ProfileProjectWorkbench({ projectId, es, onManage, onCurated, onGravity, onMt }: {
  projectId: string; es: boolean; onManage: () => void; onCurated: () => void; onGravity: () => void; onMt: () => void;
}) {
  const t = (en: string, sp: string) => es ? sp : en;
  const clients = useMemo(() => { const client = new ApiClient(window.location.origin); return { life: new LifecycleApi(client), profile: new ProfileProcessingApi(client) }; }, []);
  const lifetime = useRef(new AbortController());
  const [project, setProject] = useState<ProjectView | null>(null), [assets, setAssets] = useState<RawAsset[]>([]), [receipts, setReceipts] = useState<ProfileDatasetReceipt[]>([]), [jobs, setJobs] = useState<ProjectProcessingJob[]>([]);
  const [session, setSession] = useState("checking"), [assetId, setAssetId] = useState(""), [datasetId, setDatasetId] = useState(""), [jobId, setJobId] = useState("");
  const [result, setResult] = useState<ProfileAdmission | null>(null), [eligibility, setEligibility] = useState<MethodEligibility | null>(null);
  const [holder, setHolder] = useState(""), [citation, setCitation] = useState(""), [permission, setPermission] = useState(false), [redistribution, setRedistribution] = useState(false);
  const [busy, setBusy] = useState(false), [expanded, setExpanded] = useState(false), [revision, setRevision] = useState(0), [pollRetry, setPollRetry] = useState(0), [problem, setProblem] = useState<unknown>(null), [pollError, setPollError] = useState<unknown>(null);
  const clear = () => { setProject(null); setAssets([]); setReceipts([]); setJobs([]); setResult(null); setEligibility(null); };
  const fail = (error: unknown) => { if (error instanceof ApiHttpError && error.status === 401) { lifetime.current.abort(); clear(); setSession("expired"); } setProblem(error); };
  const message = (error: unknown) => error instanceof ApiHttpError ? `${error.code}: ${error.message}${error.fields.length ? ` · ${error.fields.join(", ")}` : ""}` : error instanceof Error ? error.message : String(error);
  useEffect(() => {
    lifetime.current = new AbortController(); const { signal } = lifetime.current; clear(); setSession("checking"); setBusy(false); setProblem(null);
    void (async () => { try {
      const account = await clients.life.probe(signal); if (signal.aborted) return; if (!account) { setSession("signedout"); return; }
      const projects = await clients.life.projects(signal), owned = projects.find(value => value.id === projectId);
      if (!owned) throw new ApiHttpError(404, "not_found", "Project not found");
      const [raw, data, history] = await Promise.all([clients.life.assets(projectId, signal), clients.profile.datasets(projectId, signal), clients.profile.jobs(projectId, signal)]);
      if (raw.some(value => value.owner_id !== account.id || value.project_id !== projectId)) throw new Error("Original ownership mismatch");
      if (signal.aborted) return;
      const profileAssets = raw.filter(value => ["ert_ohm", "traveltime_sgt"].includes(value.detected_format)), profiles = data.filter(isProfileReceipt);
      setProject(owned); setAssets(profileAssets); setReceipts(profiles); setJobs(history);
      setAssetId(value => profileAssets.some(item => item.asset_id === value) ? value : profileAssets[0]?.asset_id ?? "");
      setDatasetId(value => profiles.some(item => item.dataset_id === value) ? value : profiles.at(-1)?.dataset_id ?? ""); setSession("ready");
    } catch (error) { if (!signal.aborted) { fail(error); if (!(error instanceof ApiHttpError && error.status === 401)) setSession("unavailable"); } } })();
    return () => lifetime.current.abort();
  }, [clients, projectId, revision]);
  const receipt = receipts.find(value => value.dataset_id === datasetId), asset = assets.find(value => value.asset_id === assetId);
  useEffect(() => { setCitation(asset?.source.citation ?? ""); setHolder(""); setPermission(false); setRedistribution(false); }, [asset?.asset_id]);
  const history = jobs.filter(isProfileJob).filter(value => value.dataset_id === datasetId), job = history.find(value => value.job_id === jobId), hasActive = jobs.some(active);
  const method = receipt?.modality === "traveltime_profile" ? M09_METHOD : M07_METHOD;
  useEffect(() => { setResult(null); setEligibility(null); setJobId(""); if (session !== "ready" || !receipt) return; const controller = new AbortController();
    void clients.profile.methods(projectId, receipt.dataset_id, controller.signal).then(value => { if (!controller.signal.aborted) setEligibility(value); }).catch(error => { if (!controller.signal.aborted) fail(error); });
    return () => controller.abort();
  }, [clients, projectId, receipt, session]);
  useEffect(() => { setJobId(value => history.some(item => item.job_id === value) ? value : history.at(-1)?.job_id ?? ""); }, [jobs, datasetId]);
  useEffect(() => { if (session !== "ready" || !hasActive) return; const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>; setPollError(null);
    const poll = async () => { try { const next = await clients.profile.jobs(projectId, controller.signal); if (controller.signal.aborted) return; setJobs(next); if (next.some(active)) timer = setTimeout(poll, 1000); } catch (error) { if (!controller.signal.aborted) { if (error instanceof ApiHttpError && error.status === 401) fail(error); else setPollError(error); } } };
    timer = setTimeout(poll, 1000); return () => { clearTimeout(timer); controller.abort(); };
  }, [clients, projectId, session, hasActive, pollRetry]);
  useEffect(() => { setResult(null); if (session !== "ready" || !job || !receipt || job.state !== "succeeded") return; const controller = new AbortController();
    void clients.profile.profileResult(projectId, job, receipt, controller.signal).then(value => { if (!controller.signal.aborted) setResult(value); }).catch(error => { if (!controller.signal.aborted) fail(error); }); return () => controller.abort();
  }, [clients, projectId, receipt, job?.job_id, job?.state, job?.result_sha256, session]);
  const act = async (operation: (signal: AbortSignal) => Promise<void>) => { const { signal } = lifetime.current; if (signal.aborted || session !== "ready" || busy) return; setBusy(true); setProblem(null); try { await operation(signal); } catch (error) { if (!signal.aborted) fail(error); } finally { if (!signal.aborted) setBusy(false); } };
  const validate = () => { if (!asset || !holder.trim() || !permission || !citation.trim()) return; void act(async signal => {
    const metadata = { schema: "geophysics.supplied-profile/v1", method: asset.detected_format === "ert_ohm" ? M07_METHOD : M09_METHOD,
      source: { source_id: asset.source_id, kind: "user_upload", citation: citation.trim(), sha256: asset.sha256, bytes: asset.byte_count, rights: { holder: holder.trim(), processing_allowed: permission, redistribution_allowed: redistribution } },
      frame: { horizontal_reference: asset.physical_metadata.local_crs, vertical_datum: asset.physical_metadata.vertical_datum, coordinate_unit: "m", vertical_positive: "up", profile_axes: ["distance", "elevation"] }, weights: { policy: "provider-example-conditional/v1" } };
    const admitted = await clients.profile.validateProfile(projectId, asset.asset_id, metadata, signal); if (signal.aborted) return; setReceipts(values => [...values, admitted]); setDatasetId(admitted.dataset_id);
  }); };
  const eligible = eligibility?.methods.some(value => value.method_id === method), unavailable = eligibility?.unavailable.find(value => value.method_id === method);
  return <div className="page-body wide workbench processing-workbench">
    <aside className={`instrument-sidebar processing-sidebar ${expanded ? "expanded" : ""}`}>
      <div className="instrument-brand"><div><span className="small-caps">{t("PRIVATE PROJECT · ERT / TRAVELTIME", "PROYECTO PRIVADO · ERT / TIEMPOS")}</span><h1>{project?.name ?? t("Profile processing", "Procesamiento de perfiles")}</h1></div></div>
      <div className="processing-actions"><button className="btn" onClick={onGravity}>{t("Gravity station QC", "QC gravimétrico")}</button><button className="btn" onClick={onMt}>{t("MT transfer functions", "Funciones de transferencia MT")}</button><button className="btn" onClick={onManage}>{t("Projects & raw data", "Proyectos y datos originales")}</button><button className="btn" onClick={onCurated}>{t("Curated cases", "Casos curados")}</button></div>
      <button className="btn mobile-controls-toggle" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{t("Processing controls", "Controles de procesamiento")}</button>
      {session === "ready" && <div className="processing-controls">
        <label className="select-control"><span>{t("Stored original", "Original almacenado")}</span><select className="select" value={assetId} disabled={busy} onChange={event => { setAssetId(event.target.value); setHolder(""); setPermission(false); setRedistribution(false); }}>{!assets.length && <option value="">{t("Upload an .ohm or .sgt in Projects", "Cargue .ohm o .sgt en Proyectos")}</option>}{assets.map(value => <option key={value.asset_id} value={value.asset_id}>{value.original_filename} · {value.detected_format}</option>)}</select></label>
        <p className="project-note">{t("Original local distance/elevation in metres, elevation positive up. Counts must match every original row; no coordinate conversion or missing-value substitution.", "Distancia/elevación local original en metros, elevación positiva hacia arriba. Los conteos deben coincidir con cada fila; sin conversión de coordenadas ni sustitución de valores.")}</p>
        <details className="processing-provenance"><summary>{t("Dataset citation and processing permission", "Cita y permiso de procesamiento del conjunto")}</summary>
        <label className="select-control"><span>{t("Source citation for this profile", "Cita de fuente de este perfil")}</span><input className="select" value={citation} onChange={event => setCitation(event.target.value)} /></label>
        <label className="select-control"><span>{t("Declared rights holder", "Titular declarado de derechos")}</span><input className="select" value={holder} onChange={event => setHolder(event.target.value)} /></label>
        <label><input type="checkbox" checked={permission} onChange={event => setPermission(event.target.checked)} />{t("I have permission to process this original", "Tengo permiso para procesar este original")}</label>
        <label><input type="checkbox" checked={redistribution} onChange={event => setRedistribution(event.target.checked)} />{t("Redistribution permitted by the rights holder", "Redistribución permitida por el titular")}</label>
        <p className="project-note">{t("These explicit declarations create the immutable dataset. They do not change or publish the original asset.", "Estas declaraciones explícitas crean el conjunto inmutable. No modifican ni publican el original.")}</p>
        <button className="btn" disabled={busy || !asset || !citation.trim() || !permission || !holder.trim() || receipts.some(value => value.raw_asset_id === assetId)} onClick={validate}>{t("Parse original profile", "Analizar perfil original")}</button>
        </details>
        <label className="select-control"><span>{t("Parsed dataset", "Conjunto analizado")}</span><select className="select" value={datasetId} disabled={busy} onChange={event => setDatasetId(event.target.value)}>{!receipts.length && <option value="">{t("No profile dataset", "Sin conjunto de perfil")}</option>}{receipts.map(value => <option key={value.dataset_id} value={value.dataset_id}>{assets.find(item => item.asset_id === value.raw_asset_id)?.original_filename ?? value.dataset_id} · {value.row_count} · {value.modality}</option>)}</select></label>
        <p className="project-note">{t("Fixed conditional error policy: uncertainty is assumed, not measured. Held-source / held-geometry tests, fit checks and coverage can refuse a model. Successful job completion is not a passed scientific verdict.", "Política de error condicional fija: incertidumbre supuesta, no medida. Pruebas de fuentes/geometrías reservadas, ajuste y cobertura pueden rechazar un modelo. Finalizar trabajo no implica veredicto científico aprobado.")}</p>
        {unavailable && <p role="status">{unavailable.reason}</p>}
        <button className="btn primary" disabled={busy || !receipt || !eligible || hasActive} onClick={() => { if (!receipt) return; void act(async signal => { const admitted = await clients.profile.submitProfile(projectId, receipt, signal); if (!signal.aborted) { setJobs(values => [...values, admitted]); setJobId(admitted.job_id); } }); }}>{t("Run native profile inversion on VPS", "Ejecutar inversión nativa de perfil en VPS")}</button>
        <label className="select-control"><span>{t("Job history", "Historial de trabajos")}</span><select className="select" value={jobId} onChange={event => setJobId(event.target.value)}>{!history.length && <option value="">{t("No job", "Sin trabajo")}</option>}{history.map(value => <option key={value.job_id} value={value.job_id}>{value.state} · {value.job_id}</option>)}</select></label>
        {job && <><button className="btn" disabled={busy || !active(job) || job.cancel_requested} onClick={() => void act(async signal => { const updated = await clients.profile.cancel(projectId, job.job_id, signal); if (!signal.aborted) setJobs(values => values.map(value => value.job_id === updated.job_id ? updated : value)); })}>{job.cancel_requested ? t("Cancellation requested", "Cancelación solicitada") : t("Cancel job", "Cancelar trabajo")}</button>
          <p className="project-note">{job.method_id} · {job.job_id}</p></>}
        {job?.state === "succeeded" && receipt && <><button className="btn" disabled={busy} onClick={() => void act(async signal => { const blob = await clients.profile.profileExport(projectId, job, receipt, signal); if (signal.aborted) return; const url = URL.createObjectURL(blob), link = document.createElement("a"); link.href = url; link.download = `profile-${job.job_id}.zip`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 30000); })}>{t("Download verified result ZIP", "Descargar ZIP de resultado verificado")}</button><ResultBundleInput key={`${job.job_id}:${job.result_sha256}`} es={es} verify={blob => verifyProfileBundle(blob, job, receipt)} onOpened={setResult} /></>}
        <button className="btn" disabled={busy} onClick={() => setRevision(value => value + 1)}>{t("Refresh project data", "Actualizar datos del proyecto")}</button>
      </div>}
    </aside>
    <section className="instrument-main processing-main" aria-label={t("Protected profile results", "Resultados protegidos de perfiles")}>
      {session !== "ready" ? <div className="load-state" role="status">{session === "checking" ? t("Checking project ownership…", "Comprobando titular del proyecto…") : t("Sign in through Projects, or retry if the private service is unavailable.", "Inicie sesión en Proyectos, o reintente si el servicio privado no está disponible.")}<button className="btn" onClick={() => setRevision(value => value + 1)}>{t("Retry", "Reintentar")}</button></div> : <>
        <div className="processing-status"><strong>{t("M07 topographic ERT / M09 first arrivals", "M07 ERT topográfico / M09 primeras llegadas")}</strong><span role="status" data-testid="job-status">{job?.state ?? t("No job selected", "Sin trabajo seleccionado")}</span></div>
        {job && <p className="project-note">{t("Measured child resources", "Recursos medidos del proceso")}: {job.wall_ms ?? "n/a"} ms · RSS {job.peak_rss_bytes ?? "n/a"} B · {t("scratch", "temporales")} {job.scratch_bytes ?? "n/a"} B</p>}
        {job?.error && <p role="alert" className="project-error">{job.error.code}: {job.error.message}</p>}
        {result ? <ProfileLocalInstrument admitted={result} es={es} lane="protected-worker" /> : <p className="load-state">{t("Select a completed job to inspect its exact native result. No preset model is displayed for your original.", "Seleccione un trabajo finalizado para inspeccionar su resultado nativo exacto. No se muestra modelo predefinido para su original.")}</p>}
      </>}
      {problem != null && <p role="alert" className="project-error">{message(problem)}</p>}
      {pollError != null && <p role="alert" className="project-error">{message(pollError)} <button className="btn" onClick={() => setPollRetry(value => value + 1)}>{t("Resume status check", "Reanudar revisión de estado")}</button></p>}
    </section>
  </div>;
}
