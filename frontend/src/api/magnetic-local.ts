/** Public, in-browser M03 lane. The selected CSV is sent to a dedicated worker only. */

export const M03_LOCAL_LIMITS = Object.freeze({
  sourceBytes: 16 * 1024 * 1024,
  rows: 25_000,
  sourceLines: 25_001,
  gridCells: 100_000,
  crossoverSegmentTests: 2_000_000,
  wallMilliseconds: 180_000,
});

export interface MagneticLocalSource {
  source_id: string;
  citation: string;
  rights_decision: string;
  processing_state: string;
  value_unit: string;
  value_quantity: string;
  sensor_height_reference: string;
}

export interface MagneticLocalMapping {
  easting: string;
  northing: string;
  value: string;
  line_id: string;
  line_role: string;
  sensor_height_m: string;
  sample_order: string;
}

export interface MagneticLocalOptions {
  source: MagneticLocalSource;
  frame: { crs: string; coordinates_are_projected: true; linear_unit: "m" };
  mapping: MagneticLocalMapping;
  settings: { grid_spacing_m: number; holdout_fraction: number; seed: string };
}

export interface MagneticLocalResult {
  schema: "magnetic-flightline-process-result-1";
  claims: {
    source_hash_recomputed_from_original_bytes: true;
    corrections_applied: [];
    provider_grid_comparison: false;
    inverse_model: false;
    scientific_release_accepted: false;
  };
  source: MagneticLocalSource & { sha256: string };
  configuration: Record<string, unknown>;
  geometry_qc: Record<string, unknown>;
  split: { fit_line_ids: string[]; holdout_line_ids: string[]; [key: string]: unknown };
  heldout_interpolation: {
    heldout_line_ids: string[];
    heldout_row_count: number;
    supported_heldout_row_count: number;
    coverage_fraction: number;
    mae: number | null;
    rmse: number | null;
    interpretation: string;
  };
  grid: {
    x_easting_m: number[];
    y_northing_m: number[];
    shape_yx: [number, number];
    values: number[][];
    support_mask: boolean[][];
    unsupported_value_encoding: "zero plus false support mask";
  };
  limitations: string[];
}

export interface MagneticLocalExecution {
  lane: "browser-local-pyodide";
  pyodide_version: string;
  python_version: string;
  numpy_version: string;
  scipy_version: string;
  python_pipeline_sha256: string;
  original_csv_sha256: string;
  original_csv_bytes: number;
  original_csv_filename: string;
  resource_limits: typeof M03_LOCAL_LIMITS;
}

export interface MagneticLocalRun {
  result: MagneticLocalResult;
  execution: MagneticLocalExecution;
}

export interface MagneticLocalProgress {
  stage: "starting" | "loading-runtime" | "loading-scientific-packages" | "processing";
}

export interface MagneticLocalRunOptions {
  signal?: AbortSignal;
  onProgress?: (progress: MagneticLocalProgress) => void;
}

type WorkerReply =
  | { id: string; ok: true; result: MagneticLocalRun }
  | { id: string; ok: false; error: string };

function abortError(): DOMException {
  return new DOMException("M03 browser-local processing was cancelled", "AbortError");
}

function validateOptions(options: MagneticLocalOptions): void {
  const names = Object.values(options.mapping);
  if (names.some(name => !name.trim()) || new Set(names).size !== names.length)
    throw new Error("Map seven distinct, nonempty CSV column names before processing.");
  for (const [name, value] of Object.entries(options.source))
    if (typeof value !== "string" || !value.trim() || value.length > (name === "source_id" ? 256 : 256))
      throw new Error(`M03 source declaration ${name} must be nonempty text up to 256 characters.`);
  if (!options.frame.crs.trim() || options.frame.coordinates_are_projected !== true || options.frame.linear_unit !== "m")
    throw new Error("M03 requires a declared projected coordinate reference system in metres.");
  const { grid_spacing_m, holdout_fraction, seed } = options.settings;
  if (!Number.isFinite(grid_spacing_m) || grid_spacing_m <= 0 || grid_spacing_m > 100_000 ||
      !Number.isFinite(holdout_fraction) || holdout_fraction < 0.05 || holdout_fraction > 0.5 ||
      !seed.trim() || seed.length > 128)
    throw new Error("M03 grid spacing, whole-line holdout fraction or deterministic seed is outside its contract.");
}

/**
 * Run the repository's magnetic_processing.py in Pyodide. No CSV bytes or
 * derived arrays are sent to the application API. Cancellation terminates the
 * worker because Pyodide/WebAssembly cannot be preempted without shared-memory
 * headers that this static VPS does not currently configure.
 */
export async function runMagneticLocal(
  file: File,
  options: MagneticLocalOptions,
  runOptions: MagneticLocalRunOptions = {},
): Promise<MagneticLocalRun> {
  validateOptions(options);
  if (!(file instanceof File)) throw new TypeError("Select a local CSV file.");
  if (file.size < 1 || file.size > M03_LOCAL_LIMITS.sourceBytes)
    throw new Error(`This browser lane accepts CSV files up to ${M03_LOCAL_LIMITS.sourceBytes / 1024 / 1024} MiB.`);
  if (runOptions.signal?.aborted) throw abortError();

  const id = crypto.randomUUID();
  const worker = new Worker(new URL("../workers/magnetic-local.worker.ts", import.meta.url), { type: "module", name: "m03-magnetic-local" });
  return new Promise<MagneticLocalRun>((resolve, reject) => {
    let settled = false;
    const finish = (error?: Error, value?: MagneticLocalRun) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      runOptions.signal?.removeEventListener("abort", onAbort);
      worker.terminate();
      if (error) reject(error);
      else resolve(value!);
    };
    const onAbort = () => finish(abortError());
    const timeout = setTimeout(() => finish(new Error("M03 browser processing exceeded its 180 second execution limit.")), M03_LOCAL_LIMITS.wallMilliseconds);
    runOptions.signal?.addEventListener("abort", onAbort, { once: true });
    worker.onerror = event => finish(new Error(`M03 worker failed: ${event.message || "unknown worker error"}`));
    worker.onmessage = (event: MessageEvent<WorkerReply | { id: string; progress: MagneticLocalProgress }>) => {
      const message = event.data;
      if (message.id !== id) return;
      if ("progress" in message) {
        runOptions.onProgress?.(message.progress);
        return;
      }
      if (message.ok) finish(undefined, message.result);
      else finish(new Error(message.error));
    };
    void file.arrayBuffer().then(bytes => {
      if (settled) return;
      if (runOptions.signal?.aborted) return onAbort();
      worker.postMessage({ id, bytes, filename: file.name, options }, [bytes]);
    }).catch(error => finish(error instanceof Error ? error : new Error(String(error))));
  });
}
