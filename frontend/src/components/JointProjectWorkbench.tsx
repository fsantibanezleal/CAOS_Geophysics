import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ApiClient, ApiHttpError } from "../api/client";
import { LifecycleApi, type ProjectView } from "../api/lifecycle";
import { JointCustodyApi, type JointCustodyJob } from "../api/joint-custody";
import type { JointDatasetReceipt } from "../api/joint-input";
import type { JointInspection } from "../api/joint-result";
import { JointNativeInputPanel } from "./JointNativeInputPanel";
import { JointResultWorkbench } from "./JointResultWorkbench";

/** One parent rail; native indexing, stored custody and offline inspection differ. */
export function JointProjectWorkbench({projectId, es, onManage, onCurated, methodNavigation}: {
  projectId: string; es: boolean; onManage: () => void; onCurated: () => void; methodNavigation?: ReactNode;
}) {
  const t = (en: string, sp: string) => es ? sp : en;
  const clients = useMemo(() => {const api = new ApiClient(window.location.origin); return {api, lifecycle: new LifecycleApi(api), custody: new JointCustodyApi(api)};}, []);
  const [project, setProject] = useState<ProjectView | null>(null), [owner, setOwner] = useState("");
  const [session, setSession] = useState("checking"), [revision, setRevision] = useState(0), [section, setSection] = useState("originals");
  const [dataset, setDataset] = useState<JointDatasetReceipt | null>(null), [jobs, setJobs] = useState<JointCustodyJob[]>([]), [jobId, setJobId] = useState("");
  const [inspection, setInspection] = useState<JointInspection | null>(null), [busy, setBusy] = useState(false), [problem, setProblem] = useState("");
  const [controlsOpen, setControlsOpen] = useState(false), [instrumentRevision, setInstrumentRevision] = useState(0);
  const lifetime = useRef<AbortController | null>(null), generation = useRef(0);
  const operationControl = useRef<AbortController | null>(null), operationGeneration = useRef(0);
  const clear = () => {operationControl.current?.abort(); operationGeneration.current++; setBusy(false); setDataset(null); setJobs([]); setJobId(""); setInspection(null); setInstrumentRevision(n => n + 1);};
  const fail = (error: unknown) => {
    if (error instanceof ApiHttpError && error.status === 401) {
      lifetime.current?.abort(); generation.current++; clear(); setOwner(""); setProject(null); setSession("expired");
    }
    setProblem(error instanceof ApiHttpError ? error.code : error instanceof Error ? error.message : t("Native service unavailable", "Servicio nativo no disponible"));
  };
  useEffect(() => {
    const control = new AbortController(), ticket = ++generation.current; lifetime.current = control;
    clear(); setOwner(""); setProject(null); setSession("checking"); setProblem(""); setBusy(false);
    void (async () => {
      try {
        const account = await clients.lifecycle.probe(control.signal);
        if (control.signal.aborted || generation.current !== ticket) return;
        if (!account) {setSession("signedout"); return;}
        const projects = await clients.lifecycle.projects(control.signal), selected = projects.find(p => p.id === projectId);
        if (!selected) throw new ApiHttpError(404, "not_found", "Owned project not found");
        if (control.signal.aborted || generation.current !== ticket) return;
        setOwner(account.id); setProject(selected); setSession("ready");
      } catch (error) {if (!control.signal.aborted) {fail(error); if (!(error instanceof ApiHttpError && error.status === 401)) setSession("unavailable");}}
    })();
    return () => {control.abort(); operationControl.current?.abort(); generation.current++;};
  }, [projectId, clients, revision]);
  async function action(operation: (signal: AbortSignal) => Promise<void>) {
    const ticket = generation.current;
    if (session !== "ready" || !lifetime.current || lifetime.current.signal.aborted || busy) return;
    const control = new AbortController(), operationTicket = ++operationGeneration.current; operationControl.current = control;
    setBusy(true); setProblem("");
    try {await operation(control.signal);} catch (error) {if (!control.signal.aborted && ticket === generation.current) fail(error);}
    finally {if (ticket === generation.current && operationTicket === operationGeneration.current) setBusy(false);}
  }
  const job = jobs.find(item => item.job_id === jobId);
  return <div className="page-body wide workbench processing-workbench" data-testid="joint-project-workbench">
    <aside className={`instrument-sidebar processing-sidebar ${controlsOpen ? "expanded" : ""}`}>
      {methodNavigation}
      <div className="instrument-brand"><span className="small-caps">{t("PRIVATE PROJECT", "PROYECTO PRIVADO")}</span><h1>{project?.name ?? t("Joint survey custody", "Custodia de levantamiento conjunto")}</h1></div>
      <div className="processing-actions"><button className="btn" onClick={onManage}>{t("Projects & raw data", "Proyectos y datos originales")}</button><button className="btn" onClick={onCurated}>{t("Curated cases", "Casos curados")}</button></div>
      <button className="btn mobile-controls-toggle" aria-expanded={controlsOpen} onClick={() => setControlsOpen(v => !v)}>{t("Processing controls", "Controles de procesamiento")}</button>
      {session === "ready" && <div className="processing-controls">
        <label className="select-control"><span>{t("Joint control section", "Sección de controles conjuntos")}</span><select className="select" aria-label={t("Joint control section", "Sección de controles conjuntos")} value={section} onChange={e => setSection(e.target.value)}>
          <option value="originals">{t("Original inputs", "Entradas originales")}</option><option value="run">{t("Scientific execution", "Ejecución científica")}</option><option value="history">{t("Stored native results", "Resultados nativos almacenados")}</option></select></label>
        {section === "originals" && <JointNativeInputPanel projectId={projectId} ownerId={owner} api={clients.api} onIndexed={setDataset} onCleared={clear} onSessionExpired={() => fail(new ApiHttpError(401, "session_expired", "Session expired"))}/>}
        {section === "run" && <>
          <p className="processing-scope">{t("Structural indexing does not authorize a scientific run. The online method remains unavailable pending the applicable source-bound M02 bridge and canonical worker admission. No scientific job is submitted by this custody instrument.", "Indexar estructura no autoriza ejecutar ciencia. El método en línea sigue sin disponibilidad hasta admitir el puente M02 ligado a fuentes y el worker canónico. Este instrumento de custodia no envía trabajos científicos.")}</p>
          {dataset && <p className="processing-provenance"><code>{dataset.dataset_id}</code> · <code>{dataset.sha256}</code></p>}
          <a href="https://github.com/fsantibanezleal/CAOS_Geophysics/blob/task/geophysics-joint-survey-inversion/docs/guides/22_local_joint_survey.md" target="_blank" rel="noreferrer">{t("Wiki: explicit offline scientific workflow", "Wiki: flujo científico explícito fuera de línea")}</a>
        </>}
        {section === "history" && <>
          <button className="btn" disabled={busy} onClick={() => void action(async signal => {const rows = await clients.custody.history(owner, projectId, signal); if (!signal.aborted) {setJobs(rows); setJobId(rows[0]?.job_id ?? ""); setInspection(null);}})}>{t("Refresh literal native job history", "Actualizar historial literal de trabajos nativos")}</button>
          <label className="select-control"><span>{t("Native job", "Trabajo nativo")}</span><select className="select" aria-label={t("Native job", "Trabajo nativo")} disabled={busy || !jobs.length} value={jobId} onChange={e => {setJobId(e.target.value); setInspection(null);}}>{jobs.map(row => <option key={row.job_id} value={row.job_id}>{row.state} · {row.job_id}</option>)}</select></label>
          {job && <p className="processing-provenance">{job.state} · {job.error_code ?? t("No literal error", "Sin error literal")}<br/><code>{job.request_sha256}</code></p>}
          <button className="btn" disabled={busy || !job?.index_available} onClick={() => void action(async signal => {if (!job) return; const value = await clients.custody.inspect(job, signal); if (!signal.aborted) {setInspection(value); setInstrumentRevision(n => n + 1);}})}>{t("Verify and inspect exact stored native originals", "Verificar e inspeccionar originales nativos almacenados exactos")}</button>
        </>}
        {busy && <p role="status">{t("Reading private custody; no scientific execution", "Leyendo custodia privada; sin ejecución científica")}</p>}
        <button className="btn" onClick={clear}>{t("Clear private views, not server bytes", "Borrar vistas privadas, no bytes del servidor")}</button>
      </div>}
    </aside>
    <section className="instrument-main processing-main" aria-label={t("Joint native inspection", "Inspección nativa conjunta")}>
      {session !== "ready" ? <div className="load-state" role="status"><p>{session === "checking" ? t("Checking project ownership", "Comprobando titular del proyecto") : t("Sign in through Projects or retry the owned project service", "Inicie sesión en Proyectos o reintente el servicio del proyecto propio")}</p><button className="btn" onClick={() => setRevision(n => n + 1)}>{t("Retry project load", "Reintentar carga del proyecto")}</button></div> : <>
        {job && <p className="processing-status">{t("Server job state (unchanged by inspection)", "Estado de trabajo del servidor (sin cambio por inspección)")}: {job.state}</p>}
        <JointResultWorkbench key={`${projectId}:${owner}:${instrumentRevision}`} initial={inspection ?? undefined}/>
      </>}
      {problem && <p className="project-error" role="alert">{problem}</p>}
    </section>
  </div>;
}
