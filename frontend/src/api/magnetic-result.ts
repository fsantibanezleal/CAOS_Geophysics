/** Immutable local-result projection. No browser fitting or online admission. */
export interface MagneticArray { dtype: "float64" | "int64" | "bool"; shape: number[]; data: number[] | boolean[]; sha256: string }
export interface MagneticBinding {
  job_id: string; dataset_id: string; source_id: string; generation_sha256: string;
  configuration_sha256: string; original_sha256: string;
}
export interface MagneticRow {
  row: number; row_id: string; group_id: string; xyz_m: number[]; usable: boolean;
  qc_reason: string | null; role: "development" | "outer";
  observed_nT: number[]; predicted_nT: number[] | null; residual_nT: number[] | null;
}
export interface MagneticHistory {
  candidate: string; fold: number; phase: string; outer_iteration: number; inner_iteration: number;
  beta: number; epsilon_q: number | null; phi_d: number; phi_regularizer: number;
  objective: number; kkt_inf: number; model_sha256: string; status: string;
}
export interface MagneticView {
  schema: "magnetic-owner-result-view-1"; binding: MagneticBinding; lane: "local_replay";
  online_admitted: false; claims: Record<string, false>; quantity: string; components: string[];
  coordinate_frame: Record<string, unknown>; original: Record<string, unknown>;
  rows: MagneticRow[]; mesh: { origin_m: MagneticArray; widths_x_m: MagneticArray; widths_y_m: MagneticArray; widths_z_m: MagneticArray; active: MagneticArray };
  model: { chi_si: MagneticArray; active_indices: MagneticArray; mesh_sha256: string; sha256: string };
  selected: string; candidates: unknown[]; metrics: Record<string, unknown>; history: MagneticHistory[];
  diagnostics: { resolution_kind: string; resolution_arrays: null | { selected_indices: MagneticArray; point_spread: MagneticArray; singular_values: MagneticArray | null }; reason: string | null };
  sensitivity: null; sensitivity_reason: string; resolution_interpretation: string;
}
const fail = (why: string): never => { throw new Error(`Magnetic result: ${why}`); };
const object = (x: unknown): Record<string, unknown> => x !== null && typeof x === "object" && !Array.isArray(x) ? x as Record<string, unknown> : fail("object");
const hash = (x: unknown) => typeof x === "string" && /^[0-9a-f]{64}$/.test(x);
const numbers = (x: unknown, count: number): x is number[] => Array.isArray(x) && x.length === count && x.every(n => typeof n === "number" && Number.isFinite(n));

