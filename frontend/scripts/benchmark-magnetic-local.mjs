/** Measure the real browser-local M03 worker on an authored near-limit survey. */
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { createServer } from "vite";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repository = resolve(frontend, "..");
const args = process.argv.slice(2);
function argument(name) {
  const index = args.indexOf(name);
  if (index < 0 || !args[index + 1]) throw new Error(`Required ${name} absolute output path`);
  const value = resolve(args[index + 1]);
  if (!isAbsolute(value)) throw new Error(`${name} must be absolute`);
  const withinRepo = relative(repository, value);
  if (withinRepo === "" || (!withinRepo.startsWith("..") && !isAbsolute(withinRepo)))
    throw new Error("Performance receipts must be written outside the repository");
  if (existsSync(value)) throw new Error(`Refusing to overwrite ${value}`);
  return value;
}
const outputPath = argument("--output");
const repeatsArg = args.indexOf("--repeats");
const repeats = repeatsArg < 0 ? 3 : Number(args[repeatsArg + 1]);
if (!Number.isSafeInteger(repeats) || repeats < 1 || repeats > 10)
  throw new Error("--repeats must be an integer in [1, 10]");

function makeSurvey() {
  const rows = ["E,N,field,line,role,height,index"];
  for (let line = 0; line < 25; line++) {
    const x = line * 100;
    for (let sample = 0; sample < 1000; sample++) {
      const y = sample * 50;
      const value = 49_800 + 0.17 * x - 0.09 * y + 0.000001 * x * y;
      rows.push([x, y, value, `F${line}`, "flight", 120 + 0.001 * sample, sample].join(","));
    }
  }
  return `${rows.join("\n")}\n`;
}

const csv = makeSurvey();
const csvSha256 = createHash("sha256").update(csv).digest("hex");
const workerSourceSha256 = createHash("sha256").update(await readFile(
  resolve(frontend, "src/workers/magnetic-local.worker.ts"))).digest("hex");
const options = {
  source: { source_id: "m03-authored-resource-control", citation: "CAOS authored synthetic resource control",
    rights_decision: "authored synthetic; no external data", processing_state: "synthetic total-field anomaly",
    value_unit: "nT", value_quantity: "total-field anomaly", sensor_height_reference: "above-ground" },
  frame: { crs: "local projected metric control", coordinates_are_projected: true, linear_unit: "m" },
  mapping: { easting: "E", northing: "N", value: "field", line_id: "line", line_role: "role",
    sensor_height_m: "height", sample_order: "index" },
  settings: { grid_spacing_m: 250, holdout_fraction: 0.2, seed: "M03-resource-profile-2026-10-27" },
};

const server = await createServer({ configFile: resolve(frontend, "vite.config.ts"), root: frontend,
  logLevel: "error", server: { host: "127.0.0.1", port: 0, strictPort: false, hmr: false } });
let browser;
try {
  await server.listen();
  const address = server.httpServer?.address();
  if (!address || typeof address === "string") throw new Error("Vite did not provide a local port");
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(`http://127.0.0.1:${address.port}`, { waitUntil: "domcontentloaded" });
  const results = await page.evaluate(async ({ csvText, input, repeatCount }) => {
    const { runMagneticLocal } = await import("/src/api/magnetic-local.ts");
    const file = new File([csvText], "m03-resource-control.csv", { type: "text/csv" });
    const readJsHeap = () => performance.memory?.usedJSHeapSize ?? null;
    const jsHeapBefore = readJsHeap();
    let peakJsHeap = jsHeapBefore;
    const sampleHeap = () => {
      const used = readJsHeap();
      if (used !== null) peakJsHeap = Math.max(peakJsHeap ?? 0, used);
    };
    const sampler = setInterval(sampleHeap, 10);
    const runs = [];
    try {
      for (let index = 0; index <= repeatCount; index++) {
        const started = performance.now();
        const run = await runMagneticLocal(file, input);
        sampleHeap();
        runs.push({ ordinal: index, wall_ms: performance.now() - started,
          runtime_reused: run.execution.runtime_reused, runtime_load_ms: run.execution.runtime_load_ms,
          processing_ms: run.execution.processing_ms, total_worker_ms: run.execution.total_worker_ms,
          wasm_heap_capacity_bytes: run.execution.wasm_heap_capacity_bytes,
          original_csv_sha256: run.execution.original_csv_sha256,
          python_pipeline_sha256: run.execution.python_pipeline_sha256,
          heldout_rows: run.result.heldout_interpolation.heldout_row_count,
          supported_heldout_rows: run.result.heldout_interpolation.supported_heldout_row_count,
          grid_shape_yx: run.result.grid.shape_yx });
      }
    } finally {
      clearInterval(sampler);
    }
    return { user_agent: navigator.userAgent, hardware_concurrency: navigator.hardwareConcurrency,
      device_memory_gib: navigator.deviceMemory ?? null,
      js_heap_used_before_and_after_bytes: [jsHeapBefore, readJsHeap()],
      js_heap_peak_observed_bytes: peakJsHeap, runs };
  }, { csvText: csv, input: options, repeatCount: repeats });
  const report = {
    schema: "caos.m03-browser-resource-profile.v1", status: "measured-authored-control-only",
    measured_at: new Date().toISOString(), browser: `Chromium ${browser.version()}`,
    viewport_css_px: [1280, 900], dataset: { row_count: 25_000, csv_bytes: Buffer.byteLength(csv), csv_sha256: csvSha256,
      source: "authored deterministic parallel-line survey; not field data" },
    settings: options.settings, device: { user_agent: results.user_agent,
      hardware_concurrency: results.hardware_concurrency, device_memory_gib: results.device_memory_gib },
    implementation: { worker_source_sha256: workerSourceSha256,
      python_pipeline_sha256: results.runs[0].python_pipeline_sha256 },
    memory: { wasm_linear_heap_capacity_bytes_by_run: results.runs.map(run => run.wasm_heap_capacity_bytes),
      js_heap_used_before_and_after_bytes: results.js_heap_used_before_and_after_bytes,
      js_heap_peak_observed_bytes: results.js_heap_peak_observed_bytes,
      limitations: ["WASM linear heap capacity is the Pyodide allocator high-water capacity, not total browser process RSS.",
        "The JS heap sample is main-thread performance.memory where Chromium exposes it; it does not include worker RSS.",
        "One local headless Chromium host is not a supported-device population." ] },
    runs: results.runs,
  };
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, { flag: "wx" });
  process.stdout.write(`${JSON.stringify({ output: outputPath, schema: report.schema, row_count: 25_000,
    cold_wall_ms: report.runs[0].wall_ms,
    warm_wall_ms: report.runs.slice(1).map(run => run.wall_ms),
    wasm_heap_bytes: report.memory.wasm_linear_heap_capacity_bytes_by_run, status: report.status }, null, 2)}\n`);
} finally {
  await browser?.close();
  await server.close();
}
