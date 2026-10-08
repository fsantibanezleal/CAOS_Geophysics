import { readWaveformDraft, editWaveformDraft, editWaveformChannels, draftIssues } from "./waveform-request";
import { useState } from "react";

export function WaveformRequestControls({request,onChange,es,disabled}:{request:string;onChange:(value:string)=>void;es:boolean;disabled:boolean}){
  const t=(en:string,sp:string)=>es?sp:en;
  const [editError,setEditError]=useState("");
  let d:Record<string,unknown>;
  try{d=readWaveformDraft(request);}catch{return <p role="status">{t("Correct the imported JSON object before using structured controls.","Corrija el objeto JSON importado antes de usar los controles estructurados.")}</p>;}
  const at=(path:(string|number)[])=>{let v:unknown=d;for(const k of path){if(v===null||typeof v!=="object")return undefined;v=(v as Record<string|number,unknown>)[k];}return v;};
  function change(path:(string|number)[],value:unknown){
    setEditError("");try{
    let text=request.trim()?request:JSON.stringify({schema:"caos.local-waveform-request.v1",representation:"unrestituted_integer_counts"});
    // Method constants, not numerical defaults. Every scientific value is explicit.
    if(at(["processing"])===undefined)text=editWaveformDraft(text,["processing"],{output:"native",filter_mode:"offline-zero-phase"});
    if(at(["source"])===undefined)text=editWaveformDraft(text,["source"],{provider_url:null,declared_sha256:null});
    onChange(editWaveformDraft(text,path,value));
    }catch{setEditError(t("Imported field has an incompatible structure; correct advanced JSON without discarding evidence.","El campo importado tiene estructura incompatible; corrija JSON avanzado sin descartar evidencia."));}
  }
  function changeChannels(remove?:number){
    setEditError("");try{onChange(editWaveformChannels(request,remove));}catch{setEditError(t("Imported channel/ADC structure is incompatible; correct advanced JSON without discarding evidence.","La estructura importada de canales/ADC es incompatible; corrija JSON avanzado sin descartar evidencia."));}
  }
  function field(label:string,path:(string|number)[],numeric=false){
    const value=at(path);return <label className="select-control" key={path.join(".")}>{label}<input className="select" aria-label={label} inputMode={numeric?"decimal":undefined} disabled={disabled} value={value===undefined||value===null?"":String(value)} onChange={e=>{const raw=e.target.value;const number=/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(raw)&&Number.isFinite(Number(raw));change(path,raw===""?undefined:numeric&&number?Number(raw):raw);}}/></label>;
  }
  function choice(label:string,path:string[],values:{value:string;label:string}[]){return <label className="select-control">{label}<select className="select" disabled={disabled} value={String(at(path)??"")} onChange={e=>change(path,e.target.value||undefined)}><option value="">{t("Explicit selection required","Selección explícita requerida")}</option>{values.map(v=><option key={v.value} value={v.value}>{v.label}</option>)}</select></label>;}
  const channels=Array.isArray(d.channels)?d.channels:[];
  const issues=draftIssues(request);
  return <div data-testid="waveform-structured-request">
    {editError&&<p role="alert">{editError}</p>}
    <p>{t("No scientific defaults. Enter every required value or import an explicit request. Editing creates a new request, never changes an earlier job.","Sin valores científicos predeterminados. Ingrese cada valor requerido o importe una solicitud explícita. La edición crea otra solicitud, nunca cambia un trabajo previo.")}</p>
    <details open><summary>{t("UTC and NSLC","UTC y NSLC")}</summary>
      {field(t("Conditioning start UTC","Inicio de acondicionamiento UTC"),["conditioning_start_utc"])}
      {field(t("Conditioning end UTC","Fin de acondicionamiento UTC"),["conditioning_end_utc"])}
      {field(t("Analysis start UTC","Inicio de análisis UTC"),["analysis_start_utc"])}
      {field(t("Analysis end UTC","Fin de análisis UTC"),["analysis_end_utc"])}
      <p>{t("UTC: YYYY-MM-DDTHH:mm:ss[.ffffff]Z. Conditioning 10–300 s; analysis at least 5 s inside it. NSLC must match unchanged originals.","UTC: YYYY-MM-DDTHH:mm:ss[.ffffff]Z. Acondicionamiento 10–300 s; análisis de al menos 5 s dentro de él. NSLC debe coincidir con originales sin cambios.")}</p>
      {channels.map((_,i)=><fieldset key={i}><legend>c0{i} · NSLC</legend>
        {field(t("Network","Red")+` c0${i}`,["channels",i,"network"])}{field(t("Station","Estación")+` c0${i}`,["channels",i,"station"])}
        {field(t("Location","Ubicación")+` c0${i}`,["channels",i,"location"])}
        <label><input type="checkbox" disabled={disabled} checked={at(["channels",i,"location"])===""} onChange={e=>change(["channels",i,"location"],e.target.checked?"":undefined)}/>{t("Location is explicitly blank","Ubicación explícitamente vacía")} c0{i}</label>
        {field(t("Channel","Canal")+` c0${i}`,["channels",i,"channel"])}
        <p>{t("ADC rails: unknown unless explicit evidence is supplied in advanced JSON.","Límites ADC: desconocidos salvo evidencia explícita en JSON avanzado.")}</p>
        <button className="btn" disabled={disabled} onClick={()=>changeChannels(i)}>{t("Remove channel","Eliminar canal")} c0{i}</button>
      </fieldset>)}
      <button className="btn" disabled={disabled||channels.length>=3} onClick={()=>changeChannels()}>{t("Add explicit channel","Agregar canal explícito")}</button>
    </details>
    <details><summary>{t("Source declaration and rights","Declaración de fuente y derechos")}</summary>
      {choice(t("Source kind","Tipo de fuente"),["source","kind"],[{value:"user",label:t("User-supplied originals","Originales del usuario")},{value:"provider",label:t("Declared provider originals","Originales del proveedor declarado")}])}
      {field(t("Source citation","Cita de fuente"),["source","citation"])}
      {field(t("Previous processing statement","Declaración de procesamiento previo"),["source","processing_statement"])}
      {choice(t("Processing rights","Derechos de procesamiento"),["source","rights"],[{value:"private-use-attested",label:t("Attested private use","Uso privado atestiguado")},{value:"reviewed-public-scsn",label:t("Reviewed public SCSN rights","Derechos SCSN públicos revisados")}])}
      <p>{t("Provider URL, declared hash and evidenced ADC rails remain explicit advanced JSON fields; no provider is invented.","URL de proveedor, hash declarado y límites ADC con evidencia siguen como campos JSON avanzados explícitos; no se inventa un proveedor.")}</p>
    </details>
    <details><summary>{t("Response and prefilter","Respuesta y prefiltro")}</summary>
      <p>{t("Output: native StationXML units (m, m/s or m/s2), never assumed velocity. Complex response is evaluated by the scientific worker.","Salida: unidades nativas StationXML (m, m/s o m/s2), nunca velocidad supuesta. El trabajador científico evalúa la respuesta compleja.")}</p>
      {[0,1,2,3].map(i=>field(`${t("Prefilter corner","Esquina de prefiltro")} ${i+1} [Hz]`,["processing","prefilter_hz",i],true))}
      {field(t("Water level [dB]","Nivel de agua [dB]"),["processing","water_level_db"],true)}
      <label><input type="checkbox" disabled={disabled} checked={at(["processing","water_level_db"])===null} onChange={e=>change(["processing","water_level_db"],e.target.checked?null:undefined)}/>{t("Explicitly disable water level","Desactivar explícitamente nivel de agua")}</label>
      <p>{t("Four strictly increasing corners; first ≥0.05 Hz. Inner corners enclose the bandpass. Water level: null or 20–120 dB.","Cuatro esquinas estrictamente crecientes; primera ≥0.05 Hz. Esquinas internas contienen la banda. Nivel de agua: null o 20–120 dB.")}</p>
    </details>
    <details><summary>{t("Acausal filter","Filtro acausal")}</summary>
      {[0,1].map(i=>field(`${t("Bandpass","Banda pasante")} ${i===0?t("low","inferior"):t("high","superior")} [Hz]`,["processing","bandpass_hz",i],true))}
      {field(t("Filter order [2–6]","Orden del filtro [2–6]"),["processing","filter_order"],true)}
      {field(t("Time taper fraction [0.01–0.10]","Fracción de taper temporal [0.01–0.10]"),["processing","taper_fraction"],true)}
      {field(t("Edge guard [s]","Margen de borde [s]"),["processing","edge_guard_s"],true)}
      <p>{t("Fixed offline-zero-phase SOS filter: acausal, not an online warning. Actual valid-edge mask and taper are shown after calculation.","Filtro SOS offline-zero-phase fijo: acausal, no una alerta online. Máscara de bordes válidos y taper reales se muestran tras el cálculo.")}</p>
    </details>
    <details><summary>STA/LTA · {t("unlabelled triggers","disparos sin etiquetas")}</summary>
      {field("STA [s]",["processing","sta_s"],true)}{field("LTA [s]",["processing","lta_s"],true)}
      {field(t("Trigger on ratio","Razón de activación"),["processing","threshold_on"],true)}{field(t("Trigger off ratio","Razón de desactivación"),["processing","threshold_off"],true)}
      {field(t("Refractory [s]","Refractario [s]"),["processing","refractory_s"],true)}
      <p>{t("STA 0.05–2 s < LTA 0.5–20 s; 1 < off < on ≤100; refractory 0–10 s. No P/S assignment or timing uncertainty is inferred.","STA 0.05–2 s < LTA 0.5–20 s; 1 < off < on ≤100; refractario 0–10 s. No se infiere P/S ni incertidumbre temporal.")}</p>
    </details>
    <details><summary>{t("Welch PSD","PSD Welch")}</summary>{field(t("Welch segment [samples]","Segmento Welch [muestras]"),["processing","welch_segment_samples"],true)}<p>{t("Power of two, 64–8192 samples. The worker validates against each actual sample rate/window. PSD retains squared native units per Hz.","Potencia de dos, 64–8192 muestras. El trabajador valida con cada frecuencia/ventana real. PSD conserva unidades nativas cuadradas por Hz.")}</p></details>
    <p role="status">{issues.length?t("Incomplete or invalid explicit fields: ","Campos explícitos incompletos o inválidos: ")+issues.join(", "):t("Explicit contract complete; source review and server validation are still required.","Contrato explícito completo; aún requiere revisión de fuente y validación del servidor.")}</p>
  </div>;
}
