import type { M03Crossover } from "../api/magnetic-flightline";

const quantileAbs=(values:number[],fraction:number)=>{const sorted=values.map(Math.abs).sort((a,b)=>a-b);return sorted[Math.min(sorted.length-1,Math.floor(fraction*(sorted.length-1)))];};

export function CrossoverHeightEvidence({crossings,es,valueUnit="nT"}:{crossings:M03Crossover[];es:boolean;valueUnit?:string}) {
  const rows=crossings;
  if(!rows.length)return null;
  const xLimit=Math.max(1,quantileAbs(rows.map(p=>p.sensor_height_difference_a_minus_b_m),.98));
  const yLimit=Math.max(1e-9,quantileAbs(rows.map(p=>p.difference_a_minus_b),.98));
  const outside=rows.filter(p=>Math.abs(p.sensor_height_difference_a_minus_b_m)>xLimit||Math.abs(p.difference_a_minus_b)>yLimit).length;
  const X=(v:number)=>88+(Math.max(-xLimit,Math.min(xLimit,v))/xLimit+1)*280;
  const Y=(v:number)=>143-Math.max(-yLimit,Math.min(yLimit,v))/yLimit*95;
  return <section className="project-note"><h2>{es?"Diferencia de cruce frente a diferencia de altura":"Crossover difference versus sensor-height difference"}</h2>
    <p>{es?`${rows.length} cruces interpolados. La ventana muestra el 98 % central por magnitud; ${outside} ${outside===1?"punto queda":"puntos quedan"} en el borde porque supera ese zoom. Los valores originales están en cada punto.`:`${rows.length} interpolated crossings. The view shows the central 98% by absolute magnitude; ${outside} ${outside===1?"point is":"points are"} placed at the edge because it exceeds this zoom. Original values are available on each point.`}</p>
    <svg viewBox="0 0 720 290" role="img" aria-label={es?"Diferencias magnéticas de cruces según diferencia de altura del sensor":"Magnetic crossover differences against sensor-height differences"} style={{width:"100%",maxHeight:360,background:"var(--color-surface-2)"}}>
      <line x1="88" x2="648" y1="143" y2="143" stroke="var(--color-fg-subtle)" strokeDasharray="4 4"/><line x1="368" x2="368" y1="40" y2="238" stroke="var(--color-fg-subtle)" strokeDasharray="4 4"/>
      <circle cx="478" cy="20" r="4" fill="var(--color-accent)"/><text x="488" y="24">{"ΔB < 0"}</text><circle cx="558" cy="20" r="4" fill="var(--color-fg)"/><text x="568" y="24">{"ΔB > 0"}</text>
      {rows.map((p,i)=>{const dx=p.sensor_height_difference_a_minus_b_m,dy=p.difference_a_minus_b,clipped=Math.abs(dx)>xLimit||Math.abs(dy)>yLimit;return <circle key={`${String(p.line_a)}-${String(p.line_b)}-${i}`} cx={X(dx)} cy={Y(dy)} r={clipped?3.4:2.3} fill={dy<0?"var(--color-accent)":"var(--color-fg)"} opacity={clipped?.9:.52}><title>{`${String(p.line_a)} × ${String(p.line_b)} · Δz ${dx.toFixed(2)} m · ΔB ${dy.toFixed(5)} ${valueUnit} · E ${Number(p.easting_m).toFixed(1)} m · N ${Number(p.northing_m).toFixed(1)} m`}</title></circle>;})}
      <text x="368" y="278" textAnchor="middle">{es?"Δ altura sensor A − B [m]":"Sensor-height difference A − B [m]"}</text>
      <text x="18" y="143" transform="rotate(-90 18 143)" textAnchor="middle">{es?`Diferencia magnética A − B [${valueUnit}]`:`Magnetic difference A − B [${valueUnit}]`}</text>
      <text x="88" y="257" textAnchor="middle">{(-xLimit).toPrecision(3)}</text><text x="648" y="257" textAnchor="middle">{xLimit.toPrecision(3)}</text>
      <text x="72" y="45" textAnchor="end">{yLimit.toPrecision(3)}</text><text x="72" y="238" textAnchor="end">{(-yLimit).toPrecision(3)}</text>
    </svg>
    <p>{es?"Las diferencias de campo en cruces mezclan geometría, altura, tiempo y otros efectos. Este gráfico es QC descriptivo; no estima ni aplica una corrección de nivelación.":"Crossover field differences mix geometry, sensor height, time and other effects. This is descriptive QC; it does not estimate or apply a levelling correction."}</p>
  </section>;
}
