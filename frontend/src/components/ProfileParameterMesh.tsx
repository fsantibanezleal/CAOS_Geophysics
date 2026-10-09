import { useRef, useState } from "react";
import { color, extent, format } from "../science";
import type { ProfileModel } from "../api/profile-local-contracts";
import { Legend } from "./ScientificPlots";
import { PlotCard, Stage, type Provenance } from "@fasl-work/caos-app-shell";

/** Actual returned triangular cells, no centre-to-raster reconstruction. */
export function ProfileParameterMesh({model,sensors,row,cell,onCell,coverage,range,es,provenance}:{model:ProfileModel;sensors:number[][];row:number[];cell:number;onCell:(i:number)=>void;coverage:boolean;range?:[number,number];es:boolean;provenance:Provenance}){
  const t=(en:string,sp:string)=>es?sp:en;
  const [zoom,setZoom]=useState(1),[pan,setPan]=useState(0);
  const svg=useRef<SVGSVGElement>(null);
  const points=model.mesh?.nodes??model.centres, xr=extent([...points.map(p=>p[0]),...sensors.map(p=>p[0])]),yr=extent([...points.map(p=>p[1]),...sensors.map(p=>p[1])]);
  const width=Math.max(1e-9,xr[1]-xr[0]),height=Math.max(1e-9,yr[1]-yr[0]),centre=(xr[0]+xr[1])/2;
  const values=coverage?model.coverage:model.values.map(Math.log10),bounds=coverage?extent(values):range&&range[0]>0&&range[1]>range[0]?[Math.log10(range[0]),Math.log10(range[1])] as [number,number]:extent(values);
  const palette=coverage?"field":"velocity",title=coverage?t("Returned coverage, not posterior uncertainty","Cobertura devuelta, no incertidumbre posterior"):t("Native parameter mesh","Malla nativa de parámetros");
  return <>
    <PlotCard title={title} lane="replay" provenance={provenance} fill note={t("Equal physical scale on both axes. Cell boundaries are the returned discretization, not geological contacts or subcell resolution. Selected sensors show acquisition locations, not computed current lines or bent rays.","Escala física igual en ambos ejes. Los límites corresponden a la discretización devuelta, no a contactos geológicos ni resolución subcelda. Los sensores seleccionados indican la adquisición, no líneas de corriente ni rayos curvos calculados.")} actions={<details><summary>{t("Mesh view","Vista de malla")}</summary>
    <div className="processing-view-controls"><button className="btn" onClick={()=>setZoom(Math.min(8,zoom*1.25))}>+</button><button className="btn" onClick={()=>setZoom(Math.max(1,zoom/1.25))}>−</button><button className="btn" onClick={()=>setPan(pan-width*.1/zoom)}>←</button><button className="btn" onClick={()=>setPan(pan+width*.1/zoom)}>→</button><button className="btn" onClick={()=>{setZoom(1);setPan(0);}}>{t("Reset view","Restablecer vista")}</button></div></details>}>
    <Stage label={title}>{({width:w,height:h})=>{
      const scale=Math.min(Math.max(1,w-110)/width,Math.max(1,h-90)/height),bottom=36+height*scale;
      const X=(x:number)=>(w+52)/2+(x-centre-pan)*scale*zoom,Y=(z:number)=>36+(yr[1]-z)*scale*zoom;
      return <svg ref={svg} width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="group" tabIndex={0} aria-label={title} data-native-mesh="true" onKeyDown={e=>{if(e.key==="ArrowRight"||e.key==="ArrowLeft"){e.preventDefault();onCell(Math.max(0,Math.min(model.values.length-1,cell+(e.key==="ArrowRight"?1:-1))));}}}>
      <defs><clipPath id="profile-mesh-clip"><rect x="72" y="20" width={w-92} height={bottom-20}/></clipPath></defs>
      <g clipPath="url(#profile-mesh-clip)">
        {model.mesh?model.mesh.cells.map((ids,i)=><polygon key={i} points={ids.map(id=>`${X(points[id][0])},${Y(points[id][1])}`).join(" ")} fill={color(values[i],bounds,palette)} stroke={i===cell?"var(--color-fg)":"none"} strokeWidth={i===cell?2:0} onClick={()=>onCell(i)} data-cell-index={i} data-native-value={model.values[i]}><title>{i}: {model.values[i]} {model.unit}; {model.coverage[i]} {model.coverageUnit}</title></polygon>):model.centres.map((p,i)=><circle key={i} cx={X(p[0])} cy={Y(p[1])} r={i===cell?4:2} fill={color(values[i],bounds,palette)} onClick={()=>onCell(i)}/>)}
        <polyline pointerEvents="none" points={sensors.map(p=>`${X(p[0])},${Y(p[1])}`).join(" ")} fill="none" stroke="var(--color-fg)" strokeWidth="1.5"/>
        {row.map((id,i)=><g key={i} pointerEvents="none"><circle cx={X(sensors[id][0])} cy={Y(sensors[id][1])} r="4" fill="var(--color-surface)" stroke="var(--color-fg)" strokeWidth="2"/><text x={X(sensors[id][0])} y={Y(sensors[id][1])-8} textAnchor="middle" fill="var(--color-fg)">{row.length===4?["A","B","M","N"][i]:["S","R"][i]}</text></g>)}
      </g>
      {Array.from({length:4},(_,i)=>{const x=centre+pan-width/(2*zoom)+i*width/(3*zoom),z=yr[1]-i*height/(3*zoom);return <g key={i}><text x={X(x)} y={bottom+20} textAnchor="middle" fill="var(--color-fg)">{format(x)}</text><text x="64" y={Y(z)+4} textAnchor="end" fill="var(--color-fg)">{format(z)}</text></g>;})}
      <text x="16" y="15" fill="var(--color-fg)">{t("Elevation [m] · up","Elevación [m] · arriba")}</text>
      <text x={(w+52)/2} y={Math.min(h-10,bottom+60)} textAnchor="middle" fill="var(--color-fg)">{t("Distance [m]","Distancia [m]")}</text>
    </svg>;
    }}</Stage>
    </PlotCard>
    <Legend range={bounds} unit={coverage?model.coverageUnit:`log₁₀ ${model.unit}`} palette={palette}/>
  </>;
}
