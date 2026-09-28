/** Browser boundary for the frozen 100 Hz, 60 s ENZ M13 picker. */
export const PHASE_SAMPLES = 6000;
export const PHASE_RATE_HZ = 100;
export const PHASE_THRESHOLD = 0.8;
export const PHASE_SEPARATION_SAMPLES = 40;
const CHANNELS = ["E", "N", "Z"] as const;
const SHA256 = /^[0-9a-f]{64}$/;

export type Representation = "counts" | "normalized";
export type Channels = readonly [Float32Array, Float32Array, Float32Array];
export interface PhaseTrace {
  traceId: string;
  source: string;
  representation: Representation;
  channels: Channels;
  input: Float32Array;
  startUtc?: string;
}
export interface PhaseScores {
  probabilities: Float32Array;
  peaks: { P: number; S: number };
  picks: { P: number | null; S: number | null };
  reasons: { P: "accepted" | "below-threshold"; S: "accepted" | "below-threshold" | "ps-separation" };
}
export interface PhaseManifestEntry {
  trace_id: string;
  status: "qc-valid" | "qc-rejected";
  category: "earthquake_local" | "noise";
  network: string;
  station_id: string;
  channel: string;
  analyst_p_s: number | null;
  analyst_s_s: number | null;
  reference_is_ground_truth: false;
  waveform_file?: string;
  waveform_sha256?: string;
  waveform_bytes?: 72000;
  qc_reason?: string;
}
export interface PhaseManifest {
  schema: "caos.phase-browser-assets.v1";
  status: string;
  browser_parity_verified: boolean;
  model: { file: string; sha256: string; checkpoint_sha256: string; bytes: number };
  benchmark: { file: string; sha256: string; selected: 6000; qc_valid: number; tolerance_s: number; reference: string };
  selection: { selected: 24; qc_valid: 23; qc_rejected: 1; full_benchmark_selected: 6000; selected_before_heldout_scoring: true };
  input: { sample_rate_hz: 100; samples: 6000; component_order: ["E", "N", "Z"];
    shape: [1, 3, 6000]; file_dtype: "float32-little-endian"; file_layout: string; unit: string };
  output: { shape: [1, 3, 6000]; classes: ["N", "P", "S"] };
  source: { dataset: string; citation: string; authors: string; doi: string; license: string;
    license_url: string; original_url: string; mirror_url: string; modification: string };
  records: PhaseManifestEntry[];
}
export interface PhaseBenchmarkRow {
  f1_at_0p5s: number;
  correct_within_0p5s: number;
  reference_count: number;
  timing_absolute_median_s: number | null;
  valid_noise_false_pick_rate: number;
}
export interface PhaseBenchmark {
  selected: 6000;
  valid: number;
  qc_rejected: number;
  reference: string;
  nominal: { M08: { P: PhaseBenchmarkRow; S: PhaseBenchmarkRow };
    M13: { P: PhaseBenchmarkRow; S: PhaseBenchmarkRow } };
}

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}
function string(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a nonempty string`);
  return value;
}
function hash(value: unknown, label: string): string {
  const result = string(value, label);
  if (!SHA256.test(result)) throw new Error(`${label} must be a lowercase SHA-256 hex digest`);
  return result;
}
function filename(value: unknown, label: string): string {
  const result = string(value, label);
  if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(result) || result === "." || result === "..")
    throw new Error(`${label} must be a file in the manifest directory`);
  return result;
}
function utc(value: unknown): string | undefined {
  if (value === undefined) return undefined;
  const result = string(value, "start_utc");
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z$/.test(result) || !Number.isFinite(Date.parse(result)))
    throw new Error("start_utc must be an ISO-8601 UTC instant");
  return result;
}
function optionalArrival(value: unknown, label: string): number | null {
  if (value === null) return null;
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 59.99)
    throw new Error(`${label} must be a relative time inside the 60 s window or null`);
  return value;
}
function checkedChannels(channels: unknown, label: string): [number[], number[], number[]] {
  const source = object(channels, label);
  if (Object.keys(source).sort().join(",") !== "E,N,Z") throw new Error("Exactly E, N and Z measured components are required");
  const arrays = CHANNELS.map(name => {
    const values = source[name];
    if (!Array.isArray(values) || values.length !== PHASE_SAMPLES)
      throw new Error(`${name} must contain exactly ${PHASE_SAMPLES} samples`);
    if (!values.every(value => typeof value === "number" && Number.isFinite(value) && Number.isFinite(Math.fround(value))))
      throw new Error(`${name} contains a nonfinite or non-float32 sample`);
    return values as number[];
  }) as [number[], number[], number[]];
  for (let c = 0; c < 3; c++) {
    const first = Math.fround(arrays[c][0]);
    if (arrays[c].every(value => Math.fround(value) === first))
      throw new Error(`${CHANNELS[c]} is flat at model input precision; three measured components are required`);
    for (let d = 0; d < c; d++)
      if (arrays[c].every((value, i) => Math.fround(value) === Math.fround(arrays[d][i])))
        throw new Error(`${CHANNELS[c]} duplicates ${CHANNELS[d]} at model input precision; missing channels cannot be filled`);
  }
  return arrays;
}

/** Mirrors normalize_counts: float64 mean, then float32 sample/mean/subtraction/peak/division. */
export function normalizeCounts(channels: readonly number[][]): Channels {
  const normalized = channels.map(values => {
    const mean = values.reduce((sum, value) => sum + value, 0) / PHASE_SAMPLES;
    const centered = Float32Array.from(values, value => Math.fround(Math.fround(value) - Math.fround(mean)));
    let peak = 0;
    for (const value of centered) peak = Math.max(peak, Math.abs(value));
    if (!(peak > 0)) throw new Error("A component is flat after float32 centering");
    return Float32Array.from(centered, value => Math.fround(value / peak));
  });
  return normalized as [Float32Array, Float32Array, Float32Array];
}

function makeTrace(traceId: string, source: string, representation: Representation,
                   channelValues: [number[], number[], number[]], startUtc?: string): PhaseTrace {
  const channels = channelValues.map(values => Float32Array.from(values)) as [Float32Array, Float32Array, Float32Array];
  const normalized = representation === "counts" ? normalizeCounts(channelValues) : channels;
  if (representation === "normalized") for (const channel of normalized) {
    let peak = 0;
    for (const value of channel) peak = Math.max(peak, Math.abs(value));
    if (peak < 0.999 || peak > 1.001) throw new Error("Normalized components must have unit absolute peak; do not normalize them twice");
  }
  const input = new Float32Array(3 * PHASE_SAMPLES);
  normalized.forEach((values, channel) => input.set(values, channel * PHASE_SAMPLES));
  return { traceId, source, representation, channels, input, startUtc };
}

export function parseLocalTrace(value: unknown): PhaseTrace {
  const data = object(value, "trace");
  if (data.schema !== "caos.phase-browser-trace.v1") throw new Error("Unsupported trace schema");
  if (data.sample_rate_hz !== PHASE_RATE_HZ) throw new Error("Only 100 Hz records are supported; no browser resampling is performed");
  if (JSON.stringify(data.component_order) !== JSON.stringify(CHANNELS)) throw new Error("Component order must be E, N, Z");
  const representation = data.representation;
  if (representation !== "counts" && representation !== "normalized") throw new Error("Representation must be counts or normalized");
  if (data.unit !== (representation === "counts" ? "counts" : "dimensionless"))
    throw new Error("Input unit does not match the declared representation");
  const qc = object(data.qc, "qc");
  if (qc.components_measured !== true || qc.gaps !== false || qc.clipped !== false || qc.response_corrected !== false)
    throw new Error("Unsupported channel QC: require three measured, gap-free, unclipped, unrestituted channels");
  return makeTrace(string(data.trace_id, "trace_id"), string(data.source, "source"), representation,
    checkedChannels(data.channels, "channels"), utc(data.start_utc));
}

export function parsePhaseManifest(value: unknown): PhaseManifest {
  const data = object(value, "manifest");
  const input = object(data.input, "input");
  const output = object(data.output, "output");
  const selection = object(data.selection, "selection");
  if (data.schema !== "caos.phase-browser-assets.v1" || input.sample_rate_hz !== PHASE_RATE_HZ ||
      input.samples !== PHASE_SAMPLES || JSON.stringify(input.component_order) !== JSON.stringify(CHANNELS) ||
      JSON.stringify(input.shape) !== "[1,3,6000]" || input.file_dtype !== "float32-little-endian" ||
      input.file_layout !== "component-major; 6000 consecutive samples per component" ||
      input.unit !== "dimensionless normalized instrument counts" ||
      JSON.stringify(output.shape) !== "[1,3,6000]" || JSON.stringify(output.classes) !== '["N","P","S"]')
    throw new Error("Unsupported M13 asset manifest schema, rate, component order or tensor layout");
  if (data.browser_parity_verified !== false && data.browser_parity_verified !== true)
    throw new Error("Manifest browser parity status is missing");
  if (selection.selected !== 24 || selection.qc_valid !== 23 || selection.qc_rejected !== 1 ||
      selection.full_benchmark_selected !== 6000 || selection.selected_before_heldout_scoring !== true)
    throw new Error("Manifest does not retain the predeclared 24-trace browser selection");
  const model = object(data.model, "model");
  const parsedModel = {
    file: filename(model.file, "model.file"), sha256: hash(model.sha256, "model.sha256"),
    checkpoint_sha256: hash(model.checkpoint_sha256, "model.checkpoint_sha256"),
    bytes: Number(model.bytes),
  };
  const thresholds = object(model.thresholds, "model thresholds");
  if (thresholds.P !== PHASE_THRESHOLD || thresholds.S !== PHASE_THRESHOLD ||
      !Number.isSafeInteger(parsedModel.bytes) || parsedModel.bytes <= 0)
    throw new Error("Manifest model size or thresholds do not match the browser contract");
  const benchmark = object(data.benchmark, "benchmark");
  const parsedBenchmark = {
    file: filename(benchmark.file, "benchmark.file"), sha256: hash(benchmark.sha256, "benchmark.sha256"),
    selected: benchmark.selected as 6000, qc_valid: Number(benchmark.qc_valid),
    tolerance_s: Number(benchmark.tolerance_s), reference: string(benchmark.reference, "benchmark reference"),
  };
  if (parsedBenchmark.selected !== 6000 || !Number.isSafeInteger(parsedBenchmark.qc_valid) ||
      parsedBenchmark.qc_valid < 0 || parsedBenchmark.qc_valid > 6000 || parsedBenchmark.tolerance_s !== 0.5)
    throw new Error("Full benchmark population or tolerance differs from the fixed contract");
  const source = object(data.source, "source");
  const parsedSource = {
    dataset: string(source.dataset, "source.dataset"), citation: string(source.citation, "source.citation"),
    authors: string(source.authors, "source.authors"), doi: string(source.doi, "source.doi"),
    license: string(source.license, "source.license"), license_url: string(source.license_url, "source.license_url"),
    original_url: string(source.original_url, "source.original_url"),
    mirror_url: string(source.mirror_url, "source.mirror_url"), modification: string(source.modification, "source.modification"),
  };
  if (!Array.isArray(data.records) || data.records.length !== 24) throw new Error("The fixed browser selection must retain all 24 entries");
  const ids = new Set<string>();
  const records = data.records.map((unknownEntry): PhaseManifestEntry => {
    const entry = object(unknownEntry, "trace entry");
    const trace_id = string(entry.trace_id, "trace_id");
    if (ids.has(trace_id)) throw new Error("Duplicate browser trace identity");
    ids.add(trace_id);
    const common = {
      trace_id, network: string(entry.network, "network"), station_id: string(entry.station_id, "station_id"),
      channel: string(entry.channel, "channel"),
      category: entry.category as "earthquake_local" | "noise",
      analyst_p_s: optionalArrival(entry.analyst_p_s, "analyst P"),
      analyst_s_s: optionalArrival(entry.analyst_s_s, "analyst S"),
      reference_is_ground_truth: false as const,
    };
    if (!(["earthquake_local", "noise"] as unknown[]).includes(entry.category) || entry.reference_is_ground_truth !== false)
      throw new Error("Trace category or analyst-reference meaning is invalid");
    if (entry.status === "qc-valid") return {
      ...common, status: "qc-valid",
      waveform_file: filename(entry.waveform_file, "waveform_file"),
      waveform_sha256: hash(entry.waveform_sha256, "waveform_sha256"),
      waveform_bytes: entry.waveform_bytes as 72000,
    };
    if (entry.status === "qc-rejected" && entry.waveform_file === undefined && entry.waveform_sha256 === undefined && entry.waveform_bytes === undefined) return {
      ...common, status: "qc-rejected", qc_reason: string(entry.qc_reason, "QC reason"),
    };
    throw new Error("QC-failed entries cannot include waveform bytes or become inference inputs");
  });
  if (records.some(entry => entry.status === "qc-valid" && entry.waveform_bytes !== 72000) ||
      records.filter(entry => entry.status === "qc-valid").length !== 23 ||
      records.filter(entry => entry.status === "qc-rejected").length !== 1)
    throw new Error("The fixed browser selection must retain 23 valid traces and one QC failure");
  return { schema: "caos.phase-browser-assets.v1", status: string(data.status, "status"),
    browser_parity_verified: data.browser_parity_verified as boolean,
    model: parsedModel, benchmark: parsedBenchmark,
    selection: { selected: 24, qc_valid: 23, qc_rejected: 1, full_benchmark_selected: 6000, selected_before_heldout_scoring: true },
    input: { sample_rate_hz: 100, samples: 6000, component_order: ["E", "N", "Z"], shape: [1,3,6000],
      file_dtype: "float32-little-endian", file_layout: input.file_layout as string, unit: input.unit as string },
    output: { shape: [1,3,6000], classes: ["N","P","S"] }, source: parsedSource, records };
}

export function parseNormalizedF32(bytes: ArrayBuffer, entry: PhaseManifestEntry): PhaseTrace {
  if (entry.status !== "qc-valid") throw new Error("QC-failed entry has no waveform to infer");
  if (bytes.byteLength !== 3 * PHASE_SAMPLES * 4) throw new Error("Normalized trace must contain exactly 18,000 float32 samples");
  const view = new DataView(bytes);
  const arrays = CHANNELS.map((_, c) => Array.from({ length: PHASE_SAMPLES }, (_, i) =>
    view.getFloat32((c * PHASE_SAMPLES + i) * 4, true))) as [number[], number[], number[]];
  return makeTrace(entry.trace_id, `${entry.station_id} · ${entry.network}/${entry.channel} · STEAD`, "normalized",
    checkedChannels({ E: arrays[0], N: arrays[1], Z: arrays[2] }, "waveform"));
}

export function parsePhaseBenchmark(value: unknown, manifest: PhaseManifest): PhaseBenchmark {
  const data = object(value, "benchmark");
  if (data.schema !== "caos.stead-phase-heldout-benchmark.v1" ||
      data.checkpoint_sha256 !== manifest.model.checkpoint_sha256 ||
      data.selected !== 6000 || data.valid !== manifest.benchmark.qc_valid ||
      data.qc_rejected !== 6000 - manifest.benchmark.qc_valid ||
      data.tolerance_s !== 0.5 || data.metrics_include_qc_failures_as_unpicked !== true)
    throw new Error("Held-out benchmark population, checkpoint or QC denominator differs from manifest");
  const metrics = object(data.metrics, "metrics");
  const nominal = object(metrics.nominal, "nominal metrics");
  function row(method: "M08" | "M13", phase: "P" | "S"): PhaseBenchmarkRow {
    const source = object(object(nominal[method], method)[phase], `${method} ${phase}`);
    const f1 = Number(source.f1_at_0p5s), correct = Number(source.correct_within_0p5s);
    const referenceCount = Number(source.reference_count), median = source.timing_absolute_median_s;
    const falseRate = Number(source.valid_noise_false_pick_rate);
    if (![f1, correct, referenceCount, falseRate].every(Number.isFinite) ||
        f1 < 0 || f1 > 1 || correct < 0 || correct > referenceCount || referenceCount < 0 ||
        falseRate < 0 || falseRate > 1 ||
        (median !== null && (typeof median !== "number" || !Number.isFinite(median) || median < 0)))
      throw new Error(`Invalid ${method} ${phase} held-out metric`);
    return { f1_at_0p5s: f1, correct_within_0p5s: correct, reference_count: referenceCount,
      timing_absolute_median_s: median as number | null, valid_noise_false_pick_rate: falseRate };
  }
  return { selected: 6000, valid: data.valid as number, qc_rejected: data.qc_rejected as number,
    reference: string(data.reference, "benchmark reference"),
    nominal: { M08: { P: row("M08", "P"), S: row("M08", "S") },
      M13: { P: row("M13", "P"), S: row("M13", "S") } } };
}

export function validateProbabilities(values: Float32Array, dims: readonly number[]): PhaseScores {
  if (dims.length !== 3 || dims[0] !== 1 || dims[1] !== 3 || dims[2] !== PHASE_SAMPLES || values.length !== 3 * PHASE_SAMPLES)
    throw new Error("ONNX output must be [1,3,6000] N/P/S probabilities");
  const peaks = { P: 0, S: 0 };
  const indices = { P: 0, S: 0 };
  for (let i = 0; i < PHASE_SAMPLES; i++) {
    const n = values[i], p = values[PHASE_SAMPLES + i], s = values[2 * PHASE_SAMPLES + i];
    if (![n, p, s].every(value => Number.isFinite(value) && value >= 0 && value <= 1) || Math.abs(n + p + s - 1) > 1e-3)
      throw new Error(`Invalid N/P/S probability vector at sample ${i}`);
    if (p > peaks.P) { peaks.P = p; indices.P = i; }
    if (s > peaks.S) { peaks.S = s; indices.S = i; }
  }
  const p = peaks.P >= PHASE_THRESHOLD ? indices.P : null;
  let s = peaks.S >= PHASE_THRESHOLD ? indices.S : null;
  const sReason = s === null ? "below-threshold" : p !== null && s - p < PHASE_SEPARATION_SAMPLES ? "ps-separation" : "accepted";
  if (sReason === "ps-separation") s = null;
  return { probabilities: values, peaks, picks: { P: p, S: s },
    reasons: { P: p === null ? "below-threshold" : "accepted", S: sReason } };
}

export async function sha256(bytes: ArrayBuffer): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error("SHA-256 verification requires a secure browser context");
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), byte => byte.toString(16).padStart(2, "0")).join("");
}

export async function verifiedFetch(url: string, expectedHash: string): Promise<ArrayBuffer> {
  const response = await fetch(url, { credentials: "same-origin", cache: "no-store" });
  if (!response.ok) throw new Error(`Asset request failed: HTTP ${response.status}`);
  const bytes = await response.arrayBuffer();
  if (await sha256(bytes) !== expectedHash) throw new Error("Asset SHA-256 differs from the reviewed manifest");
  return bytes;
}
