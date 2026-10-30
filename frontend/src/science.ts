import { artifactBase, deploymentMode } from './lib/deployment';
import { formatForCurrentLocale } from "./lib/number-format";
import { gunzipSync } from "fflate";

export type Family =
  | "gravity"
  | "magnetics"
  | "mt"
  | "seismic"
  | "joint"
  | "learned";
export type Metric = number | boolean | null;
export type ModelArray = number[] | number[][];
export type Evaluation = {
  status: "recovered" | "unresolved" | "failed" | "negative-control";
  reason_codes: string[];
  reason?: string;
  reason_es?: string;
};
export type Uncertainty = {
  kind: string;
  conditioning: string;
  conditioning_es?: string;
  members: number;
  seed: number;
  lower: ModelArray;
  upper: ModelArray;
  mean: ModelArray;
  std: ModelArray;
  coverage?: number | null;
  quantiles: number[];
  units?: string;
  target?: string;
  support_coverage?: number;
  background_coverage?: number;
};
export type MethodSummary = {
  name: string;
  name_es: string;
  metrics: Record<string, Metric>;
  evaluation?: Evaluation;
  target?: { quantity: string; units: string; dimensionality: string | number; provenance: string };
  applicability?: { varied_parameter: boolean; reason: string };
};
export type Variant = {
  id: string;
  name: string;
  name_es: string;
  path: string;
  sha256: string;
  bytes: number;
  methods: Record<string, MethodSummary>;
  runtime_seconds: number;
};
export type Case = {
  id: string;
  family: Family;
  name: string;
  name_es: string;
  geometry: string;
  seed: number;
  display_scales?: Record<string, { range: [number, number]; maximum: number; signed: boolean }>;
  default_thresholds?: Record<string, number>;
  survey_max_abs?: number;
  variants: Variant[];
};
export type Catalog = {
  schema: "inverse-earth.catalog/v2";
  version: string;
  cases: Case[];
};
export type Curves = {
  real: number[];
  imag: number[];
  apparent: number[];
  phase: number[];
};
export type Method = MethodSummary & {
  model: number[] | number[][];
  secondary_model?: number[];
  column_model?: number[][];
  applicability?: { varied_parameter: boolean; reason: string };
  detection_validation?: DetectionValidation;
  cross_gradient?: number[];
  predicted: number[] | number[][][] | Curves;
  residual: number[] | number[][][] | Curves;
  network_input?: number[];
  history: number[];
  frames: (number[] | number[][])[];
  vectors?: number[][];
  vector_truth?: number[][];
  units?: string;
  checkpoint?: string;
  device?: string;
  target?: { quantity: string; units: string; dimensionality: string | number; provenance: string };
  magnetic_model?: number[];
  prior_membership?: number[][];
  petrophysical_prior?: { means: number[][]; covariances: number[][][]; weights: number[]; source: string };
  state_identity?: { final_frame_index: number | null; selected_iteration: number | null; frame_quantity: string; predictions: "final-model" };
  uncertainty?: Uncertainty;
  responsibilities?: number[][];
  membership?: number[];
  prior?: { name?: string; name_es?: string; weights?: number[]; means?: number[][]; source?: string; labels?: string[]; labels_es?: string[] };
  final_state?: { index?: number; selection?: string; objective?: number };
  frame_indices?: number[];
  history_indices?: number[];
  frame_history_indices?: number[];
  states?: { step: number; kind: string; objective: { total: number; data: number; regularization: number } }[];
};
export type DetectionValidation = {
  calibration_count: number;
  calibration_seed: number;
  ood_count: number;
  ood_seed: number;
  true_positive: number;
  false_positive: number;
  false_negative: number;
  true_negative: number;
  sensitivity: number;
  specificity: number;
  roc_auc: number;
  id_test_errors: number[];
  ood_test_errors: number[];
};
export type Run = {
  schema: "inverse-earth/v2";
  id: string;
  family: Family;
  name: string;
  name_es: string;
  geometry: string;
  variant: string;
  seed: number;
  engine: string;
  lane: string;
  truth: number[] | number[][];
  secondary_truth?: number[];
  column_truth?: number[][];
  initial?: ModelArray;
  units: string;
  data_units: string;
  methods: Record<string, Method>;
  parameters: Record<string, number | boolean | string | number[]>;
  grid?: {
    shape: number[];
    origin?: number[];
    spacing: number[];
    centers?: number[][];
  };
  survey?: {
    shape: number[];
    locations: number[][];
    observed: number[];
    clean: number[];
    sigma: number;
    active: boolean[];
    height: number;
    inclination: number;
    declination: number;
  };
  magnetic_survey?: { observed: number[]; clean: number[]; sigma: number };
  thickness?: number[];
  frequencies?: number[];
  observed?: Curves | number[][][];
  clean?: Curves;
  sigma?: number[];
  active?: boolean[];
  wavefields?: number[][][];
  dt?: number;
  wavefield_dt?: number;
  frequency?: number;
  sources?: number[][];
  receivers?: number[];
  runtime_seconds: number;
  provenance: {
    synthetic: boolean;
    version: string;
    license: string;
    seed: number;
    source?: string;
    source_url?: string;
    description?: string;
    description_es?: string;
    target_known?: boolean;
    data_kind?: string;
  };
};
export const appBase = artifactBase(deploymentMode, typeof location === 'undefined' ? '/' : location.pathname);
let fwiArtifactTail: Promise<void> = Promise.resolve();

