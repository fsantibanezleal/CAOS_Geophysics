/** Actual authenticated original-file custody, not a scientific/provider demo. */
import {useEffect,useId,useRef,useState} from 'react';
import {useShellLang,useFormat} from '@fasl-work/caos-app-shell';
import {MagneticLineSurveyApi} from './api';
import {assetRoles,assetMime,parseAssetHeader,datasetRequestFromReceipts,startFromPublishedDataset,
  type AssetRole,type AssetReceipt,type RightsDecision} from './intakeContract';
import type {SurveySourceChoice} from './SurveyInstrument';
import {SurveyActionGate,type SurveyActionLease} from './actionCustody';
import './instrument.css';

const labels:Record<AssetRole,[string,string]>={original_csv:['Complete original CSV','CSV original completo'],
  metadata_json:['Immutable metadata JSON','JSON de metadatos inmutable'],request_json:['Immutable scientific request JSON','JSON de solicitud científica inmutable'],
  typed_auxiliary_bundle:['Typed auxiliary bundle','Paquete auxiliar tipado'],navigation_original:['Original navigation','Navegación original'],
  base_original:['Original base station','Estación base original'],calibration_original:['Original calibration','Calibración original'],
  reference_original:['Original reference field','Campo de referencia original'],offset_original:['Original independent offsets','Offsets independientes originales']};