/** Server must verify NPY hashes first. Here shapes, signs and selected-job binding are rechecked. */
export function parseMagneticView(value: unknown, expected: MagneticBinding): MagneticView {
  const v = object(value), binding = object(v.binding);
  const names = ["schema", "binding", "lane", "online_admitted", "claims", "quantity", "components", "coordinate_frame", "original", "rows", "mesh", "model", "selected", "candidates", "metrics", "history", "diagnostics", "sensitivity", "sensitivity_reason", "resolution_interpretation"];
  if (Object.keys(v).length !== names.length || names.some(k => !(k in v))) fail("closed fields");
  if (v.schema !== "magnetic-owner-result-view-1" || v.lane !== "local_replay" || v.online_admitted !== false || Object.values(object(v.claims)).some(x => x !== false)) fail("lane or claims");
  if (JSON.stringify(Object.keys(object(v.claims)).sort()) !== JSON.stringify(["field_source_verified","full_method_accepted","geology_truth_known","online_admitted"])) fail("complete closed claims");
  const frame=object(v.coordinate_frame),original=object(v.original);
  if (frame.axes!=="ENU" || frame.coordinate_unit!=="m" || frame.vertical_positive!=="up" || original.id!==expected.source_id || original.original_sha256!==expected.original_sha256 || original.scope!=="complete_acquisition") fail("original source/physical frame");
  if (Object.keys(binding).length !== 6 || Object.keys(expected).some(k => binding[k] !== expected[k as keyof MagneticBinding])) fail("selected job/source/configuration");
  for (const k of ["generation_sha256", "configuration_sha256", "original_sha256"]) if (!hash(binding[k])) fail("binding hash");
  for (const k of ["job_id", "dataset_id"]) if (typeof binding[k] !== "string" || !/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(binding[k])) fail("owner id");
  const quantities = ["secondary_enu_nT", "linear_tmi_nT", "exact_total_anomaly_nT"];
  if (!quantities.includes(String(v.quantity))) fail("quantity");
  const c = v.quantity === "secondary_enu_nT" ? 3 : 1;
  if (JSON.stringify(v.components) !== JSON.stringify(c === 3 ? ["E", "N", "U"] : ["scalar"])) fail("components");
  if (!Array.isArray(v.rows) || v.rows.length < 1 || v.rows.length > 2048) fail("complete original rows");
  const ids = new Set<string>();
  (v.rows as unknown[]).forEach((raw, i) => {
    const r = object(raw);
    if (r.row !== i || typeof r.row_id !== "string" || ids.has(r.row_id) || typeof r.group_id !== "string" || !numbers(r.xyz_m, 3) || !numbers(r.observed_nT, c) || typeof r.usable !== "boolean" || !["development", "outer"].includes(String(r.role))) fail("original row identity/geometry");
    ids.add(r.row_id as string);
    if (r.predicted_nT === null || r.residual_nT === null) {
      if (r.usable || r.predicted_nT !== null || r.residual_nT !== null) fail("absent prediction");
    } else {
      if (!numbers(r.predicted_nT, c) || !numbers(r.residual_nT, c)) fail("prediction shape");
      const o = r.observed_nT as number[], p = r.predicted_nT as number[], res = r.residual_nT as number[];
      if (res.some((n, j) => n !== o[j]-p[j])) fail("signed native residual");
    }
  });
  const array = (raw: unknown, dtype: string, maximum: number) => {
    const a = object(raw), shape = a.shape;
    if (Object.keys(a).length !== 4 || a.dtype !== dtype || !hash(a.sha256) || !Array.isArray(shape) || !shape.length || shape.some(n => !Number.isSafeInteger(n) || n < 0)) fail("numeric descriptor");
    const count = (shape as number[]).reduce((a, b) => a*b, 1);
    if (count > maximum || !Array.isArray(a.data) || a.data.length !== count || a.data.some(n => dtype === "bool" ? typeof n !== "boolean" : typeof n !== "number" || !Number.isFinite(n) || (dtype === "int64" && !Number.isSafeInteger(n)))) fail("numeric count/type");
    return a as unknown as MagneticArray;
  };
  const model = object(v.model), mesh = object(v.mesh);
  const chi = array(model.chi_si, "float64", 8192), active = array(model.active_indices, "int64", 8192);
  if (chi.data.length !== active.data.length || chi.data.some(x => Number(x) < 0 || Number(x) > .1)) fail("physical SI bounds");
  const origin = array(mesh.origin_m, "float64", 3); if (origin.data.length !== 3) fail("origin");
  const widths = ["widths_x_m", "widths_y_m", "widths_z_m"].map(k => array(mesh[k], "float64", 8192));
  if (widths.some(a => !a.data.length || a.data.some(x => Number(x) <= 0))) fail("positive widths");
  const mask = array(mesh.active, "bool", 8192);
  if (mask.data.length !== widths.reduce((a, b) => a*b.data.length, 1) || JSON.stringify(active.data) !== JSON.stringify(mask.data.flatMap((x,i)=>x?[i]:[]))) fail("active mapping");
  if (!Array.isArray(v.history) || v.history.length > 4096 || !Array.isArray(v.candidates) || v.candidates.length !== 16) fail("frozen candidate/history bounds");
  for (const raw of v.history as unknown[]) { const h = object(raw); for (const k of ["beta", "phi_d", "phi_regularizer", "objective", "kkt_inf"]) if (typeof h[k] !== "number" || !Number.isFinite(h[k])) fail("actual history"); }
  if (v.sensitivity !== null || typeof v.sensitivity_reason !== "string" || typeof v.resolution_interpretation !== "string") fail("unmeasured sensitivity");
  const diagnostics = object(v.diagnostics);
  if (diagnostics.resolution_arrays !== null) {
    const d = object(diagnostics.resolution_arrays), selected = array(d.selected_indices, "int64", 8), psf = array(d.point_spread, "float64", 8192*8);
    if (JSON.stringify(psf.shape) !== JSON.stringify([chi.data.length, selected.data.length]) || selected.data.some(i => Number(i) < 0 || Number(i) >= chi.data.length)) fail("point spread mapping");
    if (d.singular_values !== null) array(d.singular_values, "float64", 8192);
  }
  return value as MagneticView;
}

