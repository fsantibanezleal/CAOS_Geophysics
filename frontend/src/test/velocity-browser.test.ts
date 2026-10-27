import { describe, expect, it } from "vitest";
import { parseAndCalculateVelocity } from "../api/velocity-browser";

function request() {
  const f=(i:number)=>i/7;
  const left=Array.from({length:8},(_,i)=>[0,(.08+.84*f(i))*800] as const);
  const right=Array.from({length:8},(_,i)=>[800,(.1+.8*f(i))*800] as const);
  const top=Array.from({length:8},(_,i)=>[(.08+.84*f(i))*800,0] as const);
  const bottom=Array.from({length:8},(_,i)=>[(.1+.8*f(i))*800,800] as const);
  const rays=[...left.flatMap(([x,z])=>right.map(([xr,zr])=>[x,z,xr,zr])),...top.flatMap(([x,z])=>bottom.map(([xr,zr])=>[x,z,xr,zr]))];
  const times=rays.map(([x0,z0,x1,z1],i)=>{
    const dx=x1-x0,dz=z1-z0,ts=[0,1];
    for(let k=1;k<16;k++){const edge=k*50;if(dx!==0)ts.push((edge-x0)/dx);if(dz!==0)ts.push((edge-z0)/dz);}
    const sorted=[...new Set(ts.filter(t=>t>=0&&t<=1))].sort((a,b)=>a-b),length=Math.hypot(dx,dz);let time=0;
    for(let k=0;k<sorted.length-1;k++){const mid=(sorted[k]+sorted[k+1])/2,iz=Math.max(0,Math.min(15,Math.floor((z0+mid*dz)/50)));time+=(sorted[k+1]-sorted[k])*length/(2000+.35*((iz+.5)*50));}
    return time+.0004*Math.sin(i*1.7);
  });
  return {schema:"geophysics.velocity-user-data/v1",id:"parity-control",source:{citation:"Authored parity control",rights:"owner-permitted",scope:"synthetic-control"},frame:"local-x-z-down",units:{distance:"m",time:"s",velocity:"m/s"},ray_ids:rays.map((_,i)=>`ray-${String(i).padStart(3,"0")}`),rays_m:rays,times_s:times,sigma_s:rays.map(()=>.001),lambda:100};
}

describe("client-side first-arrival inversion",()=>{
  it("matches the pinned Python product solver on a 128-ray physical control",()=>{
    const bytes=new TextEncoder().encode(JSON.stringify(request())),r=parseAndCalculateVelocity(bytes);
    expect(r.execution).toEqual({location:"browser",uploaded:false,field_truth_known:false,field_validated:false,heldout_advantage:false});
    expect(r.metrics.data_wrms).toBeCloseTo(.022635248821506103,7);
    expect(r.metrics.data_chi_square).toBeCloseTo(.06558137461907115,7);
    expect(r.metrics.cell_vs_bilinear_rmse_s).toBeCloseTo(.00022863825058567995,7);
    expect(r.velocity_m_s[0][0]).toBeCloseTo(2009.7666832065106,4);
    expect(r.velocity_m_s[5][7]).toBeCloseTo(2097.9578158758945,4);
    expect(r.velocity_m_s[15][15]).toBeCloseTo(2267.8933196540747,4);
    expect(r.predicted_s[0]).toBeCloseTo(.3948998396460718,7);
    expect(r.coverage_m[0][0]).toBe(0);
  });
  it("rejects malformed, duplicate-key and over-bound input before solving",()=>{
    expect(()=>parseAndCalculateVelocity(new TextEncoder().encode('{"schema":"x","schema":"y"}'))).toThrow();
    const q=request();q.rays_m[0][0]=-1;
    expect(()=>parseAndCalculateVelocity(new TextEncoder().encode(JSON.stringify(q)))).toThrow();
    const short=request();short.rays_m=short.rays_m.slice(0,7);short.ray_ids=short.ray_ids.slice(0,7);short.times_s=short.times_s.slice(0,7);short.sigma_s=short.sigma_s.slice(0,7);
    expect(()=>parseAndCalculateVelocity(new TextEncoder().encode(JSON.stringify(short)))).toThrow();
  });
});
