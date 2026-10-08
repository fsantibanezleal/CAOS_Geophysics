import { zip, type Zippable } from "fflate";

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type Obj = { [key: string]: Json };
export type Modality = "gravity" | "magnetic";
export type Partition = "training" | "validation" | "sealed";
export type NativeArray = { dtype: string; shape: number[]; values: Float64Array | Uint8Array };
type Descriptor = { dtype: string; shape: number[]; file_bytes: number; file_sha256: string; data_sha256: string };
type Spec = { dtype: string; shape: number[] };
export type NativeRecord = { payload: Obj; arrays: Record<string, NativeArray>; manifestPath: string };
export type JointFile = { path: string; size: number; read: () => Promise<Uint8Array> };
export type JointCandidate = {
  metadata: Obj; stage: number; modality: Modality | null; start: string; weights: Obj;
  status: string; reason: string; iterations: number; writerReplayed: boolean;
  trace: Record<string, NativeArray>; physical: NativeArray | null; terms: NativeArray | null;
};
export type JointInspection = {
  schema: "joint-local-inspection-1"; outcome: "completed" | "failed"; mode: string;
  receipt: Obj; frozen: NativeRecord | null; result: NativeRecord | null;
  model: NativeRecord | null; calibration: NativeRecord | null; aborted: NativeRecord | null; instrument: NativeRecord | null;
  candidates: JointCandidate[]; files: ReadonlyMap<string, Uint8Array>; hashes: ReadonlyMap<string, string>;
  importedBytes: number; limitations: typeof INSPECTION_FLAGS;
};
export const JOINT_CLIENT_PINS = Object.freeze({
  optimizer_source_sha256: "772c4de0b7747bbc9075b6fbf1357b04de752bfd900f88c9a5ddead2a91931fd",
  vendor_source_sha256: "0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4",
  runtime_epoch: "physical-gncg-nonlinear-candidate-2", policy: "exact-bound-native-gncg-actual-armijo-1",
});
export const INSPECTION_FLAGS = Object.freeze({ offline_scientific_replay_performed: false,
  inverse_executed_in_browser: false, scientific_acceptance_verified: false,
  field_eligible: false, public_redistribution: false, archive_authenticated: false });
export const JOINT_IMPORT_CAP = 268435456;
// Late failures retain both genuine ledgers: at most1090 fixed native members.
const JSON_CAP = 262144, MAX_FILES = 1100, MAX_HEADER = 4096;
const MODALITIES = ["gravity", "magnetic"] as const, PARTITIONS = ["training", "validation", "sealed"] as const;
const BETAS = [.0001, .001, .01, .1, 1, 10, 100, 1000], LAMBDAS = [.001, .01, .1, 1, 10];
const STATES = ["models_q", "phi_d", "phi_m", "phi_engine", "kkt_normalized"];
const STEPS = ["relative_changes", "branches", "active_counts", "binding_counts", "cg_counts", "cg_abs_residuals",
  "cg_relative_residuals", "line_search_counts", "line_search_alphas", "projected_slopes", "armijo_margins", "cg_residuals_available"];
const INTS = ["branches", "active_counts", "binding_counts", "cg_counts", "line_search_counts"];
const TERM_NAMES = ["data_gravity", "data_magnetic", "regularization_gravity", "regularization_magnetic", "coupling"];
const GRAM = ["gram_density", "gram_susceptibility", "gram_product", "face_contribution"];
const EXPORTER_SOURCES = ["joint_survey_instrument.py", "joint_survey_calibration_io.py", "joint_survey_evaluation.py", "joint_survey_files.py", "joint_survey_intake.py", "joint_survey_model_export.py", "joint_survey_resources.py", "joint_survey_workflow.py"];
const EPOCHS = { gravity: "simpeg-0.25.2-geoana-0.8.1-f64-ram", magnetic: "simpeg-0.25.2-geoana-0.8.1-f64-induced-ram" };
const SOURCE_NAMES = ["BaseSimilarityMeasure", "CrossGradient", "DiffOperators", "RegularizationMesh", "RegularizationMesh.cell_gradient", "TensorMesh", "Wires", "gravity_forward.py", "magnetic_forward.py", "joint_survey_compiled.py", "joint_survey_objective.py", "joint_survey_optimizer.py", "joint_survey_plan.py", "joint_survey_structure.py", "physical_nonlinear_optimizer.py", "simpeg.optimization"];
function requireThat(test: unknown, reason: string): asserts test { if (!test) throw new Error(`Joint import: ${reason}`); }
export function obj(v: Json): Obj { requireThat(v !== null && typeof v === "object" && !Array.isArray(v), "object required"); return v; }
function list(v: Json): Json[] { requireThat(Array.isArray(v), "list required"); return v; }
function keys(v: Obj, names: string[]) { requireThat(Object.keys(v).length === names.length && names.every(k => Object.hasOwn(v, k)), "exact record keys"); }
function num(v: Json, lo = -Infinity, hi = Infinity): number { requireThat(typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi, "finite numeric range"); return v; }
function integer(v: Json, lo: number, hi: number) { const n = num(v, lo, hi); requireThat(Number.isSafeInteger(n), "literal safe integer"); return n; }
function text(v: Json): string { requireThat(typeof v === "string", "text required"); return v; }
function sha(v: Json): string { const s = text(v); requireThat(/^[a-f0-9]{64}$/.test(s), "SHA-256 grammar"); return s; }
function eq(a: Json, b: Json) { return stable(a) === stable(b); }
function stable(v: Json): string { return v !== null && typeof v === "object" ? Array.isArray(v) ? `[${v.map(stable).join(",")}]` : `{${Object.keys(v).sort().map(k => `${JSON.stringify(k)}:${stable(v[k])}`).join(",")}}` : JSON.stringify(v); }
function close(a: number, b: number) { return Math.abs(a - b) <= 1e-12 * Math.max(1, Math.abs(a), Math.abs(b)); }
export async function jointSha(bytes: Uint8Array) {
  const digest = await crypto.subtle.digest("SHA-256", bytes.slice().buffer);
  return Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, "0")).join("");
}

/** Small bounded JSON grammar with duplicate-key rejection; no reviver or hooks. */
export function jointJson(bytes: Uint8Array): Obj {
  requireThat(bytes.length <= JSON_CAP, "JSON byte cap");
  const source = new TextDecoder("utf-8", { fatal: true }).decode(bytes); let at = 0, leaves = 0;
  const ws = () => { while (/[\x20\t\r\n]/.test(source[at] ?? "x")) at++; };
  function string(): string {
    const start = at++; requireThat(source[start] === '"', "JSON string");
    while (at < source.length) { const c = source[at++]; if (c === "\\") at++; else if (c === '"') {
      const s: unknown = JSON.parse(source.slice(start, at)); requireThat(typeof s === "string" && new TextEncoder().encode(s).length <= 4096, "text byte cap"); return s;
    } } throw new Error("Joint import: unterminated string");
  }
  function value(depth: number): Json {
    requireThat(depth <= 8, "metadata depth"); ws(); const c = source[at];
    if (c === "{") {
      at++; const out: Obj = Object.create(null); ws(); if (source[at] === "}") { at++; return out; }
      for (;;) { ws(); const k = string(); requireThat(!Object.hasOwn(out, k) && !["__proto__", "prototype", "constructor"].includes(k), "duplicate or unsafe key");
        ws(); requireThat(source[at++] === ":", "JSON colon"); out[k] = value(depth + 1); ws(); const next = source[at++]; if (next === "}") return out; requireThat(next === ",", "JSON object separator"); }
    }
    if (c === "[") { at++; const out: Json[] = []; ws(); if (source[at] === "]") { at++; return out; }
      for (;;) { out.push(value(depth + 1)); ws(); const next = source[at++]; if (next === "]") return out; requireThat(next === ",", "JSON list separator"); } }
    requireThat(++leaves <= 32768, "metadata scalar cap");
    if (c === '"') return string();
    for (const [literal, result] of [["null", null], ["true", true], ["false", false]] as const) if (source.startsWith(literal, at)) { at += literal.length; return result; }
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(source.slice(at));
    requireThat(match, "JSON literal"); at += match[0].length; const n = Number(match[0]); requireThat(Number.isFinite(n), "nonfinite metadata");
    if (!/[.eE]/.test(match[0])) requireThat(Number.isSafeInteger(n), "metadata integer cap"); return n;
  }
  const out = obj(value(0)); ws(); requireThat(at === source.length, "JSON trailing bytes"); return out;
}

