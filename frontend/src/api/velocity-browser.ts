import { strictVelocityJson } from "./velocity-local-contracts";

const GRID = 16, DX = 50, EXTENT = GRID * DX, CELLS = GRID * GRID;
export type VelocityRequest = {
  schema: "geophysics.velocity-user-data/v1"; id: string;
  source: { citation: string; rights: "owner-permitted" | "CC0" | "CC-BY"; scope: "owner-provided" | "synthetic-control" };
  frame: "local-x-z-down"; units: { distance: "m"; time: "s"; velocity: "m/s" };
  ray_ids: string[]; rays_m: number[][]; times_s: number[]; sigma_s: number[]; lambda: number;
};
export type BrowserVelocityResult = {
  schema: "geophysics.velocity-browser-result/v1"; method: "fixed-straight-ray weighted slowness inversion";
  request: VelocityRequest; velocity_m_s: number[][]; predicted_s: number[]; residual_s: number[];
  normalized_residual: number[]; bilinear_predicted_s: number[]; coverage_m: number[][];
  metrics: { data_wrms: number; data_chi_square: number; cell_vs_bilinear_rmse_s: number; clipped_cells: number };
  execution: { location: "browser"; uploaded: false; field_truth_known: false; field_validated: false; heldout_advantage: false };
};

export function velocityRequestWithLambda(bytes: Uint8Array, lambda: number): Uint8Array {
  const request = parseVelocityRequest(bytes);
  const selected = finite(lambda, 1e-6, 1e6, true);
  return new TextEncoder().encode(JSON.stringify({ ...request, lambda: selected }));
}

const fail = (): never => { throw new Error("First-arrival request rejected: invalid schema, units, values or geometry"); };
const finite = (x: unknown, lo: number, hi: number, openLo = false): number => {
  if (typeof x !== "number" || !Number.isFinite(x) || (openLo ? x <= lo : x < lo) || x > hi) return fail();
  return x;
};

/** Strictly admit a user-supplied request before building any numerical arrays. */
export function parseVelocityRequest(bytes: Uint8Array): VelocityRequest {
  const d = strictVelocityJson(bytes, 400000, 512 * 1024, 12) as Record<string, unknown>;
  const exact = (v: unknown, keys: string[]) => {
    if (!v || typeof v !== "object" || Array.isArray(v) || Object.keys(v).length !== keys.length || !keys.every(k => Object.hasOwn(v, k))) return fail();
    return v as Record<string, unknown>;
  };
  const q = exact(d, ["schema", "id", "source", "frame", "units", "ray_ids", "rays_m", "times_s", "sigma_s", "lambda"]);
  if (q.schema !== "geophysics.velocity-user-data/v1" || typeof q.id !== "string" || !/^[A-Za-z0-9_-]{1,64}$/.test(q.id)) return fail();
  const source = exact(q.source, ["citation", "rights", "scope"]);
  if (typeof source.citation !== "string" || !source.citation.trim() || source.citation.length > 2048 ||
      !["owner-permitted", "CC0", "CC-BY"].includes(String(source.rights)) ||
      !["owner-provided", "synthetic-control"].includes(String(source.scope))) return fail();
  if (q.frame !== "local-x-z-down") return fail();
  const units = exact(q.units, ["distance", "time", "velocity"]);
  if (units.distance !== "m" || units.time !== "s" || units.velocity !== "m/s") return fail();
  if (!Array.isArray(q.ray_ids) || !Array.isArray(q.rays_m) || !Array.isArray(q.times_s) || !Array.isArray(q.sigma_s)) return fail();
  const n = q.ray_ids.length;
  if (n < 8 || n > 2048 || q.rays_m.length !== n || q.times_s.length !== n || q.sigma_s.length !== n) return fail();
  const ids = new Set<string>();
  q.ray_ids.forEach(id => { if (typeof id !== "string" || !/^[A-Za-z0-9_-]{1,64}$/.test(id) || ids.has(id)) return fail(); ids.add(id); });
  const rays = q.rays_m.map(ray => {
    if (!Array.isArray(ray) || ray.length !== 4) return fail();
    const [x0,z0,x1,z1] = ray.map(v => finite(v, 0, EXTENT));
    if (Math.hypot(x1-x0,z1-z0) < 0.001) return fail();
    return [x0,z0,x1,z1];
  });
  const times = q.times_s.map(v => finite(v, 0, 100, true));
  const sigma = q.sigma_s.map(v => finite(v, 0, 10, true));
  const lambda = finite(q.lambda, 1e-6, 1e6, true);
  return { schema: "geophysics.velocity-user-data/v1", id: q.id,
    source: { citation: source.citation, rights: source.rights as VelocityRequest["source"]["rights"], scope: source.scope as VelocityRequest["source"]["scope"] },
    frame: "local-x-z-down", units: { distance: "m", time: "s", velocity: "m/s" }, ray_ids: [...q.ray_ids], rays_m: rays, times_s: times, sigma_s: sigma, lambda };
}

