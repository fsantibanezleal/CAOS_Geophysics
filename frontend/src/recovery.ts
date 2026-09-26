import { extent, flatten, type ModelArray, type Method, type Run, type Uncertainty } from "./science";

export type ModelState = "final" | "replay";
export type PropertyScale = { range: [number, number]; maximum: number; signed: boolean };

/** The domain is fixed by the loaded artifact, never the selected view or frame. */
export function sharedScale(arrays: ModelArray[], signed = false): PropertyScale {
  let lo = 0, hi = 0;
  for (const array of arrays) for (const value of flatten(array)) {
    if (!Number.isFinite(value)) continue;
    lo = Math.min(lo, value); hi = Math.max(hi, value);
  }
  const maximum = Math.max(Math.abs(lo), Math.abs(hi));
  const diverging = signed || lo < 0;
  return { range: diverging ? [-(maximum || 1), maximum || 1] : [0, hi || 1], maximum, signed: diverging };
}

export function modelTarget(run: Run, methodId: string): "volume" | "vector-amplitude" | "column" | "observation-error" | "layers" | "velocity" {
  if (run.family === "mt") return "layers";
  if (run.family === "seismic") return "velocity";
  if (methodId === "cnn") return "column";
  if (methodId === "autoencoder") return "observation-error";
  if (methodId === "vector") return "vector-amplitude";
  return "volume";
}

export function physicalTarget(run: Run, methodId: string): ModelArray {
  if (methodId === "vector") return run.methods[methodId].vector_truth?.map(v => Math.hypot(...v)) ?? flatten(run.truth).map(Math.abs);
  return run.truth;
}

export function propertyScale(run: Run, methodId: string, secondary = false): PropertyScale {
  const target = modelTarget(run, methodId);
  const arrays: ModelArray[] = [secondary ? run.secondary_truth ?? [] : target === "column" ? run.column_truth ?? [] : physicalTarget(run, methodId)];
  if (!secondary && run.initial && target === "velocity") arrays.push(run.initial);
  for (const [id, method] of Object.entries(run.methods)) {
    if (modelTarget(run, id) !== target) continue;
    if (secondary) { if (method.magnetic_model ?? method.secondary_model) arrays.push((method.magnetic_model ?? method.secondary_model)!); }
    else {
      arrays.push(method.model, ...method.frames);
      if (method.uncertainty) arrays.push(method.uncertainty.lower, method.uncertainty.upper);
    }
  }
  const scale = sharedScale(arrays, target === "column");
  if (target === "velocity" || target === "layers") scale.range = extent(arrays.flatMap(flatten));
  return scale;
}

export function absoluteThreshold(scale: PropertyScale, fraction: number): number {
  return scale.maximum * Math.max(0, Math.min(1, fraction));
}

export function selectedModel(method: Method, state: ModelState = "final", frame = 0): ModelArray {
  return state === "replay" && method.frames.length
    ? method.frames[Math.max(0, Math.min(method.frames.length - 1, Math.floor(frame)))]
    : method.model;
}

export function uncertaintyProblem(uncertainty: Uncertainty, model: ModelArray): string | null {
  const size = flatten(model).length;
  const fields = [uncertainty.lower, uncertainty.upper, uncertainty.mean, uncertainty.std];
  const shape = (array: ModelArray) => Array.isArray(array[0]) ? (array as number[][]).map(row => row.length).join(",") : `flat:${array.length}`;
  if (fields.some(array => shape(array) !== shape(model))) return "shape";
  if (!size || fields.some(a => flatten(a).length !== size || flatten(a).some(v => !Number.isFinite(v)))) return "shape";
  if (uncertainty.members < 2 || !Number.isInteger(uncertainty.members)) return "members";
  const [lo, hi, , std] = fields.map(flatten);
  if (lo.some((v, i) => v > hi[i]) || std.some(v => v < 0)) return "interval";
  if (uncertainty.quantiles.length !== 2 || uncertainty.quantiles[0] < 0 || uncertainty.quantiles[1] > 1 || uncertainty.quantiles[0] >= uncertainty.quantiles[1]) return "quantiles";
  if (uncertainty.coverage != null && (!Number.isFinite(uncertainty.coverage) || uncertainty.coverage < 0 || uncertainty.coverage > 1)) return "coverage";
  return null;
}

/** Nonfinite/missing observations break a line; they are not replaced by zeros. */
export function curvePath(x: number[], y: number[], X: (v: number) => number, Y: (v: number) => number): string {
  let connected = false;
  return y.map((v, i) => {
    if (!Number.isFinite(v) || !Number.isFinite(x[i])) { connected = false; return ""; }
    const part = `${connected ? "L" : "M"}${X(x[i])},${Y(v)}`;
    connected = true;
    return part;
  }).filter(Boolean).join(" ");
}

export function intervalPath(x: number[], lower: number[], upper: number[], X: (v: number) => number, Y: (v: number) => number): string {
  const paths: string[] = [];
  let section: number[] = [];
  const flush = () => {
    if (section.length) paths.push(section.map((i, j) => `${j ? "L" : "M"}${X(x[i])},${Y(lower[i])}`).join(" ") + " " + [...section].reverse().map(i => `L${X(x[i])},${Y(upper[i])}`).join(" ") + " Z");
    section = [];
  };
  x.forEach((v, i) => { if ([v, lower[i], upper[i]].every(Number.isFinite) && lower[i] <= upper[i]) section.push(i); else flush(); });
  flush();
  return paths.join(" ");
}

/** Membership weights are not a posterior probability of true lithology. */
export function membershipField(method: Method, component: number, cells: number): number[] | null {
  const rows = method.prior_membership ?? method.responsibilities;
  if (!rows || rows.length !== cells || !rows[0]?.length || component < 0 || component >= rows[0].length) return null;
  if (rows.some(row => row.length !== rows[0].length || row.some(v => !Number.isFinite(v) || v < 0 || v > 1) || Math.abs(row.reduce((a, b) => a + b, 0) - 1) > 1e-4)) return null;
  return rows.map(row => row[component]);
}
