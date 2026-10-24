import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ApiClient, ApiHttpError } from "../api/client";
import { LifecycleApi, type AccountView, type AuthConfig, type DeletionView, type ProjectView } from "../api/lifecycle";
import type { RawAsset } from "../api/contracts";
import { RawUploadForm } from "./RawUploadForm";
import { prepareUpload } from "../api/upload-metadata";
import { FORMAT_SPECS, type RawFormat } from "../api/upload-metadata";

type GuestStep = "login" | "register" | "verify" | "recover" | "reset";
type OwnerStep = "projects" | "upload" | "receipts" | "account";
type Props = { es: boolean; onClose: () => void; onOpenWorkbench?: (projectId: string) => void; onOwnerCleared?: () => void };

function errorMessage(error: unknown, es: boolean): string {
  const t = (en: string, spanish: string) => es ? spanish : en;
  if (error instanceof ApiHttpError) {
    const known: Record<string, [string, string]> = {
      LOGIN_BAD_CREDENTIALS: ["Email or password is incorrect, or the account is unavailable.", "Correo o contraseña incorrectos, o la cuenta no está disponible."],
      REGISTER_USER_ALREADY_EXISTS: ["An account already uses this email.", "Ya existe una cuenta con este correo."],
      VERIFY_USER_BAD_TOKEN: ["Verification token is invalid or expired.", "El código de verificación no es válido o expiró."],
      RESET_PASSWORD_BAD_TOKEN: ["Reset token is invalid or expired.", "El código de restablecimiento no es válido o expiró."],
      rights_forbidden: ["Forbidden-rights originals cannot be stored.", "No se pueden almacenar originales con derechos prohibidos."],
      physical_metadata_invalid: ["Physical metadata was rejected by the API.", "La API rechazó los metadatos físicos."],
      metadata_invalid: ["Upload metadata was rejected by the API.", "La API rechazó los metadatos de carga."],
      geometry_column_missing: ["Declared CSV columns are absent from the file.", "Las columnas CSV declaradas no están en el archivo."],
      format_invalid: ["File bytes do not match the declared format.", "Los bytes no corresponden al formato declarado."],
      mime_format_mismatch: ["Filename, MIME and declared format disagree.", "Nombre, MIME y formato declarado no coinciden."],
      stationxml_missing: ["MiniSEED requires a StationXML asset in this project.", "MiniSEED requiere un activo StationXML en este proyecto."],
      account_quota_exceeded: ["Account raw-byte quota exceeded.", "Se excedió la cuota de bytes originales de la cuenta."],
      upload_too_large: ["The file exceeds the API size limit.", "El archivo excede el límite de la API."],
      csrf_invalid: ["Security token expired. Retry the action; your inputs remain.", "El código de seguridad expiró. Reintente la acción; sus datos siguen aquí."],
      origin_forbidden: ["This request must come from the same site origin.", "Esta solicitud debe provenir del mismo origen del sitio."],
      request_invalid: ["The API rejected request fields.", "La API rechazó campos de la solicitud."],
      raw_integrity_failed: ["Stored bytes disagree with the receipt; operator review is required.", "Los bytes almacenados no coinciden con el recibo; se requiere revisión del operador."],
      backup_reconciliation_required: ["A project backup exists. Operator reconciliation is required before deletion; no data was deleted.", "Existe un respaldo del proyecto. Se requiere conciliación del operador antes de borrar; no se eliminaron datos."],
      raw_state_unresolved: ["Project raw storage needs operator review; no data was deleted.", "El almacenamiento original requiere revisión del operador; no se eliminaron datos."],
    };
    const base = known[error.code] ? t(...known[error.code]) : error.status === 429 ? t("Rate limit reached. Wait and retry.", "Límite de solicitudes alcanzado. Espere y reintente.") : error.status === 401 ? t("Session expired. Sign in again.", "La sesión expiró. Inicie sesión de nuevo.") : `${t("API request failed", "Falló la solicitud a la API")} (${error.status}: ${error.code})`;
    return error.fields.length ? `${base} ${t("Fields", "Campos")}: ${error.fields.join(", ")}.` : base;
  }
  return `${t("Service or response unavailable", "Servicio o respuesta no disponible")}: ${error instanceof Error ? error.message : String(error)}`;
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export function ProjectDrawer({ es, onClose, onOpenWorkbench, onOwnerCleared }: Props) {
  const t = (en: string, spanish: string) => es ? spanish : en;
  const dialog = useRef<HTMLDialogElement>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const api = useMemo(() => new LifecycleApi(new ApiClient(window.location.origin)), []);
  const epoch = useRef(0);
  const probeController = useRef<AbortController | null>(null);
  const ownerCleared = useRef(onOwnerCleared);
  ownerCleared.current = onOwnerCleared;
  const [availability, setAvailability] = useState<"checking" | "ready" | "unavailable">("checking");
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [account, setAccount] = useState<AccountView | null>(null);
  const [projects, setProjects] = useState<ProjectView[]>([]);
  const [projectId, setProjectId] = useState("");
  const [assets, setAssets] = useState<RawAsset[]>([]);
  const [receipt, setReceipt] = useState<RawAsset | null>(null);
  const [deletion, setDeletion] = useState<DeletionView | null>(null);
  const [guestStep, setGuestStep] = useState<GuestStep>("login");
  const [ownerStep, setOwnerStep] = useState<OwnerStep>("projects");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [deleteName, setDeleteName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const guestSteps: GuestStep[] = config?.mode === "email" ? ["login", ...(config.registration_enabled ? ["register" as const] : []), ...(config.mail_flows_enabled ? ["verify", "recover", "reset"] as const : [])] : ["login"];
  const effectiveStep = guestSteps.includes(guestStep) ? guestStep : "login";
  const selectedProject = projects.find(project => project.id === projectId);
  const rightsName = (decision: RawAsset["source"]["rights_decision"]) => ({
    mirror: t("mirror permitted", "réplica permitida"),
    "provider-link-only": t("provider link only", "solo enlace al proveedor"),
    "derivative-only": t("derivatives only", "solo derivados"),
    forbidden: t("forbidden", "prohibido"),
  })[decision];
  const deletionStatus = (value: DeletionView) => value.external_backup_status === "not_configured"
    ? t("External backups are not configured. This receipt does not claim backup erasure.", "No hay respaldos externos configurados. Este recibo no afirma borrado de respaldos.")
    : t("Server status: pending_reconciliation; this is not evidence that an external backup exists or was erased.", "Estado del servidor: pending_reconciliation; esto no demuestra que exista un respaldo externo ni que se haya borrado.");

  useEffect(() => {
    const node = dialog.current;
    node?.showModal();
    return () => { if (node?.open) node.close(); };
  }, []);

  useEffect(() => { if (error) errorRef.current?.scrollIntoView({ block: "nearest" }); }, [error]);

  const clearSecrets = () => { setPassword(""); setToken(""); setNewPassword(""); };
  const clearOwner = useCallback(() => {
    ++epoch.current; probeController.current?.abort();
    setAccount(null); setProjects([]); setProjectId(""); setAssets([]); setReceipt(null); setDeletion(null); setDeleteName(""); setOwnerStep("projects"); setBusy(false);
    setPassword(""); setToken(""); setNewPassword(""); ownerCleared.current?.();
  }, []);
  const loadProjects = useCallback(async (preferredId?: string) => {
    const requestEpoch = epoch.current;
    const list = await api.projects();
    if (requestEpoch !== epoch.current) throw new DOMException("Stale account request", "AbortError");
    setProjects(list);
    setProjectId(current => preferredId && list.some(project => project.id === preferredId) ? preferredId : list.some(project => project.id === current) ? current : list[0]?.id ?? "");
  }, [api]);

  const probe = useCallback(async () => {
    probeController.current?.abort();
    const controller = new AbortController(); probeController.current = controller;
    const requestEpoch = ++epoch.current;
    setAvailability("checking"); setConfig(null); setError(""); setNotice(""); setBusy(false);
    setAccount(null); setProjects([]); setProjectId(""); setAssets([]); setReceipt(null); setDeletion(null);
    setPassword(""); setToken(""); setNewPassword("");
    try {
      const snapshot = await api.session(controller.signal);
      if (requestEpoch !== epoch.current) return;
      setConfig(snapshot.config);
      setAvailability("ready");
      if (snapshot.account) { setAccount(snapshot.account); await loadProjects(); }
      else clearOwner();
    } catch (failure) {
      if (requestEpoch !== epoch.current || controller.signal.aborted) return;
      clearOwner(); setConfig(null); setAvailability("unavailable"); setError(errorMessage(failure, es));
    }
  }, [api, es, loadProjects, clearOwner]);

  useEffect(() => {
    void probe();
    return () => { ++epoch.current; probeController.current?.abort(); };
  }, [probe]);

  useEffect(() => {
    if (!account || !projectId) { setAssets([]); return; }
    let current = true;
    setAssets([]);
    api.assets(projectId).then(list => { if (current) setAssets(list); }).catch(failure => {
      if (!current) return;
      if (failure instanceof ApiHttpError && failure.status === 401) clearOwner();
      setError(errorMessage(failure, es));
    });
    return () => { current = false; };
  }, [api, account, projectId, es, clearOwner]);

  const act = async (operation: (checked: <T>(promise: Promise<T>) => Promise<T>) => Promise<void>): Promise<void> => {
    probeController.current?.abort();
    const requestEpoch = epoch.current;
    const checked = async <T,>(promise: Promise<T>): Promise<T> => {
      const result = await promise;
      if (requestEpoch !== epoch.current) throw new DOMException("Stale account request", "AbortError");
      return result;
    };
    setBusy(true); setError(""); setNotice("");
    try { await operation(checked); }
    catch (failure) {
      if (requestEpoch !== epoch.current) return;
      if (failure instanceof ApiHttpError && failure.status === 401) clearOwner();
      setError(errorMessage(failure, es));
    } finally { if (requestEpoch === epoch.current) setBusy(false); }
  };

  const auth = (event: FormEvent) => {
    event.preventDefault();
    if (!config || availability !== "ready" || busy) return;
    const authEpoch = epoch.current;
    void act(async checked => {
      if (effectiveStep === "register") {
        await checked(api.register(email.trim(), password));
        setGuestStep("verify");
        setNotice(t("Account created. Check email and paste the verification token below.", "Cuenta creada. Revise su correo y pegue el código de verificación."));
      } else if (effectiveStep === "verify") {
        await checked(api.verify(token.trim()));
        setGuestStep("login");
        setNotice(t("Account verified. Sign in to access projects.", "Cuenta verificada. Inicie sesión para acceder a proyectos."));
      } else if (effectiveStep === "recover") {
        await checked(api.forgotPassword(email.trim()));
        setGuestStep("reset");
        setNotice(t("If the account exists, a reset token was emailed.", "Si la cuenta existe, se envió un código de restablecimiento."));
      } else if (effectiveStep === "reset") {
        await checked(api.resetPassword(token.trim(), newPassword));
        setGuestStep("login");
        setNotice(t("Password changed. Sign in again.", "Contraseña cambiada. Inicie sesión de nuevo."));
      } else {
        const snapshot = await checked(api.loginSession(email.trim(), password));
        setConfig(snapshot.config); setAccount(snapshot.account); await checked(loadProjects());
        setNotice(t("Signed in to your private projects.", "Sesión iniciada en sus proyectos privados."));
      }
    }).finally(() => { if (authEpoch === epoch.current) clearSecrets(); });
  };

  const createProject = (event: FormEvent) => {
    event.preventDefault();
    void act(async checked => {
      const project = await checked(api.createProject(projectName.trim(), projectDescription.trim()));
      await checked(loadProjects(project.id));
      setProjectName(""); setProjectDescription(""); setOwnerStep("upload");
      setNotice(t("Project created. Add an original when ready.", "Proyecto creado. Agregue un original cuando esté listo."));
    });
  };

  const upload = async (file: File, declaration: ReturnType<typeof prepareUpload>) => act(async checked => {
    if (!projectId) throw new Error("No project selected");
    const result = await checked(api.upload(projectId, file, declaration));
    setAssets(await checked(api.assets(projectId)));
    setReceipt(result); setOwnerStep("receipts");
    setNotice(t("Original stored; raw metadata checked only. Scientific QC has not run.", "Original almacenado; solo se revisaron metadatos originales. No se ha ejecutado control científico."));
  });

  const showReceipt = (assetId: string) => { void act(async checked => {
    setReceipt(await checked(api.receipt(projectId, assetId)));
    setOwnerStep("receipts");
  }); };

  const download = (asset: RawAsset) => { void act(async checked => {
    saveBlob(await checked(api.download(projectId, asset)), asset.original_filename);
    setNotice(t("Downloaded bytes matched the receipt SHA-256.", "Los bytes descargados coinciden con el SHA-256 del recibo."));
  }); };

  const exportProject = () => { void act(async checked => {
    saveBlob(await checked(api.exportProject(projectId)), `project-${projectId}.zip`);
    setNotice(t("Owner project export downloaded. Verify the ZIP manifest before reuse.", "Exportación del proyecto descargada. Verifique el manifiesto ZIP antes de reutilizarla."));
  }); };

  const deleteProject = (event: FormEvent) => { event.preventDefault();
    if (!selectedProject || deleteName !== selectedProject.name) return;
    void act(async checked => {
      const result = await checked(api.deleteProject(selectedProject.id));
      setDeletion(result); setReceipt(null); setAssets([]); setDeleteName("");
      await checked(loadProjects());
      setNotice(`${t("Project deletion receipt issued.", "Se emitió el recibo de eliminación.")} ${deletionStatus(result)}`);
    });
  };

  return <dialog ref={dialog} className="project-dialog" aria-labelledby="project-dialog-title" onCancel={event => { event.preventDefault(); onClose(); }}>
    <div className="project-dialog-header"><div><span className="small-caps">{t("ACCOUNT-GATED RAW DATA", "DATOS ORIGINALES CON CUENTA")}</span><h2 id="project-dialog-title">{t("Projects and originals", "Proyectos y originales")}</h2></div><button className="btn" onClick={onClose} aria-label={t("Close projects", "Cerrar proyectos")}>×</button></div>
    <p className="project-note">{t("Curated research remains readable without an account. Private uploads are not processed datasets or online inversions.", "La investigación curada sigue disponible sin cuenta. Las cargas privadas no son conjuntos procesados ni inversiones en línea.")}</p>
    {availability === "checking" && <p role="status">{t("Checking project service…", "Comprobando servicio de proyectos…")}</p>}
    {availability === "unavailable" && <div className="project-card"><p>{t("The project API is unavailable on this origin. The curated App remains readable; no upload was sent.", "La API de proyectos no está disponible en este origen. App curada sigue legible; no se envió ninguna carga.")}</p><button className="btn" onClick={() => void probe()}>{t("Retry service check", "Reintentar comprobación")}</button></div>}
    {availability === "ready" && config && !account && <>
      {config.mode === "local" && <p className="project-note">{t("Local accounts are managed by the operator. Contact the operator for access or password changes. Courses, curated exploration and browser computation remain public.", "Las cuentas locales son administradas por el operador. Contacte al operador para obtener acceso o cambiar su contraseña. Los cursos, la exploración curada y el cálculo en el navegador siguen siendo públicos.")}</p>}
      {guestSteps.length > 1 && <label className="select-control"><span>{t("Account action", "Acción de cuenta")}</span><select className="select" disabled={busy} value={effectiveStep} onChange={event => { setGuestStep(event.target.value as GuestStep); clearSecrets(); setError(""); setNotice(""); }}>
        <option value="login">{t("Sign in", "Iniciar sesión")}</option>{config.registration_enabled && <option value="register">{t("Create account", "Crear cuenta")}</option>}{config.mail_flows_enabled && <><option value="verify">{t("Verify email", "Verificar correo")}</option><option value="recover">{t("Request password reset", "Solicitar restablecimiento")}</option><option value="reset">{t("Use password reset token", "Usar código de restablecimiento")}</option></>}
      </select></label>}
      <form className="project-form" onSubmit={auth}>
        {effectiveStep !== "verify" && effectiveStep !== "reset" && <label className="select-control"><span>{t("Email", "Correo")}</span><input className="select" type="email" required disabled={busy} autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} /></label>}
        {(effectiveStep === "login" || effectiveStep === "register") && <label className="select-control"><span>{t("Password", "Contraseña")}</span><input className="select" type="password" disabled={busy} minLength={effectiveStep === "register" ? 12 : undefined} required autoComplete={effectiveStep === "register" ? "new-password" : "current-password"} value={password} onChange={event => setPassword(event.target.value)} /></label>}
        {(effectiveStep === "verify" || effectiveStep === "reset") && <label className="select-control"><span>{t("Email token", "Código enviado por correo")}</span><input className="select" required disabled={busy} autoComplete="off" value={token} onChange={event => setToken(event.target.value)} /></label>}
        {effectiveStep === "reset" && <label className="select-control"><span>{t("New password (12+ characters)", "Nueva contraseña (12+ caracteres)")}</span><input className="select" type="password" disabled={busy} minLength={12} required autoComplete="new-password" value={newPassword} onChange={event => setNewPassword(event.target.value)} /></label>}
        <button className="btn primary" disabled={busy}>{effectiveStep === "login" ? t("Sign in", "Iniciar sesión") : effectiveStep === "register" ? t("Register", "Registrarse") : effectiveStep === "verify" ? t("Verify account", "Verificar cuenta") : effectiveStep === "recover" ? t("Send reset token", "Enviar código") : t("Change password", "Cambiar contraseña")}</button>
      </form>
      {effectiveStep === "verify" && <button className="btn" disabled={busy || !email} onClick={() => void act(async checked => { await checked(api.requestVerification(email.trim())); setNotice(t("If the account exists, a verification token was emailed.", "Si la cuenta existe, se envió un código de verificación.")); })}>{t("Resend verification token", "Reenviar código de verificación")}</button>}
    </>}
    {availability === "ready" && config && account && <>
      <p className="project-account">{account.email} · {config.mode === "local" ? t("authenticated local account", "cuenta local autenticada") : t("verified owner", "titular verificado")}</p>
      <label className="select-control"><span>{t("Project workspace section", "Sección de proyectos")}</span><select className="select" disabled={busy} value={ownerStep} onChange={event => { setOwnerStep(event.target.value as OwnerStep); setError(""); }}>
        <option value="projects">{t("Projects", "Proyectos")}</option><option value="upload" disabled={!projectId}>{t("Upload original", "Cargar original")}</option><option value="receipts" disabled={!projectId}>{t("Receipts and downloads", "Recibos y descargas")}</option><option value="account">{t("Account", "Cuenta")}</option>
      </select></label>
      {ownerStep === "projects" && <div className="project-section">
        <h3>{t("Your projects", "Sus proyectos")}</h3>
        {projects.length ? <label className="select-control"><span>{t("Selected project", "Proyecto seleccionado")}</span><select className="select" disabled={busy} value={projectId} onChange={event => { setProjectId(event.target.value); setReceipt(null); setDeleteName(""); }}>{projects.map(project => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label> : <p className="project-note">{t("No project yet. Create one below.", "Todavía no hay proyectos. Cree uno abajo.")}</p>}
        {selectedProject && <div className="project-card"><strong>{selectedProject.name}</strong><p>{selectedProject.description || t("No description", "Sin descripción")}</p><small>{selectedProject.id}</small><div className="project-actions"><button className="btn" onClick={() => setOwnerStep("upload")}>{t("Add original", "Agregar original")}</button><button className="btn" onClick={() => setOwnerStep("receipts")}>{t("View assets", "Ver activos")}</button><button className="btn" disabled={busy} onClick={exportProject}>{t("Export ZIP", "Exportar ZIP")}</button></div></div>}
        <form className="project-form project-card" onSubmit={createProject}><h3>{t("Create project", "Crear proyecto")}</h3><label className="select-control"><span>{t("Project name", "Nombre del proyecto")}</span><input className="select" required maxLength={120} value={projectName} onChange={event => setProjectName(event.target.value)} /></label><label className="select-control"><span>{t("Description", "Descripción")}</span><textarea className="select" maxLength={2000} rows={2} value={projectDescription} onChange={event => setProjectDescription(event.target.value)} /></label><button className="btn primary" disabled={busy}>{t("Create project", "Crear proyecto")}</button></form>
        {selectedProject && <form className="project-form project-delete" onSubmit={deleteProject}><h3>{t("Delete selected project", "Eliminar proyecto seleccionado")}</h3><p>{t("This removes the API-owned project and verified raw files only if the server permits it. Existing backup entries block deletion; external backup erasure is not attempted.", "Esto elimina el proyecto de la API y archivos originales verificados solo si el servidor lo permite. Los respaldos existentes bloquean la eliminación; no se intenta borrar respaldos externos.")}</p><label className="select-control"><span>{t("Type the exact project name to confirm", "Escriba el nombre exacto para confirmar")}: {selectedProject.name}</span><input className="select" required value={deleteName} onChange={event => setDeleteName(event.target.value)} /></label><button className="btn" disabled={busy || deleteName !== selectedProject.name}>{t("Delete project and request receipt", "Eliminar proyecto y solicitar recibo")}</button></form>}
        {deletion && <div className="project-card" role="status"><strong>{t("Deletion receipt", "Recibo de eliminación")}</strong><p>{deletion.receipt_id}</p><p>{deletionStatus(deletion)}</p></div>}
      </div>}
      {selectedProject && onOpenWorkbench && <button className="btn primary" disabled={busy} onClick={() => onOpenWorkbench(selectedProject.id)}>{t("Open processing workbench", "Abrir mesa de procesamiento")}</button>}
      {ownerStep === "upload" && (projectId ? <div className="project-section"><p className="project-account">{t("Private project", "Proyecto privado")}: {selectedProject?.name}</p><RawUploadForm es={es} assets={assets} busy={busy} onSubmit={upload} /></div> : <p>{t("Select or create a project first.", "Seleccione o cree un proyecto primero.")}</p>)}
      {ownerStep === "receipts" && <div className="project-section"><p className="project-account">{t("Private project", "Proyecto privado")}: {selectedProject?.name}</p><h3>{t("Original-byte receipts", "Recibos de bytes originales")}</h3><p className="project-note">{t("raw_metadata_checked means upload metadata and file envelope only; no scientific QC, dataset or solver eligibility.", "raw_metadata_checked significa solo metadatos de carga y envoltura del archivo; no implica control científico, conjunto de datos ni elegibilidad para métodos.")}</p>
        {assets.length ? <ul className="project-assets">{assets.map(asset => <li className="project-card" key={asset.asset_id}><strong>{asset.original_filename}</strong><span>{FORMAT_SPECS[asset.detected_format as RawFormat] ? (es ? FORMAT_SPECS[asset.detected_format as RawFormat].es : FORMAT_SPECS[asset.detected_format as RawFormat].en) : asset.detected_format} · {asset.byte_count.toLocaleString(es ? "es-CL" : "en-US")} bytes</span><div className="project-actions"><button className="btn" disabled={busy} onClick={() => showReceipt(asset.asset_id)}>{t("View receipt", "Ver recibo")}</button><button className="btn" disabled={busy} onClick={() => download(asset)}>{t("Download original", "Descargar original")}</button></div></li>)}</ul> : <p className="project-note">{t("No uploaded originals in this project.", "No hay originales cargados en este proyecto.")}</p>}
        {receipt && receipt.project_id === projectId && <div className="project-card project-receipt"><h3>{t("Owner upload receipt", "Recibo de carga del titular")}</h3><dl><dt>{t("Original", "Original")}</dt><dd>{receipt.original_filename}</dd><dt>SHA-256</dt><dd className="project-hash">{receipt.sha256}</dd><dt>{t("Bytes", "Bytes")}</dt><dd>{receipt.byte_count.toLocaleString(es ? "es-CL" : "en-US")}</dd><dt>{t("Source", "Fuente")}</dt><dd>{receipt.source.provider} · {receipt.source.attribution}</dd>{receipt.source.doi && <><dt>DOI</dt><dd>{receipt.source.doi}</dd></>}{receipt.source.citation && <><dt>{t("Citation", "Cita")}</dt><dd>{receipt.source.citation}</dd></>}<dt>{t("Rights", "Derechos")}</dt><dd>{rightsName(receipt.source.rights_decision)} · {receipt.source.rights_statement}</dd><dt>{t("Private storage", "Almacenamiento privado")}</dt><dd>{receipt.source.private_storage_permission === "attested" ? t("attested separately", "declarado por separado") : t("not attested", "no declarado")}</dd><dt>{t("Coordinates", "Coordenadas")}</dt><dd>{receipt.physical_metadata.coordinate_reference === "epsg" ? `EPSG:${receipt.physical_metadata.epsg}` : receipt.physical_metadata.local_crs} · {receipt.physical_metadata.axis_order} · {receipt.physical_metadata.horizontal_unit}</dd><dt>{t("Datums / vertical", "Datums / vertical")}</dt><dd>{receipt.physical_metadata.horizontal_datum} · {receipt.physical_metadata.vertical_datum} · {receipt.physical_metadata.vertical_positive} · {receipt.physical_metadata.vertical_unit}</dd><dt>{t("Measurement / component", "Medición / componente")}</dt><dd>{receipt.physical_metadata.measurement_unit} · {receipt.physical_metadata.component_frame}</dd><dt>{t("Epoch UTC", "Época UTC")}</dt><dd>{receipt.physical_metadata.epoch_utc}</dd><dt>{t("Declared geometry", "Geometría declarada")}</dt><dd className="project-geometry">{JSON.stringify(receipt.physical_metadata.geometry, null, 2)}</dd><dt>{t("Status", "Estado")}</dt><dd>{t("Raw metadata checked; scientific QC not performed", "Metadatos originales revisados; control científico no realizado")}</dd><dt>{t("Receipt path", "Ruta del recibo")}</dt><dd>{receipt.receipt}</dd></dl><button className="btn" disabled={busy} onClick={() => download(receipt)}>{t("Download verified original", "Descargar original verificado")}</button></div>}
      </div>}
      {ownerStep === "account" && <div className="project-section"><p>{account.email}</p><p className="project-note">{t("Sessions use an HTTP-only same-origin cookie. No password or access token is stored in this browser app.", "Las sesiones usan una cookie HTTP-only del mismo origen. Esta aplicación no almacena contraseña ni token de acceso.")}</p><button className="btn" disabled={busy} onClick={() => void act(async checked => { await checked(api.logout()); clearOwner(); setNotice(t("Signed out. Curated research remains readable.", "Sesión cerrada. La investigación curada sigue disponible.")); })}>{t("Sign out", "Cerrar sesión")}</button></div>}
    </>}
    {error && <p ref={errorRef} role="alert" className="project-error">{error}</p>}
    {notice && <p role="status" className="project-notice">{notice}</p>}
  </dialog>;
}
