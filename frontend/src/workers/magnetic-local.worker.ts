/// <reference types="vite/client" />

// Import the canonical pipeline as build-time source. The browser executes this
// exact file; no JavaScript rewrite of its numerical routines is maintained.
import magneticPipelineSource from "../../../data-pipeline/magnetic_processing.py?raw";

const PYODIDE_VERSION = "0.29.5";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const ROW_LIMIT = 25_000;
const SOURCE_LINE_LIMIT = 25_001;
const GRID_CELL_LIMIT = 100_000;
const CROSSOVER_TEST_LIMIT = 2_000_000;

interface PyodideRuntime {
  FS: { writeFile(path: string, data: Uint8Array): void };
  loadPackage(packages: string[]): Promise<void>;
  runPythonAsync<T = unknown>(source: string): Promise<T>;
  runPython<T = unknown>(source: string): T;
}

interface Job {
  id: string;
  bytes: ArrayBuffer;
  filename: string;
  options: {
    source: Record<string, string>;
    frame: Record<string, unknown>;
    mapping: Record<string, string>;
    settings: Record<string, unknown>;
  };
}

const scope = self as unknown as {
  onmessage: ((event: MessageEvent<Job>) => void) | null;
  postMessage(value: unknown): void;
};

let runtimePromise: Promise<PyodideRuntime> | undefined;
function runtime(): Promise<PyodideRuntime> {
  runtimePromise ??= (async () => {
    scope.postMessage({ id: activeId, progress: { stage: "loading-runtime" } });
    const moduleUrl = `${PYODIDE_BASE}pyodide.mjs`;
    const pyodideModule = await import(/* @vite-ignore */ moduleUrl) as {
      loadPyodide(options: { indexURL: string }): Promise<PyodideRuntime>;
    };
    const pyodide = await pyodideModule.loadPyodide({ indexURL: PYODIDE_BASE });
    scope.postMessage({ id: activeId, progress: { stage: "loading-scientific-packages" } });
    await pyodide.loadPackage(["numpy", "scipy"]);
    pyodide.FS.writeFile("/magnetic_processing.py", new TextEncoder().encode(magneticPipelineSource));
    return pyodide;
  })();
  return runtimePromise;
}

let activeId = "";
const runCanonicalPipeline = `
import json, sys
from pathlib import Path
sys.path.insert(0, "/")
import magnetic_processing as m03

with open("/m03-config.json", "r", encoding="utf-8") as stream:
    cfg = json.load(stream)
request = m03.read_csv(
    Path("/m03-original.csv"),
    field_map=cfg["mapping"],
    source_metadata=cfg["source"],
    frame=cfg["frame"],
    settings=cfg["settings"],
)
if len(request["rows"]) > ${ROW_LIMIT}:
    raise m03.MagneticProcessingError("Browser lane limit is ${ROW_LIMIT.toLocaleString("en-US")} observations; use the local pipeline for larger surveys.")

# Fail before allocating the interpolation mesh if the source exceeds the
# public worker budget. These are preflight checks only; processing remains in
# the canonical m03.process() implementation below.
_, config, points = m03._parse_request(request)
segments = m03._line_segments(points)
ordered_lines = sorted(segments)
segment_tests = sum(
    len(segments[left]) * len(segments[right])
    for i, left in enumerate(ordered_lines)
    for right in ordered_lines[i + 1:]
    if left[0] != right[0]
)
if segment_tests > ${CROSSOVER_TEST_LIMIT}:
    raise m03.MagneticProcessingError("Browser crossover-QC budget exceeded; reduce line samples or use the local pipeline.")
coordinates = [(point.easting_m, point.northing_m) for point in points]
xmin, xmax = min(x for x, _ in coordinates), max(x for x, _ in coordinates)
ymin, ymax = min(y for _, y in coordinates), max(y for _, y in coordinates)
nx = int((xmax - xmin) // config["grid_spacing_m"]) + 1
ny = int((ymax - ymin) // config["grid_spacing_m"]) + 1
if nx < 2 or ny < 2 or nx * ny > ${GRID_CELL_LIMIT}:
    raise m03.MagneticProcessingError("Browser grid budget is ${GRID_CELL_LIMIT.toLocaleString("en-US")} cells; increase spacing or use the local pipeline.")

result = m03.process(request, source_hash_verified=True)
json.dumps(result, allow_nan=False, separators=(",", ":"))
`;

