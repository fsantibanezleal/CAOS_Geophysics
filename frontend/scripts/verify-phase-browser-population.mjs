/** Compare actual browser WASM inference with the same frozen ONNX run through CPU ONNX Runtime on every public display trace. */
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, isAbsolute, join, resolve } from "node:path";
import { chromium } from "@playwright/test";
import { createServer } from "vite";

const args = process.argv.slice(2);
function argument(name) {
  const index = args.indexOf(name);
  if (index < 0 || !args[index + 1]) throw new Error(`Required ${name} absolute path`);
  const value = resolve(args[index + 1]);
  if (!isAbsolute(value)) throw new Error(`${name} must resolve to an absolute path`);
  return value;
}
const assetsDir = argument("--assets");
const analysisPath = argument("--analysis");
const referenceDir = argument("--references");
const reportArg = args.indexOf("--report");
const reportPath = reportArg >= 0 && args[reportArg + 1] ? resolve(args[reportArg + 1]) : null;
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
async function safeFile(dir, name) {
  if (basename(name) !== name || !/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(name))
    throw new Error(`Unsafe asset filename: ${name}`);
  return readFile(join(dir, name));
}
function f32(bytes) {
  if (bytes.length !== 3 * 6000 * 4) throw new Error(`Expected 72,000 probability bytes; got ${bytes.length}`);
  const values = new Float32Array(18000);
  for (let i = 0; i < values.length; i++) values[i] = bytes.readFloatLE(i * 4);
  return values;
}
function peak(values, offset) {
  let best = 0;
  for (let i = 1; i < 6000; i++) if (values[offset + i] > values[offset + best]) best = i;
  return best;
}
const manifestBytes = await safeFile(assetsDir, "manifest.json");
const manifest = JSON.parse(manifestBytes.toString("utf8"));
const analysis = JSON.parse(await readFile(analysisPath, "utf8"));
const manifestHash = digest(manifestBytes);
if (analysis.schema !== "caos.m13-browser-display-subset-analysis.v1" ||
    analysis.manifest_sha256 !== manifestHash || analysis.model_sha256 !== manifest.model.sha256 ||
    analysis.selected_count !== 24 || analysis.qc_valid_count !== 23 || analysis.qc_rejected_count !== 1 ||
    manifest.browser_parity_verified !== false)
  throw new Error("CPU reference analysis and frozen browser asset manifest do not match");
const expectedByTrace = new Map(analysis.traces.map(row => [row.trace_id, row]));
if (expectedByTrace.size !== 23) throw new Error("CPU reference does not contain exactly 23 valid display traces");