export function magneticCells(view: MagneticView) {
  const mesh = view.mesh, widths = [mesh.widths_x_m, mesh.widths_y_m, mesh.widths_z_m].map(a => a.data as number[]);
  const centers = widths.map((w, axis) => { let edge = Number(mesh.origin_m.data[axis]); return w.map(h => { const c=edge+h/2; edge+=h; return c; }); });
  return (view.model.active_indices.data as number[]).map((index, k) => {
    const x = index%widths[0].length, y = Math.floor(index/widths[0].length)%widths[1].length, z = Math.floor(index/(widths[0].length*widths[1].length));
    return { index, k, xyz_m: [centers[0][x], centers[1][y], centers[2][z]], widths_m:[widths[0][x],widths[1][y],widths[2][z]], chi_si: Number(view.model.chi_si.data[k]), volume_m3: widths[0][x]*widths[1][y]*widths[2][z], layer: z };
  });
}

/** Recheck every little-endian native descriptor against its exported SHA256. */
export async function verifyMagneticView(value: unknown, expected: MagneticBinding) {
  const parsed=parseMagneticView(value,expected), pending: unknown[]=[value]; let visited=0,total=0;
  while (pending.length) {
    const raw=pending.pop(); if (++visited>500000) fail("projection traversal cap");
    if (raw===null || typeof raw!=="object") continue;
    if (Array.isArray(raw)) { pending.push(...raw); continue; }
    const a=raw as Record<string,unknown>;
    if ("dtype" in a && "shape" in a && "data" in a && "sha256" in a) {
      if (!["float64","int64","bool"].includes(String(a.dtype)) || !Array.isArray(a.data) || !Array.isArray(a.shape) || !hash(a.sha256)) fail("descriptor hash inputs");
      const shape=a.shape as unknown[], data=a.data as unknown[];
      const itemBytes=a.dtype==="bool"?1:8, count=shape.reduce<number>((n,x)=>n*Number(x),1);
      if (count!==data.length || !Number.isSafeInteger(count) || count<0 || (total+=count*itemBytes)>128*1024**2) fail("native descriptor byte cap");
      const bytes=new Uint8Array(count*itemBytes), native=new DataView(bytes.buffer);
      data.forEach((x,i)=>{
        if (a.dtype==="bool") { if (typeof x!=="boolean") fail("bool"); native.setUint8(i,x?1:0); }
        else { if (typeof x!=="number" || !Number.isFinite(x)) fail("native number"); if (a.dtype==="int64") { if (!Number.isSafeInteger(x)) fail("int64"); native.setBigInt64(i*8,BigInt(x as number),true); } else native.setFloat64(i*8,x as number,true); }
      });
      const actual=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),n=>n.toString(16).padStart(2,"0")).join("");
      if (actual!==a.sha256) fail("native descriptor SHA256 mismatch");
    } else pending.push(...Object.values(a));
  }
  return parsed;
}

export function magneticSpectrum(rows: MagneticRow[], component: number) {
  if (rows.length < 3 || rows.length > 2048 || rows.some(r=>r.residual_nT===null)) return null;
  const dx=rows[1].xyz_m[0]-rows[0].xyz_m[0], dy=rows[1].xyz_m[1]-rows[0].xyz_m[1], step=Math.hypot(dx,dy);
  if (!(step>0) || rows.slice(1).some((r,i)=>Math.abs((r.xyz_m[0]-rows[i].xyz_m[0])-dx)>1e-12*Math.max(1,Math.abs(dx)) || Math.abs((r.xyz_m[1]-rows[i].xyz_m[1])-dy)>1e-12*Math.max(1,Math.abs(dy)))) return null;
  const n=rows.length, mean=rows.reduce((a,r)=>a+r.residual_nT![component],0)/n, w=rows.map((_,i)=>.5-.5*Math.cos(2*Math.PI*i/(n-1))), scale=w.reduce((a,b)=>a+b*b,0)/step;
  return Array.from({length:Math.floor(n/2)+1},(_,k)=>{
    let re=0,im=0; rows.forEach((r,i)=>{ const v=(r.residual_nT![component]-mean)*w[i], a=2*Math.PI*k*i/n; re+=v*Math.cos(a); im-=v*Math.sin(a); });
    return { frequency_cycles_per_m:k/(n*step), power_nT2_m:(re*re+im*im)/scale*(k>0 && !(n%2===0 && k===n/2)?2:1) };
  });
}