export function SurveyIntakePanel({api,projectId,disabled=false,onDataset,claimAction}:{api:MagneticLineSurveyApi;projectId:string;
  disabled?:boolean;onDataset:(source:SurveySourceChoice)=>void;claimAction?:()=>SurveyActionLease|null}) {
  const es=useShellLang()==='es',format=useFormat(),t=(en:string,sp:string)=>es?sp:en,id=useId();
  const [file,setFile]=useState<File|null>(null),[role,setRole]=useState<AssetRole>('original_csv');
  const [provider,setProvider]=useState(''),[doi,setDoi]=useState(''),[citation,setCitation]=useState('');
  const [rights,setRights]=useState(''),[decision,setDecision]=useState<RightsDecision>('mirror');
  const [attribution,setAttribution]=useState(''),[digest,setDigest]=useState(''),[attested,setAttested]=useState(false);
  const [kind,setKind]=useState<'authored'|'user_original'>('user_original');
  const [receipts,setReceipts]=useState<{project:string;value:AssetReceipt;name:string}[]>([]);
  const [busy,setBusy]=useState(false),[error,setError]=useState(false),[published,setPublished]=useState(false);
  const generation=useRef(0),localGate=useRef(new SurveyActionGate()),mounted=useRef(true),fileInput=useRef<HTMLInputElement|null>(null);
  useEffect(()=>{
    generation.current++;setFile(null);setDigest('');setAttested(false);
    setReceipts([]);setError(false);setPublished(false);
    setProvider('');setDoi('');setCitation('');setRights('');setAttribution('');
    if(fileInput.current)fileInput.current.value='';
  },[projectId]);
  useEffect(()=>{mounted.current=true;return ()=>{mounted.current=false;generation.current++;};},[]);
  const owned=receipts.filter(v=>v.project===projectId);
  let canPrepare=false;
  try{datasetRequestFromReceipts(owned.map(v=>v.value));canPrepare=true;}catch{/* No invented references. */}
  const unavailable=disabled||busy;
  async function upload() {
    const selected=file;if(unavailable||!selected||!attested)return;
    const lease=claimAction?claimAction():localGate.current.claim(projectId);if(!lease)return;
    const epoch=generation.current,currentProject=projectId;setBusy(true);setError(false);
    try {
      const header=parseAssetHeader({schema:'m03-owner-asset/1',role,filename:selected.name,mime:assetMime(role),source:{
        provider,doi:doi||null,citation:citation||null,rights_statement:rights,rights_decision:decision,
        private_storage_permission:attested,attribution,expected_bytes:selected.size,expected_sha256:digest}});
      const receipt=await api.upload(currentProject,selected,header);
      if(epoch!==generation.current)return;
      setReceipts(previous=>[...previous,{project:currentProject,value:receipt,name:selected.name}]);
      setFile(null);setDigest('');setAttested(false);setPublished(false);if(fileInput.current)fileInput.current.value='';
    } catch {if(epoch===generation.current)setError(true);}
    finally {lease.release();if(mounted.current)setBusy(false);}
  }
  async function prepare() {
    if(unavailable||!canPrepare||published)return;
    const lease=claimAction?claimAction():localGate.current.claim(projectId);if(!lease)return;
    const epoch=generation.current;setBusy(true);setError(false);
    try {
      const request=datasetRequestFromReceipts(owned.map(v=>v.value));
      // Await actual publication/refusal. Project changes discard presentation,
      // not observation by pretending a client abort rolled back durable bytes.
      const receipt=await api.createDataset(projectId,request);
      if(epoch!==generation.current)return;
      const original=owned.find(v=>v.value.role==='original_csv')!;
      onDataset({id:receipt.dataset_id,title:{en:original.name,es:original.name},start:startFromPublishedDataset(request,receipt),
        original_rows:receipt.rows,source_kind:kind,review:{
          en:'Actual published owner dataset. Provider verification is not established; field and host acceptance remain separate.',
          es:'Dataset del propietario realmente publicado. Verificación del proveedor no establecida; aceptación de campo y host son separadas.'}});
      setPublished(true);
    } catch {if(epoch===generation.current)setError(true);}
    finally {lease.release();if(mounted.current)setBusy(false);}
  }
  const input=(key:string,label:string,value:string,set:(v:string)=>void,max:number)=><label className="select-control" htmlFor={`${id}-${key}`}>
    <span>{label}</span><input className="select" id={`${id}-${key}`} disabled={unavailable} value={value} maxLength={max}
      onChange={event=>set(event.target.value)} autoComplete="off"/></label>;
  return <section className="m03-intake" aria-label={t('Original-file custody and dataset preparation','Custodia de archivos originales y preparación de dataset')}>
    <h3>{t('Original files, source declaration and owner dataset','Archivos originales, declaración de fuente y dataset del propietario')}</h3>
    <p>{t('Upload complete original bytes and immutable sidecars. No downsampling, example data, provider fetch or inferred rights. A source declaration is not provider verification.',
      'Cargue bytes originales completos y archivos auxiliares inmutables. Sin submuestreo, ejemplos, descarga del proveedor ni derechos inferidos. Declarar una fuente no verifica al proveedor.')}</p>
    <form onSubmit={event=>{event.preventDefault();void upload();}}>
      <fieldset className="m03-intake-fields" disabled={unavailable}>
        <legend>{t('Exact original custody','Custodia original exacta')}</legend>
        <label className="select-control" htmlFor={`${id}-role`}><span>{t('Stored source role','Rol de fuente almacenada')}</span>
          <select className="select" id={`${id}-role`} value={role} onChange={event=>setRole(event.target.value as AssetRole)}>
            {assetRoles.map(v=><option key={v} value={v}>{labels[v][es?1:0]}</option>)}</select></label>
        <label className="select-control" htmlFor={`${id}-file`}><span>{t('Actual selected original file','Archivo original realmente seleccionado')}</span>
          <input id={`${id}-file`} type="file" ref={fileInput} onChange={event=>{setFile(event.target.files?.[0]??null);setDigest('');setAttested(false);}}/></label>
        {file&&<p>{file.name} · {format(file.size)} {t('actual bytes','bytes reales')}</p>}
        {input('sha',t('Actual file SHA256, verified again by the server','SHA256 real del archivo, verificado nuevamente por el servidor'),digest,setDigest,64)}
        {input('provider',t('Actual provider or source','Proveedor o fuente real'),provider,setProvider,200)}
        {input('doi',t('DOI if actually supplied, otherwise blank','DOI si realmente existe, en otro caso vacío'),doi,setDoi,200)}
        {input('citation',t('Actual source citation, optional','Cita real de la fuente, opcional'),citation,setCitation,2000)}
        {input('attribution',t('Required actual attribution','Atribución real requerida'),attribution,setAttribution,2000)}
        <label className="select-control" htmlFor={`${id}-rights`}><span>{t('Exact rights statement','Declaración exacta de derechos')}</span>
          <textarea id={`${id}-rights`} value={rights} maxLength={4000} onChange={event=>setRights(event.target.value)}/></label>
        <label className="select-control" htmlFor={`${id}-decision`}><span>{t('Recorded rights decision','Decisión de derechos registrada')}</span>
          <select className="select" id={`${id}-decision`} value={decision} onChange={event=>setDecision(event.target.value as RightsDecision)}>
            <option value="mirror">{t('Original mirroring permitted','Copia del original permitida')}</option>
            <option value="provider-link-only">{t('Provider link only','Solo enlace del proveedor')}</option>
            <option value="derivative-only">{t('Derivative only','Solo derivado')}</option>
            <option value="forbidden">{t('Storage forbidden','Almacenamiento prohibido')}</option>
          </select></label>
        <label className="m03-attestation"><input type="checkbox" checked={attested} onChange={event=>setAttested(event.target.checked)}/>
          {t('I have actual permission to privately store these exact original bytes. This does not change scientific export rights.',
            'Tengo permiso real para almacenar privadamente estos bytes originales exactos. Esto no cambia derechos de exportación científica.')}</label>
        <button className="btn" type="submit" disabled={!file||!attested}>{t('Upload actual original','Cargar original real')}</button>
      </fieldset>
    </form>
    {busy&&<p role="status">{t('Awaiting actual server receipt. Closing this view does not prove native or upload cancellation.',
      'Esperando recibo real del servidor. Cerrar esta vista no prueba cancelación de carga ni proceso nativo.')}</p>}
    {error&&<p role="alert">{t('The actual custody or preparation request was refused. No dataset or scientific success is inferred.',
      'La solicitud real de custodia o preparación fue rechazada. No se infiere dataset ni éxito científico.')}</p>}
    <ul>{owned.map(v=><li key={v.value.asset_id}>{labels[v.value.role][es?1:0]}: {v.name} · {v.value.asset_id} · {v.value.sha256} · {format(v.value.bytes)} B</li>)}</ul>
    <label className="select-control" htmlFor={`${id}-kind`}><span>{t('Factual source kind declaration','Declaración factual de tipo de fuente')}</span>
      <select className="select" id={`${id}-kind`} value={kind} disabled={unavailable} onChange={event=>setKind(event.target.value as typeof kind)}>
        <option value="user_original">{t('User-held original, provider unverified','Original del usuario, proveedor no verificado')}</option>
        <option value="authored">{t('Explicit authored control, not field','Control autorado explícito, no campo')}</option></select></label>
    <div className="m03-actions">
      <button className="btn" type="button" disabled={unavailable||!canPrepare||published} onClick={()=>void prepare()}>{t('Prepare and publish owner dataset','Preparar y publicar dataset del propietario')}</button>
      <button className="btn" type="button" disabled={unavailable||!owned.length} onClick={()=>{setReceipts([]);setPublished(false);}}>{t('Clear local references, not stored bytes','Borrar referencias locales, no bytes almacenados')}</button>
    </div>
    {published&&<p role="status">{t('Actual dataset published and added to source choices. Science has not started; field and host eligibility are not established.',
      'Dataset realmente publicado y agregado a opciones de fuente. La ciencia no ha comenzado; elegibilidad de campo y host no establecida.')}</p>}
  </section>;
}
