/** Built-bundle UI check against separately supplied real STEAD display assets. */
import { readFile } from 'node:fs/promises';
import { basename, join, resolve } from 'node:path';
import { chromium } from '@playwright/test';
import { preview } from 'vite';

const index = process.argv.indexOf('--assets');
if (index < 0 || !process.argv[index + 1]) throw new Error('Pass --assets <absolute canonical STEAD browser asset directory>');
const assetsDir = resolve(process.argv[index + 1]);
const useServedAssets = process.argv.includes('--served');
const server = await preview({ preview: { host: '127.0.0.1', port: 0 } });
let browser;
try {
  const address = server.httpServer.address();
  if (!address || typeof address === 'string') throw new Error('Preview did not expose a port');
  const base = `http://127.0.0.1:${address.port}`;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  for (const sample of [
    { name: 'desktop-en-light', width: 1440, height: 900, lang: 'en', theme: 'light' },
    { name: 'phone-es-dark', width: 390, height: 844, lang: 'es', theme: 'dark' },
  ]) {
    const context = await browser.newContext({ viewport: { width: sample.width, height: sample.height } });
    await context.addInitScript(({lang, theme}) => {
      localStorage.setItem('caos.lang', lang);
      localStorage.setItem('caos.theme', theme);
    }, sample);
    const page = await context.newPage();
    page.setDefaultTimeout(120000);
    page.on('pageerror', error => errors.push(`${sample.name}: ${error.message}`));
    if (!useServedAssets) await page.route('**/data/phase/stead/**', async route => {
      const name = new URL(route.request().url()).pathname.split('/').at(-1);
      if (basename(name) !== name || !/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(name))
        throw new Error(`Unsafe asset name ${name}`);
      await route.fulfill({ status: 200, body: await readFile(join(assetsDir, name)),
        contentType: name.endsWith('.json') ? 'application/json' : 'application/octet-stream' });
    });
    await page.goto(`${base}/benchmark/`, { waitUntil: 'domcontentloaded' });
    const panel = page.locator('#phase-picker');
    await panel.waitFor();
    await panel.getByRole('button', { name: sample.lang === 'es' ? 'Cargar archivos STEAD revisados' : 'Load reviewed STEAD assets' }).click();
    await panel.getByRole('combobox', { name: sample.lang === 'es' ? 'Traza STEAD' : 'STEAD trace' }).waitFor();
    if (await panel.getByRole('option').count() !== 24) throw new Error(`${sample.name}: browser selection count differs`);
    await panel.getByRole('button', { name: sample.lang === 'es' ? 'Ejecutar inferencia web' : 'Run browser inference' }).click();
    await panel.getByRole('img', { name: sample.lang === 'es' ? 'Puntajes N P S calculados en navegador' : 'Browser-computed N P S scores' }).waitFor();
    if (await panel.locator('.phase-arrivals strong').count() !== 3 ||
        !(await panel.locator('.phase-arrivals strong').first().innerText()).includes('s'))
      throw new Error(`${sample.name}: computed arrival readout is absent`);
    await panel.getByText('0.9808').waitFor();
    await panel.locator('.phase-plots').screenshot({ path: resolve('dist', `${sample.name}-phase-plots.png`) });
    await panel.locator('.phase-benchmark').screenshot({ path: resolve('dist', `${sample.name}-heldout-benchmark.png`) });
    if (sample.name === 'desktop-en-light') {
      const traceBytes = await readFile(join(assetsDir, 'trace-00.f32'));
      const data = new DataView(traceBytes.buffer, traceBytes.byteOffset, traceBytes.byteLength);
      const values = Array.from({ length: 3 }, (_, c) => Array.from({ length: 6000 }, (_, i) => data.getFloat32((c * 6000 + i) * 4, true)));
      const local = {
        schema: 'caos.phase-browser-trace.v1', trace_id: 'local-qa-real-stead', source: 'local read of reviewed STEAD trace',
        sample_rate_hz: 100, component_order: ['E','N','Z'], representation: 'normalized', unit: 'dimensionless',
        qc: { components_measured: true, gaps: false, clipped: false, response_corrected: false },
        channels: { E: values[0], N: values[1], Z: values[2] },
      };
      await panel.locator('.phase-local-files summary').click();
      await panel.locator('input[accept=".json,application/json"]').setInputFiles({ name: 'local-stead.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(local)) });
      await panel.getByRole('button', { name: 'Run browser inference' }).click();
      await panel.getByText('6.99 s · 0.9972').waitFor();
      local.sample_rate_hz = 50;
      await panel.locator('input[accept=".json,application/json"]').setInputFiles({ name: 'wrong-rate.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(local)) });
      await panel.getByRole('alert').getByText(/Only 100 Hz records/).waitFor();
      await panel.getByRole('combobox', { name: 'STEAD trace' }).selectOption('0');
    }
    const fit = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth,
      height: document.documentElement.scrollHeight, viewportHeight: innerHeight }));
    if (fit.width > fit.viewport || fit.height > fit.viewportHeight + 1)
      errors.push(`${sample.name}: document overflow ${JSON.stringify(fit)}`);
    await panel.screenshot({ path: resolve('dist', `${sample.name}-phase-picker.png`) });
    await panel.getByRole('combobox', { name: sample.lang === 'es' ? 'Traza STEAD' : 'STEAD trace' }).selectOption('19');
    await panel.getByText(sample.lang === 'es' ? /QC rechazada; esta traza/ : /QC rejected; no waveform asset/).waitFor();
    if (await panel.getByRole('button', { name: sample.lang === 'es' ? 'Ejecutar inferencia web' : 'Run browser inference' }).isEnabled())
      throw new Error(`${sample.name}: rejected trace can be inferred`);
    if (await panel.getByRole('img', { name: sample.lang === 'es' ? 'Puntajes N P S calculados en navegador' : 'Browser-computed N P S scores' }).count())
      throw new Error(`${sample.name}: stale probabilities remain on QC rejection`);
    await context.close();
    process.stdout.write(`${sample.name}: real model run, waveform/probability plots and QC exclusion verified; ${JSON.stringify(fit)}\n`);
  }
  if (errors.length) throw new Error(errors.join('\n'));
  process.stdout.write(`Built-bundle M13 picker UI PASS (${useServedAssets ? 'Vite publicDir' : 'Playwright asset route'}); screenshots in frontend/dist\n`);
} finally {
  await browser?.close();
  await new Promise((done, reject) => server.httpServer.close(error => error ? reject(error) : done()));
}
