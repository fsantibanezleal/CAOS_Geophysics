/** Additive authenticated instrument leaf. Parent owns navigation and member registry. */
import { useEffect,useMemo,useRef,useState } from 'react';
import { Knob,Readout,useFormat,useShellLang } from '@fasl-work/caos-app-shell';
import { uuid,type SurveyJob,type SurveyResult,type SurveyStart,type CrossoverRow } from './contract';
import { MagneticLineSurveyApi } from './api';
import {profileOrdinal,sameDisplayWindow,type DisplayWindowBinding} from './display';
import { readArrayWindow,readCrossoverWindow,resolveChannelMask,type MemberReader,type ArrayWindow } from './members';
import './instrument.css';

export interface SurveySourceChoice {
  id: string; title: {en:string;es:string}; start: SurveyStart;
  original_rows: number; source_kind: 'authored'|'user_original'|'provider_original';
  review: {en:string;es:string};
}
interface RowView { binding:DisplayWindowBinding;ids:ArrayWindow|null;coordinates:ArrayWindow;values:ArrayWindow;flags:ArrayWindow|null;observed?:ArrayWindow;predicted?:ArrayWindow }
const numbers = (window: ArrayWindow) => window.cells.map(value => {
  if (typeof value !== 'number') throw new Error('Numeric member required');
  return value;
});
function bounds(values: number[]): [number,number] {
  let low=Infinity,high=-Infinity;
  for (const value of values) { low=Math.min(low,value);high=Math.max(high,value); }
  if (!Number.isFinite(low+high)) return [0,1];
  const pad=Math.max((high-low)*.05,Math.max(Math.abs(low),Math.abs(high),1)*1e-9);
  return [low-pad,high+pad];
}
export function SurveyInstrument({api,projectId,sources,readMember:suppliedReader}: {
  api: MagneticLineSurveyApi; projectId: string; sources: SurveySourceChoice[];
  // An actual persisted owner/job/member UUID binding supplied by the parent,
  // not a filename-to-URL fallback or direct provider request.
  readMember?: (job: SurveyJob) => MemberReader;
}) {
  const readMember=useMemo(()=>suppliedReader??((job:SurveyJob)=>api.reader(projectId,job)),[suppliedReader,api,projectId]);
  const es=useShellLang()==='es',format=useFormat(),t=(en:string,sp:string)=>es?sp:en;
  const [sourceId,setSourceId]=useState(sources[0]?.id??'');
  const [savedJobId,setSavedJobId]=useState('');
  const source=sources.find(item=>item.id===sourceId);
  const [jobData,setJob]=useState<SurveyJob|null>(null),[resultData,setResult]=useState<{value:SurveyResult;result_sha256:string}|null>(null);
  const job=jobData?.project_id===projectId?jobData:null;
  const result=resultData&&resultData.value.run_id===job?.job_id&&resultData.result_sha256===job.result_sha256?resultData.value:null;
  const [view,setView]=useState<'lines'|'validation'|'grid'>('lines');
  const [channel,setChannel]=useState(0),[first,setFirst]=useState(0),[selected,setSelected]=useState(0);
  const [plane,setPlane]=useState(0),[gridRow,setGridRow]=useState(0),[gridCell,setGridCell]=useState(0);
  const [verticalScale,setVerticalScale]=useState(1);
  const [rowData,setRows]=useState<RowView|null>(null),[tileData,setTile]=useState<{binding:DisplayWindowBinding;values:ArrayWindow;flags:ArrayWindow}|null>(null);
  // Never render another view/job/channel/window's previous asynchronous data
  // during the render before its effect clears/loads the new selection.
  const windowBinding:DisplayWindowBinding={job_id:job?.job_id??'',result_sha256:job?.result_sha256??'',
    view,selection:view==='lines'?channel:view==='grid'?plane:0,first:view==='grid'?gridRow:first};
  const rows=rowData&&sameDisplayWindow(rowData.binding,windowBinding)?rowData:null;
  const tile=tileData&&sameDisplayWindow(tileData.binding,windowBinding)?tileData:null;
  const [crossovers,setCrossovers]=useState<CrossoverRow[]>([]),[crossFirst,setCrossFirst]=useState(0),[crossSelected,setCrossSelected]=useState(0);
  const [busy,setBusy]=useState(false),[error,setError]=useState(false),[exported,setExported]=useState(false);
  const action=useRef<AbortController|null>(null),generation=useRef(0);
  useEffect(()=>()=>action.current?.abort(),[]);
  useEffect(()=>{
    generation.current++;action.current?.abort();setJob(null);setResult(null);setRows(null);setTile(null);
    setFirst(0);setSelected(0);setCrossovers([]);setCrossFirst(0);setCrossSelected(0);setError(false);setExported(false);setBusy(false);
    setSavedJobId('');
  },[sourceId,projectId]);
  useEffect(()=>{
    if (!job || !['queued','running'].includes(job.state)) return;
    const abort=new AbortController();
    const timer=setTimeout(()=>api.job(projectId,job.job_id,abort.signal).then(value=>{if(!abort.signal.aborted)setJob(value);}).catch(()=>{if(!abort.signal.aborted)setError(true);}),2500);
    return ()=>{clearTimeout(timer);abort.abort();};
  },[api,projectId,job]);
  useEffect(()=>{
    setCrossovers([]);
    if(!job || !result?.crossovers) return;
    const abort=new AbortController();
    readCrossoverWindow(result.crossovers,crossFirst,Math.min(128,result.crossovers.rows-crossFirst),readMember(job),abort.signal)
      .then(value=>{if(!abort.signal.aborted){setCrossovers(value);setCrossSelected(0);}})
      .catch(()=>{if(!abort.signal.aborted)setError(true);});
    return ()=>abort.abort();
  },[job,result,readMember,crossFirst]);
  useEffect(()=>{
    if (!job || job.state!=='succeeded') return;
    const abort=new AbortController();setResult(null);
    api.result(projectId,job,abort.signal).then(value=>{if(!abort.signal.aborted){setResult({value,result_sha256:job.result_sha256!});setChannel(value.channels.length-1);setFirst(0);setSelected(0);}})
      .catch(()=>{if(!abort.signal.aborted)setError(true);});
    return ()=>abort.abort();
  },[api,projectId,job]);
  useEffect(()=>{
    setRows(null);setTile(null);
    if (!job || !result) return;
    const abort=new AbortController(),read=readMember(job);
    const load=async()=>{
      if (view==='grid') {
        const grid=result.grid[plane],count=Math.min(grid.config.ny-gridRow,16,Math.floor(65536/grid.config.nx));
        const [values,flags]=await Promise.all([readArrayWindow(grid.values,gridRow,count,read,abort.signal),
          readArrayWindow(grid.support_mask,gridRow,count,read,abort.signal)]);
        if (!abort.signal.aborted) {setTile({binding:{job_id:job.job_id,result_sha256:job.result_sha256!,view:'grid',selection:plane,first:gridRow},values,flags});setGridCell(0);}
        return;
      }
      const count=Math.min(4096,(view==='validation'?result.evaluation.observed.shape[0]:result.geometry.rows)-first);
      if (view==='validation') {
        const [observed,predicted,values]=await Promise.all([
          readArrayWindow(result.evaluation.observed,first,count,read,abort.signal),
          readArrayWindow(result.evaluation.predicted,first,count,read,abort.signal),
          readArrayWindow(result.evaluation.residual,first,count,read,abort.signal)]);
        if (!abort.signal.aborted) {setRows({binding:{job_id:job.job_id,result_sha256:job.result_sha256!,view:'validation',selection:0,first},ids:null,coordinates:{...values,cells:[]},
          flags:null,values,observed,predicted});setSelected(0);}
        return;
      }
      const data=result.channels[channel].data;
      const mask=await resolveChannelMask(result,data,read,abort.signal);
      const input=result.input.arrays;
      const ids=input.find(ref=>ref.role==='row_id')!;
      const aligned=result.geometry.arrays.find(ref=>ref.role==='navigation' && ref.shape[0]===result.geometry.rows && ref.ordered_ids_sha256===ids.ordered_ids_sha256);
      const [identifiers,values,flags]=await Promise.all([readArrayWindow(ids,first,count,read,abort.signal),
        readArrayWindow(data,first,count,read,abort.signal),readArrayWindow(mask,first,count,read,abort.signal)]);
      let coordinates:ArrayWindow;
      if (aligned) coordinates=await readArrayWindow(aligned,first,count,read,abort.signal);
      else {
        const axes=await Promise.all(['easting','northing','upward'].map(role=>readArrayWindow(input.find(ref=>ref.role===role)!,first,count,read,abort.signal)));
        coordinates={...axes[0],columns:3,cells:Array.from({length:count*3},(_,i)=>axes[i%3].cells[Math.floor(i/3)])};
      }
      if (!abort.signal.aborted) {setRows({binding:{job_id:job.job_id,result_sha256:job.result_sha256!,view:'lines',selection:channel,first},ids:identifiers,coordinates,values,flags});setSelected(0);}
    };
    load().catch(()=>{if(!abort.signal.aborted)setError(true);});
    return ()=>abort.abort();
  },[result,job,readMember,view,first,channel,plane,gridRow]);
  const perform=async(work:(signal:AbortSignal)=>Promise<void>)=>{
    action.current?.abort();const abort=new AbortController();action.current=abort;
    const epoch=generation.current;setBusy(true);setError(false);
    try {await work(abort.signal);} catch {if(!abort.signal.aborted && epoch===generation.current)setError(true);}
    finally {if(epoch===generation.current)setBusy(false);}
  };
  const series=useMemo(()=>rows?numbers(rows.values).map((value,i)=>rows.flags&&Number(rows.flags.cells[i])?null:value):[],[rows]);
  const [low,high]=bounds(series.filter((v):v is number=>v!==null));
  const mid=(low+high)/2,span=(high-low)/verticalScale;
  const y=(value:number)=>250-(value-(mid-span/2))/span*210;
  const x=(index:number)=>55+index/Math.max(series.length-1,1)*560;
  const selectedValue=rows&&selected<rows.values.rows && (!rows.flags || rows.flags.cells[selected]===0) ? Number(rows.values.cells[selected]) : null;
  const active=job && ['queued','running'].includes(job.state);
  const total=view==='validation'?result?.evaluation.observed.shape[0]:result?.geometry.rows;
  return <section className="m03-instrument" aria-label={t('Aeromagnetic survey instrument','Instrumento de levantamiento aeromagnético')}>
    <form className="m03-saved-open" onSubmit={event=>{event.preventDefault();void perform(async signal=>{
      setJob(null);setResult(null);setRows(null);setTile(null);setCrossovers([]);setExported(false);
      const saved=await api.job(projectId,uuid(savedJobId),signal);
      if(!signal.aborted){setFirst(0);setCrossFirst(0);setPlane(0);setGridRow(0);setJob(saved);}
    });}}>
      <label className="select-control" htmlFor="m03-saved-job"><span>{t('Saved owner job UUID','UUID de trabajo guardado del propietario')}</span>
        <input className="select" id="m03-saved-job" value={savedJobId} maxLength={36} autoComplete="off" spellCheck={false}
          disabled={busy||!!active} onChange={event=>setSavedJobId(event.target.value)}/></label>
      <button className="btn" type="submit" disabled={!savedJobId||busy||!!active}>{t('Open saved evidence','Abrir evidencia guardada')}</button>
    </form>
    <label className="select-control"><span>{t('Owner-bound original source','Fuente original vinculada al propietario')}</span>
      <select className="select" value={sourceId} disabled={sources.length===0||!!active} onChange={event=>{setJob(null);setResult(null);setSourceId(event.target.value);}}>
        {sources.map(item=><option key={item.id} value={item.id}>{es?item.title.es:item.title.en}</option>)}
      </select></label>
    {source&&<p>{es?source.review.es:source.review.en} · {format(source.original_rows)} {t('original rows; never substituted','filas originales; nunca sustituidas')}. {source.source_kind==='authored'?t('Authored control, not field data.','Control autorado, no datos de campo.'):t('Source authentication and field acceptance are separate.','Autenticación de fuente y aceptación de campo son distintas.')}</p>}
    <div className="m03-actions">
      <button className="btn" disabled={!source||busy||!!active} onClick={()=>perform(async signal=>{setJob(null);setResult(null);setExported(false);const started=await api.start(projectId,source!.start,signal);if(!signal.aborted)setJob(started);})}>{t('Run complete survey','Procesar levantamiento completo')}</button>
      <button className="btn" disabled={!active||busy} onClick={()=>perform(async signal=>{const cancelled=await api.cancel(projectId,job!.job_id,signal);if(!signal.aborted)setJob(cancelled);})}>{t('Cancel and drain','Cancelar y drenar')}</button>
      <button className="btn" disabled={!result||busy} onClick={()=>perform(async signal=>{await api.export(projectId,job!.job_id,'private',signal);if(!signal.aborted)setExported(true);})}>{t('Create private export','Crear exportación privada')}</button>
      <button className="btn" disabled={!result||busy} onClick={()=>perform(async signal=>{await api.export(projectId,job!.job_id,'public',signal);if(!signal.aborted)setExported(true);})}>{t('Request rights-checked public export','Solicitar exportación pública con permisos')}</button>
    </div>
    {job&&<p role="status">{t('Execution state','Estado de ejecución')}: {job.state} {job.cancel_requested?t('drain requested, not yet proved','drenaje solicitado, aún no comprobado'):''}</p>}
    {error&&<p role="alert">{t('The owner request or verified member could not be completed. No missing value was filled.','No se pudo completar la solicitud del propietario o miembro verificado. No se rellenó ningún valor ausente.')}</p>}
    {exported&&<p role="status">{t('Export response received. Replay availability and actual execution remain distinct.','Respuesta de exportación recibida. Disponibilidad y ejecución real de reproducción son distintas.')}</p>}
    {result&&<>
      <p>{t('Scientific verdict','Veredicto científico')}: {result.verdict.overall} · {format(result.fit.fit_count)} {t('actual global fits','ajustes globales reales')} · {format(result.fit.selected_depth_m)} m · λ {format(result.fit.selected_damping)}.</p>
      <ul>{result.verdict.gates.map(gate=><li key={gate.gate_id}>{gate.gate_id}: {gate.verdict}</li>)}</ul>
      <label className="select-control"><span>{t('Scientific view','Vista científica')}</span><select className="select" value={view} onChange={event=>{setView(event.target.value as typeof view);setFirst(0);setSelected(0);}}>
        <option value="lines">{t('Original-row corrections','Correcciones en filas originales')}</option><option value="validation">{t('Retained outer residuals','Residuos externos conservados')}</option><option value="grid">{t('Global fitted planes','Planos ajustados globales')}</option></select></label>
      {view==='lines'&&<label className="select-control"><span>{t('Actual channel','Canal real')}</span><select className="select" value={channel} onChange={event=>setChannel(Number(event.target.value))}>{result.channels.map((item,index)=><option key={item.channel_id} value={index}>{item.channel_id} · {item.kind} [nT]</option>)}</select></label>}
      {view!=='grid'&&<>
        <Knob id="m03-display-zoom" label={{en:'Display vertical magnification',es:'Magnificación vertical de visualización'}} hint={{en:'Changes only the plotted nT range. Does not refit, retune or change QC.',es:'Cambia solo el rango gráfico en nT. No reajusta, retoca ni cambia QC.'}} unit="×" value={verticalScale} min={.5} max={4} step={.1} onChange={setVerticalScale}/>
        <div className="m03-actions"><button className="btn" disabled={first===0} onClick={()=>setFirst(Math.max(0,first-4096))}>{view==='validation'?t('Previous held-out ordinals','Ordinales reservados anteriores'):t('Previous original rows','Filas originales anteriores')}</button><button className="btn" disabled={first+4096>=(total??0)} onClick={()=>setFirst(first+4096)}>{view==='validation'?t('Next held-out ordinals','Ordinales reservados siguientes'):t('Next original rows','Filas originales siguientes')}</button></div>
        {rows&&<>
          <svg className="m03-profile" viewBox="0 0 650 290" role="img" tabIndex={0} aria-label={t('Source-order magnetic profile','Perfil magnético en orden original')}
            onPointerMove={event=>{const matrix=event.currentTarget.getScreenCTM();if(!matrix)return;
              const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());
              const ordinal=profileOrdinal(point.x,series.length);if(ordinal!==null)setSelected(ordinal);}}
            onKeyDown={event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
              event.preventDefault();setSelected(event.key==='Home'?0:event.key==='End'?series.length-1:
                Math.max(0,Math.min(series.length-1,selected+(event.key==='ArrowRight'?1:-1))));}}}>
            <path className="m03-axis" d="M55 30V250H620"/>
            {series.map((value,index)=>value===null?null:<circle key={index} cx={x(index)} cy={y(value)} r={index===selected?4:1.4} className={index===selected?'m03-picked':'m03-point'}/>)}
            <text x="4" y="30">nT</text><text x="4" y="45">{format(mid+span/2)}</text><text x="4" y="250">{format(mid-span/2)}</text>
          </svg>
          <p>{view==='validation'?t('Retained evaluation ordinal, not original row ID','Ordinal de evaluación conservada, no ID de fila original'):t('Original source-order row','Fila en orden de fuente original')} {format(first)} {t('to','a')} {format(first+rows.values.rows-1)}</p>
          <Readout lane="replay" provenance={result.lane==='local_synthetic'?'synthetic':'real'} title={{en:'Linked row readout',es:'Lectura de fila vinculada'}} items={[
            {label:{en:view==='validation'?'Held-out ordinal':'Source-order row',es:view==='validation'?'Ordinal reservado':'Fila en orden de fuente'},value:first+selected,unitless:true},
            {label:{en:view==='validation'?'Held-out residual':'Selected channel',es:view==='validation'?'Residuo reservado':'Canal seleccionado'},value:selectedValue,unit:'nT'},
            ...(rows.flags?[{label:{en:'QC flag',es:'Flag QC'},value:Number(rows.flags.cells[selected]),unitless:true}]:[]),
            ...(view==='lines'?[{label:{en:'Easting',es:'Este'},value:Number(rows.coordinates.cells[3*selected]),unit:'m'},
              {label:{en:'Northing',es:'Norte'},value:Number(rows.coordinates.cells[3*selected+1]),unit:'m'},
              {label:{en:'Upward height',es:'Altura positiva hacia arriba'},value:Number(rows.coordinates.cells[3*selected+2]),unit:'m'}]:[
              {label:{en:'Observed',es:'Observado'},value:Number(rows.observed!.cells[selected]),unit:'nT'},
              {label:{en:'Predicted',es:'Predicho'},value:Number(rows.predicted!.cells[selected]),unit:'nT'}]),
          ]}/>
          {view==='lines'&&<>
            <p>{t('Original row ID','ID de fila original')}: {String(rows.ids?.cells[selected])}</p>
            <PlanMap coordinates={rows.coordinates} selected={selected} onSelect={setSelected} crossovers={crossovers} crossover={crossSelected} onCrossover={setCrossSelected} label={t('Linked metric plan: current verified original-row and crossover windows','Plano métrico vinculado: ventanas verificadas de filas originales y cruces')}/>
          </>}
          <p>{view==='validation'?t('These are retained scored observations in evaluation order. No original ID or QC mask is invented.','Son observaciones puntuadas conservadas en orden de evaluación. No se inventa ID original ni máscara QC.'):t('Only a verified original-row window is displayed; the backend fit processed the complete survey.','Solo se muestra una ventana de filas originales verificadas; el backend ajustó el levantamiento completo.')} {t('Fragment custody does not recompute the entire array hash.','La custodia de fragmentos no recalcula el hash del arreglo completo.')}</p>
        </>}
      </>}
      {result.crossovers&&<section aria-label={t('Original sealed crossovers','Cruces originales sellados')}>
        <h3>{t('Sealed crossover evidence','Evidencia de cruces sellada')}</h3>
        <p>{t('Geometry acceptance is not a solved leveling correction. Rejected, null or missing intersections are not filled.','Aceptación geométrica no significa corrección de nivelación resuelta. Cruces rechazados, nulos o ausentes no se rellenan.')}</p>
        <div className="m03-actions"><button className="btn" disabled={crossFirst===0} onClick={()=>setCrossFirst(Math.max(0,crossFirst-128))}>{t('Previous crossover window','Ventana anterior de cruces')}</button><button className="btn" disabled={crossFirst+128>=result.crossovers!.rows} onClick={()=>setCrossFirst(crossFirst+128)}>{t('Next crossover window','Ventana siguiente de cruces')}</button></div>
        <label className="select-control"><span>{t('Actual intersection','Intersección real')}</span><select className="select" value={crossSelected} onChange={event=>setCrossSelected(Number(event.target.value))}>{crossovers.map((item,index)=><option key={item.crossover_id} value={index}>{item.crossover_id}: {item.disposition}</option>)}</select></label>
        {crossovers[crossSelected]&&<>
          <p>{crossovers[crossSelected].flight_segment_id} / {crossovers[crossSelected].tie_segment_id} · {crossovers[crossSelected].reasons.join(', ')||t('No recorded rejection reason','Sin motivo de rechazo registrado')}</p>
          <Readout lane="replay" provenance={result.lane==='local_synthetic'?'synthetic':'real'} title={{en:'Selected sealed crossover',es:'Cruce sellado seleccionado'}} items={[
            {label:{en:'Easting',es:'Este'},value:crossovers[crossSelected].easting_m,unit:'m'},
            {label:{en:'Northing',es:'Norte'},value:crossovers[crossSelected].northing_m,unit:'m'},
            {label:{en:'Height difference',es:'Diferencia de altura'},value:crossovers[crossSelected].height_difference_m,unit:'m'},
            {label:{en:'Time separation',es:'Separación temporal'},value:crossovers[crossSelected].time_separation_s,unit:'s'},
          ]}/>
        </>}
      </section>}
      {view==='grid'&&<>
        <label className="select-control"><span>{t('Physical prediction plane','Plano físico de predicción')}</span><select className="select" value={plane} onChange={event=>{setPlane(Number(event.target.value));setGridRow(0);}}>{result.grid.map((grid,index)=><option key={grid.role} value={index}>{grid.role} · {format(grid.config.plane_upward_m)} m · {grid.config.datum}</option>)}</select></label>
        <div className="m03-actions"><button className="btn" disabled={gridRow===0} onClick={()=>setGridRow(Math.max(0,gridRow-16))}>{t('Previous grid rows','Filas de malla anteriores')}</button><button className="btn" disabled={gridRow+(tile?.values.rows??16)>=result.grid[plane].config.ny} onClick={()=>setGridRow(gridRow+(tile?.values.rows??16))}>{t('Next grid rows','Filas de malla siguientes')}</button></div>
        {tile&&<GridTile tile={tile} cell={gridCell} onSelect={setGridCell}/ >}
        {tile&&<Readout lane="replay" provenance={result.lane==='local_synthetic'?'synthetic':'real'} title={{en:'Selected physical grid cell',es:'Celda física seleccionada'}} items={[
          {label:{en:'Easting',es:'Este'},value:result.grid[plane].config.origin_e_m+gridCell%tile.values.columns*result.grid[plane].config.spacing_e_m,unit:'m'},
          {label:{en:'Northing',es:'Norte'},value:result.grid[plane].config.origin_n_m+(gridRow+Math.floor(gridCell/tile.values.columns))*result.grid[plane].config.spacing_n_m,unit:'m'},
          {label:{en:'Predicted anomaly',es:'Anomalía predicha'},value:(Number(tile.flags.cells[gridCell])&~4096)===0?Number(tile.values.cells[gridCell]):null,unit:'nT'},
          {label:{en:'Support mask',es:'Máscara de soporte'},value:Number(tile.flags.cells[gridCell]),unitless:true},
        ]}/ >}
      </>}
    </>}
  </section>;
}
function PlanMap({coordinates,selected,onSelect,crossovers,crossover,onCrossover,label}:{coordinates:ArrayWindow;selected:number;onSelect:(index:number)=>void;crossovers:CrossoverRow[];crossover:number;onCrossover:(index:number)=>void;label:string}) {
  const xyz=numbers(coordinates),east=xyz.filter((_,i)=>i%3===0),north=xyz.filter((_,i)=>i%3===1);
  const finite=crossovers.filter(item=>item.easting_m!==null && item.northing_m!==null);
  const [e0,e1]=bounds([...east,...finite.map(item=>item.easting_m!)]),[n0,n1]=bounds([...north,...finite.map(item=>item.northing_m!)]);
  const span=Math.max(e1-e0,n1-n0),emin=(e0+e1-span)/2,nmin=(n0+n1-span)/2;
  const x=(e:number)=>55+(e-emin)/span*500,y=(n:number)=>530-(n-nmin)/span*500;
  return <svg className="m03-plan" viewBox="0 0 650 575" role="group" aria-label={label}>
    <title>{label}</title>
    <path className="m03-axis" d="M55 30V530H555"/><text x="4" y="20">N [m]</text><text x="555" y="565">E [m]</text>
    <text x="55" y="555">{emin.toPrecision(6)}</text><text x="490" y="555">{(emin+span).toPrecision(6)}</text><text x="4" y="45">{(nmin+span).toPrecision(6)}</text><text x="4" y="530">{nmin.toPrecision(6)}</text>
    {east.map((e,index)=><circle key={index} cx={x(e)} cy={y(north[index])} r={index===selected?5:2} className={index===selected?'m03-picked':'m03-point'} onPointerEnter={()=>onSelect(index)}><title>{coordinates.first+index}</title></circle>)}
    {crossovers.map((item,index)=>item.easting_m===null || item.northing_m===null?null:<circle key={item.crossover_id} cx={x(item.easting_m)} cy={y(item.northing_m)} r={index===crossover?7:4} className="m03-cross" tabIndex={0} role="button" aria-label={`${item.crossover_id}: ${item.disposition}`} onPointerEnter={()=>onCrossover(index)} onFocus={()=>onCrossover(index)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onCrossover(index);}}}><title>{item.crossover_id}: {item.disposition}</title></circle>)}
  </svg>;
}
function GridTile({tile,cell,onSelect}:{tile:{values:ArrayWindow;flags:ArrayWindow};cell:number;onSelect:(index:number)=>void}) {
  const canvas=useRef<HTMLCanvasElement>(null);
  useEffect(()=>{
    const context=canvas.current?.getContext('2d');if(!context)return;
    const values=numbers(tile.values),valid=values.filter((_,index)=>(Number(tile.flags.cells[index])&~4096)===0),[low,high]=bounds(valid);
    const image=context.createImageData(tile.values.columns,tile.values.rows);
    values.forEach((value,index)=>{
      if ((Number(tile.flags.cells[index])&~4096)!==0) return;
      const scale=Math.max(0,Math.min(1,(value-low)/(high-low))),offset=4*index;
      image.data[offset]=Math.round(255*scale);image.data[offset+1]=Math.round(160*(1-Math.abs(scale-.5)*2));image.data[offset+2]=Math.round(255*(1-scale));image.data[offset+3]=255;
    });context.putImageData(image,0,0);
  },[tile]);
  return <canvas className="m03-grid" ref={canvas} width={tile.values.columns} height={tile.values.rows} aria-label="nT" tabIndex={0}
    onPointerMove={event=>{const rect=event.currentTarget.getBoundingClientRect();const x=Math.min(tile.values.columns-1,Math.max(0,Math.floor((event.clientX-rect.left)/rect.width*tile.values.columns))),y=Math.min(tile.values.rows-1,Math.max(0,Math.floor((event.clientY-rect.top)/rect.height*tile.values.rows)));onSelect(y*tile.values.columns+x);}}
    onKeyDown={event=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();const move={ArrowLeft:-1,ArrowRight:1,ArrowUp:-tile.values.columns,ArrowDown:tile.values.columns}[event.key]!;onSelect(Math.max(0,Math.min(tile.values.cells.length-1,cell+move)));}}}/>;
}
