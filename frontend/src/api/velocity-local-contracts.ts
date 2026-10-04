/** Local scalar/byte admission only. No ray-operator or inverse execution. */
export type VelocityModel = "classical" | "learned";
type Model = { velocity_m_s: number[][]; predicted_s: number[]; residual_s: number[]; normalized_residual: number[];
  bilinear_predicted_s: number[]; cell_vs_bilinear_rmse_s: number; data_chi_square: number; data_wrms: number;
  clipped_cells?: number; regularizer?: number; solver?: string; bound_constrained_optimum_certified?: false };
export interface VelocityResult {
  schema: "geophysics.velocity-result/v1"; status: "computed";
  request: { schema: "geophysics.velocity-user-data/v1"; id: string; source: { citation: string; rights: string; scope: string };
    frame: "local-x-z-down"; units: { distance: "m"; time: "s"; velocity: "m/s" }; ray_ids: string[]; rays_m: number[][]; times_s: number[]; sigma_s: number[]; lambda: number };
  source: { sha256: string; bytes: number }; axes: { x_m: number[]; depth_m: number[]; order: ["depth", "distance"] }; coverage_m: number[][];
  results: { classical: Model; learned?: Model }; learned_domain: { training_geometry: boolean; training_noise: boolean; field_validated: false; heldout_advantage: false } | null;
  warnings: string[]; engine: { numpy: string; scipy: string; user_tool_sha256: string; velocity_operator_sha256: string;
    checkpoint_sha256: string | null; checkpoint_protocol: "original" | "physics-v2" | null; refinement_code_sha256: string | null };
  claims: { field_truth_known: false; field_validated: false; heldout_advantage: false; online_admitted: false };
}
export type VelocityAdmission = { result: VelocityResult; resultSha256: string; manifestSha256: string; resultBytes: number; physicsReplayed: false };
const require: (ok: unknown) => asserts ok = ok => { if (!ok) throw new Error("Local velocity files rejected: invalid or inconsistent contract"); };
const record = (v: unknown): Record<string, unknown> => { require(v !== null && typeof v === "object" && !Array.isArray(v)); return v as Record<string, unknown>; };
function closed(v: unknown, keys: string[]) { const r = record(v); require(Object.keys(r).length === keys.length && keys.every(k => Object.hasOwn(r, k))); return r; }
function num(v: unknown, lo = -Infinity, hi = Infinity): number { require(typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi); return v; }
function text(v: unknown, max: number): string { require(typeof v === "string" && v.trim().length > 0 && v.length <= max); return v; }
function hash(v: unknown) { require(typeof v === "string" && /^[a-f0-9]{64}$/.test(v)); }
function int(v: unknown, lo: number, hi: number) { num(v, lo, hi); require(Number.isInteger(v)); }
function vector(v: unknown, n: number, lo = -Infinity, hi = Infinity): number[] { require(Array.isArray(v) && v.length === n); v.forEach(x => num(x, lo, hi)); return v; }
function matrix(v: unknown, lo: number, hi = Infinity): number[][] { require(Array.isArray(v) && v.length === 16); return v.map(row => vector(row, 16, lo, hi)); }
function near(a: unknown, b: number, numpy = false) { const v = num(a); require(Math.abs(v - b) <= (numpy ? 1e-12 + 1e-12 * Math.abs(b) : Math.max(1e-12, 1e-12 * Math.max(Math.abs(v), Math.abs(b))))); }
function falseKeys(v: unknown, keys: string[]) { const r = closed(v, keys); keys.forEach(k => require(r[k] === false)); }
const sourceKeys = ["sha256", "bytes"];
function source(v: unknown) { const r = closed(v, sourceKeys); hash(r.sha256); int(r.bytes, 1, 512 * 1024); }
const engineKeys = ["numpy", "scipy", "user_tool_sha256", "velocity_operator_sha256", "checkpoint_sha256", "checkpoint_protocol", "refinement_code_sha256"];