/** All headers must pass this before ANY array value or value hash is accessed. */
function header(bytes: Uint8Array, d: Descriptor): number {
  requireThat(bytes.length === d.file_bytes && bytes.length >= 10 && bytes[0] === 147 && new TextDecoder().decode(bytes.subarray(1, 6)) === "NUMPY" && bytes[6] === 1 && bytes[7] === 0, "NPY1 magic/size");
  const length = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint16(8, true), offset = 10 + length;
  requireThat(offset <= MAX_HEADER && offset <= bytes.length && offset % 64 === 0, "NPY bounded aligned header");
  const source = new TextDecoder("ascii", { fatal: true }).decode(bytes.subarray(10, offset));
  const m = /^\{'descr': '(<f8|<i8|\|b1)', 'fortran_order': False, 'shape': \((\d+,|\d+, \d+)\), \} *\n$/.exec(source);
  requireThat(m, "literal non-executable NPY header"); const shape = m[2].split(",").map(v => v.trim()).filter(Boolean).map(Number);
  requireThat(m[1] === d.dtype && eq(shape, d.shape) && offset + shape.reduce((a, b) => a * b, 1) * (d.dtype === "|b1" ? 1 : 8) === bytes.length, "NPY descriptor shape/dtype");
  return offset;
}
function decode(bytes: Uint8Array, d: Descriptor, offset: number): NativeArray {
  const count = d.shape.reduce((a, b) => a * b, 1); let values: Float64Array | Uint8Array;
  if (d.dtype === "<f8") values = new Float64Array(bytes.buffer, bytes.byteOffset + offset, count);
  else if (d.dtype === "|b1") { values = bytes.subarray(offset); requireThat(values.every(v => v === 0 || v === 1), "native boolean bytes"); }
  else { const view = new DataView(bytes.buffer, bytes.byteOffset + offset, count * 8); values = new Float64Array(count);
    for (let i = 0; i < count; i++) { const n = view.getBigInt64(i * 8, true); requireThat(n >= BigInt(-Number.MAX_SAFE_INTEGER) && n <= BigInt(Number.MAX_SAFE_INTEGER), "int64 inspection range"); values[i] = Number(n); } }
  requireThat(values.every(Number.isFinite), "nonfinite array"); return { dtype: d.dtype, shape: d.shape, values };
}
function spec(names: Record<string, Spec>, name: string, dtype: string, shape: number[]) { requireThat(!names[name], "duplicate array binding"); names[name] = { dtype, shape }; }
function ref(node: Obj, key: string, name: string, specs: Record<string, Spec>, dtype: string, shape: number[]) {
  const r = obj(node[key]); keys(r, ["array"]); requireThat(r.array === name, "fixed array reference"); spec(specs, name, dtype, shape);
}
function falseFlags(v: Obj, names: string[]) { for (const k of names) requireThat(v[k] === false, `false claim ${k}`); }
function weights(v: Json): Obj { const w = obj(v); keys(w, ["beta_gravity", "beta_magnetic", "coupling"]);
  requireThat(BETAS.includes(num(w.beta_gravity)) && BETAS.includes(num(w.beta_magnetic)) && [0, ...LAMBDAS].includes(num(w.coupling)), "frozen candidate strengths"); return w; }
function identities(v: Obj) { for (const k of ["plan_sha256", "development_sha256", "frozen_sha256"]) sha(v[k]);
  requireThat(["supplied_model", "optimized_selection"].includes(text(v.origin)) && eq(v.physical_epochs, EPOCHS), "physical epoch/origin");
  if (v.selection_sha256 !== null) sha(v.selection_sha256); }
function binding(value: Json) { const b = obj(value); keys(b, ["accepted_export", ...Object.keys(JOINT_CLIENT_PINS), "source_inventory_sha256"]);
  requireThat(b.accepted_export === "physical_nonlinear_optimizer.solve_bounded_nonlinear", "public optimizer export");
  for (const [k, v] of Object.entries(JOINT_CLIENT_PINS)) requireThat(b[k] === v, "unsupported optimizer source/ABI"); sha(b.source_inventory_sha256); }
function resource(value: Json, complete: boolean) {
  const r = obj(value); keys(r, ["schema", "elapsed_seconds", "peak_sampled_rss_bytes", "peak_sampled_scratch_bytes", "samples", "sampling_seconds", "deadline_seconds", "rss_limit_bytes", "scratch_limit_bytes", "workflow_completed", "complete_workflow_resource_pass", "os_reservation", "hard_realtime_interruption"]);
  requireThat(r.schema === "joint-survey-resource-receipt-1" && r.deadline_seconds === 1800 && r.rss_limit_bytes === 2147483648 && r.scratch_limit_bytes === JOINT_IMPORT_CAP && r.sampling_seconds === .05, "resource ABI");
  num(r.elapsed_seconds, 0); integer(r.peak_sampled_rss_bytes, 1, Number.MAX_SAFE_INTEGER); integer(r.peak_sampled_scratch_bytes, 0, Number.MAX_SAFE_INTEGER); integer(r.samples, 2, Number.MAX_SAFE_INTEGER);
  falseFlags(r, ["os_reservation", "hard_realtime_interruption"]); requireThat(r.workflow_completed === complete && r.complete_workflow_resource_pass === complete, "resource completion declaration");
  if (complete) requireThat(num(r.elapsed_seconds) <= 1800 && num(r.peak_sampled_rss_bytes) <= 2147483648 && num(r.peak_sampled_scratch_bytes) <= JOINT_IMPORT_CAP, "completed resource overrun");
}
function attempt(c: Obj, specs: Record<string, Spec>, stage: number, last = false) {
  keys(c, last ? ["stage", "modality", "weights", "start_kind", "identity", "result", "scientific_replay_completed"] : ["stage", "modality", "weights", "start_kind", "identity", "result", "physical_trace", "terms_trace", "validation_wrms", "stationarity_verified", "eligible"]);
  requireThat(c.stage === stage && c.modality === (stage < 8 ? "gravity" : stage < 16 ? "magnetic" : null) && c.start_kind === (stage < 16 || stage % 2 === 0 ? "submitted" : "baseline"), "ordered actual candidate schedule");
  const w = weights(c.weights), id = obj(c.identity), r = obj(c.result);
  keys(id, ["allocation_plan_sha256", "beta_engine", "mode", "objective_sha256", "observation_components", "observation_rows", "parameter_count", "physical_scale", "physical_unit", "q_unit", "runtime_epoch", "source_inventory_sha256", "stage_index"]);
  for (const k of ["allocation_plan_sha256", "objective_sha256", "source_inventory_sha256"]) sha(id[k]);
  const n = integer(id.parameter_count, 1, 8192), scale = list(id.physical_scale).map(v => num(v, Number.MIN_VALUE));
  requireThat(id.stage_index === stage && id.beta_engine === 1 && id.mode === "nonlinear_gauss_newton" && id.runtime_epoch === JOINT_CLIENT_PINS.runtime_epoch && id.q_unit === (c.modality === null ? "normalized_two_property_blocks" : "normalized_property_block"), "objective ABI");
  integer(id.observation_rows, 1, 4096); requireThat(id.observation_components === (c.modality === null ? 2 : 1) && scale.length === (c.modality === null ? 2 : 1) && (c.modality !== null || n % 2 === 0), "property block identity");
  requireThat(id.physical_unit === (c.modality === "gravity" ? "kg_m3" : c.modality === "magnetic" ? "si" : "kg_m3_and_si"), "physical block units");
  if (stage < 16) requireThat(w.coupling === 0 && w[c.modality === "gravity" ? "beta_gravity" : "beta_magnetic"] === BETAS[stage % 8] && w[c.modality === "gravity" ? "beta_magnetic" : "beta_gravity"] === .0001, "baseline strength schedule");
  else requireThat(w.coupling === LAMBDAS[Math.floor((stage - 16) / 2)], "positive strength schedule");
  keys(r, ["status", "reason", "q", "phi_d", "phi_m", "phi_engine", "kkt_normalized", "iterations", "trace", "failed_trial"]);
  const status = text(r.status), reason = text(r.reason), iterations = integer(r.iterations, 0, 250);
  requireThat(["kkt", "iteration_cap", "wall_cap", "state_mismatch", "nonfinite", "engine_error", "cg_cap", "zero_free_direction", "line_search_failed"].includes(reason), "literal solver reason");
  requireThat(status === (reason === "kkt" ? "converged" : ["state_mismatch", "nonfinite", "engine_error"].includes(reason) ? "failed" : "nonconverged"), "literal solver status");
  if (status === "converged") requireThat(r.failed_trial === null, "converged failed trial");
  else { const f = obj(r.failed_trial); keys(f, ["iteration", "reason"]); requireThat(f.iteration === iterations && f.reason === reason, "failed trial identity"); }
  const count = r.q === null ? 0 : iterations + 1, steps = Math.max(0, count - 1), prefix = last ? "last_" : `c${String(stage).padStart(2, "0")}_`, tr = obj(r.trace); keys(tr, [...STATES, ...STEPS]);
  if (r.q !== null) ref(r, "q", prefix + "q", specs, "<f8", [n]);
  for (const k of [...STATES, ...STEPS]) ref(tr, k, prefix + k, specs, k === "cg_residuals_available" ? "|b1" : INTS.includes(k) ? "<i8" : "<f8", k === "models_q" ? [count, n] : [STATES.includes(k) ? count : steps]);
  if (last) requireThat(c.scientific_replay_completed === false, "unreplayed last attempt");
  else { ref(c, "physical_trace", prefix + "physical_trace", specs, "<f8", [count, n]); ref(c, "terms_trace", prefix + "terms_trace", specs, "<f8", [count, 5]);
    requireThat(typeof c.stationarity_verified === "boolean" && typeof c.eligible === "boolean", "candidate boolean claims");
    const v = obj(c.validation_wrms); keys(v, count ? c.modality === null ? [...MODALITIES] : [text(c.modality)] : []); for (const a of Object.values(v)) num(a, 0); }
  for (const k of STATES.slice(1)) if (count) num(r[k]); else requireThat(r[k] === null, "empty trace scalar");
}

