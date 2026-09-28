/** Local-only real held-out parity gate. No oracle bytes enter the web server or repository. */
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { basename, isAbsolute, join, resolve } from 'node:path';
import { chromium } from '@playwright/test';
import { createServer } from 'vite';

const args = process.argv.slice(2);
function argument(name) {
  const index = args.indexOf(name);
  if (index < 0 || !args[index + 1]) throw new Error(`Required ${name} absolute directory path`);
  const value = resolve(args[index + 1]);
  if (!isAbsolute(value)) throw new Error(`${name} must resolve to an absolute path`);
  return value;
}
const assetsDir = argument('--assets');
const oracleDir = argument('--oracle');
const useServedAssets = args.includes('--served');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const file = async (dir, name) => {
  if (basename(name) !== name || !/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(name))
    throw new Error(`Unsafe asset filename: ${name}`);
  return readFile(join(dir, name));
};
function f32(bytes) {
  if (bytes.length !== 72000) throw new Error(`Expected 72,000 probability bytes, got ${bytes.length}`);
  const values = new Float32Array(18000);
  for (let i = 0; i < values.length; i++) values[i] = bytes.readFloatLE(i * 4);
  return values;
}
function argmax(values, offset) {
  let best = 0;
  for (let i = 1; i < 6000; i++) if (values[offset + i] > values[offset + best]) best = i;
  return best;
}

const manifestBytes = await file(assetsDir, 'manifest.json');
const manifest = JSON.parse(manifestBytes.toString('utf8'));
const receipt = JSON.parse((await file(oracleDir, 'receipt.json')).toString('utf8'));
if (digest(manifestBytes) !== receipt.asset_manifest_sha256 ||
    manifest.model.sha256 !== receipt.onnx_sha256 ||
    manifest.model.checkpoint_sha256 !== receipt.checkpoint_sha256)
  throw new Error('Asset manifest does not match the private frozen parity receipt');
if (manifest.records.length !== 24 || receipt.records.length !== 23 ||
    manifest.records.filter(record => record.status === 'qc-rejected').length !== 1 ||
    manifest.records.filter(record => record.status === 'qc-valid').length !== 23)
  throw new Error('The predeclared 24/23/1 browser population changed');