function crossingRow(ray: number[]): { pairs: [number, number][]; length: number } {
  const [x0,z0,x1,z1] = ray, dx=x1-x0, dz=z1-z0, edges=Array.from({length:GRID-1},(_,i)=>(i+1)*DX), ts=[0,1];
  if (dx !== 0) for (const edge of edges) ts.push((edge-x0)/dx);
  if (dz !== 0) for (const edge of edges) ts.push((edge-z0)/dz);
  const sorted=[...new Set(ts.filter(t=>t>=0&&t<=1))].sort((a,b)=>a-b), length=Math.hypot(dx,dz), acc=new Map<number,number>();
  for (let k=0;k<sorted.length-1;k++) {
    const dt=sorted[k+1]-sorted[k], mid=(sorted[k+1]+sorted[k])/2;
    const x=Math.max(0,Math.min(GRID-1,Math.floor((x0+mid*dx)/DX))), z=Math.max(0,Math.min(GRID-1,Math.floor((z0+mid*dz)/DX))), cell=z*GRID+x;
    acc.set(cell,(acc.get(cell)??0)+dt*length);
  }
  return {pairs:[...acc.entries()],length};
}

function choleskySolve(matrix: Float64Array[], rhs: Float64Array): Float64Array {
  const n=rhs.length, l=Array.from({length:n},()=>new Float64Array(n));
  for(let i=0;i<n;i++) for(let j=0;j<=i;j++) {
    let s=matrix[i][j]; for(let k=0;k<j;k++) s-=l[i][k]*l[j][k];
    if(i===j) { if(!(s>0) || !Number.isFinite(s)) throw new Error("Numerical solve failed: positive-definite system check"); l[i][j]=Math.sqrt(s); }
    else l[i][j]=s/l[j][j];
  }
  const y=new Float64Array(n), x=new Float64Array(n);
  for(let i=0;i<n;i++){let s=rhs[i];for(let j=0;j<i;j++)s-=l[i][j]*y[j];y[i]=s/l[i][i];}
  for(let i=n-1;i>=0;i--){let s=y[i];for(let j=i+1;j<n;j++)s-=l[j][i]*x[j];x[i]=s/l[i][i];}
  return x;
}

function bilinearRow(ray: number[]): Float64Array {
  const [x0,z0,x1,z1]=ray, distance=Math.hypot(x1-x0,z1-z0), n=Math.ceil(distance/DX*8), row=new Float64Array(CELLS), step=distance/n;
  for(let i=0;i<n;i++){
    const f=(i+0.5)/n, gx=Math.max(0,Math.min(GRID-1,(x0+f*(x1-x0))/DX-0.5)), gz=Math.max(0,Math.min(GRID-1,(z0+f*(z1-z0))/DX-0.5));
    const ix=Math.floor(gx), iz=Math.floor(gz), jx=Math.min(ix+1,GRID-1), jz=Math.min(iz+1,GRID-1), ax=gx-ix, az=gz-iz;
    row[iz*GRID+ix]+=step*(1-ax)*(1-az); row[iz*GRID+jx]+=step*ax*(1-az); row[jz*GRID+ix]+=step*(1-ax)*az; row[jz*GRID+jx]+=step*ax*az;
  }
  return row;
}