function specifications(directory: string, p: Obj, descriptors: Obj): Record<string, Spec> {
  const s: Record<string, Spec> = Object.create(null);
  if (directory === "frozen") {
    keys(p, ["schema", "plan_sha256", "development_sha256", "frozen_sha256", "origin", "selection_sha256", "physical_epochs", "weights"]);
    requireThat(p.schema === "joint-survey-frozen-model-1", "frozen schema"); identities(p); weights(p.weights);
    const shape = list(obj(descriptors.q).shape); const n = integer(shape[0], 2, 8192); requireThat(n % 2 === 0 && shape.length === 1, "two property model"); spec(s, "q", "<f8", [n]);
  } else if (directory === "models") {
    keys(p, ["schema", "plan_sha256", "development_sha256", "frozen_sha256", "origin", "selection_sha256", "physical_epochs", "frame", "cell_order", "density_unit", "susceptibility_unit", "length_unit", "volume_unit", "density_scale", "susceptibility_scale", "inducing_field", "field_eligible", "recovery_verified", "global_optimum_verified", "rights_verified", "public_redistribution", "inverse_execution_asserted_by_this_model"]);
    requireThat(p.schema === "joint-survey-physical-model-1" && p.cell_order === "x-fast" && p.density_unit === "kg_m3" && p.susceptibility_unit === "si" && p.length_unit === "m" && p.volume_unit === "m3", "native physical units"); identities(p);
    falseFlags(p, ["field_eligible", "recovery_verified", "global_optimum_verified", "rights_verified", "public_redistribution", "inverse_execution_asserted_by_this_model"]);
    num(p.density_scale, .001, 5000); num(p.susceptibility_scale, 1e-8, .1);
    const frame = obj(p.frame); keys(frame, ["kind", "axes", "length_unit", "vertical_positive", "reference_id", "horizontal_datum", "vertical_datum"]);
    requireThat(frame.kind === "local_cartesian" && eq(frame.axes, ["east", "north", "up"]) && frame.length_unit === "m" && frame.vertical_positive === "up", "ENU native frame"); for (const k of ["reference_id", "horizontal_datum", "vertical_datum"]) text(frame[k]);
    const field = obj(p.inducing_field); keys(field, ["amplitude_nt", "inclination_deg", "declination_deg"]); num(field.amplitude_nt, 1, 1e6); num(field.inclination_deg, -90, 90); num(field.declination_deg, -180, 180);
    const n = integer(list(obj(descriptors.density_kg_m3).shape)[0], 1, 4096);
    for (const k of ["density_kg_m3", "susceptibility_si", "active_cell_volumes_m3"]) spec(s, k, "<f8", [n]);
    spec(s, "active_full_indices", "<i8", [n]); spec(s, "active_cell_centres_m", "<f8", [n, 3]); spec(s, "active_cell_bounds_m", "<f8", [n, 6]); spec(s, "mesh_origin_m", "<f8", [3]);
    let total = 1; for (const k of ["mesh_hx_m", "mesh_hy_m", "mesh_hz_m"]) { const len = integer(list(obj(descriptors[k]).shape)[0], 2, 64); total *= len; spec(s, k, "<f8", [len]); } requireThat(total <= 4096, "mesh count cap");
  } else if (directory === "result") {
    keys(p, ["schema", "plan_sha256", "development_sha256", "frozen_sha256", "origin", "selection_sha256", "physical_epochs", "weights", "objective", "terms", "exact_bound_kkt_inf", "metrics", "claims", "sealed_bindings"]);
    requireThat(p.schema === "joint-survey-evaluation-1", "result schema"); identities(p); weights(p.weights); num(p.objective); num(p.exact_bound_kkt_inf, 0);
    const terms = obj(p.terms); keys(terms, TERM_NAMES); for (const v of Object.values(terms)) num(v);
    const claims = obj(p.claims); keys(claims, ["calibration_identity_declared", "correction_science_verified", "cross_partition_dependence", "field_eligible", "global_optimum_verified", "inverse_completed", "public_redistribution", "recovery_verified", "rights_verified"]);
    falseFlags(claims, ["correction_science_verified", "field_eligible", "global_optimum_verified", "inverse_completed", "public_redistribution", "recovery_verified", "rights_verified"]);
    requireThat(claims.calibration_identity_declared === (p.selection_sha256 !== null), "calibration declaration"); const cross = obj(claims.cross_partition_dependence); keys(cross, [...MODALITIES]); for (const v of Object.values(cross)) requireThat(["declared_absent", "possible_not_removed"].includes(text(v)), "covariance dependence declaration");
    const metrics = obj(p.metrics); keys(metrics, [...MODALITIES]); const nq = integer(list(obj(descriptors.q).shape)[0], 2, 8192); requireThat(nq % 2 === 0, "result property count"); spec(s, "q", "<f8", [nq]);
    for (const m of MODALITIES) { const blocks = obj(metrics[m]); keys(blocks, [...PARTITIONS]); let rows = 0;
      for (const part of PARTITIONS) { const v = obj(blocks[part]); keys(v, ["count", "rmse_physical", "unit", "wrms", "chi_square"]); const n = integer(v.count, 1, 2048); rows += n; requireThat(v.unit === (m === "gravity" ? "mGal" : "nT"), "result response unit"); for (const k of ["rmse_physical", "wrms", "chi_square"]) num(v[k], 0);
        for (const k of ["rows", "observed", "predicted", "signed_residual", "whitened_residual"]) spec(s, `${m}_${part}_${k}`, k === "rows" ? "<i8" : "<f8", [n]); } requireThat(rows <= 2048, "whole modality rows cap"); }
    const sealed = obj(p.sealed_bindings); keys(sealed, ["manifest_sha256", "arrays"]); sha(sealed.manifest_sha256); const a = obj(sealed.arrays); keys(a, MODALITIES.flatMap(m => ["rows", "observed", "noise"].map(k => m + "_" + k))); for (const v of Object.values(a)) descriptor(obj(v));
  } else if (directory === "calibration" || directory === "aborted") {
    const abort = directory === "aborted";
    keys(p, abort ? ["schema", "plan_sha256", "development_sha256", "reason", "source_inventory", "optimizer_binding", "verified_candidates", "last_attempt", "inverse_completed", "sealed_values_read_started", "frozen_selection_created", "scientific_replay_completed", "field_eligible"] : ["schema", "plan_sha256", "development_sha256", "optimizer_binding", "source_inventory", "allocation_plan", "status", "reason", "candidates", "selected_baselines", "selection", "calibration_sha256"]);
    requireThat(p.schema === (abort ? "joint-survey-aborted-calibration-1" : "joint-survey-calibration-1"), "calibration schema"); sha(p.plan_sha256); sha(p.development_sha256); binding(p.optimizer_binding);
    const inventory = obj(p.source_inventory); keys(inventory, SOURCE_NAMES); for (const v of Object.values(inventory)) sha(v);
    requireThat(inventory["physical_nonlinear_optimizer.py"] === JOINT_CLIENT_PINS.optimizer_source_sha256 && inventory["simpeg.optimization"] === JOINT_CLIENT_PINS.vendor_source_sha256, "source inventory optimizer pins");
    const candidates = list(p[abort ? "verified_candidates" : "candidates"]); requireThat(candidates.length <= 26 && (abort || candidates.length === 16 || candidates.length === 26), "whole candidate count");
    candidates.forEach((v, i) => attempt(obj(v), s, i));
    if (abort) { falseFlags(p, ["inverse_completed", "scientific_replay_completed", "field_eligible"]); for (const k of ["sealed_values_read_started", "frozen_selection_created"]) requireThat(typeof p[k] === "boolean", "abort phase boolean");
      if (p.last_attempt !== null) { requireThat(candidates.length < 26, "last attempt count"); attempt(obj(p.last_attempt), s, candidates.length, true); } }
    else { sha(p.calibration_sha256); const a = obj(p.allocation_plan); keys(a, ["active_cells", "admitted_bytes", "allocation_plan_sha256", "development_bytes", "fits", "kernel_bytes", "maximum_cg_steps", "maximum_ls_trials", "trace_states_per_fit"]);
      const n = integer(a.active_cells, 1, 4096); requireThat(a.fits === 26 && a.maximum_cg_steps === 512 && a.maximum_ls_trials === 30 && a.trace_states_per_fit === 251, "allocation caps"); sha(a.allocation_plan_sha256);
      if (p.selection !== null) { requireThat(p.status === "selected" && candidates.length === 26, "selected schedule"); const selection = obj(p.selection); keys(selection, ["q", "weights", "stage", "baseline_validation_wrms", "validation_wrms", "refit", "lambda0_refitted"]); falseFlags(selection, ["refit", "lambda0_refitted"]); weights(selection.weights); ref(selection, "q", "selection_q", s, "<f8", [2 * n]); }
      else requireThat(p.status === "failed" && candidates.length === 16 && p.reason === "no_stationary_separate_baseline", "failed baseline selection"); }
  } else if (directory === "instrument") {
    keys(p, ["schema", "plan_sha256", "development_sha256", "frozen_sha256", "calibration_sha256", "original_file_sha256", "exporter_source_inventory", "physical_epochs", "entries", "coupling_method", "coupling_length_m", "coupling_factor", "metric_columns", "residual_convention", "historical_sealed_use", "refit", "scientific_acceptance_verified", "field_eligible", "recovery_verified", "global_optimum_verified", "public_activation", "public_redistribution", "archive_authenticated"]);
    requireThat(p.schema === "joint-survey-state-instrument-1" && eq(p.physical_epochs, EPOCHS) && p.coupling_method === "active-face-averaged-squared-product-gram" && eq(p.metric_columns, ["rmse_physical", "wrms", "chi_square"]) && p.residual_convention === "predicted_minus_observed" && p.historical_sealed_use === "post_freeze_diagnostic_only", "accepted state instrument ABI");
    for (const k of ["plan_sha256", "development_sha256", "frozen_sha256"]) sha(p[k]); if (p.calibration_sha256 !== null) sha(p.calibration_sha256);
    falseFlags(p, ["refit", "scientific_acceptance_verified", "field_eligible", "recovery_verified", "global_optimum_verified", "public_activation", "public_redistribution", "archive_authenticated"]);
    num(p.coupling_length_m, Number.MIN_VALUE); num(p.coupling_factor, Number.MIN_VALUE);
    const inventory = obj(p.exporter_source_inventory); keys(inventory, EXPORTER_SOURCES); for (const v of Object.values(inventory)) sha(v);
    const original = obj(p.original_file_sha256); requireThat(Object.keys(original).length > 0 && Object.keys(original).length <= 568, "original instrument inventory count"); for (const v of Object.values(original)) sha(v);
    const n = integer(list(obj(descriptors.selected_face_contribution).shape)[1], 1, 4096), entries = list(p.entries); requireThat(entries.length === (p.calibration_sha256 === null ? 1 : 28), "instrument frame count");
    for (let i = 0; i < entries.length; i++) { const e = obj(entries[i]); keys(e, ["key", "kind", "stage", "modality", "state_count", "weights"]); weights(e.weights);
      const candidate = i < entries.length - 2 && entries.length === 28, key = candidate ? `c${String(i).padStart(2, "0")}` : i === entries.length - 1 ? "selected" : "baseline";
      requireThat(e.key === key && e.kind === (candidate ? "candidate" : key === "selected" ? "frozen_selection" : "independently_optimized_pair") && e.stage === (candidate ? i : null) && e.modality === (candidate && i < 16 ? i < 8 ? "gravity" : "magnetic" : null), "ordered instrument state identity");
      const count = integer(e.state_count, candidate ? 0 : 1, candidate ? 251 : 1);
      for (const m of e.modality === null ? MODALITIES : [e.modality as Modality]) for (const part of PARTITIONS) {
        const rows = integer(list(obj(descriptors[`selected_${m}_${part}_predicted`]).shape)[1], 1, 2048);
        for (const name of ["predicted", "signed_residual", "whitened_residual", "metrics"]) spec(s, `${key}_${m}_${part}_${name}`, "<f8", [count, name === "metrics" ? 3 : rows]);
      }
      if (e.modality === null) for (const name of GRAM) spec(s, `${key}_${name}`, "<f8", [count, n]);
    }
  } else throw new Error("Joint import: unsupported directory");
  keys(descriptors, Object.keys(s)); return s;
}
function descriptor(d: Obj): Descriptor {
  keys(d, ["dtype", "shape", "file_bytes", "file_sha256", "data_sha256"]); const dtype = text(d.dtype); requireThat(["<f8", "<i8", "|b1"].includes(dtype), "native dtype");
  const shape = list(d.shape).map(v => integer(v, 0, 8192)); requireThat(shape.length >= 1 && shape.length <= 2, "native rank");
  return { dtype, shape, file_bytes: integer(d.file_bytes, 11, JOINT_IMPORT_CAP), file_sha256: sha(d.file_sha256), data_sha256: sha(d.data_sha256) };
}
const MANIFESTS: Record<string, [string, string]> = { frozen: ["frozen.json", "joint-survey-frozen-model-file-1"], result: ["result.json", "joint-survey-result-file-1"], models: ["model.json", "joint-survey-physical-model-file-1"], calibration: ["calibration.json", "joint-survey-calibration-file-1"], aborted: ["aborted.json", "joint-survey-aborted-calibration-file-1"], instrument: ["instrument.json", "joint-survey-state-instrument-file-1"] };