function abortError(): DOMException {
  return new DOMException("The operation was aborted", "AbortError");
}

function abortable<T>(operation: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return operation;
  if (signal.aborted) return Promise.reject(abortError());
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => reject(abortError());
    signal.addEventListener("abort", onAbort, { once: true });
    operation.then(
      (value) => {
        signal.removeEventListener("abort", onAbort);
        if (signal.aborted) reject(abortError());
        else resolve(value);
      },
      (error) => {
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
}

async function loadFwiReference<T>(path: string, signal?: AbortSignal): Promise<T> {
  const previous = fwiArtifactTail;
  let release!: () => void;
  fwiArtifactTail = new Promise<void>((resolve) => { release = resolve; });
  const operation = previous.then(async () => {
    if (signal?.aborted) throw abortError();
    // The transport is gzip, but Fetch may already decode HTTP Content-Encoding
    // before exposing the body (Vite does this for .json.gz). Accept either the
    // original gzip member or browser-decoded JSON, then parse the same canonical
    // artifact. Keep requests serial to bound peak memory.
    const response = await fetch(`${appBase}data/v2/${path}.gz`, { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${path}.gz`);
    const transported = new Uint8Array(await response.arrayBuffer());
    const raw = transported[0] === 0x1f && transported[1] === 0x8b
      ? gunzipSync(transported)
      : transported;
    const json = new TextDecoder("utf-8", { fatal: true }).decode(raw);
    return JSON.parse(json) as T;
  });
  operation.then(release, release);
  return abortable(operation, signal);
}

export async function loadArtifact<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  if (/^FWI_[A-Z0-9_]+\/[a-z0-9_-]+\.json$/.test(path)) {
    return loadFwiReference<T>(path, signal);
  }
  const response = await fetch(`${appBase}data/v2/${path}`, { signal,cache:'no-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${path}`);
  return response.json();
}
export const familyLabels: Record<Family, [string, string]> = {
  gravity: ["Gravity", "Gravimetría"],
  magnetics: ["Magnetics", "Magnetometría"],
  mt: ["Magnetotellurics", "Magnetotelúrica"],
  seismic: ["Seismic", "Sísmica"],
  joint: ["Joint inversion", "Inversión conjunta"],
  learned: ["Learned inversion", "Inversión aprendida"],
};
export function extent(values: number[]): [number, number] {
  let lo = Infinity,
    hi = -Infinity;
  for (const v of values) {
    if (Number.isFinite(v)) {
      lo = Math.min(lo, v);
      hi = Math.max(hi, v);
    }
  }
  return !Number.isFinite(lo)
    ? [0, 1]
    : lo === hi
      ? [lo - 1, hi + 1]
      : [lo, hi];
}
export function format(v: number): string {
  return !Number.isFinite(v)
    ? "Unavailable"
    : Math.abs(v) < 0.001 && v !== 0
      ? formatForCurrentLocale(v, { notation: "scientific", maximumSignificantDigits: 3 })
      : formatForCurrentLocale(v, { maximumFractionDigits: Math.abs(v) < 1 ? 4 : 2 });
}
export function flatten(v: number[] | number[][]): number[] {
  return v.flat();
}
export function sliceVolume(
  values: number[],
  shape: number[],
  slice: number,
): number[][] {
  const [nz, ny, nx] = shape;
  const j = Math.max(0, Math.min(ny - 1, slice));
  return Array.from({ length: nz }, (_, iz) =>
    Array.from(
      { length: nx },
      (_, ix) => values[(nz - 1 - iz) * ny * nx + j * nx + ix],
    ),
  );
}

/** Choose the cross-line section that best exposes the modeled structure.
 * The section index is still user-controlled; this only avoids opening a 3-D
 * case on an arbitrary plane that misses its body entirely. */
export function preferredSection(values: number[], shape: number[], activeFraction = 0.1): number {
  if (shape.length !== 3 || shape.some((n) => !Number.isInteger(n) || n < 1)
      || values.length !== shape.reduce((a, b) => a * b, 1)
      || !values.every(Number.isFinite)) return 0;
  const maximum = Math.max(...values.map(Math.abs));
  if (!(maximum > 0)) return Math.floor(shape[1] / 2);
  const threshold = maximum * Math.max(0, Math.min(1, activeFraction));
  let best = Math.floor(shape[1] / 2), bestArea = -1;
  for (let section = 0; section < shape[1]; section++) {
    const image = sliceVolume(values, shape, section);
    const active: [number, number][] = [];
    image.forEach((row, depth) => row.forEach((v, east) => {
      if (Math.abs(v) > threshold) active.push([east, depth]);
    }));
    if (!active.length) continue;
    const east = active.map(([x]) => x), depth = active.map(([, z]) => z);
    const area = (Math.max(...east) - Math.min(...east) + 1)
      * (Math.max(...depth) - Math.min(...depth) + 1);
    const distance = Math.abs(section - (shape[1] - 1) / 2);
    const bestDistance = Math.abs(best - (shape[1] - 1) / 2);
    if (area > bestArea || (area === bestArea && distance < bestDistance)) {
      best = section;
      bestArea = area;
    }
  }
  return best;
}
export type Palette = "earth" | "field" | "velocity" | "error";
const palettes: Record<Palette, string[]> = {
  earth: ["#edf0e9", "#d8c5a4", "#b88c60", "#865638", "#4c3027"],
  field: ["#234c74", "#80abc4", "#f4f2ed", "#d79a6b", "#923f28"],
  velocity: ["#24384e", "#496c7e", "#87a09b", "#d2c5a0", "#e8bc6e"],
  error: ["#f1eee7", "#dcc9b0", "#c1815c", "#8b342c"],
};
export function color(
  value: number,
  range: [number, number],
  palette: Palette = "earth",
): string {
  const t = Math.max(
    0,
    Math.min(0.99999, (value - range[0]) / (range[1] - range[0] || 1)),
  );
  const colors = palettes[palette],
    index = t * (colors.length - 1),
    a = colors[Math.floor(index)],
    b = colors[Math.ceil(index)],
    f = index % 1;
  const rgb = [1, 3, 5].map((i) =>
    Math.round(
      parseInt(a.slice(i, i + 2), 16) * (1 - f) +
        parseInt(b.slice(i, i + 2), 16) * f,
    ),
  );
  return `rgb(${rgb.join(",")})`;
}