/** Linear bounded lexical preflight. Decoded object-key duplicates are rejected. */
export function strictVelocityJson(bytes: Uint8Array, maxNodes = 160000): unknown {
  require(bytes.byteLength > 0 && bytes.byteLength <= 4 * 1048576);
  const s = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
  const stack: { object: boolean; keys: Set<string>; key: boolean }[] = [];
  let nodes = 0, atom = false;
  const charge = () => require(++nodes <= maxNodes);
  for (let i = 0; i < s.length; i++) {
    const c = s[i], top = stack.at(-1);
    if (c === '"') {
      charge(); const start = i; let escaped = false, ended = false;
      for (++i; i < s.length; i++) {
        if (escaped) escaped = false;
        else if (s[i] === "\\") escaped = true;
        else if (s[i] === '"') { ended = true; break; }
      }
      require(ended);
      if (top?.object && top.key) { const key = JSON.parse(s.slice(start, i + 1)); require(!top.keys.has(key)); top.keys.add(key); top.key = false; }
      atom = false;
    } else if (c === "{" || c === "[") {
      charge(); stack.push({ object: c === "{", keys: new Set(), key: c === "{" }); require(stack.length <= 12); atom = false;
    } else if (c === "}" || c === "]") { require(stack.length > 0); stack.pop(); atom = false; }
    else if (c === ",") { if (top?.object) top.key = true; atom = false; }
    else if (/[\s:]/.test(c)) atom = false;
    else if (!atom) { charge(); atom = true; }
  }
  require(stack.length === 0); return JSON.parse(s);
}

export function parseVelocityResult(value: unknown): VelocityResult {
  const d = closed(value, ["schema", "status", "request", "source", "axes", "coverage_m", "results", "learned_domain", "warnings", "engine", "claims"]);
  require(d.schema === "geophysics.velocity-result/v1" && d.status === "computed");
  const q = closed(d.request, ["schema", "id", "source", "frame", "units", "ray_ids", "rays_m", "times_s", "sigma_s", "lambda"]);
  require(q.schema === "geophysics.velocity-user-data/v1" && /^[A-Za-z0-9_-]{1,64}$/.test(text(q.id, 64)) && q.frame === "local-x-z-down");
  const rights = closed(q.source, ["citation", "rights", "scope"]); text(rights.citation, 2048);
  require(["owner-permitted", "CC0", "CC-BY"].includes(String(rights.rights)) && ["owner-provided", "synthetic-control"].includes(String(rights.scope)));
  const units = closed(q.units, ["distance", "time", "velocity"]); require(units.distance === "m" && units.time === "s" && units.velocity === "m/s");
  require(Array.isArray(q.ray_ids)); const n = q.ray_ids.length; int(n, 8, 2048);
  require(q.ray_ids.every(id => typeof id === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(id)) && new Set(q.ray_ids).size === n);
  require(Array.isArray(q.rays_m) && q.rays_m.length === n);
  q.rays_m.forEach(v => { const r = vector(v, 4, 0, 800); require(Math.hypot(r[2] - r[0], r[3] - r[1]) >= .001); });
  const times = vector(q.times_s, n, 0, 100), sigma = vector(q.sigma_s, n, 0, 10); require(times.every(v => v > 0) && sigma.every(v => v > 0)); num(q.lambda, 1e-6, 1e6);
  source(d.source);
  const axes = closed(d.axes, ["x_m", "depth_m", "order"]);
  for (const k of ["x_m", "depth_m"]) require(vector(axes[k], 16).every((v, i) => v === 25 + 50 * i));
  require(Array.isArray(axes.order) && axes.order.length === 2 && axes.order[0] === "depth" && axes.order[1] === "distance"); matrix(d.coverage_m, 0);
  const models = record(d.results), learned = Object.hasOwn(models, "learned");
  closed(models, ["classical", ...(learned ? ["learned"] : [])]);
  const base = ["velocity_m_s", "predicted_s", "residual_s", "normalized_residual", "bilinear_predicted_s", "cell_vs_bilinear_rmse_s", "data_chi_square", "data_wrms"];
  for (const name of Object.keys(models)) {
    const m = closed(models[name], [...base, ...(name === "classical" ? ["clipped_cells", "regularizer", "solver", "bound_constrained_optimum_certified"] : [])]);
    const v = matrix(m.velocity_m_s, name === "classical" ? 1400 : 0, name === "classical" ? 4000 : Infinity); require(v.flat().every(x => x > 0));
    const predicted = vector(m.predicted_s, n, 0), residual = vector(m.residual_s, n), normalized = vector(m.normalized_residual, n), alternate = vector(m.bilinear_predicted_s, n, 0);
    require(predicted.every(v => v > 0) && alternate.every(v => v > 0));
    let chi = 0, difference = 0;
    for (let i = 0; i < n; i++) { const r = times[i] - predicted[i], z = r / sigma[i]; near(residual[i], r, true); near(normalized[i], z, true); chi += z * z; difference += (predicted[i] - alternate[i]) ** 2; }
    near(m.data_chi_square, chi); near(m.data_wrms, Math.sqrt(chi / n)); near(m.cell_vs_bilinear_rmse_s, Math.sqrt(difference / n));
    if (name === "classical") { int(m.clipped_cells, 0, 256); num(m.regularizer, 0); require(m.solver === "Cholesky unconstrained normal equation followed by explicit slowness clipping" && m.bound_constrained_optimum_certified === false); }
  }
  const e = closed(d.engine, engineKeys); text(e.numpy, 64); text(e.scipy, 64); hash(e.user_tool_sha256); hash(e.velocity_operator_sha256);
  if (learned) {
    hash(e.checkpoint_sha256); require(e.checkpoint_protocol === "original" || e.checkpoint_protocol === "physics-v2");
    if (e.checkpoint_protocol === "physics-v2") hash(e.refinement_code_sha256); else require(e.refinement_code_sha256 === null);
    const dom = closed(d.learned_domain, ["training_geometry", "training_noise", "field_validated", "heldout_advantage"]);
    require(typeof dom.training_geometry === "boolean" && typeof dom.training_noise === "boolean" && dom.field_validated === false && dom.heldout_advantage === false);
  } else require(e.checkpoint_sha256 === null && e.checkpoint_protocol === null && e.refinement_code_sha256 === null && d.learned_domain === null);
  require(Array.isArray(d.warnings) && d.warnings.length <= 64); d.warnings.forEach(w => text(w, 2048));
  falseKeys(d.claims, ["field_truth_known", "field_validated", "heldout_advantage", "online_admitted"]);
  return value as VelocityResult;
}