export async function importJointOutput(input: readonly JointFile[], signal?: AbortSignal): Promise<JointInspection> {
  const cancel = () => { if (signal?.aborted) throw new Error("Joint import: cancelled"); };
  requireThat(input.length > 0 && input.length <= MAX_FILES, "whole file count"); let total = 0;
  const top = input.some(f => f.path === "workflow.json" || f.path === "failure.json"), prefix = top ? "" : input[0].path.split("/")[0] + "/";
  requireThat(top || /^[^./\\\x00-\x1f][^/\\\x00-\x1f]*\/$/.test(prefix), "ordinary selected directory prefix");
  const entries = new Map<string, JointFile>();
  for (const f of input) { requireThat(f.path.startsWith(prefix), "single selected output directory"); const path = f.path.slice(prefix.length);
    requireThat(/^(?:workflow\.json|failure\.json|(?:frozen|result|models|calibration|aborted|instrument)\/[a-z0-9_]+\.(?:json|npy))$/.test(path) && !entries.has(path), "fixed unique output path");
    requireThat(Number.isSafeInteger(f.size) && f.size > 0 && f.size <= JOINT_IMPORT_CAP && (!path.endsWith(".json") || f.size <= JSON_CAP), "original file byte cap"); total += f.size; requireThat(total <= JOINT_IMPORT_CAP, "whole original byte cap"); entries.set(path, f); }
  cancel(); const files = new Map<string, Uint8Array>(), hashes = new Map<string, string>();
  async function read(path: string) { const file = entries.get(path); requireThat(file, "missing fixed file " + path); cancel(); const bytes = new Uint8Array(await file.read()); cancel(); requireThat(bytes.length === file.size, "original file size changed"); files.set(path, bytes); return bytes; }
  const receipts: Record<string, Obj> = {}; for (const path of ["workflow.json", "failure.json"]) if (entries.has(path)) receipts[path] = jointJson(await read(path));
  requireThat(receipts["workflow.json"] || receipts["failure.json"], "workflow receipt required");
  const failed = !!receipts["failure.json"] || receipts["workflow.json"]?.status === "failed", receipt = receipts["failure.json"] ?? receipts["workflow.json"];
  function checkReceipt(receipt: Obj, failureMarker: boolean) {
  const failed = failureMarker || receipt.status === "failed", mode = text(receipt.mode); requireThat(["solve", "evaluate"].includes(mode) && receipt.status === (failed ? "failed" : "completed"), "workflow status/mode");
  if (failureMarker) { keys(receipt, ["schema", "mode", "status", "reason", "inverse_completed", "sealed_evaluation_completed", "public_activation", "accepted_attempts_retained", "resources"]); requireThat(receipt.schema === "joint-survey-workflow-failure-1" && mode === "solve" && receipt.accepted_attempts_retained === true, "abort workflow schema"); text(receipt.reason); }
  else if (failed) { keys(receipt, ["schema", "mode", "status", "reason", "calibration_sha256", "inverse_completed", "sealed_evaluation_completed", "public_activation", "resources"]); requireThat(receipt.reason === "no_stationary_separate_baseline" && mode === "solve", "failed workflow reason"); sha(receipt.calibration_sha256); }
  else { keys(receipt, ["schema", "mode", "status", "plan_sha256", "frozen_sha256", "calibration_sha256", "input_bindings", "source_diagnostics", "inverse_completed", "sealed_evaluation_completed", "field_eligible", "public_activation", "private_export_bytes_before_receipt", "resources"]);
    const completedBytes = [...entries].reduce((sum, [path, f]) => sum + (path === "workflow.json" || path === "failure.json" || path.startsWith("aborted/") || path.startsWith("instrument/") ? 0 : f.size), 0);
    sha(receipt.plan_sha256); sha(receipt.frozen_sha256); falseFlags(receipt, ["field_eligible"]); requireThat(receipt.private_export_bytes_before_receipt === completedBytes, "actual export byte receipt");
    const inputs = obj(receipt.input_bindings); keys(inputs, ["correction_sha256", "development_sha256", "directory_content_sha256", "raw_sha256", "request_file_sha256"]);
    for (const k of ["development_sha256", "directory_content_sha256", "request_file_sha256"]) sha(inputs[k]);
    for (const k of ["correction_sha256", "raw_sha256"]) { const pair = obj(inputs[k]); keys(pair, [...MODALITIES]); for (const v of Object.values(pair)) if (v !== null) sha(v); }
    const diagnostics = obj(receipt.source_diagnostics); keys(diagnostics, ["concurrent_snapshot_guaranteed", "correction_bytes_verified", "correction_science_verified", "field_eligible", "inverse_completed", "rights_verified", "sealed_values_loaded", "source_bytes_verified"]);
    falseFlags(diagnostics, ["concurrent_snapshot_guaranteed", "correction_science_verified", "field_eligible", "inverse_completed", "rights_verified", "sealed_values_loaded"]);
    for (const k of ["source_bytes_verified", "correction_bytes_verified"]) { const pair = obj(diagnostics[k]); keys(pair, [...MODALITIES]); for (const v of Object.values(pair)) requireThat(typeof v === "boolean", "source verification declaration"); }
  }
  if (!failureMarker) requireThat(receipt.schema === "joint-survey-workflow-receipt-1", "workflow schema");
  falseFlags(receipt, ["public_activation"]); requireThat(receipt.inverse_completed === (!failed && mode === "solve") && receipt.sealed_evaluation_completed === !failed, "workflow claim flags"); resource(receipt.resources, !failed);
  }
  for (const [path, r] of Object.entries(receipts)) checkReceipt(r, path === "failure.json");
  const mode = text(receipt.mode);
  const dirs = [...new Set([...entries.keys()].filter(k => k.includes("/")).map(k => k.split("/")[0]))];
  if (!failed) requireThat(eq(dirs.sort(), ["frozen", "models", "result", ...(mode === "solve" ? ["calibration"] : []), ...(dirs.includes("instrument") ? ["instrument"] : [])].sort()), "completed exact directory inventory");
  else if (receipts["failure.json"]) {
    const durable = ["calibration", "frozen", "result", "models"], primary = dirs.filter(d => d !== "aborted");
    requireThat(dirs.includes("aborted") && eq(primary.slice().sort(), durable.slice(0, primary.length).sort()), "failed exact primary inventory");
    if (receipts["workflow.json"]) requireThat(primary.length === (receipts["workflow.json"].status === "completed" ? 4 : 1), "retained receipt inventory");
  } else requireThat(eq(dirs, ["calibration"]), "failed exact primary inventory");
  const admitted: Record<string, { payload: Obj; descriptors: Record<string, Descriptor>; offsets: Record<string, number>; manifestPath: string }> = Object.create(null);
  let logical = 0;
  for (const directory of dirs) { const [name, schema] = MANIFESTS[directory], path = `${directory}/${name}`, doc = jointJson(await read(path)); keys(doc, ["schema", "payload", "arrays"]); requireThat(doc.schema === schema, "native envelope schema");
    const payload = obj(doc.payload), descriptors = obj(doc.arrays), specs = specifications(directory, payload, descriptors), ds: Record<string, Descriptor> = Object.create(null);
    requireThat(eq([...entries.keys()].filter(k => k.startsWith(directory + "/")).sort(), [path, ...Object.keys(specs).map(k => `${directory}/${k}.npy`)].sort()), "whole exact file inventory");
    for (const [k, s] of Object.entries(specs)) { const d = descriptor(obj(descriptors[k])); requireThat(d.dtype === s.dtype && eq(d.shape, s.shape) && entries.get(`${directory}/${k}.npy`)?.size === d.file_bytes, "exact array descriptor"); logical += d.shape.reduce((a, b) => a * b, 1) * (d.dtype === "|b1" ? 1 : 8); requireThat(logical <= JOINT_IMPORT_CAP, "whole logical array cap"); ds[k] = d; }
    admitted[directory] = { payload, descriptors: ds, offsets: Object.create(null), manifestPath: path };
  }
  // Whole metadata admission, then ALL original headers, then hashes/values.
  for (const [dir, record] of Object.entries(admitted)) for (const [k, d] of Object.entries(record.descriptors)) { cancel(); const path = `${dir}/${k}.npy`; record.offsets[k] = header(await read(path), d); }
  const records: Record<string, NativeRecord> = Object.create(null);
  for (const [dir, record] of Object.entries(admitted)) { const arrays: Record<string, NativeArray> = Object.create(null);
    for (const [k, d] of Object.entries(record.descriptors)) { cancel(); const path = `${dir}/${k}.npy`, bytes = files.get(path)!, fileHash = await jointSha(bytes); requireThat(fileHash === d.file_sha256 && await jointSha(bytes.subarray(record.offsets[k])) === d.data_sha256, "original array digest mismatch"); hashes.set(path, fileHash); arrays[k] = decode(bytes, d, record.offsets[k]); }
    records[dir] = { payload: record.payload, arrays, manifestPath: record.manifestPath };
  }
  // read() copies each original buffer and no array is exposed until return.
  // Preserve the already computed actual file digest; never replace it with a
  // descriptor declaration. Export independently rehashes again before use.
  for (const [path, bytes] of files) { cancel(); if (!hashes.has(path)) hashes.set(path, await jointSha(bytes)); }
  const frozen = records.frozen ?? null, result = records.result ?? null, model = records.models ?? null, calibration = records.calibration ?? null, aborted = records.aborted ?? null;
  for (const record of [calibration, aborted]) if (record) {
    const p = record.payload, b = obj(p.optimizer_binding), digest = await jointSha(new TextEncoder().encode(stable(p.source_inventory)));
    requireThat(digest === b.source_inventory_sha256, "inventory declaration digest binding");
    const attempts = [...list(p[record === aborted ? "verified_candidates" : "candidates"]), ...(record === aborted && p.last_attempt !== null ? [p.last_attempt] : [])].map(v => obj(v));
    for (const c of attempts) requireThat(obj(c.identity).source_inventory_sha256 === digest, "attempt/source inventory binding");
    if (record === calibration) for (const c of attempts) { const id = obj(c.identity), a = obj(p.allocation_plan);
      requireThat(id.allocation_plan_sha256 === a.allocation_plan_sha256 && id.parameter_count === num(a.active_cells) * (c.modality === null ? 2 : 1), "attempt/allocation binding"); }
  }
  const candidates = checkLedger(calibration, aborted);
  if (!failed) { checkCompleted(receipt, frozen!, result!, model!, calibration, candidates); if (records.instrument) checkInstrument(records.instrument, frozen!, result!, model!, calibration, candidates, hashes); }
  else if (aborted) {
    const p = aborted.payload; requireThat(p.reason === receipt.reason && p.frozen_selection_created === !!frozen && (!p.sealed_values_read_started || !!frozen), "abort phase/reason binding");
    for (const record of [calibration, frozen, result, model]) if (record) for (const k of ["plan_sha256", "development_sha256"]) requireThat(record.payload[k] === p[k], "retained failure identity binding");
    if (frozen && calibration) requireThat(frozen.payload.selection_sha256 === calibration.payload.calibration_sha256 && sameValues(frozen.arrays.q, calibration.arrays.selection_q), "retained freeze selection binding");
    if (frozen) for (const record of [result, model]) if (record) for (const k of ["frozen_sha256", "origin", "selection_sha256", "physical_epochs", ...(record === result ? ["weights"] : [])]) requireThat(eq(record.payload[k], frozen.payload[k]), "retained frozen identity binding");
  } else requireThat(calibration?.payload.reason === receipt.reason && calibration.payload.calibration_sha256 === receipt.calibration_sha256, "failed baseline receipt binding");
  cancel(); return { schema: "joint-local-inspection-1", outcome: failed ? "failed" : "completed", mode, receipt,
    frozen: failed ? null : frozen, result: failed ? null : result, model: failed ? null : model, calibration, aborted, instrument: records.instrument ?? null,
    candidates, files, hashes, importedBytes: total, limitations: INSPECTION_FLAGS };
}

