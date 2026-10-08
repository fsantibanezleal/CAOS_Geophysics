import { useEffect, useMemo, useRef, useState } from "react";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { ApiClient, ApiHttpError } from "../api/client";
import { browserJointInputs, inspectJointInputs, JointInputApi, type JointDatasetReceipt, type JointInput,
  type JointMemberReceipt, type JointSourceAttestation } from "../api/joint-input";
import type { JointFile } from "../api/joint-result";

/** Parent supplies the selected owned project and mounts this in its ONE rail. */
export function JointNativeInputPanel({ projectId, ownerId, api, onIndexed, onCleared, onSessionExpired }: {
  projectId: string; ownerId: string; api: ApiClient; onIndexed: (receipt: JointDatasetReceipt) => void; onCleared?: () => void; onSessionExpired?: () => void;
}) {
  const es=useShellLang()==="es",t=(en: string,sp: string)=>es?sp:en,client=useMemo(()=>new JointInputApi(api),[api]);
  const [section,setSection]=useState("originals"),[development,setDevelopment]=useState<JointFile[]>([]),[sealed,setSealed]=useState<JointFile[]>([]);
  const [input,setInput]=useState<JointInput|null>(null),[busy,setBusy]=useState(false),[problem,setProblem]=useState("");
  const [provider,setProvider]=useState(""),[citation,setCitation]=useState(""),[doi,setDoi]=useState(""),[attribution,setAttribution]=useState("");
  const [rights,setRights]=useState<JointSourceAttestation["rights_decision"]>("provider-link-only"),[statement,setStatement]=useState(""),[consent,setConsent]=useState(false);
  const [receipts,setReceipts]=useState(new Map<string,JointMemberReceipt>()),[dataset,setDataset]=useState<JointDatasetReceipt|null>(null);
  const [receiptKey,setReceiptKey]=useState("");
  const control=useRef<AbortController|null>(null),generation=useRef(0);
  const reset=()=> { control.current?.abort();generation.current++;setInput(null);setDevelopment([]);setSealed([]);setReceipts(new Map());setDataset(null);setBusy(false);setProblem("");
    setProvider("");setCitation("");setDoi("");setAttribution("");setRights("provider-link-only");setStatement("");setConsent(false);setReceiptKey("");onCleared?.(); };
  useEffect(()=> { reset();return ()=> {control.current?.abort();generation.current++;}; },[projectId,ownerId,client]);
  function fail(error: unknown) {
    if(error instanceof ApiHttpError&&error.status===401){reset();setProblem(t("Session expired; private receipts cleared. Sign in again.","Sesión expirada; recibos privados borrados de la vista. Inicie sesión de nuevo."));onSessionExpired?.();return;}
    setProblem(error instanceof ApiHttpError?error.code:error instanceof Error?error.message:t("Original request failed","Falló la solicitud de originales"));
  }
  async function inspect() {
    if(busy||!development.length||!sealed.length)return;const run=++generation.current,abort=new AbortController();control.current=abort;setBusy(true);setProblem("");
    try { const value=await inspectJointInputs([...development,...sealed],abort.signal);if(run!==generation.current)return;setInput(value);setSection("attribution"); }
    catch(error){if(run===generation.current&&!abort.signal.aborted)fail(error);}
    finally{if(run===generation.current)setBusy(false);}
  }
  async function upload() {
    if(!input||busy||dataset||!consent||!provider.trim()||!attribution.trim()||statement.trim().length<10)return;
    const run=++generation.current,abort=new AbortController();control.current=abort;setBusy(true);setProblem("");setSection("receipts");
    const accepted=new Map(receipts),source: JointSourceAttestation={provider,doi:doi.trim()||null,citation:citation.trim()||null,
      attribution,rights_decision:rights,rights_statement:statement,private_storage_permission:"attested"};
    try {
      for(const member of input.members) {
        abort.signal.throwIfAborted();const key=`${member.role}/${member.name}`;if(accepted.has(key))continue;
        const receipt=await client.upload(projectId,member,source,abort.signal);if(run!==generation.current)return;
        if(receipt.owner_id!==ownerId)throw new Error("joint_original_owner_mismatch");accepted.set(key,receipt);setReceipts(new Map(accepted));
      }
      const indexed=await client.index(projectId,input,accepted,abort.signal);if(run!==generation.current)return;
      setDataset(indexed);onIndexed(indexed);
    } catch(error){if(run===generation.current&&!abort.signal.aborted)fail(error);}
    finally{if(run===generation.current)setBusy(false);}
  }
  const locked=busy||receipts.size>0,sourceReady=provider.trim()&&attribution.trim()&&statement.trim().length>=10&&consent;
  const selectedKey=receipts.has(receiptKey)?receiptKey:receipts.keys().next().value??"",selectedReceipt=receipts.get(selectedKey);
  const field=(label: string,value: string,change: (value: string)=>void,maximum: number)=>
    <label className="select-control"><span>{label}</span><input className="input" aria-label={label} value={value} maxLength={maximum} disabled={locked} onChange={e=>change(e.target.value)}/></label>;
  return <section className="processing-actions" data-testid="joint-native-input-panel" aria-label={t("Original joint survey custody","Custodia de encuesta conjunta original")}>
    <label className="select-control"><span>{t("Original input section","Sección de datos originales")}</span>
      <select className="select" aria-label={t("Original input section","Sección de datos originales")} value={section} onChange={e=>setSection(e.target.value)}>
        {[['originals',t("Original directories","Directorios originales")],['attribution',t("Provider and attribution","Proveedor y atribución")],['rights',t("Rights and permission","Derechos y permiso")],['receipts',t("Exact private receipts","Recibos privados exactos")]].map(([id,name])=><option key={id} value={id}>{name}</option>)}
      </select></label>
    {section==="originals"&&<>
      <p className="processing-scope">{t("Two complete ordinary directories, no ZIP. Geometry, masks, units and noise remain in the original request. Sealed values are not decoded here.","Dos directorios originales completos, sin ZIP. Geometría, máscaras, unidades y ruido permanecen en la solicitud original. Los valores reservados no se decodifican aquí.")}</p>
      {([['development',t("Original development directory","Directorio original de desarrollo"),setDevelopment],['sealed',t("Original sealed directory","Directorio original reservado"),setSealed]] as const).map(([role,label,change])=><label className="select-control" key={role}><span>{label}</span><input type="file" multiple {...{webkitdirectory:""} as object} aria-label={label} disabled={locked} onChange={e=>{setInput(null);setProblem("");try {change(e.target.files?browserJointInputs(role,e.target.files):[]);}catch(error){fail(error);}}}/></label>)}
      <button className="btn" disabled={busy||!development.length||!sealed.length||locked} onClick={()=>void inspect()}>{t("Verify opaque original bytes","Verificar bytes originales opacos")}</button>
      {input&&<output>{input.members.length} {t("members verified, native values not decoded","miembros verificados, valores nativos sin decodificar")} · {input.bytes} B</output>}
    </>}
    {section==="attribution"&&<>
      {field(t("Original provider","Proveedor original"),provider,setProvider,200)}
      {field(t("Attribution","Atribución"),attribution,setAttribution,2000)}
      {field(t("Citation (optional)","Cita (opcional)"),citation,setCitation,2000)}
      {field(t("DOI (optional)","DOI (opcional)"),doi,setDoi,200)}
      <button className="btn" onClick={()=>setSection("rights")}>{t("Review private-storage rights","Revisar derechos de almacenamiento privado")}</button>
    </>}
    {section==="rights"&&<>
      <label className="select-control"><span>{t("Rights decision","Decisión de derechos")}</span><select className="select" aria-label={t("Rights decision","Decisión de derechos")} value={rights} disabled={locked} onChange={e=>setRights(e.target.value as JointSourceAttestation["rights_decision"])}>
        <option value="provider-link-only">{t("Provider link only","Solo enlace al proveedor")}</option><option value="derivative-only">{t("Derivative only","Solo derivados")}</option><option value="mirror">{t("Mirroring permitted","Réplica permitida")}</option></select></label>
      <label className="select-control"><span>{t("Original rights statement","Declaración original de derechos")}</span><textarea className="input" aria-label={t("Original rights statement","Declaración original de derechos")} rows={3} maxLength={4000} value={statement} disabled={locked} onChange={e=>setStatement(e.target.value)}/></label>
      <label><input type="checkbox" checked={consent} disabled={locked} onChange={e=>setConsent(e.target.checked)}/>{t("I attest permission to store every supplied original privately. This does not grant public redistribution.","Declaro permiso para almacenar privadamente todos los originales suministrados. Esto no autoriza redistribución pública.")}</label>
      <button className="btn" disabled={busy||!input||!sourceReady||!!dataset} onClick={()=>void upload()}>{t("Upload originals and index, not a scientific run","Cargar originales e indexar, no ejecutar ciencia")}</button>
    </>}
    {section==="receipts"&&<>
      <output aria-live="polite">{receipts.size} / {input?.members.length??0} {t("originals stored privately","originales almacenados privadamente")}</output>
      <p className="processing-scope">{t("No automatic retry or deletion on failure. Successful original receipts remain. A structural index is not inversion, calibration, scientific acceptance or host admission.","Sin reintento ni eliminación automática al fallar. Los recibos originales exitosos se conservan. Un índice estructural no es inversión, calibración, aceptación científica ni admisión del servidor.")}</p>
      {!!receipts.size&&selectedReceipt&&<details className="processing-provenance"><summary>{t("Original versions, hashes and custody","Versiones, hashes y custodia originales")}</summary>
        <label className="select-control"><span>{t("Original member receipt","Recibo de miembro original")}</span>
          <select className="select" aria-label={t("Original member receipt","Recibo de miembro original")} value={selectedKey} onChange={e=>setReceiptKey(e.target.value)}>
            {(['development','sealed'] as const).map(role=><optgroup key={role} label={role==='development'?t("Development originals","Originales de desarrollo"):t("Sealed originals","Originales reservados")}>
              {[...receipts.keys()].filter(key=>key.startsWith(role+'/')).map(key=><option key={key} value={key}>{key}</option>)}
            </optgroup>)}
          </select></label>
        <p data-testid="joint-native-member-receipt"><a href={`/api/projects/${selectedReceipt.project_id}/assets/${selectedReceipt.asset_id}`}>{selectedKey}</a> · {t("Version","Versión")} {selectedReceipt.source.version} · {selectedReceipt.byte_count} B · <code>{selectedReceipt.sha256}</code></p>
        <p>{selectedReceipt.source.rights_decision} · {selectedReceipt.source.private_storage_permission} · {selectedReceipt.source.attribution}</p>
      </details>}
      {!busy&&receipts.size>0&&!dataset&&<button className="btn" onClick={()=>void upload()}>{t("Explicitly continue remaining uploads / index","Continuar explícitamente cargas restantes / índice")}</button>}
      {dataset&&<p className="processing-provenance" data-testid="joint-native-indexed">{t("Structural dataset selected for the existing processing sidebar","Conjunto estructural seleccionado para la barra existente")} · <code>{dataset.dataset_id}</code> · <code>{dataset.sha256}</code></p>}
    </>}
    {busy&&<button className="btn" onClick={()=>{control.current?.abort();generation.current++;setBusy(false);setProblem(t("Cancelled locally; accepted or uncertain server originals are not deleted.","Cancelado localmente; los originales aceptados o inciertos del servidor no se eliminan."));}}>{t("Cancel transfer / inspection","Cancelar transferencia / inspección")}</button>}
    {problem&&<p role="alert">{problem}</p>}
    <details className="processing-provenance"><summary>{t("Scientific run versus inspection","Ejecución científica frente a inspección")}</summary>
      <p>{t("Use the explicit scientific processing action in the existing sidebar after its source/runtime admission. The offline CLI performs real fits, freeze and sealed evaluation. The native result instrument only inspects/export those exact outputs; it never runs an inverse in the browser.","Use la acción científica explícita en la barra existente tras su admisión de fuentes y entorno. La CLI fuera de línea ejecuta ajustes reales, congelación y evaluación reservada. El instrumento nativo solo inspecciona/exporta esos resultados exactos; nunca invierte en el navegador.")}</p>
      <a href="https://github.com/fsantibanezleal/CAOS_Geophysics/blob/main/docs/guides/24_private_joint_execution.md" target="_blank" rel="noreferrer">{t("Execution and custody wiki","Wiki de ejecución y custodia")}</a>
      <a href="https://github.com/fsantibanezleal/CAOS_Geophysics/blob/main/docs/guides/26_private_joint_original_inputs.md" target="_blank" rel="noreferrer">{t("Original-input and privacy guide","Guía de originales y privacidad")}</a>
    </details>
    <button className="btn" disabled={busy} onClick={reset}>{t("Forget this local selection, preserve server originals","Olvidar selección local, conservar originales del servidor")}</button>
  </section>;
}
