import { useEffect, useRef, useState } from "react";

/** Parent is keyed by successful job identity; existing verifiers do all admission. */
export function ResultBundleInput<T>({ verify, onOpened, es }: {
  verify: (file: Blob) => Promise<T>; onOpened: (result: T) => void; es: boolean;
}) {
  const t = (en: string, sp: string) => es ? sp : en;
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(""), [failed, setFailed] = useState(false);
  const epoch = useRef(0);
  useEffect(() => () => { epoch.current++; }, []);
  return <div className="processing-run-form">
    <label className="select-control"><span>{t("Open saved ZIP for selected job", "Abrir ZIP guardado del trabajo seleccionado")}</span>
      <input className="select" type="file" accept=".zip,application/zip" disabled={busy} onChange={async event => {
        const file = event.currentTarget.files?.[0]; event.currentTarget.value = "";
        if (!file) return;
        const token = ++epoch.current; setBusy(true); setMessage(""); setFailed(false);
        try {
          const result = await verify(file);
          if (epoch.current !== token) return;
          onOpened(result); setMessage(t("Saved ZIP verified against this selected job; no upload or new computation.", "ZIP guardado verificado contra este trabajo; sin carga ni cálculo nuevo."));
        } catch (error) {
          if (epoch.current !== token) return;
          setFailed(true); setMessage(`${t("Saved file rejected; the last verified result remains. No imported values displayed.", "Archivo rechazado; se conserva el último resultado verificado. Sin valores importados visibles.")} ${error instanceof Error ? error.message : String(error)}`);
        } finally { if (epoch.current === token) setBusy(false); }
      }} />
    </label>
    {busy && <p role="status">{t("Verifying original member hashes and selected identity…", "Verificando hashes originales e identidad seleccionada…")}</p>}
    {message && <p className={failed ? "project-error" : "project-notice"} role={failed ? "alert" : "status"}>{message}</p>}
  </div>;
}