function candidate(record: NativeRecord, c: Obj, last: boolean): JointCandidate {
  const r = obj(c.result), prefix = last ? "last_" : `c${String(c.stage).padStart(2, "0")}_`, tr: Record<string, NativeArray> = Object.create(null);
  for (const k of [...STATES, ...STEPS]) tr[k] = record.arrays[prefix + k];
  const state = tr.models_q, n = state.shape[1], count = state.shape[0], scale = list(obj(c.identity).physical_scale).map(v => num(v));
  if (count) { const q = record.arrays[prefix + "q"].values;
    for (let j = 0; j < n; j++) requireThat(q[j] === state.values[(count - 1) * n + j], "terminal model/accepted state binding");
    for (const k of STATES.slice(1)) requireThat(r[k] === tr[k].values[count - 1], "terminal scalar/accepted state binding"); }
  const physical = last ? null : record.arrays[prefix + "physical_trace"], terms = last ? null : record.arrays[prefix + "terms_trace"];
  if (physical) for (let i = 0; i < physical.values.length; i++) requireThat(physical.values[i] === state.values[i] * scale[scale.length === 1 ? 0 : i % n < n / 2 ? 0 : 1], "state exact physical scaling");
  if (terms) for (let i = 0; i < count; i++) { const t = terms.values, w = weights(c.weights), regularization = num(w.beta_gravity) * t[i * 5 + 2] + num(w.beta_magnetic) * t[i * 5 + 3] + num(w.coupling) * t[i * 5 + 4], data = t[i * 5] + t[i * 5 + 1];
    requireThat(close(data + regularization, tr.phi_engine.values[i]) && close(data, tr.phi_d.values[i]) && close(regularization, tr.phi_m.values[i]), "recorded five terms/frozen strengths"); }
  if (!last) requireThat(c.stationarity_verified === (count > 0 && r.status === "converged" && tr.kkt_normalized.values[count - 1] <= 1e-5), "recorded stationarity declaration");
  for (let i = 0; i < count - 1; i++) { const branch = tr.branches.values[i], cg = tr.cg_residuals_available.values[i];
    requireThat((branch === 0 || branch === 1) && cg === branch && tr.line_search_counts.values[i] >= 1 && tr.line_search_counts.values[i] <= 30 && tr.line_search_alphas.values[i] === .5 ** (tr.line_search_counts.values[i] - 1), "recorded branch/line search");
    requireThat(tr.projected_slopes.values[i] < 0 && tr.armijo_margins.values[i] <= 0 && tr.cg_counts.values[i] >= 0 && tr.cg_counts.values[i] <= 512, "recorded accepted step");
    if (cg) requireThat(tr.cg_relative_residuals.values[i] >= 0 && tr.cg_relative_residuals.values[i] <= 1e-6, "recorded CG cap");
    else for (const k of ["cg_counts", "cg_abs_residuals", "cg_relative_residuals"]) requireThat(tr[k].values[i] === 0, "unavailable CG quantity"); }
  return { metadata: c, stage: integer(c.stage, 0, 25), modality: c.modality === null ? null : text(c.modality) as Modality, start: text(c.start_kind), weights: weights(c.weights), status: text(r.status), reason: text(r.reason), iterations: integer(r.iterations, 0, 250), writerReplayed: !last, trace: tr, physical, terms };
}
function checkLedger(calibration: NativeRecord | null, aborted: NativeRecord | null) {
  const candidates = calibration ? list(calibration.payload.candidates).map(c => candidate(calibration, obj(c), false)) : [];
  if (aborted) { const prefix = list(aborted.payload.verified_candidates).map(c => candidate(aborted, obj(c), false));
    if (calibration) {
      requireThat(eq(calibration.payload.candidates, aborted.payload.verified_candidates) && eq(calibration.payload.optimizer_binding, aborted.payload.optimizer_binding) && eq(calibration.payload.source_inventory, aborted.payload.source_inventory), "retained ledger/prefix binding");
      for (const [name, array] of Object.entries(calibration.arrays)) if (name !== "selection_q") requireThat(sameValues(array, aborted.arrays[name]), "retained ledger array binding");
    }
    const last = aborted.payload.last_attempt === null ? [] : [candidate(aborted, obj(aborted.payload.last_attempt), true)]; return [...prefix, ...last]; }
  return candidates;
}
function sameValues(a: NativeArray, b: NativeArray) { return eq(a.shape, b.shape) && a.values.every((v, i) => v === b.values[i]); }
function checkCompleted(receipt: Obj, frozen: NativeRecord, result: NativeRecord, model: NativeRecord, calibration: NativeRecord | null, candidates: JointCandidate[]) {
  for (const k of ["plan_sha256", "development_sha256", "frozen_sha256", "origin", "selection_sha256", "physical_epochs"]) requireThat(eq(frozen.payload[k], result.payload[k]) && eq(frozen.payload[k], model.payload[k]), "shared model/result/freeze identity");
  // input_bindings.development_sha256 hashes development alone; the compiled
  // identity hashes survey_request plus development. Do not equate them.
  requireThat(receipt.plan_sha256 === frozen.payload.plan_sha256 && receipt.frozen_sha256 === frozen.payload.frozen_sha256 && eq(result.payload.weights, frozen.payload.weights) && sameValues(frozen.arrays.q, result.arrays.q), "workflow/frozen result binding");
  const n = model.arrays.density_kg_m3.shape[0], q = frozen.arrays.q.values; requireThat(q.length === 2 * n, "physical property count binding");
  for (let i = 0; i < n; i++) requireThat(model.arrays.density_kg_m3.values[i] === q[i] * num(model.payload.density_scale) && model.arrays.susceptibility_si.values[i] === q[n + i] * num(model.payload.susceptibility_scale), "exact frozen physical property binding");
  checkGeometry(model);
  for (const m of MODALITIES) { const seen = new Set<number>(); for (const part of PARTITIONS) { const prefix = `${m}_${part}_`, a = result.arrays, metric = obj(obj(result.payload.metrics)[m])[part], v = obj(metric); let r2 = 0, w2 = 0;
    const rows = a[prefix + "rows"].values; rows.forEach((row, i) => { requireThat(Number.isInteger(row) && row >= 0 && row < 2048 && !seen.has(row) && (i === 0 || row > rows[i - 1]), "unique ordered original partition rows"); seen.add(row);
      const residual = a[prefix + "predicted"].values[i] - a[prefix + "observed"].values[i]; requireThat(residual === a[prefix + "signed_residual"].values[i], "predicted-minus-observed convention"); r2 += residual * residual; w2 += a[prefix + "whitened_residual"].values[i] ** 2; });
    requireThat(close(Math.sqrt(r2 / rows.length), num(v.rmse_physical)) && close(w2, num(v.chi_square)) && close(Math.sqrt(w2 / rows.length), num(v.wrms)), "inspection metric arithmetic"); }
  }
  if (calibration) {
    requireThat(receipt.mode === "solve" && calibration.payload.calibration_sha256 === receipt.calibration_sha256 && calibration.payload.calibration_sha256 === frozen.payload.selection_sha256 && calibration.payload.plan_sha256 === frozen.payload.plan_sha256 && calibration.payload.development_sha256 === frozen.payload.development_sha256 && frozen.payload.origin === "optimized_selection", "actual calibration declaration binding");
    const selection = obj(calibration.payload.selection); requireThat(eq(selection.weights, frozen.payload.weights) && sameValues(calibration.arrays.selection_q, frozen.arrays.q), "selected frozen model binding");
    const baselines = obj(calibration.payload.selected_baselines); keys(baselines, [...MODALITIES]); const baseline: Record<string, JointCandidate> = {};
    for (const m of MODALITIES) { const entries = candidates.filter(c => c.modality === m && c.metadata.stationarity_verified === true);
      entries.sort((a, b) => num(obj(a.metadata.validation_wrms)[m]) - num(obj(b.metadata.validation_wrms)[m]) || num(b.weights["beta_" + m]) - num(a.weights["beta_" + m]) || a.stage - b.stage);
      requireThat(entries.length > 0 && baselines[m] === entries[0].stage, "independent validation baseline selection"); baseline[m] = entries[0]; }
    const bwrms = obj(selection.baseline_validation_wrms); for (const m of MODALITIES) requireThat(bwrms[m] === obj(baseline[m].metadata.validation_wrms)[m], "uncoupled baseline validation binding");
    const positives = candidates.slice(16).filter(c => { requireThat(c.weights.beta_gravity === baseline.gravity.weights.beta_gravity && c.weights.beta_magnetic === baseline.magnetic.weights.beta_magnetic, "joint frozen baseline strengths");
      const wrms = obj(c.metadata.validation_wrms), eligible = c.metadata.stationarity_verified === true && MODALITIES.every(m => num(wrms[m]) <= 1.05 * num(bwrms[m])); requireThat(c.metadata.eligible === eligible, "literal candidate eligibility"); return eligible; });
    positives.sort((a, b) => { const score = (c: JointCandidate) => (num(obj(c.metadata.validation_wrms).gravity) ** 2 + num(obj(c.metadata.validation_wrms).magnetic) ** 2) / 2; return score(a) - score(b) || num(a.weights.coupling) - num(b.weights.coupling) || (a.start === "baseline" ? 0 : 1) - (b.start === "baseline" ? 0 : 1) || a.stage - b.stage; });
    requireThat(selection.stage === (positives[0]?.stage ?? null) && calibration.payload.reason === (positives.length ? "validated_coupled_selection" : "no_validated_coupling_benefit"), "frozen exact selection policy");
    const selected = positives[0]; if (selected) { const qlast = selected.trace.models_q; for (let i = 0; i < q.length; i++) requireThat(q[i] === qlast.values[(qlast.shape[0] - 1) * q.length + i], "selected actual state"); }
    else for (const [j, m] of MODALITIES.entries()) { const a = baseline[m].trace.models_q; for (let i = 0; i < n; i++) requireThat(q[j * n + i] === a.values[(a.shape[0] - 1) * n + i], "lambda0 actual pair no refit"); }
  } else requireThat(receipt.mode === "evaluate" && receipt.calibration_sha256 === null, "evaluation is not inversion");
}
function checkGeometry(model: NativeRecord) {
  const a = model.arrays, widths = [a.mesh_hx_m.values, a.mesh_hy_m.values, a.mesh_hz_m.values], origin = a.mesh_origin_m.values;
  const edges = widths.map((w, axis) => { let value = origin[axis]; const out = [value]; for (const dx of w) { requireThat(dx >= .001 && dx <= 1e5, "native positive mesh width"); value += dx; out.push(value); } return out; });
  const nx = widths[0].length, ny = widths[1].length, nz = widths[2].length, ids = a.active_full_indices.values;
  ids.forEach((id, i) => { requireThat(id >= 0 && id < nx * ny * nz && (i === 0 || id > ids[i - 1]), "x-fast active index"); const xyz = [id % nx, Math.floor(id / nx) % ny, Math.floor(id / (nx * ny))]; let volume = 1;
    xyz.forEach((cell, axis) => { const lo = edges[axis][cell], hi = edges[axis][cell + 1]; requireThat(close(a.active_cell_bounds_m.values[6 * i + 2 * axis], lo) && close(a.active_cell_bounds_m.values[6 * i + 2 * axis + 1], hi) && close(a.active_cell_centres_m.values[3 * i + axis], (lo + hi) / 2), "native active geometry binding"); volume *= widths[axis][cell]; });
    requireThat(close(a.active_cell_volumes_m3.values[i], volume), "native cell volume binding"); });
}

