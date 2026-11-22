import { describe, expect, it } from "vitest";
import { calculateM12PhysicsInBrowser, parseAndCalculateVelocity, parseVelocityRequest,
  velocityPhysicsFeatures, velocityRequestWithLambda, type VelocityRequest } from "../api/velocity-browser";

function request(): VelocityRequest {
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
  it("changes the actual recovered model when the user changes regularization",()=>{
    const source=new TextEncoder().encode(JSON.stringify(request()));
    const baseline=parseAndCalculateVelocity(source),selectedBytes=velocityRequestWithLambda(source,1000),selectedRequest=parseVelocityRequest(selectedBytes);
    const selected=parseAndCalculateVelocity(selectedBytes);
    expect(selectedRequest.lambda).toBe(1000);
    expect(selected.request.lambda).toBe(1000);
    expect(selected.velocity_m_s).not.toEqual(baseline.velocity_m_s);
    expect(selected.predicted_s).not.toEqual(baseline.predicted_s);
    expect(()=>velocityRequestWithLambda(source,0)).toThrow();
    expect(()=>velocityRequestWithLambda(source,1_000_001)).toThrow();
  });
  it("keeps active velocity bounds in the solved objective and reports projected KKT",()=>{
    const q=request();q.times_s=q.times_s.map((v,i)=>v+.1*(2*i/(q.times_s.length-1)-1));
    const result=parseAndCalculateVelocity(new TextEncoder().encode(JSON.stringify(q)));
    expect(result.metrics.active_bound_cells).toBeGreaterThan(0);
    expect(result.metrics.kkt_relative).toBeLessThanOrEqual(result.metrics.kkt_relative_tolerance);
    expect(result.metrics.kkt_relative_tolerance).toBe(1e-9);
    expect(result.solver).toBe("Deterministic primal active-set box-QP with projected KKT gate");
    expect(result.velocity_m_s.flat().every(v=>v>=1400&&v<=4000)).toBe(true);
    expect(result.metrics.active_bound_cells).toBe(127);
    expect(result.metrics.solver_iterations).toBe(134);
    expect(result.metrics.data_wrms).toBeCloseTo(17.276330634904177,7);
    expect(result.velocity_m_s[0][0]).toBeCloseTo(2064.8644568639766,3);
    expect(result.velocity_m_s[5][7]).toBeCloseTo(2286.153461042268,3);
    expect(result.velocity_m_s[15][15]).toBeCloseTo(2081.4622948206534,3);
  });
  it("reproduces the Python physics-v2 feature operator and keeps support separate",()=>{
    const q=request(),{tensor,coverage}=velocityPhysicsFeatures(q);
    expect(tensor).toHaveLength(512);
    // Channel 0 is the geometry-normalized residual; channel 1 begins at 256.
    expect(tensor[1]).toBeCloseTo(-0.00031037768349051476,9);
    expect(tensor[16]).toBeCloseTo(0.00008211217209463939,9);
    expect(tensor[127]).toBeCloseTo(0.00046271205064840615,9);
    expect(tensor[128]).toBeCloseTo(0.0009559880127198994,9);
    expect(tensor[256 + 127]).toBeCloseTo(0.3301851451396942,7);
    expect(coverage[0][0]).toBe(0);
    expect(coverage.some(row => row.some(value => value > 0))).toBe(true);
  });
  it("independently forwards an exploratory model and masks unsupported cells",async()=>{
    const q=request(),velocity=new Float32Array(256).fill(2000);
    const learned=await calculateM12PhysicsInBrowser(q,async features=>{
      expect(features).toHaveLength(512); return velocity;
    },{checkpointSha256:"a".repeat(64),onnxSha256:"b".repeat(64)});
    expect(learned.status).toBe("exploratory-unvalidated");
    expect(learned.velocity_m_s).toHaveLength(16);
    expect(learned.supported_cells[0][0]).toBe(false);
    expect(learned.metrics.unsupported_cells).toBeGreaterThan(0);
    expect(learned.predicted_s).toHaveLength(q.rays_m.length);
    expect(learned.residual_s[0]).toBeCloseTo(q.times_s[0]-learned.predicted_s[0],12);
    await expect(calculateM12PhysicsInBrowser(q,async()=>new Float32Array(256).fill(4001),
      {checkpointSha256:"a".repeat(64),onnxSha256:"b".repeat(64)})).rejects.toThrow("invalid velocity grid");
  });
});