async function sha256(bytes: Uint8Array): Promise<string> {
  const owned = new Uint8Array(bytes.byteLength);
  owned.set(bytes);
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", owned.buffer));
  return Array.from(digest, value => value.toString(16).padStart(2, "0")).join("");
}

scope.onmessage = async ({ data }: MessageEvent<Job>) => {
  activeId = data.id;
  try {
    if (!(data.bytes instanceof ArrayBuffer) || data.bytes.byteLength < 1 || data.bytes.byteLength > 16 * 1024 * 1024)
      throw new Error("M03 browser lane accepts original CSV files from 1 byte to 16 MiB.");
    const originalBytes = new Uint8Array(data.bytes);
    let physicalLines = 1;
    for (let i = 0; i < originalBytes.length; i++) {
      if (originalBytes[i] === 10 || (originalBytes[i] === 13 && originalBytes[i + 1] !== 10)) physicalLines++;
      if (physicalLines > SOURCE_LINE_LIMIT + 1)
        throw new Error(`Browser lane limit is ${ROW_LIMIT.toLocaleString("en-US")} CSV observations; multiline records count toward the conservative physical-line bound.`);
    }
    if (originalBytes[originalBytes.length - 1] === 10 || originalBytes[originalBytes.length - 1] === 13) physicalLines--;
    if (physicalLines > SOURCE_LINE_LIMIT)
      throw new Error(`Browser lane limit is ${ROW_LIMIT.toLocaleString("en-US")} CSV observations; reduce the source or use the local pipeline.`);
    const pyodide = await runtime();
    scope.postMessage({ id: data.id, progress: { stage: "processing" } });
    pyodide.FS.writeFile("/m03-original.csv", originalBytes);
    const config = new TextEncoder().encode(JSON.stringify(data.options));
    pyodide.FS.writeFile("/m03-config.json", config);
    const encoded = await pyodide.runPythonAsync<string>(runCanonicalPipeline);
    const result = JSON.parse(encoded);
    if (result?.schema !== "magnetic-flightline-process-result-1" ||
        result?.claims?.source_hash_recomputed_from_original_bytes !== true ||
        result?.source?.sha256 !== await sha256(originalBytes))
      throw new Error("Canonical M03 result failed original-byte identity verification.");
    const versions = JSON.parse(pyodide.runPython<string>(
      'import json, numpy, scipy, sys; json.dumps({"python": ".".join(map(str, sys.version_info[:3])), "numpy": numpy.__version__, "scipy": scipy.__version__})',
    ));
    const pipelineHash = await sha256(new TextEncoder().encode(magneticPipelineSource));
    scope.postMessage({
      id: data.id,
      ok: true,
      result: {
        result,
        execution: {
          lane: "browser-local-pyodide",
          pyodide_version: PYODIDE_VERSION,
          python_version: versions.python,
          numpy_version: versions.numpy,
          scipy_version: versions.scipy,
          python_pipeline_sha256: pipelineHash,
          original_csv_sha256: result.source.sha256,
          original_csv_bytes: originalBytes.byteLength,
          original_csv_filename: data.filename,
          resource_limits: {
            sourceBytes: 16 * 1024 * 1024,
            rows: ROW_LIMIT,
            sourceLines: SOURCE_LINE_LIMIT,
            gridCells: GRID_CELL_LIMIT,
            crossoverSegmentTests: CROSSOVER_TEST_LIMIT,
            wallMilliseconds: 180_000,
          },
        },
      },
    });
  } catch (error) {
    scope.postMessage({ id: data.id, ok: false, error: error instanceof Error ? error.message : String(error) });
  }
};