export function jointResponse(result: JointInspection, modality: Modality, partition: Partition) {
  requireThat(result.outcome === "completed" && result.result, "no completed response on failure"); const a = result.result.arrays, prefix = `${modality}_${partition}_`;
  return { rows: a[prefix + "rows"].values, observed: a[prefix + "observed"].values, predicted: a[prefix + "predicted"].values,
    residual: a[prefix + "signed_residual"].values, whitened: a[prefix + "whitened_residual"].values, unit: modality === "gravity" ? "mGal" : "nT" };
}
function checkInstrument(instrument: NativeRecord, frozen: NativeRecord, result: NativeRecord, model: NativeRecord,
  calibration: NativeRecord | null, candidates: JointCandidate[], hashes: ReadonlyMap<string, string>) {
  const p = instrument.payload, a = instrument.arrays, originals = obj(p.original_file_sha256);
  const paths = [...hashes.keys()].filter(k => !k.startsWith("instrument/")); keys(originals, paths);
  for (const path of paths) requireThat(originals[path] === hashes.get(path), "instrument original byte binding");
  for (const key of ["plan_sha256", "development_sha256", "frozen_sha256", "physical_epochs"]) requireThat(eq(p[key], frozen.payload[key]), "instrument frozen identity binding");
  requireThat(p.calibration_sha256 === (calibration?.payload.calibration_sha256 ?? null), "instrument calibration binding");
  const n = model.arrays.density_kg_m3.shape[0], totalVolume = Array.from(model.arrays.active_cell_volumes_m3.values).reduce((x, y) => x + y, 0);
  requireThat(close(num(p.coupling_factor), num(p.coupling_length_m) ** 4 / totalVolume), "instrument actual volume factor");
  for (const value of list(p.entries)) { const e = obj(value), key = text(e.key), count = num(e.state_count), c = e.kind === "candidate" ? candidates[num(e.stage)] : null;
    if (c) requireThat(count === c.trace.models_q.shape[0] && eq(e.weights, c.weights) && e.modality === c.modality, "instrument candidate/frame binding");
    if (key === "selected") requireThat(eq(e.weights, frozen.payload.weights), "instrument selected strengths");
    if (key === "baseline") { requireThat(calibration, "baseline calibration required"); const b = obj(calibration.payload.selected_baselines), w = obj(e.weights);
      requireThat(w.coupling === 0 && w.beta_gravity === candidates[num(b.gravity)].weights.beta_gravity && w.beta_magnetic === candidates[num(b.magnetic)].weights.beta_magnetic, "instrument independent baseline strengths"); }
    for (const m of e.modality === null ? MODALITIES : [e.modality as Modality]) for (const part of PARTITIONS) {
      const prefix = `${key}_${m}_${part}_`, original = result.arrays[`${m}_${part}_observed`].values, rows = original.length;
      requireThat(a[prefix + "predicted"].shape[1] === rows, "instrument original partition shape");
      for (let i = 0; i < count; i++) { let r2 = 0, w2 = 0;
        for (let j = 0; j < rows; j++) { const offset = i * rows + j, residual = a[prefix + "predicted"].values[offset] - original[j];
          requireThat(residual === a[prefix + "signed_residual"].values[offset], "historical signed residual convention"); r2 += residual ** 2; w2 += a[prefix + "whitened_residual"].values[offset] ** 2;
          if (key === "selected") for (const name of ["predicted", "signed_residual", "whitened_residual"]) requireThat(a[prefix + name].values[offset] === result.arrays[`${m}_${part}_${name}`].values[j], "historical selected response binding"); }
        const metric = a[prefix + "metrics"].values;
        requireThat(close(metric[i * 3], Math.sqrt(r2 / rows)) && close(metric[i * 3 + 1], Math.sqrt(w2 / rows)) && close(metric[i * 3 + 2], w2), "historical partition metric arithmetic");
        if (c && part === "validation" && i === count - 1) requireThat(close(metric[i * 3 + 1], num(obj(c.metadata.validation_wrms)[m])), "historical terminal validation binding");
      }
    }
    if (e.modality === null) { requireThat(a[key + "_face_contribution"].shape[1] === n, "historical native coupling cells");
      for (let i = 0; i < count; i++) { let sum = 0;
        for (let j = 0; j < n; j++) { const offset = i * n + j, density = a[key + "_gram_density"].values[offset], susceptibility = a[key + "_gram_susceptibility"].values[offset], product = a[key + "_gram_product"].values[offset], contribution = a[key + "_face_contribution"].values[offset];
          requireThat(density >= 0 && susceptibility >= 0 && close(contribution, num(p.coupling_factor) * (density * susceptibility - product * product)), "historical exact face Gram arithmetic"); sum += contribution; }
        if (c) requireThat(close(sum, c.terms!.values[i * 5 + 4]), "historical coupling/term binding");
        if (key === "selected") requireThat(close(sum, num(obj(result.payload.terms).coupling)), "selected exact coupling binding");
      }
    }
  }
}