/** Client-only port of the product's fixed straight-ray weighted slowness solve. */
export function calculateVelocityInBrowser(request: VelocityRequest): BrowserVelocityResult {
  const n=request.ray_ids.length, rows=request.rays_m.map(crossingRow), qrows=request.rays_m.map(bilinearRow);
  const reference=Float64Array.from({length:CELLS},(_,i)=>2000+0.35*((Math.floor(i/GRID)+0.5)*DX));
  const s0=Float64Array.from(reference,v=>1/v), normal=Array.from({length:CELLS},(_,i)=>{const r=new Float64Array(CELLS);r[i]=0.01;return r;}), rhs=new Float64Array(CELLS), coverage=new Float64Array(CELLS);
  for(let r=0;r<n;r++){
    const {pairs}=rows[r], weight=1/(1000*request.sigma_s[r]), predicted0=pairs.reduce((sum,[j,len])=>sum+len*s0[j],0), y=(request.times_s[r]-predicted0)/request.sigma_s[r];
    for(const [i,len] of pairs){ const bi=len*weight; rhs[i]+=bi*y; coverage[i]+=len; for(const [j,lenj] of pairs) normal[i][j]+=bi*lenj*weight; }
  }
  for(let z=0;z<GRID;z++)for(let x=0;x<GRID;x++){
    const i=z*GRID+x;
    for(const j of [...(x<GRID-1?[i+1]:[]),...(z<GRID-1?[i+GRID]:[])]){normal[i][i]+=request.lambda;normal[j][j]+=request.lambda;normal[i][j]-=request.lambda;normal[j][i]-=request.lambda;}
  }
  const q=choleskySolve(normal,rhs), velocity=Array.from({length:CELLS},(_,i)=>{const slowness=s0[i]+q[i]/1000, clipped=Math.max(1/4000,Math.min(1/1400,slowness));return 1/clipped;});
  let clippedCells=0; for(let i=0;i<CELLS;i++) if(s0[i]+q[i]/1000<1/4000||s0[i]+q[i]/1000>1/1400)clippedCells++;
  const predicted=rows.map(({pairs})=>pairs.reduce((sum,[j,len])=>sum+len/velocity[j],0));
  const alternate=qrows.map(row=>row.reduce((sum,len,j)=>sum+len/velocity[j],0));
  const residual=predicted.map((v,i)=>request.times_s[i]-v), normalized=residual.map((v,i)=>v/request.sigma_s[i]);
  const chi=normalized.reduce((s,v)=>s+v*v,0), diff=predicted.reduce((s,v,i)=>s+(v-alternate[i])**2,0);
  return {schema:"geophysics.velocity-browser-result/v1",method:"fixed-straight-ray weighted slowness inversion",request,
    velocity_m_s:Array.from({length:GRID},(_,z)=>velocity.slice(z*GRID,(z+1)*GRID)),predicted_s:predicted,residual_s:residual,normalized_residual:normalized,
    bilinear_predicted_s:alternate,coverage_m:Array.from({length:GRID},(_,z)=>Array.from(coverage.slice(z*GRID,(z+1)*GRID))),
    metrics:{data_wrms:Math.sqrt(chi/n),data_chi_square:chi,cell_vs_bilinear_rmse_s:Math.sqrt(diff/n),clipped_cells:clippedCells},
    execution:{location:"browser",uploaded:false,field_truth_known:false,field_validated:false,heldout_advantage:false}};
}

export function parseAndCalculateVelocity(bytes: Uint8Array) { const request=parseVelocityRequest(bytes); return calculateVelocityInBrowser(request); }