async function digest(bytes: Uint8Array) { return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes as Uint8Array<ArrayBuffer>))].map(v => v.toString(16).padStart(2, "0")).join(""); }
export async function readVelocityFiles(resultFile: Blob, manifestFile: Blob): Promise<VelocityAdmission> {
  int(resultFile.size, 1, 4 * 1048576); int(manifestFile.size, 1, 4096); // BOTH before either read.
  const [r, m] = await Promise.all([resultFile.arrayBuffer(), manifestFile.arrayBuffer()]);
  require(r.byteLength === resultFile.size && m.byteLength === manifestFile.size);
  const result = parseVelocityResult(strictVelocityJson(new Uint8Array(r)));
  const manifest = closed(strictVelocityJson(new Uint8Array(m), 40000), ["schema", "result_sha256", "result_bytes", "source", "engine"]);
  require(manifest.schema === "geophysics.velocity-bundle/v1"); hash(manifest.result_sha256); int(manifest.result_bytes, 1, 4 * 1048576);
  source(manifest.source); closed(manifest.engine, engineKeys);
  require(sourceKeys.every(k => record(manifest.source)[k] === result.source[k as keyof typeof result.source]) && engineKeys.every(k => record(manifest.engine)[k] === result.engine[k as keyof typeof result.engine]));
  const resultSha256 = await digest(new Uint8Array(r)); require(manifest.result_bytes === r.byteLength && manifest.result_sha256 === resultSha256);
  return { result, resultSha256, manifestSha256: await digest(new Uint8Array(m)), resultBytes: r.byteLength, physicsReplayed: false };
}
export function velocitySelection(result: VelocityResult, model: VelocityModel, ray: number, x: number, z: number) {
  int(ray, 0, result.request.ray_ids.length - 1); int(x, 0, 15); int(z, 0, 15);
  const m = result.results[model]; require(m); const q = result.request;
  return { model, ray: { index: ray, id: q.ray_ids[ray], endpoints_m: q.rays_m[ray], observed_s: q.times_s[ray], sigma_s: q.sigma_s[ray],
    predicted_s: m.predicted_s[ray], residual_s: m.residual_s[ray], normalized_residual: m.normalized_residual[ray], bilinear_predicted_s: m.bilinear_predicted_s[ray] },
    cell: { x_index: x, depth_index: z, x_m: result.axes.x_m[x], depth_m: result.axes.depth_m[z], velocity_m_s: m.velocity_m_s[z][x], coverage_m: result.coverage_m[z][x] } };
}
