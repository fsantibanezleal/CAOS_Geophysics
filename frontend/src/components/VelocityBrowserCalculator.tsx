import { useEffect, useRef, useState } from "react";
import { parseVelocityRequest, type BrowserVelocityResult } from "../api/velocity-browser";
import { Heatmap, Plot } from "./ScientificPlots";

type Reply = { ok: true; result: BrowserVelocityResult; inputSha256: string; inputBytes: number; requestSha256: string; requestBytes: number } | { ok: false; error: string };
type View = "velocity" | "coverage" | "times" | "residual" | "standardized";

export function VelocityBrowserCalculator({ es }: { es: boolean }) {
  const t=(en:string,sp:string)=>es?sp:en;
  const [file,setFile]=useState<File|null>(null),[result,setResult]=useState<BrowserVelocityResult|null>(null),[sha,setSha]=useState(""),[bytes,setBytes]=useState(0),[requestSha,setRequestSha]=useState(""),[requestBytes,setRequestBytes]=useState(0),[lambda,setLambda]=useState("100"),[lambdaLoading,setLambdaLoading]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(""),[view,setView]=useState<View>("velocity"),[ray,setRay]=useState(0);
  const worker=useRef<Worker|null>(null);
  useEffect(()=>()=>worker.current?.terminate(),[]);
  const selectFile=async(next:File|null)=>{
    setFile(next);setResult(null);setSha("");setBytes(0);setRequestSha("");setRequestBytes(0);setError("");
    if(!next||next.size<1||next.size>512*1024)return;
    setLambdaLoading(true);
    try{const source=new Uint8Array(await next.arrayBuffer());setLambda(String(parseVelocityRequest(source).lambda));}
    catch{/* The worker returns the closed-contract error when Calculate is selected. */}
    finally{setLambdaLoading(false);}
  };
  const calculate=async()=>{
    if(!file||file.size<1||file.size>512*1024){setError(t("Choose a JSON request between 1 byte and 512 KiB.","Seleccione una solicitud JSON entre 1 byte y 512 KiB."));return;}
    const selectedLambda=Number(lambda);
    if(!Number.isFinite(selectedLambda)||selectedLambda<=1e-6||selectedLambda>1e6){setError(t("Regularization λ must be greater than 0.000001 and no greater than 1,000,000.","La regularización λ debe ser mayor que 0,000001 y no superar 1.000.000."));return;}
    worker.current?.terminate();const job=new Worker(new URL("../workers/velocity-browser.worker.ts",import.meta.url),{type:"module"});worker.current=job;setBusy(true);setError("");
    job.onmessage=(event:MessageEvent<Reply>)=>{setBusy(false);job.terminate();worker.current=null;if(event.data.ok){setResult(event.data.result);setSha(event.data.inputSha256);setBytes(event.data.inputBytes);setRequestSha(event.data.requestSha256);setRequestBytes(event.data.requestBytes);setView("velocity");setRay(0);}else setError(t(event.data.error,"Solicitud rechazada o cálculo fallido. Revise esquema, unidades, geometría de rayos y límites de parámetros."));};
    job.onerror=()=>{setBusy(false);setError(t("The browser calculation worker stopped unexpectedly; no result was admitted.","El worker de cálculo del navegador se detuvo inesperadamente; no se admitió ningún resultado."));job.terminate();worker.current=null;};
    try{const buffer=await file.arrayBuffer();if(buffer.byteLength!==file.size)throw new Error();job.postMessage({sourceBytes:buffer,lambda:selectedLambda},[buffer]);}catch{setBusy(false);setError(t("Could not read the selected request file.","No se pudo leer el archivo de solicitud seleccionado."));job.terminate();worker.current=null;}
  };
  const download=()=>{if(!result)return;const payload={...result,provenance:{source_file_sha256:sha,source_file_bytes:bytes,effective_request_sha256:requestSha,effective_request_bytes:requestBytes}};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`${result.request.id}-browser-result.json`;a.click();URL.revokeObjectURL(url);};
  const q=result?.request;
  return <article className="processing-result" data-testid="velocity-browser-calculator">
    <header><p className="small-caps">{t("CLIENT-SIDE · NO UPLOAD","CÁLCULO EN CLIENTE · SIN CARGA")}</p><h2>{t("Calculate supplied first-arrival data","Calcular datos de primeras llegadas aportados")}</h2>
      <p>{t("Select a geophysics.velocity-user-data/v1 JSON request. Parsing and the weighted slowness solve run in this browser worker; the file is not sent to the VPS.","Seleccione una solicitud JSON geophysics.velocity-user-data/v1. El análisis y la inversión ponderada de lentitud se ejecutan en este navegador; el archivo no se envía al VPS.")}</p></header>
    <div className="processing-controls">
      <label className="select-control"><span>{t("First-arrival request JSON","Solicitud JSON de primeras llegadas")}</span><input type="file" accept=".json,application/json" disabled={busy||lambdaLoading} onChange={e=>void selectFile(e.target.files?.[0]??null)}/></label>
      <label className="select-control"><span>{t("Regularization weight λ","Peso de regularización λ")}</span><input className="select" aria-label={t("Regularization weight λ","Peso de regularización λ")} type="number" min="0.000001" max="1000000" step="any" value={lambda} disabled={busy||lambdaLoading} onChange={e=>setLambda(e.target.value)}/></label>
      <p className="plot-note">{t("λ is applied to the first-difference smoothness penalty. Larger values favor smoother models and can worsen data fit. The value from your request is loaded on file selection; you can change it before solving.","λ se aplica a la penalización de suavidad por primeras diferencias. Valores mayores favorecen modelos más suaves y pueden empeorar el ajuste. El valor de la solicitud se carga al elegir el archivo y puede cambiarse antes del cálculo.")}</p>
      <button className="btn" disabled={!file||busy||lambdaLoading} onClick={()=>void calculate()}>{busy?t("Calculating in browser…","Calculando en el navegador…"):t("Calculate locally in browser","Calcular localmente en el navegador")}</button>
      {error&&<p role="alert">{error}</p>}
      {busy&&<p role="status">{t("The browser is building ray-cell lengths and solving a 256-cell regularized system.","El navegador calcula longitudes rayo-celda y resuelve un sistema regularizado de 256 celdas.")}</p>}
    </div>
    {result&&q&&<section aria-label={t("Browser calculation result","Resultado del cálculo en navegador")}>
      <h3>{q.id} · {t("computed on this device","calculado en este dispositivo")}</h3>
      <p className="plot-note">{t("Source file SHA-256","SHA-256 del archivo fuente")}: <code className="processing-station-readout">{sha}</code> · {bytes} {t("bytes","bytes")}</p>
      <p className="plot-note">{t("Solved request SHA-256","SHA-256 de la solicitud calculada")}: <code className="processing-station-readout">{requestSha}</code> · {requestBytes} {t("bytes","bytes")} · {q.ray_ids.length} {t("rays","rayos")} · λ {q.lambda} · WRMS {result.metrics.data_wrms.toPrecision(5)} · {t("no field truth or validation claim","sin verdad ni validación de terreno")}</p>
      <label className="select-control"><span>{t("Scientific view","Vista científica")}</span><select className="select" value={view} onChange={e=>setView(e.target.value as View)}>
        {([["velocity",t("Estimated velocity [m/s]","Velocidad estimada [m/s]")],["coverage",t("Ray path coverage [m]","Cobertura de trayectos [m]")],["times",t("Observed and predicted times","Tiempos observados y predichos")],["residual",t("Signed residuals [s]","Residuales con signo [s]")],["standardized",t("Residual / declared sigma","Residual / sigma declarada")]] as [View,string][]).map(([v,label])=><option key={v} value={v}>{label}</option>)}
      </select></label>
      {(view==="velocity"||view==="coverage")&&<Heatmap data={view==="velocity"?result.velocity_m_s:result.coverage_m} title={view==="velocity"?t("Regularized velocity estimate; truth unknown","Estimación regularizada de velocidad; verdad desconocida"):t("Accumulated straight-ray path length; not uncertainty","Longitud acumulada de rayos rectos; no es incertidumbre")} unit={view==="velocity"?"m/s":"m"} palette="velocity" xLabel="x [m]" yLabel={t("depth z [m] · positive down","profundidad z [m] · positiva abajo")} xRange={[0,800]} yRange={[0,800]} xCoordinates={Array.from({length:16},(_,i)=>(i+.5)*50)} yCoordinates={Array.from({length:16},(_,i)=>(i+.5)*50)}/>}
      {(view==="times"||view==="residual"||view==="standardized")&&<><label className="select-control"><span>{t("Selected ray","Rayo seleccionado")}</span><select className="select" value={ray} onChange={e=>setRay(Number(e.target.value))}>{q.ray_ids.map((id,i)=><option key={id} value={i}>{id}</option>)}</select></label>
        <Plot x={q.ray_ids.map((_,i)=>i)} selectedIndex={ray} onSelect={setRay} pointLabels={q.ray_ids} title={view==="times"?t("Observed and predicted first arrivals","Primeras llegadas observadas y predichas"):view==="residual"?t("Observed minus predicted time","Tiempo observado menos predicho"):t("Residual divided by declared sigma","Residual dividido por sigma declarada")} xLabel={t("Original ray index","Índice original de rayo")} yLabel={view==="standardized"?"Δt/σ [1]":"time [s]"} zeroCentered={view!=="times"} series={view==="times"?[{name:t("Observed ± sigma","Observado ± sigma"),values:q.times_s,errors:q.sigma_s,points:true},{name:t("Cell prediction","Predicción por celdas"),values:result.predicted_s},{name:t("Bilinear quadrature check","Control de cuadratura bilineal"),values:result.bilinear_predicted_s,dashed:true}]:[{name:view==="residual"?"Δt [s]":"Δt/σ [1]",values:view==="residual"?result.residual_s:result.normalized_residual,points:true}]}/></>}
      <p className="plot-note">{t("Model clipping:","Celdas recortadas:")} {result.metrics.clipped_cells} · χ² {result.metrics.data_chi_square.toPrecision(5)} · {t("cell vs bilinear travel-time RMS [s]:","RMSE de tiempo celdas vs bilineal [s]:")} {result.metrics.cell_vs_bilinear_rmse_s.toPrecision(5)}. {t("Coverage is geometric support, not resolution. The straight-ray approximation does not model refraction, bent rays or wave propagation.","La cobertura es soporte geométrico, no resolución. La aproximación de rayos rectos no modela refracción, rayos curvos ni propagación ondulatoria.")}</p>
      <button className="btn" onClick={download}>{t("Export browser result JSON","Exportar resultado JSON del navegador")}</button>
    </section>}
  </article>;
}