const server = await createServer({ configFile: resolve("vite.config.ts"), server: { host: "127.0.0.1", port: 0 } });
let browser;
try {
  await server.listen();
  const address = server.httpServer.address();
  if (!address || typeof address === "string") throw new Error("Vite did not provide a local port");
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(120000);
  await page.route("**/data/phase/stead/**", async route => {
    const name = new URL(route.request().url()).pathname.split("/").at(-1);
    try {
      const bytes = await safeFile(assetsDir, name);
      await route.fulfill({ status: 200, body: bytes, contentType: name.endsWith(".json") ? "application/json" : "application/octet-stream" });
    } catch (cause) {
      await route.fulfill({ status: 404, body: String(cause) });
    }
  });
  await page.goto(`http://127.0.0.1:${address.port}`, { waitUntil: "domcontentloaded" });
  await page.evaluate(async expectedHash => {
    const contract = await import("/src/phase-picker.ts");
    const runtime = await import("/src/phase-runtime.ts");
    const response = await fetch("/data/phase/stead/manifest.json");
    if (!response.ok) throw new Error(`Manifest HTTP ${response.status}`);
    const bytes = await response.arrayBuffer();
    if (await contract.sha256(bytes) !== expectedHash) throw new Error("Served browser manifest hash differs");
    const manifest = contract.parsePhaseManifest(JSON.parse(new TextDecoder().decode(bytes)));
    const model = await contract.verifiedFetch(`/data/phase/stead/${manifest.model.file}`, manifest.model.sha256);
    if (model.byteLength !== manifest.model.bytes) throw new Error("ONNX byte count differs from the manifest");
    window.__phaseParity = { contract, runtime, manifest, session: await runtime.createPhaseSession(model) };
  }, manifestHash);

  let maximumAbsoluteError = 0;
  let maximumPeakDifferenceSamples = 0;
  let totalInferenceMs = 0;
  let checked = 0;
  const traceResults = [];
  for (const [index, record] of manifest.records.entries()) {
    if (record.status === "qc-rejected") {
      if (record.waveform_file || record.waveform_sha256 || expectedByTrace.has(record.trace_id))
        throw new Error(`QC-rejected ${record.trace_id} has waveform/reference input`);
      continue;
    }
    const cpuRow = expectedByTrace.get(record.trace_id);
    if (!cpuRow || cpuRow.trace_id !== record.trace_id)
      throw new Error(`Missing CPU result for ${record.trace_id}`);
    const browserResult = await page.evaluate(async rowIndex => {
      const { contract, manifest, session } = window.__phaseParity;
      const row = manifest.records[rowIndex];
      const bytes = await contract.verifiedFetch(`/data/phase/stead/${row.waveform_file}`, row.waveform_sha256);
      const trace = contract.parseNormalizedF32(bytes, row);
      const started = performance.now();
      const scores = await session.run(trace);
      return { traceId: trace.traceId, probabilities: Array.from(scores.probabilities),
        picks: scores.picks, elapsedMs: performance.now() - started };
    }, index);
    if (browserResult.traceId !== record.trace_id || browserResult.probabilities.length !== 18000)
      throw new Error(`Wrong browser trace/output shape for ${record.trace_id}`);
    const referenceName = `${basename(record.waveform_file, ".f32")}.probabilities.f32`;
    const cpuBytes = await safeFile(referenceDir, referenceName);
    if (!cpuRow.m13_probabilities_sha256 || digest(cpuBytes) !== cpuRow.m13_probabilities_sha256)
      throw new Error(`CPU reference hash differs for ${record.trace_id}`);
    const cpu = f32(cpuBytes);
    let traceMax = 0;
    for (let i = 0; i < cpu.length; i++)
      traceMax = Math.max(traceMax, Math.abs(cpu[i] - browserResult.probabilities[i]));
    maximumAbsoluteError = Math.max(maximumAbsoluteError, traceMax);
    if (traceMax > 0.001) throw new Error(`${record.trace_id}: max |CPU-WASM| ${traceMax} > 0.001`);
    for (const [phase, offset] of [["P", 6000], ["S", 12000]]) {
      const samples = Math.abs(peak(cpu, offset) - peak(browserResult.probabilities, offset));
      maximumPeakDifferenceSamples = Math.max(maximumPeakDifferenceSamples, samples);
      if (samples > 1) throw new Error(`${record.trace_id} ${phase} probability peak differs by ${samples} samples`);
      const cpuPick = cpuRow[`m13_${phase.toLowerCase()}_s`];
      const wasmPick = browserResult.picks[phase];
      if ((cpuPick === null) !== (wasmPick === null) ||
          (cpuPick !== null && Math.abs(cpuPick * 100 - wasmPick) > 1))
        throw new Error(`${record.trace_id} ${phase} CPU/WASM pick or abstention differs`);
    }
    totalInferenceMs += browserResult.elapsedMs;
    traceResults.push({ traceId: record.trace_id, maxProbabilityAbsoluteError: traceMax,
      peakDifferenceSamples: { P: Math.abs(peak(cpu, 6000) - peak(browserResult.probabilities, 6000)),
        S: Math.abs(peak(cpu, 12000) - peak(browserResult.probabilities, 12000)) },
      browserInferenceMs: browserResult.elapsedMs });
    checked++;
    process.stdout.write(`${checked}/23 ${record.trace_id}: maxabs ${traceMax.toExponential(2)}, ${browserResult.elapsedMs.toFixed(0)} ms\n`);
  }
  await page.evaluate(() => window.__phaseParity.session.release());
  if (checked !== 23) throw new Error(`Expected 23 browser-inferred traces, checked ${checked}`);
  const report = { schema: "caos.m13-browser-population-parity.v1", status: "pass",
    measuredAt: new Date().toISOString(),
    parity: { sameFrozenOnnx: true, reference: analysis.reference_runtime,
      browser: "ONNX Runtime Web WASM through frontend/src/phase-runtime.ts",
      browserRuntimeVersion: JSON.parse(await readFile(new URL("../node_modules/onnxruntime-web/package.json", import.meta.url), "utf8")).version,
      chromiumVersion: browser.version(),
      probabilityAbsoluteTolerance: 0.001, peakToleranceSamples: 1, pickToleranceSamples: 1 },
    population: { selected: 24, qcValidBrowserInferences: checked, qcRejectedExcluded: 1,
      selectionBeforeHeldoutScoring: true, allCpuReferenceHashesVerified: true, accuracyClaim: false },
    maxProbabilityAbsoluteError: maximumAbsoluteError,
    maxPeakDifferenceSamples: maximumPeakDifferenceSamples,
    meanBrowserInferenceMs: totalInferenceMs / checked,
    manifestSha256: manifestHash, modelSha256: manifest.model.sha256,
    limitations: ["CPU ONNX and browser WASM execute the same exported checkpoint; this is runtime parity, not an independent PyTorch-oracle comparison.",
      "The preselected 23-trace display subset is not an accuracy population; the frozen 6,000-trace benchmark remains the reported aggregate result."],
    traces: traceResults };
  if (reportPath) {
    await mkdir(resolve(reportPath, ".."), { recursive: true });
    await writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");
  }
  process.stdout.write(JSON.stringify({ ...report, reportPath }, null, 2) + "\n");
} finally {
  await browser?.close();
  await server.close();
}