/** Frames are offline-exported data, never browser kernel estimates. */
export function jointInstrumentFrame(inspection: JointInspection, key: string, state: number) {
  requireThat(inspection.outcome === "completed" && inspection.instrument && inspection.model && inspection.result, "native accepted-state supplement required");
  const instrument = inspection.instrument, entry = list(instrument.payload.entries).map(obj).find(e => e.key === key);
  requireThat(entry && Number.isInteger(state) && state >= 0 && state < num(entry.state_count), "exact instrument frame index");
  const a = instrument.arrays, model = inspection.model, n = model.arrays.density_kg_m3.shape[0], candidate = entry.kind === "candidate" ? inspection.candidates[num(entry.stage)] : null;
  const geometry = Object.fromEntries(Object.entries(model.arrays).filter(([k]) => !["density_kg_m3", "susceptibility_si"].includes(k)));
  const properties: Record<string, NativeArray> = {};
  if (key === "selected") for (const name of ["density_kg_m3", "susceptibility_si"]) properties[name] = model.arrays[name];
  else if (key === "baseline") { const b = obj(inspection.calibration!.payload.selected_baselines);
    for (const [m, name] of [["gravity", "density_kg_m3"], ["magnetic", "susceptibility_si"]] as const) { const c = inspection.candidates[num(b[m])]; properties[name] = { dtype: "<f8", shape: [n], values: c.physical!.values.slice(c.iterations * n, (c.iterations + 1) * n) }; } }
  else if (candidate) { requireThat(candidate.physical, "actual physical trace required"); const values = candidate.physical.values, width = candidate.physical.shape[1];
    if (candidate.modality !== "magnetic") properties.density_kg_m3 = { dtype: "<f8", shape: [n], values: values.slice(state * width, state * width + n) };
    if (candidate.modality !== "gravity") { const offset = state * width + (candidate.modality === null ? n : 0); properties.susceptibility_si = { dtype: "<f8", shape: [n], values: values.slice(offset, offset + n) }; } }
  const responses: Partial<Record<Modality, Record<Partition, ReturnType<typeof jointResponse> & { metrics: { rmse_physical: number; wrms: number; chi_square: number; count: number } }>>> = {};
  for (const m of entry.modality === null ? MODALITIES : [entry.modality as Modality]) { responses[m] = {} as NonNullable<typeof responses[Modality]>;
    for (const part of PARTITIONS) { const original = jointResponse(inspection, m, part), prefix = `${key}_${m}_${part}_`, rows = original.rows.length, metric = a[prefix + "metrics"].values;
      responses[m]![part] = { ...original, predicted: a[prefix + "predicted"].values.subarray(state * rows, (state + 1) * rows), residual: a[prefix + "signed_residual"].values.subarray(state * rows, (state + 1) * rows), whitened: a[prefix + "whitened_residual"].values.subarray(state * rows, (state + 1) * rows),
        metrics: { count: rows, rmse_physical: metric[state * 3], wrms: metric[state * 3 + 1], chi_square: metric[state * 3 + 2] } }; } }
  const coupling = entry.modality === null ? Object.fromEntries(GRAM.map(name => [name, Array.from(a[key + "_" + name].values.subarray(state * n, (state + 1) * n))])) : null;
  return { key, state, entry, model: { arrays: { ...geometry, ...properties } }, responses, coupling, candidate,
    historical_sealed_use: "post_freeze_diagnostic_only", weights: entry.weights };
}
/** Display endpoints from actual values, with no constant-range padding. */
export function jointPhysicalRange(values: Float64Array | Uint8Array, signed: boolean): [number, number] {
  requireThat(values.length > 0, "nonempty physical range"); let lo = Infinity, hi = -Infinity;
  for (const value of values) { requireThat(Number.isFinite(value), "finite physical range"); lo = Math.min(lo, value); hi = Math.max(hi, value); }
  if (signed) { const magnitude = Math.max(Math.abs(lo), Math.abs(hi)); return [-magnitude, magnitude]; }
  return [lo, hi];
}
export function jointState(c: JointCandidate, state: number) {
  requireThat(Number.isSafeInteger(state) && state >= 0 && state < c.trace.models_q.shape[0], "recorded state index"); const n = c.trace.models_q.shape[1];
  return { stage: c.stage, state, weights: c.weights, terminal_status: c.status, terminal_reason: c.reason,
    objective_identity: c.metadata.identity,
    terminal_metrics_apply: state === c.trace.models_q.shape[0] - 1, writer_declares_scientific_replay_completed: c.writerReplayed,
    q: Array.from(c.trace.models_q.values.slice(state * n, (state + 1) * n)),
    physical: c.physical ? Array.from(c.physical.values.slice(state * n, (state + 1) * n)) : null,
    terms: c.terms ? Object.fromEntries(TERM_NAMES.map((k, i) => [k, c.terms!.values[state * 5 + i]])) : null,
    objective: c.trace.phi_engine.values[state], kkt_normalized: c.trace.kkt_normalized.values[state], historical_prediction: null,
    preceding_step: state === 0 ? null : Object.fromEntries(STEPS.map(k => [k, k === "cg_residuals_available" ? !!c.trace[k].values[state - 1] : !c.trace.cg_residuals_available.values[state - 1] && ["cg_counts", "cg_abs_residuals", "cg_relative_residuals"].includes(k) ? null : c.trace[k].values[state - 1]])) };
}
export function jointSidecar(inspection: JointInspection, modality: Modality, partition: Partition, row: number, cell: number, attemptIndex: number, state: number) {
  const response = inspection.outcome === "completed" ? jointResponse(inspection, modality, partition) : null;
  if (response) requireThat(Number.isInteger(row) && row >= 0 && row < response.rows.length, "receiver index");
  if (inspection.model) requireThat(Number.isInteger(cell) && cell >= 0 && cell < inspection.model.arrays.density_kg_m3.shape[0], "active cell index");
  return { schema: "joint-inspection-sidecar-1", ...INSPECTION_FLAGS, original_file_sha256: Object.fromEntries(inspection.hashes), outcome: inspection.outcome,
    workflow_declaration: inspection.receipt, residual_convention: "predicted_minus_observed",
    selected_response: response ? { modality, partition, row: response.rows[row], unit: response.unit, observed: response.observed[row], predicted: response.predicted[row], signed_residual: response.residual[row], marginal_whitened_coordinate: response.whitened[row] } : null,
    selected_cell: inspection.model ? { active_index: cell, full_index: inspection.model.arrays.active_full_indices.values[cell],
      density_kg_m3: inspection.model.arrays.density_kg_m3.values[cell], susceptibility_si: inspection.model.arrays.susceptibility_si.values[cell],
      centre_m: Array.from(inspection.model.arrays.active_cell_centres_m.values.slice(cell * 3, cell * 3 + 3)), bounds_m: Array.from(inspection.model.arrays.active_cell_bounds_m.values.slice(cell * 6, cell * 6 + 6)), volume_m3: inspection.model.arrays.active_cell_volumes_m3.values[cell] } : null,
    selected_attempt_state: inspection.candidates[attemptIndex]?.trace.models_q.shape[0] ? jointState(inspection.candidates[attemptIndex], state) : null,
    selected_native_frame: inspection.instrument && (!inspection.candidates[attemptIndex] || inspection.candidates[attemptIndex].trace.models_q.shape[0] > 0) ? jointFrameSidecar(inspection, inspection.candidates[attemptIndex] ? `c${String(inspection.candidates[attemptIndex].stage).padStart(2, "0")}` : "selected", state) : null };
}
export function jointFrameSidecar(inspection: JointInspection, key: string, state: number) {
  const frame = jointInstrumentFrame(inspection, key, state);
  return { key, state, ...INSPECTION_FLAGS, original_file_sha256: Object.fromEntries(inspection.hashes), weights: frame.weights,
    historical_sealed_use: frame.historical_sealed_use, entry: frame.entry,
    original_frozen_context: inspection.frozen!.payload, original_selected_q: Array.from(inspection.frozen!.arrays.q.values),
    candidate_state: frame.candidate ? jointState(frame.candidate, state) : null,
    selection_context: inspection.calibration ? { reason: inspection.calibration.payload.reason, selected_baselines: inspection.calibration.payload.selected_baselines, selection: inspection.calibration.payload.selection, lambda0_refitted: false } : null,
    frame_property_units: { density_kg_m3: "kg_m3", susceptibility_si: "si", active_cell_centres_m: "m", active_cell_bounds_m: "m", active_cell_volumes_m3: "m3", face_contribution: "dimensionless" },
    original_geometry_context: inspection.model!.payload, exporter_source_inventory: inspection.instrument!.payload.exporter_source_inventory,
    original_physical_and_optimizer_source_inventory: inspection.calibration?.payload.source_inventory ?? null,
    model: Object.fromEntries(Object.entries(frame.model.arrays).map(([k, v]) => [k, { dtype: v.dtype, shape: v.shape, values: Array.from(v.values) }])),
    responses: Object.fromEntries(Object.entries(frame.responses).map(([m, partitions]) => [m, Object.fromEntries(Object.entries(partitions!).map(([p, r]) => [p,
      { ...r, rows: Array.from(r.rows), observed: Array.from(r.observed), predicted: Array.from(r.predicted), residual: Array.from(r.residual), whitened: Array.from(r.whitened) }]))])), coupling: frame.coupling };
}
export async function exportJointOriginals(inspection: JointInspection): Promise<Uint8Array> {
  const archive: Zippable = Object.create(null); for (const [path, bytes] of inspection.files) { requireThat(await jointSha(bytes) === inspection.hashes.get(path), "original changed before private export"); archive[path] = [bytes, { level: 0 }]; }
  return new Promise((resolve, reject) => zip(archive, { level: 0 }, (error, bytes) => error ? reject(error) : resolve(bytes)));
}
export function browserJointFiles(files: FileList | File[]): JointFile[] {
  return Array.from(files, file => ({ path: file.webkitRelativePath || file.name, size: file.size, read: async () => new Uint8Array(await file.arrayBuffer()) }));
}
