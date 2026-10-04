import { useEffect, useRef, useState } from "react";
import { color, extent, format } from "../science";
import type { ProfileModel } from "../api/profile-local-contracts";
import { Legend } from "./ScientificPlots";

/** Actual returned triangular cells, no centre-to-raster reconstruction. */
export function ProfileParameterMesh({model,sensors,row,cell,onCell,coverage,range,es}:{model:ProfileModel;sensors:number[][];row:number[];cell:number;onCell:(i:number)=>void;coverage:boolean;range?:[number,number];es:boolean}){
  const t=(en:string,sp:string)=>es?sp:en;
  const [zoom,setZoom]=useState(1),[pan,setPan]=useState(0);
  const svg=useRef<SVGSVGElement>(null),[w,setWidth]=useState(940);
  useEffect(()=>{const target=svg.current;if(!target)return;const update=()=>setWidth(Math.max(280,Math.round(target.getBoundingClientRect().width)));const observer=new ResizeObserver(update);observer.observe(target);update();return()=>observer.disconnect();},[]);
  const points=model.mesh?.nodes??model.centres, xr=extent([...points.map(p=>p[0]),...sensors.map(p=>p[0])]),yr=extent([...points.map(p=>p[1]),...sensors.map(p=>p[1])]);
  const width=Math.max(1e-9,xr[1]-xr[0]),height=Math.max(1e-9,yr[1]-yr[0]),scale=Math.min((w-110)/width,270/height),centre=(xr[0]+xr[1])/2;
  const X=(x:number)=>(w+52)/2+(x-centre-pan)*scale*zoom,Y=(z:number)=>32+(yr[1]-z)*scale*zoom;
  const values=coverage?model.coverage:model.values.map(Math.log10),bounds=coverage?extent(values):range&&range[0]>0&&range[1]>range[0]?[Math.log10(range[0]),Math.log10(range[1])] as [number,number]:extent(values);
  const palette=coverage?"field":"velocity",title=coverage?t("Returned coverage, not posterior uncertainty","Cobertura devuelta, no incertidumbre posterior"):t("Native parameter mesh","Malla nativa de parámetros");
  return <figure className="science-plot curve">
    <figcaption>{title}<output>{model.mesh?`${model.values.length} ${t("actual cells","celdas reales")}`:t("Centres only; topology unavailable","Solo centros; topología no disponible")}</output></figcaption>
    <div className="processing-view-controls"><button className="btn" onClick={()=>setZoom(Math.min(8,zoom*1.25))}>+</button><button className="btn" onClick={()=>setZoom(Math.max(1,zoom/1.25))}>−</button><button className="btn" onClick={()=>setPan(pan-width*.1/zoom)}>←</button><button className="btn" onClick={()=>setPan(pan+width*.1/zoom)}>→</button><button className="btn" onClick={()=>{setZoom(1);setPan(0);}}>{t("Reset view","Restablecer vista")}</button></div>
    <svg ref={svg} viewBox={`0 0 ${w} 360`} role="group" tabIndex={0} aria-label={title} onKeyDown={e=>{if(e.key==="ArrowRight"||e.key==="ArrowLeft"){e.preventDefault();onCell(Math.max(0,Math.min(model.values.length-1,cell+(e.key==="ArrowRight"?1:-1))));}}}>
      <defs><clipPath id="profile-mesh-clip"><rect x="72" y="20" width={w-92} height="300"/></clipPath></defs>
      <g clipPath="url(#profile-mesh-clip)">
        {model.mesh?model.mesh.cells.map((ids,i)=><polygon key={i} points={ids.map(id=>`${X(points[id][0])},${Y(points[id][1])}`).join(" ")} fill={color(values[i],bounds,palette)} stroke={i===cell?"var(--color-text)":"none"} strokeWidth={i===cell?2:0} onClick={()=>onCell(i)} data-cell-index={i} data-native-value={model.values[i]}><title>{i}: {model.values[i]} {model.unit}; {model.coverage[i]} {model.coverageUnit}</title></polygon>):model.centres.map((p,i)=><circle key={i} cx={X(p[0])} cy={Y(p[1])} r={i===cell?4:2} fill={color(values[i],bounds,palette)} onClick={()=>onCell(i)}/>)}
        <polyline points={sensors.map(p=>`${X(p[0])},${Y(p[1])}`).join(" ")} fill="none" stroke="var(--color-text)" strokeWidth="1.5"/>
        {row.map((id,i)=><g key={i}><circle cx={X(sensors[id][0])} cy={Y(sensors[id][1])} r="4" fill="var(--color-surface)" stroke="var(--color-text)" strokeWidth="2"/><text x={X(sensors[id][0])} y={Y(sensors[id][1])-8} textAnchor="middle" fill="var(--color-text)">{row.length===4?["A","B","M","N"][i]:["S","R"][i]}</text></g>)}
      </g>
      <text x="72" y="15" fill="var(--color-text)">{t("Elevation [m] · up","Elevación [m] · arriba")} {format(yr[0])} … {format(yr[1])}</text>
      <text x={(w+52)/2} y="348" textAnchor="middle" fill="var(--color-text)">{t("Distance [m]","Distancia [m]")} {format(xr[0])} … {format(xr[1])}</text>
    </svg>
    <Legend range={bounds} unit={coverage?model.coverageUnit:`log₁₀ ${model.unit}`} palette={palette}/>
    <p className="plot-note">{t("Equal physical scale on both axes. Cell boundaries are the returned discretization, not geological contacts or subcell resolution. Selected sensors show acquisition locations, not computed current lines or bent rays.","Escala física igual en ambos ejes. Los límites corresponden a la discretización devuelta, no a contactos geológicos ni resolución subcelda. Los sensores seleccionados indican la adquisición, no líneas de corriente ni rayos curvos calculados.")}</p>
  </figure>;
}