const server = await createServer({ configFile: resolve('vite.config.ts'), server: { host: '127.0.0.1', port: 0 } });
let browser;
try {
  await server.listen();
  const address = server.httpServer.address();
  if (!address || typeof address === 'string') throw new Error('Vite did not provide a local port');
  const origin = `http://127.0.0.1:${address.port}`;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(120000);
  if (!useServedAssets) await page.route('**/data/phase/stead/**', async route => {
    const name = new URL(route.request().url()).pathname.split('/').at(-1);
    try {
      const bytes = await file(assetsDir, name);
      await route.fulfill({ status: 200, body: bytes, contentType: name.endsWith('.json') ? 'application/json' : 'application/octet-stream' });
    } catch (cause) {
      await route.fulfill({ status: 404, body: String(cause) });
    }
  });
  await page.goto(origin, { waitUntil: 'domcontentloaded' });
  await page.evaluate(async expectedManifestHash => {
    const contract = await import('/src/phase-picker.ts');
    const runtime = await import('/src/phase-runtime.ts');
    const response = await fetch('/data/phase/stead/manifest.json');
    if (!response.ok) throw new Error(`Served manifest HTTP ${response.status}`);
    const manifestBytes = await response.arrayBuffer();
    if (await contract.sha256(manifestBytes) !== expectedManifestHash)
      throw new Error('Served manifest differs from the private frozen parity receipt');
    const parsed = contract.parsePhaseManifest(JSON.parse(new TextDecoder().decode(manifestBytes)));
    const model = await contract.verifiedFetch(`/data/phase/stead/${parsed.model.file}`, parsed.model.sha256);
    if (model.byteLength !== parsed.model.bytes) throw new Error('Model byte count differs');
    window.__phaseParity = { contract, runtime, manifest: parsed, session: await runtime.createPhaseSession(model) };
  }, receipt.asset_manifest_sha256);
  let maxAbs = 0, maxPeakSamples = 0, totalMs = 0;
  for (const [index, record] of manifest.records.entries()) {
    if (record.status === 'qc-rejected') {
      if (record.waveform_file || receipt.records.some(item => item.trace_id === record.trace_id))
        throw new Error(`QC-rejected record ${record.trace_id} acquired a waveform or oracle row`);
      continue;
    }
    const oracleRow = receipt.records.find(item => item.trace_id === record.trace_id);
    if (!oracleRow || oracleRow.waveform_file !== record.waveform_file ||
        oracleRow.waveform_sha256 !== record.waveform_sha256)
      throw new Error(`Oracle/asset identity mismatch at display row ${index}`);
    const expectedBytes = await file(oracleDir, oracleRow.expected_probabilities_file);
    if (digest(expectedBytes) !== oracleRow.expected_probabilities_sha256)
      throw new Error(`Private oracle SHA-256 mismatch for ${record.trace_id}`);
    const expected = f32(expectedBytes);
    const browserResult = await page.evaluate(async rowIndex => {
      const { contract, manifest: parsed, session } = window.__phaseParity;
      const row = parsed.records[rowIndex];
      const bytes = await contract.verifiedFetch(`/data/phase/stead/${row.waveform_file}`, row.waveform_sha256);
      const trace = contract.parseNormalizedF32(bytes, row);
      const start = performance.now();
      const output = await session.run(trace);
      return { traceId: trace.traceId, probabilities: Array.from(output.probabilities),
        picks: output.picks, elapsedMs: performance.now() - start };
    }, index);
    if (browserResult.traceId !== record.trace_id || browserResult.probabilities.length !== 18000)
      throw new Error(`Browser returned wrong trace or output shape at row ${index}`);
    let localMax = 0;
    for (let i = 0; i < expected.length; i++)
      localMax = Math.max(localMax, Math.abs(expected[i] - browserResult.probabilities[i]));
    maxAbs = Math.max(maxAbs, localMax);
    if (localMax > 0.001) throw new Error(`${record.trace_id}: max probability error ${localMax} exceeds 0.001`);
    for (const [phase, offset] of [['P', 6000], ['S', 12000]]) {
      const peakError = Math.abs(argmax(expected, offset) - argmax(browserResult.probabilities, offset));
      maxPeakSamples = Math.max(maxPeakSamples, peakError);
      if (peakError > 1) throw new Error(`${record.trace_id}: ${phase} peak differs by ${peakError} samples`);
      const canonicalPick = oracleRow.torch_picks_s[phase];
      const browserPick = browserResult.picks[phase];
      if ((canonicalPick === null) !== (browserPick === null) ||
          (canonicalPick !== null && Math.abs(canonicalPick * 100 - browserPick) > 1))
        throw new Error(`${record.trace_id}: ${phase} pick/abstention differs from frozen PyTorch`);
    }
    totalMs += browserResult.elapsedMs;
    process.stdout.write(`${index + 1}/24 ${record.trace_id}: maxabs ${localMax.toExponential(2)}, ${browserResult.elapsedMs.toFixed(0)} ms\n`);
  }
  await page.evaluate(() => window.__phaseParity.session.release());
  process.stdout.write(JSON.stringify({ status: 'pass', checked: 23, retainedQcFailure: 1,
    fullBenchmarkSelected: 6000, maxAbs, maxPeakSamples, meanBrowserInferenceMs: totalMs / 23,
    assetDelivery: useServedAssets ? 'vite-publicDir' : 'playwright-route',
    manifestSha256: receipt.asset_manifest_sha256, modelSha256: receipt.onnx_sha256 }, null, 2) + '\n');
} finally {
  await browser?.close();
  await server.close();
}
