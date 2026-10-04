import { useEffect, useRef, useState } from "react";
import { readVelocityFiles, type VelocityAdmission } from "../api/velocity-local-contracts";
import { VelocityLocalInstrument } from "./VelocityLocalInstrument";

export function VelocityLocalWorkbench({ es, onCurated }: { es: boolean; onCurated: () => void }) {
  const t = (en: string, sp: string) => es ? sp : en;
  const [resultFile, setResultFile] = useState<File | null>(null), [manifestFile, setManifestFile] = useState<File | null>(null);
  const [admitted, setAdmitted] = useState<VelocityAdmission | null>(null), [error, setError] = useState("");
  const [busy, setBusy] = useState(false), [controls, setControls] = useState(false);
  const epoch = useRef(0);
  useEffect(() => () => { epoch.current++; }, []);
  const pick = (file: File | null, result: boolean) => { epoch.current++; setBusy(false); setError(""); if (result) setResultFile(file); else setManifestFile(file); };
  const open = async () => {
    if (!resultFile || !manifestFile) return;
    const current = ++epoch.current; setBusy(true); setError("");
    try { const value = await readVelocityFiles(resultFile, manifestFile); if (current === epoch.current) { setAdmitted(value); setControls(false); } }
    catch { if (current === epoch.current) setError(t("Files rejected; the last admitted view is unchanged. Select the original result.json and matching manifest.json.", "Archivos rechazados; la última vista admitida no cambia. Seleccione result.json original y manifest.json correspondiente.")); }
    finally { if (current === epoch.current) setBusy(false); }
  };
  return <div className="page-body wide workbench processing-workbench">
    <aside className={`instrument-sidebar processing-sidebar ${controls ? "expanded" : ""}`}>
      <div className="instrument-brand"><span className="small-caps">{t("LOCAL FILES · NO UPLOAD", "ARCHIVOS LOCALES · SIN CARGA")}</span><h1>{t("First-arrival velocity results", "Resultados de velocidad de primeras llegadas")}</h1></div>
      <button className="btn mobile-controls-toggle" aria-expanded={controls} onClick={() => setControls(!controls)}>{t("Local result controls", "Controles de resultado local")}</button>
      <div className="processing-controls">
        <button className="btn" onClick={onCurated}>{t("Curated cases", "Casos curados")}</button>
        <label className="select-control"><span>{t("Original result.json", "result.json original")}</span><input type="file" accept=".json,application/json" onChange={e => pick(e.target.files?.[0] ?? null, true)} /></label>
        <label className="select-control"><span>{t("Matching manifest.json", "manifest.json correspondiente")}</span><input type="file" accept=".json,application/json" onChange={e => pick(e.target.files?.[0] ?? null, false)} /></label>
        <button className="btn" disabled={busy || !resultFile || !manifestFile} onClick={() => void open()}>{t("Open local velocity result", "Abrir resultado local de velocidad")}</button>
        {busy && <p role="status">{t("Checking original bytes and scalar contract…", "Comprobando bytes originales y contrato escalar…")}</p>}
        {error && <p role="alert">{error}</p>}
        <p className="plot-note">{t("Run the local first-arrival tool first. Files stay in this browser; no account, server upload, new solve or training.", "Ejecute primero la herramienta local de primeras llegadas. Los archivos permanecen en este navegador; sin cuenta, carga al servidor, nuevo cálculo ni entrenamiento.")}</p>
      </div>
    </aside>
    <section className="instrument-main processing-main" aria-label={t("Local velocity inspection", "Inspección local de velocidad")}>
      {admitted ? <VelocityLocalInstrument key={admitted.resultSha256} admitted={admitted} es={es}/> : <p>{t("Choose both files from one completed local generation. No example or synthetic result is loaded automatically.", "Seleccione ambos archivos de una generación local completa. No se carga automáticamente ningún ejemplo ni resultado sintético.")}</p>}
    </section>
  </div>;
}
